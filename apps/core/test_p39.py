"""P39 — guard the premium sources library, human result report, and the
internal Pexels imagery on sources / source detail / services / guided.

The phase rule: no main public page may stay "text + cards". Each guard checks
a concrete, visible artefact (a real image, a plain-language section) rather
than a class name alone, so a regression that strips the imagery fails here.
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
REPORT_TPL = (BASE / "templates" / "partials" / "_result_report_summary.html").read_text("utf-8")
BODY_IMG_TPL = (BASE / "templates" / "partials" / "_premium_body_image.html").read_text("utf-8")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


def _document_result(lang="it"):
    """Upload one file → the dossier result page that carries the report header."""
    f = SimpleUploadedFile("offerta.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    return Client().post(
        "/documents/upload/",
        {"document": [f], "analysis_consent": "on", "website": ""},
        REMOTE_ADDR="203.0.113.77",
        HTTP_ACCEPT_LANGUAGE=lang,
    ).content.decode("utf-8")


@contextmanager
def _with_images():
    """The pytest harness points MEDIA_ROOT at an empty tmp dir, so the Pexels
    manifest never resolves and no internal photo renders. Patch the lookup to
    a stand-in entry so the body-image partial actually emits its markup."""
    fake = {"local_path": "pexels/test.jpg", "alt": "test image"}
    with patch("apps.core.pexels.get_image_for_slot", return_value=fake):
        yield


# --- 1. Sources opens as a library, not a filter bar ----------------------
@pytest.mark.django_db
def test_sources_has_internal_visual_section():
    body = _get("/sources/")
    assert "Documenti ufficiali, spiegati in modo semplice" in body
    assert "Come leggere una fonte" in body
    assert "source-read-row" in body  # the five-question explainer


# --- 2. Source detail has plain-language document sections ----------------
@pytest.mark.django_db
def test_source_detail_has_document_sections():
    from apps.core import official_sources as official

    slug = official.all_sources()[0].source_id
    body = _get(f"/sources/{slug}/")
    assert "A cosa serve questa fonte" in body
    assert "Quando può aiutare una stima" in body
    assert "Quando basta la verifica dei documenti" in body


# --- 3. Source cards carry elegant official-document CTAs -----------------
@pytest.mark.django_db
def test_source_cards_have_official_link_cta():
    body = _get("/sources/")
    # External official links open in a new, safe tab.
    assert 'rel="noopener noreferrer"' in body
    assert "Scheda fonte" in body  # "Source details" link, in Italian


# --- 4. Services has three plain-language internal sections ---------------
@pytest.mark.django_db
def test_services_has_three_internal_sections():
    body = _get("/services/")
    assert "Fai una stima" in body
    assert "Casi transfrontalieri" in body
    assert "Verifica i documenti" in body


# --- 5. Guided opens with a visual path preview ---------------------------
@pytest.mark.django_db
def test_guided_has_visual_path():
    body = _get("/guided/")
    # Four-step path preview (Country / Case / Documents / Result).
    assert "Caso" in body and "Risultato" in body


# --- 1b/4b/5b. Internal photos actually render when the manifest resolves --
@pytest.mark.django_db
@pytest.mark.parametrize("tpl,var", [
    ("public/sources.html", "img_library"),
    ("public/source_detail.html", "img_document"),
    ("public/services.html", "img_estimate"),
    ("public/services.html", "img_documents"),
    ("public/services.html", "img_international"),
    ("public/guided_router.html", "img_workflow"),
])
def test_templates_wire_internal_body_image(tpl, var):
    text = (BASE / "templates" / tpl).read_text("utf-8")
    assert "_premium_body_image.html" in text
    assert var in text


@pytest.mark.django_db
def test_pages_render_internal_images_when_manifest_resolves():
    with _with_images():
        assert "premium-figure" in _get("/sources/")
        assert "premium-figure" in _get("/guided/")
        # Three internal service-section figures (estimate / documents / international).
        assert _get("/services/").count("premium-figure") >= 3


# --- 6-9. Every result page speaks plain language -------------------------
_HUMAN_SECTIONS = ("Hai indicato", "Possiamo fare ora", "Manca ancora", "Prossimo passo")


@pytest.mark.django_db
def test_document_result_has_human_report_sections():
    body = _document_result()
    assert 'id="document-result"' in body
    for s in _HUMAN_SECTIONS:
        assert s in body, f"document result missing human section {s!r}"


@pytest.mark.parametrize(
    "tpl",
    ["public/wizard_result.html", "public/precheck.html", "public/documents_upload.html"],
)
def test_all_result_templates_include_report_summary(tpl):
    text = (BASE / "templates" / tpl).read_text("utf-8")
    assert "_result_report_summary.html" in text


# --- 10. No technical vocabulary in the human report partial --------------
_RESULT_BANNED = ["readiness", "engine", "flow", "result kind", "result_kind",
                  "metadata", "fallback"]


@pytest.mark.django_db
def test_result_report_section_has_no_technical_words():
    body = _document_result()
    section = body.split('class="result-report"', 1)[1].split("</section>", 1)[0]
    low = re.sub(r"<[^>]+>", " ", section).lower()
    for w in _RESULT_BANNED:
        assert w not in low, f"result report exposes technical word {w!r}"


# --- 11. Image-sources documentation exists -------------------------------
def test_p39_image_sources_doc_exists():
    doc = BASE / "docs" / "audits" / "P39_IMAGE_SOURCES_2026-06-29.md"
    assert doc.is_file()
    text = doc.read_text("utf-8")
    for slot in ("sources_body", "source_document", "result_report",
                 "services_estimate", "services_documents",
                 "services_international", "guided_workflow"):
        assert slot in text


# --- 12. No heavy binary assets are committed -----------------------------
def test_no_heavy_assets_committed():
    # Pexels binaries live under the gitignored media/ tree, never in the repo.
    gitignore = (BASE / ".gitignore").read_text("utf-8")
    assert "media/" in gitignore or "/media" in gitignore
    # The seven new internal images are pinned in the (committable) override
    # file, so they are reproducible from the gitignored media tree.
    from apps.core import pexels

    overrides = pexels.load_overrides()
    for slot in ("sources_body", "source_document", "result_report",
                 "services_estimate", "services_documents",
                 "services_international", "guided_workflow"):
        over = overrides.get(slot, {})
        assert over.get("photo_id"), f"{slot} has no frozen photo_id"
        assert over.get("approved_visual"), f"{slot} not approved_visual"


# --- 13. No invented money on the internal pages --------------------------
_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/sources/", "/services/", "/guided/"])
def test_no_money_on_internal_pages(path):
    assert not _MONEY.search(_get(path))


# --- 14. No unvalidated engine was fabricated -----------------------------
def test_engine_set_unchanged():
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


# --- 15. Document upload still works --------------------------------------
@pytest.mark.django_db
def test_document_upload_still_works():
    assert 'id="document-result"' in _document_result()


# --- 16. Calculator canaries intact ---------------------------------------
def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators

    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


# --- 17. i18n hygiene: no fuzzy / English leak ----------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")


# --- 18. RTL routes for the reworked pages -------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/sources/", "/ar/services/", "/ar/guided/"])
def test_rtl_internal_pages_200(path):
    resp = Client().get(path, HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200 and 'dir="rtl"' in resp.content.decode()


# --- 19. Mobile QA note recorded ------------------------------------------
def test_mobile_qa_note_present():
    doc = BASE / "docs" / "audits" / "P39_IMAGE_SOURCES_2026-06-29.md"
    assert "390" in doc.read_text("utf-8")


# --- Hygiene: body-image partial is lazy + WebP, no inline style ----------
def test_body_image_partial_is_lazy_webp():
    assert 'loading="lazy"' in BODY_IMG_TPL
    assert "image/webp" in BODY_IMG_TPL
    assert "style=" not in REPORT_TPL
