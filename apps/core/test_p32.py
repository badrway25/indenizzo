"""P32 — guard the premium visual-rescue system.

Source-scan + render guards for: the restored CSS utilities, the unified button
system (no flat raw-utility CTAs), the navbar mega-menu + mobile drawer, the
wrap-tolerant badge, dedicated hero slots, count-up motion, and hygiene.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
SITE_CSS = (BASE / "static" / "css" / "site.css").read_text("utf-8")
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
HEADER = (BASE / "templates" / "partials" / "header.html").read_text("utf-8")
SITE_JS = (BASE / "static" / "js" / "site.js").read_text("utf-8")
PUBLIC = BASE / "templates" / "public"
PARTIALS = BASE / "templates" / "partials"


# --- 1. Restored CSS utilities ---------------------------------------------
@pytest.mark.parametrize("sel", [".truncate", ".min-w-0", ".shrink-0",
                                 ".place-items-center", ".max-w-full"])
def test_overflow_utilities_defined(sel):
    assert sel + " " in SITE_CSS or sel + "{" in SITE_CSS, f"{sel} missing in site.css"


def test_responsive_display_utilities_defined():
    # the navbar relies on these — they were silently missing before P32
    assert r".lg\:flex " in SITE_CSS or r".lg\:flex{" in SITE_CSS
    assert r".lg\:hidden " in SITE_CSS or r".lg\:hidden{" in SITE_CSS


def test_dragover_uses_a_real_token():
    assert "var(--ivory)" not in SITE_CSS  # undefined token removed
    assert ".is-dragover" in SITE_CSS


# --- 2. Unified button system ----------------------------------------------
_FLAT_CTA = re.compile(r"<(?:a|button)\b[^>]*\brounded-full\s+(?:bg-ink-950|bg-gold-500)\b")


def test_no_flat_button_shaped_ctas_in_public_templates():
    offenders = []
    for tpl in list(PUBLIC.glob("*.html")) + list(PARTIALS.glob("*.html")):
        src = tpl.read_text("utf-8")
        if _FLAT_CTA.search(src):
            offenders.append(tpl.name)
    assert not offenders, f"flat raw-utility CTAs remain: {offenders}"


def test_premium_button_variants_exist():
    for v in (".premium-btn-primary", ".premium-btn-secondary", ".premium-btn-gold",
              ".premium-btn-ghost", ".premium-btn-on-dark", ".premium-chip"):
        assert v in DS_CSS, f"{v} missing"


def test_consultation_cta_uses_system():
    cta = (PARTIALS / "cta_consultation.html").read_text("utf-8")
    assert "premium-btn premium-btn-primary" in cta
    assert "rounded-full bg-ink-950" not in cta


# --- 3. Navbar mega-menu + mobile drawer -----------------------------------
def test_navbar_has_dropdowns_and_drawer():
    assert "nav-menu" in HEADER and "nav-group" in HEADER       # desktop dropdowns
    assert 'data-drawer="nav"' in HEADER                         # mobile drawer
    assert 'data-drawer-open="nav"' in HEADER                    # hamburger opener
    assert "nav-desktop" in HEADER and "nav-mobile" in HEADER    # responsive toggles


def test_drawer_is_keyed_and_generalized():
    # the source-list drawer was re-keyed so the nav drawer can coexist
    wr = (PUBLIC / "wizard_result.html").read_text("utf-8")
    assert 'data-drawer="sources"' in wr
    assert "data-drawer-open" in SITE_JS and 'getAttribute("data-drawer")' in SITE_JS


def test_nav_responsive_classes_defined():
    assert ".nav-desktop" in DS_CSS and ".nav-mobile" in DS_CSS


# --- 4. Wrap-tolerant badge ------------------------------------------------
def test_badge_wraps_instead_of_clipping():
    block = DS_CSS.split(".premium-badge {", 1)[1].split("}", 1)[0]
    assert "white-space: normal" in block
    assert "overflow-wrap: anywhere" in block


# --- 5. Dedicated hero imagery ---------------------------------------------
def test_new_hero_slots_registered():
    from apps.core import pexels
    purposes = {s["purpose"] for s in pexels.SITE_IMAGE_SLOTS}
    for p in ("documents_hero", "sources_hero", "case_types_hero",
              "result_hero", "guided_hero"):
        assert p in purposes, f"{p} slot missing"


def test_new_hero_overrides_pinned():
    import json
    data = json.loads((BASE / "config" / "pexels_image_overrides.json").read_text("utf-8"))
    slots = data["slots"]
    for p in ("documents_hero", "sources_hero", "case_types_hero",
              "result_hero", "guided_hero"):
        assert slots.get(p, {}).get("photo_id"), f"{p} not pinned"


def test_heroes_wired_in_views():
    views = (BASE / "apps" / "core" / "views.py").read_text("utf-8")
    assert '_pexels_hero(request, "documents_hero")' in views
    assert '_pexels_hero(request, "sources_hero")' in views
    assert '_pexels_hero(request, "guided_hero")' in views
    assert '_pexels_hero(request, "case_types_hero")' in views


def test_image_sources_doc_exists():
    docs = list((BASE / "docs" / "audits").glob("P32_IMAGE_SOURCES_*.md"))
    assert docs, "image-sources attribution doc missing"


# --- 6. Count-up motion ----------------------------------------------------
def test_countup_behaviour_and_markup():
    assert "initCountUp" in SITE_JS and "data-count-to" in SITE_JS
    assert "prefersReduced" in SITE_JS  # reduced-motion respected
    home = (PUBLIC / "home.html").read_text("utf-8")
    assert "data-count-to" in home


def test_countries_grid_has_reveal():
    countries = (PUBLIC / "countries.html").read_text("utf-8")
    assert "data-reveal" in countries


# --- 7. Hygiene ------------------------------------------------------------
def test_no_inline_style_in_changed_templates():
    for name in ("header.html",):
        src = (PARTIALS / name).read_text("utf-8")
        assert "style=" not in src, f"{name} has an inline style attribute"


def test_no_external_cdn_in_header():
    assert "cdn." not in HEADER and "unpkg" not in HEADER and "googleapis" not in HEADER


def test_coming_soon_wording_removed():
    ct = (PUBLIC / "case_types.html").read_text("utf-8")
    assert "Coming next" not in ct
    assert "Other areas" in ct


# --- 8. Regression: flows + i18n + RTL + canaries --------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/documents/", "/documents/upload/", "/sources/",
                                  "/guided/", "/case-types/", "/countries/", "/precheck/inail/"])
def test_public_pages_200(path):
    assert Client().get(path).status_code == 200


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/", "/ar/documents/", "/ar/sources/", "/ar/case-types/"])
def test_rtl_pages_200(path):
    resp = Client().get(path, HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200
    assert 'dir="rtl"' in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_document_upload_flow_still_works():
    from django.core.files.uploadedfile import SimpleUploadedFile
    f = SimpleUploadedFile("offerta.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    # Unique REMOTE_ADDR so the shared public-POST rate-limit counter (accumulated
    # across the P30/P31/P32 upload tests in a full run) never 429s this one.
    body = Client().post("/documents/upload/", {"document": [f], "analysis_consent": "on",
                                                "website": ""},
                         REMOTE_ADDR="203.0.113.32").content.decode()
    assert 'id="document-result"' in body


def test_openai_fallback_still_works():
    from apps.core import document_ai as dai
    a = dai.analyze_document(filename="referto.pdf", mime="application/pdf", size=1)
    assert a.provider == "local"


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
