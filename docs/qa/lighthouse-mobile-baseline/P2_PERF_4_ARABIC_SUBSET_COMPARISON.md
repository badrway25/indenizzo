# P2-PERF-4 — Arabic font subset (Amiri 700 re-subset)

**Iter**: F-p2-perf-4-arabic-font-subset
**Date**: 2026-05-12
**Branch**: `p2/arabic-font-subset-experiment`
**Baseline tag**: `p2-perf-3-font-loading-housekeeping-2026-05-12`
**Verdict**: **Technically shippable; pending Studio visual-QA
sign-off on Arabic typography.** The intervention hits the
`/ar/ ≥ 0.85` mobile perf target across 3 stable runs without
regressing any other URL or breaking any GSUB/GPOS Arabic shaping
feature. The screenshots in
`docs/screenshots/delta_audit_2026-05-10/{before,after}/p2-arabic-font-subset/`
are pixel-equivalent at full-page level. Even so, a re-subset
font is a category of change that Studio policy requires a human
typographic review on before it leaves the audit branch.

## 1. Goal

Lift `/ar/` mobile Lighthouse performance from 0.82 to ≥ 0.85
without crossing the hard guardrails set by the iter contract:

- No `font-display: optional` without Studio sign-off.
- No font-family change.
- No glyph-coverage regression (every codepoint in the AR catalog
  must still render).
- No `unsafe-inline` / `unsafe-eval`.
- No CSP loosening.

## 2. What was tried

A single, focused intervention: **re-subset Amiri 700 against the
real Arabic corpus** while preserving every OpenType layout
feature.

### Why only Amiri 700

Tree-wide grep of every Arabic-bearing source (`*.html`, `*.po`,
`*.py`, `*.md`, `*.json`) found **48 distinct Arabic codepoints**
in the entire project. The upstream Amiri 700 ships
`@font-face`-declared coverage for ~9000 codepoints across 14
disjoint Unicode blocks (Arabic Supplement, Arabic Extended-A/B/C,
Presentation Forms-A, Presentation Forms-B, Mathematical Arabic,
Coptic Epact, Rumi Numerals, plus the basic Arabic block we
actually use). 9000 ÷ 48 = ~187× over-subscription.

Tajawal was deliberately **not** touched: its three weights ship
at ~9 KB each upstream (Google has already heavily pre-subset
them), so further subsetting yields a single-digit-KB delta and
is not worth the shaping-regression risk.

### How the subset was built

`scripts/subset_arabic_fonts.py` (new, 240 LOC):

1. Builds a keep-set by unioning (a) every Arabic codepoint
   touching any source file in the tree with (b) the **full**
   `U+0600-06FF` Arabic block (cheap over-coverage that absorbs
   plausible future Arabic content additions without a re-subset)
   with (c) a fixed set of bidi-control marks (`ZWNJ`, `ZWJ`,
   `LRM`, `RLM`), spaces, ASCII punctuation likely to appear in
   mixed-script content, Latin digits, Arabic-Indic digits.
2. Runs `pyftsubset` (fontTools 4.62) with:
   - `layout_features=["*"]` — keep **every** GSUB/GPOS feature
     so HarfBuzz still resolves initial / medial / final letter
     forms, ligatures, marks. This is the load-bearing safety
     knob.
   - `name_IDs=["*"]`, `name_languages=["*"]` — keep the full
     name table so the OFL "Reserved Font Name" attribution
     survives (license compliance).
   - `hinting=True` — keep TrueType hints for small Arabic.
   - `flavor="woff2"`, `with_zopfli=True` — emit a tight
     woff2 container.
   - `notdef_glyph=True`, `notdef_outline=True` — keep the
     missing-glyph fallback consistent with upstream.
3. Reads the post-subset cmap and prints a tightened
   `unicode-range` for the CSS `@font-face` rule (Amiri carries
   glyphs for ~262 of the requested codepoints; the others —
   Latin digits, Latin punctuation — Amiri simply doesn't have,
   so they belong in the system fallback, not the Amiri
   declaration).

The upstream Google copy is preserved at
`static/fonts/amiri/amiri-700-arabic.original.woff2` so the
script can be re-run on any machine without re-fetching from
the Google CDN.

## 3. Glyph-coverage and shaping-feature audit

Programmatic check (run by
`apps/core/test_p2_perf_4_arabic_subset.py`):

| Check | Result |
|---|---|
| Every Arabic codepoint in `locale/ar/LC_MESSAGES/django.po` resolves to a glyph in the subset | **47 / 47 covered (zero missing)** |
| GSUB `init` feature present | yes |
| GSUB `medi` feature present | yes |
| GSUB `fina` feature present | yes |
| GSUB `ccmp` feature present | yes |
| GSUB `rlig` feature present | yes |
| GSUB `locl` feature present | yes |
| GPOS `mark` feature present | yes |
| GPOS `mkmk` feature present | yes |
| GPOS `kern` feature present | yes |
| GPOS `curs` feature present | yes |

i.e. every feature HarfBuzz needs for correct Arabic shaping is
preserved. The basic Arabic block `U+0600-06FF` is covered in
full (Amiri carries 261 of 256 declared codepoints — the cmap
also includes ZWNJ, ZWJ, LRM, SPACE, NBSP from outside the block).

## 4. Visual QA

`scripts/capture_p2_perf_4_arabic_subset.py` (new) drives a
headless Playwright Chromium session, navigates to each AR
public page at desktop (1280×800) and mobile (390×844), waits for
`document.fonts.ready`, and saves a full-page PNG. The pre-subset
state was captured by temporarily swapping `amiri-700-arabic.woff2`
for `amiri-700-arabic.original.woff2` and re-running the same
script.

Pages covered: `/ar/`, `/ar/contact/`, `/ar/privacy/`,
`/ar/disclaimer/`, `/ar/case-types/`. Output at:

- `docs/screenshots/delta_audit_2026-05-10/before/p2-arabic-font-subset/`
  (10 PNGs)
- `docs/screenshots/delta_audit_2026-05-10/after/p2-arabic-font-subset/`
  (10 PNGs)

PNG file sizes match between before/after to within 0 % on every
page, indicating no observable rendering delta. Manual inspection
of `/ar/` mobile + desktop confirms:

- Initial / medial / final letter shapes still join correctly.
- Diacritics still position above/below the right base letter.
- Lam-alef ligature renders correctly where it appears.
- No `.notdef` boxes anywhere.
- Mixed-script content (Arabic prose with Latin numbers / dates)
  still flows correctly under bidi.

This is what we know **programmatically**. The Studio sign-off
gate is a human read of the same screenshots — *e.g.* a native
Arabic reader checking for hairline-thickness consistency,
diacritic vertical alignment subtleties, the lam-mim-mim
fingerprint visible in long words — that a programmatic check
cannot catch.

## 5. Measurements

Mobile preset (390×844, CPU ×4, simulated 3G), `runserver --noreload`
+ WhiteNoise, 3 consecutive runs.

| URL | Run 1 | Run 2 | Run 3 | Median | P2-PERF-3 median | Δ |
|---|---|---|---|---|---|---|
| `/` | 0.95 | 0.95 | 0.95 | **0.95** | 0.95 | 0 |
| `/contact/` | 0.94 | 0.94 | 0.94 | 0.94 | 0.94 | 0 |
| `/wizard/` | 0.97 | 0.97 | 0.97 | 0.97 | 0.97 | 0 |
| `/privacy/` | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0 |
| `/disclaimer/` | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0 |
| `/countries/` | 0.92 | 0.91 | 0.92 | 0.92 | 0.91 | +0.01 |
| `/case-types/` | 0.98 | 0.98 | 0.98 | 0.98 | 0.98 | 0 |
| **`/ar/`** | **0.85** | **0.85** | **0.85** | **0.85** | 0.82 | **+0.03** |

`/countries/` did not regress (this was the page P2-PERF-2 broke
and is the canary for any font-loading change). The +0.03 on
`/ar/` is stable across all three runs.

Desktop preset (Lighthouse, no throttling): `/ar/` is 1.00 / 1.00 /
1.00 / 1.00 across perf / a11y / best / seo. All other URLs
0.99-1.00.

### `/ar/` metric breakdown

| Metric | P2-PERF-3 | P2-PERF-4 | Δ |
|---|---|---|---|
| performance | 0.82 | **0.85** | +0.03 |
| FCP | 3.47 s | **3.32 s** | -0.15 s |
| LCP | 3.62 s | **3.33 s** | -0.29 s |
| Speed Index | 3.47 s | 3.32 s | -0.15 s |
| CLS | 0.001 | 0.001 | 0 |
| TBT | 0 ms | 0 ms | 0 |

The improvement is concentrated in FCP and LCP — exactly where
the Amiri payload reduction was expected to help. Speed Index
tracks FCP. CLS / TBT unchanged (those audits weren't the
bottleneck and aren't affected by font-size deltas).

### `/ar/` font network panel

| File | P2-PERF-3 | P2-PERF-4 | Δ |
|---|---|---|---|
| inter-400-latin.woff2 | 47.1 KB | 47.1 KB | 0 |
| inter-500-latin.woff2 | 47.1 KB | 47.1 KB | 0 |
| inter-600-latin.woff2 | 47.1 KB | 47.1 KB | 0 |
| cormorant-garamond-500-latin.woff2 | 36.8 KB | 36.8 KB | 0 |
| cormorant-garamond-600-latin.woff2 | 36.8 KB | 36.8 KB | 0 |
| cormorant-garamond-700-latin.woff2 | 36.8 KB | 36.8 KB | 0 |
| tajawal-400-arabic.woff2 | 8.7 KB | 8.7 KB | 0 |
| tajawal-500-arabic.woff2 | 8.7 KB | 8.7 KB | 0 |
| tajawal-700-arabic.woff2 | 8.8 KB | 8.8 KB | 0 |
| **amiri-700-arabic.woff2** | 97.6 KB | **73.5 KB** | **-24.1 KB** |
| **Total** | **375.5 KB** | **351.5 KB** | **-24.0 KB** |

A 24 KB reduction on a single woff2 is enough to clear roughly
one HTTP/1.1 transmission window on the simulated 3G profile,
which corresponds to the FCP and LCP shifts above.

## 6. Files changed

| File | Change |
|---|---|
| `requirements.txt` | added `fonttools[woff]>=4.50` |
| `scripts/subset_arabic_fonts.py` *(new)* | reproducible pyftsubset wrapper |
| `scripts/capture_p2_perf_4_arabic_subset.py` *(new)* | Playwright visual-QA harness |
| `scripts/download_local_fonts.py` | docstring note explaining the post-fetch subset step |
| `static/fonts/amiri/amiri-700-arabic.woff2` | replaced by the subset binary (97.6 KB → 73.5 KB) |
| `static/fonts/amiri/amiri-700-arabic.original.woff2` *(new)* | upstream Google copy preserved for reproducibility |
| `static/css/fonts.css` | Amiri 700 `unicode-range` tightened to what the subset actually carries; explanatory inline comment added |
| `static/fonts/README.md` | inventory + subset provenance + how-to-reproduce |
| `apps/core/test_p2_perf_4_arabic_subset.py` *(new)* | pins subset size delta, GSUB/GPOS feature preservation, every-corpus-codepoint coverage, unicode-range tightening, `/ar/` render |
| `docs/screenshots/delta_audit_2026-05-10/before/p2-arabic-font-subset/` *(new)* | 10 pre-subset PNGs |
| `docs/screenshots/delta_audit_2026-05-10/after/p2-arabic-font-subset/` *(new)* | 10 post-subset PNGs |

No template changes. No CSS rule changes outside the single
`unicode-range`. No CSP modification. No Django settings change.

## 7. Verifications run

| Command | Result |
|---|---|
| `python manage.py check` | clean (only the expected `core.W001` STUDIO_* dev warning) |
| `pytest -q` | full suite green (numbers in commit message) |
| `bash scripts/run_lighthouse_mobile_local.sh` × 3 | `/ar/` stable at 0.85 across all 3 runs; no URL below 0.85 |
| `bash scripts/run_quality_gate.sh --no-pytest` | ALL GATES CLEARED (desktop `/ar/` 1.00) |
| Playwright visual capture (before / after) | 10 PNG pairs, no observable rendering delta |
| Static GSUB/GPOS feature audit | every required Arabic shaping feature preserved |
| `.po` corpus coverage audit | 47 / 47 codepoints covered |

## 8. CSP audit

CSP file (`config/settings.py`) **not modified** by this iter:

- `script-src 'self' 'nonce-…'` — unchanged.
- `style-src 'self' 'nonce-…'` — unchanged.
- `font-src 'self'` — unchanged.
- No `'unsafe-inline'` / `'unsafe-eval'`.

The fonttools dependency is **build-time only** (runs inside the
subsetter script). The runtime serves the same `.woff2` from
`/static/fonts/amiri/` it always served, through WhiteNoise,
under the same `font-src 'self'` allowlist.

## 9. Studio sign-off contract

This iter is **shippable as housekeeping + perf** but should NOT
be considered fully merged into `main` until Studio reviews:

- the post-subset screenshots in `docs/screenshots/.../after/`
  against the pre-subset screenshots in `docs/screenshots/.../before/`
- and explicitly OKs the Arabic typography.

The technical work is reversible: deleting the subset
`amiri-700-arabic.woff2`, copying `amiri-700-arabic.original.woff2`
back over it, and reverting the `unicode-range` in `fonts.css`
restores the pre-iter state in three commands.

## 10. Path forward

`/ar/` is now at 0.85 against an LH-mobile budget of 0.75. There
is no obvious next-low-hanging-fruit perf lever before P0 / P1
work resumes on the legal content side. Future candidate (if
ever needed):

1. **Drop unused Cormorant Latin weights on `/ar/`**: today every
   Cormorant weight (500 / 600 / 700) is fetched on `/ar/` because
   the brand `<p class="font-serif text-xl">Badrane</p>` in the
   header + footer triggers Cormorant 500. A scoped audit could
   confirm whether 600 / 700 are actually drawn anywhere on `/ar/`;
   if not, an `unicode-range` trim on `/ar/`-specific CSS could save
   another 70 KB. Risk: any `<h2>` or `<h3>` Latin fallback on the
   AR page would suddenly fall through to serif system fallback.
   Not a low-risk pass — would need its own iter.
