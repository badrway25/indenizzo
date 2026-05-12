# Wizard mobile UX improvements — 2026-05-12

**Iter**: `PRODUCT-3-wizard-mobile-ux`
**Branch**: `product/wizard-mobile-ux`
**Companion of**: `docs/product/WIZARD_MOBILE_UX_AUDIT_2026-05-12.md` (phase 1 audit).
**Verdict**: shipped — 4 P0 quick-wins from the audit, fully reversible, no model / settings / signed-copy changes.

## 1. What was improved

Four P0 items from the audit, in priority order:

### W0.4 — DRY: shared form-fields partial across IT / FR / BE

**Before**: three country wizard templates (Italy / France / Belgium)
each inlined the **same** 80-line `<fieldset>` block (~240 LOC of
duplicated HTML). Any UX change required editing 3 files in
lockstep.

**After**: a single shared partial
`templates/public/_road_accident_wizard_form_fields.html` renders
the 8 domain fields. The three country templates now `{% include
%}` the partial. Future UX changes touch one file.

### W0.1 — Progressive disclosure

**Before**: 8 domain fields rendered in 3 stacked fieldsets — on
mobile (390 viewport) the form is **5-6 viewport heights tall**
between the page intro and the submit button. Many users
abandoned before reaching submit.

**After**: the 3 calculator-driving fields stay visible
("Essential information" fieldset):

- `accident_date`
- `victim_age`
- `permanent_disability_percentage`

The 5 informational fields collapse under a native
`<details>` block labeled **"Additional details (optional)"**:

- `total_temporary_disability_days`
- `partial_temporary_disability_days`
- `medical_expenses`
- `lost_income`
- `fault_percentage`

The `<details>` block is **default-closed**, opens via click or
keyboard, native HTML — no JS required. The disclosure triangle
rotates 180° when open (CSS `group-open:rotate-180`).

The consents and submit button stay **OUTSIDE** the disclosure —
they cannot be hidden behind the toggle.

### W0.2 — Microcopy reassurance

**Before**: page-level intro says "all fields below are optional"
once, far above the form. By the time the user reaches the form
they've scrolled past it.

**After**: a small reassurance line at the top of the form:

> "Fill in the essential details below to receive a first
> indicative assessment. You can add more details — they help
> the Studio's review but are not required."

And inside the `<details>` block:

> "Add what you know. None of these is required. They give the
> Studio a fuller picture for the manual review and may refine
> the indicative range when applicable."

### W0.3 — Sharpened IT CTA

**Before**: Italian wizard submit said "Run simulation" — generic
and slightly technical-feeling.

**After**: "Calculate indicative estimate" — keeps the
deontological "indicative" guardrail explicit while sharpening
the call to action.

France and Belgium wizards **keep** "Submit for legal review" —
they are review-gated, no number is published, so a "calculate"
verb would mislead.

## 2. Before / after

Screenshots in
`docs/screenshots/delta_audit_2026-05-10/after/product-wizard-mobile-ux/`
(14 PNGs across 4 wizard states × 2 viewports + result + contact).

| State | Before | After |
|---|---|---|
| IT wizard, mobile, by default | 8 fields rendered top-to-bottom | 3 essential fields + closed disclosure toggle |
| IT wizard, mobile, when user clicks toggle | n/a (no toggle) | 3 essential + 5 optional rendered |
| IT wizard, desktop | 8 fields in 3 fieldsets | 3 essential + closed disclosure toggle (still saves vertical space) |
| FR wizard | 8 fields, "Submit for legal review" | 3 essential + closed disclosure toggle, same CTA (review-gated) |
| BE wizard | 8 fields, "Submit for legal review" | same shape as FR |
| AR (RTL) | 8 fields stacked | 3 essential + closed disclosure, RTL layout preserved |
| IT CTA | "Run simulation" | "Calculate indicative estimate" |
| FR / BE CTA | "Submit for legal review" | unchanged (correct for review-gated) |

The result page and contact form are **unchanged** by this iter —
they were already improved by PRODUCT-2.

## 3. Impact expected

- **Shorter form on mobile** by default: roughly halves the
  scroll-length on first paint. Lower bounce on mobile.
- **Lower cognitive load**: 3 fields feel like a triage, not a
  tax return. Users who only know their age + disability % can
  submit immediately.
- **Higher quality of optional data**: users who DO click the
  toggle are showing intent and tend to provide better data than
  users who reluctantly fill 8 fields.
- **DRY across countries**: the three road-accident wizards now
  share one source of truth for form fields. Adding a fourth
  country (or fixing a labeling issue) touches one file.

Calculator output is **unchanged** — the form accepts the same
inputs, the wizard view treats them the same way, the simulation
output schema is identical. Italy still returns the same min/mid/max
for the same inputs.

## 4. Files modified / created

| File | Change |
|---|---|
| `templates/public/_road_accident_wizard_form_fields.html` *(new)* | Shared partial. Renders 3 essential fields + `<details>` collapsible with 5 optional fields. ~120 LOC. |
| `templates/public/wizard_italy_road_accident.html` | Replaced 80 inline lines of fieldsets with `{% include %}` of the partial. CTA changed `Run simulation` → `Calculate indicative estimate`. |
| `templates/public/wizard_france_road_accident.html` | Same `{% include %}` replacement. CTA unchanged (review-gated). |
| `templates/public/wizard_belgium_road_accident.html` | Same. |
| `apps/cases/test_product_3_wizard_mobile_ux.py` *(new)* | 22 tests: audit doc + partial existence, essential fields outside `<details>`, optional fields inside, consents outside, sharpened IT CTA, FR/BE CTA unchanged, banned-promise lint, submit consents-only + submit-all-fields, submit without consents rejected, live rendering checks IT/FR/BE, France review-gated, AR/RTL renders. |
| `scripts/capture_product_3_wizard_mobile_ux.py` *(new)* | Playwright harness: collapsed + expanded states, IT/FR/BE/AR, result + contact linked. |
| `docs/product/WIZARD_MOBILE_UX_AUDIT_2026-05-12.md` *(new)* | Phase 1 audit. |
| `docs/product/WIZARD_MOBILE_UX_IMPROVEMENTS_2026-05-12.md` *(new)* | This file. |
| `docs/screenshots/.../after/product-wizard-mobile-ux/` *(new)* | 14 PNGs. |

No model migration. No view change. No form change. No settings
change. No CSP / robots / consent copy change. No France
activation.

## 5. Tests

| Suite | Before | After |
|---|---|---|
| Full `pytest -q` | 1995 passed, 1 skipped | **2017 passed, 1 skipped** (+22 new) |
| `apps/cases/test_product_3_wizard_mobile_ux.py` | n/a | 22/22 passed |
| `python manage.py check` | clean (only W001 STUDIO_* dev) | unchanged |
| `python scripts/legal_data/audit_non_it_readiness.py` | APPROVED-PARTIAL × 4 | APPROVED-PARTIAL × 4 (France stays review-gated) |
| `python scripts/audit_legal_content_hygiene.py --strict` | no findings | no findings |

One latent test-isolation bug was caught and fixed during the iter
(my AR test was leaking Django's `translation.activate('ar')`
thread-local into subsequent tests). The fix: `translation.deactivate_all()`
in a `finally:` block. Worth noting because if PRODUCT-2's AR
test ever moves up in alphabetical ordering and hits the same
issue, the same fix applies — but PRODUCT-2's test has not
exhibited the leak in this iter.

## 6. Residual risks

| Risk | Severity | Mitigation |
|---|---|---|
| The `<details>` summary icon (▾) may not rotate on browsers that don't support `group-open:` Tailwind variant (very old) | low | Native `<details>` semantics work without the rotation. Function preserved, just visual flair lost. |
| Users who type "advanced details" (e.g. fault %) but don't expand the toggle would not see their typed values on form re-submit (validation errors) | low | If the form re-renders with errors and the user typed something inside `<details>`, browsers preserve the user-typed values in the form fields, and Django re-renders the same template. The `<details>` block stays closed by default — but with values present. There's a small chance the user doesn't realize their hidden input has a validation error. The audit listed this as P1.2 (out of scope). |
| RTL/Arabic users see `<details>` with the LTR triangle on the right; locale-natural would be on the left | low | Default browser rendering for `<details>` in `[dir="rtl"]` flips the disclosure marker automatically in Chrome/Safari. Not all browsers, but the major ones. |
| Translations of the new strings ("Essential information", "Additional details", "Optional") are not yet in the `.po` files | low | Strings are wrapped in `{% translate %}` / `{% blocktranslate %}` — they'll show in English until the `.po` files are updated. The platform's translation team handles this asynchronously. |

## 7. Next improvements

Documented in the audit (phase 1) as P1 / P2; **not implemented**
in this batch:

1. **W1.1** — clarify `fault_percentage` help_text (needs Studio
   review on legal-loaded phrasing).
2. **W1.2** — client-side validation feedback before submit
   (would add JS; cost > benefit today).

The highest-value adjacent product work continues to be:
- **France activation** once Studio signs (`docs/studio/`).
- **STUDIO-2 Belgium readiness pack** to mirror PRODUCT-1 / STUDIO-1
  for Belgium.

## 8. Rollback

A single `git revert` restores the prior wizard layout:

- removes the partial file;
- restores the 80-line inlined fieldsets in IT / FR / BE wizards;
- reverts the IT CTA from "Calculate indicative estimate" back to "Run simulation";
- removes the new test + capture + audit + this report.

No DB rollback needed.
