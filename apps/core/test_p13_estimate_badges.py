"""P13-FIX — guard that the public estimate badge is not limited to road accident.

The /services/ page and the result page must distinguish the three approved
estimate states (numeric / tabular-biological / offer-comparison) plus the
guided pathway, so "Stima da fonte ufficiale" is no longer the only estimate
badge and medical / offer are not rendered as guided-only.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators.enums import CalculationStatus, CaseType
from apps.core import public_pages

_BADGES_IT = (
    "Stima da fonte ufficiale",
    "Stima tabellare del danno biologico",
    "Confronto con fonte ufficiale",
    "Percorso assistito con fonte ufficiale",
)
_COEFF = {1: "1.0", 2: "1.1", 3: "1.2", 4: "1.3", 5: "1.5", 6: "1.7", 7: "1.9", 8: "2.1", 9: "2.3"}


# ---- data-level contract -------------------------------------------------

def test_three_engines_are_calculable_not_only_road():
    calculable = {s.key for s in public_pages.SERVICES if s.calculable}
    assert calculable == {"road_accident", "medical", "insurance_offer"}
    assert len(calculable) >= 3  # not only road accident


def test_each_estimate_state_has_a_distinct_badge():
    from django.utils import translation

    with translation.override("en"):  # resolve lazy badges to their English source
        by_key = {s.key: str(s.badge) for s in public_pages.SERVICES}
        badges = {str(s.badge) for s in public_pages.SERVICES}
    assert by_key["road_accident"] == "Estimate based on official sources"
    assert by_key["medical"] == "Official table-based biological damage estimate"
    assert by_key["insurance_offer"] == "Comparison based on official sources"
    # P15: work injury is now a documental pre-check; death stays a guided path;
    # international is reframed as applicable-law framing.
    assert by_key["work_injury"] == "Documental pre-check with official sources"
    assert by_key["death"] == "Assisted path based on official sources"
    assert by_key["international"] == "Applicable-law framing"
    # all estimate/guided states are present and distinct
    assert {
        "Estimate based on official sources",
        "Official table-based biological damage estimate",
        "Comparison based on official sources",
        "Assisted path based on official sources",
        "Documental pre-check with official sources",
        "Applicable-law framing",
    } <= badges


def test_calculable_services_route_to_a_wizard():
    for s in public_pages.SERVICES:
        if s.calculable:
            assert s.cta_url_name.startswith("cases:wizard"), s.key


@pytest.mark.django_db
def test_services_page_renders_four_distinct_badges():
    body = Client().get("/services/", HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    for badge in _BADGES_IT:
        assert badge in body, f"/services/ missing badge {badge!r}"
    # medical/offer reachable from services as estimate flows, not contact-only
    assert "/wizard/it/medical-malpractice/" in body
    assert "/wizard/it/offer-comparison/" in body


# ---- result-page badges (need the approved stack) ------------------------

@pytest.fixture
def italy_official_stack(db):
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
        default_currency=eur, default_language=italian)
    micro_src = LegalSource.objects.create(
        slug="it-art139", title="art. 139", country=italy, jurisdiction=juris, language=italian,
        source_type=SourceType.MINISTRY_DECREE, status=SourceStatus.APPROVED,
        publication_date=date(2025, 7, 31), effective_date=date(2025, 4, 1))
    micro_ds = CompensationDataset.objects.create(
        source=micro_src, source_version=approved_source_version(micro_src),
        jurisdiction=juris, country=italy, case_type=CaseType.ROAD_ACCIDENT_MICROLESIONS.value,
        name="micro", version_label="ART139", status=DatasetStatus.APPROVED, valid_from=date(2025, 4, 1))
    for p, c in _COEFF.items():
        CompensationTableRow.objects.create(
            dataset=micro_ds, row_type="disability_coefficient",
            disability_min=p, disability_max=p, coefficient=Decimal(c))
    CompensationTableRow.objects.create(dataset=micro_ds, row_type="first_point_value", point_value=Decimal("963.40"))
    CompensationTableRow.objects.create(dataset=micro_ds, row_type="itt_daily_absolute", daily_amount=Decimal("56.18"))
    tun_src = LegalSource.objects.create(
        slug="it-tun", title="TUN", country=italy, jurisdiction=juris, language=italian,
        source_type=SourceType.MINISTRY_DECREE, status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11), effective_date=date(2025, 1, 13))
    base_ds = CompensationDataset.objects.create(
        source=tun_src, source_version=approved_source_version(tun_src),
        jurisdiction=juris, country=italy, case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base", version_label="DPR-12-2025", status=DatasetStatus.APPROVED, valid_from=date(2025, 1, 13))
    CompensationTableRow.objects.create(
        dataset=base_ds, row_type="tun_biological_total_amount",
        age_min=35, age_max=35, disability_min=10, disability_max=10, point_value=Decimal("1"))
    moral_ds = CompensationDataset.objects.create(
        source=tun_src, source_version=approved_source_version(tun_src),
        jurisdiction=juris, country=italy, case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral", version_label="DPR-12-2025-MORAL", status=DatasetStatus.APPROVED, valid_from=date(2025, 1, 13))
    for kind, amount in (("min", "26268"), ("mid", "27353"), ("max", "28439")):
        CompensationTableRow.objects.create(
            dataset=moral_ds, row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=35, age_max=35, disability_min=10, disability_max=10, point_value=Decimal(amount))
    CalculationFormula.objects.create(
        dataset=base_ds, code="italy_art_138_tun_2025_base", name="range",
        expression_text="x", source_reference="x", status=DatasetStatus.APPROVED,
        parameters={"engine": "italy_tun_point_value_v1",
                    "requires": ["victim_age", "permanent_disability_percentage"],
                    "row_match": ["victim_age", "permanent_disability_percentage"],
                    "amount_rule": "row_amount_range_direct", "fault_reduction": True,
                    "range_dataset_version_label": "DPR-12-2025-MORAL",
                    "min_row_type": "tun_biological_moral_min_total_amount",
                    "mid_row_type": "tun_biological_moral_mid_total_amount",
                    "max_row_type": "tun_biological_moral_max_total_amount"})
    return {"country": italy}


def _result_body(client, case_type, pct, age=35, extra=None):
    from apps.cases.services import run_simulation
    data = {"victim_age": age, "permanent_disability_percentage": pct,
            "total_temporary_disability_days": 0}
    if extra:
        data.update(extra)
    sim = run_simulation(jurisdiction_code="IT-NATIONAL", case_type=case_type, input_data=data)
    url = reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    return client.get(url, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8"), sim


@pytest.mark.django_db
@pytest.mark.parametrize("pct", [5, 10])
def test_medical_result_shows_tabular_badge(client, italy_official_stack, pct):
    body, sim = _result_body(client, CaseType.MEDICAL_LIABILITY_BIOLOGICAL.value, pct)
    assert sim.status == CalculationStatus.CALCULATED.value
    assert "Stima tabellare del danno biologico" in body


@pytest.mark.django_db
@pytest.mark.parametrize("pct", [5, 10])
def test_road_result_shows_official_estimate_badge(client, italy_official_stack, pct):
    ct = (CaseType.ROAD_ACCIDENT_MICROLESIONS.value if pct < 10
          else CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    body, sim = _result_body(client, ct, pct)
    assert sim.status == CalculationStatus.CALCULATED.value
    assert "Stima da fonte ufficiale" in body


@pytest.mark.django_db
def test_offer_result_shows_comparison_badge(client, italy_official_stack):
    body, sim = _result_body(
        client, CaseType.ROAD_ACCIDENT_MICROLESIONS.value, 5, extra={"offer_amount": "3000"})
    assert sim.status == CalculationStatus.CALCULATED.value
    assert "Confronto con fonte ufficiale" in body
