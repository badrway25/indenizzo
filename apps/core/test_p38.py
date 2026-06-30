"""P38 — guard the estimate availability matrix (truthful, human, no tech words)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
MATRIX_TPL = (BASE / "templates" / "partials" / "_estimate_matrix.html").read_text("utf-8")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1. Matrix renders on the required pages -------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/services/", "/guided/", "/countries/"])
def test_matrix_present_on_required_pages(path):
    body = _get(path)
    assert "estimate-matrix" in body
    assert body.count('class="matrix-card"') == 6   # one card per jurisdiction
    assert "matrix-chip--ok" in body                # at least one "estimate available"


def test_matrix_css_and_mobile_rules():
    assert ".matrix-card" in DS_CSS and ".matrix-chip" in DS_CSS
    assert "@media (max-width: 480px)" in DS_CSS     # rows stack on small screens
    assert "grid-cols-1" in MATRIX_TPL               # one column on mobile


# --- 2. Matrix uses ONLY human public states (no technical vocabulary) -----
_MATRIX_BANNED = ["approval_needed", "non-binding", "non_binding", "engine",
                  "readiness", "fallback", "unavailable", "roadmap",
                  "manual review", "approval"]


@pytest.mark.django_db
def test_matrix_has_no_technical_states():
    body = _get("/services/")
    # isolate the matrix section text
    matrix = body.split("estimate-matrix", 1)[1].split("</section>", 1)[0]
    low = re.sub(r"<[^>]+>", " ", matrix).lower()
    for w in _MATRIX_BANNED:
        assert w not in low, f"matrix exposes technical word {w!r}"


@pytest.mark.django_db
def test_matrix_shows_simple_states():
    body = _get("/services/", lang="it")
    for human in ("Stima disponibile", "Verifica i documenti", "Controllo offerta"):
        assert human in body, f"missing human state {human!r}"


# --- 3. Truthful: no fabricated engine; money only with an engine ----------
def test_no_unvalidated_engine_was_fabricated():
    from apps.calculators.registry import list_available_calculators
    available = {(j, c) for j, c in list_available_calculators()}
    expected = {
        ("BE-NATIONAL", "road_accident_bodily_injury"),
        ("FR-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "inheritance_basic"),
        ("IT-NATIONAL", "medical_liability_biological_damage"),
        ("IT-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "road_accident_microlesions"),
        ("MA-NATIONAL", "international_inheritance"),
        ("TN-NATIONAL", "international_inheritance"),
    }
    assert available == expected


_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/services/", "/guided/", "/countries/"])
def test_no_money_on_matrix_pages(path):
    assert not _MONEY.search(_get(path))


# --- 4. Hygiene -------------------------------------------------------------
def test_matrix_partial_no_inline_style():
    assert "style=" not in MATRIX_TPL


# --- 5. Regression: RTL / canaries / i18n / upload -------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/", "/ar/services/", "/ar/guided/", "/ar/countries/"])
def test_rtl_matrix_pages_200(path):
    resp = Client().get(path, HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200 and 'dir="rtl"' in resp.content.decode()


@pytest.mark.django_db
def test_document_upload_still_works():
    from django.core.files.uploadedfile import SimpleUploadedFile
    f = SimpleUploadedFile("offerta.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    body = Client().post("/documents/upload/", {"document": [f], "analysis_consent": "on",
                                                "website": ""},
                         REMOTE_ADDR="203.0.113.38").content.decode()
    assert 'id="document-result"' in body


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
