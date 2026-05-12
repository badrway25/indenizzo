"""
Tests F-p2-perf-3-font-loading-performance.

Conservative font-loading pass. Shipped as housekeeping; the
`/ar/` mobile target (>= 0.85) was NOT achieved by this lever
set, but the cleanup (preload weight correctness, removal of
unused Inter 700 and Amiri 400) is a strict improvement and is
pinned here so a future drive-by edit doesn't silently revert it.

See `docs/qa/lighthouse-mobile-baseline/P2_PERF_3_COMPARISON.md`
for the measurements and the rationale per dropped weight.

If a future iter intentionally wants to re-add Inter 700 or
Amiri 400, delete the matching assertions as part of that iter.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_HTML = REPO_ROOT / "templates" / "base.html"
FONTS_CSS = REPO_ROOT / "static" / "css" / "fonts.css"
DOWNLOAD_SCRIPT = REPO_ROOT / "scripts" / "download_local_fonts.py"
README = REPO_ROOT / "static" / "fonts" / "README.md"
REPORT = (
    REPO_ROOT
    / "docs"
    / "qa"
    / "lighthouse-mobile-baseline"
    / "P2_PERF_3_COMPARISON.md"
)
INTER_700_LATIN = REPO_ROOT / "static" / "fonts" / "inter" / "inter-700-latin.woff2"
INTER_700_LATIN_EXT = (
    REPO_ROOT / "static" / "fonts" / "inter" / "inter-700-latin-ext.woff2"
)
AMIRI_400 = REPO_ROOT / "static" / "fonts" / "amiri" / "amiri-400-arabic.woff2"


# ---------------------------------------------------------------------------
# Report exists and is non-trivial
# ---------------------------------------------------------------------------


def test_p2_perf_3_report_exists():
    assert REPORT.exists()
    assert REPORT.stat().st_size > 2000


def test_p2_perf_3_report_documents_no_go_on_ar_target():
    text = REPORT.read_text(encoding="utf-8")
    # The report must be explicit that /ar/ >= 0.85 was NOT achieved.
    assert "0.82" in text
    assert "ar/" in text or "/ar/" in text


# ---------------------------------------------------------------------------
# base.html: Cormorant preload is weight 700 (not 600)
# ---------------------------------------------------------------------------


def test_base_html_preloads_cormorant_700_not_600():
    text = BASE_HTML.read_text(encoding="utf-8")
    assert "cormorant-garamond-700-latin.woff2" in text, (
        "LTR preload must target Cormorant 700 (the weight h1/h2/h3 "
        "actually paint with via browser default-bold)"
    )
    # And NOT 600 — the previous, mismatched preload.
    assert "cormorant-garamond-600-latin.woff2" not in text, (
        "Cormorant 600 preload was replaced by 700 in P2-PERF-3"
    )


def test_base_html_carries_pointer_to_p2_perf_3_report():
    text = BASE_HTML.read_text(encoding="utf-8")
    assert "P2_PERF_3_COMPARISON.md" in text


# ---------------------------------------------------------------------------
# fonts.css: Inter 700 and Amiri 400 @font-face blocks are gone
# ---------------------------------------------------------------------------


def test_fonts_css_no_inter_700_declaration():
    text = FONTS_CSS.read_text(encoding="utf-8")
    assert "inter-700-latin.woff2" not in text
    assert "inter-700-latin-ext.woff2" not in text


def test_fonts_css_no_amiri_400_declaration():
    text = FONTS_CSS.read_text(encoding="utf-8")
    assert "amiri-400-arabic.woff2" not in text


def test_fonts_css_still_has_amiri_700():
    """Sanity check: we dropped Amiri 400, not the whole family."""
    text = FONTS_CSS.read_text(encoding="utf-8")
    assert "amiri-700-arabic.woff2" in text
    assert "font-family: 'Amiri'" in text


def test_fonts_css_still_has_inter_400_500_600():
    """Sanity check: we dropped Inter 700, not the whole family."""
    text = FONTS_CSS.read_text(encoding="utf-8")
    assert "inter-400-latin.woff2" in text
    assert "inter-500-latin.woff2" in text
    assert "inter-600-latin.woff2" in text


# ---------------------------------------------------------------------------
# Disk: the unused .woff2 files are gone
# ---------------------------------------------------------------------------


def test_inter_700_woff2_files_deleted():
    assert not INTER_700_LATIN.exists(), (
        "Inter 700 latin must be deleted from disk. If a future iter "
        "intentionally wants to re-add it, delete this assertion "
        "as part of that iter."
    )
    assert not INTER_700_LATIN_EXT.exists(), (
        "Inter 700 latin-ext must be deleted from disk. If a future "
        "iter intentionally wants to re-add it, delete this assertion "
        "as part of that iter."
    )


def test_amiri_400_woff2_file_deleted():
    assert not AMIRI_400.exists(), (
        "Amiri 400 must be deleted from disk. If a future iter "
        "intentionally wants to re-add it, delete this assertion "
        "as part of that iter."
    )


# ---------------------------------------------------------------------------
# Regenerator stays in sync: FAMILIES config no longer requests the
# dropped weights, so re-running the script won't silently re-add them.
# ---------------------------------------------------------------------------


def test_download_script_inter_drops_700():
    text = DOWNLOAD_SCRIPT.read_text(encoding="utf-8")
    # The Inter family block must list weights without 700.
    inter_block_idx = text.find('"family": "Inter"')
    assert inter_block_idx > 0
    # Inspect the next ~250 chars after the Inter family marker.
    inter_chunk = text[inter_block_idx : inter_block_idx + 250]
    assert '"weights": [400, 500, 600]' in inter_chunk, (
        f"Inter FAMILIES weights must be [400, 500, 600] — got chunk: {inter_chunk!r}"
    )


def test_download_script_amiri_drops_400():
    text = DOWNLOAD_SCRIPT.read_text(encoding="utf-8")
    amiri_idx = text.find('"family": "Amiri"')
    assert amiri_idx > 0
    amiri_chunk = text[amiri_idx : amiri_idx + 250]
    assert '"weights": [700]' in amiri_chunk, (
        f"Amiri FAMILIES weights must be [700] only — got chunk: {amiri_chunk!r}"
    )


# ---------------------------------------------------------------------------
# README inventory tracks the new state
# ---------------------------------------------------------------------------


def test_readme_inventory_lists_six_inter_files():
    text = README.read_text(encoding="utf-8")
    # Inventory line is now: Inter | 400, 500, 600 | latin, latin-ext | 6
    assert "Inter | 400, 500, 600" in text


def test_readme_inventory_lists_one_amiri_file():
    text = README.read_text(encoding="utf-8")
    # Inventory line is now: Amiri | 700 | arabic | 1
    assert "Amiri | 700" in text
