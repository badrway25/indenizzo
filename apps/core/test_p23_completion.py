"""P23 — guard the completed page-by-page redesign of the remaining pages.

Locks the concrete bespoke sections added to the precheck, countries hub, country,
case-types hub, case-type landing and estimate-result templates so they cannot
quietly regress to generic layouts.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
TEMPLATES = Path(settings.BASE_DIR) / "templates" / "public"


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- Pre-check page + result get bespoke composition -------------------------
@pytest.mark.django_db
def test_precheck_page_has_bespoke_intro_band():
    body = _get("/precheck/inail/")
    assert "Leggiamo le tue risposte e organizziamo la pratica" in body  # "what we'll do" band
    assert body.count("icon-medallion") >= 3  # the 3-point band medallions


@pytest.mark.django_db
def test_precheck_result_has_next_steps_timeline():
    body = Client().post("/precheck/inail/", {"impairment_pct": "10", "medical_cert": "yes"},
                         HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert "Raccogli i documenti elencati sopra" in body  # timeline step 1
    assert 'id="precheck-result"' in body
    assert not _MONEY.search(body)


# --- Countries hub bespoke landing ------------------------------------------
@pytest.mark.django_db
def test_countries_hub_has_hero_and_explainer():
    body = _get("/countries/")
    assert "premium-hero-mini" in body
    assert "Stima o pre-check?" in body          # estimate-or-precheck explainer
    assert "Come scegliamo la fonte" in body     # source-selection note
    assert body.count("<h1") == 1                # single h1


# --- Country pages: FR/BE rich guided sections; MA/TN keep categories --------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/countries/france/", "/countries/belgium/"])
def test_guided_country_has_rich_coverage(path):
    body = _get(path)
    assert "Copertura guidata" in body or "premium-hero-mini" in body
    assert "Responsabilità" in body and "Assicurazione" in body
    assert not _MONEY.search(body)


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/countries/morocco/", "/countries/tunisia/"])
def test_category_country_keeps_categories_and_source_panel(path):
    body = _get(path)
    assert "Categorie coperte" in body
    assert "premium-hero-mini" in body  # new dossier band
    assert "§" in body                  # source chips


# --- Case-types hub + landing -----------------------------------------------
@pytest.mark.django_db
def test_case_types_hub_has_hero_band():
    body = _get("/case-types/")
    assert "premium-hero-mini" in body
    assert body.count("<h1") == 1


@pytest.mark.django_db
def test_case_type_landing_has_structured_sections():
    body = _get("/case-types/work-injury/")
    assert "premium-hero-mini" in body
    assert "Quando si applica" in body  # "when it applies" card


# --- Estimate result shell (file-level: result needs a live simulation) -----
def test_wizard_result_has_premium_shell():
    src = (TEMPLATES / "wizard_result.html").read_text("utf-8")
    assert "premium-hero-mini" in src
    assert "Preliminary result" in src


# --- No regressions on the redesigned pages ---------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", [
    "/countries/", "/countries/morocco/", "/countries/france/", "/case-types/",
    "/case-types/work-injury/", "/precheck/inail/", "/precheck/morocco-road-accident/",
])
def test_redesigned_pages_clean(path):
    body = _get(path)
    assert not _MONEY.search(body)
    low = body.lower()
    for tok in ("in revisione", "non disponibile", "da validare", "roadmap",
                "placeholder", "manual review", "needs review"):
        assert tok not in low, f"{path} leaks {tok!r}"
    # no inline style attribute in the rendered source markup of templates is
    # covered by test_p18; here we just ensure no snake_case slug surfaces.
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)))
    assert not re.search(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b", visible), f"{path} leaks snake_case"


# --- Catalogs fuzzy-free ----------------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
