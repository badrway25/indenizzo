"""
Tests F-italy-moral-range-engine — `row_amount_range_direct` rule and
calculator integration.

REGOLA D'ORO: nessun valore TUN reale nei test. I `Decimal` qui sono
SEGNAPOSTO sintattici (es. 100, 200, 300 EUR) che permettono di validare
la meccanica del range engine senza riprodurre la fonte legale.

Cosa verifichiamo:
- la regola produce 3 amounts distinti per la stessa (age, disability);
- fault_reduction si applica uniformemente ai 3 amounts;
- ogni row mancante porta a `unavailable` con missing_document specifico;
- monotonicity violata (min > mid o mid > max) → `unavailable`;
- dataset moral DRAFT NON viene letto dal calculator pubblico;
- la regola single-row `row_amount_direct` continua a dare min=mid=max.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.calculators.enums import CalculationStatus, CaseType
from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
)
from apps.compensation.services import (
    RANGE_AMOUNT_RULES,
    SUPPORTED_AMOUNT_RULES,
    RangeAmounts,
    apply_amount_range_rule,
    find_matching_row_by_type,
    get_approved_dataset_by_version_label,
    is_range_rule,
)
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource

# ---------------------------------------------------------------------------
# Pure unit tests on the rule (no DB)
# ---------------------------------------------------------------------------


def _row(point_value):
    """Lightweight stub: anything with a `.point_value` attribute is enough
    for `_rule_row_amount_range_direct` (it only reads that field)."""

    class _Stub:
        pass

    s = _Stub()
    s.point_value = Decimal(point_value)
    return s


def test_range_registered_as_supported_rule():
    assert "row_amount_range_direct" in SUPPORTED_AMOUNT_RULES
    assert "row_amount_range_direct" in RANGE_AMOUNT_RULES


def test_is_range_rule_predicate():
    assert is_range_rule("row_amount_range_direct") is True
    # Non-range rules return False — backward-compat path stays untouched.
    assert is_range_rule("row_amount_direct") is False
    assert is_range_rule("point_value_times_disability_percentage") is False
    assert is_range_rule("nonexistent_rule") is False


def test_range_rule_returns_three_distinct_amounts():
    out = apply_amount_range_rule(
        "row_amount_range_direct",
        row_min=_row("100"),
        row_mid=_row("200"),
        row_max=_row("300"),
        input_data={},
        fault_reduction_enabled=False,
    )
    assert isinstance(out, RangeAmounts)
    assert out.min_amount == Decimal("100")
    assert out.mid_amount == Decimal("200")
    assert out.max_amount == Decimal("300")
    assert out.is_monotone()


def test_range_rule_fault_50_halves_uniformly():
    out = apply_amount_range_rule(
        "row_amount_range_direct",
        row_min=_row("100"),
        row_mid=_row("200"),
        row_max=_row("300"),
        input_data={"fault_percentage": 50},
        fault_reduction_enabled=True,
    )
    assert out.min_amount == Decimal("50")
    assert out.mid_amount == Decimal("100")
    assert out.max_amount == Decimal("150")


def test_range_rule_fault_disabled_ignores_fault_percentage():
    """`fault_reduction_enabled=False` ⇒ fault_percentage non viene applicato."""
    out = apply_amount_range_rule(
        "row_amount_range_direct",
        row_min=_row("100"),
        row_mid=_row("200"),
        row_max=_row("300"),
        input_data={"fault_percentage": 50},
        fault_reduction_enabled=False,
    )
    assert out.min_amount == Decimal("100")
    assert out.mid_amount == Decimal("200")
    assert out.max_amount == Decimal("300")


def test_range_rule_unknown_raises():
    with pytest.raises(ValueError, match="Unsupported range amount_rule"):
        apply_amount_range_rule(
            "made_up_rule",
            row_min=_row("1"),
            row_mid=_row("2"),
            row_max=_row("3"),
            input_data={},
            fault_reduction_enabled=False,
        )


def test_range_amounts_is_monotone_detects_violation():
    # mid < min
    bad = RangeAmounts(
        min_amount=Decimal("200"), mid_amount=Decimal("100"), max_amount=Decimal("300")
    )
    assert bad.is_monotone() is False
    # mid > max
    bad2 = RangeAmounts(
        min_amount=Decimal("100"), mid_amount=Decimal("400"), max_amount=Decimal("300")
    )
    assert bad2.is_monotone() is False
    # equal is OK (degenerate range still monotone)
    eq = RangeAmounts(
        min_amount=Decimal("100"), mid_amount=Decimal("100"), max_amount=Decimal("100")
    )
    assert eq.is_monotone() is True


# ---------------------------------------------------------------------------
# DB fixtures — base (approved) + moral (draft by default)
# ---------------------------------------------------------------------------


@pytest.fixture
def italy(db) -> Country:
    return Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")


@pytest.fixture
def italy_jurisdiction(italy: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


@pytest.fixture
def italian(db) -> Language:
    return Language.objects.create(code="it", name="Italiano")


@pytest.fixture
def approved_source(italy, italy_jurisdiction, italian) -> LegalSource:
    return LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title="D.P.R. 12/2025 (test stub)",
        country=italy,
        jurisdiction=italy_jurisdiction,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )


@pytest.fixture
def base_dataset_approved(approved_source) -> CompensationDataset:
    """Tabella 1 stub APPROVED with one fixture row (1 EUR)."""
    ds = CompensationDataset.objects.create(
        source=approved_source,
        jurisdiction=approved_source.jurisdiction,
        country=approved_source.country,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base (test)",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=ds,
        row_type="tun_biological_total_amount",
        age_min=0,
        age_max=0,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    return ds


def _make_moral_dataset(
    source: LegalSource, *, status: str, with_rows: bool = True
) -> CompensationDataset:
    ds = CompensationDataset.objects.create(
        source=source,
        jurisdiction=source.jurisdiction,
        country=source.country,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral (test)",
        version_label="DPR-12-2025-MORAL",
        status=status,
        valid_from=date(2025, 1, 13),
    )
    if with_rows:
        # 3 row_type per (age=0, inv=10), placeholder values.
        CompensationTableRow.objects.create(
            dataset=ds,
            row_type="tun_biological_moral_min_total_amount",
            age_min=0,
            age_max=0,
            disability_min=10,
            disability_max=10,
            point_value=Decimal("100"),
        )
        CompensationTableRow.objects.create(
            dataset=ds,
            row_type="tun_biological_moral_mid_total_amount",
            age_min=0,
            age_max=0,
            disability_min=10,
            disability_max=10,
            point_value=Decimal("200"),
        )
        CompensationTableRow.objects.create(
            dataset=ds,
            row_type="tun_biological_moral_max_total_amount",
            age_min=0,
            age_max=0,
            disability_min=10,
            disability_max=10,
            point_value=Decimal("300"),
        )
    return ds


# ---------------------------------------------------------------------------
# DB tests on resolvers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_approved_dataset_by_version_label_filters_draft(approved_source):
    """Il dataset DRAFT non viene mai restituito al calculator pubblico."""
    _make_moral_dataset(approved_source, status=DatasetStatus.DRAFT)
    got = get_approved_dataset_by_version_label(
        source=approved_source,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        version_label="DPR-12-2025-MORAL",
    )
    assert got is None


@pytest.mark.django_db
def test_get_approved_dataset_by_version_label_returns_approved(approved_source):
    moral = _make_moral_dataset(approved_source, status=DatasetStatus.APPROVED)
    got = get_approved_dataset_by_version_label(
        source=approved_source,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        version_label="DPR-12-2025-MORAL",
    )
    assert got is not None
    assert got.pk == moral.pk


@pytest.mark.django_db
def test_find_matching_row_by_type_filters_by_row_type(approved_source):
    moral = _make_moral_dataset(approved_source, status=DatasetStatus.APPROVED)
    out = find_matching_row_by_type(
        moral,
        row_type="tun_biological_moral_mid_total_amount",
        row_match_fields=["victim_age", "permanent_disability_percentage"],
        input_data={"victim_age": 0, "permanent_disability_percentage": 10},
    )
    assert out.row is not None
    assert out.row.row_type == "tun_biological_moral_mid_total_amount"
    assert out.row.point_value == Decimal("200")


# ---------------------------------------------------------------------------
# Calculator integration — moral dataset DRAFT vs APPROVED
# ---------------------------------------------------------------------------


def _make_range_formula(dataset: CompensationDataset) -> CalculationFormula:
    """Approved formula with range parameters, attached to the BASE dataset."""
    return CalculationFormula.objects.create(
        dataset=dataset,
        code="italy_art_138_tun_2025_base",
        name="Stub range formula",
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


@pytest.mark.django_db
def test_calculator_refuses_draft_moral_dataset(base_dataset_approved, approved_source):
    """Il calculator pubblico NON usa un moral DRAFT — restituisce unavailable."""
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    _make_moral_dataset(approved_source, status=DatasetStatus.DRAFT)
    _make_range_formula(base_dataset_approved)

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute({"victim_age": 0, "permanent_disability_percentage": 10})

    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "range_dataset_approved" in r.missing_documents


@pytest.mark.django_db
def test_calculator_uses_approved_moral_dataset(base_dataset_approved, approved_source):
    """Quando il moral è APPROVED, il calcolo restituisce 3 valori distinti."""
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    _make_moral_dataset(approved_source, status=DatasetStatus.APPROVED)
    _make_range_formula(base_dataset_approved)

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute({"victim_age": 0, "permanent_disability_percentage": 10})

    assert r.status == CalculationStatus.CALCULATED.value
    assert r.estimated_min == Decimal("100")
    assert r.estimated_mid == Decimal("200")
    assert r.estimated_max == Decimal("300")


@pytest.mark.django_db
def test_calculator_range_applies_fault_reduction(base_dataset_approved, approved_source):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    _make_moral_dataset(approved_source, status=DatasetStatus.APPROVED)
    _make_range_formula(base_dataset_approved)

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute(
        {"victim_age": 0, "permanent_disability_percentage": 10, "fault_percentage": 50}
    )

    assert r.status == CalculationStatus.CALCULATED.value
    assert r.estimated_min == Decimal("50")
    assert r.estimated_mid == Decimal("100")
    assert r.estimated_max == Decimal("150")


@pytest.mark.django_db
def test_calculator_unavailable_when_min_row_missing(base_dataset_approved, approved_source):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    moral = _make_moral_dataset(approved_source, status=DatasetStatus.APPROVED)
    moral.rows.filter(row_type="tun_biological_moral_min_total_amount").delete()
    _make_range_formula(base_dataset_approved)

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute({"victim_age": 0, "permanent_disability_percentage": 10})

    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_row_match" in r.missing_documents


@pytest.mark.django_db
def test_calculator_unavailable_when_mid_row_missing(base_dataset_approved, approved_source):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    moral = _make_moral_dataset(approved_source, status=DatasetStatus.APPROVED)
    moral.rows.filter(row_type="tun_biological_moral_mid_total_amount").delete()
    _make_range_formula(base_dataset_approved)

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute({"victim_age": 0, "permanent_disability_percentage": 10})

    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_row_match" in r.missing_documents


@pytest.mark.django_db
def test_calculator_unavailable_when_max_row_missing(base_dataset_approved, approved_source):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    moral = _make_moral_dataset(approved_source, status=DatasetStatus.APPROVED)
    moral.rows.filter(row_type="tun_biological_moral_max_total_amount").delete()
    _make_range_formula(base_dataset_approved)

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute({"victim_age": 0, "permanent_disability_percentage": 10})

    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_row_match" in r.missing_documents


@pytest.mark.django_db
def test_calculator_unavailable_when_range_non_monotone(base_dataset_approved, approved_source):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    # Build a moral dataset where mid < min (corrupted).
    moral = CompensationDataset.objects.create(
        source=approved_source,
        jurisdiction=approved_source.jurisdiction,
        country=approved_source.country,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral (corrupted test)",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=moral,
        row_type="tun_biological_moral_min_total_amount",
        age_min=0,
        age_max=0,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("500"),
    )
    CompensationTableRow.objects.create(
        dataset=moral,
        row_type="tun_biological_moral_mid_total_amount",
        age_min=0,
        age_max=0,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("100"),  # < min — VIOLA monotonicità
    )
    CompensationTableRow.objects.create(
        dataset=moral,
        row_type="tun_biological_moral_max_total_amount",
        age_min=0,
        age_max=0,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("300"),
    )
    _make_range_formula(base_dataset_approved)

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute({"victim_age": 0, "permanent_disability_percentage": 10})

    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_range_inconsistent" in r.missing_documents


@pytest.mark.django_db
def test_calculator_unavailable_when_range_parameters_incomplete(
    base_dataset_approved, approved_source
):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    _make_moral_dataset(approved_source, status=DatasetStatus.APPROVED)
    # Formula approvata ma con parameters range INCOMPLETI (manca min_row_type)
    CalculationFormula.objects.create(
        dataset=base_dataset_approved,
        code="italy_art_138_tun_2025_base",
        name="Incomplete range formula",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct",
            "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            # MANCA min_row_type
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        },
        status=DatasetStatus.APPROVED,
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute({"victim_age": 0, "permanent_disability_percentage": 10})

    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_range_parameters_incomplete" in r.missing_documents


# ---------------------------------------------------------------------------
# Backward-compat: row_amount_direct continua a produrre min == mid == max.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_single_row_rule_still_produces_equal_amounts(base_dataset_approved):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    # NESSUN moral dataset creato. Formula tradizionale row_amount_direct.
    CalculationFormula.objects.create(
        dataset=base_dataset_approved,
        code="italy_art_138_tun_2025_base",
        name="Single-row formula",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_direct",
            "fault_reduction": True,
        },
        status=DatasetStatus.APPROVED,
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    r = calc.compute({"victim_age": 0, "permanent_disability_percentage": 10})

    assert r.status == CalculationStatus.CALCULATED.value
    # Fixture point_value=1 — verifichiamo solo che min == mid == max,
    # non il valore (regola d'oro: nessun reale TUN nei test).
    assert r.estimated_min == r.estimated_mid == r.estimated_max
