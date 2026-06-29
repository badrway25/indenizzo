"""P22 — guard the bespoke page-by-page redesign.

Locks the new, dedicated sections so a future change can't quietly flatten the
front-door pages back into a generic card list: the home product sections, the
grouped services page, and the guided-router cockpit stepper.
"""

from __future__ import annotations

import re

import pytest
from django.test import Client

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- Home: dedicated product sections ---------------------------------------
@pytest.mark.django_db
def test_home_has_estimate_and_precheck_sections():
    body = _get("/")
    # "what you can estimate today" — links the three live engines
    assert "Cosa puoi stimare oggi" in body
    assert "/wizard/it/road-accident/" in body
    assert "/wizard/it/medical-malpractice/" in body
    assert "/wizard/it/offer-comparison/" in body
    # documental pre-checks block — links the guided flows
    assert "Pre-check guidati" in body
    assert "/precheck/inail/" in body
    assert "/precheck/morocco-road-accident/" in body
    assert "/guided/" in body
    # the home never shows an invented amount
    assert not _MONEY.search(body)


# --- Services: grouped sections, not a flat list ----------------------------
@pytest.mark.django_db
def test_services_is_grouped_into_sections():
    body = _get("/services/")
    # P26: 3 journey-selector groups (comparison merged into "Available estimates").
    for group in ("Stime disponibili", "Pre-check documentali",
                  "Casi transfrontalieri e clienti esteri"):
        assert group in body, group
    # the grouping helper returns ordered, non-empty sections covering all 8 services
    from apps.core import public_pages
    groups = public_pages.grouped_services()
    assert len(groups) == 3
    covered = sum(len(g["services"]) for g in groups)
    assert covered == len(public_pages.SERVICES)
    # each group now carries its own CTA
    assert all(g["cta_label"] and g["cta_url_name"] for g in groups)


# --- Guided router: cockpit stepper -----------------------------------------
@pytest.mark.django_db
def test_guided_router_has_stepper_cockpit():
    body = _get("/guided/")
    assert "Come funziona l'instradamento guidato" in body  # stepper aria-label
    # P39: the cockpit is now a four-step visual path (Country/Case/Documents/Result).
    assert "Caso" in body and "Risultato" in body            # path steps 2 & 4
    assert "Passo 1" in body                                 # step labelling
    # the four step medallions render
    assert body.count("icon-medallion") >= 4


# --- No regression: redesigned pages stay clean -----------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/services/", "/guided/"])
def test_redesigned_pages_no_money_no_weak_state(path):
    body = _get(path)
    assert not _MONEY.search(body)
    low = body.lower()
    for tok in ("in revisione", "non disponibile", "da validare", "roadmap",
                "placeholder", "manual review"):
        assert tok not in low, f"{path} leaks {tok!r}"
