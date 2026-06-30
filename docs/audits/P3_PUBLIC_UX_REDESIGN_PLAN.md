# P3 — Public UX Redesign — Plan

**Branch:** `feature/p3-public-ux-redesign` (from `product/staging-readiness-p0` @ `6a100a0`).
**Date:** 2026-06-24 · Builds on the P2 design system.

## 1. Visual audit (from P1/P2 browser QA + this pass)

The public pages are already structurally premium (P1: 7.5/10 static) and fully translated. So P3 is **harmonisation + targeted trust UX**, not a from-scratch rewrite (which would break the large i18n/content test suite and risk re-introducing English leaks on FR/AR).

Specific gaps to close:
- **Country availability is not legible** — `/countries/` badges exist but there is no clear "Available / In verification / Source missing" legend; the home country strip shows codes with no status. (P1 #1 UX gap.)
- **Result page does not state its own scope** — users can over-read the indicative range; P1 flagged temporary/personalisation are silently not modelled.
- **CTAs / cards** use bespoke utility soup rather than the P2 `.premium-*` system → inconsistent.
- **Disclaimer** is a long text wall.
- **Mobile nav** is cramped (no hamburger).

## 2. Constraints driving the approach

- **i18n safety:** any NEW copy is `{% translate %}`/`{% blocktranslate %}` and translated in IT/FR/AR/EN, then `compilemessages` — so coverage does not drop and FR/AR gain no English residue. Most changes are **visual class application** (zero new strings).
- **Fail-closed untouched:** no view/engine/dataset change that could let a non-IT country emit an amount; the readiness/`public_status` source of truth is reused, not bypassed.
- **No calc/data/source change**, no EU download, EU stays honestly "source missing", IT real-data caveat surfaced (coverage card), not hidden.

## 3. Scope (P3 deliverables)

1. **Home** — apply `.premium-btn` to hero CTAs and `.premium-card`/eyebrow rhythm to the feature cards; tighten hierarchy. (Visual.)
2. **Countries** — premium country cards + map the 3 status variants to `.premium-badge-success/-warning/-muted`; add a compact **readiness legend** (Available / In verification / Source missing) with a one-line fail-closed explainer. (Visual + small translated copy.)
3. **Result** — a **"Coverage & limits"** premium card stating honestly what the Italian engine models (permanent biological + moral by age/disability + optional fault) and what it does not (temporary disability, personalisation, income) — review recommended; apply `.premium-provenance-card` / `.premium-disclaimer-card` to the existing provenance/disclaimer blocks. (Visual + translated copy; canary untouched.)
4. **Unavailable state** — premium `.premium-unavailable-card` styling on the non-IT status panel; reassure (fail-closed = guarantee), never "technical error". (Visual.)
5. **Disclaimer** — section the wall into `.premium-disclaimer-card`s. (Visual.)
6. **Navbar** — a real mobile hamburger menu (CSP-nonce JS, progressive-enhancement: nav still usable without JS). (Markup + small JS.)
7. **Tests** — P3 smoke (premium markers, readiness legend, coverage card, fail-closed-no-amount, design-system loaded, FR/AR 200).

## 4. Reused P2 components

`.premium-btn*`, `.premium-card*`, `.premium-badge*`, `.premium-provenance-card`, `.premium-disclaimer-card`, `.premium-unavailable-card`, `.premium-stepper`, `.premium-alert`, layout helpers. `site.css` + `design-system.css` unchanged except possibly tiny additive rules for the mobile menu.

## 5. Mobile / RTL risks

Hamburger must be keyboard-accessible + `aria-expanded`; RTL must mirror. Country cards + legend must wrap at 390. New copy must render RTL on AR. Verified in browser at 1440 + 390.

## 6. Rollback

No migration, no Python domain logic, no data. Reverting the branch removes the redesign; the site returns to its current premium-foundation state. New `.po` entries are additive (appended), removable with the revert.
