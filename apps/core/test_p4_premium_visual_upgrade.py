"""P4 — Premium Visual Design, Motion & Public Experience Upgrade guards.

The P4 phase is an additive, presentation-only elevation of the public site
(CSS design-system + a CSP-safe motion layer + template class changes). These
tests pin that the elevation is present AND that it did not weaken any of the
load-bearing contracts: strict CSP (no inline styles), reduced-motion + RTL
safety, the frozen wizard field names, fail-closed FR/BE/MA/TN, the FAQ
FAQPage JSON-LD, hreflang, and the "no invented number / no public prescription
term" rules. P4 touches no calculator/engine code; the Italy smoke invariant in
test_premium_visual_i18n_pass1 remains the calculation regression guard.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

_STATIC = Path(settings.BASE_DIR) / "static"
_DS_CSS = _STATIC / "css" / "design-system.css"
_SITE_JS = _STATIC / "js" / "site.js"
_TEMPLATES = Path(settings.BASE_DIR) / "templates"

# Numeric period presented as a term, e.g. "2 anni" / "3 years" — must NOT appear
# on any public page (mirrors the prescription guard's word-boundaried pattern).
_PERIOD_RE = re.compile(
    r"\b\d+\s*(anni|anno|years?|ans?|mesi|mese|months?|giorni|giorno|days?)\b", re.IGNORECASE
)
# Grouped currency amount, e.g. "€ 1.234" / "12,500 EUR" — no invented figures.
_AMOUNT_RE = re.compile(r"(€|eur)\s?\d{1,3}[.,]\d{3}", re.IGNORECASE)


# --- 1. Premium markers are present on the upgraded public pages ------------

@pytest.mark.django_db
@pytest.mark.parametrize(
    "path,markers",
    [
        ("/", ["premium-hero__veil", "premium-hero__pattern", "premium-stat",
               "premium-service-card", "data-tilt", "data-magnetic", "cta-arrow"]),
        ("/services/", ["premium-service-card", "premium-icon-tile", "is-calculable", "cta-arrow"]),
        ("/how-it-works/", ["premium-timeline", "premium-timeline__index", "premium-timeline__card"]),
        ("/faq/", ["premium-accordion", "premium-accordion__body"]),
        ("/wizard/it/road-accident/", ["premium-wizard-shell", "cta-arrow"]),
    ],
)
def test_premium_markers_present(path, markers):
    body = Client().get(path).content.decode("utf-8")
    missing = [m for m in markers if m not in body]
    assert not missing, f"{path} missing premium markers: {missing}"


@pytest.mark.django_db
def test_design_system_and_motion_js_still_loaded_no_cdn():
    body = Client().get("/").content.decode("utf-8")
    assert "/static/css/design-system.css" in body
    assert "/static/js/site.js" in body
    assert "cdn.tailwindcss" not in body  # no Tailwind CDN runtime


# --- 2. CSP safety: no inline style attribute reaches a public page ---------

@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/services/", "/how-it-works/", "/faq/", "/wizard/it/road-accident/"])
def test_no_inline_style_attribute_on_public_pages(path):
    """Strict CSP has no style-src 'unsafe-inline'; dynamic values go through the
    CSSOM from site.js, never as inline style= attributes in the served HTML."""
    body = Client().get(path).content.decode("utf-8")
    assert ' style="' not in body, f"{path} leaked an inline style attribute (CSP risk)"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/services/", "/how-it-works/", "/faq/"])
def test_no_template_comment_leak_on_public_pages(path):
    """Multi-line {# #} comments leak as literal text in Django; ensure none do."""
    body = Client().get(path).content.decode("utf-8")
    for token in ("{#", "{% comment", "data-tilt transform", "layered veil"):
        assert token not in body, f"{path} leaked template token {token!r}"


# --- 3. Reduced-motion + RTL are honoured by the new layer ------------------

def test_reduced_motion_guards_cover_new_motion_hooks():
    css = _DS_CSS.read_text("utf-8")
    # the new motion hooks + components must degrade under reduced motion
    rm_blocks = css.count("prefers-reduced-motion")
    assert rm_blocks >= 6, f"expected several reduced-motion guards, found {rm_blocks}"
    for hook in ("[data-magnetic]", "[data-tilt]", ".premium-service-card", ".premium-timeline__card"):
        assert hook in css, f"new motion hook {hook} missing from design-system.css"
    # the magnetic/tilt block explicitly neutralises transforms under reduced motion
    assert "transform: none !important" in css


def test_new_premium_components_defined_and_rtl_aware():
    css = _DS_CSS.read_text("utf-8")
    for cls in (
        ".premium-hero", ".premium-hero__veil", ".premium-hero__pattern",
        ".premium-service-card", ".premium-stat", ".premium-cta",
        ".premium-timeline", ".premium-wizard-shell", ".premium-source-panel",
        ".premium-image-frame", ".premium-icon-tile", ".premium-accordion", ".cta-arrow",
    ):
        assert cls in css, f"premium component {cls} not defined in design-system.css"
    # RTL: logical properties + an explicit [dir="rtl"] mirror for the arrow
    assert "inset-inline-start" in css
    assert '[dir="rtl"] .cta-arrow' in css


def test_motion_js_is_progressively_enhanced_and_guarded():
    js = _SITE_JS.read_text("utf-8")
    assert "initMagnetic" in js and "initTilt" in js
    # both effects must bail on reduced motion and on coarse/touch pointers
    assert js.count("prefersReduced") >= 4
    assert "(hover: hover) and (pointer: fine)" in js
    # values written through the CSSOM (element.style), never inline HTML attrs
    assert "el.style.transform" in js


# --- 4. Fail-closed FR/BE/MA/TN unchanged after the visual upgrade ----------

@pytest.mark.django_db
def test_non_it_still_fail_closed_after_p4():
    data = json.loads(Client().get("/countries/readiness.json").content.decode("utf-8"))
    non_it = {
        c["country_code"]: c["can_calculate"]
        for c in data["countries"]
        if c["country_code"] != "IT"
    }
    assert non_it and all(v is False for v in non_it.values()), f"non-IT must stay fail-closed: {non_it}"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/countries/france/", "/countries/belgium/",
                                  "/countries/morocco/", "/countries/tunisia/"])
def test_non_it_landing_shows_no_invented_amount(path):
    body = Client().get(path).content.decode("utf-8")
    assert not _AMOUNT_RE.search(body), f"{path} shows a grouped currency amount"
    for forbidden in ("26268", "27353", "28439"):
        assert forbidden not in body


# --- 5. No invented number / no public prescription term on premium pages ---

@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/services/", "/how-it-works/", "/faq/"])
def test_no_numeric_prescription_term_or_invented_amount_on_premium_pages(path):
    # strip the rendered HTML to visible text-ish content for the period scan;
    # the amount scan runs on the whole body (markup never carries € groups).
    body = Client().get(path).content.decode("utf-8")
    assert not _AMOUNT_RE.search(body), f"{path} shows a grouped currency amount"
    visible = re.sub(r"<[^>]+>", " ", body)
    assert not _PERIOD_RE.search(visible), f"{path} shows a numeric (prescription-like) term"


# --- 6. FAQ JSON-LD stays valid and accordion stays native <details> --------

@pytest.mark.django_db
def test_faq_jsonld_valid_and_native_details_accordion():
    body = Client().get("/faq/").content.decode("utf-8")
    # native <details>/<summary> — keyboard-accessible without JS
    assert "<details" in body and "<summary" in body
    assert "premium-accordion" in body
    m = re.search(r'<script type="application/ld\+json"[^>]*>(.*?)</script>', body, re.DOTALL)
    assert m, "FAQ page lost its JSON-LD block"
    data = json.loads(m.group(1))
    assert data.get("@type") == "FAQPage"
    assert data.get("mainEntity"), "FAQPage has no questions"


# --- 7. hreflang contract intact on the upgraded indexable pages ------------

@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/services/", "/how-it-works/", "/faq/", "/about/"])
def test_hreflang_intact_on_upgraded_pages(path):
    body = Client().get(path).content.decode("utf-8")
    for lang in ("it", "fr", "en", "ar"):
        assert f'hreflang="{lang}"' in body, f"{path} lost hreflang {lang}"
    assert 'hreflang="x-default"' in body


# --- 8. Frozen wizard field names survive the shell restyle -----------------

@pytest.mark.django_db
def test_wizard_frozen_field_names_present_after_shell_restyle():
    """site.js wizard-progress reads these exact names; the premium-wizard-shell
    restyle must not rename or drop any field."""
    body = Client().get("/wizard/it/road-accident/").content.decode("utf-8")
    for field in (
        "accident_date", "victim_age", "permanent_disability_percentage",
        "total_temporary_disability_days", "partial_temporary_disability_days",
        "medical_expenses", "lost_income", "fault_percentage",
        "consent_simulation", "special_categories_consent", "accident_country",
    ):
        assert field in body, f"wizard lost frozen field {field!r}"
