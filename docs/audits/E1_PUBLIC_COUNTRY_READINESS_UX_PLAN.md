# E1 — Public Country Readiness UX — Plan

**Branch:** `feature/e1-public-country-readiness-ux` (from `product/staging-readiness-p0` @ `7d9c495`).
**Date:** 2026-06-23.

> Goal: make the experience for a not-yet-calculation-ready country (FR/BE/MA/TN)
> transparent and professional, and prove it never leaks internal review detail
> — WITHOUT activating any calculation. Public UX / product transparency only,
> no legal-data, no legal-engine, no migration.

## 1. Current state (audit) — the flow already exists and is mature

- **`apps/cases/services.py::run_simulation`** never crashes: with no active
  calculator it persists a `Simulation` with
  `status=unavailable_requires_legal_validation` and no amounts (estimated_*
  = None). Non-crash is an explicit design invariant.
- **`apps/cases/public_result_messages.py`** maps the status to *curated* public
  copy (FR/BE road-accident, MA/TN inheritance, default) — the raw status slug
  never reaches the template.
- **`templates/public/wizard_result.html`** renders the unavailable card: public
  title/summary/explanation, "what happens next", a contact CTA
  (`/contact/?sim=<id>`), `noindex`, **no amounts**.
- **`apps/core/public_status.py`** is the single source of truth for public
  country/case-type copy (4 states: available / legal_assessment /
  inheritance_review / manual_review), with a documented **banned-wording** list
  (scaffold, placeholder, "coming soon", the status slug, …).
- **`/countries/`** + per-country landings already show Italy *available* and
  FR/BE/MA/TN under *legal assessment / review* with badges.
- Existing tests (`test_france_review_gated_e2e_p0_mvp_1`,
  `test_product_1_france_signoff_pack`) lock the France contract: status stays
  unavailable, no EUR, "preliminary/assessment" wording, banned terms forbidden,
  noindex.

**Verified during the audit:** the `/countries*` pages and the FR wizard
unavailable result render with **0 amounts** and **0 forbidden internal tokens**
(no sha256, slug, `review_readiness`/`review_evidence`, `legal_data/`, reviewer,
content_hash, scaffold/placeholder).

## 2. UX gaps addressed by E1

The flow is already correct; E1 adds the missing *consolidation* and *safety
net*:

1. A single public, leak-safe **readiness service** with the E1 schema
   (`public_status` ∈ available / legal_validation_in_progress / not_available,
   `can_calculate`, `public_message`, `recommended_action`,
   `manual_review_available`, and a non-public `internal_reason`).
2. A small public **`/countries/readiness.json`** surface (the transparent
   "public readiness state") and the same data on the `/countries/` context.
3. A **leak-guard test suite** asserting no public surface ever exposes internal
   review detail — the brief's central safety requirement.

## 3. Design — reuse, additive, no schema change

- **No migration.** Availability is derived (registry + `public_status`), not a
  DB field.
- **`apps/core/country_readiness.py`** — pure service on top of
  `get_country_public_status`. `as_public_dict()` omits `internal_reason` and
  renders lazy strings eagerly so no proxy/secret leaks through a serializer.
  Public 3-state: Italy `available`; FR/BE/MA/TN `legal_validation_in_progress`.
- **`core:country_readiness_json`** (`/countries/readiness.json`) — GET-only,
  leak-safe JSON; the `/countries/` view also passes `country_readiness`.
- **No template rewrite.** The existing unavailable card + countries page already
  deliver the transparent UX; E1 does not duplicate them.

## 4. i18n

No new public strings: the readiness copy reuses `public_status` (translated in
C1/C2) and standard country names (already in the catalogs — `Francia` / `France`
/ `فرنسا`). Coverage floors unchanged (it 58.8 / fr 49.3 / ar 49.3).

## 5. Fail-closed / leak safety

- Tested: IT `can_calculate=True` (active registry calculator); FR/BE/MA/TN
  `can_calculate=False`; the FR wizard produces no amount and no
  `status=calculated`.
- Tested: `internal_reason` never appears in the public dict / JSON; the
  `/countries*` pages, `readiness.json` and the FR unavailable result contain
  none of the forbidden internal tokens.
- The IT canary is untouched (no engine/dataset change).

## 6. Rollback

No schema change → reverting the branch removes the service, the route and the
tests; nothing to undo at the DB level.
