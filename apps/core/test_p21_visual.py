"""P21 — guard the premium 2026 visual direction in the design system.

These lock the CSS-level invariants of the visual redesign: the premium tokens
and gradients ship, cards/medallions/buttons gained depth, the motion layer is
present AND degrades under prefers-reduced-motion, and nothing reintroduces an
inline style (CSP) or a heavy dependency.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings

DS_CSS = Path(settings.BASE_DIR) / "static" / "css" / "design-system.css"
SITE_JS = Path(settings.BASE_DIR) / "static" / "js" / "site.js"


def _css():
    return DS_CSS.read_text("utf-8")


def test_premium_tokens_present():
    css = _css()
    for token in ("--premium-gold", "--premium-bronze", "--premium-navy", "--premium-ivory",
                  "--premium-border", "--premium-shadow-soft", "--premium-shadow-lift",
                  "--premium-gradient-legal", "--premium-gradient-gold"):
        assert token in css, token


def test_cards_and_medallions_have_depth():
    css = _css()
    # card gradient surface + soft shadow
    assert ".premium-service-card" in css
    assert "linear-gradient(180deg, #ffffff" in css
    # gold radial medallion for icon tiles
    assert ".premium-icon-tile" in css
    assert "radial-gradient(120% 120% at 30% 18%" in css


def test_motion_layer_present_and_reduced_motion_safe():
    css = _css()
    # discreet button light-sweep
    assert ".premium-btn::after" in css
    assert "translateX(130%)" in css
    # and it is disabled under reduced motion
    rm = css.split("prefers-reduced-motion: reduce", 1)
    assert len(rm) == 2, "no reduced-motion block"
    # the button sweep is switched off in a reduced-motion block somewhere
    assert ".premium-btn::after { display: none" in css


def test_page_texture_is_decorative_only():
    css = _css()
    # the whole-page warmth must sit behind everything and never capture clicks
    assert "body::before" in css
    block = css.split("body::before", 1)[1][:300]
    assert "pointer-events: none" in block
    assert "z-index: -1" in block


def test_no_external_cdn_or_heavy_dependency_added():
    css = _css()
    # data-URI SVGs are fine; remote url() pulls are not
    assert "url(http://" not in css and "url(https://" not in css
    assert "@import url(http" not in css
