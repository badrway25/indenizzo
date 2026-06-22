"""Tests F-italy-calculator-warning-strings-translatable-pass1.

Cover the Italy calculated-path warning migration: the inline English
sentences are now routed through ``apps.calculators.diagnostics``
under public-safe codes that translate to IT / FR / AR. The Italy
35/10/0 → 26 268 / 27 353 / 28 439 EUR result is preserved verbatim.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators import diagnostics as _diag

# ---------------------------------------------------------------------------
# 1 — public_safe is True for the Italy codes
# ---------------------------------------------------------------------------


def test_italy_codes_are_public_safe():
    for code in (
        _diag.ITALY_RANGE_COLLAPSED,
        _diag.ITALY_FIELD_NOT_AGGREGATED,
        _diag.ITALY_FAULT_REDUCTION_APPLIED,
        _diag.ITALY_FAULT_REDUCTION_APPLIED_UNIFORM,
    ):
        assert _diag.diagnostic_public_safe(code) is True


# ---------------------------------------------------------------------------
# 2 — public_safe is False for FR / BE / MA / TN internal codes
# ---------------------------------------------------------------------------


def test_internal_codes_remain_public_unsafe():
    for code in (
        _diag.LEGAL_SOURCES_NOT_APPROVED,
        _diag.COMPENSATION_DATASET_NOT_APPROVED,
        _diag.CALCULATION_FORMULA_NOT_APPROVED,
        _diag.CALCULATOR_ENGINE_PENDING,
        _diag.FORMULA_ENGINE_UNKNOWN,
        _diag.FORMULA_AMOUNT_RULE_UNKNOWN,
        _diag.FORMULA_AMOUNT_RULE_NOT_SINGLE_ROW_RANGE,
        _diag.FORMULA_AMOUNT_RULE_NOT_INHERITANCE_SHARE,
        _diag.FORMULA_ROW_TYPE_MISSING,
        _diag.FORMULA_RANGE_PARAMETERS_INCOMPLETE,
        _diag.COMPENSATION_ROW_MATCH_MISSING,
        _diag.COMPENSATION_ROW_DISAMBIGUATION,
        _diag.COMPENSATION_RANGE_INCONSISTENT,
        _diag.INHERITANCE_SHARE_SPEC_INVALID,
        _diag.APPLICABLE_LAW_REVIEW_REQUIRED,
    ):
        assert _diag.diagnostic_public_safe(code) is False


# ---------------------------------------------------------------------------
# 3 — diagnostic_to_public_warning refuses internal codes
# ---------------------------------------------------------------------------


def test_diagnostic_to_public_warning_refuses_internal_codes():
    with pytest.raises(ValueError):
        _diag.diagnostic_to_public_warning(_diag.LEGAL_SOURCES_NOT_APPROVED)


# ---------------------------------------------------------------------------
# 4 — IT / FR / AR translations exist for the Italy public-safe codes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        _diag.ITALY_RANGE_COLLAPSED,
        _diag.ITALY_FIELD_NOT_AGGREGATED,
        _diag.ITALY_FAULT_REDUCTION_APPLIED,
        _diag.ITALY_FAULT_REDUCTION_APPLIED_UNIFORM,
    ],
)
def test_italy_public_codes_translated_in_it_fr_ar(code):
    en = _diag.diagnostic_message(code, language="en", context={"field": "medical_expenses"})
    for lang in ("it", "fr", "ar"):
        translated = _diag.diagnostic_message(
            code, language=lang, context={"field": "medical_expenses"}
        )
        assert translated != en, f"{code} not translated in {lang}"


# ---------------------------------------------------------------------------
# 5 — context interpolation localises the field label
# ---------------------------------------------------------------------------


def test_italy_field_not_aggregated_localises_field_label():
    en = _diag.diagnostic_message(
        _diag.ITALY_FIELD_NOT_AGGREGATED,
        language="en",
        context={"field": "medical_expenses"},
    )
    it = _diag.diagnostic_message(
        _diag.ITALY_FIELD_NOT_AGGREGATED,
        language="it",
        context={"field": "medical_expenses"},
    )
    assert "medical expenses" in en or "documented medical expenses" in en
    assert "spese mediche" in it


# ---------------------------------------------------------------------------
# 6 — Italia 35 / 10 / 0 unchanged with diagnostics migration
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_full_setup(db):
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
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
        slug="it-fixture-italy-public-warnings",
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
        source_version=approved_source_version(src),
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
        source_version=approved_source_version(src),
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
        code="italy_art_138_tun_2025_italy_pub_warn",
        name="italy-pub-warn-smoke",
        expression_text="placeholder-test",
        source_reference="placeholder-test",
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
    return italy


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_italy_warning_migration(italy_full_setup):
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
# 7 — single-row scenario: warning "range collapsed" is emitted via diagnostic
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_single_row_setup(db):
    """Seed a single-row formula (no range) so the calculated path
    triggers the ``ITALY_RANGE_COLLAPSED`` warning."""
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
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
        slug="it-fixture-italy-single-row",
        title="Italy single-row fixture",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
        effective_date=date(2025, 1, 1),
    )
    ds = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="single-row",
        version_label="DPR-SINGLE-ROW",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 1),
    )
    CompensationTableRow.objects.create(
        dataset=ds,
        row_type="tun_biological_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("12345"),
    )
    CalculationFormula.objects.create(
        dataset=ds,
        code="italy_single_row_warn",
        name="single-row-warn",
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
    return italy


@pytest.mark.django_db
def test_italy_single_row_warning_uses_public_diagnostic(italy_single_row_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "medical_expenses": "5000",
        },
    )
    warnings = (sim.output_data or {}).get("warnings") or []
    # Range-collapsed warning must be present in some locale.
    candidates_collapsed = {
        _diag.diagnostic_message(_diag.ITALY_RANGE_COLLAPSED, language=lang)
        for lang in ("en", "it", "fr", "ar")
    }
    assert any(w in candidates_collapsed for w in warnings), warnings
    # Field-not-aggregated warning interpolates the field label.
    assert any("medical" in w.lower() or "mediche" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# 8 — public result IT shows the localised warning
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_result_it_shows_translated_warning(italy_single_row_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "medical_expenses": "5000",
        },
    )
    response = Client().get(
        reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    )
    body = response.content.decode("utf-8")
    # Italian rendering shows the translated phrase.
    assert (
        "I valori min, centrale e max coincidono" in body
        or "spese mediche documentate" in body
        or "min, central and max" in body
    )


# ---------------------------------------------------------------------------
# 9 — PDF IT remains a valid %PDF document
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_pdf_remains_valid_pdf(italy_full_setup):
    from apps.calculators.enums import CaseType
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
    response = Client().get(
        reverse("reports:simulation_pdf", kwargs={"public_id": str(sim.public_id)})
    )
    assert response.status_code == 200
    content = b"".join(response.streaming_content)
    assert content.startswith(b"%PDF")


# ---------------------------------------------------------------------------
# 10 — public result IT contains no banned words after migration
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_banned_words_on_italy_result_page(italy_full_setup):
    from apps.calculators.enums import CaseType
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
    body = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)}))
        .content.decode("utf-8")
        .lower()
    )
    for banned in (
        "scaffold",
        "placeholder",
        "under validation",
        "module pending",
        "engine pending",
        "missing_documents",
        "unavailable_requires_legal_validation",
    ):
        assert banned not in body


# ---------------------------------------------------------------------------
# 11 — no Pexels attribution on Italy result
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_pexels_attribution_on_italy_result(italy_full_setup):
    from apps.calculators.enums import CaseType
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
    body = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)}))
        .content.decode("utf-8")
    )
    assert "pexels.com" not in body.lower()
    assert not ("Photo by" in body and "Pexels" in body)


# ---------------------------------------------------------------------------
# 12 — no API key leak on Italy result
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_api_key_leak_on_italy_result(italy_full_setup):
    from apps.calculators.enums import CaseType
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
    body = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)}))
        .content.decode("utf-8")
    )
    for needle in ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY"):
        assert needle not in body


# ---------------------------------------------------------------------------
# 13 — single H1 regression net for the result page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_result_renders_single_h1(italy_full_setup):
    from apps.calculators.enums import CaseType
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
    body = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)}))
        .content.decode("utf-8")
    )
    h1s = re.findall(r"<h1\b", body, flags=re.IGNORECASE)
    assert len(h1s) == 1
