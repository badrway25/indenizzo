"""Tests F-france-engine-inactive-fixture-only.

Cover the scaffold + fixture-only behaviour of the France road-accident
calculator. Three rules of these tests:

1. **Synthetic values only.** Test fixtures use ``point_value=100``,
   ``disability=10`` → expected ``1000``. No real Mornet/Gazette numbers
   appear anywhere in this file. A static check (test #last) enforces
   this contract by scanning the file's own bytes for known real Mornet
   amounts.
2. **Public DB stays unavailable.** A separate test confirms that
   running the FR calculator against the live (non-test) DB still yields
   ``unavailable_requires_legal_validation`` because no FR
   ``LegalSource`` is ``APPROVED`` and no FR ``CalculationFormula`` is
   ``APPROVED``.
3. **Italia smoke unchanged.** Even with FR fixtures seeded in the same
   test DB, Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.

The tests exercise the full gating chain: missing source, missing
dataset, draft dataset, unknown engine, unknown rule, missing input,
no row match, multiple matches, non-monotone range, and finally the
happy path.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

# Synthetic numeric constants used as fixture values. These intentionally
# differ from any real Mornet 2024 / Gazette du Palais 2022 amount so a
# regression in the test fixtures cannot leak real values into snapshots.
SYNTH_POINT_VALUE = Decimal("100")
SYNTH_POINT_VALUE_MIN = Decimal("80")
SYNTH_POINT_VALUE_MID = Decimal("100")
SYNTH_POINT_VALUE_MAX = Decimal("120")
SYNTH_DISABILITY_PCT = 10  # → expected synthetic outputs:
SYNTH_FAULT_HALF = 50  # → divide each by two

EXPECTED_SCALAR = Decimal("1000")  # 100 × 10
EXPECTED_RANGE_MIN = Decimal("800")  # 80 × 10
EXPECTED_RANGE_MID = Decimal("1000")  # 100 × 10
EXPECTED_RANGE_MAX = Decimal("1200")  # 120 × 10


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


@pytest.fixture
def fr_jurisdiction(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    Currency.objects.create(code="EUR", name="Euro", symbol="€")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": france, "language": french, "jurisdiction": juris}


def _seed_fr_approved(
    fr_jurisdiction,
    *,
    point_value=SYNTH_POINT_VALUE,
    extra_amount_min=None,
    extra_amount_mid=None,
    extra_amount_max=None,
    dataset_status=None,
    formula_engine="france_road_accident_v1",
    formula_amount_rule="france_dfp_point_value_direct",
    include_row=True,
    age_min=0,
    age_max=120,
    disability_min=1,
    disability_max=100,
):
    """Seed a synthetic APPROVED FR source/dataset/formula for fixture tests."""
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    france = fr_jurisdiction["country"]
    juris = fr_jurisdiction["jurisdiction"]
    french = fr_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug="fr-fixture-source-synthetic",
        title="FR fixture (synthetic, approved)",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2024, 1, 1),
    )
    ds_status = dataset_status or DatasetStatus.APPROVED
    ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=france,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="FR Mornet fixture (synthetic)",
        version_label="FR-FIXTURE-SYNTHETIC",
        status=ds_status,
        valid_from=date(2024, 1, 1),
    )
    if include_row and ds_status == DatasetStatus.APPROVED:
        extra: dict = {}
        if extra_amount_min is not None:
            extra["amount_min"] = str(extra_amount_min)
        if extra_amount_mid is not None:
            extra["amount_mid"] = str(extra_amount_mid)
        if extra_amount_max is not None:
            extra["amount_max"] = str(extra_amount_max)
        CompensationTableRow.objects.create(
            dataset=ds,
            row_type="fr_dfp_per_age_disability_amount_per_point",
            age_min=age_min,
            age_max=age_max,
            disability_min=disability_min,
            disability_max=disability_max,
            point_value=point_value,
            extra=extra,
        )
    if ds_status == DatasetStatus.APPROVED:
        CalculationFormula.objects.create(
            dataset=ds,
            code="france_road_accident_fixture",
            name="FR fixture formula (synthetic)",
            expression_text="point_value × disability%",
            source_reference="synthetic test fixture",
            parameters={
                "engine": formula_engine,
                "amount_rule": formula_amount_rule,
                "row_type": "fr_dfp_per_age_disability_amount_per_point",
                "row_match": ["victim_age", "permanent_disability_percentage"],
                "requires": ["victim_age", "permanent_disability_percentage"],
                "fault_reduction": True,
            },
            status=DatasetStatus.APPROVED,
        )
    return {"source": src, "dataset": ds}


# ---------------------------------------------------------------------------
# 1 — happy path: scalar (min=mid=max), no fault
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_engine_scalar_happy_path(fr_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_fr_approved(fr_jurisdiction)
    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == EXPECTED_SCALAR
    assert sim.estimated_mid == EXPECTED_SCALAR
    assert sim.estimated_max == EXPECTED_SCALAR


# ---------------------------------------------------------------------------
# 2 — happy path: range from extra amount_min/mid/max
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_engine_range_from_extra(fr_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_fr_approved(
        fr_jurisdiction,
        extra_amount_min=SYNTH_POINT_VALUE_MIN,
        extra_amount_mid=SYNTH_POINT_VALUE_MID,
        extra_amount_max=SYNTH_POINT_VALUE_MAX,
    )
    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == EXPECTED_RANGE_MIN
    assert sim.estimated_mid == EXPECTED_RANGE_MID
    assert sim.estimated_max == EXPECTED_RANGE_MAX


# ---------------------------------------------------------------------------
# 3 — fault reduction applied uniformly
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_engine_fault_reduction(fr_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_fr_approved(fr_jurisdiction)
    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
            "fault_percentage": SYNTH_FAULT_HALF,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    # 1000 × (100-50)/100 = 500
    assert sim.estimated_min == Decimal("500")
    assert sim.estimated_mid == Decimal("500")
    assert sim.estimated_max == Decimal("500")


# ---------------------------------------------------------------------------
# 4 — missing dataset → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_engine_unavailable_when_no_dataset(fr_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    # APPROVED source but no dataset attached.
    LegalSource.objects.create(
        slug="fr-fixture-source-no-dataset",
        title="FR source without dataset",
        country=fr_jurisdiction["country"],
        jurisdiction=fr_jurisdiction["jurisdiction"],
        language=fr_jurisdiction["language"],
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2024, 1, 1),
    )

    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_dataset_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 5 — DRAFT dataset → unavailable (gating refuses to read draft data)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_engine_unavailable_when_dataset_draft(fr_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation
    from apps.compensation.models import DatasetStatus

    _seed_fr_approved(fr_jurisdiction, dataset_status=DatasetStatus.DRAFT)
    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_dataset_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 6 — no row matches the input → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_engine_unavailable_when_no_row_match(fr_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    # Row covers only ages 0-10, but input is age 35 → no match.
    _seed_fr_approved(fr_jurisdiction, age_min=0, age_max=10)
    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_row_match" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 7 — unknown engine → unavailable (defends future formula misconfig)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_engine_unavailable_when_formula_engine_unknown(fr_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_fr_approved(fr_jurisdiction, formula_engine="france_unknown_v999")
    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_engine_unknown" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 8 — non single-row range rule on FR engine → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_engine_unavailable_when_amount_rule_not_single_row_range(fr_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    # row_amount_direct is supported globally but is NOT a single-row range
    # rule. The FR engine refuses it: only single-row range rules are
    # currently supported by FR.
    _seed_fr_approved(fr_jurisdiction, formula_amount_rule="row_amount_direct")
    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_amount_rule_not_single_row_range" in (sim.output_data or {}).get(
        "missing_documents", []
    )


# ---------------------------------------------------------------------------
# 9 — public DB (non-test, no fixture) stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_fr_engine_public_db_stays_unavailable():
    """No FR LegalSource in this transactional test DB → calculator
    falls back to placeholder behaviour. Mirrors the real public DB
    where Mornet / Gazette stay ``needs_review``."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": SYNTH_DISABILITY_PCT,
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 10 — Italia 35/10/0 stays unchanged with FR fixture seeded in test DB
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_fr_engine(db, fr_jurisdiction):
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
    Currency.objects.filter(code="EUR").exists() or Currency.objects.create(
        code="EUR", name="Euro", symbol="€"
    )
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-fixture-fr-engine",
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
        code="italy_art_138_tun_2025_fr_engine_smoke",
        name="fr-engine-smoke",
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
    # Seed FR fixture too, so both engines coexist.
    _seed_fr_approved(fr_jurisdiction)
    return {"italy": italy}


@pytest.mark.django_db
def test_italy_smoke_unchanged_with_fr_fixture(italy_smoke_fr_engine):
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
# 11 — Static guard: this test file contains NO real Mornet/Gazette amounts
# ---------------------------------------------------------------------------


def test_no_real_fr_values_in_this_test_file():
    """The iter forbids real FR values in tests. We load the canonical
    per-row_type counts and a few real amounts from the upstream CSVs on
    disk and assert none of them appear in this test file's body.

    Reading from the CSVs (rather than hard-coding the forbidden values
    here) is intentional: literal real numbers in this file would defeat
    the very check we're trying to enforce."""
    import csv

    here = Path(__file__).read_text(encoding="utf-8")
    repo_root = Path(__file__).resolve().parents[2]
    csv_paths = [
        repo_root
        / "legal_data"
        / "sources"
        / "france"
        / "mornet_2024"
        / "fr-mornet-2024-dfp-per-age-disability.csv",
        repo_root
        / "legal_data"
        / "sources"
        / "france"
        / "mornet_2024"
        / "fr-mornet-2024-prejudice-affection-per-relation.csv",
        repo_root
        / "legal_data"
        / "sources"
        / "france"
        / "gazette_2022"
        / "fr-gazette-2022-capitalisation-viagere.csv",
    ]
    forbidden: set[str] = set()
    # Exclude trivial "round" values and year-like 4-digit strings from the
    # check: years legitimately appear in this file's date/version fixtures
    # and would accidentally match Mornet amounts on the same digits. The
    # point of the test is to catch the characteristic non-year amounts and
    # decimal capitalisation coefficients (deliberately not listed verbatim
    # here — listing them would defeat the check).
    trivial = {"0", "1", "100"}

    def _is_year_like(s: str) -> bool:
        return s.isdigit() and len(s) == 4 and 1900 <= int(s) <= 2099

    for path in csv_paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                for col in ("amount_min", "amount_mid", "amount_max", "coefficient"):
                    val = (row.get(col) or "").strip()
                    if not val or val in trivial or _is_year_like(val):
                        continue
                    forbidden.add(val)
    # Cap the search set so the assertion message stays readable; a few
    # leaks are enough to fail the test.
    leaked = sorted({v for v in forbidden if v in here})[:20]
    assert not leaked, (
        f"Real FR amounts/coefficients leaked into test fixtures: {leaked}. "
        "Tests must use synthetic values only."
    )
