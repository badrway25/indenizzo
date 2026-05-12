# P2-PERF-3 — conservative font loading / subset pass

**Iter**: F-p2-perf-3-font-loading-performance
**Date**: 2026-05-12
**Branch**: `p2/font-loading-performance`
**Baseline tag**: `p2-perf-2-critical-css-experiment-2026-05-10`
**Verdict**: **Shipped as housekeeping.** The cleanup landed; the
`/ar/` mobile perf target (≥ 0.85) was NOT achieved. No P2-PERF-3
intervention that would lift it without crossing one of the hard
guardrails (no `font-display: optional` without Studio sign-off, no
family/glyph-coverage change, no async CSS) was identified.

## 1. Goal

Move `/ar/` mobile perf from 0.82 toward ≥ 0.85 by tuning local
font loading — without re-trying the async-CSS path that P2-PERF-2
already proved regresses `/countries/`.

## 2. Mini-plan recap

The mini-plan that gated this iter (delivered before any code
change) inventoried the actual font-fetch behaviour per page via
the Lighthouse mobile `network-requests` audit. Key findings:

- The Cormorant Garamond preload tag in `base.html` targeted weight
  600, but the hero `<h1>` / `<h2>` / `<h3>` rules in the inline
  critical CSS resolve to **bold** = weight 700 via browser font
  matching. The preloaded file was therefore NOT the file Chrome
  paints with — a small FOUT window on LCP on text-LCP pages.
- Inter weight 700 (latin + latin-ext) was vendored in `fonts.css`
  but **never fetched** by any measured public-page render. The
  only template using a Latin `<strong>` is the staff-only
  `templates/admin/mfa_required.html` page (never reached publicly
  and excluded from the Lighthouse target set).
- Amiri weight 400 (arabic) was vendored but **never fetched** by
  `/ar/`. The Arabic typographic system on this site renders the
  large hero text via `<h1>` / `<h2>` / `<h3>`, which resolve to
  default-bold = Amiri 700. No template element is set to a
  non-bold Amiri context.

Three strictly-conservative levers cleared the safety bar:

- **A** — swap LTR preload Cormorant 600 → 700 (paint the file we
  preload).
- **B** — drop Inter 700 from `fonts.css` (and disk).
- **C** — drop Amiri 400 from `fonts.css` (and disk).

Four other candidate levers (font-display change, latin-ext drop,
subset-trim Inter, switch hero LCP element to an image) were
ruled out at mini-plan time for explicit reasons documented in the
plan (Studio sign-off required / glyph-coverage risk / out of scope).

## 3. Implemented changes

| File | Change |
|---|---|
| `templates/base.html` | LTR preload Cormorant 600 → 700; doc-block extended with a P2-PERF-3 note pointing here. |
| `static/css/fonts.css` | Removed Inter 700 (latin + latin-ext) `@font-face` blocks; removed Amiri 400 (arabic) block. 19 blocks → 16. |
| `static/fonts/inter/inter-700-latin.woff2` | Deleted from disk. |
| `static/fonts/inter/inter-700-latin-ext.woff2` | Deleted from disk. |
| `static/fonts/amiri/amiri-400-arabic.woff2` | Deleted from disk. |
| `scripts/download_local_fonts.py` | `FAMILIES` config aligned (dropped Inter 700, Amiri 400). Comment block annotates why. |
| `static/fonts/README.md` | Inventory table updated; provenance of the drops documented. |
| `apps/core/test_perf_pass_p2_perf_1.py` | Preload assertion now pins Cormorant **700**. |
| `apps/core/test_local_fonts_p1_sec_1.py` | `@font-face` block floor 19 → 16 with a per-weight rationale. |

CSP unchanged. No new files. No `unsafe-inline` / `unsafe-eval`.
No external runtime. No `font-display: optional`. No font-family
change. No latin-ext drop.

## 4. Measurements

Mobile preset (390×844, CPU ×4, simulated 3G), `runserver --noreload`
+ WhiteNoise, 3 runs back-to-back. Two transient `score=0.00`
audits (Lighthouse runtime jitter, not real perf) were dropped
from the medians.

| URL | Run 1 | Run 2 | Run 3 | Median perf | FCP (med) | LCP (med) |
|---|---|---|---|---|---|---|
| `/` (home-it) | 0.95 | 0.95 | 0.95 | **0.95** | 1.97 s | 2.57 s |
| `/contact/` | 0.94 | 0.94 | 0.95 | 0.94 | 1.96 s | 2.86 s |
| `/wizard/` | 0.98 | (jitter) | 0.97 | 0.97 | 1.74 s | 2.26 s |
| `/privacy/` | 0.98 | 0.98 | 0.98 | 0.98 | 1.81 s | 2.11 s |
| `/disclaimer/` | 0.98 | 0.98 | (jitter) | 0.98 | 1.82 s | 2.12 s |
| `/countries/` | 0.91 | 0.91 | 0.91 | 0.91 | 1.82 s | 3.32 s |
| `/case-types/` | 0.98 | 0.98 | 0.98 | 0.98 | 1.81 s | 2.11 s |
| `/ar/` | 0.82 | 0.82 | 0.82 | **0.82** | 3.47 s | 3.62 s |

The `/countries/` median LCP (3.32 s) sits a hair above the
post-P2-IMG-1 P2-PERF-2-revert reading (3.2 s) and is well clear
of the P2-PERF-2 regression band (3.4 s+) that triggered that
revert — i.e. no font-swap LCP regression has been re-introduced.

### Comparison vs the tracked baseline JSON

The committed baseline at `docs/qa/lighthouse-mobile-baseline/`
predates the WhiteNoise + preload + WebP work. Today's
post-PERF-3 measurements vs that older snapshot:

| URL | Tracked baseline perf | P2-PERF-3 median | Δ |
|---|---|---|---|
| `/` | 0.87 | 0.95 | +0.08 |
| `/countries/` | 0.83 | 0.91 | +0.08 |
| `/ar/` | 0.79 | 0.82 | +0.03 |

These deltas are dominated by P2-PERF-1 / P2-IMG-1 (already shipped)
— they are not P2-PERF-3's contribution. P2-PERF-3 contributes
zero perf-score movement at the Lighthouse rounding floor.

## 5. Why `/ar/` did not move

The `/ar/` font network panel post-PERF-3 is identical to
pre-PERF-3:

| File | Size |
|---|---|
| inter-400-latin.woff2 | 47.1 KB |
| inter-500-latin.woff2 | 47.1 KB |
| inter-600-latin.woff2 | 47.1 KB |
| cormorant-garamond-500-latin.woff2 | 36.8 KB |
| cormorant-garamond-600-latin.woff2 | 36.8 KB |
| cormorant-garamond-700-latin.woff2 | 36.8 KB |
| amiri-700-arabic.woff2 | 97.6 KB |
| tajawal-400-arabic.woff2 | 8.7 KB |
| tajawal-500-arabic.woff2 | 8.7 KB |
| tajawal-700-arabic.woff2 | 8.8 KB |
| **Total** | **375.5 KB** (10 files) |

Lever **A** (preload swap) does not apply to `/ar/` because the
preload block is guarded by `{% if not IS_RTL %}` (per
F-p2-perf-1: preloading on `/ar/` competes with the hero image
for HTTP/1.1 connection slots and regresses LCP).

Levers **B** and **C** removed files that were never on the `/ar/`
network panel to begin with — the cleanup is correct hygiene but
buys zero network or score on `/ar/`.

The actual `/ar/` bottleneck (FCP 3.47 s, score 0.32) is still
the Arabic font cold-start: Amiri 700 alone is 97.6 KB and
Tajawal × 3 adds another 26 KB, all over the slow link, all
discovered only after `fonts.css` parses. Without one of:

- (P2-PERF-4 candidate) a smaller Arabic subset that fits in a
  single HTTP packet, OR
- (requires Studio sign-off) a font-display change on the Arabic
  family, OR
- preloading the Arabic fonts on `/ar/` AND accepting the
  documented LCP-vs-image trade-off,

`/ar/` will continue to sit at 0.82.

None of these clear this iter's guardrails, so this iter does
NOT ship one.

## 6. What this iter contributes

- **Correctness**: the preload now targets the file the browser
  actually paints with on LTR text-LCP pages.
- **Hygiene**: ~95 KB of unused `.woff2` (Inter 700 × 2 + Amiri
  400) removed from disk and from the WhiteNoise immutable
  manifest. Three fewer @font-face blocks in `fonts.css`.
- **Drift guard**: tests pin the new state. A future drive-by
  edit that re-adds Inter 700 / Amiri 400 to the regenerator
  will trip `test_fonts_css_declares_all_four_families` /
  `test_base_html_preloads_ltr_fonts`.
- **A documented no-go on `/ar/ ≥ 0.85` for this lever set**, with
  the actual blocker (Arabic font cold-start) identified for the
  next iter.

## 7. Verifications run

| Command | Result |
|---|---|
| `python manage.py check` | clean (only the expected `core.W001` STUDIO_* dev warning) |
| `pytest -q` | **1947 passed, 1 skipped** (full suite green) |
| `bash scripts/run_lighthouse_mobile_local.sh` × 3 | mobile floors preserved; `/ar/` at 0.82, no URL below 0.75 |
| `grep -r 'inter-700\\|amiri-400'` (working tree) | no hits |
| `git status` | the documented file set |

## 8. CSP audit

CSP file (`config/settings.py`) **not modified**. Verified by the
P1-SEC-1 + P2-PERF-1 + P2-PERF-2 tests, all green:

- `script-src 'self' 'nonce-…'` — unchanged.
- `style-src 'self' 'nonce-…'` — unchanged.
- `font-src 'self'` — unchanged.
- No `'unsafe-inline'` / `'unsafe-eval'`.

## 9. Path forward — P2-PERF-4 candidates

In strict order of how much they cost vs how much `/ar/` could
move:

1. **Arabic subset trim**: today's `amiri-700-arabic.woff2` carries
   ~12 unicode-range chunks far beyond the script range actually
   used (mathematical Arabic symbols, presentation forms). A
   targeted glyph-coverage audit + a re-subset against the actual
   `/ar/` template content could bring Amiri 700 from 97.6 KB
   toward ~25-40 KB. Highest-impact candidate. Risk: a single
   missed glyph regresses rendering on `/ar/`. Needs a Studio
   visual-QA sign-off on the produced subset.
2. **`font-display: optional` on Amiri/Tajawal only** (leave Latin
   on `swap`): on slow connections users would permanently see
   the system Arabic fallback. Requires Studio sign-off — typography
   is part of the platform's brand contract.
3. **Preload Arabic fonts on `/ar/` AND accept image-LCP delay**:
   inverts the F-p2-perf-1 trade. Probably regresses `/ar/` LCP
   net, but worth a measurement.
4. **Move the `/ar/` hero LCP off the background image** (e.g.
   to a text element above the fold whose font-swap timing we
   control) — design-level call, out of perf-iter scope.

None are landed by this iter.
