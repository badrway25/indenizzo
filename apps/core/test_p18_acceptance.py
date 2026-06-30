"""P18 — final premium acceptance guards.

Locks the finalisation invariants: no inline style attributes anywhere in the
templates (the strict CSP forbids them — this is the class of bug fixed in P16),
the guided service badges read with variety rather than identically, the key
funnel destinations resolve, and the premium component classes ship in the
design system.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

TEMPLATES_DIR = Path(settings.BASE_DIR) / "templates"
DS_CSS = Path(settings.BASE_DIR) / "static" / "css" / "design-system.css"
_INLINE_STYLE = re.compile(r'\sstyle\s*=\s*["\']')


# --- CSP: no inline style attributes in templates ---------------------------
def test_no_inline_style_attributes_in_templates():
    offenders = []
    for html in TEMPLATES_DIR.rglob("*.html"):
        text = html.read_text("utf-8")
        if _INLINE_STYLE.search(text):
            offenders.append(str(html.relative_to(settings.BASE_DIR)))
    assert not offenders, f"inline style= breaks CSP in: {offenders}"


# --- Copy variety: guided service badges are not all identical --------------
def test_service_badges_have_variety():
    from django.utils import translation

    from apps.core import public_pages

    with translation.override("en"):
        badges = [str(s.badge) for s in public_pages.SERVICES]
    # The guided "Assisted path" badge appears at most once now (death only).
    assert badges.count("Assisted path based on official sources") <= 1
    # The differentiated badges ship.
    assert "Multilingual assistance on official sources" in badges
    assert "Documental verification" in badges


@pytest.mark.django_db
def test_services_page_is_not_one_repeated_badge():
    body = Client().get("/services/", HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert body.count("Percorso assistito con fonte ufficiale") <= 1
    assert "Assistenza multilingue su fonti ufficiali" in body
    assert "Verifica documentale" in body


# --- Funnel: every key CTA destination resolves -----------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", [
    "/wizard/it/road-accident/", "/wizard/it/medical-malpractice/", "/wizard/it/offer-comparison/",
    "/precheck/inail/", "/precheck/loss-of-relative/", "/precheck/morocco-road-accident/",
    "/precheck/tunisia-road-accident/", "/precheck/international-road-accident/",
    "/guided/", "/services/", "/case-types/", "/countries/morocco/", "/ta3ouid/",
])
def test_funnel_destination_resolves(path):
    assert Client().get(path, HTTP_ACCEPT_LANGUAGE="it").status_code == 200


# --- Premium component classes ship in the design system --------------------
def test_premium_component_classes_present():
    css = DS_CSS.read_text("utf-8")
    for cls in (".premium-card", ".premium-card-hover", ".field-select",
                ".lang-switch-select", ".precheck-layout", ".readiness-fill",
                ".icon-medallion", ".premium-sidebar-sticky"):
        assert cls in css, cls
