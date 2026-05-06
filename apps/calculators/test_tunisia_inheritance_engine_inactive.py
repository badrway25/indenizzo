"""Tests F-tunisia-inheritance-engine-inactive-fixture-only.

Twin of ``test_morocco_inheritance_engine_inactive.py``: cover the
scaffold + fixture-only behaviour of the Tunisia inheritance
calculator. Three rules:

1. **Synthetic share specs only.** Test fixtures use a synthetic
   share spec that matches a canonical CSP-style allocation but is
   not exhaustive. No CSP article numbers appear as numeric thresholds
   and no Loi 98-97 article is cited as a value; only generic
   institute names (spouse, mother, sons, daughters) are used.
2. **Public DB stays unavailable.** A separate test confirms that
   running the TN calculator against the live (non-test) DB still
   yields ``unavailable_requires_legal_validation`` because no TN
   ``LegalSource`` is ``APPROVED`` and no TN ``CalculationFormula``
   is ``APPROVED``.
3. **Italia smoke unchanged.** Even with TN fixtures seeded in the
   same test DB, Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR
   remains.

The tests exercise the full gating chain: missing dataset, draft
dataset, missing formula, unknown rule, missing heirs, invalid
estate_value, structurally invalid share spec (negative residual),
no-residual-heirs (residual stays explicit, no invented allocation),
and the happy paths (with and without ``estate_value``).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

# Synthetic share spec used as the canonical TN fixture. The shape
# matches a classic CSP-style allocation (spouse 1/8, mother 1/6,
# sons:daughters 2:1 on the residual) without being a complete
# codification.
SYNTH_SHARES = {
    "spouse": "1/8",
    "mother": "1/6",
    "sons_group": "remainder_2_to_1",
    "daughters_group": "remainder_2_to_1",
}
SYNTH_ESTATE = Decimal("1200000")
EXPECTED_SPOUSE_AMOUNT = Decimal("150000")  # 1200000 × 1/8
EXPECTED_MOTHER_AMOUNT = Decimal("200000")  # 1200000 × 1/6


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


@pytest.fixture
def tn_jurisdiction(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    tunisia = Country.objects.create(code="TN", code_alpha3="TUN", name="Tunisie")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    arabic = Language.objects.create(code="ar", name="العربية")
    juris = Jurisdiction.objects.create(
        country=tunisia,
        code="TN-NATIONAL",
        name="Tunisie",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": tunisia, "language": arabic, "jurisdiction": juris}


def _seed_tn_source_and_dataset(
    tn_jurisdiction,
    *,
    dataset_status=None,
    slug_suffix="default",
):
    """Seed an APPROVED TN LegalSource + CompensationDataset."""
    from apps.calculators.enums import CaseType
    from apps.compensation.models import CompensationDataset, DatasetStatus
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    tunisia = tn_jurisdiction["country"]
    juris = tn_jurisdiction["jurisdiction"]
    arabic = tn_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug=f"tn-fixture-source-{slug_suffix}",
        title=f"TN fixture (synthetic, approved) — {slug_suffix}",
        country=tunisia,
        jurisdiction=juris,
        language=arabic,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(1956, 8, 13),
    )
    ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=tunisia,
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        name=f"TN CSP fixture ({slug_suffix})",
        version_label=f"TN-FIXTURE-SYNTHETIC-{slug_suffix.upper()}",
        status=dataset_status or DatasetStatus.APPROVED,
        valid_from=date(1956, 8, 13),
    )
    return {"source": src, "dataset": ds}


def _seed_tn_formula(
    handle,
    *,
    formula_engine="tunisia_inheritance_v1",
    formula_amount_rule="tunisia_inheritance_fixed_share_direct",
    shares=None,
):
    from apps.compensation.models import CalculationFormula, DatasetStatus

    ds = handle["dataset"]
    CalculationFormula.objects.create(
        dataset=ds,
        code=f"tunisia_inheritance_fixture_{handle['source'].slug[-12:]}",
        name="TN inheritance fixture (synthetic)",
        expression_text="fixed shares + 2:1 residual",
        source_reference="synthetic test fixture (CSP Livre IX shape)",
        parameters={
            "engine": formula_engine,
            "amount_rule": formula_amount_rule,
            "requires": ["heirs"],
            "shares": shares if shares is not None else SYNTH_SHARES,
        },
        status=DatasetStatus.APPROVED,
    )


# ---------------------------------------------------------------------------
# 1 — happy path with estate_value: spouse 1/8, mother 1/6, sons/daughters 2:1
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_inheritance_happy_path_with_estate(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="happy")
    _seed_tn_formula(handle)
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "TN",
            "heirs": {"spouse": 1, "mother": 1, "sons": 1, "daughters": 1},
            "estate_value": str(SYNTH_ESTATE),
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    # Total allocated = estate_value (the spec covers all classes).
    assert sim.estimated_min == SYNTH_ESTATE
    assert sim.estimated_mid == SYNTH_ESTATE
    assert sim.estimated_max == SYNTH_ESTATE

    breakdown = (sim.output_data or {}).get("breakdown") or []
    spouse_items = [b for b in breakdown if "Surviving spouse" in b["label"]]
    mother_items = [b for b in breakdown if "Mother" in b["label"]]
    sons_items = [b for b in breakdown if "Sons (collective)" in b["label"]]
    daughters_items = [b for b in breakdown if "Daughters (collective)" in b["label"]]
    assert spouse_items
    assert mother_items
    assert sons_items and daughters_items
    assert Decimal(spouse_items[0]["amount_mid"]) == EXPECTED_SPOUSE_AMOUNT
    assert Decimal(mother_items[0]["amount_mid"]) == EXPECTED_MOTHER_AMOUNT
    # Residual = 1 - 1/8 - 1/6 = 17/24. Split 2:1 between one son and
    # one daughter:
    #   sons_group = 17/24 × 2/3 = 17/36
    #   daughters  = 17/24 × 1/3 = 17/72
    sons_amount = Decimal(sons_items[0]["amount_mid"])
    daughters_amount = Decimal(daughters_items[0]["amount_mid"])
    expected_sons = SYNTH_ESTATE * Decimal(17) / Decimal(36)
    expected_daughters = SYNTH_ESTATE * Decimal(17) / Decimal(72)
    assert abs(sons_amount - expected_sons) < Decimal("0.01")
    assert abs(daughters_amount - expected_daughters) < Decimal("0.01")
    total = (
        Decimal(spouse_items[0]["amount_mid"])
        + Decimal(mother_items[0]["amount_mid"])
        + sons_amount
        + daughters_amount
    )
    assert abs(total - SYNTH_ESTATE) < Decimal("0.001")


# ---------------------------------------------------------------------------
# 2 — happy path without estate_value: shares only, no absolute amounts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_inheritance_shares_only_without_estate(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="no-estate")
    _seed_tn_formula(handle)
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "TN",
            "heirs": {"spouse": 1, "mother": 1, "sons": 2, "daughters": 1},
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None
    breakdown = (sim.output_data or {}).get("breakdown") or []
    labels = [b["label"] for b in breakdown]
    assert any("Surviving spouse (1/8)" in lbl for lbl in labels)
    assert any("Mother (1/6)" in lbl for lbl in labels)


# ---------------------------------------------------------------------------
# 3 — missing heirs → insufficient_input
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_inheritance_missing_heirs_insufficient_input(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="missing-heirs")
    _seed_tn_formula(handle)
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"estate_value": "100000"},
    )
    assert sim.status == CalculationStatus.INSUFFICIENT_INPUT.value


# ---------------------------------------------------------------------------
# 4 — invalid estate_value (negative) → insufficient_input
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_inheritance_negative_estate_insufficient_input(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="neg-estate")
    _seed_tn_formula(handle)
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "heirs": {"spouse": 1, "mother": 1, "sons": 1, "daughters": 1},
            "estate_value": "-1000",
        },
    )
    assert sim.status == CalculationStatus.INSUFFICIENT_INPUT.value


# ---------------------------------------------------------------------------
# 5 — no APPROVED source → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_engine_unavailable_when_no_source(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"heirs": {"spouse": 1, "sons": 1}},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


# ---------------------------------------------------------------------------
# 6 — DRAFT dataset → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_engine_unavailable_when_dataset_draft(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation
    from apps.compensation.models import DatasetStatus

    handle = _seed_tn_source_and_dataset(
        tn_jurisdiction, slug_suffix="draft", dataset_status=DatasetStatus.DRAFT
    )
    _ = handle
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"heirs": {"spouse": 1, "sons": 1}},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_dataset_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 7 — APPROVED dataset, no formula → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_engine_unavailable_when_no_formula(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="no-formula")
    _ = handle
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"heirs": {"spouse": 1, "sons": 1}},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "calculation_formula_approved" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 8 — unknown rule → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_engine_unavailable_when_amount_rule_unknown(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="bad-rule")
    _seed_tn_formula(handle, formula_amount_rule="row_amount_direct")
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={"heirs": {"spouse": 1, "sons": 1}},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_amount_rule_not_inheritance_share" in (sim.output_data or {}).get(
        "missing_documents", []
    )


# ---------------------------------------------------------------------------
# 9 — structurally invalid share spec (sum > 1) → unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_engine_unavailable_when_share_spec_invalid(tn_jurisdiction):
    """When the formula's fixed-fraction shares sum > 1, the TN engine
    refuses to compute. Real Tunisian inheritance applies 'awl
    (proportional reduction) here, but the scaffold rule does not, so
    the engine must surface the misconfiguration rather than mask it."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="bad-spec")
    # 2/3 + 1/2 = 7/6 > 1 → invalid spec.
    _seed_tn_formula(
        handle,
        shares={"spouse": "2/3", "mother": "1/2"},
    )
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "TN",
            "heirs": {"spouse": 1, "mother": 1},
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "shares_spec_invalid" in (sim.output_data or {}).get("missing_documents", [])


# ---------------------------------------------------------------------------
# 10 — no residual heirs leaves residual explicit, no invented allocation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_inheritance_no_residual_heirs_residual_explicit(tn_jurisdiction):
    """When fixed shares allocate < 1 and no class is wired to
    ``remainder_2_to_1`` (or residual classes have zero head_count),
    the residual is reported verbatim as a warning. The rule does not
    invent an allocation; ``radd`` belongs to a future iter."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="no-residual")
    _seed_tn_formula(handle)
    # Spouse + mother only, no sons/daughters → residual 17/24 of the
    # estate is unallocated.
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "TN",
            "heirs": {"spouse": 1, "mother": 1, "sons": 0, "daughters": 0},
            "estate_value": str(SYNTH_ESTATE),
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    breakdown = (sim.output_data or {}).get("breakdown") or []
    sons_items = [b for b in breakdown if "Sons (collective)" in b["label"]]
    daughters_items = [b for b in breakdown if "Daughters (collective)" in b["label"]]
    assert not sons_items
    assert not daughters_items
    warnings = (sim.output_data or {}).get("warnings", [])
    assert any("residual fraction of 17/24" in w for w in warnings)
    # Total allocated < estate (only fixed shares applied).
    assert sim.estimated_mid is not None
    assert sim.estimated_mid < SYNTH_ESTATE


# ---------------------------------------------------------------------------
# 11 — public DB stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=True)
def test_tn_engine_public_db_stays_unavailable():
    """No TN LegalSource is APPROVED in this transactional test DB
    (mirrors the real public DB). The calculator falls back to the
    placeholder unavailable response."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "heirs": {"spouse": 1, "mother": 1, "sons": 1, "daughters": 1},
            "estate_value": str(SYNTH_ESTATE),
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 12 — public_status TN stays at International inheritance review
# ---------------------------------------------------------------------------


def test_tn_public_status_unchanged():
    from apps.core.public_status import (
        STATUS_INHERITANCE_REVIEW,
        get_country_public_status,
    )

    ps = get_country_public_status("TN", "international_inheritance")
    assert ps.status_key == STATUS_INHERITANCE_REVIEW
    assert ps.is_calculation_available is False


# ---------------------------------------------------------------------------
# 13 — Italia 35/10/0 stays unchanged with TN fixture seeded in test DB
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_tn_engine(db, tn_jurisdiction):
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
        slug="it-fixture-tn-engine",
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
        code="italy_art_138_tun_2025_tn_engine_smoke",
        name="tn-engine-smoke",
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
    handle = _seed_tn_source_and_dataset(tn_jurisdiction, slug_suffix="coexist")
    _seed_tn_formula(handle)
    return {"italy": italy}


@pytest.mark.django_db
def test_italy_smoke_unchanged_with_tn_fixture(italy_smoke_tn_engine):
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
