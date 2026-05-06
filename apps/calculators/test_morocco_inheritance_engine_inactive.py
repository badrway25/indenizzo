"""Tests F-morocco-inheritance-engine-inactive-fixture-only.

Cover the scaffold + fixture-only behaviour of the Morocco inheritance
calculator. Three rules of these tests:

1. **Synthetic share specs only.** Test fixtures use a synthetic
   share spec (spouse 1/8, sons/daughters 2:1 on the residual) that
   matches one canonical Moudawana shape but is not exhaustive. No
   real Moudawana article numbers appear as numeric thresholds; only
   institute names (spouse, father, mother, sons, daughters) are
   used.
2. **Public DB stays unavailable.** A separate test confirms that
   running the MA calculator against the live (non-test) DB still
   yields ``unavailable_requires_legal_validation`` because no MA
   ``LegalSource`` is ``APPROVED`` and no MA ``CalculationFormula``
   is ``APPROVED``.
3. **Italia smoke unchanged.** Even with MA fixtures seeded in the
   same test DB, Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR
   remains.

The tests exercise the gating chain: missing dataset, draft dataset,
missing formula, unknown rule, missing heirs, invalid estate_value,
and finally the happy paths (with and without ``estate_value``).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

# Synthetic share spec used as the canonical MA fixture. The shape
# matches a classic faraïd allocation (spouse 1/8, sons:daughters 2:1
# on the residual) without being a complete codification.
SYNTH_SHARES = {
    "spouse": "1/8",
    "sons_group": "remainder_2_to_1",
    "daughters_group": "remainder_2_to_1",
}
SYNTH_ESTATE = Decimal("800000")
EXPECTED_SPOUSE_AMOUNT = Decimal("100000")  # 800000 × 1/8


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


@pytest.fixture
def ma_jurisdiction(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    morocco = Country.objects.create(code="MA", code_alpha3="MAR", name="Maroc")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=morocco,
        code="MA-NATIONAL",
        name="Maroc",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": morocco, "language": french, "jurisdiction": juris}


def _seed_ma_source_and_dataset(
    ma_jurisdiction,
    *,
    dataset_status=None,
    slug_suffix="default",
):
    """Seed an APPROVED MA LegalSource + CompensationDataset."""
    from apps.calculators.enums import CaseType
    from apps.compensation.models import CompensationDataset, DatasetStatus
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    morocco = ma_jurisdiction["country"]
    juris = ma_jurisdiction["jurisdiction"]
    french = ma_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug=f"ma-fixture-source-{slug_suffix}",
        title=f"MA fixture (synthetic, approved) — {slug_suffix}",
        country=morocco,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2004, 2, 5),
    )
    ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=morocco,
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        name=f"MA Moudawana fixture ({slug_suffix})",
        version_label=f"MA-FIXTURE-SYNTHETIC-{slug_suffix.upper()}",
        status=dataset_status or DatasetStatus.APPROVED,
        valid_from=date(2004, 2, 5),
    )
    return {"source": src, "dataset": ds}


def _seed_ma_formula(
    handle,
    *,
    formula_engine="morocco_inheritance_v1",
    formula_amount_rule="morocco_inheritance_fixed_share_direct",
    shares=None,
):
    from apps.compensation.models import CalculationFormula, DatasetStatus

    ds = handle["dataset"]
    CalculationFormula.objects.create(
        dataset=ds,
        code=f"morocco_inheritance_fixture_{handle['source'].slug[-12:]}",
        name="MA inheritance fixture (synthetic)",
        expression_text="fixed shares + 2:1 residual",
        source_reference="synthetic test fixture (Moudawana Livre III shape)",
        parameters={
            "engine": formula_engine,
            "amount_rule": formula_amount_rule,
            "requires": ["heirs"],
            "shares": shares if shares is not None else SYNTH_SHARES,
        },
        status=DatasetStatus.APPROVED,
    )


# ---------------------------------------------------------------------------
# 1 — happy path with estate_value: spouse 1/8, sons/daughters 2:1
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_inheritance_happy_path_with_estate(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="happy")
    _seed_ma_formula(handle)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": str(SYNTH_ESTATE),
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    # Total allocated = estate_value (the spec covers all classes).
    assert sim.estimated_min == SYNTH_ESTATE
    assert sim.estimated_mid == SYNTH_ESTATE
    assert sim.estimated_max == SYNTH_ESTATE

    # Per-heir breakdown lives in output_data.
    breakdown = (sim.output_data or {}).get("breakdown") or []
    spouse_items = [b for b in breakdown if "Surviving spouse" in b["label"]]
    assert spouse_items
    assert Decimal(spouse_items[0]["amount_mid"]) == EXPECTED_SPOUSE_AMOUNT
    sons_items = [b for b in breakdown if "Sons (collective)" in b["label"]]
    daughters_items = [b for b in breakdown if "Daughters (collective)" in b["label"]]
    assert sons_items and daughters_items
    # 7/8 split 2:1 between one son and one daughter:
    #   sons_group = 7/8 × 2/3 = 7/12   = 466666.67 (approx)
    #   daughters  = 7/8 × 1/3 = 7/24   = 233333.33 (approx)
    sons_amount = Decimal(sons_items[0]["amount_mid"])
    daughters_amount = Decimal(daughters_items[0]["amount_mid"])
    expected_sons = SYNTH_ESTATE * Decimal(7) / Decimal(12)
    expected_daughters = SYNTH_ESTATE * Decimal(7) / Decimal(24)
    assert abs(sons_amount - expected_sons) < Decimal("0.01")
    assert abs(daughters_amount - expected_daughters) < Decimal("0.01")
    # The three amounts add up to the estate.
    total = sons_amount + daughters_amount + Decimal(spouse_items[0]["amount_mid"])
    assert abs(total - SYNTH_ESTATE) < Decimal("0.001")


# ---------------------------------------------------------------------------
# 2 — happy path without estate_value: shares only, no absolute amounts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_inheritance_shares_only_without_estate(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="no-estate")
    _seed_ma_formula(handle)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "heirs": {"spouse": 1, "sons": 2, "daughters": 1},
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None
    # Breakdown is still present with fractional notes.
    breakdown = (sim.output_data or {}).get("breakdown") or []
    labels = [b["label"] for b in breakdown]
    assert any("Surviving spouse (1/8)" in lbl for lbl in labels)


# ---------------------------------------------------------------------------
# 3 — missing heirs → insufficient_input
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_inheritance_missing_heirs_insufficient_input(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="missing-heirs")
    _seed_ma_formula(handle)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"estate_value": "100000"},  # no heirs provided
    )
    assert sim.status == CalculationStatus.INSUFFICIENT_INPUT.value


# ---------------------------------------------------------------------------
# 4 — invalid estate_value (negative) → insufficient_input
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_inheritance_negative_estate_insufficient_input(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="neg-estate")
    _seed_ma_formula(handle)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "-1000",
        },
    )
    assert sim.status == CalculationStatus.INSUFFICIENT_INPUT.value


# ---------------------------------------------------------------------------
# 5 — no APPROVED source → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_engine_unavailable_when_no_source(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    # No LegalSource seeded at all.
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"heirs": {"spouse": 1, "sons": 1}},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


# ---------------------------------------------------------------------------
# 6 — DRAFT dataset → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_engine_unavailable_when_dataset_draft(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation
    from apps.compensation.models import DatasetStatus

    handle = _seed_ma_source_and_dataset(
        ma_jurisdiction, slug_suffix="draft", dataset_status=DatasetStatus.DRAFT
    )
    _ = handle
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"heirs": {"spouse": 1, "sons": 1}},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_dataset_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 7 — APPROVED dataset, no formula → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_engine_unavailable_when_no_formula(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="no-formula")
    _ = handle  # source + dataset only, no formula
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"heirs": {"spouse": 1, "sons": 1}},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "calculation_formula_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 8 — unknown rule → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_engine_unavailable_when_amount_rule_unknown(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="bad-rule")
    # row_amount_direct is supported globally but is NOT an
    # inheritance-share rule. The MA engine refuses it.
    _seed_ma_formula(handle, formula_amount_rule="row_amount_direct")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"heirs": {"spouse": 1, "sons": 1}},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_amount_rule_not_inheritance_share" in (sim.output_data or {}).get(
        "missing_documents", []
    )


# ---------------------------------------------------------------------------
# 9 — public DB stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_ma_engine_public_db_stays_unavailable():
    """No MA LegalSource is APPROVED in this transactional test DB
    (mirrors the real public DB). The calculator falls back to the
    placeholder unavailable response."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": str(SYNTH_ESTATE),
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 10 — public_status MA stays at International inheritance review
# ---------------------------------------------------------------------------


def test_ma_public_status_unchanged():
    from apps.core.public_status import (
        STATUS_INHERITANCE_REVIEW,
        get_country_public_status,
    )

    ps = get_country_public_status("MA", "international_inheritance")
    assert ps.status_key == STATUS_INHERITANCE_REVIEW
    assert ps.is_calculation_available is False


# ---------------------------------------------------------------------------
# 11 — Italia 35/10/0 stays unchanged with MA fixture seeded in test DB
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_ma_engine(db, ma_jurisdiction):
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
        slug="it-fixture-ma-engine",
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
        code="italy_art_138_tun_2025_ma_engine_smoke",
        name="ma-engine-smoke",
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
    # Seed MA fixture too, so both engines coexist.
    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="coexist")
    _seed_ma_formula(handle)
    return {"italy": italy}


@pytest.mark.django_db
def test_italy_smoke_unchanged_with_ma_fixture(italy_smoke_ma_engine):
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
# 12 — daughters_only edge case: 1/8 spouse + remainder split entirely to daughters
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_inheritance_daughters_only_edge_case(ma_jurisdiction):
    """When only daughters survive (no sons), the residual goes
    entirely to ``daughters_group``. Sanity-check that the 2:1 ratio
    degenerates safely and the breakdown still adds up."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="daughters-only")
    _seed_ma_formula(handle)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "heirs": {"spouse": 1, "sons": 0, "daughters": 2},
            "estate_value": "240000",
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    breakdown = (sim.output_data or {}).get("breakdown") or []
    spouse_items = [b for b in breakdown if "Surviving spouse" in b["label"]]
    daughters_items = [b for b in breakdown if "Daughters (collective)" in b["label"]]
    sons_items = [b for b in breakdown if "Sons (collective)" in b["label"]]
    assert spouse_items
    assert daughters_items
    assert not sons_items  # zero sons → no sons_group line
    spouse_amount = Decimal(spouse_items[0]["amount_mid"])
    daughters_amount = Decimal(daughters_items[0]["amount_mid"])
    # spouse = 1/8 × 240000 = 30000; daughters = 7/8 × 240000 = 210000
    assert spouse_amount == Decimal("30000")
    assert daughters_amount == Decimal("210000")
