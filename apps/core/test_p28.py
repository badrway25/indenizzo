"""P28 — guard the smart dossier, print and result-aware lead capture.

Locks the unified DossierSummary across estimates and pre-checks, the
print-ready dossier panel + CSS, the result-aware contact CTA and its captured
origin payload, and the privacy/honeypot/no-email-in-test contracts.
"""

from __future__ import annotations

import re
from pathlib import Path
from types import SimpleNamespace

import pytest
from django.conf import settings
from django.core import mail
from django.test import Client

from apps.core.dossier import (
    KIND_COMPARISON,
    KIND_ESTIMATE,
    KIND_PRE_CHECK,
    from_estimate,
    from_precheck,
)
from apps.core.precheck import get_precheck
from apps.core.precheck_engine import evaluate

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


def _fake_sim(case_type, **kw):
    base = dict(case_type=case_type, estimated_min=1000, estimated_mid=2000,
               estimated_max=3000, currency="EUR", public_id="11111111-1111-1111-1111-111111111111",
               country_id=1, country=SimpleNamespace(code="IT"))
    base.update(kw)
    return SimpleNamespace(**base)


# --- DossierSummary across every result type ------------------------------
def test_dossier_for_road_estimate():
    d = from_estimate(_fake_sim("road_accident_bodily_injury"), has_estimate=True,
                      sources=[{"title": "art. 139 CAP"}], missing_documents=[],
                      offer_comparison=None, assumptions=["a"], language="it")
    assert d.flow_type == "road_estimate" and d.result_kind == KIND_ESTIMATE
    assert d.can_calculate_amount and d.amount_summary  # real engine figure
    assert d.primary_cta.query.get("sim")


def test_dossier_for_medical_estimate():
    d = from_estimate(_fake_sim("medical_liability_biological_damage"), has_estimate=True,
                      sources=[], missing_documents=[], offer_comparison=None,
                      assumptions=[], language="it")
    assert d.flow_type == "medical_estimate" and d.result_kind == KIND_ESTIMATE


def test_dossier_for_offer_comparison():
    d = from_estimate(_fake_sim("road_accident_bodily_injury"), has_estimate=True,
                      sources=[], missing_documents=[],
                      offer_comparison={"offer": 1}, assumptions=[], language="it")
    assert d.flow_type == "offer_comparison" and d.result_kind == KIND_COMPARISON


def test_dossier_for_inail_precheck():
    flow = get_precheck("inail")
    r = evaluate(flow, {"impairment_pct": "12", "medical_cert": "yes", "employer_docs": "no"})
    d = from_precheck(flow, r, "it")
    assert d.flow_type == "inail" and d.category == "work_injury"
    assert d.result_kind == KIND_PRE_CHECK
    assert not d.can_calculate_amount and d.amount_summary == ""  # engine-less → no money
    assert d.data_used and d.documents_missing and d.official_sources
    assert d.primary_cta.query == {"flow": "inail", "result_kind": "pre_check",
                                   "readiness": d.readiness_level, "country": "IT",
                                   "category": "work_injury"}


def test_dossier_for_morocco_precheck():
    flow = get_precheck("morocco-road-accident")
    r = evaluate(flow, {"injury_or_death": "injury", "police_report": "yes", "ipp_known": "yes"})
    d = from_precheck(flow, r, "it")
    assert d.flow_type == "morocco_road" and d.country == "MA"
    assert not d.can_calculate_amount and d.amount_summary == ""


# --- Rendered dossier panel: print + contact CTA --------------------------
@pytest.mark.django_db
def test_precheck_result_renders_dossier_panel_with_print_and_send():
    body = Client().post("/precheck/inail/",
                         {"impairment_pct": "12", "medical_cert": "yes", "employer_docs": "no"},
                         HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert 'data-print="dossier"' in body          # print button
    assert "Stampa il riepilogo" in body           # IT print label
    assert "Consolida il dossier" in body          # panel title
    assert "/contact/?flow=inail" in body          # result-aware send CTA
    assert "dossier-print" in body                 # printable region
    assert not _MONEY.search(body)


def test_print_css_isolates_the_dossier():
    css = (Path(settings.BASE_DIR) / "static" / "css" / "site.css").read_text("utf-8")
    assert "@media print" in css
    assert ".printing-dossier .dossier-print" in css  # dossier-only print isolation


def test_estimate_result_template_includes_dossier_panel():
    src = (Path(settings.BASE_DIR) / "templates" / "public" / "wizard_result.html").read_text("utf-8")
    assert "_dossier_panel.html" in src


# --- Lead capture: consent, honeypot, captured origin, no email in test ----
@pytest.mark.django_db
def test_contact_requires_privacy_consent():
    # missing privacy_accepted → no Lead, form re-rendered (200, not 302)
    from apps.crm.models import Lead
    resp = Client().post("/contact/", {
        "first_name": "A", "last_name": "B", "email": "a@b.com", "preferred_language": "it",
        "message": "A sufficiently long message about my dossier please review it.",
        "special_categories_accepted": "on", "website": "",
    })
    assert resp.status_code == 200
    assert Lead.objects.count() == 0


@pytest.mark.django_db
def test_honeypot_blocks_spam_lead():
    from apps.crm.models import Lead
    resp = Client().post("/contact/", {
        "first_name": "A", "last_name": "B", "email": "a@b.com", "preferred_language": "it",
        "message": "A sufficiently long message about my dossier please review it.",
        "privacy_accepted": "on", "special_categories_accepted": "on",
        "website": "http://spam.example",  # honeypot filled
    })
    assert resp.status_code == 302  # redirected to thank-you (trap hidden)
    assert Lead.objects.count() == 0  # but no Lead created


@pytest.mark.django_db
def test_lead_captures_dossier_origin_and_sends_no_email():
    from apps.crm.models import Lead, LeadEvent
    mail.outbox = []
    resp = Client().post(
        "/contact/?flow=inail&result_kind=pre_check&readiness=consolidating",
        {"first_name": "M", "last_name": "R", "email": "m@r.com", "preferred_language": "it",
         "message": "Please verify my INAIL documental dossier, thank you very much.",
         "privacy_accepted": "on", "special_categories_accepted": "on", "website": ""})
    assert resp.status_code == 302
    lead = Lead.objects.order_by("-created_at").first()
    ev = LeadEvent.objects.filter(lead=lead, event_type=LeadEvent.EventType.CREATED).first()
    assert ev.metadata.get("flow") == "inail"
    assert ev.metadata.get("result_kind") == "pre_check"
    assert ev.metadata.get("readiness") == "consolidating"
    # no real email sent in test (LEAD_NOTIFICATION_TO_EMAILS empty by default)
    assert mail.outbox == []
    # double consent recorded
    assert lead.privacy_consent_given and lead.special_categories_consent_given


@pytest.mark.django_db
def test_thank_you_page_200():
    assert Client().get("/contact/thank-you/").status_code == 200


# --- No technical data / RTL / canaries -----------------------------------
@pytest.mark.django_db
def test_dossier_panel_leaks_no_slug_or_money():
    body = Client().post("/precheck/morocco-road-accident/",
                         {"injury_or_death": "injury", "police_report": "yes"},
                         HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert not _MONEY.search(body)
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                     re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)))
    assert not re.search(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b", visible)


@pytest.mark.django_db
def test_arabic_precheck_result_200_rtl():
    resp = Client().post("/ar/precheck/inail/",
                         {"impairment_pct": "12", "medical_cert": "yes", "employer_docs": "no"},
                         HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200
    assert 'dir="rtl"' in resp.content.decode("utf-8")


def test_engine_registry_canaries_intact():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
