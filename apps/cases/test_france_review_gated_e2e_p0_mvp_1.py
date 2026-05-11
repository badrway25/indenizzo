"""
Tests F-p0-mvp-1-non-it-readiness — France review-gated e2e.

Black-box HTTP tests for the FR road-accident funnel. They pin the
**public contract** that, as long as the FR chain is not fully
APPROVED end-to-end (LegalSource + Dataset + Formula + calculator
override), the public path MUST NOT publish any compensation amount
— regardless of how unit-level test fixtures behave.

What is covered:

1. ``GET /countries/france/`` returns 200.
2. ``GET /wizard/fr/road-accident/`` returns 200 with the
   review-gated public_status panel + ``noindex, nofollow``.
3. The wizard form rejects a POST without the GDPR consents
   (art. 6 + art. 9).
4. A POST with valid inputs + both consents redirects to the result
   page.
5. The result page renders without any EUR amount in the body and
   surfaces the ``unavailable_requires_legal_validation`` semantics.
6. The result page carries ``noindex, nofollow``.
7. The Simulation row persisted carries
   ``status=unavailable_requires_legal_validation``.
8. No banned wording ("scaffold", "placeholder", "module pending",
   "engine pending", "validation pending", etc.) leaks into the
   public surface, per the project's premium-copy discipline.
9. The disclaimer line is present on the result page.

These tests **never seed APPROVED LegalSources** for FR — the goal
is to prove the public path stays review-gated against today's DB.
"""

from __future__ import annotations

import re

import pytest
from django.urls import reverse

# Wording that must never appear on a public surface (mirrors the
# ``public_status.py`` banned list).
BANNED_PUBLIC_WORDING = (
    "scaffold",
    "placeholder",
    "under validation",
    "in preparation",
    "coming soon",
    "work in progress",
    "in corso",
    "legal validation wizard",
    "module pending",
    "engine pending",
    "missing_documents",
    "unavailable_requires_legal_validation",
)

# An EUR amount expressed at any common locale formatting we use.
EUR_AMOUNT_RX = re.compile(r"\d[\d\s.,]{2,}\s*(€|EUR)", re.IGNORECASE)


def _assert_no_banned_wording(html: str, where: str) -> None:
    body = html.lower()
    leaked = [w for w in BANNED_PUBLIC_WORDING if w in body]
    assert not leaked, f"banned wording leaked into {where}: {leaked}"


def _assert_no_eur_amount(html: str, where: str) -> None:
    match = EUR_AMOUNT_RX.search(html)
    assert match is None, (
        f"EUR amount '{match.group(0)}' leaked into {where} — FR must "
        "stay review-gated until the chain is APPROVED end-to-end."
    )


def _consent_aware_post(client, url, data, **extra):
    return client.post(url, data, HTTP_HOST="127.0.0.1", **extra)


# ---------------------------------------------------------------------------
# 1-2. Country landing + wizard GET
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_country_france_landing_renders(client):
    resp = client.get("/countries/france/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    _assert_no_banned_wording(html, "GET /countries/france/")
    _assert_no_eur_amount(html, "GET /countries/france/")


@pytest.mark.django_db
def test_france_wizard_get_renders_with_review_panel(client):
    resp = client.get("/wizard/fr/road-accident/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")

    assert "noindex" in html, "wizard pages must carry noindex meta robots"
    assert "nofollow" in html

    assert "victim_age" in html or "id_victim_age" in html
    _assert_no_banned_wording(html, "GET /wizard/fr/road-accident/")
    _assert_no_eur_amount(html, "GET /wizard/fr/road-accident/")


# ---------------------------------------------------------------------------
# 3. POST without consents is rejected (form invalid → re-renders with errors)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_france_wizard_post_without_consent_is_rejected(client):
    payload = {
        "accident_country": "FR",
        "victim_age": "35",
        "permanent_disability_percentage": "10",
        "fault_percentage": "0",
        "website": "",
    }
    resp = _consent_aware_post(client, "/wizard/fr/road-accident/", payload)
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert (
        "simulation consent" in html.lower()
        or "consent" in html.lower()
        or "consenso" in html.lower()
    ), "wizard must surface the GDPR consent requirement on validation failure"


# ---------------------------------------------------------------------------
# 4-7. POST with valid inputs + consents → review-gated result
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_france_wizard_post_with_valid_input_lands_unavailable(client):
    """End-to-end happy path. The Studio has not yet signed Mornet/
    Gazette, so even a perfectly-valid submit must NOT produce a
    number on the public surface."""
    from apps.cases.models import Simulation

    payload = {
        "accident_country": "FR",
        "victim_age": "35",
        "permanent_disability_percentage": "10",
        "fault_percentage": "0",
        "consent_simulation": "on",
        "special_categories_consent": "on",
        "website": "",
    }
    resp = _consent_aware_post(client, "/wizard/fr/road-accident/", payload)

    assert resp.status_code == 302, (
        "a valid FR wizard POST must redirect to the result page"
    )
    assert "/wizard/result/" in resp["Location"]

    sim = Simulation.objects.order_by("-created_at").first()
    assert sim is not None
    assert sim.status == "unavailable_requires_legal_validation", (
        f"FR simulation must land 'unavailable', got {sim.status!r}. "
        "Either the chain has been promoted without this test being "
        "updated, OR the calculator is leaking output past its gating."
    )

    result_url = resp["Location"]
    result_resp = client.get(result_url, HTTP_HOST="127.0.0.1")
    assert result_resp.status_code == 200
    html = result_resp.content.decode("utf-8")

    assert "noindex" in html
    assert "nofollow" in html

    _assert_no_banned_wording(html, f"GET {result_url}")
    _assert_no_eur_amount(html, f"GET {result_url}")

    body = html.lower()
    assert (
        "assessment" in body
        or "valutazione" in body
        or "évaluation" in body
        or "evaluation" in body
        or "preliminary" in body
        or "preliminare" in body
        or "review" in body
    ), "result page must surface the review-pending semantics in user-friendly copy"

    assert (
        "disclaimer" in body
        or "simulazione" in body
        or "indicative" in body
        or "indicativ" in body
    ), "result page must carry the disclaimer wording"


# ---------------------------------------------------------------------------
# 8. The disclaimer / privacy / mandate pages are reachable from FR funnel
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_disclaimer_and_privacy_pages_are_reachable(client):
    for path in ("/disclaimer/", "/privacy/"):
        resp = client.get(path, HTTP_HOST="127.0.0.1")
        assert resp.status_code == 200, f"GET {path} returned {resp.status_code}"
        html = resp.content.decode("utf-8")
        _assert_no_banned_wording(html, f"GET {path}")
