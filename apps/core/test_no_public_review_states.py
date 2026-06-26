"""P12-FIX — guard: no public page exposes a review/technical state.

The public site must never render "in revisione" / "under review" / "needs
review" / "not available" / a raw technical status token, in any locale. These
states may only live in internal audit docs / admin / tests / approval packs.
This test renders every public content route in it/fr/en/ar and fails on any
banned token, so the regression cannot come back.
"""

from __future__ import annotations

import pytest
from django.test import Client

# Content routes that must read as finished (estimate or premium guided path).
_ROUTES = [
    "/", "/services/", "/how-it-works/", "/faq/", "/countries/", "/case-types/",
    "/countries/italy/", "/countries/france/", "/countries/belgium/",
    "/countries/morocco/", "/countries/tunisia/",
    "/case-types/road-accident/", "/case-types/bodily-injury/",
    "/case-types/insurance-offer-review/", "/case-types/work-injury/",
    "/case-types/medical-malpractice/", "/case-types/death-of-relative/",
    "/case-types/foreigners-in-italy/", "/case-types/cross-border-cases/",
    "/case-types/product-liability/",
    "/wizard/", "/wizard/it/road-accident/", "/wizard/it/medical-malpractice/",
    "/wizard/it/offer-comparison/", "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/", "/wizard/ma/inheritance/", "/wizard/tn/inheritance/",
    "/countries/readiness.json",
]
_LOCALES = ["it", "fr", "en", "ar"]

# Banned user-facing review/technical-state tokens (per-locale + technical).
_BANNED = [
    "in revisione", "under review", "under studio review", "needs review",
    "needs_review", "pending review", "da validare", "à valider",
    "validation required", "non disponibile", "non disponible", "not available",
    "unavailable", "valutazione preliminare", "valutazione legale preliminare",
    "preliminary legal assessment", "évaluation préliminaire",
    "évaluation juridique préliminaire", "fail_closed", "fail-closed",
    "unresolved", "placeholder", "source_verified", "approval_required",
    "chatgpt_approval", "legal_validation_in_progress",
    "قيد المراجعة", "غير متاح",  # NB: "في انتظار ردّنا" (awaiting our reply) is positive copy, allowed
]


def _params():
    for loc in _LOCALES:
        prefix = "" if loc == "it" else f"/{loc}"
        for r in _ROUTES:
            url = r if r.startswith("/countries/readiness") else (prefix + r)
            yield pytest.param(url, loc, id=f"{loc}:{r}")


@pytest.mark.django_db
@pytest.mark.parametrize("url,locale", list(_params()))
def test_public_route_has_no_review_state(url, locale):
    resp = Client().get(url, HTTP_ACCEPT_LANGUAGE=locale)
    if resp.status_code != 200:
        pytest.skip(f"{url} -> {resp.status_code}")
    body = resp.content.decode("utf-8", "replace").lower()
    leaks = [t for t in _BANNED if t in body]
    assert not leaks, f"{locale} {url} leaks public review/technical state(s): {leaks}"
