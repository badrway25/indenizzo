"""P25 — guard the professional product overhaul.

Locks the analytical pre-check intelligence (dossier status, solid vs. attention
signals, legal-path reasoning, categorised document checklist), the guided-router
pre-click preview, and the analytical result shell, so they cannot regress to a
flat readiness signal.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

from apps.core.precheck import get_precheck
from apps.core.precheck_engine import (
    DOC_ESSENTIAL,
    STATUS_CONSOLIDATING,
    STATUS_READY,
    evaluate,
)

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


def _post(slug, data, lang="it"):
    return Client().post(f"/precheck/{slug}/", data, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- Engine: analytical layer is populated --------------------------------
def test_result_carries_the_full_analytical_layer():
    flow = get_precheck("inail")
    r = evaluate(flow, {"impairment_pct": "10", "medical_cert": "yes", "employer_docs": "yes"})
    # the analytical fields the result shell renders
    assert r.result_status == STATUS_READY
    assert str(r.result_status_label)
    assert str(r.dossier_summary)
    assert r.strong_points  # solid data was detected
    assert str(r.path_reason)
    assert str(r.assessable_now) and str(r.pending_for_estimate)
    assert r.documents_by_category  # categorised, not a flat list


def test_inail_grade_bands_are_specific():
    flow = get_precheck("inail")
    cap = evaluate(flow, {"impairment_pct": "10"})
    ann = evaluate(flow, {"impairment_pct": "30"})
    cap_txt = " ".join(str(m) for m in cap.messages)
    ann_txt = " ".join(str(m) for m in ann.messages)
    assert "capital" in cap_txt.lower()         # 6–15 band → capital indemnity
    assert "annuity" in ann_txt.lower() or "rendita" in ann_txt.lower()  # >15 → annuity
    # a third-party answer adds a secondary action (differential beyond INAIL)
    third = evaluate(flow, {"impairment_pct": "10", "third_party_liability": "yes"})
    assert str(third.secondary_cta_label)


def test_inail_attention_flags_missing_essentials():
    flow = get_precheck("inail")
    r = evaluate(flow, {"impairment_pct": "10", "medical_cert": "no", "employer_docs": "no"})
    assert r.result_status != STATUS_READY
    assert r.attention_points  # missing essentials surface as points to verify


@pytest.mark.parametrize("slug,answers", [
    ("morocco-road-accident", {"injury_or_death": "injury", "police_report": "yes",
                               "medical_cert": "yes", "ipp_known": "yes",
                               "income_documentable": "yes", "liability_estimate": "full"}),
    ("tunisia-road-accident", {"injury_or_death": "injury", "police_report": "yes",
                               "medical_cert": "yes", "ipp_known": "yes",
                               "income_documentable": "yes"}),
])
def test_road_ready_dossier_has_strong_points_and_path(slug, answers):
    flow = get_precheck(slug)
    r = evaluate(flow, answers)
    assert r.result_status == STATUS_READY
    assert len(r.strong_points) >= 3              # incapacity, income, report…
    assert str(r.path_reason) and str(r.pending_for_estimate)
    assert not _MONEY.search(" ".join(str(x) for x in r.messages))


def test_road_partial_dossier_consolidating():
    flow = get_precheck("morocco-road-accident")
    r = evaluate(flow, {"injury_or_death": "injury", "police_report": "yes",
                        "medical_cert": "no", "ipp_known": "no",
                        "income_documentable": "no"})
    assert r.result_status == STATUS_CONSOLIDATING
    assert r.attention_points


def test_loss_relative_output_is_parental_specific():
    flow = get_precheck("loss-of-relative")
    r = evaluate(flow, {"country": "IT", "death_cause": "road_accident",
                        "relationship": "spouse", "civil_docs": "yes", "offer_received": "yes"})
    txt = (str(r.path_reason) + str(r.assessable_now) + str(r.pending_for_estimate)).lower()
    assert "parental" in txt or "affection" in txt or "relationship" in txt or "parentale" in txt
    # a foreign country re-routes the primary CTA to applicable-law framing
    foreign = evaluate(flow, {"country": "FR", "civil_docs": "yes"})
    assert foreign.cta_url_name == "core:precheck"
    assert foreign.cta_kwargs.get("slug") == "international-road-accident"


# --- Document checklist is categorised ------------------------------------
def test_document_checklist_is_categorised_with_reasons():
    flow = get_precheck("morocco-road-accident")
    r = evaluate(flow, {"injury_or_death": "injury", "police_report": "yes", "medical_cert": "no"})
    cats = [str(label) for label, _ in r.documents_by_category]
    assert len(cats) >= 1
    # every essential item carries a purpose ("reason") and a present flag
    essentials = [d for d in r.document_items if d.category == DOC_ESSENTIAL]
    assert essentials and all(str(d.reason) for d in essentials)
    assert any(d.present for d in r.document_items)  # the police report is marked present


# --- Rendered result shell ------------------------------------------------
@pytest.mark.django_db
def test_precheck_result_renders_analytical_shell():
    body = _post("inail", {"impairment_pct": "10", "medical_cert": "yes", "employer_docs": "no"})
    assert 'id="precheck-result"' in body
    assert not _MONEY.search(body)
    # IT analytical section headers
    for it_label in ("Analisi del dossier", "Percorso legale", "Checklist dei documenti",
                     "Cosa possiamo valutare ora"):
        assert it_label in body, f"result missing {it_label!r}"
    # categorised checklist headers
    assert "Essenziali" in body


@pytest.mark.django_db
def test_precheck_result_has_contextual_ctas():
    # INAIL + third-party liability → primary + secondary CTA both present
    body = _post("inail", {"impairment_pct": "10", "medical_cert": "yes",
                           "employer_docs": "yes", "third_party_liability": "yes"})
    # two distinct premium buttons in the result CTA group
    assert body.count("premium-btn") >= 2


# --- Guided router pre-click preview --------------------------------------
@pytest.mark.django_db
def test_guided_router_shows_preview_meta():
    body = _get("/guided/")
    assert "Fonte" in body          # main source label
    assert "Tempo" in body          # indicative time label
    assert "Dahir 1-84-177" in body  # a real normative reference
    assert "minuti" in body         # indicative time value (IT)
    assert not _MONEY.search(body)
    assert body.count("<h1") == 1


# --- No regressions: no money / slug / weak states ------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("slug", [
    "inail", "loss-of-relative", "morocco-road-accident",
    "tunisia-road-accident", "international-road-accident",
])
def test_precheck_results_clean(slug):
    body = _post(slug, {"injury_or_death": "injury", "police_report": "yes"})
    assert not _MONEY.search(body)
    low = body.lower()
    for tok in ("in revisione", "non disponibile", "da validare", "roadmap",
                "placeholder", "manual review", "needs review"):
        assert tok not in low, f"{slug} leaks {tok!r}"
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                     re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)))
    assert not re.search(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b", visible), f"{slug} leaks snake_case"


# --- Catalogs fuzzy-free --------------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
