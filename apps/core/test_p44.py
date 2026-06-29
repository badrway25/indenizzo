"""P44 — guard the documentation 2.0 expansion (start-here band, glossary,
mini-FAQ), the mega-menu mini-previews, and the unchanged legal guardrails
(truthful matrix, no money engine-less, engine set, i18n, RTL, journeys)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
DOC_TPL = (BASE / "templates" / "public" / "documentation.html").read_text("utf-8")
HEADER_TPL = (BASE / "templates" / "partials" / "header.html").read_text("utf-8")
AUDITS = BASE / "docs" / "audits"


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1-3. Documentation 2.0: start-here + glossary + mini-FAQ --------------
@pytest.mark.django_db
def test_documentation_has_start_here_glossary_faq():
    body = _get("/documentation/")
    assert "doc-start" in body                     # Start-here band
    assert "doc-glossary" in body and "doc-term" in body
    assert "doc-mini-faq" in body and "doc-faq" in body
    assert body.count('class="doc-faq"') >= 4      # at least four Q&A
    assert body.count("doc-term") >= 6             # glossary terms


@pytest.mark.django_db
def test_documentation_still_has_nine_topic_cards_and_anchors():
    body = _get("/documentation/")
    assert body.count('class="doc-card scroll-mt-24"') == 9
    assert body.count("doc-toc__link") >= 11       # 9 topics + glossary + quick answers
    assert "#doc-glossary" in body and "#doc-mini-faq" in body


# --- 4. Mega-menu panels carry preview + CTA + descriptions ----------------
@pytest.mark.django_db
def test_mega_menu_has_preview_cta_description():
    body = _get("/")
    assert body.count("nav-menu__preview") >= 5    # one preview per dropdown
    assert "nav-menu__cta" in body and "nav-menu__desc" in body


def test_menu_preview_styled():
    assert ".nav-menu__preview" in DS_CSS


# --- 5. Icon system used in the new sections -------------------------------
def test_icon_used_in_start_here():
    assert 'name="sparkles"' in DOC_TPL


# --- 8-9. Explainer + reduced-motion fallback still present ----------------
@pytest.mark.django_db
def test_explainer_and_reduced_motion_intact():
    assert "explainer-flow" in _get("/documents/")
    assert "@media (prefers-reduced-motion: reduce)" in DS_CSS
    assert "prefers-reduced-motion: no-preference" in DS_CSS


# --- 10-12. No heavy media / no CDN / no inline styles ---------------------
def test_no_video_anywhere():
    for tpl in (BASE / "templates").rglob("*.html"):
        assert "<video" not in tpl.read_text("utf-8"), f"{tpl} has a <video>"


def test_no_external_cdn():
    pat = re.compile(r"https?://(cdn|fonts\.googleapis|unpkg|jsdelivr|cdnjs|tailwindcss\.com)", re.I)
    for tpl in (BASE / "templates").rglob("*.html"):
        assert not pat.search(tpl.read_text("utf-8")), f"{tpl} references a CDN"
    assert not pat.search(DS_CSS)


def test_no_inline_styles_on_documentation():
    assert "style=" not in DOC_TPL


# --- 13. No banned public technical words on documentation -----------------
_BANNED = ["engine", "fallback", "pipeline", "crm", "debug", "approval",
           "manual review", "feature flag"]


@pytest.mark.django_db
def test_documentation_no_technical_words():
    low = re.sub(r"<[^>]+>", " ", _get("/documentation/")).lower()
    for w in _BANNED:
        assert w not in low, f"documentation exposes technical word {w!r}"


# --- 14-16. Matrix truthful, no money engine-less, engine set --------------
def test_matrix_still_truthful_only_italy_estimates():
    from apps.core.templatetags.estimate_tags import _MATRIX, ST_ESTIMATE

    total = 0
    for idx, (_c, rows) in enumerate(_MATRIX):
        n = sum(1 for _cat, s in rows if s == ST_ESTIMATE)
        total += n
        if idx != 0:
            assert n == 0
    assert total == 3


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/sources/", "/guided/", "/documents/", "/documentation/"])
def test_no_money_on_engine_less_pages(path):
    money = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
    assert not money.search(_get(path))


def test_engine_set_unchanged():
    from apps.calculators.registry import list_available_calculators

    available = {(j, c) for j, c in list_available_calculators()}
    assert available == {
        ("BE-NATIONAL", "road_accident_bodily_injury"),
        ("FR-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "inheritance_basic"),
        ("IT-NATIONAL", "medical_liability_biological_damage"),
        ("IT-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "road_accident_microlesions"),
        ("MA-NATIONAL", "international_inheritance"),
        ("TN-NATIONAL", "international_inheritance"),
    }


@pytest.mark.django_db
def test_gated_pairs_still_produce_no_figure():
    from apps.cases.services import run_simulation

    inp = {"victim_age": 35, "permanent_disability_percentage": 10, "estate_value": 100000}
    for j, ct in [("FR-NATIONAL", "road_accident_bodily_injury"),
                  ("BE-NATIONAL", "road_accident_bodily_injury"),
                  ("MA-NATIONAL", "international_inheritance"),
                  ("TN-NATIONAL", "international_inheritance")]:
        sim = run_simulation(jurisdiction_code=j, case_type=ct, input_data=inp)
        assert sim.estimated_mid is None


# --- 18-19. P44 docs exist -------------------------------------------------
@pytest.mark.parametrize("doc", [
    "P44_PREMIUM_FRONTEND_FEATURE_AUDIT_2026-06-29.md",
    "P44_OFFICIAL_ESTIMATE_EXPANSION_VALIDATION_2026-06-29.md",
    "P44_FRONTEND_PERFORMANCE_AND_UX_2026-06-29.md",
])
def test_p44_docs_exist(doc):
    assert (AUDITS / doc).is_file()


# --- 20. i18n hygiene ------------------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")


# --- 21. RTL routes 200 ----------------------------------------------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/documentation/", "/ar/", "/ar/sources/", "/ar/guided/"])
def test_rtl_routes_200(path):
    resp = Client().get(path, HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200 and 'dir="rtl"' in resp.content.decode()


# --- 22-25. Core journeys still work ---------------------------------------
@pytest.mark.django_db
def test_document_upload_still_works():
    from django.core.files.uploadedfile import SimpleUploadedFile

    f = SimpleUploadedFile("o.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    body = Client().post("/documents/upload/", {"document": [f], "analysis_consent": "on",
                                                "website": ""},
                         REMOTE_ADDR="203.0.113.61").content.decode()
    assert 'id="document-result"' in body


@pytest.mark.django_db
def test_sources_and_search_work():
    assert Client().get("/sources/").status_code == 200
    assert Client().get("/search/?q=incidente").status_code == 200


# --- 26. Canaries ----------------------------------------------------------
def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators

    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs
