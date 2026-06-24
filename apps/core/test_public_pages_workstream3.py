"""Workstream-3 public content pages: routes, FAQ structured data, prudence.

These pages are informational and must stay deontological: no invented amounts,
no outcome promises, a visible disclaimer, and calculability claims that mirror
the real registry (only Italy road-accident is calculable today).
"""

from __future__ import annotations

import json
import re

import pytest
from django.test import Client
from django.urls import reverse

from apps.core import public_pages

NEW_VIEW_NAMES = [
    "core:how_it_works",
    "core:services",
    "core:faq",
    "core:about",
    "core:community",
]

# Positive marketing/outcome promises that must never appear (negations like
# "no guarantee of outcome" are fine and intentionally NOT listed here).
FORBIDDEN_PHRASES = [
    "guaranteed compensation",
    "guaranteed payout",
    "we guarantee",
    "best lawyer",
    "number one",
    "100% success",
    "success rate",
    "win your case",
    "we always win",
    "risarcimento garantito",
]

# Thousands-grouped number (an amount), e.g. 26.268 / 1,607,393 — must not appear.
_AMOUNT_RE = re.compile(r"\b\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{2})?\b")


def _paths():
    from django.utils import translation

    with translation.override("it"):  # default → unprefixed base paths
        return [reverse(n) for n in NEW_VIEW_NAMES]


def _en_html(name):
    """Canonical English content of a page (deterministic, language-stable)."""
    from django.utils import translation

    with translation.override("it"):
        base = reverse(name)
    return Client().get(f"/en{base}").content.decode("utf-8")


@pytest.mark.parametrize("prefix", ["", "/fr", "/ar", "/en"])
@pytest.mark.parametrize("name", NEW_VIEW_NAMES)
def test_new_pages_render_200(prefix, name, db):
    from django.utils import translation

    # Force the unprefixed base path under the default language, otherwise a
    # language left active by a previous request makes reverse() return an
    # already-prefixed path and `prefix + path` would double-prefix.
    with translation.override("it"):
        path = reverse(name)
    full = f"{prefix}{path}" if prefix else path
    resp = Client().get(full)
    assert resp.status_code == 200, f"GET {full} -> {resp.status_code}"


@pytest.mark.parametrize("name", NEW_VIEW_NAMES)
def test_new_pages_have_no_forbidden_promises(name, db):
    # Check the canonical English content; faithful translations carry no
    # promise the English source lacks.
    html = _en_html(name).lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in html, f"{name}: forbidden marketing phrase {phrase!r}"


@pytest.mark.parametrize("name", NEW_VIEW_NAMES)
def test_new_pages_have_no_invented_amounts(name, db):
    html = _en_html(name)
    assert "€" not in html, f"{name}: unexpected currency symbol"
    assert "EUR" not in html, f"{name}: unexpected EUR amount"
    assert not _AMOUNT_RE.search(html), f"{name}: looks like a monetary amount on an informational page"


@pytest.mark.parametrize("name", NEW_VIEW_NAMES)
def test_new_pages_carry_a_disclaimer(name, db):
    html = _en_html(name).lower()
    assert ("does not constitute" in html) or ("guarantee of outcome" in html), (
        f"{name}: no visible disclaimer phrase"
    )


def test_faq_jsonld_is_valid_and_complete(db):
    html = Client().get(reverse("core:faq")).content.decode("utf-8")
    m = re.search(r'application/ld\+json"[^>]*>(.*?)</script>', html, re.S)
    assert m, "FAQ page is missing FAQPage JSON-LD"
    data = json.loads(m.group(1))
    assert data["@type"] == "FAQPage"
    entities = data["mainEntity"]
    assert len(entities) == len(public_pages.FAQ_ITEMS)
    for q in entities:
        assert q["@type"] == "Question"
        assert q["name"].strip()
        assert q["acceptedAnswer"]["@type"] == "Answer"
        assert q["acceptedAnswer"]["text"].strip()


def test_services_calculability_mirrors_registry():
    """Only Italy road-accident is calculable; everything else is preliminary."""
    calculable = [s for s in public_pages.SERVICES if s.calculable]
    assert len(calculable) == 1, "exactly one service must be calculable today"
    assert calculable[0].key == "road_accident"
    assert calculable[0].cta_url_name == "cases:wizard_italy_road_accident"
    # Non-calculable services must route to the contact funnel, never a calculator.
    for s in public_pages.SERVICES:
        if not s.calculable:
            assert s.cta_url_name == "crm:contact", f"{s.key} should route to contact"


def test_new_pages_are_indexable_and_in_nav(db):
    """Header + footer expose the new pages (discoverability) and they are index/follow."""
    home = Client().get("/").content.decode("utf-8")
    for name in ("core:services", "core:how_it_works", "core:faq", "core:about", "core:community"):
        assert reverse(name) in home, f"{name} not linked from header/footer on home"
    for path in _paths():
        html = Client().get(path).content.decode("utf-8").lower()
        assert "noindex" not in html, f"{path}: should be indexable"
