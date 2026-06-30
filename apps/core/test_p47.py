"""P47 — guard the accessible custom-select system (progressive enhancement),
the honest "why no amount" public callout + sources gap map, and the unchanged
legal guardrails."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
SITE_JS = (BASE / "static" / "js" / "site.js").read_text("utf-8")
AUDITS = BASE / "docs" / "audits"
_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1-5. Custom select: JS, CSS, fallback, sync, keyboard ----------------
def test_custom_select_js_and_css_exist():
    assert "initCustomSelect" in SITE_JS
    assert "initCustomSelect();" in SITE_JS  # registered in ready()
    for cls in (".premium-select-enhanced", ".premium-select-trigger",
                ".premium-select-menu", ".premium-select-option",
                ".premium-select-option--selected", ".premium-select-check"):
        assert cls in DS_CSS, f"{cls} missing from CSS"


def test_custom_select_is_progressive_enhancement():
    # The native <select> stays in the DOM (source of truth); JS only enhances it.
    assert 'querySelectorAll("select.premium-select, select.field-select")' in SITE_JS
    assert "premium-select-native-hidden" in SITE_JS  # native hidden, not removed


def test_custom_select_syncs_value_and_dispatches_change():
    # choosing an option sets the native select value and fires `change`
    assert "sel.selectedIndex = i" in SITE_JS
    assert 'sel.dispatchEvent(new Event("change"' in SITE_JS


def test_custom_select_has_keyboard_and_aria():
    for token in ('aria-haspopup', '"listbox"', 'aria-expanded', 'aria-selected',
                  '"ArrowDown"', '"ArrowUp"', '"Enter"', '"Escape"',
                  'aria-activedescendant'):
        assert token in SITE_JS, f"custom select missing {token}"


@pytest.mark.django_db
def test_enhanced_forms_still_render_native_select():
    # without JS the native premium-select must still be present (fallback)
    body = _get("/sources/")
    assert "premium-select" in body or "field-select" in body


# --- 6-8. Source display / icons / no dot badge ----------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/guided/", "/sources/", "/countries/"])
def test_no_dot_or_section_glyph(path):
    body = _get(path)
    assert "●" not in body and "§" not in body


def test_icon_set_has_status_and_document_icons():
    icons = (BASE / "templates" / "partials" / "_icon.html").read_text("utf-8")
    for name in ("clock", "book-open", "file-text", "globe", "shield-check"):
        assert f'name == "{name}"' in icons


# --- 9-10. Buttons + cards carry interaction states ------------------------
def test_buttons_have_hover_focus_states():
    assert ".premium-btn" in DS_CSS
    assert ":focus-visible" in DS_CSS
    assert ":hover" in DS_CSS


def test_cards_have_hover():
    assert ".premium-card-hover" in DS_CSS or ".matrix-card:hover" in DS_CSS


# --- 11. Motion respects reduced-motion ------------------------------------
def test_reduced_motion_block_exists():
    assert "@media (prefers-reduced-motion: reduce)" in DS_CSS


# --- 12-13. Gap-map doc + public "why no amount" explanation ---------------
def test_missing_sources_gap_map_exists():
    doc = AUDITS / "P47_MISSING_OFFICIAL_SOURCES_FOR_ESTIMATES_2026-06-30.md"
    assert doc.is_file()
    text = doc.read_text("utf-8")
    for c in ("Italy", "Morocco", "Tunisia", "France", "Belgium", "EU"):
        assert c in text


def test_global_audit_doc_exists():
    assert (AUDITS / "P47_GLOBAL_PREMIUM_MICRO_UX_AUDIT_2026-06-30.md").is_file()


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/services/", "/guided/", "/"])
def test_public_why_no_amount_explanation(path):
    body = _get(path)
    assert "why-no-amount" in body
    assert "Perché alcune sezioni non mostrano un importo" in body  # it copy


# --- 14-16. Legal guardrails -----------------------------------------------
_BANNED = ["engine", "fallback", "pipeline", "crm", "debug", "approval",
           "manual review", "feature flag"]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/guided/", "/sources/", "/documentation/"])
def test_no_banned_words(path):
    low = re.sub(r"<[^>]+>", " ", _get(path)).lower()
    for w in _BANNED:
        assert w not in low, f"{path} exposes {w!r}"


def test_matrix_truthful():
    from apps.core.templatetags.estimate_tags import _MATRIX, ST_ESTIMATE

    total = sum(1 for i, (_c, rows) in enumerate(_MATRIX)
                for _cat, s in rows if s == ST_ESTIMATE and i == 0)
    other = sum(1 for i, (_c, rows) in enumerate(_MATRIX)
                for _cat, s in rows if s == ST_ESTIMATE and i != 0)
    assert total == 3 and other == 0


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/guided/", "/sources/", "/documents/"])
def test_no_money_engine_less(path):
    assert not _MONEY.search(_get(path))


def test_engine_set_unchanged():
    from apps.calculators.registry import list_available_calculators

    available = {(j, c) for j, c in list_available_calculators()}
    assert available == {
        ("BE-NATIONAL", "road_accident_bodily_injury"),
        ("FR-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "inheritance_basic"),
        ("IT-NATIONAL", "medical_liability_biological_damage"),
        ("IT-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "road_accident_microlesions"),
        ("MA-NATIONAL", "international_inheritance"),
        ("TN-NATIONAL", "international_inheritance"),
    }


# --- 18-19. i18n + RTL -----------------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/guided/", "/ar/sources/", "/ar/documentation/"])
def test_rtl_routes_200(path):
    resp = Client().get(path, HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200 and 'dir="rtl"' in resp.content.decode()


# --- 20-23. Journeys + canaries --------------------------------------------
@pytest.mark.django_db
def test_document_upload_works():
    from django.core.files.uploadedfile import SimpleUploadedFile

    f = SimpleUploadedFile("o.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    body = Client().post("/documents/upload/", {"document": [f], "analysis_consent": "on",
                                                "website": ""},
                         REMOTE_ADDR="203.0.113.91").content.decode()
    assert 'id="document-result"' in body


@pytest.mark.django_db
def test_sources_and_search_work():
    assert Client().get("/sources/").status_code == 200
    assert Client().get("/search/?q=incidente").status_code == 200


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators

    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs
