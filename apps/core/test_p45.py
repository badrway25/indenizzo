"""P45 — guard the Guided Path Studio recommender, the documentation guides-by-
case-type, the official estimate validation packs, and the unchanged legal
guardrails. The headline guard: the path studio never promises money, and its
internal validation-pack statuses never leak to the public."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
SITE_JS = (BASE / "static" / "js" / "site.js").read_text("utf-8")
GUIDED_TPL = (BASE / "templates" / "public" / "guided_router.html").read_text("utf-8")
VALIDATION = BASE / "docs" / "legal_validation"
AUDITS = BASE / "docs" / "audits"
_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1-2. Guided Path Studio: outputs exist; never promises money ----------
@pytest.mark.django_db
def test_guided_path_studio_exists():
    body = _get("/guided/")
    assert "data-path-studio" in body
    assert body.count("data-path-result") == 5  # 5 recommended paths
    assert "initPathStudio" in SITE_JS          # CSP-safe JS behaviour
    assert ".path-studio" in DS_CSS


@pytest.mark.django_db
def test_path_studio_never_shows_money():
    body = _get("/guided/")
    widget = body.split("data-path-studio", 1)[1].split("Step 1", 1)[0]
    assert not _MONEY.search(widget), "path studio shows a monetary figure"


def test_path_studio_estimate_path_is_italy_only_logic():
    # The recommender only routes to the estimate path for IT + injury — the only
    # validated road/medical engine. Guard the deterministic rule in the JS.
    assert 'country === "IT" && injury' in SITE_JS
    assert 'path = "estimate"' in SITE_JS
    assert '(country === "MA" || country === "TN") && injury' in SITE_JS
    assert 'path = "needs_table"' in SITE_JS


# --- 5. Documentation guides by case type ----------------------------------
@pytest.mark.django_db
def test_documentation_has_case_type_guides():
    body = _get("/documentation/")
    assert "doc-by-category" in body
    assert body.count('class="doc-cat premium-card premium-card-hover"') == 9
    assert "/case-types/road-accident/" in body


# --- 6-7. Validation packs exist and are internal only ---------------------
@pytest.mark.parametrize("pack", [
    "README.md",
    "INAIL_WORK_INJURY_VALIDATION.md",
    "MOROCCO_ROAD_DAMAGE_VALIDATION.md",
    "TUNISIA_ROAD_DAMAGE_VALIDATION.md",
    "MOROCCO_FAMILY_LOSS_VALIDATION.md",
    "TUNISIA_FAMILY_LOSS_VALIDATION.md",
])
def test_validation_packs_exist(pack):
    assert (VALIDATION / pack).is_file()


def test_no_validation_pack_is_ready_for_engine():
    # Cardinal rule: an engine is built only at ready_for_engine. None declares it.
    # (P50 added not_calculable packs for product liability + FR/BE road, so a pack
    # may be needs_legal_review OR not_calculable — but never ready_for_engine.)
    _NON_READY = ("needs_legal_review", "not_calculable", "needs_official_table",
                  "needs_formula", "needs_canary")
    for pack in VALIDATION.glob("*_VALIDATION.md"):
        text = pack.read_text("utf-8")
        assert "**Status:** `ready_for_engine`" not in text, f"{pack.name} claims ready_for_engine"
        assert any(f"**Status:** `{s}`" in text for s in _NON_READY), f"{pack.name} has no known status"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/guided/", "/documentation/", "/sources/", "/services/"])
def test_validation_pack_statuses_do_not_leak_to_public(path):
    low = _get(path).lower()
    for status in ("ready_for_engine", "needs_official_table", "needs_legal_review", "not_calculable"):
        assert status not in low, f"internal status {status!r} leaked on {path}"


# --- 8/16. No banned public technical words --------------------------------
_BANNED = ["engine", "fallback", "pipeline", "crm", "debug", "approval",
           "manual review", "feature flag"]


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/guided/", "/documentation/"])
def test_no_banned_public_words(path):
    low = re.sub(r"<[^>]+>", " ", _get(path)).lower()
    for w in _BANNED:
        assert w not in low, f"{path} exposes technical word {w!r}"


# --- 10. Reduced-motion fallback exists ------------------------------------
def test_reduced_motion_fallback_exists():
    assert "@media (prefers-reduced-motion: reduce)" in DS_CSS


# --- 12-15. Legal guardrails -----------------------------------------------
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
@pytest.mark.parametrize("path", ["/guided/", "/documents/", "/sources/", "/documentation/"])
def test_no_money_on_engine_less_pages(path):
    assert not _MONEY.search(_get(path))


def test_matrix_still_truthful():
    from apps.core.templatetags.estimate_tags import _MATRIX, ST_ESTIMATE

    total = sum(1 for i, (_c, rows) in enumerate(_MATRIX) for _cat, s in rows
                if s == ST_ESTIMATE and i == 0)
    other = sum(1 for i, (_c, rows) in enumerate(_MATRIX) for _cat, s in rows
                if s == ST_ESTIMATE and i != 0)
    assert total == 3 and other == 0


# --- 18-19. Audit doc + i18n + RTL -----------------------------------------
def test_p45_audit_doc_exists():
    assert (AUDITS / "P45_OFFICIAL_FUNCTIONALITY_AND_PREMIUM_UX_AUDIT_2026-06-29.md").is_file()


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/ar/guided/", "/ar/documentation/", "/ar/sources/"])
def test_rtl_routes_200(path):
    resp = Client().get(path, HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200 and 'dir="rtl"' in resp.content.decode()


# --- 20-23. Core journeys + canaries ---------------------------------------
@pytest.mark.django_db
def test_document_upload_works():
    from django.core.files.uploadedfile import SimpleUploadedFile

    f = SimpleUploadedFile("o.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    body = Client().post("/documents/upload/", {"document": [f], "analysis_consent": "on",
                                                "website": ""},
                         REMOTE_ADDR="203.0.113.71").content.decode()
    assert 'id="document-result"' in body


@pytest.mark.django_db
def test_sources_and_search_work():
    assert Client().get("/sources/").status_code == 200
    assert Client().get("/search/?q=incidente").status_code == 200


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators

    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs
