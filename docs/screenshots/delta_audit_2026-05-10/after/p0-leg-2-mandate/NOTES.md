# P0-LEG-2 — mandate signed scaffold

**Date**: 2026-05-10
**Iter**: `F-p0-leg-2-mandate`
**Branch**: `audit/indennizzati-platform`

## Scope

Technical scaffold only. The professional mandate wording stays
working-copy until the Studio signs. The codebase contributes:

1. an explicit data model for "the lead has been turned into an
   engagement" (denormalized fields on `Lead` + dedicated
   `MandateAcceptance` ledger);
2. a service that records that transition in a single atomic operation;
3. a guard helper that any future "lead → active case" promotion path
   must call (it raises `MandateNotSignedError` until the lead has
   `mandate_signed=True`);
4. a production-blocking system check (`core.E008`);
5. a clear public-side notice on `/contact/thank-you/` and on the
   wizard result page that the preliminary evaluation is **not** an
   engagement.

No public sign-flow is added (no upload form, no e-signature
integration). That belongs to a follow-on iter; this scaffold makes it
safe to add later.

## Existing surface analysis

`git grep`-checked: there is **no** existing `Case` model or
"lead → active case" promotion flow in the codebase today. `Lead.status`
already has `RECEIVED → CONTACTED → QUALIFIED → CONVERTED → REJECTED →
ARCHIVED`, and `CONVERTED` is the closest semantic point at which a
mandate would normally be signed. The scaffold reuses that:

- `mark_mandate_signed` promotes a `Lead` to `LeadStatus.CONVERTED`
  (unless already in a terminal state like `REJECTED` / `ARCHIVED`),
  sets `converted_at = signed_at` if not yet set, and writes the
  `mandate_*` denormalized fields.
- `assert_mandate_signed_for_case_activation(lead)` is the guard the
  future case-activation flow must call.

## What changed

### Settings (`config/settings.py`)

- `MANDATE_TEMPLATE_VERSION` (default `working-copy-2026-05-10`)
- `MANDATE_TEMPLATE_STATUS` (default `working_copy`; allowed: `working_copy|signed|deprecated`)
- `MANDATE_TEMPLATE_SIGNED_AT` (default `""`)
- `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION` (default `True`)

### Models (`apps/compliance/models.py`)

- `MandateTemplateVersion` — versions the template text the Studio
  has adopted. Status enum: `working_copy / signed / deprecated`.
  Optional locale + signed_at + notes.
- `MandateAcceptance` — append-only ledger of every signed mandate.
  FK to `crm.Lead` and `cases.Simulation` (both nullable). Fields:
  `mandate_version`, `accepted`, `signed_at`, `client_name_snapshot`
  (max 160 chars, may be empty for offline signatures), `source`
  (`manual / upload / external_signature / staff`), `locale`,
  `metadata` (JSON for staff notes, ticket IDs, etc.).

### Lead denormalized fields (`apps/crm/models.py`)

Added on `Lead`:

- `mandate_signed` (bool, db_index, default `False`)
- `mandate_signed_at` (datetime, nullable)
- `mandate_version` (char64, blank)
- `mandate_status` (`mandate_required / mandate_sent / mandate_signed
  / mandate_declined`; default `mandate_required`, db_index)
- `mandate_source` (char24, blank)

Decision: **`Simulation` does not get mandate fields.** A simulation is
always pre-contractual; no path elevates a simulation to a case. The
test `test_simulation_has_no_mandate_fields` pins this decision.

### Migrations

- `apps/compliance/migrations/0005_mandatetemplateversion_mandateacceptance.py` — new models.
- `apps/crm/migrations/0004_lead_mandate_signed_lead_mandate_signed_at_and_more.py` — Lead fields.

### Service (`apps/compliance/mandate.py`)

- `mark_mandate_signed(lead, *, version, signed_at, source="staff", ...)`:
  atomic. Idempotent on `(lead, version)`. Updates the denormalized
  fields, creates a `MandateAcceptance` row, promotes the lead status
  to `CONVERTED` if not already terminal, logs a `PrivacyAuditEvent`
  with `metadata.trigger="mandate_signed"`.
- `assert_mandate_signed_for_case_activation(lead)`: pure guard.
  Raises `MandateNotSignedError` unless either
  `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=False` or
  `lead.mandate_signed=True`.

### System check `core.E008`

In `DEBUG=False`, blocks deploy when:

1. `MANDATE_TEMPLATE_VERSION` is empty;
2. version contains `working-copy` / `draft`;
3. `MANDATE_TEMPLATE_STATUS != "signed"`;
4. status is signed but `MANDATE_TEMPLATE_SIGNED_AT` is empty;
5. `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=False` (would let an
   internal flow promote a lead without a signed mandate).

### Templates

- New `templates/partials/mandate_notice.html` — reusable working-copy
  banner: "The preliminary evaluation does not constitute a
  professional engagement. Any engagement requires a separate written
  agreement (mandate) signed by the Studio." Plus an amber line until
  `MANDATE_TEMPLATE_STATUS=signed`.
- `templates/public/contact_thank_you.html` — includes the partial.
- `templates/public/wizard_result.html` — includes the partial right
  after the disclaimer block.

Both pages already had a generic engagement disclaimer; the new
partial is more explicit ("mandate", "separate written agreement") and
exposes the working-copy banner the Studio's signing milestone
will turn off.

### Admin (`apps/crm/admin.py`)

`LeadAdmin`:

- `list_display` gains `mandate_status`, `mandate_signed`;
- `list_filter` gains `mandate_status`, `mandate_signed`;
- new fieldset "Mandate (professional engagement)" exposing
  `mandate_status`, `mandate_signed`, `mandate_signed_at`,
  `mandate_version`, `mandate_source` with a description that
  redirects staff to `apps.compliance.mandate.mark_mandate_signed`.

### Context processor

`apps/core/context_processors.py::site_context` exposes
`MANDATE_TEMPLATE_VERSION`, `MANDATE_TEMPLATE_STATUS`,
`MANDATE_TEMPLATE_SIGNED_AT` to every template.

## Tests (`apps/compliance/test_mandate_scaffold.py`)

17 tests covering:

- defaults on Lead (`mandate_signed=False`, `mandate_status=mandate_required`);
- Simulation has **no** mandate fields (decision pin);
- `mark_mandate_signed` writes denormalized fields and acceptance row;
- idempotent on the same `(lead, version)`;
- promotes Lead to `CONVERTED`, sets `converted_at`;
- does **not** un-archive a terminal lead;
- logs the `PrivacyAuditEvent`;
- guard raises when not signed;
- guard is no-op with `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=False`;
- guard is no-op when lead is signed;
- `core.E008` matrix: working-copy / status-not-signed / require-flag-off / signed-and-flag-on;
- `/contact/thank-you/` renders the mandate notice;
- `/wizard/result/<uuid>/` renders the mandate notice;
- `LeadAdmin` exposes the mandate fields in `list_display` / `list_filter`.

Suite: 1720 passed, 1 skipped (zero regressions, +17 from
P0-LEG-1/6 baseline).

## Browser live (Playwright)

| # | View | Viewport | File |
|---|------|----------|------|
| 01 | `/contact/thank-you/` (it) | desktop 1280 | `01_contact_thank_you_desktop_it.png` |
| 02 | `/wizard/result/<uuid>/` (it) | desktop 1280 | `02_wizard_result_desktop_it.png` |
| 03 | `/contact/thank-you/` (it) | mobile 390 | `03_contact_thank_you_mobile_390_it.png` |
| 04 | `/ar/contact/thank-you/` (RTL) | desktop 1280 | `04_contact_thank_you_desktop_ar_rtl.png` |

All four show the new `[data-mandate-notice="working_copy"]` block
with the working-copy banner. AR confirms `<html dir="rtl">`.

## What the Studio still has to sign

Before the mandate flow can ship enabled in production:

1. Sign the wording of the professional mandate template (currently
   working-copy — this scaffold ships the *delivery mechanism*, not
   the legal text).
2. Set the env vars:
   - `MANDATE_TEMPLATE_VERSION=2026-XX-XX-final`
   - `MANDATE_TEMPLATE_STATUS=signed`
   - `MANDATE_TEMPLATE_SIGNED_AT=2026-XX-XX`
3. Keep `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True` (default). Only
   the Studio should ever flip it (and the system check will warn if
   they do).
4. When a future case-activation flow is added (lead → active case),
   call `assert_mandate_signed_for_case_activation(lead)` at the top
   of the activation function. The test
   `test_guard_raises_when_not_signed` pins the contract.

Until step 2, `manage.py check` in production-like (`DEBUG=False`)
fails with `core.E008` — must be green before deploy.

## Files touched

**Modified**: `config/settings.py`, `apps/compliance/models.py`,
`apps/crm/models.py`, `apps/crm/admin.py`, `apps/core/checks.py`,
`apps/core/context_processors.py`,
`templates/public/contact_thank_you.html`,
`templates/public/wizard_result.html`.

**New**: `apps/compliance/mandate.py`,
`apps/compliance/test_mandate_scaffold.py`,
`apps/compliance/migrations/0005_mandatetemplateversion_mandateacceptance.py`,
`apps/crm/migrations/0004_lead_mandate_signed_lead_mandate_signed_at_and_more.py`,
`templates/partials/mandate_notice.html`,
`docs/screenshots/delta_audit_2026-05-10/after/p0-leg-2-mandate/` (4 screenshots + this NOTES.md).
