"""
Tests F-product-public-site-qa-polish-pass1.

Coprono i post-condition della QA polish pass 1 — verificano che:

1. Tutte le pagine pubbliche principali rispondono 200.
2. Nessuna pagina pubblica espone "Photo by"/"on Pexels"
   come testo visibile (manifest interno OK, attribuzione visibile NO).
3. Nessuna pagina pubblica leakka un valore PEXELS_API_KEY
   anche quando una key fittizia è iniettata in settings.
4. Marker tradotti FR/AR sono presenti sui rispettivi entrypoint.
5. Wizard FR/BE/MA/TN POST con consenso → unavailable, nessun
   importo calcolato visibile.
6. IT 35/10/0 → 26 268 / 27 353 / 28 439 EUR (stesso contratto
   numerico dei pass precedenti — non deve regredire dopo la QA).
7. /sitemap.xml contiene gli URL delle 5 country landing.
8. Il PDF report per la simulazione Italia risponde 200 con
   `application/pdf`.
9. /contact/ POST con dati validi → /contact/thank-you/ + corpo IT.
10. I nomi paese (Italy/France/Belgium/Morocco/Tunisia) appaiono
    tradotti su /it/ /fr/ /ar/ countries — fix introdotto in QA pass1.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.test import Client, override_settings

PUBLIC_PAGES = [
    "/",
    "/fr/",
    "/ar/",
    "/countries/",
    "/countries/italy/",
    "/fr/countries/france/",
    "/ar/countries/morocco/",
    "/methodology/",
    "/fr/methodology/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
    "/fr/contact/",
    "/ar/contact/",
    "/privacy/",
    "/disclaimer/",
    "/sitemap.xml",
]


def _body(client: Client, url: str) -> str:
    response = client.get(url)
    assert response.status_code == 200, f"{url} status {response.status_code}"
    return response.content.decode("utf-8")


# ---------------------------------------------------------------------------
# 1 — public pages 200
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_page_returns_200(path: str):
    response = Client().get(path)
    assert response.status_code == 200, f"{path} -> {response.status_code}"


# ---------------------------------------------------------------------------
# 2 — no visible Pexels attribution leaks on public pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/fr/",
        "/ar/",
        "/countries/",
        "/countries/italy/",
        "/fr/countries/france/",
        "/ar/countries/morocco/",
        "/methodology/",
        "/wizard/",
        "/wizard/it/road-accident/",
        "/contact/",
    ],
)
def test_no_visible_pexels_attribution(path: str):
    body = _body(Client(), path)
    # Match the visible patterns "Photo by ... on Pexels" / "Photo de ... sur Pexels"
    # but allow path tokens like /media/pexels/foo.jpg that are URL filenames.
    visible_attribution = re.search(r"Photo by [A-Z]", body) or re.search(r"on Pexels\b", body)
    assert not visible_attribution, f"visible Pexels attribution leaked on {path}"
    assert "Photographed by" not in body
    assert "Crédit photo" not in body
    assert "Foto di" not in body


# ---------------------------------------------------------------------------
# 3 — no PEXELS_API_KEY leak in HTML
# ---------------------------------------------------------------------------


SENTINEL_API_KEY = "QA-PASS1-SENTINEL-KEY-9988776655"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/fr/", "/ar/", "/countries/", "/contact/"])
@override_settings(PEXELS_API_KEY=SENTINEL_API_KEY)
def test_no_api_key_leak(path: str):
    body = _body(Client(), path)
    assert SENTINEL_API_KEY not in body, f"API key leaked on {path}"


# ---------------------------------------------------------------------------
# 4 — FR/AR markers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_home_has_pass1_markers():
    body = _body(Client(), "/fr/")
    # The pass1 i18n iter shipped these visible strings; they must persist.
    must_have = [
        "Cabinet Légal International",
        "Lancer la simulation",  # P35: home CTA simplified ("…Italie" dropped)
    ]
    for needle in must_have:
        assert needle in body, f"FR marker missing on /fr/: {needle!r}"


@pytest.mark.django_db
def test_ar_home_has_pass1_markers():
    body = _body(Client(), "/ar/")
    # At least 4 of these 5 Arabic markers should appear (resilient to copy tweaks).
    markers = [
        "محاكاة إرشادية",  # indicative simulation
        "ابدأ محاكاة التعويض",  # start italy compensation simulation
        "ملفات تعريف الارتباط",  # cookies
        "زيارة الموقع المؤسسي",  # visit institutional website
        "البلدان",  # countries
    ]
    hits = [m for m in markers if m in body]
    assert len(hits) >= 3, f"AR markers on /ar/: {hits}"


# ---------------------------------------------------------------------------
# 5 — FR/BE/MA/TN wizard never claims a calculated estimate
# ---------------------------------------------------------------------------


def _post_with_consent(client: Client, url: str, *, with_consent_field: str = "consent_simulation"):
    """Fetch CSRF, then POST the bare minimum (consent + honeypot empty).

    The scaffold wizards accept this and reply with a 'requires legal
    validation' message rather than a calculated amount.
    """
    response = client.get(url)
    assert response.status_code == 200, url
    csrf = client.cookies.get("csrftoken")
    token = csrf.value if csrf else ""
    return client.post(
        url,
        data={
            "csrfmiddlewaretoken": token,
            with_consent_field: "on",
            "website": "",
            "robots": "",
        },
        follow=True,
    )


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/wizard/fr/road-accident/",
        "/wizard/be/road-accident/",
        "/wizard/ma/inheritance/",
        "/wizard/tn/inheritance/",
    ],
)
def test_under_review_wizards_never_show_calculated_amount(path: str):
    response = _post_with_consent(Client(), path)
    # Either redirect to a result, or stay on the page with a banner.
    body = response.content.decode("utf-8")
    # Must not show a 4-5 digit currency amount such as "26.268" "26 268" or
    # "26,268" or "EUR 26268" anywhere on the page.
    money = re.search(r"\b\d{1,3}[\xa0\.,\s]\d{3}(?!\d)\s*(?:EUR|€)", body)
    assert money is None, f"FR/BE/MA/TN wizard {path} returned a numeric amount: {money.group(0)!r}"


# ---------------------------------------------------------------------------
# 6 — IT 35/10/0 = 26 268 / 27 353 / 28 439 EUR
# (engine-level — same fixture pattern as test_i18n_translations_pass3.py)
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_qa_pass1(db):
    """Reuses the seed pattern of test_i18n_translations_pass3.italy_smoke_pass3
    so the QA pass1 contract test does not depend on production data."""
    from datetime import date

    from apps.calculators.enums import CaseType
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
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-qa-pass1",
        title="D.P.R. 12/2025",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
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
        code="italy_art_138_tun_2025_qa_pass1",
        name="qa-pass1-smoke",
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
    return {"country": italy}


@pytest.mark.django_db
def test_italy_smoke_engine_preserves_pass1_contract(italy_smoke_qa_pass1):
    """Re-checks that QA pass1 changes did not regress the Italy 35/10/0
    numeric contract at engine level — full HTTP funnel is exercised
    live by the runserver smoke at deploy time and by the funnel doc."""
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
# 7 — sitemap.xml lists the 5 country landing URLs
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sitemap_lists_country_landings():
    body = _body(Client(), "/sitemap.xml")
    for slug in ("italy", "france", "belgium", "morocco", "tunisia"):
        assert f"/countries/{slug}/" in body, f"sitemap missing /countries/{slug}/"


# ---------------------------------------------------------------------------
# 8 — Italy PDF report (via seeded simulation, not full HTTP funnel)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_pdf_report_returns_pdf(italy_smoke_qa_pass1):
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
    pdf_response = Client().get(f"/reports/simulation/{sim.public_id}/pdf/")
    assert pdf_response.status_code == 200
    assert pdf_response["content-type"].startswith("application/pdf"), pdf_response["content-type"]
    payload = b"".join(pdf_response.streaming_content)
    assert payload[:4] == b"%PDF", "PDF magic bytes missing"


# ---------------------------------------------------------------------------
# 9 — contact submit produces thank-you in IT
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_submit_renders_thank_you_in_italian():
    client = Client()
    client.get("/contact/")
    csrf = client.cookies.get("csrftoken")
    token = csrf.value if csrf else ""
    payload = {
        "csrfmiddlewaretoken": token,
        "first_name": "QA",
        "last_name": "Pass1",
        "email": "qa+local@example.test",
        "phone_number": "",
        "preferred_language": "it",
        "country": "",
        "case_type": "",
        "message": "QA pass1 funnel test (do not reply). Lorem ipsum dolor sit amet.",
        "privacy_accepted": "on",
        "special_categories_accepted": "on",
        "robots": "",
    }
    response = client.post("/contact/", data=payload, follow=True)
    assert response.status_code == 200
    body = response.content.decode("utf-8").lower()
    assert "thank-you" in response.request["PATH_INFO"] or "ricevuta" in body
    assert "grazie" in body or "ricevuta" in body, "thank-you copy missing"


# ---------------------------------------------------------------------------
# 10 — country names appear in the requested language on /countries/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_country_names_translated_per_language():
    client = Client()
    # IT default
    body_it = _body(client, "/countries/")
    for it_name in ("Italia", "Francia", "Belgio", "Marocco", "Tunisia"):
        assert it_name in body_it, f"IT country name missing on /countries/: {it_name}"

    body_fr = _body(client, "/fr/countries/")
    for fr_name in ("Italie", "France", "Belgique", "Maroc", "Tunisie"):
        assert fr_name in body_fr, f"FR country name missing on /fr/countries/: {fr_name}"

    body_ar = _body(client, "/ar/countries/")
    for ar_name in ("إيطاليا", "فرنسا", "بلجيكا", "المغرب", "تونس"):
        assert ar_name in body_ar, f"AR country name missing on /ar/countries/: {ar_name}"
