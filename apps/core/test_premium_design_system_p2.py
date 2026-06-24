"""P2 — Premium Design System Foundation smoke tests.

Asserts the additive design-system layer is wired and present, without
changing the existing site.css contract, the calculation canary, or the
fail-closed behaviour of non-IT countries.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client

DS_CSS = Path(__file__).resolve().parents[2] / "static" / "css" / "design-system.css"
PUBLIC_PATHS = ("/", "/countries/", "/wizard/", "/wizard/it/road-accident/", "/contact/")


@pytest.mark.django_db
def test_base_links_design_system_after_site_css():
    body = Client().get("/").content.decode("utf-8")
    assert 'href="/static/css/design-system.css"' in body
    assert 'href="/static/css/site.css"' in body
    # design-system loads AFTER site.css so components can build on the base
    assert body.index("/static/css/site.css") < body.index("/static/css/design-system.css")


@pytest.mark.django_db
def test_public_pages_carry_both_stylesheets_and_no_cdn():
    for path in PUBLIC_PATHS:
        body = Client().get(path).content.decode("utf-8")
        assert "/static/css/site.css" in body, f"{path} missing site.css"
        assert "/static/css/design-system.css" in body, f"{path} missing design-system.css"
        assert "cdn.tailwindcss.com" not in body, f"{path} regressed to CDN"


def test_design_system_carries_tokens_and_components():
    text = DS_CSS.read_text(encoding="utf-8")
    for token in (
        "--ds-navy",
        "--ds-gold",
        "--ds-success",
        "--ds-warning",
        "--ds-error",
        "--ds-focus-ring",
    ):
        assert token in text, f"design-system.css missing token {token}"
    for cls in (
        ".premium-btn",
        ".premium-btn-primary",
        ".premium-badge",
        ".premium-card",
        ".premium-provenance-card",
        ".premium-input",
        ".premium-alert",
        ".premium-modal",
        ".premium-toast",
        ".premium-stepper",
        ".premium-step-active",
    ):
        assert cls in text, f"design-system.css missing component {cls}"


@pytest.mark.django_db
def test_wizard_pages_render_stepper():
    start = Client().get("/wizard/").content.decode("utf-8")
    assert "premium-stepper" in start
    assert 'aria-current="step"' in start  # step 1 marked current
    italy = Client().get("/wizard/it/road-accident/").content.decode("utf-8")
    assert "premium-stepper" in italy


@pytest.mark.django_db
def test_disclaimer_bar_has_premium_accent():
    body = Client().get("/").content.decode("utf-8")
    assert "premium-disclaimer-bar" in body


@pytest.mark.django_db
def test_premium_submit_buttons_applied():
    assert "premium-btn premium-btn-primary" in Client().get("/contact/").content.decode("utf-8")
    assert "premium-btn premium-btn-primary" in Client().get(
        "/wizard/it/road-accident/"
    ).content.decode("utf-8")


@pytest.mark.django_db
def test_non_it_still_fail_closed_after_p2():
    """Design layer must not change the fail-closed readiness contract."""
    import json

    data = json.loads(Client().get("/countries/readiness.json").content.decode("utf-8"))
    non_it = {
        c["country_code"]: c["can_calculate"]
        for c in data["countries"]
        if c["country_code"] != "IT"
    }
    assert non_it, "expected non-IT countries in readiness payload"
    assert all(v is False for v in non_it.values()), f"non-IT must stay fail-closed: {non_it}"
