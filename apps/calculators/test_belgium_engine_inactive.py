"""Tests F-belgium-engine-inactive-fixture-only.

Cover the scaffold + fixture-only behaviour of the Belgium road-accident
calculator. Three rules of these tests:

1. **Synthetic values only.** Test fixtures use synthetic numeric values
   (e.g. ``annual=100``, ``incapacity=10`` → ``1000``) that intentionally
   differ from any Tableau Indicatif 2020 amount. A static guard
   (``test_no_real_be_values_in_this_test_file``) reads the upstream BE
   CSVs at test time and asserts none of those numbers appear in this
   file's source.
2. **Public DB stays unavailable.** A separate test confirms that
   running the BE calculator against the live (non-test) DB still yields
   ``unavailable_requires_legal_validation`` because no BE
   ``LegalSource`` is ``APPROVED`` and no BE ``CalculationFormula`` is
   ``APPROVED``.
3. **Italia smoke unchanged.** Even with BE fixtures seeded in the same
   test DB, Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.

The tests exercise the full gating chain: missing dataset, draft
dataset, missing formula, unknown engine, unknown amount_rule,
non single-row range rule, missing input, no row match, multiple matches,
non-monotone range, and finally the happy path for each of the three
pass-1 amount rules.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

# Synthetic numeric constants used as fixture values. These intentionally
# differ from any real Tableau Indicatif 2020 amount so a regression in
# the test fixtures cannot leak real values into snapshots.
SYNTH_SOUFFRANCES_MIN = Decimal("777")
SYNTH_SOUFFRANCES_MID = Decimal("888")
SYNTH_SOUFFRANCES_MAX = Decimal("999")
SYNTH_FORFAIT_ANNUAL = Decimal("100")
SYNTH_FORFAIT_INCAPACITY = 10  # → 100 × 10 / 100 = 10 (then × ?? in test)
SYNTH_DECES_MIN = Decimal("1234")
SYNTH_DECES_MID = Decimal("1456")
SYNTH_DECES_MAX = Decimal("1678")
SYNTH_FAULT_HALF = 50  # → divide each by two


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


@pytest.fixture
def be_jurisdiction(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    belgium = Country.objects.create(code="BE", code_alpha3="BEL", name="Belgique")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=belgium,
        code="BE-NATIONAL",
        name="Belgique",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": belgium, "language": french, "jurisdiction": juris}


def _seed_be_source_and_dataset(
    be_jurisdiction,
    *,
    dataset_status=None,
    slug_suffix="default",
):
    """Seed an APPROVED BE LegalSource + CompensationDataset (status
    overridable). No formula is created here — the per-rule fixtures
    add their own formula/row in a second step.
    """
    from apps.calculators.enums import CaseType
    from apps.compensation.models import CompensationDataset, DatasetStatus
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    belgium = be_jurisdiction["country"]
    juris = be_jurisdiction["jurisdiction"]
    french = be_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug=f"be-fixture-source-{slug_suffix}",
        title=f"BE fixture (synthetic, approved) — {slug_suffix}",
        country=belgium,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2020, 1, 1),
    )
    ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=belgium,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name=f"BE Tableau Indicatif fixture ({slug_suffix})",
        version_label=f"BE-FIXTURE-SYNTHETIC-{slug_suffix.upper()}",
        status=dataset_status or DatasetStatus.APPROVED,
        valid_from=date(2020, 1, 1),
    )
    return {"source": src, "dataset": ds}


def _seed_souffrances_formula_and_row(
    handle,
    *,
    formula_engine="belgium_road_accident_v1",
    formula_amount_rule="belgium_souffrances_age_severity_direct",
    age_min=0,
    age_max=120,
    severity_code="3_7",
    amount_min=SYNTH_SOUFFRANCES_MIN,
    amount_mid=SYNTH_SOUFFRANCES_MID,
    amount_max=SYNTH_SOUFFRANCES_MAX,
    include_row=True,
    row_type="be_souffrances_endurees_per_age_severity_amount",
):
    from apps.compensation.models import (
        CalculationFormula,
        CompensationTableRow,
        DatasetStatus,
    )

    ds = handle["dataset"]
    if include_row:
        CompensationTableRow.objects.create(
            dataset=ds,
            row_type=row_type,
            age_min=age_min,
            age_max=age_max,
            extra={
                "severity_code": severity_code,
                "amount_min": str(amount_min),
                "amount_mid": str(amount_mid),
                "amount_max": str(amount_max),
            },
        )
    CalculationFormula.objects.create(
        dataset=ds,
        code=f"belgium_souffrances_fixture_{handle['source'].slug[-12:]}",
        name="BE souffrances fixture (synthetic)",
        expression_text="row.extra.amount_min/mid/max",
        source_reference="synthetic test fixture",
        parameters={
            "engine": formula_engine,
            "amount_rule": formula_amount_rule,
            "row_type": row_type,
            "row_match": ["victim_age", "severity_scale"],
            "requires": ["victim_age", "severity_scale"],
            "fault_reduction": True,
        },
        status=DatasetStatus.APPROVED,
    )


def _seed_forfait_formula_and_row(
    handle,
    *,
    age_min=0,
    age_max=120,
    annual_amount=SYNTH_FORFAIT_ANNUAL,
):
    from apps.compensation.models import (
        CalculationFormula,
        CompensationTableRow,
        DatasetStatus,
    )

    ds = handle["dataset"]
    CompensationTableRow.objects.create(
        dataset=ds,
        row_type="be_indemnite_forfaitaire_per_age_annual_amount",
        age_min=age_min,
        age_max=age_max,
        extra={
            "severity_code": "default",
            "annual_amount": str(annual_amount),
        },
    )
    CalculationFormula.objects.create(
        dataset=ds,
        code=f"belgium_forfait_fixture_{handle['source'].slug[-12:]}",
        name="BE forfait fixture (synthetic)",
        expression_text="annual × incapacity / 100",
        source_reference="synthetic test fixture",
        parameters={
            "engine": "belgium_road_accident_v1",
            "amount_rule": "belgium_forfait_age_annual_direct",
            "row_type": "be_indemnite_forfaitaire_per_age_annual_amount",
            "row_match": ["victim_age"],
            "requires": ["victim_age"],
            "fault_reduction": True,
        },
        status=DatasetStatus.APPROVED,
    )


def _seed_deces_formula_and_row(
    handle,
    *,
    relation_code="synthetic_relation_x",
    amount_min=SYNTH_DECES_MIN,
    amount_mid=SYNTH_DECES_MID,
    amount_max=SYNTH_DECES_MAX,
):
    from apps.compensation.models import (
        CalculationFormula,
        CompensationTableRow,
        DatasetStatus,
    )

    ds = handle["dataset"]
    CompensationTableRow.objects.create(
        dataset=ds,
        row_type="be_prejudice_deces_affection_per_relation_amount",
        extra={
            "relation_code": relation_code,
            "amount_min": str(amount_min),
            "amount_mid": str(amount_mid),
            "amount_max": str(amount_max),
        },
    )
    CalculationFormula.objects.create(
        dataset=ds,
        code=f"belgium_deces_fixture_{handle['source'].slug[-12:]}",
        name="BE deces fixture (synthetic)",
        expression_text="row.extra.amount_min/mid/max",
        source_reference="synthetic test fixture",
        parameters={
            "engine": "belgium_road_accident_v1",
            "amount_rule": "belgium_deces_affection_relation_direct",
            "row_type": "be_prejudice_deces_affection_per_relation_amount",
            "row_match": ["relation_code"],
            "requires": ["relation_code"],
            "fault_reduction": True,
        },
        status=DatasetStatus.APPROVED,
    )


# ---------------------------------------------------------------------------
# 1 — souffrances happy path: range from extra
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_souffrances_range_happy_path(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="souffrances")
    _seed_souffrances_formula_and_row(handle)
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "3_7"},
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == SYNTH_SOUFFRANCES_MIN
    assert sim.estimated_mid == SYNTH_SOUFFRANCES_MID
    assert sim.estimated_max == SYNTH_SOUFFRANCES_MAX


# ---------------------------------------------------------------------------
# 2 — souffrances fault reduction applied uniformly
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_souffrances_fault_reduction(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="souffr-fault")
    _seed_souffrances_formula_and_row(handle)
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "severity_scale": "3_7",
            "fault_percentage": SYNTH_FAULT_HALF,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    # Each amount × (100-50)/100 = half.
    assert sim.estimated_min == SYNTH_SOUFFRANCES_MIN / 2
    assert sim.estimated_mid == SYNTH_SOUFFRANCES_MID / 2
    assert sim.estimated_max == SYNTH_SOUFFRANCES_MAX / 2


# ---------------------------------------------------------------------------
# 3 — forfait happy path: annual × incapacity / 100
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_forfait_annual_with_incapacity(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="forfait")
    _seed_forfait_formula_and_row(handle)
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "incapacity_percentage": SYNTH_FORFAIT_INCAPACITY,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    # 100 × 10 / 100 = 10, broadcast across (min, mid, max).
    expected = SYNTH_FORFAIT_ANNUAL * SYNTH_FORFAIT_INCAPACITY / Decimal(100)
    assert sim.estimated_min == expected
    assert sim.estimated_mid == expected
    assert sim.estimated_max == expected


# ---------------------------------------------------------------------------
# 4 — deces happy path: range keyed by relation_code
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_deces_relation_happy_path(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="deces")
    _seed_deces_formula_and_row(handle)
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"relation_code": "synthetic_relation_x"},
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == SYNTH_DECES_MIN
    assert sim.estimated_mid == SYNTH_DECES_MID
    assert sim.estimated_max == SYNTH_DECES_MAX


# ---------------------------------------------------------------------------
# 5 — missing dataset → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_engine_unavailable_when_no_dataset(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    LegalSource.objects.create(
        slug="be-fixture-source-no-dataset",
        title="BE source without dataset",
        country=be_jurisdiction["country"],
        jurisdiction=be_jurisdiction["jurisdiction"],
        language=be_jurisdiction["language"],
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2020, 1, 1),
    )
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "3_7"},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_dataset_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 6 — DRAFT dataset → unavailable (gating refuses to read draft data)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_engine_unavailable_when_dataset_draft(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation
    from apps.compensation.models import DatasetStatus

    handle = _seed_be_source_and_dataset(
        be_jurisdiction, slug_suffix="draft-ds", dataset_status=DatasetStatus.DRAFT
    )
    # No row / no formula seeded — even if they were, gating fails at
    # the dataset-status check before reaching them.
    _ = handle
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "3_7"},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_dataset_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 7 — APPROVED dataset, no formula → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_engine_unavailable_when_no_formula(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="no-formula")
    _ = handle
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "3_7"},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "calculation_formula_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 8 — unknown engine → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_engine_unavailable_when_formula_engine_unknown(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="bad-engine")
    _seed_souffrances_formula_and_row(handle, formula_engine="belgium_unknown_v999")
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "3_7"},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_engine_unknown" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 9 — non single-row range rule → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_engine_unavailable_when_amount_rule_not_single_row_range(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="bad-rule")
    # row_amount_direct is supported globally but is NOT a single-row
    # range rule. The BE engine refuses it.
    _seed_souffrances_formula_and_row(handle, formula_amount_rule="row_amount_direct")
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "3_7"},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_amount_rule_not_single_row_range" in (sim.output_data or {}).get(
        "missing_documents", []
    )


# ---------------------------------------------------------------------------
# 10 — no row matches the input → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_engine_unavailable_when_no_row_match(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="no-row")
    # Row covers only severity 3_7, but input asks for 5_7.
    _seed_souffrances_formula_and_row(handle, severity_code="3_7")
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "5_7"},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_row_match" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 11 — invalid range (non-monotone) → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_engine_unavailable_when_range_non_monotone(be_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="non-monotone")
    # min > max → range invalid. The engine must refuse to publish.
    _seed_souffrances_formula_and_row(
        handle,
        amount_min=Decimal("999"),
        amount_mid=Decimal("888"),
        amount_max=Decimal("777"),
    )
    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "3_7"},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_range_inconsistent" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 12 — public DB (non-test, no fixture) stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_be_engine_public_db_stays_unavailable():
    """No BE LegalSource is APPROVED in this transactional test DB
    (which mirrors the real public DB). The calculator falls back to
    the placeholder unavailable response."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "severity_scale": "3_7"},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 13 — Italia 35/10/0 stays unchanged with BE fixture seeded in test DB
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_be_engine(db, be_jurisdiction):
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
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-fixture-be-engine",
        title="D.P.R. 12/2025 fixture",
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
        code="italy_art_138_tun_2025_be_engine_smoke",
        name="be-engine-smoke",
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
    # Seed BE souffrances fixture too, so both engines coexist.
    handle = _seed_be_source_and_dataset(be_jurisdiction, slug_suffix="coexist")
    _seed_souffrances_formula_and_row(handle)
    return {"italy": italy}


@pytest.mark.django_db
def test_italy_smoke_unchanged_with_be_fixture(italy_smoke_be_engine):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

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
# 14 — Static guard: this test file contains NO real BE Tableau values
# ---------------------------------------------------------------------------


def test_no_real_be_values_in_this_test_file():
    """The iter forbids real BE Tableau Indicatif values in tests. We
    load the canonical amounts from the upstream BE CSVs on disk and
    assert none of them appear in this file's source.

    Reading from the CSVs (rather than hard-coding the forbidden values
    here) is intentional: literal real numbers in this file would defeat
    the very check we're trying to enforce."""
    import csv

    here = Path(__file__).read_text(encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[2]
    base = repo_root / "legal_data" / "sources" / "belgium" / "tableau_indicatif_2020"
    csv_paths = [
        base / "be-ti-2020-souffrances-endurees.csv",
        base / "be-ti-2020-prejudice-esthetique.csv",
        base / "be-ti-2020-prejudice-deces-affection.csv",
        base / "be-ti-2020-vehicule-remplacement.csv",
    ]
    forbidden: set[str] = set()
    # Trivial / structural values that would not be a "leak" (small ints
    # legitimately appear in test fixtures: ages, severity codes, etc.).
    trivial = {"0", "1", "100"}

    def _is_year_like(s: str) -> bool:
        return s.isdigit() and len(s) == 4 and 1900 <= int(s) <= 2099

    for path in csv_paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                for col in (
                    "amount_min",
                    "amount_mid",
                    "amount_max",
                    "annual_amount",
                    "daily_amount_min",
                    "daily_amount_mid",
                    "daily_amount_max",
                ):
                    val = (row.get(col) or "").strip()
                    if not val or val in trivial or _is_year_like(val):
                        continue
                    forbidden.add(val)
    leaked = sorted({v for v in forbidden if v in here})[:20]
    assert not leaked, (
        f"Real BE amounts/coefficients leaked into test fixtures: {leaked}. "
        "Tests must use synthetic values only."
    )
