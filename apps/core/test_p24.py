"""P24 — guard elegant background imagery, refined motion and the card status cleanup.

Locks three things so they cannot quietly regress:
  1. Calculable case cards read as a direct estimate, never a generic
     "Percorso legale assistito" / "Esame legale dedicato", and each card
     carries its own (non-repeated) description.
  2. The listed public pages carry a real text-over-image hero (the
     `.premium-hero-*` classes) plus a photographic texture band on the home page.
  3. The motion system is defined AND neutralised under prefers-reduced-motion.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
DS_CSS = Path(settings.BASE_DIR) / "static" / "css" / "design-system.css"
TEMPLATES = Path(settings.BASE_DIR) / "templates" / "public"

# Wording that must never label a calculable Italian card.
GENERIC_ASSISTED = ("Percorso legale assistito", "Esame legale dedicato",
                    "revisione legale manuale")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- Card status cleanup (highest-priority complaint) -----------------------
@pytest.mark.django_db
def test_case_cards_drop_generic_assisted_badges():
    body = _get("/case-types/")
    for tok in GENERIC_ASSISTED:
        assert tok not in body, f"/case-types/ still labels a card {tok!r}"


@pytest.mark.django_db
def test_calculable_cards_read_as_estimates():
    body = _get("/case-types/")
    # road → official estimate; medical → tabular biological-damage estimate;
    # work injury → documental pre-check (short badge matching the legend).
    assert "Stima da fonte ufficiale" in body
    assert "Stima tabellare del danno biologico" in body
    assert "Pre-check documentale" in body


@pytest.mark.django_db
def test_case_cards_have_varied_descriptions():
    body = _get("/case-types/")
    # The pre-P24 page repeated one generic blurb on every gold card.
    assert "revisione legale manuale su richiesta" not in body
    # Each family now has its own line — assert several distinct ones render.
    distinct = [
        "Stima indicativa del danno alla persona",          # road
        "Una stima tabellare del danno biologico",          # medical
        "Individuiamo la fonte ufficiale INAIL",            # work injury
        "Una lettura guidata del danno",                    # parental loss
        "Verifica documentale del fascicolo",               # death
        "Calcolo indicativo delle quote di legittima",      # inheritance
    ]
    present = [d for d in distinct if d in body]
    assert len(present) >= 5, f"only {len(present)} distinct card descriptions render"


# --- Imagery: real text-over-image heroes -----------------------------------
# NOTE: conftest redirects MEDIA_ROOT to a tmp dir, so the Pexels manifest is
# absent under pytest and the photos never resolve. We therefore guard the
# wiring at the template-source level, and prove the runtime integration with a
# single mocked render below (production ships the manifest + media).
def test_imagery_partial_uses_overlay_classes():
    src = (TEMPLATES.parent / "partials" / "_premium_hero_image.html").read_text("utf-8")
    # P46: the hero is now full-bleed; the readable copy layer is `premium-hero-inner`.
    for cls in ("premium-hero-image", "premium-hero-overlay", "premium-hero-inner", "premium-hero-fullbleed"):
        assert cls in src, f"hero partial missing {cls}"


@pytest.mark.parametrize("template,needle", [
    ("services.html", "_premium_hero_image.html"),
    ("guided_router.html", "_premium_hero_image.html"),
    ("precheck.html", "_premium_hero_image.html"),
    ("countries.html", "_premium_hero_image.html"),
    ("case_types.html", "_premium_hero_image.html"),
    ("wizard_result.html", "_premium_hero_image.html"),
    ("home.html", "premium-hero-image"),
    ("country_landing.html", "premium-hero-image"),
])
def test_pages_wire_a_real_image_hero(template, needle):
    src = (TEMPLATES / template).read_text("utf-8")
    assert needle in src, f"{template} does not wire an image hero ({needle})"


def test_home_template_has_photographic_texture_band():
    src = (TEMPLATES / "home.html").read_text("utf-8")
    assert "premium-bg-architecture" in src
    assert "premium-bg-media" in src  # the real, tinted photo layer


@pytest.mark.django_db
def test_case_types_renders_image_hero_when_media_present(monkeypatch):
    # Force a resolved Pexels image so the hero actually renders end-to-end.
    fake = {"src": "/media/pexels/x.jpg", "alt": "Studio legale"}
    monkeypatch.setattr("apps.core.views._pexels_hero", lambda *a, **k: fake)
    body = _get("/case-types/")
    assert "premium-hero-image" in body
    assert "premium-hero-overlay" in body
    assert "premium-hero-inner" in body  # P46: the readable text-over-image layer (full-bleed)


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/case-types/", "/countries/morocco/"])
def test_imagery_pages_show_no_money_or_slug(path):
    body = _get(path)
    assert not _MONEY.search(body), f"{path} leaks a money figure"
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                     re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)))
    assert not re.search(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b", visible), f"{path} leaks snake_case"


# --- Imagery CSS contract ---------------------------------------------------
def test_imagery_classes_defined_in_css():
    css = DS_CSS.read_text("utf-8")
    for cls in (".premium-hero-image", ".premium-hero-overlay", ".premium-hero-content",
                ".premium-visual-panel", ".premium-image-card", ".premium-bg-legal",
                ".premium-bg-architecture", ".premium-bg-documents"):
        assert cls in css, f"{cls} missing from design-system.css"


# --- Motion: defined and reduced-motion-safe --------------------------------
def test_motion_keyframes_defined():
    css = DS_CSS.read_text("utf-8")
    assert "@keyframes premium-rise" in css
    assert "@keyframes premium-slow-zoom" in css
    assert "@keyframes premium-float" in css


def test_motion_disabled_under_reduced_motion():
    css = DS_CSS.read_text("utf-8")
    # find the LAST reduced-motion block and confirm it neutralises the new
    # animations (so the imagery/motion layer respects the user preference).
    idx = css.rfind("@media (prefers-reduced-motion: reduce)")
    assert idx != -1
    tail = css[idx:]
    for cls in (".premium-rise", ".premium-hero-image", ".premium-bg-media", ".premium-float"):
        assert cls in tail, f"{cls} not neutralised under prefers-reduced-motion"
    assert "animation: none" in tail


@pytest.mark.django_db
def test_home_hero_copy_has_entrance_motion():
    assert "premium-rise" in _get("/")


# --- Result template carries imagery + motion (file-level: needs a live sim) -
def test_result_template_has_image_and_motion():
    src = (TEMPLATES / "wizard_result.html").read_text("utf-8")
    assert "_premium_hero_image.html" in src
    assert "premium-rise" in src


# --- Catalogs stay fuzzy-free ----------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
