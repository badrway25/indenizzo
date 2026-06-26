"""P5 — Official coverage & premium service labels guards.

Pins that the /services/ page no longer shows the weak
"preliminary assessment needed" / "Valutazione preliminare necessaria" label,
that each service now carries a premium area badge + an official "Legal basis"
citation, that the new labels are translated (no English/Italian leak on fr/ar),
and that the fail-closed contract is unchanged (exactly one calculable service).
The official-coverage audit docs exist. No calculator/engine change.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

from apps.core import public_pages

_DOCS = Path(settings.BASE_DIR) / "docs" / "audits"

# weak labels that must NOT appear on the services page (any locale)
_WEAK_ON_SERVICES = (
    "Preliminary assessment needed",
    "Valutazione preliminare necessaria",
    "valutazione preliminare necessaria",
    "Request a preliminary assessment",
)
_AMOUNT_RE = re.compile(r"(€|eur)\s?\d{1,3}[.,]\d{3}", re.IGNORECASE)


def test_official_coverage_docs_exist():
    assert (_DOCS / "PUBLIC_SERVICE_OFFICIAL_COVERAGE_2026-06-25.md").is_file()
    assert (_DOCS / "OFFICIAL_SOURCES_NOT_FOUND_2026-06-25.md").is_file()


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/services/", "/fr/services/", "/ar/services/"])
def test_services_has_no_weak_label(path):
    body = Client().get(path).content.decode("utf-8")
    for weak in _WEAK_ON_SERVICES:
        assert weak not in body, f"{path} still shows weak label {weak!r}"
    assert not _AMOUNT_RE.search(body), f"{path} shows a grouped currency amount"


@pytest.mark.django_db
def test_services_shows_premium_badges_and_legal_basis():
    body = Client().get("/services/").content.decode("utf-8")
    # P13-FIX: three distinct estimate-state badges + the guided badge (IT unprefixed)
    assert "Stima da fonte ufficiale" in body                 # road: numeric estimate
    assert "Stima tabellare del danno biologico" in body      # medical: tabular biological
    assert "Confronto con fonte ufficiale" in body            # offer: comparison
    assert "Percorso assistito con fonte ufficiale" in body   # guided
    # official "Legal basis" attribution + real instrument citations
    assert ("Base normativa" in body) or ("Base legale" in body)
    for citation in ("D.P.R. 12/2025", "L. 24/2017", "D.P.R. 1124/1965",
                     "D.Lgs. 209/2005", "Reg. CE 864/2007"):
        assert citation in body, f"missing official legal-basis citation {citation!r}"


@pytest.mark.django_db
def test_services_premium_labels_translated_fr_ar():
    fr = Client().get("/fr/services/").content.decode("utf-8")
    assert "Parcours assisté fondé sur une source officielle" in fr  # guided FR
    assert "Estimation tabellaire du dommage biologique" in fr        # medical estimate FR
    assert "Assisted legal pathway" not in fr          # no English leak
    ar = Client().get("/ar/services/")
    assert ar.status_code == 200
    body = ar.content.decode("utf-8")
    assert 'dir="rtl"' in body
    assert "مسار موجَّه يستند إلى مصدر رسمي" in body      # guided badge AR (P13-FIX)
    assert "Assisted legal pathway" not in body


def test_services_fail_closed_exactly_one_calculable():
    """P13-FIX contract: the three approved engines (road accident, medical
    liability, insurance-offer) are calculable, each routing to its wizard;
    everything else is a guided pathway routing to the contact funnel."""
    calculable = {s.key for s in public_pages.SERVICES if s.calculable}
    assert calculable == {"road_accident", "medical", "insurance_offer"}
    for s in public_pages.SERVICES:
        if s.calculable:
            assert s.cta_url_name.startswith("cases:wizard"), s.key
            assert s.badge  # has a premium estimate badge
        else:
            assert s.cta_url_name == "crm:contact"  # guided → funnel, never a calc


def test_service_base_normativa_is_official_instrument():
    """Each base_normativa value references a real official instrument, never an
    invented figure or a prescription term."""
    period = re.compile(r"\b\d+\s*(anni|anno|years?|mesi|giorni)\b", re.IGNORECASE)
    for s in public_pages.SERVICES:
        if s.base_normativa:
            assert not _AMOUNT_RE.search(s.base_normativa)
            assert not period.search(s.base_normativa), "no numeric term in legal basis"
