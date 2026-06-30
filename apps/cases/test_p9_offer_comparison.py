"""P9 Fase D — public guard tests for the insurance offer comparison.

Guards the public cabling: the comparison wizard renders the mandatory
disclaimer, requires an offer, routes to the approved estimate engine, and the
result page reports offer-vs-estimate with a below/within/above verdict and the
percentage deviation. The estimate itself is the approved engine (proven in
test_italy_art139_micro.py); the comparison is pure arithmetic.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from apps.calculators.enums import CalculationStatus, CaseType

OFFER_URL = "/wizard/it/offer-comparison/"
_DISCLAIMER_IT = "Confronto tabellare orientativo basato su fonti ufficiali"
_COEFF = {1: "1.0", 2: "1.1", 3: "1.2", 4: "1.3", 5: "1.5", 6: "1.7", 7: "1.9", 8: "2.1", 9: "2.3"}


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
        default_currency=eur, default_language=italian,
    )
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
        name="Microlesioni art. 139", version_label="ART139-MIMIT-2025",
        status=DatasetStatus.APPROVED, valid_from=date(2025, 4, 1),
    )
    for p, c in _COEFF.items():
        CompensationTableRow.objects.create(
            dataset=micro_ds, row_type="disability_coefficient",
            disability_min=p, disability_max=p, coefficient=Decimal(c))
    CompensationTableRow.objects.create(
        dataset=micro_ds, row_type="first_point_value", point_value=Decimal("963.40"))
    CompensationTableRow.objects.create(
        dataset=micro_ds, row_type="itt_daily_absolute", daily_amount=Decimal("56.18"))

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
        status=DatasetStatus.APPROVED, valid_from=date(2025, 1, 13))
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


def _post(client, *, offer, pct, age=35, itt=0):
    # Pin the default language on the followed result-page GET so the request
    # does not leave a non-default language active in the thread (which would
    # make unprefixed-URL reverse() assertions elsewhere see an /en/ prefix).
    return client.post(OFFER_URL, {
        "accident_country": "IT",
        "victim_age": age,
        "permanent_disability_percentage": pct,
        "total_temporary_disability_days": itt,
        "offer_amount": offer,
        "consent_simulation": "on",
        "special_categories_consent": "on",
    }, follow=True, HTTP_ACCEPT_LANGUAGE="it")


@pytest.mark.django_db
def test_offer_wizard_get_renders_field_and_disclaimer(client):
    resp = client.get(OFFER_URL, HTTP_ACCEPT_LANGUAGE="it")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert 'name="offer_amount"' in body
    assert _DISCLAIMER_IT in body  # mandatory comparison disclaimer (Italian)


@pytest.mark.django_db
def test_offer_required(client):
    # No offer_amount → form invalid → re-render (200), no redirect to a result.
    resp = client.post(OFFER_URL, {
        "accident_country": "IT", "victim_age": 35,
        "permanent_disability_percentage": 5, "total_temporary_disability_days": 0,
        "consent_simulation": "on", "special_categories_consent": "on",
    }, HTTP_ACCEPT_LANGUAGE="it")
    assert resp.status_code == 200
    assert "/wizard/result/" not in resp.get("Location", "")


@pytest.mark.django_db
def test_offer_below_range(client, italy_official_stack):
    # 5% @35 → micro estimate 6322.31; offer 3000 is below.
    resp = _post(client, offer="3000", pct=5)
    body = resp.content.decode("utf-8")
    assert 'data-offer-verdict="below"' in body
    assert _DISCLAIMER_IT in body


@pytest.mark.django_db
def test_offer_above_range(client, italy_official_stack):
    resp = _post(client, offer="9000", pct=5)
    body = resp.content.decode("utf-8")
    assert 'data-offer-verdict="above"' in body


@pytest.mark.django_db
def test_offer_within_range(client, italy_official_stack):
    # 10% @35 → TUN range 26268..28439; offer 27000 is within.
    resp = _post(client, offer="27000", pct=10)
    body = resp.content.decode("utf-8")
    assert 'data-offer-verdict="within"' in body


@pytest.mark.django_db
def test_offer_simulation_is_calculated(client, italy_official_stack):
    _post(client, offer="3000", pct=5)
    from apps.cases.models import Simulation
    sim = Simulation.objects.latest("created_at")
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.input_data.get("offer_amount") == "3000"


@pytest.mark.django_db
def test_offer_landing_primary_cta_points_to_wizard(client):
    body = client.get(
        "/case-types/insurance-offer-review/", HTTP_ACCEPT_LANGUAGE="it"
    ).content.decode("utf-8")
    assert OFFER_URL in body


@pytest.mark.django_db
def test_plain_road_result_has_no_offer_block(client, italy_official_stack):
    """A road simulation without an offer must not show the comparison block."""
    from django.urls import reverse

    from apps.cases.services import run_simulation
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_MICROLESIONS.value,
        input_data={"victim_age": 35, "permanent_disability_percentage": 5,
                    "total_temporary_disability_days": 0},
    )
    url = reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    body = client.get(url, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert "data-offer-verdict" not in body
