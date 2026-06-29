"""P37 — guard the mega-menu, the fixed mobile drawer, and the honest source stance."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
HEADER = (BASE / "templates" / "partials" / "header.html").read_text("utf-8")
AUDITS = BASE / "docs" / "audits"


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1. Mega-menu panels with icons ----------------------------------------
def test_megamenu_css_defined():
    for cls in (".nav-menu__item", ".nav-menu__ico", ".nav-menu__cta", ".nav-menu__desc"):
        assert cls in DS_CSS, f"{cls} missing"


@pytest.mark.django_db
def test_megamenu_renders_icon_panels():
    body = _get("/")
    assert body.count("nav-menu__item") >= 15      # icon rows across the panels
    assert body.count("nav-menu__ico") >= 15        # each row has an icon
    assert body.count("nav-menu__cta") >= 4         # a panel CTA per main menu
    assert body.count("nav-menu__desc") >= 15       # mini-descriptions


# --- 2. Mobile drawer (fixed: full height, outside the header) -------------
def test_drawer_is_full_height():
    block = DS_CSS.split(".js .drawer {", 1)[1].split("}", 1)[0]
    assert "100dvh" in block or "100vh" in block, "drawer must be full viewport height"


@pytest.mark.django_db
def test_drawer_is_outside_header():
    """The backdrop-filter on the header creates a containing block that would trap a
    fixed-positioned drawer; the drawer must render AFTER </header>."""
    body = _get("/")
    assert "</header>" in body and 'id="nav-drawer"' in body
    assert body.index("</header>") < body.index('id="nav-drawer"')


@pytest.mark.django_db
def test_drawer_mirrors_all_sections():
    body = _get("/")
    # the drawer carries every section (Stime/Documenti/Paesi/Fonti structure)
    drawer = body.split('id="nav-drawer"', 1)[1]
    assert drawer.count("nav-drawer__section") >= 4
    assert "nav-drawer__link" in drawer
    assert 'data-drawer-open="nav"' in body  # the hamburger opener


# --- 3. Honest source stance (no fabrication) ------------------------------
def test_source_validation_queue_doc_exists():
    docs = list(AUDITS.glob("P37_OFFICIAL_SOURCE_VALIDATION_QUEUE_*.md"))
    assert docs
    txt = docs[0].read_text("utf-8")
    assert "approval_needed" in txt and "INAIL" in txt


def test_no_unvalidated_engine_was_fabricated():
    from apps.calculators.registry import list_available_calculators
    available = {(j, c) for j, c in list_available_calculators()}
    expected = {
        ("BE-NATIONAL", "road_accident_bodily_injury"),
        ("FR-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "inheritance_basic"),
        ("IT-NATIONAL", "medical_liability_biological_damage"),
        ("IT-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "road_accident_microlesions"),
        ("MA-NATIONAL", "international_inheritance"),
        ("TN-NATIONAL", "international_inheritance"),
    }
    assert available == expected


# --- 4. Hygiene -------------------------------------------------------------
def test_playwright_artifacts_gitignored():
    gi = (BASE / ".gitignore").read_text("utf-8")
    assert ".playwright-mcp" in gi


_BANNED = ["pipeline", "feature flag", "engine-less", "manual review",
           "fallback", "debug", "readiness", "result kind"]
_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/documents/", "/sources/", "/guided/", "/case-types/"])
def test_no_banned_words_and_no_money_engineless(path):
    body = _get(path)
    low = re.sub(r"<[^>]+>", " ", body).lower()
    for w in _BANNED:
        assert w not in low, f"{path} exposes {w!r}"
    assert not _MONEY.search(body), f"{path} shows money without an engine"


def test_no_inline_styles_or_cdn_in_header():
    assert "style=" not in HEADER
    assert "cdn." not in HEADER and "googleapis" not in HEADER


# --- 5. Regression: RTL / canaries / i18n / upload -------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/", "/ar/documents/", "/ar/sources/"])
def test_rtl_pages_200(path):
    resp = Client().get(path, HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200 and 'dir="rtl"' in resp.content.decode()


@pytest.mark.django_db
def test_document_upload_still_works():
    from django.core.files.uploadedfile import SimpleUploadedFile
    f = SimpleUploadedFile("offerta.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    body = Client().post("/documents/upload/", {"document": [f], "analysis_consent": "on",
                                                "website": ""},
                         REMOTE_ADDR="203.0.113.99").content.decode()
    assert 'id="document-result"' in body


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
