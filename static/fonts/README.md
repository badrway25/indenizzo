# Local web fonts

**Iter**: P1-SEC-1 (`p1/local-fonts-csp-hardening`).
**Date**: 2026-05-10.

This directory holds the `.woff2` files served from `/static/fonts/`
so the platform no longer depends on `fonts.googleapis.com` and
`fonts.gstatic.com` at runtime. With local fonts, the CSP can drop
the two CDN allowlist entries (`style-src` and `font-src`).

The `@font-face` rules pointing at these files live in
`static/css/fonts.css`. `templates/base.html` includes that file
instead of the Google Fonts `<link>` it used to load.

## Inventory

| Family | Weights | Subsets | Files | Notes |
|---|---|---|---|---|
| Inter | 400, 500, 600 | latin, latin-ext | 6 | Google Fonts upstream subset, unmodified. |
| Cormorant Garamond | 500, 600, 700 | latin, latin-ext | 6 | Google Fonts upstream subset, unmodified. |
| Amiri | 700 | arabic | 1 (+ `.original.woff2`) | **Re-subset locally** — see `scripts/subset_arabic_fonts.py`. |
| Tajawal | 400, 500, 700 | arabic | 3 | Google Fonts upstream subset, unmodified. |

Inter 700 was removed in **F-p2-perf-3** (2026-05-12): no public
template renders Latin text with `font-weight: 700` outside the
`<h1>`/`<h2>`/`<h3>` rule, which targets Cormorant Garamond (serif),
not Inter. Browser font matching now resolves the few default-bold
sans-serif fragments (e.g. `<strong>` on the staff-only MFA page) to
Inter 600, which is visually indistinguishable at body sizes and
never on a public hot path.

Amiri 400 was removed in the same pass: the RTL templates set every
Amiri-rendered element to a bold weight via the `<h1>`/`<h2>`/`<h3>`
inherit chain, and Lighthouse mobile runs on `/ar/` never fetched
the 400 weight. Browser matching falls back to Amiri 700 if a 400
ever does appear.

See `docs/qa/lighthouse-mobile-baseline/P2_PERF_3_COMPARISON.md`.

### Amiri 700 re-subset (F-p2-perf-4, 2026-05-12)

The Google Fonts CDN ships an `amiri-700-arabic.woff2` covering
~9000 codepoints across 14 disjoint Unicode blocks (Arabic
Supplement, Arabic Extended-A/B/C, Presentation Forms-A,
Presentation Forms-B, Mathematical Arabic, Coptic Epact, Rumi
Numerals). A tree-wide grep shows the platform's actual Arabic
corpus uses **48** codepoints, all in the basic Arabic block
(`U+0600-06FF`).

`scripts/subset_arabic_fonts.py` re-subsets Amiri 700 against the
real corpus while **preserving every OpenType GSUB/GPOS layout
feature** — `init`, `medi`, `fina`, `ccmp`, `rlig`, `locl`, `mark`,
`mkmk`, `kern`, `curs` — which is what HarfBuzz uses to drive
Arabic contextual shaping. Stripping those features would silently
break Arabic rendering; the script does not allow that.

Size delta on disk: 97.6 KB → 73.5 KB (-24.7 %). The upstream
reference is preserved at `amiri/amiri-700-arabic.original.woff2`
so the subset is fully reproducible without re-fetching from the
Google CDN:

```
.venv/Scripts/python.exe scripts/subset_arabic_fonts.py
```

See `docs/qa/lighthouse-mobile-baseline/P2_PERF_4_ARABIC_SUBSET_COMPARISON.md`
for the full measurements, the visual-QA harness, and the
Studio-sign-off contract.

`latin` covers the basic Latin range used by Italian, French and
English (including the accented letters `à è é ì ò ù ç …`).
`latin-ext` is kept for robustness: the platform handles
cross-border cases where contact-form names may include
Polish/Czech/Romanian glyphs.

`arabic` covers the AR locale (RTL).

## Source

All four families ship under the **SIL Open Font License 1.1**
(commercial self-hosting permitted; see per-family files in
`LICENSES/`).

The `.woff2` binaries were obtained via the official Google Fonts
CSS API (`fonts.googleapis.com/css2?family=…`) which serves a
manifest of versioned files hosted on `fonts.gstatic.com`. Only
the unicode subsets actually needed by the platform were kept; the
script discards `cyrillic`, `greek`, `vietnamese` and similar.

The license `.txt` files were downloaded from each family's
canonical upstream:

- `Inter-OFL.txt` — `github.com/rsms/inter`
- `CormorantGaramond-OFL.txt` — `github.com/CatharsisFonts/Cormorant`
- `Amiri-OFL.txt` — `github.com/aliftype/amiri`
- `Tajawal-OFL.txt` — `github.com/google/fonts`

## How to refresh

`scripts/download_local_fonts.py` regenerates the `.woff2` files and
the `static/css/fonts.css` rules from a single command:

```
python scripts/download_local_fonts.py
```

The script:

1. queries the Google Fonts CSS API for the four families with the
   weights listed in the `FAMILIES` constant;
2. parses the response and keeps only the `@font-face` blocks for
   the configured `subsets`;
3. downloads each `.woff2` from the URL embedded in the response;
4. emits `static/css/fonts.css` with the correct
   `unicode-range` per family.

If a Google Fonts version bumps the URL hashes upstream, re-running
the script and committing the diff is the supported path.

## Why `font-display: swap`

To avoid invisible text on slow networks. The browser renders the
fallback first and swaps in the local font when ready — the same
behavior the previous Google Fonts integration used.
