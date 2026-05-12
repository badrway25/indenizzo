"""Download `.woff2` files for local hosting (P1-SEC-1).

One-shot helper: fetches the Google Fonts CSS for the four families
the platform uses, filters the `@font-face` blocks to the unicode
ranges actually needed (latin / latin-ext for LTR fonts, arabic for
RTL fonts), downloads each `.woff2` from fonts.gstatic.com and saves
it to `static/fonts/<family>/<weight>.woff2`.

Run once locally to refresh the vendored set:

    python scripts/download_local_fonts.py

The script also emits `static/css/fonts.css` with the local
`@font-face` rules.

IMPORTANT — F-p2-perf-4 (2026-05-12): Amiri 700 is **re-subset
locally** after the upstream fetch by `scripts/subset_arabic_fonts.py`,
and the `unicode-range` in `static/css/fonts.css` is tightened to
match what the post-subset font actually carries. If you re-run
this script, you MUST also re-run the Amiri subsetter AND restore
the tightened Amiri `@font-face` block in `fonts.css`. The
upstream Google copy is preserved at
`static/fonts/amiri/amiri-700-arabic.original.woff2` and is the
input the subsetter reads.
"""

from __future__ import annotations

import re
import sys
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
FONTS_DIR = REPO_ROOT / "static" / "fonts"
CSS_PATH = REPO_ROOT / "static" / "css" / "fonts.css"

CHROME_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
)

# Each family: which weights, which unicode subsets to keep.
#
# F-p2-perf-3 (2026-05-12): Inter 700 and Amiri 400 were removed.
# Lighthouse mobile network panels showed neither weight was ever
# fetched by a real page render (templates default to the system
# `font-bold` keyword which Tailwind resolves to 700 only for the
# sans-serif body — but body text in headers and CTAs uses Inter
# 500/600 explicitly, and `font-bold` Latin text outside h1-h3
# does not exist in the public templates; for Arabic, `<b>` /
# default-bold Cormorant tags do not render Amiri 400 because
# RTL pages always inherit a bold weight). Dropping the unused
# weights saves ~95 KB of .woff2 ship weight per release and
# removes the spurious entries from the `Cache-Control: immutable`
# WhiteNoise manifest. See
# `docs/qa/lighthouse-mobile-baseline/P2_PERF_3_COMPARISON.md`.
FAMILIES = [
    {
        "family": "Inter",
        "slug": "inter",
        "weights": [400, 500, 600],
        "subsets": {"latin", "latin-ext"},
    },
    {
        "family": "Cormorant Garamond",
        "slug": "cormorant-garamond",
        "weights": [500, 600, 700],
        "subsets": {"latin", "latin-ext"},
    },
    {
        "family": "Amiri",
        "slug": "amiri",
        "weights": [700],
        "subsets": {"arabic"},
    },
    {
        "family": "Tajawal",
        "slug": "tajawal",
        "weights": [400, 500, 700],
        "subsets": {"arabic"},
    },
]

# `@font-face` block pattern: subset comment + the block itself.
BLOCK_RE = re.compile(
    r"/\*\s*([\w-]+)\s*\*/\s*@font-face\s*\{([^}]+)\}",
    re.DOTALL,
)
URL_RE = re.compile(r"url\((https://fonts\.gstatic\.com/[^)]+)\)\s*format\('woff2'\)")
WEIGHT_RE = re.compile(r"font-weight:\s*(\d+)")
UNICODE_RANGE_RE = re.compile(r"unicode-range:\s*([^;]+);")


def fetch(url: str, *, binary: bool = False):
    req = urllib.request.Request(url, headers={"User-Agent": CHROME_UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read() if binary else resp.read().decode("utf-8")


def css_url(family: str, weights: list[int]) -> str:
    fam = family.replace(" ", "+")
    w = ";".join(str(x) for x in weights)
    return f"https://fonts.googleapis.com/css2?family={fam}:wght@{w}&display=swap"


def slugify_subset(subset: str) -> str:
    return subset.replace("[", "").replace("]", "").lower()


def process(family_spec: dict) -> list[str]:
    """Returns @font-face CSS blocks pointing at the vendored files."""
    family = family_spec["family"]
    slug = family_spec["slug"]
    needed_weights = family_spec["weights"]
    keep_subsets = family_spec["subsets"]

    css_text = fetch(css_url(family, needed_weights))
    out_dir = FONTS_DIR / slug
    out_dir.mkdir(parents=True, exist_ok=True)

    rules: list[str] = []
    seen: set[tuple[int, str]] = set()  # (weight, subset) — guard duplicates

    for match in BLOCK_RE.finditer(css_text):
        subset = match.group(1).strip()
        block = match.group(2)
        if subset not in keep_subsets:
            continue
        url_match = URL_RE.search(block)
        weight_match = WEIGHT_RE.search(block)
        urange_match = UNICODE_RANGE_RE.search(block)
        if not (url_match and weight_match and urange_match):
            print(f"  skip: incomplete block in {family} ({subset})")
            continue
        weight = int(weight_match.group(1))
        if weight not in needed_weights:
            continue
        key = (weight, subset)
        if key in seen:
            continue
        seen.add(key)

        gstatic_url = url_match.group(1)
        woff2_bytes = fetch(gstatic_url, binary=True)
        filename = f"{slug}-{weight}-{slugify_subset(subset)}.woff2"
        target = out_dir / filename
        target.write_bytes(woff2_bytes)
        size_kb = len(woff2_bytes) / 1024
        print(f"  {family} weight={weight} subset={subset}: {filename} ({size_kb:.1f} KB)")

        rule = (
            f"@font-face {{\n"
            f"  font-family: '{family}';\n"
            f"  font-style: normal;\n"
            f"  font-weight: {weight};\n"
            f"  font-display: swap;\n"
            f"  src: url('../fonts/{slug}/{filename}') format('woff2');\n"
            f"  unicode-range: {urange_match.group(1).strip()};\n"
            f"}}"
        )
        rules.append(rule)

    return rules


def main() -> int:
    print(f"Vendoring fonts into {FONTS_DIR}")
    all_rules: list[str] = []
    for spec in FAMILIES:
        print(f"\n[{spec['family']}]")
        all_rules.extend(process(spec))

    header = (
        "/*\n"
        " * Local web fonts (P1-SEC-1).\n"
        " *\n"
        " * Sourced from Google Fonts CSS API (fonts.googleapis.com/css2)\n"
        " * with .woff2 files downloaded from fonts.gstatic.com. Each\n"
        " * family ships under SIL Open Font License 1.1; see\n"
        " * static/fonts/LICENSES/ for the per-family license files.\n"
        " *\n"
        " * Generated by scripts/download_local_fonts.py — re-run that\n"
        " * script (or hand-edit) to refresh the vendored set.\n"
        " */\n\n"
    )
    CSS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CSS_PATH.write_text(header + "\n\n".join(all_rules) + "\n", encoding="utf-8")
    total_kb = sum(
        f.stat().st_size for f in FONTS_DIR.glob("*/*.woff2")
    ) / 1024
    print(f"\nWrote {CSS_PATH.relative_to(REPO_ROOT)}")
    print(f"Total woff2 size: {total_kb:.1f} KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
