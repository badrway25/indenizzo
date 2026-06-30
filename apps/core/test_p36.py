"""P36 — guard the final premium acceptance pass + honest estimate stance.

Guards the home intent section (imagery + visible icons), the new Pexels slots,
the audit docs, simple copy, and — critically — that NO unvalidated monetary engine
was fabricated (the platform's first rule: no figure without a validated source).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
HOME = (BASE / "templates" / "public" / "home.html").read_text("utf-8")
AUDITS = BASE / "docs" / "audits"


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1. Home intent section (imagery + cards) ------------------------------
def test_intent_section_markup():
    assert "intent-card" in HOME
    assert "intent-card__media" in HOME and "intent-card__icon" in HOME
    assert "What would you like to do?" in HOME


@pytest.mark.django_db
def test_intent_section_renders_four_image_cards():
    body = _get("/")
    assert body.count('class="intent-card"') == 4
    # each card carries a section image
    assert body.count("intent-card__media") >= 4


def test_intent_card_css_defined():
    assert ".intent-card" in DS_CSS and ".intent-card__media" in DS_CSS


def test_intent_icon_is_not_clipped_by_media():
    # the icon must live in the body with a negative margin (overlap), NOT be
    # absolutely positioned inside the overflow:hidden media (which clipped it).
    block = DS_CSS.split(".intent-card__icon {", 1)[1].split("}", 1)[0]
    assert "margin-top" in block
    assert "position: absolute" not in block
    # markup: the icon span sits inside the card body
    body_part = HOME.split('class="intent-card__body"', 1)[1][:400]
    assert "intent-card__icon" in body_part


# --- 2. New Pexels imagery (slots, pins, attribution) ----------------------
def test_new_intent_slots_registered():
    from apps.core import pexels
    purposes = {s["purpose"] for s in pexels.SITE_IMAGE_SLOTS}
    for p in ("intent_estimate", "intent_offer", "intent_documents", "intent_law"):
        assert p in purposes, f"{p} slot missing"


def test_new_intent_images_pinned():
    data = json.loads((BASE / "config" / "pexels_image_overrides.json").read_text("utf-8"))
    for p in ("intent_estimate", "intent_offer", "intent_documents", "intent_law"):
        assert data["slots"].get(p, {}).get("photo_id"), f"{p} not pinned"


def test_p36_image_sources_doc_lists_new_images():
    doc = next(AUDITS.glob("P36_IMAGE_SOURCES_*.md")).read_text("utf-8")
    for slot in ("intent_estimate", "intent_offer", "intent_documents", "intent_law"):
        assert slot in doc


# --- 3. Audit docs ----------------------------------------------------------
def test_estimate_coverage_audit_exists():
    docs = list(AUDITS.glob("P36_ESTIMATE_COVERAGE_AND_OFFICIAL_SOURCES_*.md"))
    assert docs
    txt = docs[0].read_text("utf-8")
    assert "usable_for_engine" in txt and "approval_needed" in txt


def test_visual_acceptance_audit_exists():
    assert list(AUDITS.glob("P36_PREMIUM_VISUAL_ACCEPTANCE_AUDIT_*.md"))


# --- 4. No fabricated monetary engine --------------------------------------
def test_no_unvalidated_engine_was_fabricated():
    """The available engines must stay exactly the 8 validated ones. If a new
    estimate is ever added it MUST come with its own canary — this guard fails
    loudly if an engine appears without updating the expected set here."""
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
    assert available == expected, f"engine set changed: {available ^ expected}"


def test_approval_needed_sources_are_not_engine_grade():
    from apps.core import official_sources as osrc
    by_id = {s.source_id: s for s in osrc.all_sources()}
    for sid in ("it-dm-45-2019", "ma-dahir-1-84-177", "tn-code-assurances"):
        s = by_id.get(sid)
        if s is None:
            continue
        status = str(getattr(s, "validation_status", getattr(s, "status", "")))
        assert status != "usable_for_engine", f"{sid} must not be engine-grade yet"


# --- 5. Hygiene + simple copy ----------------------------------------------
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
    assert not _MONEY.search(body), f"{path} shows a money figure without an engine"


def test_no_inline_styles_or_cdn_in_home():
    assert "style=" not in HOME
    assert "cdn." not in HOME and "googleapis" not in HOME


def test_no_heavy_intent_images_committed():
    # the intent WebP live under gitignored media/ — none must be tracked
    import subprocess
    out = subprocess.run(["git", "ls-files", "media/pexels/intent_"], cwd=BASE,
                         capture_output=True, text=True).stdout
    assert "intent_" not in out, "intent images must not be committed"


# --- 6. Regression: RTL / canaries / i18n / upload -------------------------
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
                         REMOTE_ADDR="203.0.113.91").content.decode()
    assert 'id="document-result"' in body


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
