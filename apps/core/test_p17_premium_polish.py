"""P17 — guard public copy sanitisation, readiness depth and premium polish.

No technical slug/enum may reach rendered public copy; the language switcher
shows full language names with a globe; pre-check results carry a structured
readiness (percentage, potential path, what-unlocks) and a premium sidebar
(sources / documents / next step); and no amount or technical state leaks.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

from apps.core import precheck_engine as pe
from apps.core.precheck import get_precheck
from apps.core.public_labels import humanize

_TAG = re.compile(r"<[^>]+>", re.S)
_SCRIPTSTYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_SNAKE = re.compile(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b")
_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
_ENUMS = ("road_accident_bodily_injury", "medical_malpractice", "work_injury",
          "loss_of_relative", "morocco_road_accident", "tunisia_road_accident",
          "international_road_accident", "death_of_relative", "international_inheritance")

PUBLIC_ROUTES = ["/", "/services/", "/countries/", "/case-types/", "/guided/",
                 "/countries/morocco/", "/countries/tunisia/", "/countries/italy/",
                 "/precheck/inail/", "/precheck/loss-of-relative/",
                 "/precheck/morocco-road-accident/", "/precheck/tunisia-road-accident/",
                 "/precheck/international-road-accident/"]
LANGS = ["it", "fr", "en", "ar"]


def _visible(html):
    html = _SCRIPTSTYLE.sub(" ", html)
    return re.sub(r"\s+", " ", _TAG.sub(" ", html))


def _get(path, lang="it"):
    url = f"/{lang}{path}" if lang != "it" else path
    return Client().get(url, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


def _post(slug, data):
    return Client().post(f"/precheck/{slug}/", data, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")


# --- 1 & 2. no technical slug / enum in rendered public copy ----------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_ROUTES)
@pytest.mark.parametrize("lang", LANGS)
def test_no_snake_case_or_enum_in_visible_text(path, lang):
    text = _visible(_get(path, lang))
    snake = _SNAKE.findall(text)
    assert not snake, f"{lang} {path} leaks snake_case: {snake[:5]}"
    for e in _ENUMS:
        assert e not in text, f"{lang} {path} leaks enum {e!r}"


def test_humanize_never_returns_snake_case():
    for code in _ENUMS + ("some_unknown_code",):
        assert "_" not in str(humanize(code)), code


# --- 3 & 4. premium language switcher ---------------------------------------
@pytest.mark.django_db
def test_language_switcher_full_names_and_globe():
    body = _get("/", "it")
    for name in ("Italiano", "Français", "English", "العربية"):
        assert name in body, name
    assert 'aria-label' in body
    # a globe icon ships in the switcher form (the chevron + globe are inline SVG)
    assert "Language switcher" in body or "switcher" in body.lower()


@pytest.mark.django_db
def test_language_switcher_select_has_label():
    body = _get("/", "it")
    assert 'id="lang-switcher"' in body
    assert 'for="lang-switcher"' in body  # accessible label


# --- 6. pre-check result has the premium sidebar + structured readiness ------
@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["inail", "morocco-road-accident", "loss-of-relative"])
def test_precheck_has_sidebar_and_readiness(slug):
    # GET shows the sidebar (sources / documents / next step).
    body = _get(f"/precheck/{slug}/")
    assert "premium-sidebar-sticky" in body
    assert "M12 7v14" in body  # book-open source icon (P46 replaced §)  # source chips
    # POST surfaces the documental readiness meter.
    posted = _post(slug, {"injury_or_death": "injury", "country": "IT",
                          "medical_cert": "yes", "civil_docs": "yes"})
    assert "data-readiness-fill" in posted


# --- 7 & 8. cards use premium classes + chips -------------------------------
@pytest.mark.django_db
def test_guided_cards_are_premium():
    body = _get("/guided/")
    assert "premium-card" in body
    assert "premium-card-hover" in body


# --- 10-13. richer readiness in the engine ----------------------------------
def test_inail_readiness_detail():
    r = pe.evaluate(get_precheck("inail"), {"impairment_pct": "10", "medical_cert": "yes",
                                            "employer_docs": "yes", "event_date": "2024-01-01", "age": "40"})
    assert r.potential_path == pe._PATH_INAIL
    assert pe._UNLOCK_INAIL in r.unlocking_data
    assert 0 < r.readiness_pct <= 100
    assert r.has_numeric_estimate is False


def test_morocco_readiness_detail():
    r = pe.evaluate(get_precheck("morocco-road-accident"),
                    {"injury_or_death": "injury", "ipp_known": "yes", "income_documentable": "yes"})
    assert r.potential_path == pe._PATH_MA
    assert pe._UNLOCK_MA in r.unlocking_data


def test_tunisia_readiness_detail():
    r = pe.evaluate(get_precheck("tunisia-road-accident"),
                    {"injury_or_death": "injury", "ipp_known": "yes"})
    assert r.potential_path == pe._PATH_TN
    assert pe._UNLOCK_TN in r.unlocking_data


def test_loss_readiness_detail():
    r = pe.evaluate(get_precheck("loss-of-relative"), {"country": "IT", "civil_docs": "yes"})
    assert r.potential_path == pe._PATH_PARENTAL
    assert r.unlocking_data
    assert r.has_numeric_estimate is False


# --- 14. no money on any engine-less pre-check result -----------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug,data", [
    ("inail", {"impairment_pct": "12", "medical_cert": "yes"}),
    ("morocco-road-accident", {"injury_or_death": "death", "ipp_known": "yes",
                               "income_documentable": "yes", "liability_estimate": "full", "heirs": "yes"}),
    ("tunisia-road-accident", {"injury_or_death": "injury", "ipp_known": "yes", "income_documentable": "yes"}),
])
def test_no_money_in_readiness_result(slug, data):
    assert not _MONEY.search(_post(slug, data))


# --- 15. IT road canary still estimates -------------------------------------
@pytest.mark.django_db
def test_italy_road_canary():
    assert Client().get("/wizard/it/road-accident/", HTTP_ACCEPT_LANGUAGE="it").status_code == 200


# --- 16 & 17. no technical / weak state on public pages ---------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/case-types/", "/guided/", "/precheck/inail/", "/services/"])
def test_no_technical_state(path):
    text = _get(path).lower()
    for tok in ("in revisione", "needs review", "non disponibile", "da validare",
                "manual review", "fail-closed", "placeholder", "roadmap"):
        assert tok not in text, f"{path} leaks {tok!r}"


# --- 18. catalogs fuzzy-free ------------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
