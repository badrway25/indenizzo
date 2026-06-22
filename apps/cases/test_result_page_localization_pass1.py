"""Tests F-inheritance-wizard-result-page-localization-pass1.

Cover the public result page so that:

1. FR / BE / MA / TN unavailable results never surface internal
   diagnostics ("missing_documents", "compensation_dataset_approved",
   "calculator_engine_pending_for_jurisdiction", "No approved legal
   sources are available", etc.).
2. The result page contains the curated public title / summary /
   next-steps from :mod:`apps.cases.public_result_messages`.
3. /fr/ and /ar/ result pages render the localised public copy and
   no English fallback for the in-iter strings.
4. No banned public words, no duplicate H1, no Pexels attribution
   leak, no API key leak.
5. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains unchanged.
6. The Italian PDF still serves a valid ``%PDF`` document.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

# ---------------------------------------------------------------------------
# fixture builders
# ---------------------------------------------------------------------------


@pytest.fixture
def fr_setup(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    fr_lang = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": france, "language": fr_lang, "jurisdiction": juris}


@pytest.fixture
def be_setup(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    belgium = Country.objects.create(code="BE", code_alpha3="BEL", name="Belgique")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    fr_lang = Language.objects.get_or_create(code="fr", defaults={"name": "Français"})[0]
    juris = Jurisdiction.objects.create(
        country=belgium,
        code="BE-NATIONAL",
        name="Belgique",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": belgium, "language": fr_lang, "jurisdiction": juris}


@pytest.fixture
def morocco_setup(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    morocco = Country.objects.create(code="MA", code_alpha3="MAR", name="Maroc")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    arabic = Language.objects.create(code="ar", name="العربية")
    juris = Jurisdiction.objects.create(
        country=morocco,
        code="MA-NATIONAL",
        name="Maroc",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": morocco, "language": arabic, "jurisdiction": juris}


@pytest.fixture
def tunisia_setup(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    tunisia = Country.objects.create(code="TN", code_alpha3="TUN", name="Tunisie")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    arabic = Language.objects.get_or_create(code="ar", defaults={"name": "العربية"})[0]
    juris = Jurisdiction.objects.create(
        country=tunisia,
        code="TN-NATIONAL",
        name="Tunisie",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": tunisia, "language": arabic, "jurisdiction": juris}


# ---------------------------------------------------------------------------
# Banned strings — never on the public result page.
# ---------------------------------------------------------------------------


BANNED_INTERNAL = (
    "unavailable_requires_legal_validation",
    "No approved legal sources are available",
    "missing_documents",
    "compensation_dataset_approved",
    "calculation_formula_approved",
    "calculator_engine_pending_for_jurisdiction",
    "formula_engine_unknown",
    "formula_amount_rule_unknown",
    "formula_amount_rule_not_inheritance_share",
    "formula_amount_rule_not_single_row_range",
    "shares_spec_invalid",
    "Approved legal sources are present",
    "Approved formula declares amount_rule",
    "An approved formula exists",
)


_COUNTRY_ISO = {"morocco": "MA", "tunisia": "TN", "france": "FR", "belgium": "BE"}


def _post_and_follow_inheritance(client: Client, country_code: str, payload_extra: dict) -> str:
    url = reverse(f"cases:wizard_{country_code}_inheritance")
    iso = _COUNTRY_ISO[country_code]
    base_payload = {
        "deceased_country_of_last_residence": iso,
        "nationality": iso,
        "spouse_present": "on",
        "surviving_spouse_gender": "wife",
        "sons_count": "1",
        "daughters_count": "1",
        "consent_simulation": "on",
        "special_categories_consent": "on",
        "website": "",
        **payload_extra,
    }
    response = client.post(url, base_payload, follow=True)
    return response.content.decode("utf-8", errors="replace")


def _post_and_follow_road_accident(client: Client, country_code: str) -> str:
    url = reverse(f"cases:wizard_{country_code}_road_accident")
    payload = {
        "victim_age": "30",
        "permanent_disability_percentage": "5",
        "fault_percentage": "0",
        "consent_simulation": "on",
        "special_categories_consent": "on",
        "website": "",
    }
    response = client.post(url, payload, follow=True)
    return response.content.decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# 1 — FR result hides internal diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_unavailable_result_hides_internal_diagnostics(fr_setup):
    body = _post_and_follow_road_accident(Client(), "france")
    for needle in BANNED_INTERNAL:
        assert needle not in body, f"FR result leaks {needle!r}"


# ---------------------------------------------------------------------------
# 2 — BE result hides internal diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_be_unavailable_result_hides_internal_diagnostics(be_setup):
    body = _post_and_follow_road_accident(Client(), "belgium")
    for needle in BANNED_INTERNAL:
        assert needle not in body, f"BE result leaks {needle!r}"


# ---------------------------------------------------------------------------
# 3 — MA result hides internal diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_unavailable_result_hides_internal_diagnostics(morocco_setup):
    body = _post_and_follow_inheritance(Client(), "morocco", {"estate_value": "800000"})
    for needle in BANNED_INTERNAL:
        assert needle not in body, f"MA result leaks {needle!r}"


# ---------------------------------------------------------------------------
# 4 — TN result hides internal diagnostics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_unavailable_result_hides_internal_diagnostics(tunisia_setup):
    body = _post_and_follow_inheritance(
        Client(),
        "tunisia",
        {"mother_present": "on", "estate_value": "1200000"},
    )
    for needle in BANNED_INTERNAL:
        assert needle not in body, f"TN result leaks {needle!r}"


# ---------------------------------------------------------------------------
# 5 — unavailable result contains public title + summary
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_unavailable_result_shows_public_message(morocco_setup):
    body = _post_and_follow_inheritance(Client(), "morocco", {"estate_value": "800000"})
    # Localised summary (default IT) must appear.
    assert "caso successorio è stato ricevuto" in body.lower()
    # Status panel badge (centralised public_status copy) still rendered.
    assert "Analisi successoria internazionale" in body
    # "What happens next" header (IT) appears too.
    assert "Cosa succede ora" in body


# ---------------------------------------------------------------------------
# 6 — FR result page translated under /fr/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_result_translated_under_fr_locale(fr_setup):
    client = Client()
    payload = {
        "victim_age": "30",
        "permanent_disability_percentage": "5",
        "fault_percentage": "0",
        "consent_simulation": "on",
        "special_categories_consent": "on",
        "website": "",
    }
    response = client.post("/fr/wizard/fr/road-accident/", payload, follow=True)
    body = response.content.decode("utf-8", errors="replace")
    # FR localisation of the public message
    assert "Votre dossier a été reçu" in body
    assert "Étapes suivantes" in body or "Étapes suivantes" in body
    # English source must not leak through
    assert "Your case has been received for a preliminary legal" not in body
    assert "What happens next" not in body


# ---------------------------------------------------------------------------
# 7 — MA result page translated under /ar/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_result_translated_under_ar_locale(morocco_setup):
    client = Client()
    payload = {
        "deceased_country_of_last_residence": "MA",
        "nationality": "MA",
        "spouse_present": "on",
        "surviving_spouse_gender": "wife",
        "sons_count": "1",
        "daughters_count": "1",
        "estate_value": "800000",
        "consent_simulation": "on",
        "special_categories_consent": "on",
        "website": "",
    }
    response = client.post("/ar/wizard/ma/inheritance/", payload, follow=True)
    body = response.content.decode("utf-8", errors="replace")
    # AR localisation
    assert "تم استلام ملف الميراث الخاص بك" in body
    assert "ما الذي يحدث بعد ذلك" in body
    # English source must not leak through
    assert "Your inheritance case has been received" not in body
    assert "What happens next" not in body


# ---------------------------------------------------------------------------
# 8 — no banned public words on result pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_no_banned_public_words(morocco_setup):
    body = _post_and_follow_inheritance(Client(), "morocco", {"estate_value": "800000"})
    banned = (
        "scaffold",
        "placeholder",
        "under validation",
        "in preparation",
        "coming soon",
        "work in progress",
        "in corso",
        "legal validation wizard",
        "module pending",
        "engine pending",
    )
    body_lower = body.lower()
    for word in banned:
        assert word not in body_lower, f"banned word {word!r} on MA result page"


# ---------------------------------------------------------------------------
# 9 — no duplicate H1 on the result page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_no_duplicate_h1(morocco_setup):
    body = _post_and_follow_inheritance(Client(), "morocco", {"estate_value": "800000"})
    h1_open = re.findall(r"<h1\b", body, flags=re.IGNORECASE)
    assert len(h1_open) == 1, f"result page has {len(h1_open)} H1 tags, expected 1"


# ---------------------------------------------------------------------------
# 10 — no Pexels attribution on the result page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_no_pexels_attribution(morocco_setup):
    body = _post_and_follow_inheritance(Client(), "morocco", {"estate_value": "800000"})
    assert "pexels.com" not in body.lower()
    # Don't conflate Pexels attribution with photographer credits in
    # other contexts; only flag the dual signal.
    assert not ("Photo by" in body and "Pexels" in body)


# ---------------------------------------------------------------------------
# 11 — no API key leak on the result page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_no_api_key_leak(morocco_setup):
    body = _post_and_follow_inheritance(Client(), "morocco", {"estate_value": "800000"})
    assert "PEXELS_API_KEY" not in body
    assert "STRIPE_SECRET" not in body
    assert "SENDGRID_API_KEY" not in body


# ---------------------------------------------------------------------------
# 12 — Italia calculated result unchanged
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
        slug="it-fixture-result-localization",
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
        code="italy_art_138_tun_2025_result_localization",
        name="result-localization",
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
def test_italy_calculated_result_unchanged(italy_full_setup):
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
    # And the rendered result page still shows the range card.
    response = Client().get(
        reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    )
    body = response.content.decode("utf-8")
    assert "26268" in body
    assert "27353" in body
    assert "28439" in body


# ---------------------------------------------------------------------------
# 13 — IT PDF still serves a valid %PDF document
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_pdf_still_starts_with_pdf_marker(italy_full_setup):
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
    # ``simulation_pdf`` returns a streaming FileResponse. Pull the
    # first chunk to verify the magic marker.
    content = b"".join(response.streaming_content)
    assert content.startswith(b"%PDF"), "PDF response does not start with %PDF marker"
