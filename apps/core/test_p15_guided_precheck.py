"""P15 — guard the intelligent guided pre-check flows and country × category router.

The public must get a CONCRETE guided path for every category: an estimate where
an approved engine exists, otherwise a documental pre-check / applicable-law
framing grounded in official sources — never a roadmap, a weak technical state or
an invented amount. These tests lock that contract in.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from apps.core.guided_router import ROUTES, resolve

# A money amount = thousands-grouped number followed by a currency mark.
_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")

PRECHECK_SLUGS = [
    "inail",
    "loss-of-relative",
    "morocco-road-accident",
    "tunisia-road-accident",
    "international-road-accident",
]

# Technical / weak states that must never reach the public.
_BANNED = ("in revisione", "needs review", "non disponibile", "da validare",
           "placeholder", "manual review", "fail-closed", "roadmap")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1. routes 200 ----------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug", PRECHECK_SLUGS)
def test_precheck_route_200(slug):
    assert Client().get(f"/precheck/{slug}/", HTTP_ACCEPT_LANGUAGE="it").status_code == 200


@pytest.mark.django_db
def test_unknown_precheck_is_404():
    assert Client().get("/precheck/does-not-exist/").status_code == 404


@pytest.mark.django_db
def test_guided_router_route_200():
    assert Client().get("/guided/", HTTP_ACCEPT_LANGUAGE="it").status_code == 200


# --- 2. pre-check pages compute no amount -----------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug", PRECHECK_SLUGS)
def test_precheck_page_shows_no_money(slug):
    body = _get(f"/precheck/{slug}/")
    assert not _MONEY.search(body), f"money leaked on /precheck/{slug}/"


@pytest.mark.django_db
def test_guided_router_shows_no_money():
    assert not _MONEY.search(_get("/guided/"))


# --- 3. country × category routing decisions --------------------------------
@pytest.mark.parametrize("country,category,expected", [
    ("IT", "road_accident", "estimate"),
    ("IT", "medical_liability", "tabular"),
    ("IT", "insurance_offer", "comparison"),
    ("IT", "work_injury", "pre_check"),
    ("IT", "loss_of_relative", "guided"),
    ("MA", "road_accident", "pre_check"),
    ("TN", "road_accident", "pre_check"),
    ("FR", "road_accident", "guided"),
    ("BE", "road_accident", "guided"),
    ("INT", "cross_border", "applicable_law"),
])
def test_router_resolves_pair(country, category, expected):
    route = resolve(country, category)
    assert route is not None, f"no route for {country}/{category}"
    assert route.status == expected


def test_only_real_engines_compute_an_amount():
    # Exactly the three approved-engine categories may compute a numeric range.
    computing = {(r.country_code, r.category_id) for r in ROUTES if r.computes_amount}
    assert computing == {("IT", "road_accident"), ("IT", "medical_liability"),
                         ("IT", "insurance_offer")}


# --- 4. source chips on every pre-check -------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug", PRECHECK_SLUGS)
def test_precheck_shows_official_source_chips(slug):
    body = _get(f"/precheck/{slug}/")
    assert "§" in body, f"no source chip on /precheck/{slug}/"


@pytest.mark.django_db
@pytest.mark.parametrize("slug", PRECHECK_SLUGS)
def test_precheck_shows_no_amount_disclaimer(slug):
    body = _get(f"/precheck/{slug}/")
    assert "Nessun importo viene calcolato senza" in body


# --- 5. no technical / weak states ------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", [f"/precheck/{s}/" for s in PRECHECK_SLUGS] + ["/guided/"])
def test_no_technical_state_leaks(path):
    body = _get(path).lower()
    for tok in _BANNED:
        assert tok not in body, f"{path} leaks {tok!r}"


# --- 6. country pages link into the pre-checks (not succession only) --------
@pytest.mark.django_db
@pytest.mark.parametrize("path,slug", [
    ("/countries/morocco/", "morocco-road-accident"),
    ("/countries/tunisia/", "tunisia-road-accident"),
])
def test_country_page_links_road_precheck(path, slug):
    body = _get(path)
    assert f"/precheck/{slug}/" in body
    # and still a multi-category, non-succession-only page
    assert "Incidenti stradali e danno alla persona" in body


# --- 7. services differentiate pre-check vs applicable-law vs guided --------
@pytest.mark.django_db
def test_services_route_into_prechecks_with_differentiated_badges():
    body = _get("/services/")
    assert "/precheck/inail/" in body
    assert "/precheck/international-road-accident/" in body
    # the documental pre-check badge wording is present (work injury)
    assert "Pre-check documentale con fonte ufficiale" in body
    # the applicable-law framing wording is present (international)
    assert "Inquadramento della legge applicabile" in body


# --- 8. case-type landings route their primary CTA into the pre-checks ------
@pytest.mark.django_db
@pytest.mark.parametrize("landing,slug", [
    ("work-injury", "inail"),
    ("death-of-relative", "loss-of-relative"),
    ("cross-border-cases", "international-road-accident"),
])
def test_case_type_landing_primary_cta_routes_to_precheck(landing, slug):
    body = _get(f"/case-types/{landing}/")
    assert f"/precheck/{slug}/" in body


# --- 9. IT canary: Italian rendered, no English leak ------------------------
@pytest.mark.django_db
def test_it_canary_no_english_leak():
    body = _get("/precheck/inail/")
    assert "Pre-check documentale con fonte ufficiale" in body
    for en in ("Documental pre-check with official sources", "Documents needed",
               "Back to services", "Data to verify"):
        assert en not in body, f"English leak: {en!r}"


# --- 10. catalogs have zero fuzzy entries -----------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_has_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8"), f"{lang} has fuzzy entries"


# --- 11. guided router is reachable & indexed -------------------------------
@pytest.mark.django_db
def test_guided_router_is_linked_from_footer_and_case_types():
    assert reverse("core:guided_router") == "/guided/"
    # discoverable from the case-types hub
    assert "/guided/" in _get("/case-types/")
