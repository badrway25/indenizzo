"""P31 — guard the multi-document AI dossier flow.

Covers multi-file intake, structured extraction (redacted), dossier aggregation,
universal routing, the non-public dev diagnostic, security (no key/content in
logs or HTML), premium UI hooks and i18n/RTL hygiene. OpenAI is always mocked —
no real network call and no real key ever reaches a test.
"""

from __future__ import annotations

import logging
import re
from dataclasses import replace
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse

from apps.core import document_ai as dai

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
_FORBIDDEN = ("crm", "lead", "pipeline", "debug", "in revisione", "non disponibile",
              "da validare", "manual review", "placeholder", "openai", "api_key",
              "fallback", "dev_mode")


def _pdf(name="referto.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake", content_type="application/pdf")


def _post(files, extra=None, lang="it"):
    data = {"document": files, "analysis_consent": "on", "website": ""}
    data.update(extra or {})
    return Client().post("/documents/upload/", data, HTTP_ACCEPT_LANGUAGE=lang)


# --- Multi-file intake ------------------------------------------------------
@pytest.mark.django_db
def test_single_pdf_accepted():
    body = _post([_pdf("offerta.pdf")]).content.decode()
    assert 'id="document-result"' in body


@pytest.mark.django_db
def test_multiple_files_accepted_and_aggregated():
    files = [_pdf("offerta.pdf"), _pdf("referto.pdf"),
             SimpleUploadedFile("foto.png", b"\x89PNG", content_type="image/png")]
    body = _post(files).content.decode()
    assert 'id="document-result"' in body
    # all three files appear as per-file cards
    for n in ("offerta.pdf", "referto.pdf", "foto.png"):
        assert n in body


@pytest.mark.django_db
def test_max_files_cap_enforced():
    n = settings.DOCUMENT_INTAKE_MAX_FILES + 1
    files = [_pdf(f"doc{i}.pdf") for i in range(n)]
    body = _post(files).content.decode()
    assert 'id="document-result"' not in body  # rejected, nothing analysed


# --- Security: validation ---------------------------------------------------
@pytest.mark.django_db
def test_invalid_type_rejected():
    bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/x-msdownload")
    assert 'id="document-result"' not in _post([bad]).content.decode()


@pytest.mark.django_db
def test_oversized_rejected():
    big = SimpleUploadedFile(
        "big.pdf", b"%PDF" + b"x" * (settings.DOCUMENT_INTAKE_MAX_UPLOAD_MB * 1024 * 1024 + 10),
        content_type="application/pdf")
    assert 'id="document-result"' not in _post([big]).content.decode()


@pytest.mark.django_db
def test_missing_consent_and_honeypot_rejected():
    body = Client().post("/documents/upload/", {"document": [_pdf()], "website": ""}).content.decode()
    assert 'id="document-result"' not in body
    body = _post([_pdf()], {"website": "http://spam"}).content.decode()
    assert 'id="document-result"' not in body


# --- Fallback + OpenAI mock -------------------------------------------------
def test_fallback_local_classifies():
    a = dai.analyze_document(filename="referto.pdf", mime="application/pdf", size=1)
    assert a.provider == "local" and a.type_key == "it_medical_report"


def test_openai_mock_classifies_and_extracts_structured(monkeypatch):
    base = dai._build(dai._BY_KEY["it_insurance_offer"], dai.CONF_STRONG, provider="openai")
    enriched = replace(base, detected_pairs=(
        (dai._E_EVENT_DATE, "2024-03-01"), (dai._E_OFFER_PRESENT, dai._E_YES)))
    monkeypatch.setattr(dai, "_analyze_openai", lambda *a, **k: enriched)
    a = dai.analyze_document(filename="whatever.pdf", mime="application/pdf", size=1)
    assert a.provider == "openai"
    assert ("2024-03-01" in dict((str(k), v) for k, v in a.detected_pairs).values())


def test_structured_extraction_is_redacted():
    pairs = dai._pairs_from_extraction({
        "event_date": "2024-03-01", "age": "45", "impairment_percent": "12%",
        "offer_present": True, "income_present": False, "insurer_present": True,
        "full_name": "Mario Rossi", "plate": "AB123CD", "amount": 18500,
    })
    flat = " ".join(f"{k}={v}" for k, v in pairs)
    assert "Mario Rossi" not in flat and "AB123CD" not in flat  # personal data dropped
    assert "18500" not in flat  # raw amounts never surfaced, only presence flags
    keys = {str(k) for k, _ in pairs}
    assert str(dai._E_OFFER_PRESENT) in keys and str(dai._E_INSURER_PRESENT) in keys
    assert str(dai._E_INCOME_PRESENT) not in keys  # False → omitted


def test_openai_disabled_uses_fallback():
    assert not settings.OPENAI_DOCUMENT_AI_ENABLED
    a = dai.analyze_document(filename="referto.pdf", mime="application/pdf", size=1)
    assert a.provider == "local"


def test_openai_error_falls_back(monkeypatch):
    monkeypatch.setattr(dai, "_analyze_openai", lambda *a, **k: None)
    a = dai.analyze_document(filename="referto.pdf", mime="application/pdf", size=1)
    assert a.provider == "local"


def test_openai_inert_without_key():
    assert dai._analyze_openai("f.pdf", "application/pdf", country="", category="") is None


# --- Dev diagnostic (non-public) -------------------------------------------
def test_dev_status_shape_and_no_key():
    sentinel = "sk-THISKEY-must-never-leak-123"
    with override_settings(OPENAI_DOCUMENT_AI_ENABLED=True, OPENAI_API_KEY=sentinel):
        st = dai.dev_status()
    assert st["ai_enabled"] is True and st["key_present"] is True
    assert st["fallback_available"] is True
    # the key must NOT appear anywhere in the diagnostic, not even partially
    assert sentinel not in str(st)
    assert "sk-THISKEY" not in str(st)


@pytest.mark.django_db
def test_dev_details_never_rendered_public(monkeypatch):
    sentinel = "sk-PUBLICLEAK-must-never-appear"
    monkeypatch.setattr(dai, "_analyze_openai", lambda *a, **k: None)  # no network
    with override_settings(OPENAI_DOCUMENT_AI_ENABLED=True, OPENAI_API_KEY=sentinel,
                           OPENAI_DOCUMENT_AI_MODEL="gpt-secret-model"):
        body = _post([_pdf("offerta.pdf")]).content.decode()
    assert sentinel not in body
    assert "gpt-secret-model" not in body  # model name is internal too
    low = re.sub(r"<[^>]+>", " ", body).lower()
    for tok in ("api_key", "dev_mode", "openai", "fallback_available"):
        assert tok not in low


@pytest.mark.django_db
def test_no_content_or_key_in_logs(caplog, monkeypatch):
    sentinel = "sk-LOGLEAK-never"
    monkeypatch.setattr(dai, "_analyze_openai", lambda *a, **k: None)
    with override_settings(OPENAI_API_KEY=sentinel):
        with caplog.at_level(logging.INFO):
            _post([_pdf("TopSecretClaimant.pdf")])
    blob = " ".join(r.getMessage() for r in caplog.records)
    assert sentinel not in blob and "TopSecretClaimant" not in blob


# --- Dossier aggregation + routing -----------------------------------------
def _analyze(name, country=""):
    return dai.analyze_document(filename=name, mime="application/pdf", size=1, country=country)


def test_dossier_offer_plus_injury_is_comparison_ready():
    agg = dai.aggregate_dossier([_analyze("offerta.pdf"), _analyze("referto.pdf")])
    assert agg.document_count == 2
    assert agg.can_compare_offer is True
    assert agg.recommended[0] == "cases:wizard_insurance_offer"
    assert "it-cap-139" in agg.official_source_ids  # sources unioned
    assert agg.can_estimate_now is False  # never a figure without an engine run


def test_dossier_surfaces_missing_documents():
    # offer alone → a medical report is still useful (compare lazy object, not text)
    agg = dai.aggregate_dossier([_analyze("offerta.pdf")])
    assert dai._M_INJURY in agg.missing_documents


@pytest.mark.parametrize("name,country,exp_url,exp_slug", [
    ("offerta.pdf", "", "cases:wizard_insurance_offer", None),
    ("referto.pdf", "", "cases:wizard_italy_road_accident", None),
    ("provvedimento_inail.pdf", "", "core:precheck", "inail"),
    ("constat_maroc.jpg", "MA", "core:precheck", "morocco-road-accident"),
    ("constat_tunisie.pdf", "TN", "core:precheck", "tunisia-road-accident"),
    ("traduzione_apostille.pdf", "", "core:precheck", "international-road-accident"),
])
def test_routing_per_document(name, country, exp_url, exp_slug):
    agg = dai.aggregate_dossier([_analyze(name, country)])
    assert agg.recommended[0] == exp_url
    if exp_slug:
        assert agg.recommended[1].get("slug") == exp_slug


@pytest.mark.django_db
def test_result_has_sources_cta_and_no_money():
    body = _post([_pdf("offerta.pdf")]).content.decode()
    assert "/sources/it-cap-139/" in body
    assert "flow=document" in body
    assert not _MONEY.search(body)


# --- Search + navbar + sidebar ---------------------------------------------
def test_search_finds_document_flow():
    from apps.core.search_index import search
    for q in ("referto medico", "offerta assicurativa", "carica documento"):
        results = search(q)
        assert any(r.url_name == "core:documents" for r in results), q


@pytest.mark.django_db
def test_navbar_and_sidebar_present():
    home = Client().get("/").content.decode()
    assert f'href="{reverse("core:documents")}"' in home
    body = _post([_pdf("offerta.pdf")]).content.decode()
    # sticky document-flow sidebar
    assert "lg:sticky" in body
    assert 'data-event-zone="document"' in body


# --- Hygiene: no money / no weak states / no snake_case in result ----------
@pytest.mark.django_db
def test_result_clean_no_weak_states():
    # filenames without underscores so any snake_case found is a real leak
    body = _post([_pdf("offerta.pdf"), _pdf("referto.pdf")]).content.decode()
    no_sc = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", no_sc))
    low = visible.lower()
    for tok in _FORBIDDEN:
        assert tok not in low, f"result leaks {tok!r}"
    assert not re.search(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b", visible), "result leaks snake_case"
    assert not _MONEY.search(body)


# --- i18n / RTL / canaries --------------------------------------------------
@pytest.mark.django_db
def test_arabic_upload_200_rtl():
    resp = Client().get("/ar/documents/upload/", HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200
    assert 'dir="rtl"' in resp.content.decode()


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs
