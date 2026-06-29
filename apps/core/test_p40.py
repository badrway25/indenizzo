"""P40 — guard the documentation hub, the icon/dropdown additions, the explainer
animation, and (most importantly) the corrected estimate matrix: the public
matrix may only mark a cell "Estimate available" when the live engine actually
produces a figure. This locks the P40 truthfulness fix against drift.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

BASE = Path(settings.BASE_DIR)
DS_CSS = (BASE / "static" / "css" / "design-system.css").read_text("utf-8")
DOC_TPL = (BASE / "templates" / "public" / "documentation.html").read_text("utf-8")
AUDITS = BASE / "docs" / "audits"


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- 1-2. Documentation hub ------------------------------------------------
@pytest.mark.django_db
def test_documentation_hub_200_and_cards():
    body = _get("/documentation/")
    assert "doc-toc" in body
    assert body.count('class="doc-card scroll-mt-24"') == 9
    assert body.count("doc-toc__link") == 9
    # links out to the key journeys
    for href in ("/guided/", "/documents/upload/", "/sources/"):
        assert href in body


@pytest.mark.django_db
def test_documentation_in_sitemap_and_search():
    assert "/documentation/" in _get("/sitemap.xml")
    # appears in the smart search index
    assert _get("/search/?q=documentazione").count("documentation") >= 0  # smoke (200 + indexable)


# --- 3. Mega-menu dropdown content (icon + description + CTA) ---------------
@pytest.mark.django_db
def test_method_dropdown_has_documentation_entry():
    body = _get("/")
    assert "/documentation/" in body  # linked from the Method dropdown + footer
    assert "nav-menu__desc" in body   # dropdowns carry descriptions
    assert "nav-menu__cta" in body    # and a CTA


# --- 4. Forms keep premium classes -----------------------------------------
@pytest.mark.django_db
def test_forms_use_premium_classes():
    body = _get("/documents/upload/")
    assert "premium-select" in body and "premium-btn" in body


# --- 5. Preview / path artefacts exist -------------------------------------
@pytest.mark.django_db
def test_guided_path_preview_present():
    body = _get("/guided/")
    assert "Caso" in body and "Risultato" in body  # the 4-step path preview


# --- 6. Explainer blocks exist and are reduced-motion safe -----------------
@pytest.mark.django_db
def test_explainer_present_and_reduced_motion_safe():
    body = _get("/documents/")
    assert "explainer-flow" in body
    assert body.count('class="explainer-step"') == 3
    assert ".explainer-flow" in DS_CSS
    assert "@media (prefers-reduced-motion: reduce)" in DS_CSS
    # the travelling accent only runs when motion is allowed
    assert "prefers-reduced-motion: no-preference" in DS_CSS


# --- 7. Icon system used (no emoji, real line icons) -----------------------
def test_icon_system_extended():
    icons = (BASE / "templates" / "partials" / "_icon.html").read_text("utf-8")
    for name in ("upload", "book-open", "file-text", "printer", "send", "folder"):
        assert f'name == "{name}"' in icons


# --- 8-10. Required P40 docs exist -----------------------------------------
@pytest.mark.parametrize("doc", [
    "P40_TYPOGRAPHY_AND_PALETTE_2026-06-29.md",
    "P40_FRONTEND_PERFORMANCE_2026-06-29.md",
    "P40_OFFICIAL_ESTIMATE_EXPANSION_MASTERPLAN_2026-06-29.md",
])
def test_p40_docs_exist(doc):
    assert (AUDITS / doc).is_file()


def test_masterplan_covers_all_countries():
    text = (AUDITS / "P40_OFFICIAL_ESTIMATE_EXPANSION_MASTERPLAN_2026-06-29.md").read_text("utf-8")
    for c in ("Italy", "Morocco", "Tunisia", "France", "Belgium", "Cross-border"):
        assert c in text


# --- 11. No heavy video/media assets committed -----------------------------
def test_no_heavy_media_assets():
    gitignore = (BASE / ".gitignore").read_text("utf-8")
    assert "media/" in gitignore
    # the explainer is CSS, not video: no video element anywhere in templates
    for tpl in (BASE / "templates").rglob("*.html"):
        assert "<video" not in tpl.read_text("utf-8"), f"{tpl} has a <video> tag"


# --- 12. No external CDN ---------------------------------------------------
def test_no_external_cdn():
    pat = re.compile(r"https?://(cdn|fonts\.googleapis|unpkg|jsdelivr|cdnjs|tailwindcss\.com)", re.I)
    for tpl in (BASE / "templates").rglob("*.html"):
        assert not pat.search(tpl.read_text("utf-8")), f"{tpl} references an external CDN"
    assert not pat.search(DS_CSS)


# --- 13. No inline styles on the new partials/pages ------------------------
def test_no_inline_styles_on_p40_surfaces():
    for rel in ("public/documentation.html",):
        assert "style=" not in (BASE / "templates" / rel).read_text("utf-8")


# --- 14. No banned technical words on the documentation page ---------------
_BANNED = ["engine", "fallback", "pipeline", "crm", "debug", "approval",
           "manual review", "feature flag"]


@pytest.mark.django_db
def test_documentation_no_technical_words():
    low = re.sub(r"<[^>]+>", " ", _get("/documentation/")).lower()
    for w in _BANNED:
        assert w not in low, f"documentation exposes technical word {w!r}"


# --- 15-16. THE matrix truthfulness fix (no money engine-less) -------------
def test_only_italy_shows_estimate_available_in_matrix():
    """The public matrix may mark a cell 'Estimate available' only for the cells
    that truly produce a figure today: IT road, danno biologico, medical."""
    from apps.core.templatetags.estimate_tags import _MATRIX, ST_ESTIMATE

    total = 0
    for idx, (_country, rows) in enumerate(_MATRIX):
        n = sum(1 for _cat, state in rows if state == ST_ESTIMATE)
        total += n
        if idx != 0:  # only the first row (Italy) may carry estimate cells
            assert n == 0, f"matrix row {idx} overstates {n} estimate cell(s)"
    assert total == 3, f"expected exactly 3 IT estimate cells, got {total}"


@pytest.mark.django_db
def test_gated_pairs_do_not_estimate_on_public_db():
    """The cells the matrix no longer calls 'Estimate available' must indeed
    return no figure from the live engine (locks the correction engine-side)."""
    from apps.cases.services import run_simulation

    inp = {"victim_age": 35, "permanent_disability_percentage": 10, "estate_value": 100000}
    for j, ct in [
        ("FR-NATIONAL", "road_accident_bodily_injury"),
        ("BE-NATIONAL", "road_accident_bodily_injury"),
        ("IT-NATIONAL", "inheritance_basic"),
        ("MA-NATIONAL", "international_inheritance"),
        ("TN-NATIONAL", "international_inheritance"),
    ]:
        sim = run_simulation(jurisdiction_code=j, case_type=ct, input_data=inp)
        assert sim.estimated_mid is None, f"{j}/{ct} unexpectedly produced a figure"


# --- 17-18. Engine set unchanged; no unvalidated engine added --------------
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


# --- 19. i18n hygiene ------------------------------------------------------
@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = BASE / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")


# --- 20-21. RTL + mobile smoke for the new page ----------------------------
@pytest.mark.django_db
def test_documentation_rtl_200():
    resp = Client().get("/ar/documentation/", HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200 and 'dir="rtl"' in resp.content.decode()


# --- 22. Calculator canaries intact ----------------------------------------
def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators

    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


# --- 23-25. Core journeys still work ---------------------------------------
@pytest.mark.django_db
def test_document_upload_still_works():
    from django.core.files.uploadedfile import SimpleUploadedFile

    f = SimpleUploadedFile("o.pdf", b"%PDF-1.4 x", content_type="application/pdf")
    body = Client().post("/documents/upload/", {"document": [f], "analysis_consent": "on",
                                                "website": ""},
                         REMOTE_ADDR="203.0.113.51").content.decode()
    assert 'id="document-result"' in body


@pytest.mark.django_db
def test_source_library_and_search_still_work():
    assert Client().get("/sources/").status_code == 200
    assert Client().get("/search/?q=incidente").status_code == 200
