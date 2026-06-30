"""Canary tests for the official art. 139 micropermanenti engine (P8).

Every numeric value comes from approved DB rows (the 9 progression coefficients,
the first-point value €963.40, the ITT daily €56.18 — D.M. MIMIT 18/07/2025).
The formula (art. 139 co.1/co.6) is asserted to the cent so the engine can never
silently drift, exactly like the TUN smoke. Nothing is hardcoded in the engine.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.calculators.enums import CalculationStatus, CaseType

# Official art. 139 comma-6 coefficients (owner-approved).
_COEFF = {1: "1.0", 2: "1.1", 3: "1.2", 4: "1.3", 5: "1.5", 6: "1.7", 7: "1.9", 8: "2.1", 9: "2.3"}
_PRIMO_PUNTO = Decimal("963.40")
_ITT_DAILY = Decimal("56.18")


@pytest.fixture
def italy_micro_stack(db):
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy, code="IT-NATIONAL", name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur, default_language=italian,
    )
    # micro source + dataset (approved)
    micro_src = LegalSource.objects.create(
        slug="it-art139-cap-micropermanenti", title="art. 139 CAP + D.M. MIMIT 2025",
        country=italy, jurisdiction=juris, language=italian,
        source_type=SourceType.MINISTRY_DECREE, status=SourceStatus.APPROVED,
        publication_date=date(2025, 7, 31), effective_date=date(2025, 4, 1),
    )
    micro_ds = CompensationDataset.objects.create(
        source=micro_src, source_version=approved_source_version(micro_src),
        jurisdiction=juris, country=italy,
        case_type=CaseType.ROAD_ACCIDENT_MICROLESIONS.value,
        name="Microlesioni art. 139 (D.M. MIMIT 2025)", version_label="ART139-MIMIT-2025",
        status=DatasetStatus.APPROVED, valid_from=date(2025, 4, 1),
    )
    for p, c in _COEFF.items():
        CompensationTableRow.objects.create(
            dataset=micro_ds, row_type="disability_coefficient",
            disability_min=p, disability_max=p, coefficient=Decimal(c),
        )
    CompensationTableRow.objects.create(
        dataset=micro_ds, row_type="first_point_value", point_value=_PRIMO_PUNTO)
    CompensationTableRow.objects.create(
        dataset=micro_ds, row_type="itt_daily_absolute", daily_amount=_ITT_DAILY)

    # TUN base + moral (approved) — so medical >=10% can reuse the existing engine
    tun_src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico", title="D.P.R. 12/2025 TUN",
        country=italy, jurisdiction=juris, language=italian,
        source_type=SourceType.MINISTRY_DECREE, status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11), effective_date=date(2025, 1, 13),
    )
    base_ds = CompensationDataset.objects.create(
        source=tun_src, source_version=approved_source_version(tun_src),
        jurisdiction=juris, country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base", version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED, valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=base_ds, row_type="tun_biological_total_amount",
        age_min=35, age_max=35, disability_min=10, disability_max=10, point_value=Decimal("1"))
    moral_ds = CompensationDataset.objects.create(
        source=tun_src, source_version=approved_source_version(tun_src),
        jurisdiction=juris, country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral", version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED, valid_from=date(2025, 1, 13))
    for kind, amount in (("min", "26268"), ("mid", "27353"), ("max", "28439")):
        CompensationTableRow.objects.create(
            dataset=moral_ds, row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=35, age_max=35, disability_min=10, disability_max=10, point_value=Decimal(amount))
    CalculationFormula.objects.create(
        dataset=base_ds, code="italy_art_138_tun_2025_base", name="range",
        expression_text="x", source_reference="x", status=DatasetStatus.APPROVED,
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct", "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            "min_row_type": "tun_biological_moral_min_total_amount",
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        },
    )
    return {"country": italy}


def _sim(pct, age, itt_abs=0, case_type=None):
    from apps.cases.services import run_simulation
    return run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=case_type or CaseType.ROAD_ACCIDENT_MICROLESIONS.value,
        input_data={
            "victim_age": age,
            "permanent_disability_percentage": pct,
            "total_temporary_disability_days": itt_abs,
        },
    )


@pytest.mark.django_db
@pytest.mark.parametrize("pct,age,expected", [
    (1, 35, "842.98"),     # 963.40 × 1.0 × 1 × 0.875
    (9, 35, "17449.58"),   # 963.40 × 2.3 × 9 × 0.875
    (5, 35, "6322.31"),    # 963.40 × 1.5 × 5 × 0.875
    (1, 10, "963.40"),     # age 10 → no reduction
    (1, 11, "958.58"),     # age 11 → ×0.995
])
def test_micro_permanent_canary(italy_micro_stack, pct, age, expected):
    sim = _sim(pct, age)
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == sim.estimated_mid == sim.estimated_max == Decimal(expected)


@pytest.mark.django_db
def test_micro_with_itt(italy_micro_stack):
    sim = _sim(1, 35, itt_abs=30)  # 842.98 + 30 × 56.18 = 2528.38
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_mid == Decimal("2528.38")


@pytest.mark.django_db
def test_micro_provenance_required(italy_micro_stack):
    sim = _sim(9, 35)
    prov = sim.calculation_provenance
    assert prov and prov.get("engine") == "italy_art139_micro_v1"
    assert prov.get("table_rows")


@pytest.mark.django_db
@pytest.mark.parametrize("pct", [0, 10, 100])
def test_micro_fail_closed_outside_1_9(italy_micro_stack, pct):
    """0% and >=10% are NOT micro: the micro engine never invents a number."""
    sim = _sim(pct, 35)
    assert sim.status != CalculationStatus.CALCULATED.value
    assert sim.estimated_min is None


@pytest.mark.django_db
def test_medical_5pct_uses_art139(italy_micro_stack):
    sim = _sim(5, 35, case_type=CaseType.MEDICAL_LIABILITY_BIOLOGICAL.value)
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_mid == Decimal("6322.31")  # same as road micro 5%


@pytest.mark.django_db
def test_medical_10pct_uses_tun(italy_micro_stack):
    sim = _sim(10, 35, case_type=CaseType.MEDICAL_LIABILITY_BIOLOGICAL.value)
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("26268")
    assert sim.estimated_max == Decimal("28439")


@pytest.mark.django_db
def test_tun_canary_unchanged(italy_micro_stack):
    """The existing TUN 35/10/0 path is untouched by the micro engine."""
    sim = _sim(10, 35, case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert sim.estimated_min == Decimal("26268")
    assert sim.estimated_mid == Decimal("27353")
    assert sim.estimated_max == Decimal("28439")
