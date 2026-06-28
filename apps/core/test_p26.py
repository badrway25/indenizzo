"""P26 — guard the premium hub-page redesign.

Locks the services journey-selector groups + group CTAs, the case-types thematic
navigator, and the enriched countries hub (categories + source, no country
reduced to inheritance), plus the home funnel links — so the hubs cannot regress
to generic card grids.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
_GENERIC = ("Percorso legale assistito", "Esame legale dedicato")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- Services hub: grouped journey selector --------------------------------
@pytest.mark.django_db
def test_services_hub_has_premium_groups_and_ctas():
    body = _get("/services/")
    # three section groups with their own CTA
    assert "Stime disponibili" in body            # Available estimates (merged)
    assert "Pre-check documentali" in body
    assert "Avvia una stima" in body              # group CTA → guided
    assert "Inquadra il tuo caso" in body         # cross-border group CTA
    assert body.count("<h1") == 1


@pytest.mark.django_db
def test_services_calculable_cards_have_no_generic_badge():
    body = _get("/services/")
    for tok in _GENERIC:
        assert tok not in body, f"/services/ shows {tok!r}"
    assert not _MONEY.search(body)


# --- Countries hub: categories + source, never inheritance-only ------------
@pytest.mark.django_db
def test_countries_hub_shows_categories_source_and_cta():
    body = _get("/countries/")
    assert "Dahir 1-84-177" in body and "Loi 2005-86" in body  # main sources
    assert "Incidente stradale" in body                         # category chip
    from django.urls import reverse
    assert f'href="{reverse("core:country_morocco")}"' in body  # per-country CTA
    assert not _MONEY.search(body)


@pytest.mark.django_db
def test_countries_hub_does_not_reduce_morocco_tunisia_to_inheritance():
    body = _get("/countries/")
    # Morocco/Tunisia must surface road accident, not only succession.
    # The category chip "Incidente stradale" appears for MA/TN coverage.
    assert body.count("Incidente stradale") >= 3  # IT + MA + TN at least


# --- Case-types hub: thematic navigator ------------------------------------
@pytest.mark.django_db
def test_case_types_hub_is_a_grouped_navigator():
    body = _get("/case-types/")
    assert "Seleziona il tipo di danno" in body
    # thematic group labels
    for label in ("Danno alla persona", "Famiglia e decesso", "Successioni"):
        assert label in body, f"case-types missing group {label!r}"
    assert "Cosa fornisci" in body   # per-card "you'll provide" hint
    assert body.count("<h1") == 1


@pytest.mark.django_db
def test_case_types_calculable_cards_have_no_generic_tag():
    body = _get("/case-types/")
    for tok in _GENERIC:
        assert tok not in body
    # road + medical read as estimates
    assert "Stima da fonte ufficiale" in body
    assert "Stima tabellare del danno biologico" in body


# --- Home funnel links the three hubs --------------------------------------
@pytest.mark.django_db
def test_home_funnel_links_the_hubs():
    body = _get("/")
    from django.urls import reverse
    for url in (reverse("core:services"), reverse("core:guided_router"), reverse("core:countries")):
        assert f'href="{url}"' in body, f"home does not funnel to {url}"


# --- No regressions across the hubs ----------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/services/", "/countries/", "/case-types/"])
def test_hub_pages_clean(path):
    body = _get(path)
    assert not _MONEY.search(body)
    low = body.lower()
    for tok in ("in revisione", "non disponibile", "da validare", "roadmap",
                "placeholder", "manual review", "needs review"):
        assert tok not in low, f"{path} leaks {tok!r}"
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                     re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)))
    assert not re.search(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b", visible), f"{path} leaks snake_case"


# --- Calculator registry unchanged (no engine touched) ---------------------
def test_calculator_registry_unchanged():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    # the three live IT engines must still be registered
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs
    assert ("IT-NATIONAL", "inheritance_basic") in pairs


# --- Catalogs fuzzy-free ----------------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
