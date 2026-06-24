# P2 — Premium Design System Foundation — Plan

**Branch:** `feature/p2-premium-design-system-foundation` (from `product/staging-readiness-p0` @ `c6075c7`).
**Date:** 2026-06-24 · **Scope:** reusable visual foundation + targeted application. NOT a full page redesign (that is P3).

## 1. Existing-design audit (code + browser)

- **CSS:** one hand-written Tailwind-subset, `static/css/site.css` (681 lines) with a `:root` token block (ink/gold/sand/stone palette) + utility classes; `static/css/fonts.css` vendors Cormorant Garamond + Inter (+ Amiri/Tajawal for RTL), subsetted. Loaded in `base.html` (a critical-CSS block + `site.css` link). `.css.gz` are dev artifacts, **not git-tracked**.
- **Templates:** consistent utility-class markup; premium palette genuinely applied (P1 rated visual layer 7.5/10). Country status badges already have a centralised ok/gold/neutral variant system (`apps/core/public_status.py`).
- **Guards to respect:** `test_frontend_local_css_pass1` asserts (a) `base.html` links `site.css`, (b) public pages load `site.css` and never the Tailwind CDN, (c) `site.css` still carries specific tokens + utilities. `audit_local_css_coverage.py` is read-only/non-blocking.
- **Weak spots (from P1, confirmed in browser):** no wizard stepper; forms have no inline error/help-state styling (server-side only); disclaimer banner is plain; no documented/named component layer (markup uses arbitrary Tailwind values); mobile nav slightly cramped; FR/AR i18n leaks (out of scope here — copy, not design).

## 2. Strategy (safe, additive)

1. **Keep `site.css` 100% intact** (so the CSS-coverage + token assertions stay green).
2. **Add `static/css/design-system.css`** — the foundation: formalised tokens (reconciled to the *existing* palette for visual harmony, plus genuinely-new semantic colors) + a named `.premium-*` component layer (buttons, badges, cards, forms, alerts, modal, toast, popover, stepper, layout). Purely additive; nothing overrides existing pages unless a `.premium-*` class is explicitly applied.
3. **Link it after `site.css`** in `base.html` (keep the `site.css` link).
4. **Apply to a focused, low-risk, high-visibility subset**, browser-verified: the disclaimer bar (gold accent polish), a reusable wizard **stepper** on the wizard start, and a global premium enhancement of form controls (focus glow + error/`aria-invalid` state) that benefits every form without touching Python widgets.

### Palette decision (honest)

The brief proposes navy `#0B1220` / gold `#B8894D` / ivory `#F7F3EA`. These are within ~2–4% of the values **already in production** (`--ink-950 #07172f`, `--gold-500 #b88336`, `--sand-50 #faf6ef`). Introducing a second, slightly-different navy/gold would make applied components clash with the surrounding (unchanged) pages. **Decision:** map the design-system tokens to the existing palette for harmony, and add the genuinely-new semantic colors the project lacks (muted teal `#2F6F73`, success green `#2F7D5C`, warning amber `#B7791F`, error burgundy `#8A1F2D`, slate `#64748B`, soft border). P3 (full redesign) can revisit the base hues holistically if desired.

## 3. Tokens delivered

Spacing scale, radius scale, soft layered shadow scale, type scale, button heights, card padding, focus ring, modal/dropdown/toast z-index, status colors, mobile touch-target min — all as CSS variables under a `:root` extension in `design-system.css`.

## 4. Components delivered

`.premium-btn` (+ `-primary/-secondary/-ghost/-gold/-danger/-sm/-lg`), `.premium-badge` (+ `-success/-warning/-danger/-muted`, `.country-status-badge`, `.calc-readiness-badge`), `.premium-card` (+ `-header/-body/-metric/-provenance/-disclaimer/-unavailable`), `.premium-form/-input/-select/-textarea/-field-error/-help-text/-form-section`, `.premium-alert` (+ `-info/-warning`), `.premium-modal`, `.premium-toast`, `.premium-popover`, `.premium-stepper` (+ `-step/-active/-complete/-disabled`), layout (`.premium-section/-container/-grid/-page-header/-hero-mini/-footer/-navbar`).

## 5. Accessibility

AA contrast on all status colors over their backgrounds; a visible 2px gold focus ring on every interactive component; hover never color-only (also shadow/transform); a clear `:disabled` state; readable `.premium-field-error` with an icon affordance; ≥44px touch targets on `.premium-btn`; RTL-safe (logical properties / mirrored where needed).

## 6. Out of scope (kept untouched)

Calculations, engines, formulas, datasets, source_version, hashes, legal sources, FR/BE/MA/TN activation, the IT canary, the EU source. No deploy, no `main`, no `legal_data`. The IT real-data risk from P1 is **not** masked — it is unrelated to P2.

## 7. Rollback

No migration, no Python, no data. `design-system.css` is a new additive file + a handful of additive template class/markup additions. Reverting the branch fully removes the layer; the site returns to its current (already-premium) state with zero residue.
