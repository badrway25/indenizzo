# P2-PERF-4 — Arabic font subset visual QA

**Date**: 2026-05-12
**Iter**: F-p2-perf-4-arabic-font-subset
**Branch**: `p2/arabic-font-subset-experiment`
**Verdict**: technically shippable; pending Studio visual-QA sign-off.

This directory holds the **post-subset** Playwright captures
of the public AR pages. The matching **pre-subset** captures are in
`../../before/p2-arabic-font-subset/`. The full reasoning + the
Lighthouse numbers are in
`docs/qa/lighthouse-mobile-baseline/P2_PERF_4_ARABIC_SUBSET_COMPARISON.md`.

## How the captures were made

`scripts/capture_p2_perf_4_arabic_subset.py` drives headless
Chromium via Playwright, sets `locale=ar`, navigates to each AR
public page at desktop (1280×800, DPR 2) and mobile (390×844,
DPR 2), waits for `document.fonts.ready`, then takes a full-page
screenshot.

Pages covered:

- `/ar/` (home)
- `/ar/contact/`
- `/ar/privacy/`
- `/ar/disclaimer/`
- `/ar/case-types/`

For each page, both viewports were captured — so 10 PNGs total.

## What the screenshots prove (and don't)

**They prove**: the subsetted Amiri 700 carries every Arabic
glyph used on every AR public page. No `.notdef` boxes appear.
Letters join properly (init/medi/fina shapes). Diacritics
position correctly above/below base letters. Bidi is preserved
in mixed-script content.

**They do NOT prove**: that a native Arabic reader would judge
the typography visually equivalent. Things like hairline
consistency across stylistic-set substitutions, the precise
vertical offset of a tashdid + fatha stack on a particular base
letter, or the lam-mim-mim contour fingerprint visible only in
long words — these require a human review. That review is the
Studio sign-off gate documented in `P2_PERF_4_..._COMPARISON.md` §9.

## How to reproduce

1. Start runserver in one shell:
   ```
   .venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
   ```
2. From another shell:
   ```
   .venv/Scripts/python.exe scripts/capture_p2_perf_4_arabic_subset.py
   ```

The script overwrites the PNGs in this directory.

## What if the subset breaks Arabic in a future Amiri bump

`scripts/subset_arabic_fonts.py` reads from
`static/fonts/amiri/amiri-700-arabic.original.woff2` (the upstream
Google copy). If Google ships a different Amiri 700 build, the
subset can be rebuilt by:

1. Re-running `scripts/download_local_fonts.py` to refresh the
   `.original.woff2`.
2. Re-running `scripts/subset_arabic_fonts.py`.
3. Re-capturing this directory + the `before/` peer.
4. Re-comparing against the prior set under Studio review.

The test pin `test_every_corpus_codepoint_has_a_glyph_in_subset`
in `apps/core/test_p2_perf_4_arabic_subset.py` catches the worst
class of regression (a corpus codepoint without a glyph) without
needing a human review.
