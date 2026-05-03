"""Tests F-france-import-datasets-draft-seed.

Cover the new ``import_france_candidate_datasets`` management command:

1. Both DRAFT datasets are created on first run.
2. Mini-fixture CSVs (synthetic values, NOT real Mornet/Gazette numbers)
   import the expected row counts.
3. A re-run is idempotent: same input + same dataset → same row count,
   no duplicates, only updates.
4. The command refuses to write into a dataset that already exists with
   a status != DRAFT (e.g. someone manually promoted it).
5. Rows whose ``row_type`` is not in the whitelist are skipped (counted
   in ``rows_skipped`` on the ExtractionLog).
6. Rows with empty amount/coefficient/years_value are skipped.
7. Static check: the command source file contains no destructive
   ``delete()`` / ``QuerySet.delete`` / ``raw()`` calls. Re-runs may
   only ``update_or_create``.
8. The import does not change ``LegalSource.status`` (Mornet + Gazette
   stay ``needs_review``).
9. The import does not create any ``CalculationFormula`` for the FR
   datasets.
10. ``run_simulation(FR-NATIONAL, road_accident_bodily_injury)`` stays
    ``unavailable_requires_legal_validation`` after import.
11. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR resta invariata.

Test fixtures use synthetic numeric values (e.g. amount=999, coef=1.234)
so this file never accidentally serves as a "second source of truth" for
the real FR bareme.
"""

from __future__ import annotations

import re
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND_FILE = (
    REPO_ROOT
    / "apps"
    / "compensation"
    / "management"
    / "commands"
    / "import_france_candidate_datasets.py"
)


# ---------------------------------------------------------------------------
# Fixtures: minimal synthetic CSVs (not real FR values).
# ---------------------------------------------------------------------------


@pytest.fixture
def fr_legal_sources(db):
    """Pre-seed the FR LegalSource rows the command resolves by slug."""
    from datetime import date

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    mornet = LegalSource.objects.create(
        slug="fr-referentiel-mornet-2024",
        title="Référentiel Mornet 2024 — fixture",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.DOCTRINE,
        reliability=Reliability.MEDIUM,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2024, 1, 1),
    )
    gazette = LegalSource.objects.create(
        slug="fr-bareme-capitalisation-gazette-palais-2022",
        title="Gazette du Palais 2022 — fixture",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.DOCTRINE,
        reliability=Reliability.MEDIUM,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2022, 1, 1),
    )
    return {
        "country": france,
        "jurisdiction": juris,
        "mornet": mornet,
        "gazette": gazette,
    }


def _write_synthetic_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    path.write_text(
        ",".join(header) + "\n" + "\n".join(",".join(r) for r in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _mornet_dfp_csv(tmp_path: Path) -> Path:
    return _write_synthetic_csv(
        tmp_path / "mornet_dfp.csv",
        header=[
            "row_type",
            "victim_age_min",
            "victim_age_max",
            "disability_min",
            "disability_max",
            "amount_min",
            "amount_mid",
            "amount_max",
            "currency",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "fr_dfp_per_age_disability_amount_per_point",
                "0",
                "10",
                "1",
                "5",
                "999",
                "999",
                "999",
                "EUR",
                "71",
                "legal_review_required=true;no_human_legal_approval=true;synthetic=test_fixture",
            ],
            [
                "fr_dfp_per_age_disability_amount_per_point",
                "11",
                "20",
                "1",
                "5",
                "888",
                "888",
                "888",
                "EUR",
                "71",
                "legal_review_required=true;no_human_legal_approval=true;synthetic=test_fixture",
            ],
        ],
    )


def _mornet_affection_csv(tmp_path: Path) -> Path:
    return _write_synthetic_csv(
        tmp_path / "mornet_affection.csv",
        header=[
            "row_type",
            "relation_code",
            "relation_label_fr",
            "amount_min",
            "amount_mid",
            "amount_max",
            "currency",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "fr_prejudice_affection_per_relation_amount",
                "synthetic_relation_a",
                "Synthetic relation A",
                "100",
                "150",
                "200",
                "EUR",
                "94",
                "legal_review_required=true;synthetic=test_fixture",
            ],
        ],
    )


def _gazette_viagere_csv(tmp_path: Path) -> Path:
    return _write_synthetic_csv(
        tmp_path / "gazette_viagere.csv",
        header=[
            "row_type",
            "mortality_table",
            "sex",
            "age",
            "interest_rate_pct",
            "coefficient",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "fr_capitalisation_viagere_per_age_sex_rate_coefficient",
                "SYNTH-TABLE",
                "F",
                "0",
                "-1.00",
                "1.234",
                "5",
                "synthetic=test_fixture",
            ],
            [
                "fr_capitalisation_viagere_per_age_sex_rate_coefficient",
                "SYNTH-TABLE",
                "M",
                "0",
                "-1.00",
                "1.500",
                "5",
                "synthetic=test_fixture",
            ],
        ],
    )


# ---------------------------------------------------------------------------
# 1, 2 — DRAFT datasets created with expected row counts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_creates_two_draft_datasets_with_expected_counts(fr_legal_sources, tmp_path):
    from apps.compensation.models import (
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )

    out = StringIO()
    call_command(
        "import_france_candidate_datasets",
        "--mornet-dfp",
        str(_mornet_dfp_csv(tmp_path)),
        "--mornet-affection",
        str(_mornet_affection_csv(tmp_path)),
        "--gazette-viagere",
        str(_gazette_viagere_csv(tmp_path)),
        stdout=out,
    )

    mornet = CompensationDataset.objects.get(version_label="FR-MORNET-2024-DRAFT")
    gazette = CompensationDataset.objects.get(version_label="FR-GAZETTE-PALAIS-2022-DRAFT")
    assert mornet.status == DatasetStatus.DRAFT
    assert gazette.status == DatasetStatus.DRAFT
    assert mornet.is_usable_for_calculations is False
    assert gazette.is_usable_for_calculations is False

    # Row counts: 2 DFP + 1 Affection in Mornet; 2 Viagere in Gazette.
    assert (
        CompensationTableRow.objects.filter(
            dataset=mornet,
            row_type="fr_dfp_per_age_disability_amount_per_point",
        ).count()
        == 2
    )
    assert (
        CompensationTableRow.objects.filter(
            dataset=mornet,
            row_type="fr_prejudice_affection_per_relation_amount",
        ).count()
        == 1
    )
    assert (
        CompensationTableRow.objects.filter(
            dataset=gazette,
            row_type="fr_capitalisation_viagere_per_age_sex_rate_coefficient",
        ).count()
        == 2
    )

    # Source flags carried into ``extra``.
    sample = CompensationTableRow.objects.filter(
        dataset=mornet, row_type="fr_dfp_per_age_disability_amount_per_point"
    ).first()
    assert sample.extra["source_flags"]["legal_review_required"] is True
    assert sample.extra["source_flags"]["no_human_legal_approval"] is True


# ---------------------------------------------------------------------------
# 3 — idempotent re-run via update_or_create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_is_idempotent_on_rerun(fr_legal_sources, tmp_path):
    from apps.compensation.models import CompensationDataset, CompensationTableRow

    csv1 = _mornet_dfp_csv(tmp_path)
    out1 = StringIO()
    call_command("import_france_candidate_datasets", "--mornet-dfp", str(csv1), stdout=out1)
    mornet = CompensationDataset.objects.get(version_label="FR-MORNET-2024-DRAFT")
    first = CompensationTableRow.objects.filter(dataset=mornet).count()

    out2 = StringIO()
    call_command("import_france_candidate_datasets", "--mornet-dfp", str(csv1), stdout=out2)
    second = CompensationTableRow.objects.filter(dataset=mornet).count()
    assert first == second == 2, (first, second)

    # Bump amounts in the same CSV — same natural key, just different
    # values: rows must be UPDATED, not duplicated.
    csv1.write_text(
        csv1.read_text().replace("999,999,999", "1001,1002,1003"),
        encoding="utf-8",
    )
    out3 = StringIO()
    call_command("import_france_candidate_datasets", "--mornet-dfp", str(csv1), stdout=out3)
    third = CompensationTableRow.objects.filter(dataset=mornet).count()
    assert third == 2, third
    updated = CompensationTableRow.objects.filter(
        dataset=mornet,
        age_min=0,
        age_max=10,
        disability_min=1,
        disability_max=5,
    ).first()
    assert updated.extra["amount_min"] == "1001"


# ---------------------------------------------------------------------------
# 4 — refuses to write into a non-DRAFT dataset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_refuses_non_draft_dataset(fr_legal_sources, tmp_path):
    """Operator promoted the dataset by hand → command must abort."""
    from apps.compensation.models import CompensationDataset, DatasetStatus

    # First run creates the dataset in DRAFT.
    call_command(
        "import_france_candidate_datasets",
        "--mornet-dfp",
        str(_mornet_dfp_csv(tmp_path)),
        stdout=StringIO(),
    )
    ds = CompensationDataset.objects.get(version_label="FR-MORNET-2024-DRAFT")
    # Manually promote to needs_review (any status != DRAFT triggers refusal).
    ds.status = DatasetStatus.NEEDS_REVIEW
    ds.save(update_fields=["status"])

    with pytest.raises(CommandError, match="non-DRAFT dataset"):
        call_command(
            "import_france_candidate_datasets",
            "--mornet-dfp",
            str(_mornet_dfp_csv(tmp_path)),
            stdout=StringIO(),
        )


# ---------------------------------------------------------------------------
# 5 — non-whitelist row_type is skipped
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_skips_non_whitelist_row_type(fr_legal_sources, tmp_path):
    from apps.compensation.models import CompensationTableRow, ExtractionLog

    bad = _write_synthetic_csv(
        tmp_path / "mornet_bad.csv",
        header=[
            "row_type",
            "victim_age_min",
            "victim_age_max",
            "disability_min",
            "disability_max",
            "amount_min",
            "amount_mid",
            "amount_max",
            "currency",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "fr_completely_unknown_row_type",
                "0",
                "10",
                "1",
                "5",
                "1",
                "1",
                "1",
                "EUR",
                "71",
                "synthetic=test_fixture",
            ]
        ],
    )

    call_command("import_france_candidate_datasets", "--mornet-dfp", str(bad), stdout=StringIO())
    assert (
        CompensationTableRow.objects.filter(row_type="fr_completely_unknown_row_type").count() == 0
    )
    log = ExtractionLog.objects.filter(file_path__endswith="mornet_bad.csv").latest("created_at")
    assert log.rows_imported == 0
    assert log.rows_skipped == 1
    assert "not in whitelist" in log.error_message


# ---------------------------------------------------------------------------
# 6 — empty amount/coefficient is skipped
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_skips_rows_with_empty_amount_or_coefficient(fr_legal_sources, tmp_path):
    from apps.compensation.models import CompensationTableRow, ExtractionLog

    csv_path = _write_synthetic_csv(
        tmp_path / "viagere_empty.csv",
        header=[
            "row_type",
            "mortality_table",
            "sex",
            "age",
            "interest_rate_pct",
            "coefficient",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "fr_capitalisation_viagere_per_age_sex_rate_coefficient",
                "SYNTH-TABLE",
                "F",
                "0",
                "-1.00",
                "",  # empty coefficient
                "5",
                "synthetic=test_fixture",
            ],
        ],
    )

    call_command(
        "import_france_candidate_datasets",
        "--gazette-viagere",
        str(csv_path),
        stdout=StringIO(),
    )
    assert (
        CompensationTableRow.objects.filter(
            row_type="fr_capitalisation_viagere_per_age_sex_rate_coefficient"
        ).count()
        == 0
    )
    log = ExtractionLog.objects.filter(file_path__endswith="viagere_empty.csv").latest("created_at")
    assert log.rows_skipped == 1
    assert "coefficient must be present" in log.error_message


# ---------------------------------------------------------------------------
# 7 — static guard: the command source has no destructive deletes
# ---------------------------------------------------------------------------


def test_command_source_has_no_destructive_delete():
    """The iter forbids destructive deletes. A plain ``.delete()`` call
    on QuerySets or model instances would silently wipe rows on re-runs;
    we guard against that via static inspection of the committed source.
    """
    src = COMMAND_FILE.read_text(encoding="utf-8")
    # No "QuerySet.delete()" or instance ``.delete()`` call on
    # CompensationTableRow / CompensationDataset / LegalSource.
    forbidden_patterns = [
        r"CompensationTableRow\.objects[^\n]*\.delete\(",
        r"CompensationDataset\.objects[^\n]*\.delete\(",
        r"LegalSource\.objects[^\n]*\.delete\(",
        r"\.objects\.all\(\)\.delete\(",
        r"\.raw\(",
    ]
    for pat in forbidden_patterns:
        assert (
            re.search(pat, src) is None
        ), f"Forbidden pattern {pat!r} appears in import_france_candidate_datasets.py"


# ---------------------------------------------------------------------------
# 8 — LegalSource.status not changed by import
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_does_not_promote_legal_source(fr_legal_sources, tmp_path):
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalSource

    call_command(
        "import_france_candidate_datasets",
        "--mornet-dfp",
        str(_mornet_dfp_csv(tmp_path)),
        "--gazette-viagere",
        str(_gazette_viagere_csv(tmp_path)),
        stdout=StringIO(),
    )
    mornet = LegalSource.objects.get(slug="fr-referentiel-mornet-2024")
    gazette = LegalSource.objects.get(slug="fr-bareme-capitalisation-gazette-palais-2022")
    assert mornet.status == SourceStatus.NEEDS_REVIEW
    assert gazette.status == SourceStatus.NEEDS_REVIEW
    assert mornet.legal_reviewer_id is None
    assert gazette.legal_reviewer_id is None


# ---------------------------------------------------------------------------
# 9 — no CalculationFormula created for FR
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_does_not_create_calculation_formula(fr_legal_sources, tmp_path):
    from apps.compensation.models import CalculationFormula

    formula_before = CalculationFormula.objects.count()

    call_command(
        "import_france_candidate_datasets",
        "--mornet-dfp",
        str(_mornet_dfp_csv(tmp_path)),
        "--mornet-affection",
        str(_mornet_affection_csv(tmp_path)),
        "--gazette-viagere",
        str(_gazette_viagere_csv(tmp_path)),
        stdout=StringIO(),
    )
    assert CalculationFormula.objects.count() == formula_before
    assert CalculationFormula.objects.filter(dataset__country__code="FR").count() == 0


# ---------------------------------------------------------------------------
# 10 — FR calculator stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_calculator_unavailable_after_import(fr_legal_sources, tmp_path):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    call_command(
        "import_france_candidate_datasets",
        "--mornet-dfp",
        str(_mornet_dfp_csv(tmp_path)),
        "--gazette-viagere",
        str(_gazette_viagere_csv(tmp_path)),
        stdout=StringIO(),
    )
    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 11 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_fr_import(db):
    from datetime import date

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    french = Language.objects.create(code="fr", name="Français")
    Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    LegalSource.objects.create(
        slug="fr-referentiel-mornet-2024",
        title="Mornet fixture",
        country=france,
        language=french,
        source_type=SourceType.DOCTRINE,
        reliability=Reliability.MEDIUM,
        status=SourceStatus.NEEDS_REVIEW,
    )
    LegalSource.objects.create(
        slug="fr-bareme-capitalisation-gazette-palais-2022",
        title="Gazette fixture",
        country=france,
        language=french,
        source_type=SourceType.DOCTRINE,
        reliability=Reliability.MEDIUM,
        status=SourceStatus.NEEDS_REVIEW,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-fr-import-fixture",
        title="D.P.R. 12/2025",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )
    base_ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=base_ds,
        row_type="tun_biological_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    moral_ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    for kind, amount in (("min", "26268"), ("mid", "27353"), ("max", "28439")):
        CompensationTableRow.objects.create(
            dataset=moral_ds,
            row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=35,
            age_max=35,
            disability_min=10,
            disability_max=10,
            point_value=Decimal(amount),
        )
    CalculationFormula.objects.create(
        dataset=base_ds,
        code="italy_art_138_tun_2025_fr_import",
        name="fr-import-smoke",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct",
            "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            "min_row_type": "tun_biological_moral_min_total_amount",
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        },
        status=DatasetStatus.APPROVED,
    )
    return {"country": italy}


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_fr_import(italy_smoke_fr_import, tmp_path):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    call_command(
        "import_france_candidate_datasets",
        "--mornet-dfp",
        str(_mornet_dfp_csv(tmp_path)),
        "--gazette-viagere",
        str(_gazette_viagere_csv(tmp_path)),
        stdout=StringIO(),
    )

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("26268")
    assert sim.estimated_mid == Decimal("27353")
    assert sim.estimated_max == Decimal("28439")
