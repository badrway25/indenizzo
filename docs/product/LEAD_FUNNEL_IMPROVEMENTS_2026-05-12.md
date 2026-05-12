# Lead funnel improvements — 2026-05-12

**Iter**: `PRODUCT-2-lead-funnel-improvements`
**Branch**: `product/lead-funnel-improvements`
**Companion of**: `docs/product/LEAD_FUNNEL_AUDIT_2026-05-12.md` (phase 1 audit).
**Verdict**: shipped — 4 P0 quick-wins, fully reversible, no model / settings / signed-copy changes.

## 1. What was improved

The audit (phase 1) identified 4 P0 friction points; phase 2 ships
focused fixes for each. P1 / P2 items in the audit are
deliberately **not** addressed — they belong to follow-up iters or
require Studio / policy decisions outside this batch's scope.

### F0.1 + F0.2 — Contact form prefill + linked-simulation banner

**Before**: when the user clicks "Request legal review" on the
result page, the contact form opens with `?sim=<uuid>` set in the
URL. The hidden field `simulation_public_id` is captured, but
`country` and `case_type` start blank — the user has to re-pick
what they just selected in the wizard 30 seconds earlier. There
is also **no visual confirmation** that the form is connected to
their simulation; the hidden field is invisible by definition.

**After**: when `?sim=<uuid>` resolves to a real `Simulation`,
`crm.views.contact` prefills `country` (FK) and `case_type` from
the linked simulation. The contact template renders a small green
banner above the "What happens next" reassurance:

> ✓ Connected to your simulation
> We have prefilled the country and case type from simulation
> `<short-uuid>`. The Studio will read your inputs and the cited
> sources together with your message — no need to retype them
> here.

Failure-soft: malformed UUID (`ValidationError`), unknown UUID
(no row), or any DB hiccup is caught and the form opens blank —
never a 500.

### F0.3 — Thank-you "while you wait" block

**Before**: thank-you page tells the user "3–5 working days for a
written reply" and stops there. The user has no actionable
guidance and many leave the page without preparing the materials
the Studio will need.

**After**: new shared partial
`templates/partials/_documents_to_prepare.html` rendered with
`variant="thank-you"` below the mandate notice:

- "While you wait for our reply"
- 5 generic, country-agnostic items: medical reports, accident
  records, insurance correspondence, proof of economic impact,
  identity + contact.
- Closing line: "You don't need to send everything at once. The
  Studio will ask for what's missing once the case has been
  reviewed."

### F0.4 — Result page document-prep hint

**Before**: result page has excellent next-steps copy but no
"documents to prepare" hint. The user knows what to do (request
review) but not what to bring.

**After**: same partial rendered with `variant="result"` directly
under the existing "Next steps" / "What this means" blocks. Title
is "Documents to prepare — What the Studio will ask for" with a
6th item (witness contacts) included because at the result stage
the case is fresh enough to recover witness info if any.

The partial is rendered **outside** the `{% if has_estimate %}`
guard so it appears on both the calculation-available path and
the review-gated path (e.g. France). The documents the Studio
needs are the same in either case; surfacing them helps users
move forward regardless of whether the calculator was able to
produce a number.

The "Next steps" ordered list on the estimate path was extended
from 3 to 4 items, with a new item 3 ("Gather the documents
listed below…") that points to the new partial.

## 2. Before / after

Screenshots in
`docs/screenshots/delta_audit_2026-05-10/after/product-lead-funnel-improvements/`
(18 PNGs, desktop 1280 + mobile 390 for each step). The directory
captures both the new states (contact-with-sim, thank-you with
the new block, result with the doc-prep partial) and the
unchanged steps (homepage, wizard-IT, AR home, FR review-gated)
so the next visual review has the full funnel snapshot.

| State | Before | After |
|---|---|---|
| Contact form GET, no `?sim` | unchanged | unchanged |
| Contact form GET with valid `?sim=<uuid>` | hidden field set, no UI feedback, `country` / `case_type` empty | green banner above "What happens next", `country` + `case_type` preselected |
| Contact form GET with bad `?sim=` (malformed) | could 500 on `Simulation.objects.filter()` ValidationError | failure-soft, form opens blank, no banner |
| Result page (estimate path) | 3-item "Next steps" | 4-item "Next steps" + "Documents to prepare" block |
| Result page (review-gated path, e.g. France) | no doc-prep block | "Documents to prepare" block appears here too |
| Thank-you page | mandate notice → CTAs | mandate notice → "While you wait for our reply" block → CTAs |

## 3. Impact expected

- Reduced re-entry friction on the contact form (no need to
  reselect country / case type).
- Stronger user perception of continuity ("the platform knows
  what I just did") via the linked-simulation banner.
- Faster case turnaround once the Lead reaches the Studio:
  documents that arrive **with** the first reply (or before it)
  shorten the back-and-forth.
- Better passive UX on thank-you and result pages: users have
  something concrete to do while waiting for the manual reply.

These improvements are UX-side; the underlying Lead pipeline
(double consent, audit ledger, webhook outbox, email
notification) is unchanged.

## 4. Files modified

| File | Change |
|---|---|
| `apps/crm/views.py` | `contact()` now resolves `?sim=<uuid>` to a `Simulation` row (failure-soft against malformed UUID), prefills `initial["country"]` and `initial["case_type"]`, and passes `linked_simulation` in the template context. |
| `templates/public/contact.html` | New `{% if linked_simulation %}` confirmation banner above the existing "What happens next" reassurance block. |
| `templates/public/wizard_result.html` | Added 4th item to the "Next steps" ordered list on the estimate path. Inserted include of `_documents_to_prepare.html` outside the `{% if has_estimate %}` guard so the partial renders on both paths. |
| `templates/public/contact_thank_you.html` | Inserted include of `_documents_to_prepare.html` with `variant="thank-you"` between the mandate notice and the CTAs. |
| `templates/partials/_documents_to_prepare.html` (new) | Shared partial: 5- or 6-item generic, country-agnostic checklist. Two variants (`result`, `thank-you`) for layout matching. |
| `apps/crm/test_product_2_lead_funnel.py` (new) | 11 tests covering audit-doc existence, partial rendering on result + thank-you, banner rendering on contact GET (with/without/malformed sim), failure-soft view, full POST flow with Lead.simulation FK, no-EUR leak on doc-prep block, AR/RTL contact still 200, France still review-gated. |
| `scripts/capture_product_2_lead_funnel.py` (new) | Playwright harness: walks the full funnel (home → wizard → result → contact with `?sim=` → thank-you) plus AR / FR snapshots at desktop 1280 + mobile 390. |
| `docs/product/LEAD_FUNNEL_AUDIT_2026-05-12.md` | Phase 1 audit. |
| `docs/product/LEAD_FUNNEL_IMPROVEMENTS_2026-05-12.md` (this file) | Phase 5 report. |
| `docs/screenshots/.../after/product-lead-funnel-improvements/` | 18 PNGs documenting the post-iter state. |

No model migration. No settings change. No CSP / robots / consent
/ mandate-notice / disclaimer copy change. No France activation.

## 5. Tests

| Suite | Before | After |
|---|---|---|
| Full `pytest -q` | 1984 passed, 1 skipped | **1995 passed, 1 skipped** (+11 new) |
| `apps/crm/test_product_2_lead_funnel.py` | n/a (file did not exist) | 11/11 passed |
| `python manage.py check` | clean (only W001 STUDIO_* dev) | unchanged |
| `python scripts/legal_data/audit_non_it_readiness.py` | APPROVED-PARTIAL × 4 | APPROVED-PARTIAL × 4 (France stays review-gated) |
| `python scripts/audit_legal_content_hygiene.py --strict` | no findings | no findings |

## 6. Residual risks

| Risk | Severity | Mitigation |
|---|---|---|
| Generic doc-prep checklist might miss case-type-specific documents (e.g. inheritance vs road accident) | low | The wording stays at "documents the Studio typically needs". The Studio's manual reply remains the authoritative source for what's needed. The list is informational, not contractual. |
| Linked-simulation banner shows the full public UUID — could be perceived as long | low | The UUID is rendered in a `font-mono text-xs` span; it's compact. Identical UUID is shown at the bottom of the result page (existing behaviour). |
| Prefilling `country` / `case_type` could mask a user's intent to file a different request | low | The fields are preselected, not locked. Users can change them; the form re-submits whatever they choose. The banner copy is explicit ("prefilled from your simulation") so the prefill is not surprising. |
| RTL languages may not render the green banner perfectly | low | `flex-col sm:flex-row` + start-anchored content + Arabic locale tested by `test_contact_renders_rtl_for_arabic_locale`. Screenshots in AR captured. |

## 7. Next improvements

Documented in the audit (phase 1) as P1 / P2; **not implemented**
in this batch because they require either Studio decisions, infra
work, or a deeper UX iter:

1. **Progressive disclosure of optional wizard fields** (P1.1) —
   collapse advanced fields under `<details>` to shorten mobile
   form. Requires UX iter with copy review.
2. **GeoIP-based country preselection on contact form** (P1.4) —
   requires GeoIP infra.
3. **WhatsApp / phone urgent-contact channel** (P2.1) — requires
   Studio decision on supported channels.

And of course, the highest-value adjacent product work remains
**France activation** once Studio signs the 4 documents in
`docs/studio/FRANCE_SIGNOFF_DECISION_FORM.md`. That work doesn't
require any further funnel changes — the funnel is already
review-gated correctly for France today.

## 8. Rollback

Single `git revert` of the PRODUCT-2 commit restores the prior
funnel:

- removes the linked-simulation banner block;
- removes the doc-prep partial includes from result + thank-you;
- removes the new partial file;
- removes the new test file + capture script + this report;
- reverts the view-side prefill logic.

No DB rollback needed (no migration, no fixture, no data change).
