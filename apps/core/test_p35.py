"""P35 — guard the human-first premium UX (forms, navbar shell, simple copy).

Source-scan + render guards: the premium form system, the distinct navy navbar
shell, simple human home copy, no banned technical words in public copy, plus the
standing hygiene gates (no flat CTA, no inline styles, no money engine-less, RTL).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
HEADER = (BASE / "templates" / "partials" / "header.html").read_text("utf-8")
PUBLIC = BASE / "templates" / "public"


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


def _visible(html):
    no_sc = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", no_sc))


# --- 1. Premium form system -------------------------------------------------
@pytest.mark.parametrize("cls", [
    ".premium-form", ".premium-form-section", ".premium-field", ".premium-label",
    ".premium-input", ".premium-select", ".premium-textarea",
    ".premium-checkbox-card", ".premium-radio-card", ".premium-form-actions",
    ".premium-form-help", ".premium-form-error",
])
def test_premium_form_classes_defined(cls):
    assert cls in DS_CSS, f"{cls} missing in design-system.css"


def test_form_actions_separated_from_fields():
    # the actions row carries a top divider + margin so the button is never cramped
    block = DS_CSS.split(".premium-form-actions {", 1)[1].split("}", 1)[0]
    assert "border-top" in block and "padding-top" in block


@pytest.mark.parametrize("tpl", ["documents_upload.html", "precheck.html", "contact.html"])
def test_key_forms_use_premium_system(tpl):
    src = (PUBLIC / tpl).read_text("utf-8")
    assert "premium-form-actions" in src, f"{tpl}: submit not in premium-form-actions"
    assert "premium-select" in src or "premium-input" in src, f"{tpl}: no premium fields"


# --- 2. Distinct premium navbar shell ---------------------------------------
def test_navbar_has_distinct_shell():
    block = DS_CSS.split(".site-header {", 1)[1].split("}", 1)[0]
    assert "background" in block and "box-shadow" in block  # not flat / same as page
    assert ".site-header .nav-link" in DS_CSS  # links re-coloured for the dark shell
    assert "brand-mark" in HEADER  # distinct brand treatment


def test_header_not_using_old_ivory_bg():
    assert "bg-sand-50/90" not in HEADER


# --- 3. Simple human copy ---------------------------------------------------
def test_home_has_simple_simulation_copy():
    src = (PUBLIC / "home.html").read_text("utf-8")
    assert "Simulate your case and prepare the right documents." in src
    assert "Start the simulation" in src


@pytest.mark.django_db
def test_home_renders_simple_copy_it():
    body = _get("/")
    assert "Simula il tuo caso" in body
    assert "Inizia la simulazione" in body


# --- 4. No banned technical words in public copy ----------------------------
_BANNED = ["pipeline", "feature flag", "engine-less", "manual review",
           "fallback", "debug", "readiness", "result kind", "source metadata"]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/documents/", "/documents/upload/", "/sources/",
                                  "/guided/", "/contact/", "/precheck/inail/", "/case-types/"])
def test_no_banned_technical_words_public(path):
    low = _visible(_get(path)).lower()
    for w in _BANNED:
        assert w not in low, f"{path} exposes technical word {w!r}"


@pytest.mark.django_db
def test_no_crm_pipeline_lead_jargon_public():
    # CRM / pipeline must never surface; 'lead' only as a standalone marketing term
    for path in ("/", "/documents/", "/contact/"):
        low = _visible(_get(path)).lower()
        assert "crm" not in low
        assert "pipeline" not in low


# --- 5. Standing hygiene gates ---------------------------------------------
_FLAT_CTA = re.compile(r"<(?:a|button)\b[^>]*\brounded-full\s+(?:bg-ink-950|bg-gold-500)\b")


def test_no_flat_ctas_remain():
    offenders = [t.name for t in PUBLIC.glob("*.html")
                 if _FLAT_CTA.search(t.read_text("utf-8"))]
    assert not offenders, f"flat CTAs remain: {offenders}"


def test_no_inline_styles_in_changed_templates():
    for name in ("header.html", "cta_consultation.html"):
        src = (BASE / "templates" / "partials" / name).read_text("utf-8")
        assert "style=" not in src


def test_no_external_cdn_in_header():
    assert "cdn." not in HEADER and "googleapis" not in HEADER


_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/documents/", "/guided/", "/case-types/", "/sources/"])
def test_no_money_on_engineless_pages(path):
    assert not _MONEY.search(_get(path))


# --- 6. Regression: RTL / canaries / i18n / upload --------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/", "/ar/documents/", "/ar/sources/"])
def test_rtl_pages_200(path):
    resp = Client().get(path, HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200 and 'dir="rtl"' in resp.content.decode()


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


@pytest.mark.django_db
def test_document_upload_still_works():
    from django.core.files.uploadedfile import SimpleUploadedFile
    f = SimpleUploadedFile("offerta.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    body = Client().post("/documents/upload/", {"document": [f], "analysis_consent": "on",
                                                "website": ""},
                         REMOTE_ADDR="203.0.113.77").content.decode()
    assert 'id="document-result"' in body


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
