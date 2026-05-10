# P0-LEG-3 — explicit double consent (GDPR art. 6 + art. 9)

**Date**: 2026-05-10
**Iter**: `F-p0-leg-3-consent`
**Branch**: `audit/indennizzati-platform`

## What changed

Two separate, mandatory checkboxes on every public form:

1. **Privacy (GDPR art. 6.1.b — pre-contractual)** — base consent to process
   contact data so the Studio can reply.
2. **Special categories (GDPR art. 9.2.a — explicit consent)** — required
   because the platform legitimately receives health, family-event and
   judicial-proceeding data via the wizard / contact message.

Previously the public flows had a single "consent_simulation" checkbox that
implicitly tried to cover both bases. Under GDPR art. 9 that is not
sufficient: art. 9 requires *explicit* consent, separate from the art. 6
base. P0-LEG-3 splits the two so each can be recorded and revoked independently.

## Live verification (Playwright on dev runserver)

| # | View | Viewport | File |
|---|------|----------|------|
| 01 | `/contact/` (it) | desktop 1280 | `01_contact_desktop_it.png` |
| 02 | `/contact/` (it) | mobile 390 | `02_contact_mobile_390_it.png` |
| 03 | `/wizard/it/road-accident/` | desktop 1280 | `03_wizard_italy_desktop_it.png` |
| 04 | `/wizard/ma/inheritance/` | desktop 1280 | `04_wizard_morocco_desktop_it.png` |
| 05 | `/ar/contact/` (RTL) | desktop 1280 | `05_contact_desktop_ar_rtl.png` |

In every view both checkboxes:

- render side by side under a `[data-consent-block]` container,
- start UNCHECKED (no pre-tick),
- carry `required`,
- expose distinct `name="..."` attributes (`privacy_accepted` /
  `special_categories_accepted` on the contact form, `consent_simulation` /
  `special_categories_consent` on the wizard).

Submitting `/contact/` POST with both checkboxes missing produces two
`role="alert"` field errors on the same page, status 200 (no Lead created,
no `ConsentRecord` written).

The Arabic RTL page renders `<html lang="ar" dir="rtl">` with the privacy
line localized in Arabic; the art. 9 line currently still renders in English
because the `.po` AR translation has not been provided yet — this is
expected and tracked under "What the Studio still has to sign" below.

## What the Studio still has to sign

The two settings drive the version field persisted on every `Lead` and
`Simulation`:

- `PRIVACY_NOTICE_VERSION` — currently `working-copy-2026-05-10`
- `SPECIAL_CATEGORIES_NOTICE_VERSION` — currently `working-copy-2026-05-10`

Going to production requires:

1. The Studio signs the **final wording** of:
   - the privacy notice (art. 6 base — link in the checkbox label currently
     points to `/it/legal/privacy/` placeholder),
   - the special-categories notice (art. 9 — health / family-events /
     judicial-proceedings, scoped to the contact-reply purpose),
2. set `PRIVACY_NOTICE_VERSION=2026-XX-XX-final` and
   `SPECIAL_CATEGORIES_NOTICE_VERSION=2026-XX-XX-final` via env vars,
3. translate both lines in the `it`, `fr`, `en`, `ar` `.po` files,
4. deploy.

Until step 2 is done, `manage.py check` in production-like scenarios
(`DEBUG=False`) fails with `core.E004` because any consent persisted with a
`working-copy-*` / `draft-*` version is, in legal terms, consent to a text
that may still change.

The dev server keeps running with the working-copy default so the team can
iterate without crashing the local stack.

## Test coverage (10 + 4 added)

`apps/core/test_consent_double_optin.py` — 14 tests:

- contact form rejected with neither / only-art.6 / only-art.9 consent;
- wizard Italy / Morocco rejected with neither / only-art.6 consent;
- both checkboxes never pre-checked in initial GET;
- versions persisted on `Lead.privacy_consent_version` /
  `Simulation.special_categories_consent_version`;
- `core.E004` system check: empty / `working-copy-*` / `draft-*` / signed
  values, in DEBUG=True (silent) and DEBUG=False (error).

Full suite: `1663 passed, 1 skipped`.

## Files touched

- `config/settings.py` — `PRIVACY_NOTICE_VERSION`, `SPECIAL_CATEGORIES_NOTICE_VERSION`.
- `apps/cases/models.py` + migration `0003_*` — denormalized fields on `Simulation`.
- `apps/crm/models.py` + migration `0002_*` — denormalized fields on `Lead`.
- `apps/cases/forms.py` — special-categories field on Italy / France /
  Belgium road-accident wizard + international inheritance wizard.
- `apps/crm/forms.py` — special-categories field on contact form.
- `templates/partials/consent_checkboxes.html` — reusable consent block.
- `templates/public/contact.html`, `wizard_*_road_accident.html`,
  `_inheritance_wizard_fields.html` — switched to the partial.
- `apps/compliance/services.py::record_double_consent` — atomic helper that
  records the two `ConsentRecord` rows together.
- `apps/cases/services.py::run_simulation` — extended signature to persist
  consent versions.
- `apps/cases/views.py` — refactored 4 wizard views around
  `_run_road_accident_simulation` calling `record_double_consent`.
- `apps/crm/services.py::create_lead_from_form` — uses
  `record_double_consent` and populates denormalized fields.
- `apps/core/checks.py::check_consent_versions_signed_in_production` — `core.E004`.
- `apps/core/context_processors.py` — `consent_versions` exposed to
  templates for the working-copy banner.
