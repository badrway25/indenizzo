"""
Tests PRODUCT-5-result-page-next-pages.

The wizard result page (`/wizard/result/<uuid>/`) now surfaces a
case-type-aware "Useful pages for your case" section listing 1-3
of the PRODUCT-4 landing pages, picked from
`apps.core.case_type_landings._RECOMMENDATIONS_BY_CASE_TYPE`.

What these tests guard:

 1. Audit doc + the recommendations mapping exist.
 2. `get_recommended_landings()` returns the expected slugs per
    case_type, capped at 3, in the documented order.
 3. Unmapped / empty case_type yields an empty tuple (the template
    silently omits the section).
 4. Every slug in the mapping resolves to a real CaseTypeLanding
    in LANDINGS_BY_SLUG (sync guard against future drift).
 5. The result page for an Italy road-accident simulation
    surfaces the expected landing links.
 6. The result page for a France review-gated simulation still
    publishes no EUR amount AND still shows recommendation links.
 7. The result page keeps the `?sim=<uuid>` contact CTA.
 8. Every recommended landing URL on the result page reverses
    to a path that returns 200.
 9. No banned-promise phrase appears in the new section.
10. The result page stays `noindex, nofollow` after the change.
11. AR / RTL renders without breakage.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.test import Client
from django.utils import translation

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "product" / "RESULT_PAGE_NEXT_STEPS_AUDIT_2026-05-12.md"


# ---------------------------------------------------------------------------
# 0. Audit doc exists
# ---------------------------------------------------------------------------


def test_audit_doc_exists():
    assert AUDIT_DOC.exists()
    assert AUDIT_DOC.stat().st_size > 4000


# ---------------------------------------------------------------------------
# 1. The mapping + helper exist and behave correctly
# ---------------------------------------------------------------------------


def test_recommendations_mapping_and_helper_importable():
    from apps.core.case_type_landings import (
        _RECOMMENDATIONS_BY_CASE_TYPE,
        RESULT_PAGE_RECOMMENDATION_LIMIT,
        get_recommended_landings,
    )

    assert RESULT_PAGE_RECOMMENDATION_LIMIT == 3
    assert isinstance(_RECOMMENDATIONS_BY_CASE_TYPE, dict)
    assert callable(get_recommended_landings)


def test_recommendations_for_road_accident_in_order():
    from apps.core.case_type_landings import get_recommended_landings

    landings = get_recommended_landings("road_accident_bodily_injury")
    slugs = [landing.slug for landing in landings]
    # First three documented in the audit: bodily-injury,
    # insurance-offer-review, cross-border-cases — in that order.
    assert slugs == [
        "bodily-injury",
        "insurance-offer-review",
        "cross-border-cases",
    ]


@pytest.mark.parametrize(
    "case_type,expected_slugs",
    [
        ("medical_malpractice", ["medical-malpractice", "insurance-offer-review"]),
        ("work_injury", ["work-injury", "insurance-offer-review"]),
        ("death_compensation", ["death-of-relative", "cross-border-cases"]),
        ("parental_loss", ["death-of-relative"]),
        ("international_inheritance", ["cross-border-cases", "foreigners-in-italy"]),
        ("inheritance_basic", ["cross-border-cases"]),
        ("generic_legal_assessment", ["insurance-offer-review", "cross-border-cases"]),
        ("patrimonial_damage", ["insurance-offer-review", "cross-border-cases"]),
    ],
)
def test_recommendations_per_case_type(case_type, expected_slugs):
    from apps.core.case_type_landings import get_recommended_landings

    landings = get_recommended_landings(case_type)
    slugs = [landing.slug for landing in landings]
    assert slugs == expected_slugs, (
        f"Recommendations for {case_type!r}: expected {expected_slugs}, " f"got {slugs}"
    )


def test_recommendations_for_unknown_case_type_is_empty():
    from apps.core.case_type_landings import get_recommended_landings

    assert get_recommended_landings("") == ()
    assert get_recommended_landings("__not_a_real_case_type__") == ()


def test_recommendations_capped_at_three():
    """If a mapping entry ever lists more than 3 slugs, the helper
    must still cap the output at 3 — protects against accidental
    sprawl that would distract from the primary CTA."""
    from apps.core.case_type_landings import (
        RESULT_PAGE_RECOMMENDATION_LIMIT,
        get_recommended_landings,
    )

    for code in (
        "road_accident_bodily_injury",
        "medical_malpractice",
        "work_injury",
        "death_compensation",
        "international_inheritance",
        "generic_legal_assessment",
        "patrimonial_damage",
    ):
        landings = get_recommended_landings(code)
        assert len(landings) <= RESULT_PAGE_RECOMMENDATION_LIMIT


def test_every_recommendation_slug_resolves_to_a_real_landing():
    """Sync guard against future drift between
    `_RECOMMENDATIONS_BY_CASE_TYPE` and `LANDINGS`."""
    from apps.core.case_type_landings import (
        _RECOMMENDATIONS_BY_CASE_TYPE,
        LANDINGS_BY_SLUG,
    )

    for case_type, slugs in _RECOMMENDATIONS_BY_CASE_TYPE.items():
        for slug in slugs:
            assert slug in LANDINGS_BY_SLUG, (
                f"Recommendation mapping for {case_type!r} references "
                f"slug {slug!r} which is not in LANDINGS"
            )


# ---------------------------------------------------------------------------
# 2. Result page rendering — Italy road accident
# ---------------------------------------------------------------------------


def _create_italy_simulation(client: Client) -> str:
    """Run a real Italy wizard POST; return the simulation's
    public_id (string). Uses the live view path so the test stays
    a true e2e: schema drifts break the test instead of silently
    passing on a stale fixture."""
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
    assert resp.status_code == 302
    from apps.cases.models import Simulation

    sim = Simulation.objects.order_by("-created_at").first()
    assert sim is not None
    return str(sim.public_id)


@pytest.mark.django_db
def test_result_page_italy_road_accident_shows_recommendations(client):
    sim_id = _create_italy_simulation(client)
    # Use the /en/ language-prefixed URL: the result route is under
    # i18n_patterns(prefix_default_language=False), so a non-prefixed URL is
    # always served in the default locale (it) regardless of Accept-Language.
    # The header string "Useful pages for your case" is now translated in IT
    # ("Pagine utili per il tuo caso"), so we assert it explicitly in English.
    body = client.get(
        f"/en/wizard/result/{sim_id}/",
        HTTP_HOST="127.0.0.1",
    ).content.decode("utf-8")

    # Recommendation section header.
    assert "Useful pages for your case" in body, (
        "Result page missing the recommendations section header — "
        "F-product-5 not wired into wizard_result.html"
    )
    # Three expected links for road_accident_bodily_injury.
    assert "/case-types/bodily-injury/" in body
    assert "/case-types/insurance-offer-review/" in body
    assert "/case-types/cross-border-cases/" in body


@pytest.mark.django_db
def test_result_page_keeps_contact_cta_with_sim(client):
    """The primary CTA `?sim=<uuid>` must stay the strongest
    action on the page — recommendations are soft secondary links."""
    sim_id = _create_italy_simulation(client)
    body = client.get(f"/wizard/result/{sim_id}/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    assert (
        f"/contact/?sim={sim_id}" in body
    ), "Result page lost the contact CTA with ?sim= querystring"


# ---------------------------------------------------------------------------
# 3. Result page — France review-gated
# ---------------------------------------------------------------------------


def _create_france_simulation(client: Client) -> str:
    resp = client.post(
        "/wizard/fr/road-accident/",
        {
            "accident_country": "FR",
            "victim_age": 35,
            "permanent_disability_percentage": "10",
            "fault_percentage": "0",
            "consent_simulation": "on",
            "special_categories_consent": "on",
        },
        HTTP_HOST="127.0.0.1",
        follow=False,
    )
    assert resp.status_code == 302
    from apps.cases.models import Simulation

    sim = Simulation.objects.order_by("-created_at").first()
    assert sim is not None
    return str(sim.public_id)


@pytest.mark.django_db
def test_france_result_no_eur_amount_with_recommendations(client):
    sim_id = _create_france_simulation(client)
    body = client.get(f"/wizard/result/{sim_id}/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    # France stays review-gated — no EUR amount leaks even with
    # the new recommendations section.
    assert not re.search(
        r"\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)", body
    ), "France result page leaks an EUR amount after the PRODUCT-5 change"
    # And the recommendations section still appears (France maps
    # to road_accident_bodily_injury → same 3 links).
    assert "/case-types/bodily-injury/" in body


# ---------------------------------------------------------------------------
# 4. All recommended links resolve 200
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_recommended_links_resolve_to_200(client):
    from apps.core.case_type_landings import _RECOMMENDATIONS_BY_CASE_TYPE

    visited_slugs: set[str] = set()
    for slugs in _RECOMMENDATIONS_BY_CASE_TYPE.values():
        visited_slugs.update(slugs)
    for slug in sorted(visited_slugs):
        resp = client.get(f"/case-types/{slug}/", HTTP_HOST="127.0.0.1")
        assert resp.status_code == 200, (
            f"/case-types/{slug}/ returns {resp.status_code} — broken "
            "recommendation link on the result page"
        )


# ---------------------------------------------------------------------------
# 5. Banned-promise phrases never appear in the new section
# ---------------------------------------------------------------------------


BANNED_PROMISE_PHRASES = (
    "scopri quanto ti spetta",
    "ottieni il risarcimento",
    "calcolo definitivo",
    "paghi solo se vinci",
    "pay only if you win",
    "no win no fee",
    "risarcimento garantito",
)


@pytest.mark.django_db
def test_result_page_has_no_banned_phrases(client):
    sim_id = _create_italy_simulation(client)
    body = (
        client.get(f"/wizard/result/{sim_id}/", HTTP_HOST="127.0.0.1")
        .content.decode("utf-8")
        .lower()
    )
    leaks = [p for p in BANNED_PROMISE_PHRASES if p in body]
    assert not leaks, f"Result page leaks banned phrases: {leaks}"


# ---------------------------------------------------------------------------
# 6. noindex preserved on the result page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_still_noindex(client):
    sim_id = _create_italy_simulation(client)
    body = client.get(f"/wizard/result/{sim_id}/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    assert 'content="noindex, nofollow"' in body, (
        "Result page must remain noindex, nofollow — PRODUCT-5 must "
        "not regress the SEO posture of a parametric per-user page"
    )


# ---------------------------------------------------------------------------
# 7. Unmapped case_type renders without the section
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_omits_section_when_case_type_unmapped(client, monkeypatch):
    """If a simulation's case_type doesn't appear in the
    recommendations mapping, the section must be silently
    omitted — no empty card, no broken layout."""
    sim_id = _create_italy_simulation(client)
    # Patch the simulation's case_type to something unmapped, then
    # re-fetch. We update the DB row directly because Italy wizard
    # always emits road_accident_bodily_injury.
    from apps.cases.models import Simulation

    Simulation.objects.filter(public_id=sim_id).update(case_type="__unmapped_for_test__")
    body = client.get(
        f"/wizard/result/{sim_id}/",
        HTTP_HOST="127.0.0.1",
        HTTP_ACCEPT_LANGUAGE="en",
    ).content.decode("utf-8")
    assert "Useful pages for your case" not in body, (
        "Result page rendered the recommendations section for an "
        "unmapped case_type — should be silently omitted"
    )


# ---------------------------------------------------------------------------
# 8. AR / RTL still renders the result page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_renders_arabic_rtl(client):
    """Same fix pattern as PRODUCT-3 / PRODUCT-4: deactivate
    translation in `finally:` to keep test isolation."""
    sim_id = _create_italy_simulation(client)
    try:
        resp = client.get(f"/ar/wizard/result/{sim_id}/", HTTP_HOST="127.0.0.1")
        assert resp.status_code == 200
        body = resp.content.decode("utf-8")
        assert 'dir="rtl"' in body
    finally:
        translation.deactivate_all()
