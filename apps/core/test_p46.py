"""P46 — guard the pixel-level premium frontend acceptance: no "●" dot glyph or
"§" source glyph in public pages, full-bleed hero, navbar icons, premium select
trigger, clock/source icons — plus the unchanged legal guardrails."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
ICON_TPL = (BASE / "templates" / "partials" / "_icon.html").read_text("utf-8")
HEADER_TPL = (BASE / "templates" / "partials" / "header.html").read_text("utf-8")
HERO_TPL = (BASE / "templates" / "partials" / "_premium_hero_image.html").read_text("utf-8")
AUDITS = BASE / "docs" / "audits"


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1-2. No ugly dot badges ----------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/guided/", "/sources/", "/precheck/inail/",
                                  "/countries/", "/documentation/", "/services/"])
def test_no_bullet_glyph_in_public_pages(path):
    assert "●" not in _get(path), f"{path} still renders the ● glyph"


def test_premium_badge_dot_is_css_not_glyph():
    # the badge dot is a CSS-drawn circle, not the "●" font glyph
    block = DS_CSS.split(".premium-badge::before", 1)[1].split("}", 1)[0]
    assert 'content: ""' in block
    assert "●" not in block
    assert ".badge-dot" in DS_CSS


# --- 4. No § source glyph; sources shown with an icon ----------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/guided/", "/sources/", "/precheck/inail/", "/countries/"])
def test_no_section_sign_glyph(path):
    assert "§" not in _get(path), f"{path} still renders the § glyph"


# --- 3/6. Time + source icons exist in the set -----------------------------
def test_icon_set_has_clock_and_book():
    for name in ("clock", "book-open", "file-text", "calendar-check"):
        assert f'name == "{name}"' in ICON_TPL


def test_guided_time_label_uses_clock():
    # the route "Time" label carries the clock icon
    assert 'name="clock"' in (BASE / "templates" / "public" / "guided_router.html").read_text("utf-8")


# --- 5/6. Navbar icons + mega-menu preview ---------------------------------
@pytest.mark.django_db
def test_navbar_top_items_have_icons():
    assert HEADER_TPL.count("nav-link__ico") >= 5
    assert ".nav-link__ico" in DS_CSS
    body = _get("/")
    assert body.count("nav-link__ico") >= 5
    assert "nav-menu__preview" in body  # mega-menu mini-preview (P44)


# --- 7. Premium select trigger (appearance + caret) ------------------------
def test_premium_select_trigger_is_styled():
    block = DS_CSS.split(".premium-select,\n.field-select {", 1)
    assert len(block) > 1, "premium select trigger rule missing"
    rule = block[1].split("}", 1)[0]
    assert "appearance: none" in rule
    assert "background-image" in rule  # custom caret
    assert '[dir="rtl"] .premium-select' in DS_CSS  # RTL-aware caret


# --- 8. Full-bleed hero on key pages ---------------------------------------
def test_hero_partial_is_fullbleed():
    assert "premium-hero-fullbleed" in HERO_TPL
    assert "premium-hero-media" in HERO_TPL
    assert ".premium-hero-fullbleed" in DS_CSS


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/sources/", "/guided/", "/services/", "/documents/"])
def test_pages_use_fullbleed_hero(path):
    # The test harness empties MEDIA_ROOT, so the hero partial only emits its
    # markup when the Pexels lookup resolves — patch it to a stand-in entry.
    from unittest.mock import patch

    fake = {"local_path": "pexels/test.jpg", "alt": "test"}
    with patch("apps.core.pexels.get_image_for_slot", return_value=fake):
        assert "premium-hero-fullbleed" in _get(path)


# --- 11/12. No banned words; buttons use premium classes -------------------
_BANNED = ["engine", "fallback", "pipeline", "crm", "debug", "approval",
           "manual review", "feature flag"]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/guided/", "/sources/", "/documentation/"])
def test_no_banned_words(path):
    low = re.sub(r"<[^>]+>", " ", _get(path)).lower()
    for w in _BANNED:
        assert w not in low, f"{path} exposes {w!r}"


@pytest.mark.django_db
def test_buttons_use_premium_classes():
    body = _get("/")
    assert "premium-btn" in body


# --- 14-16. Legal guardrails -----------------------------------------------
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
    assert not re.search(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)", _get(path))


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


# --- 17-19. docs + i18n + RTL ----------------------------------------------
def test_p46_audit_doc_exists():
    assert (AUDITS / "P46_PIXEL_LEVEL_FRONTEND_AUDIT_2026-06-29.md").is_file()


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/sources/", "/ar/guided/", "/ar/documentation/"])
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
                         REMOTE_ADDR="203.0.113.81").content.decode()
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
