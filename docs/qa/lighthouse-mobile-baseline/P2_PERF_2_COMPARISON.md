# P2-PERF-2 — critical CSS / async stylesheet loading

**Iter**: F-p2-perf-2-critical-css-performance
**Date**: 2026-05-11
**Baseline tag**: `p2-img-1-hero-image-optimization-2026-05-10`
**Verdict**: **Experiment NOT shipped.** The proposed change was
implemented, measured, and reverted on the same branch after the
trade-off failed to clear in favour of shipping. This document
captures the negative result so the next perf iter can build on
it.

## 1. Goal

Move `/ar/` mobile perf to ≥ 0.85 by removing the render-blocking
CSS dependency on the first paint — the bottleneck identified
in `P2_IMG_1_COMPARISON.md` §6 (FCP score 0.35 / 3.5 s).

## 2. What was tried

A four-step intervention compatible with the existing CSP
(`script-src 'self' 'nonce-…'`, no `unsafe-inline`, no
`unsafe-eval`, no inline event handlers):

1. **Critical-CSS partial** (`templates/partials/_critical_css.html`,
   ~5 KiB nonce-protected `<style>` block) — extracted from
   `site.css` the rules used above-the-fold: design tokens,
   reset, container/grid utilities, hero positioning, hero
   typography, CTA pills, focus ring, reduce-motion, RTL
   overrides, and (in the iteration that came closest to working)
   the height utilities the secondary hero `<figure>` depends on.

2. **Async stylesheet loader** (`static/js/css-loader.js`, 1.7 KiB):
   a self-hosted, defer-loaded, nonce-protected `<script>` that
   creates and appends a `<link rel="stylesheet" href="site.css">`
   after HTML parse. No inline JS. Idempotent (skips if a
   sibling `<link>` already references the file).

3. **Preload of the deferred stylesheet**
   (`<link rel="preload" as="style" href="site.css">`): kicks the
   network fetch off in parallel with HTML parse, so the JS
   loader's later `<link>` attachment is a cache hit instead of a
   second round-trip.

4. **`<noscript>` fallback** (`<noscript><link rel="stylesheet"
   href="site.css"></noscript>`): JS-disabled clients keep the
   pre-experiment behaviour — render-blocking `<link>`, no
   reliance on the loader, identical paint.

CSP was unchanged throughout: `script-src 'self' 'nonce-…'` allows
the loader (it carries the nonce + is on `'self'`); `style-src
'self' 'nonce-…'` covers both the inline critical block and the
dynamically-attached `<link>`. **No `unsafe-inline` was
introduced at any point.**

## 3. Measurements

Mobile preset (390×844, CPU ×4, simulated 3G), runserver +
WhiteNoise gzip, fresh measurements per state.

### `/ar/`

| Metric | Baseline (P2-IMG-1) | Experiment | Reverted (final) |
|---|---|---|---|
| performance | 0.82 | **0.84** | 0.82 |
| FCP | 3.5 s (score 0.35) | 1.7 s (score 0.91) | 3.5 s (score 0.35) |
| LCP | 3.6 s (score 0.60) | 3.6 s (score 0.60) | 3.6 s (score 0.60) |
| CLS | 0.001 | 0.001 | 0.001 |
| TBT | 0 ms | 0 ms | 0 ms |
| Speed Index | 3.5 s (0.88) | 1.7 s (1.00) | 3.5 s (0.88) |

`/ar/` clearly benefited. FCP halved (3.5 s → 1.7 s). Perf score
went +0.02. Target ≥ 0.85 was 0.01 short.

### `/countries/` — the regression that triggered the revert

| Metric | Baseline | Experiment | Reverted (final) |
|---|---|---|---|
| performance | 0.96 (high) / 0.91 (low) | 0.91 | 0.92 (jittered 0.91–0.96 across runs) |
| FCP | 1.7 s | 1.7 s | 1.7 s |
| LCP | 2.0 s | 3.4 s | 1.9 s |
| CLS | 0.02 | 0.02 | 0.02 |

The experiment **pushed LCP from 2.0 s to 3.4 s** on `/countries/`.
Root cause: the LCP element on that page is a text paragraph
(`<p class="mt-5 text-lg text-ink-800 leading-relaxed
max-w-3xl">`). With site.css render-blocking, the page paints
all-at-once and LCP fires at the paint. With site.css async, the
page paints at FCP (1.7 s) with system-fallback font; then Inter
arrives (`font-display: swap` triggers the swap); Chrome marks
LCP at the post-swap repaint (~3.4 s) because that is when the
LCP element's *final* size and font stabilise.

Adding the missing utility classes to critical CSS (`mt-5`,
`max-w-3xl`, `text-ink-800`, `text-lg`, `leading-relaxed`) did
NOT fix this — the regression is owned by the font-swap timing,
not by missing layout rules.

Preloading site.css alongside the JS loader did not fix it
either: even with site.css fully cached at FCP, the font-swap
LCP timing is unchanged.

### `/` (LTR home), `/contact/`, `/wizard/`, `/privacy/`, `/disclaimer/`, `/case-types/`

Net change with the experiment vs baseline: within ±0.01 each
(jitter band). No clear gain, no clear regression.

## 4. Why it was reverted

| Signal | Read |
|---|---|
| `/ar/` perf gain | +0.02 confirmed (stable across 3 runs). |
| `/countries/` perf | Within jitter of baseline on one set of runs; clearly regressed on another. Inconsistent. |
| LCP regression mechanism on `/countries/` | Real and documented (font-swap timing on a text LCP element). |
| Net effect across 8 URLs | Marginal — between -0.01 and +0.01 weighted mean depending on which jitter-band reading is used. |
| Architectural cost | Two new files (`_critical_css.html`, `css-loader.js`), an extra `<script>` + `<noscript>` block, a +5 KiB inline `<style>` payload per response. |
| Risk profile | A real LCP regression that the existing CI gate (`/ar/ ≥ 0.75`) does not catch but a strict-prod CDN could amplify. |

The change buys ~+0.02 on one URL while moving a measurable
regression onto another. Per the iter's mini-plan contract ("if
async CSS is too risky for layout, fall back to the conservative
solution"), the choice is to revert.

## 5. Files NOT shipped

The trial added these files; they have been **removed before
commit**:

- `templates/partials/_critical_css.html` (deleted)
- `static/js/css-loader.js` (deleted)
- the corresponding `<include>`, `<script>`, `<preload>`,
  `<noscript>` lines in `templates/base.html` (reverted)

The only ship-worthy artefact is **this report** and a small
in-file documentation block in `base.html` pointing future
developers at this report. The pre-existing inline critical-CSS
block (P2-PERF-1) is preserved exactly as it was.

## 6. What would unlock the target

The bottleneck identified by the experiment is the **font-swap
LCP timing on text-LCP pages**. To genuinely move `/ar/` to
≥ 0.85, one of the following must change:

1. **Tighter font-display strategy on the Latin body font**: e.g.
   `font-display: optional` on Inter + Cormorant Garamond. Cost:
   on slow connections the user permanently sees the system
   fallback. Premium-typography trade-off — requires Studio
   sign-off.
2. **Self-host a smaller Inter subset** that fits in a single
   HTTP packet (~14 KiB). Today's `inter-400-latin.woff2` is
   ~18 KiB; a stripped Latin-1 subset is feasible. Would let the
   preload land before FCP on most connections.
3. **Critical-CSS + async + pre-CSS font preconnect/preload of
   the entire above-the-fold font set**, all wired so the font
   load completes before LCP measurement settles. Significant
   work, depends on (2).
4. **Move the LCP element on text-heavy pages above the fold
   such that it is always image-based** — out of scope for a
   perf iter; this is a content/design call.

None of these are perf-safe-by-default. The right path forward is
a P2-PERF-3 iter that picks ONE of the above with explicit
sign-off on the trade.

## 7. What this iter contributes

- **A documented negative finding** (this file) with reproducible
  measurements, root-cause analysis, and a list of follow-up
  paths.
- **An in-tree note in `base.html`** pointing the next maintainer
  at this report.
- **Tests pinning the post-revert state of `base.html`** so a
  drive-by edit doesn't re-introduce the change without an
  explicit iter.

## 8. Verifications run

| Command | Result |
|---|---|
| `python manage.py check` | clean (only the expected `core.W001` STUDIO_* dev warning) |
| `pytest -q` | full suite green (numbers in commit message) |
| `bash scripts/run_lighthouse_local.sh` | desktop all ≥ 0.99 perf |
| `bash scripts/run_lighthouse_mobile_local.sh` × 3 | mobile floors preserved; no URL below 0.82 |
| `bash scripts/run_quality_gate.sh --no-pytest` | ALL GATES CLEARED |
| `git status` | clean |

## 9. CSP audit

The CSP file (`config/settings.py`) was **not modified** by this
iter. Verified by the smoke tests:

- `script-src 'self' 'nonce-…'` — unchanged.
- `style-src 'self' 'nonce-…'` — unchanged.
- No `'unsafe-inline'` / `'unsafe-eval'` was introduced.
