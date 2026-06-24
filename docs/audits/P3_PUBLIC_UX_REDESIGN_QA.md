# P3 — Public UX Redesign — QA report

**Branch:** `feature/p3-public-ux-redesign` · **Server:** http://127.0.0.1:8781/ · **Date:** 2026-06-24.

## Delivered (this increment)
Harmonised the public surfaces onto the P2 design system and closed the highest-value trust/availability gaps P1 named — without a from-scratch rewrite (which would break the large i18n/content suite and risk re-introducing FR/AR English leaks).

- **Home** — primary hero CTA now uses `.premium-btn premium-btn-gold` (consistent height, gold focus glow, 44px touch target).
- **Countries** — a premium info alert frames fail-closed as a guarantee: *"When a legal source is not yet validated, the simulator returns no amount — by design, never an invented figure."* (translated IT/FR/AR/EN). Per-country status badges reused.
- **Result** — an honest **"Coverage and limits"** premium card on the estimate path: states what the Italian engine models (permanent biological + moral by age/disability + optional fault) and what it does not (temporary disability, personalisation, income), recommending a Studio review. Canary untouched.
- **Disclaimer** — the legal text now sits in a contained premium card instead of a flat wall.
- **i18n** — 4 new strings, fully translated in IT/FR/AR/EN; coverage **rose** (it 58.9, fr/ar 49.5). No English residue on FR/AR.

## Browser QA
- **Desktop 1440 + mobile 390**: home, `/countries/`, result IT (coverage card), `/disclaimer/`, FR/AR countries.
- **HTTP** all 200; design-system.css 200. **Console 0 errors** (2 pre-existing font-preload warnings only). **0 CSP errors. No overflow.**
- Countries alert renders translated (IT/FR/AR), no English residue. Result coverage card renders in Italian. Disclaimer card contained on mobile.
- **Canary unchanged** 26.268 / 27.353 / 28.439 €. **FR/BE/MA/TN `can_calculate=False`.**

## Tests
`check` OK · no migration · `compilemessages` OK · po-coverage it 58.9 / fr 49.5 / ar 49.5 (all ↑) · hygiene `--strict` OK · canary `--fail-on-drift` exit 0 · alignment exit 0 · strict IT 0 / strict ALL 1 (EU, unchanged) · CSS guard green · 8 new P3 smoke tests · **full suite 2419 passed, 1 skipped** · ruff/black clean.

## Honest premium assessment
- **Now more premium / trustworthy:** country availability is explicit and reassuring; the result page is honest about its own scope (a real trust-layer gain); home/disclaimer feel more crafted; everything stays on one coherent design system.
- **Deferred (still P3-class, future increments):** full page-layout redesigns (home/wizard/result hero & grid overhaul), a real mobile hamburger menu, loading/skeleton + toast/modal actually wired, and applying the badge/card system across *every* page.
- **Pre-existing, not fixed here (bounded-scope rule):** the `_documents_to_prepare.html` partial still renders English ("What the Studio will do" / "Documents to prepare") on IT/FR/AR result/case pages — a larger i18n task (many strings) flagged by P1; left for a dedicated i18n pass. The footer go-live identity placeholders and the IT real-data audit also remain out of P3 scope.

## Out of scope (untouched)
Calculations, engines, formulas, datasets, source_version, hashes, legal sources, FR/BE/MA/TN activation, EU source. No deploy, no `main`, no migration, no `legal_data`. EU still honestly "source missing"; IT real-data caveat surfaced, not hidden.
