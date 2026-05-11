# P2-PERF-2 — critical CSS / async stylesheet loading

**Date**: 2026-05-11
**Iter**: F-p2-perf-2-critical-css-performance
**Branch**: p2/critical-css-performance
**Verdict**: experiment NOT shipped.

This directory documents the negative-result iter for P2-PERF-2.
The full reasoning is in
`docs/qa/lighthouse-mobile-baseline/P2_PERF_2_COMPARISON.md`.

## Short version

We tried to remove the render-blocking dependency on `site.css`
to lift `/ar/` mobile perf from 0.82 to ≥ 0.85. The intervention
was CSP-safe (self-hosted nonce-protected JS loader, no inline
event handlers, no `unsafe-inline`). It moved `/ar/` perf
+0.02 (to 0.84, still 0.01 short of the target) but introduced
an LCP regression on `/countries/` from font-swap timing: the
text LCP element re-paints when Inter swaps in after FCP, so
Chrome marks LCP at ~3.4 s instead of at FCP.

The trade did not clear. The change was reverted to the
P2-IMG-1 baseline. The pre-existing inline critical-CSS block
(P2-PERF-1) and font-preload work (P2-PERF-1) remain in place
and are unaffected by this iter.

## What was kept

- This NOTES.md.
- `docs/qa/lighthouse-mobile-baseline/P2_PERF_2_COMPARISON.md` —
  the full negative-result report.
- A static smoke test pinning the post-revert state of
  `base.html` so a future drive-by edit doesn't silently
  re-introduce the experimental change.
- A 12-line documentation comment in `templates/base.html`
  pointing future maintainers at the comparison report.

## What was deleted

- `templates/partials/_critical_css.html` (5 KiB nonce-protected
  `<style>` block with extracted above-the-fold rules).
- `static/js/css-loader.js` (1.7 KiB deferred stylesheet loader).
- The `<include>`, `<script>`, `<preload>`, `<noscript>`
  rewiring in `base.html`.

The files were deleted, not commented out: dead code is more
expensive than a documented absence.

## Path forward

`P2_PERF_2_COMPARISON.md` §6 lists four candidate paths to
unlock `/ar/ ≥ 0.85`. The most likely next iter (P2-PERF-3) is:

1. Self-host a smaller Inter subset that fits in a single HTTP
   packet, OR
2. Trial `font-display: optional` on the Latin body font with
   Studio sign-off on the trade-off.

Either of these would let the font preload complete before FCP
on simulated 3G, which is the actual blocker behind the
font-swap LCP timing.
