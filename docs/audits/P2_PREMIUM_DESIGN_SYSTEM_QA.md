# P2 — Premium Design System Foundation — QA report

**Branch:** `feature/p2-premium-design-system-foundation` · **Server:** http://127.0.0.1:8781/ · **Date:** 2026-06-24.

## Delivered
- **`static/css/design-system.css`** — additive foundation: formalised tokens (spacing/radius/soft-shadow/type/control/z-index scales + status colors) reconciled to the existing palette, plus the `.premium-*` component layer (buttons, badges, cards, forms, alerts, modal/toast/popover, **wizard stepper**, layout). Loaded after `site.css`; `site.css` untouched.
- **Reusable wizard stepper** (`partials/_premium_stepper.html`) on wizard start (step 1), Italy wizard (step 2), result (step 3) — the "where am I" affordance P1 flagged as missing. Green-complete / gold-active / disabled states; `aria-current="step"`; RTL-safe.
- **Premium primary buttons** on the wizard and contact submit CTAs (44px touch target, focus glow, full-width on mobile).
- **Premium disclaimer bar** (gold left accent) on the global disclaimer banner.
- **Global form-control enhancement** (gold focus glow + `aria-invalid` error state) — every form benefits, no Python widget change.

## Browser QA
- **Desktop 1440 + mobile 390** across home, `/countries/`, `/wizard/`, `/wizard/it/road-accident/`, `/contact/`, FR/AR case-types, disclaimer, methodology, result.
- **HTTP:** all 200. `design-system.css` served 200.
- **Console:** 0 errors (the 2 warnings are pre-existing font-preload notices on every page, not introduced here). 0 CSP errors.
- **Stepper:** renders correctly with complete/active/disabled states; mobile-wrapped cleanly.
- **Buttons:** premium CTAs render; full-width + good touch target on mobile.
- **Forms:** inputs/selects/textarea styled with gold focus; submit premium.
- **No layout overflow** at 390; RTL (AR) unaffected.
- **Canary unchanged:** 26.268 / 27.353 / 28.439 €. **FR/BE/MA/TN `can_calculate=False`** (verified via readiness.json + a dedicated test).

## Tests
`check` OK · no migration · `compilemessages` OK · po-coverage it 58.8 / fr 49.3 / ar 49.3 · hygiene `--strict` OK · canary `--fail-on-drift` exit 0 · alignment/validator exit 0 · strict IT 0 / strict ALL 1 (EU, unchanged) · CSS-guard `test_frontend_local_css_pass1` still green (site.css contract intact) · 7 new P2 smoke tests · **full suite 2411 passed, 1 skipped** · ruff/black clean.

## Honest premium assessment
- **Improved:** a real, documented, reusable component foundation now exists (was: arbitrary Tailwind values only); the wizard finally shows progress; forms have a premium focus + error affordance; the primary CTAs and disclaimer feel more crafted.
- **Not yet premium (P3):** full page redesigns (home/countries/result hero & layout), an available-vs-coming-soon signal on `/countries/`, loading/skeleton states, a real modal/toast in use, hamburger mobile nav, and applying the badge/card classes across all pages. Plus the non-design P1 items (footer go-live identity, FR/AR i18n leaks, IT real-data audit) remain out of P2 scope.

## Out of scope (untouched)
Calculations, engines, formulas, datasets, source_version, hashes, legal sources, FR/BE/MA/TN activation, EU source, IT canary. No deploy, no `main`, no migration, no `legal_data`.
