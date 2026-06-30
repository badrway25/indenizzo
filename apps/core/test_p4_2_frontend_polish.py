"""P4-2 — Exhaustive frontend QA & premium polish guards.

P4-2 is a verification + targeted-polish pass on top of P4. The only code
changes are presentation-only and defensive: a premium gradient header for
image-less country cards (so the no-photo fallback used on a fresh CI checkout
stays coherent with the photo cards) and scroll-reveal on the methodology
cards (the one content page whose cards did not animate). These tests pin those
additions and re-assert the load-bearing contracts on the touched pages.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

_DS_CSS = Path(settings.BASE_DIR) / "static" / "css" / "design-system.css"

_AMOUNT_RE = re.compile(r"(€|eur)\s?\d{1,3}[.,]\d{3}", re.IGNORECASE)


def test_country_card_cover_defined_and_premium():
    """The image-less country card falls back to a premium gradient header,
    not a flat code+badge, so MA/TN (and any image-absent checkout) stay coherent.
    The class deliberately avoids the word 'placeholder' (a FORBIDDEN public token)."""
    css = _DS_CSS.read_text("utf-8")
    assert ".country-card__cover" in css
    assert ".country-card__placeholder" not in css  # forbidden public token
    # it is a layered navy gradient (reuses the brand tokens), not a flat colour
    block = css.split(".country-card__cover", 1)[1][:400]
    assert "--ds-navy" in block and "gradient" in block


@pytest.mark.django_db
def test_countries_page_premium_and_single_h1():
    body = Client().get("/countries/").content.decode("utf-8")
    assert body.count("<h1") == 1
    assert ' style="' not in body  # CSP: no inline style attribute
    # the fail-closed reassurance is present (no invented figure by design)
    assert "premium-alert" in body


@pytest.mark.django_db
def test_countries_fail_closed_badges_present_no_calc_for_non_it():
    """FR/BE/MA/TN must read as assessment, never as a calculated amount."""
    body = Client().get("/countries/").content.decode("utf-8")
    low = body.lower()
    # IT carries the calculation-available wording; the others an assessment label
    assert "calcolo indicativo" in low  # IT ok badge (it served unprefixed)
    assert "percorso legale assistito" in low  # FR/BE assessment badge
    # no grouped currency amount is published on the hub
    assert not _AMOUNT_RE.search(body)


@pytest.mark.django_db
def test_countries_fail_closed_in_french_and_arabic():
    fr = Client().get("/fr/countries/").content.decode("utf-8").lower()
    assert "accompagné" in fr  # "parcours juridique accompagné" (assisted pathway)
    assert "returns no amount" not in fr  # no English residue
    ar = Client().get("/ar/countries/")
    assert ar.status_code == 200
    body = ar.content.decode("utf-8")
    assert 'dir="rtl"' in body
    # arabic assisted-pathway label present, no English residue
    assert "مسار قانوني مرافَق" in body
    assert "Assisted legal pathway" not in body


@pytest.mark.django_db
def test_methodology_cards_animate_and_render():
    """The methodology cards now carry data-reveal (animation consistency)."""
    body = Client().get("/methodology/").content.decode("utf-8")
    assert body.count("<h1") == 1
    # the four numbered cards each opt into scroll-reveal
    assert body.count("data-reveal") >= 4
    assert ' style="' not in body
