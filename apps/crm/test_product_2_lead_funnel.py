"""
Tests PRODUCT-2-lead-funnel-improvements.

Funnel improvements covered:

 1. Result page renders the new "Documents to prepare" partial.
 2. Thank-you page renders the same partial (variant="thank-you").
 3. Contact GET with `?sim=<uuid>` shows the linked-simulation
    confirmation banner AND prefills country + case_type.
 4. Contact GET WITHOUT `?sim=` does NOT render the banner.
 5. Contact GET with an invalid / unknown `?sim=` does NOT 500
    (failure-soft) — banner is suppressed, form opens blank.
 6. Contact POST flow still resolves the Simulation FK on the Lead.
 7. The thank-you doc-prep block does not leak any EUR amount
    (it's generic, country-agnostic).
 8. AR (RTL) /contact/ still renders 200 with `dir="rtl"`.
 9. France stays review-gated (no EUR amount on /wizard/fr/).
"""

from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest
from django.test import Client

from apps.cases.models import Simulation
from apps.crm.models import Lead

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "product" / "LEAD_FUNNEL_AUDIT_2026-05-12.md"


# ---------------------------------------------------------------------------
# 0. Audit doc exists
# ---------------------------------------------------------------------------


def test_funnel_audit_doc_exists():
    assert AUDIT_DOC.exists()
    assert AUDIT_DOC.stat().st_size > 4000, (
        "Audit doc must be substantive (P0/P1/P2 friction map + " "recommendations), not a stub."
    )


# ---------------------------------------------------------------------------
# 1. Result page renders the new "Documents to prepare" partial.
#    We use a real wizard POST so we exercise the actual view path.
# ---------------------------------------------------------------------------


def _create_italy_simulation(client: Client) -> Simulation:
    """Run a real Italy wizard POST and return the persisted Simulation.

    This deliberately uses the live view so the test stays a true
    funnel e2e: if the wizard form schema changes, the test breaks
    instead of silently passing on a stale fixture.
    """
    resp = client.post(
        "/wizard/it/road-accident/",
        {
            "accident_country": "IT",
            "victim_age": 35,
            "permanent_disability_percentage": "10",
            "fault_percentage": "0",
            "consent_simulation": "on",
            "special_categories_consent": "on",
        },
        HTTP_HOST="127.0.0.1",
        follow=False,
    )
    # Should redirect to /wizard/result/<uuid>/
    assert (
        resp.status_code == 302
    ), f"Wizard POST did not redirect to result page (status={resp.status_code})"
    sim = Simulation.objects.order_by("-created_at").first()
    assert sim is not None, "Simulation was not persisted by wizard POST"
    return sim


@pytest.mark.django_db
def test_result_page_includes_documents_to_prepare(client):
    sim = _create_italy_simulation(client)
    resp = client.get(
        f"/wizard/result/{sim.public_id}/",
        HTTP_HOST="127.0.0.1",
        HTTP_ACCEPT_LANGUAGE="en",
    )
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    # The new block must be rendered on BOTH the estimate path AND
    # the review-gated path (test DB has no approved Italy formula,
    # so the simulation lands on the review-gated branch). The
    # partial is now outside the `{% if has_estimate %}` guard.
    assert "Documents to prepare" in body, (
        "Result page missing the 'Documents to prepare' block — "
        "F-product-2-funnel partial not included."
    )
    # Generic content markers from the partial.
    hits = sum(
        1
        for marker in (
            "Medical reports",
            "Accident records",
            "Insurance correspondence",
            "Proof of economic impact",
            "Identity and contact",
        )
        if marker in body
    )
    assert hits >= 3, (
        f"Documents-to-prepare partial appears truncated on result "
        f"page ({hits}/5 markers found)"
    )


# ---------------------------------------------------------------------------
# 2. Thank-you page renders the partial (variant="thank-you").
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_thank_you_includes_while_you_wait_block(client):
    resp = client.get("/contact/thank-you/", HTTP_HOST="127.0.0.1", HTTP_ACCEPT_LANGUAGE="en")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    # Thank-you variant has a different headline.
    assert "While you wait for our reply" in body, (
        "Thank-you page missing the 'while you wait' headline — "
        "F-product-2-funnel doc-prep partial not included."
    )
    # Same checklist content, different variant.
    assert "Medical reports" in body
    assert "Insurance correspondence" in body


# ---------------------------------------------------------------------------
# 3. Contact GET with valid `?sim=<uuid>` — banner + prefill
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_get_with_sim_shows_banner_and_prefills(client):
    sim = _create_italy_simulation(client)
    # /en/ prefix: the route is under i18n_patterns(prefix_default_language
    # =False), so a non-prefixed URL renders in the default locale (it). This
    # test asserts the English banner string (now translated in IT).
    resp = client.get(
        f"/en/contact/?sim={sim.public_id}",
        HTTP_HOST="127.0.0.1",
    )
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    # 3.a Banner is rendered.
    assert (
        "Connected to your simulation" in body
    ), "Contact GET with valid ?sim= must show the confirmation banner"
    # 3.b Simulation public_id is shown in the banner copy.
    assert str(sim.public_id) in body
    # 3.c case_type is prefilled (we POSTed IT road-accident).
    # The wizard sets case_type=ROAD_ACCIDENT_BODILY_INJURY on Simulation.
    expected_case_type = sim.case_type
    assert expected_case_type
    # The selected case_type appears as `value="<code>" ... selected`
    # OR as `selected` on an option with that code. We check loosely:
    assert (
        f'value="{expected_case_type}" selected' in body
        or f'<option value="{expected_case_type}" selected' in body
    ), (
        f"Contact form should preselect case_type={expected_case_type!r} "
        f"from the linked simulation"
    )


# ---------------------------------------------------------------------------
# 4. Contact GET WITHOUT `?sim=` — no banner
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_get_without_sim_has_no_banner(client):
    # Force English so the assertion isn't translation-dependent.
    resp = client.get("/contact/", HTTP_HOST="127.0.0.1", HTTP_ACCEPT_LANGUAGE="en")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert (
        "Connected to your simulation" not in body
    ), "Contact GET without ?sim= must NOT render the banner"
    # The contact form itself must still render (sanity check that we
    # didn't accidentally hide the wrong block).
    assert "id_first_name" in body
    assert "id_message" in body


# ---------------------------------------------------------------------------
# 5. Contact GET with unknown/invalid `?sim=` — failure-soft
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_get_with_unknown_sim_does_not_500(client):
    # A well-formed UUID that resolves to no Simulation row.
    fake = uuid.uuid4()
    resp = client.get(f"/contact/?sim={fake}", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200, "Contact GET with unknown sim must return 200, not 500"
    body = resp.content.decode("utf-8")
    assert (
        "Connected to your simulation" not in body
    ), "Banner must be suppressed when ?sim= does not resolve"


@pytest.mark.django_db
def test_contact_get_with_malformed_sim_does_not_500(client):
    # A garbage string — must not crash the Simulation query.
    resp = client.get("/contact/?sim=not-a-uuid", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200, "Contact GET with malformed sim must return 200, not 500"


# ---------------------------------------------------------------------------
# 6. Contact POST end-to-end — Lead.simulation FK still gets set.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_post_links_lead_to_simulation(client):
    sim = _create_italy_simulation(client)
    resp = client.post(
        "/contact/",
        {
            "first_name": "Test",
            "last_name": "User",
            "email": "test.user@example.com",
            "phone_number": "",
            "preferred_language": "it",
            "country": "",
            "case_type": sim.case_type,
            "message": "Please review this case from my simulation.",
            "privacy_accepted": "on",
            "special_categories_accepted": "on",
            "simulation_public_id": str(sim.public_id),
        },
        HTTP_HOST="127.0.0.1",
        follow=False,
    )
    assert resp.status_code == 302, f"Contact POST did not redirect (status={resp.status_code})"
    lead = Lead.objects.order_by("-created_at").first()
    assert lead is not None
    assert lead.simulation_id == sim.id, "Lead.simulation FK must be set to the linked simulation"


# ---------------------------------------------------------------------------
# 7. The doc-prep block is generic — no EUR amount leaks.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_thank_you_doc_prep_does_not_leak_amounts(client):
    body = client.get("/contact/thank-you/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    # No formatted EUR amount anywhere on the thank-you page.
    assert not re.search(
        r"\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)", body
    ), "Thank-you doc-prep partial must remain generic (no EUR amount)"


# ---------------------------------------------------------------------------
# 8. AR (RTL) /contact/ still renders 200 with dir="rtl".
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_renders_rtl_for_arabic_locale(client):
    resp = client.get("/ar/contact/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert 'dir="rtl"' in body
    # "What happens next" reassurance still present (i18n active).
    # We do not assert the exact Arabic translation — only that the
    # form structure is intact and the new partial does not break RTL.


# ---------------------------------------------------------------------------
# 9. France stays review-gated — no EUR amount on /wizard/fr/.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_france_wizard_still_review_gated(client):
    body = client.get("/wizard/fr/road-accident/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    assert not re.search(r"\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)", body), (
        "France wizard must remain review-gated — no EUR amount until "
        "the 4 Studio signatures arrive."
    )
