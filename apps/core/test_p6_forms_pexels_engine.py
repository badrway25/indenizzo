"""P6 — premium forms, Pexels section imagery, engine-expansion guards.

Pins the P6 deliverables and the safety invariants: the premium form layer is
present, the new Pexels section slots are defined + pinned (no API key anywhere
committed), the section heroes render, the engine-expansion audit docs exist, and
NO new calculating engine was silently added (the audit documents; it does not
implement — fail-closed is unchanged).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from django.conf import settings

_BASE = Path(settings.BASE_DIR)
_DS_CSS = _BASE / "static" / "css" / "design-system.css"
_OVERRIDES = _BASE / "config" / "pexels_image_overrides.json"
_PEXELS = _BASE / "apps" / "core" / "pexels.py"
_DOCS = _BASE / "docs" / "audits"

_NEW_SLOTS = ("services_hero", "about_hero", "ta3ouid_hero", "how_it_works_hero", "faq_hero")


# --- 1. premium form design system ------------------------------------------

def test_premium_form_layer_present_and_rtl_aware():
    css = _DS_CSS.read_text("utf-8")
    for cls in (".premium-field", ".premium-label", ".premium-help", ".premium-error",
                ".premium-radio-card", ".premium-checkbox", ".premium-form-actions"):
        assert cls in css, f"missing form component {cls}"
    # custom select chevron via appearance:none + inline SVG, mirrored under RTL
    assert "appearance: none" in css
    assert "data:image/svg+xml" in css
    assert '[dir="rtl"] form select' in css
    # premium controls degrade under reduced motion (radio-card transition guarded)
    assert "prefers-reduced-motion" in css


# --- 2. Pexels section imagery (no key committed) ---------------------------

def test_pexels_section_slots_defined_and_pinned():
    from apps.core import pexels
    purposes = {s["purpose"] for s in pexels.SITE_IMAGE_SLOTS}
    for slot in _NEW_SLOTS:
        assert slot in purposes, f"slot {slot} not defined in SITE_IMAGE_SLOTS"
    overrides = json.loads(_OVERRIDES.read_text("utf-8"))["slots"]
    for slot in _NEW_SLOTS:
        assert slot in overrides, f"slot {slot} not pinned in overrides"
        assert overrides[slot].get("photo_id"), f"{slot} has no frozen photo_id"
        assert overrides[slot].get("approved_visual") is True


def test_no_pexels_api_key_committed():
    """The API key must never appear in a committed config/source file."""
    suspicious = re.compile(r"PEXELS_API_KEY\s*[:=]\s*['\"][A-Za-z0-9]{15,}", re.IGNORECASE)
    for f in (_OVERRIDES, _PEXELS):
        raw = f.read_text("utf-8")
        assert not suspicious.search(raw), f"possible API key in {f.name}"
        # the override doc itself states it never contains the key
    doc = json.loads(_OVERRIDES.read_text("utf-8")).get("_doc", "")
    assert "NEVER contains the API key" in doc


@pytest.mark.parametrize("tmpl", ["services.html", "about.html", "community.html",
                                  "how_it_works.html", "faq.html"])
def test_section_pages_include_hero_partial(tmpl):
    """The section pages integrate the premium hero image (the partial renders a
    <picture> when the media exists; in an isolated-MEDIA test env it no-ops —
    so we assert the integration point, not the rendered image)."""
    src = (_BASE / "templates" / "public" / tmpl).read_text("utf-8")
    assert 'partials/_premium_hero_image.html' in src, f"{tmpl} does not include the hero partial"


def test_section_views_wire_pexels_slots():
    views = (_BASE / "apps" / "core" / "views.py").read_text("utf-8")
    for slot in _NEW_SLOTS:
        assert f'_pexels_hero(request, "{slot}")' in views, f"view does not wire slot {slot}"


# --- 3. engine-expansion audit (documented, not silently implemented) -------

def test_engine_expansion_audit_docs_exist():
    assert (_DOCS / "CALCULATOR_ENGINE_EXPANSION_AUDIT_2026-06-25.md").is_file()
    assert (_DOCS / "MOROCCO_NON_IT_COMPENSATION_SOURCE_AUDIT_2026-06-25.md").is_file()


def test_no_new_calculating_engine_added_failclosed_unchanged():
    """P6 documents engine expansion; it must NOT have silently registered a new
    numeric engine. Only the IT road-accident chain calculates; FR/BE/MA/TN and
    the IT placeholders stay inert."""
    from apps.calculators.enums import CaseType
    from apps.calculators.registry import get_calculator

    # the one real engine is still the IT road-accident calculator
    it = get_calculator("IT-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert it is not None and "RoadAccident" in it.__name__
    # no medical / microlesion / inail engine was wired up this phase
    for ct in ("medical_liability_macro", "road_accident_microlesion",
               "inail_biological_damage", "medical_liability"):
        assert get_calculator("IT-NATIONAL", ct) is None, f"unexpected engine for {ct}"
