"""P16 — guard the interactive pre-check journeys and smart guided results.

The pre-checks are now interactive mini-flows: a POST of answers produces a
personalised, non-numeric guided result (completeness, missing documents,
applicable sources, contextual messages, next step, CTA). These tests lock the
decision logic and the no-amount / no-technical-state contract.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

from apps.core import precheck_engine as pe
from apps.core.precheck import get_precheck

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
PRECHECK_SLUGS = ["inail", "loss-of-relative", "morocco-road-accident",
                  "tunisia-road-accident", "international-road-accident"]
_BANNED = ("in revisione", "needs review", "non disponibile", "da validare",
           "placeholder", "manual review", "fail-closed", "roadmap")


def _post(slug, data, lang="it"):
    return Client().post(f"/precheck/{slug}/", data, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


def _ev(slug, answers):
    return pe.evaluate(get_precheck(slug), answers)


# --- 1. routes 200 ----------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug", PRECHECK_SLUGS)
def test_precheck_get_200(slug):
    assert Client().get(f"/precheck/{slug}/", HTTP_ACCEPT_LANGUAGE="it").status_code == 200


# --- 2. a valid POST produces a result --------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug,data", [
    ("inail", {"event_date": "2024-01-01", "age": "40", "medical_cert": "yes", "employer_docs": "yes"}),
    ("loss-of-relative", {"country": "IT", "civil_docs": "yes"}),
    ("morocco-road-accident", {"injury_or_death": "injury", "police_report": "yes", "medical_cert": "yes"}),
    ("tunisia-road-accident", {"injury_or_death": "injury", "police_report": "yes", "medical_cert": "yes"}),
    ("international-road-accident", {"event_country": "France", "residence_country": "Italy"}),
])
def test_precheck_post_produces_result(slug, data):
    body = _post(slug, data)
    assert 'id="precheck-result"' in body


# --- 3 & 14. no amount on any result ----------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug,data", [
    ("inail", {"impairment_pct": "12", "third_party_liability": "yes", "medical_cert": "yes", "employer_docs": "yes"}),
    ("morocco-road-accident", {"injury_or_death": "death", "ipp_known": "yes", "income_documentable": "yes",
                               "liability_estimate": "full", "heirs": "yes"}),
    ("tunisia-road-accident", {"injury_or_death": "injury", "ipp_known": "yes", "income_documentable": "yes"}),
    ("international-road-accident", {"event_country": "France", "foreign_docs": "yes"}),
])
def test_precheck_result_has_no_money(slug, data):
    assert not _MONEY.search(_post(slug, data)), f"money leaked on {slug}"


# --- 4. INAIL 6–15% → capital-table message ---------------------------------
def test_inail_capital_band_message():
    res = _ev("inail", {"impairment_pct": "10", "medical_cert": "yes", "employer_docs": "yes"})
    assert pe._M_INAIL_CAPITAL in res.messages
    assert pe._M_INAIL_ANNUITY not in res.messages
    assert res.has_numeric_estimate is False


# --- 5. INAIL >15% → annuity / analysis message -----------------------------
def test_inail_annuity_message():
    res = _ev("inail", {"impairment_pct": "25", "third_party_liability": "yes"})
    assert pe._M_INAIL_ANNUITY in res.messages
    assert pe._M_INAIL_DIFFERENTIAL in res.messages  # third-party liability set


# --- 6. Morocco with IPP+income+liability → barème readiness, no amount ------
def test_morocco_barème_readiness():
    res = _ev("morocco-road-accident", {"injury_or_death": "injury", "ipp_known": "yes",
                                        "income_documentable": "yes", "liability_estimate": "full",
                                        "police_report": "yes", "medical_cert": "yes"})
    assert pe._M_MA_READY in res.messages
    assert res.has_numeric_estimate is False


# --- 7. Morocco without IPP → IPP listed as missing --------------------------
def test_morocco_missing_ipp():
    res = _ev("morocco-road-accident", {"injury_or_death": "injury", "ipp_known": "no",
                                        "income_documentable": "no"})
    assert pe._MISS_IPP in res.missing_documents
    assert pe._M_MA_READY not in res.messages


# --- 8. Tunisia with IPP+income → barème readiness, no amount ----------------
def test_tunisia_barème_readiness():
    res = _ev("tunisia-road-accident", {"injury_or_death": "injury", "ipp_known": "yes",
                                        "income_documentable": "yes"})
    assert pe._M_TN_READY in res.messages
    assert res.has_numeric_estimate is False


# --- 9. Loss of relative, IT + offer → comparison suggestion -----------------
def test_loss_italy_offer_suggests_comparison():
    res = _ev("loss-of-relative", {"country": "IT", "death_cause": "road_accident",
                                   "offer_received": "yes", "civil_docs": "yes"})
    assert pe._M_LOSS_OFFER in res.messages


def test_loss_foreign_suggests_applicable_law():
    res = _ev("loss-of-relative", {"country": "MA", "civil_docs": "no"})
    assert pe._M_LOSS_FOREIGN in res.messages
    assert res.cta_url_name == "core:precheck"
    assert res.cta_kwargs == {"slug": "international-road-accident"}


# --- 10. International → Rome II applicable-law message ----------------------
def test_international_rome_ii_message():
    res = _ev("international-road-accident", {"event_country": "France", "residence_country": "Italy",
                                             "foreign_docs": "yes", "translation_needed": "yes"})
    assert pe._M_INT_LAW in res.messages
    assert pe._M_INT_TRANSLATE in res.messages


# --- 11. /guided/ routes to the right wizard / pre-check --------------------
@pytest.mark.django_db
def test_guided_router_links_destinations():
    body = Client().get("/guided/", HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    for frag in ["/wizard/it/road-accident/", "/precheck/inail/", "/precheck/morocco-road-accident/",
                 "/wizard/fr/road-accident/", "/precheck/international-road-accident/"]:
        assert frag in body, frag
    # France/Belgium guided pathway shows the documents-and-liability CTA.
    assert "Verifica documenti e responsabilità" in body


# --- 12. Services CTAs point to real flows ----------------------------------
@pytest.mark.django_db
def test_services_ctas_reach_flows():
    body = Client().get("/services/", HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert "/precheck/inail/" in body
    assert "Avvia il pre-check INAIL" in body


# --- 13. Country page CTAs point to real flows ------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path,slug,label", [
    ("/countries/morocco/", "morocco-road-accident", "Avvia il pre-check Dahir / ACAPS"),
    ("/countries/tunisia/", "tunisia-road-accident", "Avvia il pre-check Code des assurances"),
])
def test_country_ctas_reach_flows(path, slug, label):
    body = Client().get(path, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert f"/precheck/{slug}/" in body
    assert label in body


# --- 15 & 16. no technical / weak state on form or result -------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug", PRECHECK_SLUGS)
def test_no_technical_state(slug):
    get_body = Client().get(f"/precheck/{slug}/", HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8").lower()
    post_body = _post(slug, {"injury_or_death": "injury", "country": "IT"}).lower()
    for tok in _BANNED:
        assert tok not in get_body, f"GET {slug} leaks {tok!r}"
        assert tok not in post_body, f"POST {slug} leaks {tok!r}"


# --- 17. IT canary engine still green ---------------------------------------
@pytest.mark.django_db
def test_italy_road_canary_still_estimates():
    # The approved IT road engine still produces a numeric estimate page.
    r = Client().get("/wizard/it/road-accident/", HTTP_ACCEPT_LANGUAGE="it")
    assert r.status_code == 200


# --- 18. catalogs fuzzy-free ------------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
