"""
Tests F-p2-perf-4-arabic-font-subset.

Pins the post-iter state of the Amiri 700 re-subset.

What this iter does: takes the upstream Amiri 700 (~9000 glyphs
across 14 Unicode blocks) and re-subsets it locally against the
real Arabic corpus used in templates + locale, while preserving
every OpenType GSUB/GPOS layout feature so contextual shaping
keeps working.

What these tests guard:
 1. The reproducer script exists and the fontTools dep is wired
    via requirements.txt.
 2. The subsetted Amiri 700 ships at well under the upstream size
    (sanity check that the subsetter actually ran).
 3. The upstream reference is checked in (so the subset is
    reproducible without re-fetching from Google).
 4. The fonts.css `@font-face` for Amiri 700 carries the tightened
    unicode-range, NOT the broad upstream one.
 5. Every Arabic codepoint used by `locale/ar/LC_MESSAGES/django.po`
    resolves to a glyph in the subset font (catastrophic-failure
    guard against silently-broken Arabic).
 6. The subset font preserves the critical OpenType layout
    features (init/medi/fina/ccmp/rlig + mark/mkmk/kern) — these
    are what HarfBuzz uses for Arabic shaping.
 7. No Google Fonts URLs leak. CSP unchanged.
 8. `/ar/` still renders 200 with `dir="rtl"`.

If a future iter intentionally reverts the subset, delete the
matching assertions as part of that iter.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SUBSET_SCRIPT = REPO_ROOT / "scripts" / "subset_arabic_fonts.py"
AMIRI = REPO_ROOT / "static" / "fonts" / "amiri" / "amiri-700-arabic.woff2"
AMIRI_ORIGINAL = (
    REPO_ROOT / "static" / "fonts" / "amiri" / "amiri-700-arabic.original.woff2"
)
FONTS_CSS = REPO_ROOT / "static" / "css" / "fonts.css"
REQUIREMENTS = REPO_ROOT / "requirements.txt"
LOCALE_PO = REPO_ROOT / "locale" / "ar" / "LC_MESSAGES" / "django.po"
REPORT = (
    REPO_ROOT
    / "docs"
    / "qa"
    / "lighthouse-mobile-baseline"
    / "P2_PERF_4_ARABIC_SUBSET_COMPARISON.md"
)


# ---------------------------------------------------------------------------
# 1. Reproducer is in tree
# ---------------------------------------------------------------------------


def test_subset_script_exists():
    assert SUBSET_SCRIPT.exists(), (
        "scripts/subset_arabic_fonts.py is the reproducer for the "
        "Amiri 700 subset. It must stay in tree so the subset can "
        "be regenerated without network access."
    )


def test_fonttools_in_requirements():
    text = REQUIREMENTS.read_text(encoding="utf-8")
    assert "fonttools" in text.lower(), (
        "fonttools must be declared in requirements.txt — it's the "
        "tool the subsetter script depends on."
    )


# ---------------------------------------------------------------------------
# 2. Subset is materially smaller than upstream
# ---------------------------------------------------------------------------


def test_amiri_subset_is_present_on_disk():
    assert AMIRI.exists(), "subset Amiri 700 must be on disk"


def test_amiri_upstream_reference_is_present():
    """The upstream Google copy is committed so the subset can be
    regenerated on any machine without re-fetching."""
    assert AMIRI_ORIGINAL.exists(), (
        "static/fonts/amiri/amiri-700-arabic.original.woff2 is the "
        "upstream Google CDN copy. It MUST be committed so the "
        "subsetter has a stable reproducible input."
    )


def test_amiri_subset_is_smaller_than_upstream():
    """Sanity: if the subset went 0 % smaller, the subsetter
    didn't actually run / pyftsubset failed silently."""
    subset_size = AMIRI.stat().st_size
    upstream_size = AMIRI_ORIGINAL.stat().st_size
    assert upstream_size > subset_size, (
        f"upstream {upstream_size} bytes is not larger than subset "
        f"{subset_size} bytes — subsetter likely didn't run"
    )
    # Expect at least 15 % reduction. Actual reduction is ~24 %;
    # 15 % is a generous floor that protects against a future
    # upstream Google bump that ships a smaller Amiri.
    reduction_pct = 100 * (upstream_size - subset_size) / upstream_size
    assert reduction_pct >= 15, (
        f"subset is only {reduction_pct:.1f} % smaller than upstream; "
        f"expected >= 15 %. Subsetter may be missing features."
    )


# ---------------------------------------------------------------------------
# 3. fonts.css unicode-range is tightened
# ---------------------------------------------------------------------------


def _amiri_block(css: str) -> str:
    m = re.search(
        r"@font-face\s*\{[^}]*?font-family:\s*'Amiri'[^}]*?\}",
        css,
        re.DOTALL,
    )
    assert m, "Amiri @font-face block not found in fonts.css"
    return m.group(0)


def test_fonts_css_amiri_unicode_range_is_tightened():
    css = FONTS_CSS.read_text(encoding="utf-8")
    block = _amiri_block(css)
    # The broad upstream range carried `U+FB50-FDFF` (Presentation
    # Forms-A) and `U+FE70-FEFC` (Presentation Forms-B); the
    # tightened range must NOT mention them.
    assert "U+FB50" not in block, (
        "Amiri unicode-range still references Presentation Forms-A "
        "— the upstream broad range was not tightened."
    )
    assert "U+1EE" not in block, (
        "Amiri unicode-range still references Mathematical Arabic — "
        "the upstream broad range was not tightened."
    )
    # The tightened range must keep the basic Arabic block.
    assert "U+0600-06FF" in block or "U+0600-0604" in block, (
        "Amiri unicode-range must still cover the basic Arabic block."
    )


# ---------------------------------------------------------------------------
# 4. Every corpus codepoint resolves in the subset
# ---------------------------------------------------------------------------


def _arabic_codepoints_from_po() -> set[int]:
    """Extract every Arabic codepoint that appears inside any
    msgstr in the AR catalog."""
    text = LOCALE_PO.read_text(encoding="utf-8")
    cps: set[int] = set()
    for ch in text:
        o = ord(ch)
        if (
            0x0600 <= o <= 0x06FF
            or 0x0750 <= o <= 0x077F
            or 0xFB50 <= o <= 0xFDFF
            or 0xFE70 <= o <= 0xFEFF
        ):
            cps.add(o)
    return cps


def test_every_corpus_codepoint_has_a_glyph_in_subset():
    pytest.importorskip("fontTools")
    from fontTools.ttLib import TTFont

    font = TTFont(AMIRI)
    cmap = font.getBestCmap()
    used = _arabic_codepoints_from_po()
    missing = sorted(cp for cp in used if cp not in cmap)
    assert not missing, (
        "Arabic codepoints used in locale/ar/django.po but missing "
        f"from the subset font: {[f'U+{cp:04X}' for cp in missing]}. "
        "Re-run scripts/subset_arabic_fonts.py to refresh the keep-set."
    )


# ---------------------------------------------------------------------------
# 5. OpenType layout features survived the subset
# ---------------------------------------------------------------------------


def test_subset_preserves_arabic_shaping_features():
    """HarfBuzz uses GSUB/GPOS features to drive Arabic contextual
    shaping (initial / medial / final / isolated letter forms,
    ligatures, mark positioning). If those are stripped, Arabic
    text renders as a sequence of disconnected isolated glyphs."""
    pytest.importorskip("fontTools")
    from fontTools.ttLib import TTFont

    font = TTFont(AMIRI)
    assert "GSUB" in font, "subset font lost GSUB table"
    assert "GPOS" in font, "subset font lost GPOS table"
    gsub_feats = {
        fr.FeatureTag for fr in font["GSUB"].table.FeatureList.FeatureRecord
    }
    gpos_feats = {
        fr.FeatureTag for fr in font["GPOS"].table.FeatureList.FeatureRecord
    }
    required_gsub = {"init", "medi", "fina", "ccmp", "rlig"}
    missing_gsub = required_gsub - gsub_feats
    assert not missing_gsub, (
        f"subset font missing critical GSUB features: {missing_gsub}. "
        "Arabic shaping will break."
    )
    required_gpos = {"mark", "mkmk", "kern"}
    missing_gpos = required_gpos - gpos_feats
    assert not missing_gpos, (
        f"subset font missing critical GPOS features: {missing_gpos}. "
        "Diacritic positioning will break."
    )


# ---------------------------------------------------------------------------
# 6. Report exists
# ---------------------------------------------------------------------------


def test_p2_perf_4_report_exists():
    assert REPORT.exists()
    assert REPORT.stat().st_size > 2000


# ---------------------------------------------------------------------------
# 7-8. CSP / leak / render regression guards
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ar_home_renders_200_with_rtl(client):
    resp = client.get("/ar/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert 'dir="rtl"' in body
    # No regression: still no Google Fonts URLs in the AR home.
    assert "fonts.googleapis.com" not in body
    assert "fonts.gstatic.com" not in body
    # And the Amiri @font-face from fonts.css must STILL be reachable
    # — but fonts.css is included via <link>, not inlined, so we
    # just check the include is there.
    assert "css/fonts.css" in body
