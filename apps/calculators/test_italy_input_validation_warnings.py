"""Tests F-italy-input-validation-warnings-pass1.

Cover the input-validation diagnostic migration: missing required
inputs and out-of-range fault percentage now route through the
public-safe diagnostics layer with localised messages and field
labels in IT / FR / AR / EN. Italia 35/10/0 → 26 268 / 27 353 /
28 439 EUR remains, the PDF still serves a valid `%PDF` document.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators import diagnostics as _diag

# ---------------------------------------------------------------------------
# 1 — required input missing routes through the diagnostic helper
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
        slug="it-fixture-input-validation",
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
        code="italy_art_138_tun_2025_input_validation",
        name="input-validation-smoke",
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
def test_required_input_missing_uses_diagnostic_helper(italy_full_setup):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"permanent_disability_percentage": 10})
    assert result.status == CalculationStatus.INSUFFICIENT_INPUT.value
    # Warning is sourced from ITALY_REQUIRED_INPUT_MISSING — text contains
    # the localised "age of the injured person" label.
    assert any(
        "age of the injured person" in w
        or "età della persona infortunata" in w
        or "âge de la personne blessée" in w
        for w in result.warnings
    )


# ---------------------------------------------------------------------------
# 2 — fault_percentage < 0 routes to ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fault_percentage_negative_routes_to_diagnostic(italy_full_setup):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute(
        {
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "fault_percentage": -5,
        }
    )
    assert result.status == CalculationStatus.INSUFFICIENT_INPUT.value
    candidates = {
        _diag.diagnostic_message(_diag.ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE, language=lang)
        for lang in ("en", "it", "fr", "ar")
    }
    assert any(any(c == w or c in w for c in candidates) for w in result.warnings)


# ---------------------------------------------------------------------------
# 3 — fault_percentage > 100 routes to ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fault_percentage_over_100_routes_to_diagnostic(italy_full_setup):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute(
        {
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "fault_percentage": 150,
        }
    )
    assert result.status == CalculationStatus.INSUFFICIENT_INPUT.value
    candidates = {
        _diag.diagnostic_message(_diag.ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE, language=lang)
        for lang in ("en", "it", "fr", "ar")
    }
    assert any(any(c == w or c in w for c in candidates) for w in result.warnings)


# ---------------------------------------------------------------------------
# 4 — field labels are localised, including in lists
# ---------------------------------------------------------------------------


def test_required_input_missing_localises_field_list():
    en = _diag.diagnostic_message(
        _diag.ITALY_REQUIRED_INPUT_MISSING,
        language="en",
        context={"fields": ("victim_age", "permanent_disability_percentage")},
    )
    it = _diag.diagnostic_message(
        _diag.ITALY_REQUIRED_INPUT_MISSING,
        language="it",
        context={"fields": ("victim_age", "permanent_disability_percentage")},
    )
    fr = _diag.diagnostic_message(
        _diag.ITALY_REQUIRED_INPUT_MISSING,
        language="fr",
        context={"fields": ("victim_age", "permanent_disability_percentage")},
    )
    ar = _diag.diagnostic_message(
        _diag.ITALY_REQUIRED_INPUT_MISSING,
        language="ar",
        context={"fields": ("victim_age", "permanent_disability_percentage")},
    )
    assert "age of the injured person" in en
    assert "permanent disability percentage" in en
    assert "età della persona infortunata" in it
    assert "percentuale di invalidità permanente" in it
    assert "âge de la personne blessée" in fr
    assert "pourcentage d'invalidité permanente" in fr
    # Arabic uses the localised label too.
    assert "عمر الشخص المصاب" in ar


# ---------------------------------------------------------------------------
# 5 — FR result/warning is translated, no English fallback
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_locale_no_english_fallback_for_input_warning(italy_full_setup):
    from django.utils import translation

    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    # The diagnostic message is resolved at engine-compute time
    # using the active translation. The wizard's LocaleMiddleware
    # activates the request locale before calling run_simulation;
    # the test reproduces that by overriding to FR for compute.
    with translation.override("fr"):
        sim = run_simulation(
            jurisdiction_code="IT-NATIONAL",
            case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
            input_data={"permanent_disability_percentage": 10},
            locale="fr",
        )
    response = Client(HTTP_ACCEPT_LANGUAGE="fr").get(f"/fr/wizard/result/{sim.public_id}/")
    body = response.content.decode("utf-8", errors="replace")
    # FR translated warning must be present.
    assert "Certains champs nécessaires" in body or "âge de la personne blessée" in body
    # English source string must NOT appear publicly.
    assert "Some fields needed for the estimate are missing" not in body


# ---------------------------------------------------------------------------
# 6 — AR result/warning is translated
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ar_locale_no_english_fallback_for_input_warning(italy_full_setup):
    from django.utils import translation

    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    with translation.override("ar"):
        sim = run_simulation(
            jurisdiction_code="IT-NATIONAL",
            case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
            input_data={"permanent_disability_percentage": 10},
            locale="ar",
        )
    response = Client(HTTP_ACCEPT_LANGUAGE="ar").get(f"/ar/wizard/result/{sim.public_id}/")
    body = response.content.decode("utf-8", errors="replace")
    assert "تنقص بعض الحقول" in body or "عمر الشخص المصاب" in body
    assert "Some fields needed for the estimate are missing" not in body


# ---------------------------------------------------------------------------
# 7 — public result page does not show diagnostic codes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_result_page_no_diagnostic_codes(italy_full_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "fault_percentage": 200,
        },
    )
    response = Client().get(
        reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    )
    body = response.content.decode("utf-8")
    for code in (
        _diag.ITALY_REQUIRED_INPUT_MISSING,
        _diag.ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE,
        _diag.ITALY_INVALID_PERCENTAGE_INPUT,
        _diag.ITALY_INPUT_PAYLOAD_INVALID,
        _diag.ITALY_FORMULA_INPUT_MISMATCH,
    ):
        assert code not in body


# ---------------------------------------------------------------------------
# 8 — form errors visible in IT (Django default) and translated
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_form_field_labels_visible_on_wizard_it():
    body = Client().get("/wizard/it/road-accident/").content.decode("utf-8")
    # IT locale must show the IT field labels.
    for needle in (
        "Età della persona infortunata",
        "Invalidità permanente",
        "Concorso di colpa",
    ):
        assert needle in body, f"missing field label {needle!r}"


# ---------------------------------------------------------------------------
# 9 — Italia 35/10/0 unchanged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_input_validation_migration(italy_full_setup):
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
# 10 — IT PDF still %PDF
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_pdf_remains_valid_after_input_validation(italy_full_setup):
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
# 11 — no banned words on the result page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_banned_words_on_result_page(italy_full_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "fault_percentage": 200,
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
# 12 — no Pexels attribution
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_pexels_attribution_on_result_page(italy_full_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "permanent_disability_percentage": 10},
    )
    body = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)}))
        .content.decode("utf-8")
    )
    assert "pexels.com" not in body.lower()
    assert not ("Photo by" in body and "Pexels" in body)


# ---------------------------------------------------------------------------
# 13 — no API key leak
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_api_key_leak_on_result_page(italy_full_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "permanent_disability_percentage": 10},
    )
    body = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)}))
        .content.decode("utf-8")
    )
    for needle in ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY"):
        assert needle not in body
