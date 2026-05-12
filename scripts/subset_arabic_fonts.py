"""Re-subset Amiri 700 against the actual Arabic corpus (F-p2-perf-4).

The Google Fonts CDN ships `amiri-700-arabic.woff2` covering ~9000
codepoints across a dozen disjoint Unicode blocks (Arabic + Arabic
Supplement + Extended-A/B/C + Presentation Forms-A + Presentation
Forms-B + Mathematical Arabic + Coptic Epact + Rumi Numerals).
The platform's actual Arabic corpus uses **48** of those, all in
the basic U+0600-U+066A range. This script discards the unused
glyphs while keeping every OpenType GSUB/GPOS feature (which is
what HarfBuzz uses to pick contextual letter shapes — dropping
those would silently break Arabic rendering).

Usage:

    .venv/Scripts/python.exe scripts/subset_arabic_fonts.py

Idempotent: each run rebuilds the subset from the original woff2
checked in at `static/fonts/amiri/amiri-700-arabic.original.woff2`
(created on first run from whatever is on disk).

Tajawal is NOT subset by this script: its Google upstream is
already heavily pre-subset (each weight is ~9 KB), so further
subsetting yields a single-digit-KB delta and isn't worth the
shaping-regression risk.

See `docs/qa/lighthouse-mobile-baseline/P2_PERF_4_ARABIC_SUBSET_COMPARISON.md`
for the measurements, the rationale, and the visual-QA gate this
script is part of.
"""

from __future__ import annotations

import io
import re
import sys
from pathlib import Path

from fontTools.subset import Options, Subsetter
from fontTools.ttLib import TTFont

REPO_ROOT = Path(__file__).resolve().parents[1]
AMIRI_DIR = REPO_ROOT / "static" / "fonts" / "amiri"
AMIRI_LIVE = AMIRI_DIR / "amiri-700-arabic.woff2"
AMIRI_BACKUP = AMIRI_DIR / "amiri-700-arabic.original.woff2"
LOCALE_PO = REPO_ROOT / "locale" / "ar" / "LC_MESSAGES" / "django.po"
TEMPLATES_DIR = REPO_ROOT / "templates"

# Fixed keep-set that the subset must always carry, beyond whatever
# the corpus scan finds. Keeps the subset stable across small text
# edits and absorbs realistic near-term Arabic content additions.
#
# Note: the full U+0600-U+06FF Arabic block is added below in
# `compute_keep_set` regardless of whether each codepoint appears in
# the current corpus — over-coverage in the same block is essentially
# free, and it makes the subset robust to copy edits.
FIXED_EXTRAS: set[int] = {
    # ASCII space, NBSP — required for mixed-script text to break.
    0x0020,
    0x00A0,
    # Latin digits — show up in dates, prices, addresses on /ar/.
    *range(0x0030, 0x003A),
    # Arabic-Indic digits — keep for safety even if .po doesn't use
    # them today (a CMS edit could introduce them tomorrow).
    *range(0x0660, 0x066A),
    # Latin punctuation that appears in mixed-script content.
    0x002C,  # ,
    0x002E,  # .
    0x003A,  # :
    0x003B,  # ;
    0x003F,  # ?
    0x0021,  # !
    0x0028,  # (
    0x0029,  # )
    0x002D,  # -
    0x002F,  # /
    # Bidi / shaping control marks.
    0x200C,  # ZWNJ
    0x200D,  # ZWJ
    0x200E,  # LRM
    0x200F,  # RLM
    # NO-BREAK ZWNJ etc.
    0x202A,  # LRE
    0x202B,  # RLE
    0x202C,  # PDF
}

ARABIC_BLOCK = range(0x0600, 0x0700)  # entire basic Arabic block


def is_arabic(c: str) -> bool:
    """Loose test: any codepoint in any Arabic-flavoured block."""
    o = ord(c)
    return (
        0x0600 <= o <= 0x06FF
        or 0x0750 <= o <= 0x077F
        or 0xFB50 <= o <= 0xFDFF
        or 0xFE70 <= o <= 0xFEFF
    )


def scan_corpus() -> set[int]:
    """Read every Arabic-bearing source in the tree and return the
    union of codepoints actually used.

    Sources scanned: templates/**/*.html, locale/**/*.po,
    apps/**/*.py, docs/**/*.md, config/**/*.json. We deliberately do
    NOT scan .venv, node_modules, staticfiles, artifacts.
    """
    used: set[int] = set()
    skip_dirs = {".venv", "node_modules", ".git", "staticfiles", "artifacts", "__pycache__"}
    interesting_exts = {".html", ".po", ".py", ".md", ".json", ".txt"}
    for path in REPO_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part in skip_dirs for part in path.parts):
            continue
        if path.suffix.lower() not in interesting_exts:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for c in text:
            if is_arabic(c):
                used.add(ord(c))
    return used


def compute_keep_set() -> set[int]:
    """Union of: (a) every codepoint we actually use, (b) the full
    U+0600-06FF Arabic block (cheap over-coverage), (c) FIXED_EXTRAS.
    """
    used = scan_corpus()
    return used | set(ARABIC_BLOCK) | FIXED_EXTRAS


def ensure_backup() -> Path:
    """Stash the as-shipped Amiri 700 as the upstream reference.

    First run: copy the current woff2 to `.original.woff2`. Subsequent
    runs: use the backup as the input, so re-running the script is
    idempotent (we never re-subset an already-subset font, which
    would lose the original glyph table entirely).
    """
    if not AMIRI_BACKUP.exists():
        AMIRI_BACKUP.write_bytes(AMIRI_LIVE.read_bytes())
        print(f"  stashed upstream copy: {AMIRI_BACKUP.relative_to(REPO_ROOT)}")
    return AMIRI_BACKUP


def subset_amiri(keep_codepoints: set[int]) -> tuple[int, int]:
    """Run pyftsubset on Amiri 700 and write the result in place.

    Returns (input_size_bytes, output_size_bytes).
    """
    source = ensure_backup()
    input_size = source.stat().st_size

    opts = Options()
    # Keep every OpenType layout feature — Arabic shaping (isol /
    # init / medi / fina / liga / mset / rlig / mark / mkmk / ccmp
    # / kerning ...) is driven by GSUB/GPOS tables. Removing
    # features silently breaks contextual letter shapes.
    opts.layout_features = ["*"]
    # Keep the full name table (OFL "Reserved Font Name" attribution).
    opts.name_IDs = ["*"]
    # Keep language-tagged variants — Arabic has many.
    opts.name_languages = ["*"]
    # Keep notdef glyph so missing-codepoint rendering remains
    # consistent with the original.
    opts.notdef_glyph = True
    opts.notdef_outline = True
    # Output format: woff2, served by the existing `font-src 'self'`
    # allowlist. zopfli pass on the WOFF2 container.
    opts.flavor = "woff2"
    opts.with_zopfli = True
    # Don't drop hinting — Amiri carries hints for small Arabic text.
    opts.hinting = True
    # Keep glyph names off (smaller table; web doesn't need them).
    opts.glyph_names = False
    # Don't store deprecated CFF subroutines if any.
    opts.no_subset_tables += ["DSIG"]

    font = TTFont(source)
    subsetter = Subsetter(options=opts)
    subsetter.populate(unicodes=sorted(keep_codepoints))
    subsetter.subset(font)

    buf = io.BytesIO()
    font.flavor = "woff2"
    font.save(buf)
    output_bytes = buf.getvalue()
    AMIRI_LIVE.write_bytes(output_bytes)
    return input_size, len(output_bytes)


def format_unicode_range(codepoints: set[int]) -> str:
    """Render a sorted codepoint set as a comma-separated
    unicode-range string for a CSS @font-face rule.

    Collapses contiguous runs into `U+NNNN-NNNN` ranges.
    """
    sorted_cps = sorted(codepoints)
    ranges: list[tuple[int, int]] = []
    start = end = sorted_cps[0]
    for cp in sorted_cps[1:]:
        if cp == end + 1:
            end = cp
        else:
            ranges.append((start, end))
            start = end = cp
    ranges.append((start, end))

    parts = []
    for lo, hi in ranges:
        if lo == hi:
            parts.append(f"U+{lo:04X}")
        else:
            parts.append(f"U+{lo:04X}-{hi:04X}")
    return ", ".join(parts)


def main() -> int:
    print(f"Reading Arabic corpus from {REPO_ROOT}")
    keep = compute_keep_set()
    print(f"  keep-set size: {len(keep)} codepoints")
    print(f"  requested unicode-range:")
    print(f"    {format_unicode_range(keep)}")

    print(f"\nSubsetting {AMIRI_LIVE.relative_to(REPO_ROOT)}")
    in_size, out_size = subset_amiri(keep)
    delta = in_size - out_size
    pct = 100 * delta / in_size if in_size else 0
    print(f"  input:  {in_size:>7,} bytes ({in_size/1024:>6.1f} KB)")
    print(f"  output: {out_size:>7,} bytes ({out_size/1024:>6.1f} KB)")
    print(f"  saved:  {delta:>7,} bytes ({delta/1024:>6.1f} KB, -{pct:.1f}%)")

    # Amiri is an Arabic-only font: glyphs the keep-set requested
    # for Latin digits / Latin punctuation simply don't exist in
    # the source, so the post-subset cmap is narrower than the
    # requested keep-set. The CSS @font-face `unicode-range` must
    # match what the font ACTUALLY carries, not what we asked for —
    # otherwise the browser tries to render mismatched glyphs in
    # Amiri and falls through to .notdef instead of system fallback.
    font_out = TTFont(AMIRI_LIVE)
    actual_cmap = sorted(font_out.getBestCmap().keys())
    print(f"\nPost-subset cmap: {len(actual_cmap)} codepoints")
    print(f"CSS @font-face unicode-range for fonts.css:")
    print(f"  {format_unicode_range(set(actual_cmap))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
