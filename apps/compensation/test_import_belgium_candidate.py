"""Tests F-belgium-import-candidate-datasets-draft-seed.

Cover the new ``import_belgium_candidate_datasets`` management command:

1. The DRAFT dataset is created on first run.
2. Mini-fixture CSVs (synthetic values, NOT real Tableau Indicatif
   numbers) import the expected row counts per row_type.
3. A re-run is idempotent: same input + same dataset → same row count,
   no duplicates, only updates.
4. The command refuses to write into a dataset that already exists with
   a status != DRAFT.
5. Rows whose ``row_type`` is not in the whitelist are skipped.
6. Rows with empty / null / negative amounts are skipped.
7. Static check: the command source has no destructive
   ``delete()`` / ``raw()`` calls.
8. The import does not change ``LegalSource.status`` (stays
   ``needs_review``).
9. The import does not create any ``CalculationFormula`` for BE.
10. ``run_simulation(BE-NATIONAL, road_accident_bodily_injury)`` stays
    ``unavailable_requires_legal_validation`` after import.
11. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR resta invariata.
12. No banned public wording introduced on the BE wizard / landing.

Test fixtures use synthetic numeric values (e.g. amount=999, daily=42)
so this file never accidentally serves as a "second source of truth"
for the real BE Tableau Indicatif.
"""

from __future__ import annotations

import re
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND_FILE = (
    REPO_ROOT
    / "apps"
    / "compensation"
    / "management"
    / "commands"
    / "import_belgium_candidate_datasets.py"
)


# ---------------------------------------------------------------------------
# Fixtures: minimal synthetic CSVs (not real BE values).
# ---------------------------------------------------------------------------


@pytest.fixture
def be_legal_source(db):
    """Pre-seed the BE LegalSource the command resolves by slug."""
    from datetime import date

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    belgium = Country.objects.create(code="BE", code_alpha3="BEL", name="Belgique")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=belgium,
        code="BE-NATIONAL",
        name="Belgique",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="be-tableau-indicatif-2020",
        title="BE Tableau Indicatif 2020 — fixture",
        country=belgium,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.DOCTRINE,
        reliability=Reliability.MEDIUM,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2020, 1, 1),
    )
    return {"country": belgium, "jurisdiction": juris, "source": src}


def _write_synthetic_csv(path: Path, header: list[str], rows: list[list[str]]) -> Path:
    path.write_text(
        ",".join(header) + "\n" + "\n".join(",".join(r) for r in rows) + "\n",
        encoding="utf-8",
    )
    return path


def _souffrances_csv(tmp_path: Path) -> Path:
    return _write_synthetic_csv(
        tmp_path / "souffrances.csv",
        header=[
            "row_type",
            "severity_code",
            "severity_label_fr",
            "victim_age_min",
            "victim_age_max",
            "amount_min",
            "amount_mid",
            "amount_max",
            "currency",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "be_souffrances_endurees_per_age_severity_amount",
                "1_7",
                "synthetic-minime",
                "0",
                "10",
                "999",
                "999",
                "999",
                "EUR",
                "17",
                "legal_review_required=true;no_human_legal_approval=true;synthetic=test_fixture",
            ],
            [
                "be_souffrances_endurees_per_age_severity_amount",
                "2_7",
                "synthetic-tres-leger",
                "0",
                "10",
                "888",
                "888",
                "888",
                "EUR",
                "17",
                "legal_review_required=true;no_human_legal_approval=true;synthetic=test_fixture",
            ],
        ],
    )


def _forfait_csv(tmp_path: Path) -> Path:
    return _write_synthetic_csv(
        tmp_path / "forfait.csv",
        header=[
            "row_type",
            "severity_code",
            "severity_label_fr",
            "victim_age_min",
            "victim_age_max",
            "annual_amount",
            "currency",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "be_indemnite_forfaitaire_per_age_annual_amount",
                "default",
                "default (no severity scale)",
                "0",
                "15",
                "1234",
                "EUR",
                "22",
                "legal_review_required=true;synthetic=test_fixture",
            ],
        ],
    )


def _deces_csv(tmp_path: Path) -> Path:
    return _write_synthetic_csv(
        tmp_path / "deces.csv",
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
                "be_prejudice_deces_affection_per_relation_amount",
                "synthetic_relation_a",
                "Synthetic relation A",
                "100",
                "150",
                "200",
                "EUR",
                "26",
                "legal_review_required=true;synthetic=test_fixture",
            ],
        ],
    )


def _vehicule_csv(tmp_path: Path) -> Path:
    return _write_synthetic_csv(
        tmp_path / "vehicule.csv",
        header=[
            "row_type",
            "vehicle_type_code",
            "vehicle_type_label_fr",
            "daily_amount_min",
            "daily_amount_mid",
            "daily_amount_max",
            "currency",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "be_vehicule_remplacement_per_type_per_day_amount",
                "fr_synthetic_type_x",
                "Synthetic vehicle type X",
                "42",
                "42",
                "42",
                "EUR",
                "32",
                "legal_review_required=true;synthetic=test_fixture",
            ],
        ],
    )


# ---------------------------------------------------------------------------
# 1, 2 — DRAFT dataset created with expected row counts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_creates_draft_dataset_with_expected_counts(be_legal_source, tmp_path):
    from apps.compensation.models import (
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )

    out = StringIO()
    call_command(
        "import_belgium_candidate_datasets",
        "--souffrances",
        str(_souffrances_csv(tmp_path)),
        "--forfait",
        str(_forfait_csv(tmp_path)),
        "--deces",
        str(_deces_csv(tmp_path)),
        "--vehicule",
        str(_vehicule_csv(tmp_path)),
        stdout=out,
    )

    ds = CompensationDataset.objects.get(version_label="BE-TABLEAU-INDICATIF-2020-DRAFT")
    assert ds.status == DatasetStatus.DRAFT
    assert ds.is_usable_for_calculations is False

    # Row counts: 2 souffrances + 1 forfait + 1 deces + 1 vehicule = 5.
    assert (
        CompensationTableRow.objects.filter(
            dataset=ds, row_type="be_souffrances_endurees_per_age_severity_amount"
        ).count()
        == 2
    )
    assert (
        CompensationTableRow.objects.filter(
            dataset=ds, row_type="be_indemnite_forfaitaire_per_age_annual_amount"
        ).count()
        == 1
    )
    assert (
        CompensationTableRow.objects.filter(
            dataset=ds, row_type="be_prejudice_deces_affection_per_relation_amount"
        ).count()
        == 1
    )
    assert (
        CompensationTableRow.objects.filter(
            dataset=ds, row_type="be_vehicule_remplacement_per_type_per_day_amount"
        ).count()
        == 1
    )

    # Source flags carried into ``extra``.
    sample = CompensationTableRow.objects.filter(
        dataset=ds, row_type="be_souffrances_endurees_per_age_severity_amount"
    ).first()
    assert sample.extra["source_flags"]["legal_review_required"] is True
    assert sample.extra["source_flags"]["no_human_legal_approval"] is True


# ---------------------------------------------------------------------------
# 3 — idempotent re-run via update_or_create
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_is_idempotent_on_rerun(be_legal_source, tmp_path):
    from apps.compensation.models import CompensationDataset, CompensationTableRow

    csv1 = _souffrances_csv(tmp_path)
    out1 = StringIO()
    call_command("import_belgium_candidate_datasets", "--souffrances", str(csv1), stdout=out1)
    ds = CompensationDataset.objects.get(version_label="BE-TABLEAU-INDICATIF-2020-DRAFT")
    first = CompensationTableRow.objects.filter(dataset=ds).count()

    out2 = StringIO()
    call_command("import_belgium_candidate_datasets", "--souffrances", str(csv1), stdout=out2)
    second = CompensationTableRow.objects.filter(dataset=ds).count()
    assert first == second == 2, (first, second)

    # Same natural key, different value: rows must be UPDATED, not duplicated.
    csv1.write_text(
        csv1.read_text().replace("999,999,999", "1001,1002,1003"),
        encoding="utf-8",
    )
    out3 = StringIO()
    call_command("import_belgium_candidate_datasets", "--souffrances", str(csv1), stdout=out3)
    third = CompensationTableRow.objects.filter(dataset=ds).count()
    assert third == 2, third
    updated = CompensationTableRow.objects.filter(dataset=ds, extra__severity_code="1_7").first()
    assert updated.extra["amount_min"] == "1001"


# ---------------------------------------------------------------------------
# 4 — refuses to write into a non-DRAFT dataset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_refuses_non_draft_dataset(be_legal_source, tmp_path):
    """Operator promoted the dataset by hand → command must abort."""
    from apps.compensation.models import CompensationDataset, DatasetStatus

    call_command(
        "import_belgium_candidate_datasets",
        "--souffrances",
        str(_souffrances_csv(tmp_path)),
        stdout=StringIO(),
    )
    ds = CompensationDataset.objects.get(version_label="BE-TABLEAU-INDICATIF-2020-DRAFT")
    ds.status = DatasetStatus.NEEDS_REVIEW
    ds.save(update_fields=["status"])

    with pytest.raises(CommandError, match="non-DRAFT dataset"):
        call_command(
            "import_belgium_candidate_datasets",
            "--souffrances",
            str(_souffrances_csv(tmp_path)),
            stdout=StringIO(),
        )


# ---------------------------------------------------------------------------
# 5 — non-whitelist row_type is skipped
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_skips_non_whitelist_row_type(be_legal_source, tmp_path):
    from apps.compensation.models import CompensationTableRow, ExtractionLog

    bad = _write_synthetic_csv(
        tmp_path / "souffrances_bad.csv",
        header=[
            "row_type",
            "severity_code",
            "severity_label_fr",
            "victim_age_min",
            "victim_age_max",
            "amount_min",
            "amount_mid",
            "amount_max",
            "currency",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "be_completely_unknown_row_type",
                "1_7",
                "x",
                "0",
                "10",
                "1",
                "1",
                "1",
                "EUR",
                "17",
                "synthetic=test_fixture",
            ],
        ],
    )

    call_command("import_belgium_candidate_datasets", "--souffrances", str(bad), stdout=StringIO())
    assert (
        CompensationTableRow.objects.filter(row_type="be_completely_unknown_row_type").count() == 0
    )
    log = ExtractionLog.objects.filter(file_path__endswith="souffrances_bad.csv").latest(
        "created_at"
    )
    assert log.rows_imported == 0
    assert log.rows_skipped == 1
    assert "not in whitelist" in log.error_message


# ---------------------------------------------------------------------------
# 6 — empty / negative amounts are skipped
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_skips_rows_with_empty_or_negative_amounts(be_legal_source, tmp_path):
    from apps.compensation.models import CompensationTableRow, ExtractionLog

    csv_path = _write_synthetic_csv(
        tmp_path / "souffrances_bad_amount.csv",
        header=[
            "row_type",
            "severity_code",
            "severity_label_fr",
            "victim_age_min",
            "victim_age_max",
            "amount_min",
            "amount_mid",
            "amount_max",
            "currency",
            "source_page",
            "source_note",
        ],
        rows=[
            [
                "be_souffrances_endurees_per_age_severity_amount",
                "1_7",
                "x-empty",
                "0",
                "10",
                "",  # empty amount_min
                "",
                "",
                "EUR",
                "17",
                "synthetic=test_fixture",
            ],
            [
                "be_souffrances_endurees_per_age_severity_amount",
                "2_7",
                "x-negative",
                "0",
                "10",
                "-1",  # negative
                "-1",
                "-1",
                "EUR",
                "17",
                "synthetic=test_fixture",
            ],
        ],
    )

    call_command(
        "import_belgium_candidate_datasets",
        "--souffrances",
        str(csv_path),
        stdout=StringIO(),
    )
    assert (
        CompensationTableRow.objects.filter(
            row_type="be_souffrances_endurees_per_age_severity_amount"
        ).count()
        == 0
    )
    log = ExtractionLog.objects.filter(file_path__endswith="souffrances_bad_amount.csv").latest(
        "created_at"
    )
    assert log.rows_skipped == 2
    assert ("must all be present" in log.error_message) or ("non-negative" in log.error_message)


# ---------------------------------------------------------------------------
# 7 — static guard: the command source has no destructive deletes
# ---------------------------------------------------------------------------


def test_command_source_has_no_destructive_delete():
    """The iter forbids destructive deletes. Static check guards
    against any silent ``.delete()`` / ``raw()`` introduction."""
    src = COMMAND_FILE.read_text(encoding="utf-8")
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
        ), f"Forbidden pattern {pat!r} appears in import_belgium_candidate_datasets.py"


# ---------------------------------------------------------------------------
# 8 — LegalSource.status not changed by import
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_does_not_promote_legal_source(be_legal_source, tmp_path):
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalSource

    call_command(
        "import_belgium_candidate_datasets",
        "--souffrances",
        str(_souffrances_csv(tmp_path)),
        "--forfait",
        str(_forfait_csv(tmp_path)),
        "--deces",
        str(_deces_csv(tmp_path)),
        "--vehicule",
        str(_vehicule_csv(tmp_path)),
        stdout=StringIO(),
    )
    src = LegalSource.objects.get(slug="be-tableau-indicatif-2020")
    assert src.status == SourceStatus.NEEDS_REVIEW
    assert src.legal_reviewer_id is None


# ---------------------------------------------------------------------------
# 9 — no CalculationFormula created for BE
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_import_does_not_create_calculation_formula(be_legal_source, tmp_path):
    from apps.compensation.models import CalculationFormula

    formula_before = CalculationFormula.objects.count()

    call_command(
        "import_belgium_candidate_datasets",
        "--souffrances",
        str(_souffrances_csv(tmp_path)),
        "--forfait",
        str(_forfait_csv(tmp_path)),
        "--deces",
        str(_deces_csv(tmp_path)),
        "--vehicule",
        str(_vehicule_csv(tmp_path)),
        stdout=StringIO(),
    )
    assert CalculationFormula.objects.count() == formula_before
    assert CalculationFormula.objects.filter(dataset__country__code="BE").count() == 0


# ---------------------------------------------------------------------------
# 10 — BE calculator stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_calculator_unavailable_after_import(be_legal_source, tmp_path):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    call_command(
        "import_belgium_candidate_datasets",
        "--souffrances",
        str(_souffrances_csv(tmp_path)),
        "--vehicule",
        str(_vehicule_csv(tmp_path)),
        stdout=StringIO(),
    )
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
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
def italy_smoke_be_import(db):
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
    belgium = Country.objects.create(code="BE", code_alpha3="BEL", name="Belgique")
    french = Language.objects.create(code="fr", name="Français")
    Jurisdiction.objects.create(
        country=belgium,
        code="BE-NATIONAL",
        name="Belgique",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    LegalSource.objects.create(
        slug="be-tableau-indicatif-2020",
        title="BE Tableau Indicatif 2020 fixture",
        country=belgium,
        language=french,
        source_type=SourceType.DOCTRINE,
        reliability=Reliability.MEDIUM,
        status=SourceStatus.NEEDS_REVIEW,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-be-import-fixture",
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
        code="italy_art_138_tun_2025_be_import",
        name="be-import-smoke",
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
def test_italy_smoke_unchanged_after_be_import(italy_smoke_be_import, tmp_path):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    call_command(
        "import_belgium_candidate_datasets",
        "--souffrances",
        str(_souffrances_csv(tmp_path)),
        "--vehicule",
        str(_vehicule_csv(tmp_path)),
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


# ---------------------------------------------------------------------------
# 12 — no banned public wording on BE wizard / landing
# ---------------------------------------------------------------------------


BANNED_WORDS = (
    "scaffold",
    "placeholder",
    "under validation",
    "in preparation",
    "coming soon",
    "work in progress",
    "in corso",
    "modulo non operativo",
    "legal validation wizard",
    "module pending",
    "engine pending",
    "missing_documents",
    "unavailable_requires_legal_validation",
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/wizard/be/road-accident/",
        "/countries/belgium/",
    ],
)
def test_be_public_pages_have_no_banned_words_after_import(path):
    """The BE wizard / landing must not regress to banned wording.
    The import command does not touch templates, but a defensive
    end-to-end check guards against future drift."""
    body = Client().get(path).content.decode("utf-8", errors="replace").lower()
    # Strip script/style + tags before lower-casing for a body-text view.
    visible = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", body, flags=re.DOTALL)
    visible = re.sub(r"<[^>]+>", " ", visible)
    for word in BANNED_WORDS:
        assert word not in visible, f"{path}: banned word {word!r} surfaced"
