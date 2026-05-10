# P0-LEG-1/6 — versioned privacy and disclaimer legal pages

**Date**: 2026-05-10
**Iter**: `F-p0-leg-1-6-legal-pages`
**Branch**: `audit/indennizzati-platform`

## URL choice

The pages already existed under `/privacy/` and `/disclaimer/` (see
`apps/core/urls.py`). 44 files across the codebase (footer, consent
partial, sitemaps, hreflang allowlist, tests) reference these paths
through `{% url 'core:privacy' %}` / `{% url 'core:disclaimer' %}`.

P0-LEG-1/6 keeps these URLs unchanged to avoid a 44-file rename and
the SEO churn it would cause. The Studio can rename to
`/legal/privacy/` later as a single, contained PR (URL rename + name
preservation via `RedirectView` from the old paths).

Multilingual via `i18n_patterns(prefix_default_language=False)`:

- `/privacy/` (it, default — no prefix)
- `/fr/privacy/`, `/en/privacy/`, `/ar/privacy/`
- same matrix for `/disclaimer/`.

## What changed

### Settings (`config/settings.py`)

Six new env-driven fields:

- `PRIVACY_POLICY_VERSION` (default `working-copy-2026-05-10`)
- `PRIVACY_POLICY_STATUS` (default `working_copy`; allowed: `working_copy|signed`)
- `PRIVACY_POLICY_SIGNED_AT` (default `""`; ISO date when signed)
- `DISCLAIMER_VERSION` (default `working-copy-2026-05-10`)
- `DISCLAIMER_STATUS` (default `working_copy`)
- `DISCLAIMER_SIGNED_AT` (default `""`)

Distinct from `PRIVACY_NOTICE_VERSION` /
`SPECIAL_CATEGORIES_NOTICE_VERSION` (P0-LEG-3) which version the
**consent text** shown on every form. The two pairs are independent
on purpose: the privacy *policy page* and the consent *checkbox text*
can be revised on different schedules.

### Context processor (`apps/core/context_processors.py`)

`site_context` now exposes `PRIVACY_POLICY_*` and `DISCLAIMER_*` to
every template, alongside the existing `STUDIO_*` and consent
versions.

### Pages

- `templates/public/privacy.html` — full structured privacy policy
  with 9 sections (data controller, what we collect, special
  categories art. 9, legal bases, retention, your rights, sharing,
  consent versions, contact). Working-copy banner + version footer.
  All wording marked working copy until the Studio signs.
- `templates/public/disclaimer.html` — 9 sections covering all the
  points required by the iter spec: informational nature; no
  automated legal advice; no guarantee of outcome; indicative ranges
  only; sources and limits of the tables; engagement only by written
  agreement; professional independence; data and confidentiality;
  international handling.

### New partial

`templates/partials/legal_page_status.html` — renders the
`status="working_copy"` (amber) or `status="signed"` (emerald)
banner. Reusable for any future versioned legal page (e.g. a future
"Conditions of use" page).

### System checks

- `core.E006` — `check_privacy_policy_signed_in_production`. In
  `DEBUG=False`, fails when `PRIVACY_POLICY_VERSION` is empty,
  contains `working-copy` / `draft`, or when `PRIVACY_POLICY_STATUS`
  is not `signed`, or when `PRIVACY_POLICY_SIGNED_AT` is empty
  while `STATUS=signed`.
- `core.E007` — same logic for the disclaimer
  (`DISCLAIMER_VERSION` / `DISCLAIMER_STATUS` / `DISCLAIMER_SIGNED_AT`).

Both share an internal `_check_legal_page_signed` helper to keep the
behavior aligned.

### Footer + consent partial

Already linked to the canonical URLs via `{% url 'core:privacy' %}` /
`{% url 'core:disclaimer' %}` — no rewire needed. Verified at runtime
via Playwright that `[data-consent-block] a` resolves to
`http://.../privacy/` and `http://.../disclaimer/`.

### SEO

Privacy and disclaimer were already in the global hreflang allowlist
(`apps/core/context_processors.py::_GLOBAL_HREFLANG_VIEW_NAMES`), so
they emit `<link rel="alternate" hreflang="...">` for IT/FR/EN/AR
out of the box. They also remain `index, follow` (no `noindex`
meta added). The sitemap continues to surface them under the existing
`StaticPagesSitemap`.

## Tests (`apps/core/test_legal_pages_versioned.py`)

24 tests, all green:

- 4× privacy page returns 200 in IT/FR/EN/AR;
- 4× disclaimer page returns 200 in IT/FR/EN/AR;
- footer links to `/privacy/` and `/disclaimer/`;
- contact consent block links to `/privacy/` and `/disclaimer/`;
- working-copy banner visible on both pages by default in dev;
- `core.E006` matrix: working-copy fails / empty version fails /
  signed-but-no-signed_at fails / signed+signed_at passes;
- `core.E007` matrix: same shape;
- reverse URL: `core:privacy` → `/privacy/`, `core:disclaimer` → `/disclaimer/`;
- CSP header present on privacy and disclaimer (no P0-CODICE-4 regression);
- `hreflang="it|fr|en|ar"` present on both pages (no P0-CODICE-2 regression);
- privacy page in signed mode shows `data-legal-status="signed"` and
  the signed date.

Suite: 1703 passed, 1 skipped (zero regressions, +24 from
P0-LEG-4 baseline).

## Browser live (Playwright)

| # | View | Viewport | File |
|---|------|----------|------|
| 01 | `/privacy/` (it) | desktop 1280 | `01_privacy_desktop_it.png` |
| 02 | `/disclaimer/` (it) | desktop 1280 | `02_disclaimer_desktop_it.png` |
| 03 | `/privacy/` (it) | mobile 390 | `03_privacy_mobile_390_it.png` |
| 04 | `/contact/` (consent links highlighted) | desktop 1280 | `04_contact_with_legal_links_desktop_it.png` |
| 05 | `/wizard/it/road-accident/` | desktop 1280 | `05_wizard_italy_with_legal_links_desktop_it.png` |
| 06 | `/ar/privacy/` (RTL) | desktop 1280 | `06_privacy_desktop_ar_rtl.png` |

`/ar/privacy/` confirms `<html lang="ar" dir="rtl">` and the AR
translations available in the `.po` files render correctly. Sections
that have no AR translation yet fall back to English — same as the
rest of the platform.

## What the Studio still has to sign

Before going to production the Studio must:

1. Review and sign the wording of `/privacy/` (9 sections currently
   working-copy) and `/disclaimer/` (9 sections).
2. Set the env vars:
   - `PRIVACY_POLICY_VERSION=2026-XX-XX-final`
   - `PRIVACY_POLICY_STATUS=signed`
   - `PRIVACY_POLICY_SIGNED_AT=2026-XX-XX`
   - `DISCLAIMER_VERSION=2026-XX-XX-final`
   - `DISCLAIMER_STATUS=signed`
   - `DISCLAIMER_SIGNED_AT=2026-XX-XX`
3. Translate signed-off wording into `it`, `fr`, `en`, `ar` `.po`
   files (the structure is in place; the translations are not).

Until step 2 is done, `manage.py check` in production-like scenarios
(`DEBUG=False`) fails with `core.E006` and `core.E007` — both must be
green before deploy.

## Files touched

**Modified**: `config/settings.py`, `apps/core/checks.py`,
`apps/core/context_processors.py`, `templates/public/privacy.html`,
`templates/public/disclaimer.html`.

**New**: `apps/core/test_legal_pages_versioned.py`,
`templates/partials/legal_page_status.html`,
`docs/screenshots/delta_audit_2026-05-10/after/p0-leg-1-6-legal-pages/` (6 screenshots + this NOTES.md).
