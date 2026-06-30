"""P30 — guard the intelligent document intake (security, recognition, OpenAI gating)."""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse

from apps.core import document_ai as dai

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
_FORBIDDEN = ("crm", "lead", "pipeline", "debug", "in revisione", "non disponibile",
              "da validare", "manual review", "placeholder")


def _pdf(name="referto_medico.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 fake", content_type="application/pdf")


def _post(data, lang="it"):
    return Client().post("/documents/upload/", data, HTTP_ACCEPT_LANGUAGE=lang)


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- Pages -----------------------------------------------------------------
@pytest.mark.django_db
def test_documents_pages_200():
    assert Client().get("/documents/").status_code == 200
    assert Client().get("/documents/upload/").status_code == 200


# --- Upload security -------------------------------------------------------
@pytest.mark.django_db
def test_invalid_file_type_rejected():
    bad = SimpleUploadedFile("x.exe", b"MZ", content_type="application/x-msdownload")
    body = _post({"document": bad, "analysis_consent": "on", "website": ""}).content.decode()
    assert 'id="document-result"' not in body


@pytest.mark.django_db
def test_oversized_file_rejected():
    big = SimpleUploadedFile("big.pdf", b"%PDF" + b"x" * (settings.DOCUMENT_INTAKE_MAX_UPLOAD_MB * 1024 * 1024 + 10),
                             content_type="application/pdf")
    body = _post({"document": big, "analysis_consent": "on", "website": ""}).content.decode()
    assert 'id="document-result"' not in body


@pytest.mark.django_db
def test_pdf_and_image_accepted():
    for f in (_pdf(), SimpleUploadedFile("scan.png", b"\x89PNG", content_type="image/png")):
        body = _post({"document": f, "analysis_consent": "on", "website": "",
                      "category": "road_accident"}).content.decode()
        assert 'id="document-result"' in body


@pytest.mark.django_db
def test_consent_required_and_honeypot_drops_silently():
    # missing consent → no result
    body = _post({"document": _pdf(), "website": ""}).content.decode()
    assert 'id="document-result"' not in body
    # honeypot filled → no result (and no error revealed)
    body = _post({"document": _pdf(), "analysis_consent": "on",
                  "website": "http://spam"}).content.decode()
    assert 'id="document-result"' not in body


# --- Recognition mapping ---------------------------------------------------
@pytest.mark.parametrize("name,exp_cat,exp_country,exp_url", [
    ("offerta_assicurativa.pdf", "insurance_offer", "IT", "cases:wizard_insurance_offer"),
    ("referto_medico.pdf", "road_accident", "IT", "cases:wizard_italy_road_accident"),
    ("provvedimento_inail.pdf", "work_injury", "IT", "core:precheck"),
    ("constat_maroc.jpg", "road_accident", "MA", "core:precheck"),
    ("constat_tunisie.pdf", "road_accident", "TN", "core:precheck"),
])
def test_document_maps_to_path(name, exp_cat, exp_country, exp_url):
    a = dai.analyze_document(filename=name, mime="application/pdf", size=100)
    assert a.category == exp_cat
    assert a.country == exp_country
    assert a.recommended[0] == exp_url
    assert a.official_source_ids  # at least one connected source
    assert not a.can_estimate_now  # a single document never produces a figure


def test_insurance_offer_unlocks_offer_comparison():
    a = dai.analyze_document(filename="offerta_assicurativa.pdf", mime="application/pdf", size=1)
    assert dai.READY_OFFER in a.readiness


# --- OpenAI gating ---------------------------------------------------------
def test_openai_disabled_uses_local_fallback():
    # default settings: OPENAI_DOCUMENT_AI_ENABLED is False
    assert not settings.OPENAI_DOCUMENT_AI_ENABLED
    a = dai.analyze_document(filename="referto_medico.pdf", mime="application/pdf", size=1)
    assert a.provider == "local"


def test_openai_enabled_mock_returns_structured(monkeypatch):
    fake = dai._build(dai._BY_KEY["it_inail_decision"], dai.CONF_STRONG, provider="openai")
    monkeypatch.setattr(dai, "_analyze_openai", lambda *a, **k: fake)
    a = dai.analyze_document(filename="anything.pdf", mime="application/pdf", size=1)
    assert a.provider == "openai" and a.type_key == "it_inail_decision"


def test_openai_error_falls_back_safely(monkeypatch):
    # _analyze_openai returns None on any failure → local fallback
    monkeypatch.setattr(dai, "_analyze_openai", lambda *a, **k: None)
    a = dai.analyze_document(filename="referto_medico.pdf", mime="application/pdf", size=1)
    assert a.provider == "local"


def test_real_openai_path_inert_without_key():
    # With the flag off and no key, the OpenAI path must return None (no call).
    assert dai._analyze_openai("file.pdf", "application/pdf", country="", category="") is None


@pytest.mark.django_db
def test_no_document_filename_or_content_in_logs(caplog):
    secret = "TopSecretClaimant_referto.pdf"
    with caplog.at_level(logging.INFO):
        _post({"document": _pdf(secret), "analysis_consent": "on", "website": "",
               "category": "medical"})
    blob = " ".join(r.getMessage() for r in caplog.records)
    assert secret not in blob


# --- Rendered result -------------------------------------------------------
@pytest.mark.django_db
def test_result_has_sources_and_dossier_cta_and_no_money():
    body = _post({"document": _pdf("offerta_assicurativa.pdf"), "analysis_consent": "on",
                  "website": ""}).content.decode()
    assert 'id="document-result"' in body
    assert "/sources/it-cap-139/" in body  # connected official source chip (rendered URL)
    assert "flow=document" in body  # send-to-Studio dossier CTA
    assert not _MONEY.search(body)


# --- Search + navbar -------------------------------------------------------
def test_search_finds_document_flow():
    from apps.core.search_index import search
    for q in ("referto medico", "offerta assicurativa", "constat marocco", "carica documento"):
        results = search(q)
        assert any(r.url_name == "core:documents" for r in results), q


@pytest.mark.django_db
def test_navbar_links_documents():
    assert f'href="{reverse("core:documents")}"' in _get("/")


# --- Hygiene ---------------------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/documents/", "/documents/upload/"])
def test_document_pages_clean(path):
    body = _get(path)
    assert not _MONEY.search(body)
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                     re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)))
    low = visible.lower()
    for tok in _FORBIDDEN:
        assert tok not in low, f"{path} leaks {tok!r}"
    assert not re.search(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b", visible), f"{path} snake_case"


@pytest.mark.django_db
def test_arabic_documents_200_rtl():
    resp = Client().get("/ar/documents/", HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200
    assert 'dir="rtl"' in resp.content.decode("utf-8")


def test_no_external_cdn_in_document_templates():
    tpl = Path(settings.BASE_DIR) / "templates" / "public"
    for name in ("documents.html", "documents_upload.html"):
        src = (tpl / name).read_text("utf-8")
        assert "cdn." not in src and "unpkg" not in src and "googleapis" not in src


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
