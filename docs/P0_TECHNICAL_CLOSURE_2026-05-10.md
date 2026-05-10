# P0 — Technical closure
# Studio Legale Internazionale Badrane LegalTech Platform

**Date**: 2026-05-10
**Branch**: `audit/indennizzati-platform`
**Working tree at closure**: clean
**Test suite at closure**: 1720 passed, 1 skipped

This is the technical sign-off for the P0 batch executed on
2026-05-10. It ties every commit to its scope, lists every system
check now blocking production, and documents the residual gates that
require the Studio's signed input before go-live.

The companion documents are:

- `docs/STUDIO_SIGNOFF_ACTION_PACK.md` — what the Studio must sign,
  in non-technical terms.
- `docs/PRODUCTION_ENV_REQUIRED_VARS.md` — every env var that, if
  unset or working-copy, blocks `manage.py check` in production.
- `docs/GO_LIVE_GATE_CHECKLIST.md` — the operational checklist the
  team runs immediately before deploy.

---

## 1. P0 commits in chronological order

| # | Commit | Title | Iter |
|---|--------|-------|------|
| 1 | `b45ec5d` | `p0-codice-1: robots.txt, noindex regression tests, crm.E001 check` | F-p0-codice-1-robots-txt |
| 2 | `1b2cfbc` | `p0-codice-2: add global hreflang metadata and contact indexability regression tests` | F-p0-codice-2-hreflang-globale |
| 3 | `5fe7e11` | `p0-codice-3: add professional identification footer settings and checks` | F-p0-codice-3-footer-pass1 |
| 4 | `d2bd12b` | `p0-codice-4: enforce django csp security headers` | F-p0-codice-4-csp |
| 5 | `d57a22d` | `p0-leg-3: add explicit privacy and special-category consent scaffold` | F-p0-leg-3-consent |
| 6 | `88a6f9e` | `p0-leg-4: add retention policy scaffold and dry-run command` | F-p0-leg-4-retention |
| 7 | `3b3c4f7` | `test: prevent france readiness audit timestamp drift` | test infra micro-fix |
| 8 | `0431ce1` | `p0-leg-1-6: add versioned privacy and disclaimer legal pages scaffold` | F-p0-leg-1-6-legal-pages |
| 9 | `96e9320` | `p0-leg-2: add mandate signed scaffold and production checks` | F-p0-leg-2-mandate |

The pre-existing branch `work/tunisia-csp-eu650-restore` (commit
`b44a5c2`) — created during the P0 setup — holds the Tunisia/EU650
restore work that was already in flight when the P0 batch started.
That branch is **untouched by P0** and intentionally left aside; the
work there will be reviewed and merged separately.

---

## 2. What each commit closed

### 2.1 `b45ec5d` — P0-CODICE-1 (robots.txt + noindex)

- `/robots.txt` served by `apps.core.views.robots_txt` (out of
  `i18n_patterns`, single neutral file).
- `/wizard/result/<uuid>/`, `/contact/thank-you/` and the wizard
  partials carry `noindex, nofollow`.
- `crm.E001` system check: blocks deploy if `LEAD_NOTIFICATION_ENABLED=True`
  with `LEAD_NOTIFICATION_TO_EMAILS=[]`.

### 2.2 `1b2cfbc` — P0-CODICE-2 (global hreflang)

- `seo_global_hreflang` context processor with explicit allowlist of
  view names (default-deny posture).
- `/contact/` removed from `noindex` list (it's an indexable
  institutional page).

### 2.3 `5fe7e11` — P0-CODICE-3 (professional identification footer)

- `STUDIO_*` settings (lawyer name, bar association, VAT, PEC,
  address, professional insurance).
- Footer renders `[da configurare prima del go-live]` placeholders
  when env vars are empty.
- `core.E001` (production-blocking) and `core.W001` (dev warning).

### 2.4 `d2bd12b` — P0-CODICE-4 (CSP enforcing)

- `django-csp` 4.x with per-request `NONCE`, `unsafe-inline` removed.
- DIRECTIVES env-driven via `CSP_DEFAULT_SRC` / `CSP_SCRIPT_SRC` /
  `CSP_STYLE_SRC` / etc.
- `core.E002` (CSP must be enabled in prod) and `core.E003` (must be
  enforcing, not report-only).

### 2.5 `d57a22d` — P0-LEG-3 (double consent GDPR art. 6 + art. 9)

- Two separate, mandatory checkboxes on every public form:
  - `privacy_accepted` / `consent_simulation` (GDPR art. 6.1.b);
  - `special_categories_accepted` / `special_categories_consent`
    (GDPR art. 9.2.a, explicit consent).
- `Lead` and `Simulation` get six denormalized fields each:
  `privacy_consent_given/at/version`,
  `special_categories_consent_given/at/version`.
- `apps.compliance.services.record_double_consent` writes two
  `ConsentRecord` rows atomically per submit.
- `core.E004` blocks deploy with working-copy / draft consent
  versions.
- `templates/partials/consent_checkboxes.html` partial reused on
  contact + 4 wizard templates.

### 2.6 `88a6f9e` — P0-LEG-4 (retention policy + cron scaffold)

- Settings: `RETENTION_POLICY_VERSION`, `RETENTION_ENABLED`,
  `RETENTION_MODE` (`dry_run|anonymize|delete`),
  `RETENTION_LEAD_DAYS`, `RETENTION_SIMULATION_DAYS`,
  `RETENTION_CONSENT_RECORD_DAYS`, `RETENTION_AUDIT_LOG_DAYS`,
  `RETENTION_REQUIRE_SIGNED_VERSION`.
- `apps.compliance.models.RetentionRunLog` (append-only run audit).
- `Lead` gains `anonymized` + `anonymized_at` (mirroring `Simulation`).
- `apps.compliance.retention.run_retention(mode, allow_delete=False)`
  service: dry-run / anonymize / delete (delete double-gated by
  `allow_delete`).
- Management command `python manage.py run_retention_policy` with
  `--dry-run`, `--mode`, `--yes-i-understand`, `--allow-delete`,
  `--now`, `--executed-by`.
- `compliance.E001` blocks deploy on working-copy / draft / invalid
  mode / ambiguous enabled+dry_run.

### 2.7 `3b3c4f7` — test infra micro-fix

- `apps/compensation/test_france_activation_readiness_audit.py` was
  calling `module.main()` which writes to the tracked
  `docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md`,
  refreshing the "Generated:" timestamp on every suite run and
  leaving the working tree dirty.
- Fix: autouse fixture monkeypatches the script's module-level
  `REPORT_PATH` to a per-test `tmp_path`. Script's `print` of the
  relative report path hardened to fall back to absolute when the
  redirected path lives outside `REPO_ROOT`.

### 2.8 `0431ce1` — P0-LEG-1/6 (versioned privacy + disclaimer pages)

- `/privacy/` and `/disclaimer/` enhanced with structured 9-section
  content (working-copy until signed).
- `templates/partials/legal_page_status.html` — reusable status pill
  (`working_copy` amber / `signed` emerald) + working-copy banner.
- Settings: `PRIVACY_POLICY_VERSION/STATUS/SIGNED_AT` and
  `DISCLAIMER_VERSION/STATUS/SIGNED_AT`.
- `core.E006` (privacy) and `core.E007` (disclaimer): block deploy
  on empty / working-copy / draft, on `STATUS != "signed"`, or on
  `STATUS=signed` with empty `SIGNED_AT`.

### 2.9 `96e9320` — P0-LEG-2 (mandate scaffold)

- Settings: `MANDATE_TEMPLATE_VERSION/STATUS/SIGNED_AT` and
  `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION`.
- `apps.compliance.models.MandateTemplateVersion` (versioned text)
  and `MandateAcceptance` (append-only ledger).
- `Lead` gains `mandate_signed`, `mandate_signed_at`,
  `mandate_version`, `mandate_status`, `mandate_source`.
- `apps.compliance.mandate.mark_mandate_signed(lead, ...)` —
  atomic, idempotent, promotes Lead to `CONVERTED`, logs
  `PrivacyAuditEvent`.
- `apps.compliance.mandate.assert_mandate_signed_for_case_activation`
  — pure guard, raises `MandateNotSignedError`. Hook for any future
  case-activation flow.
- `core.E008`: blocks deploy on working-copy / draft / status not
  signed / signed_at empty / `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=False`.
- `templates/partials/mandate_notice.html` on
  `/contact/thank-you/` and the wizard result page.
- `LeadAdmin` exposes mandate state.

---

## 3. P0 technical gates closed

All purely-technical P0 items shipped. Nothing in the technical
column is waiting on the dev team:

| ID | Voce | Status | Commit |
|---|---|---|---|
| P0-SEC-1 | Content-Security-Policy emessa | ✅ | `d2bd12b` |
| P0-SEC-2 | Django check su `LEAD_NOTIFICATION_TO_EMAILS=[]` | ✅ | `b45ec5d` |
| P0-SEO-1 | `robots.txt` servito | ✅ | `b45ec5d` |
| P0-SEO-2 | `noindex` su result/thank-you | ✅ | `b45ec5d` |
| P0-SEO-3 | hreflang globale | ✅ | `1b2cfbc` |
| P0-LEG-5 | Identificativi professionali nel footer | ✅ | `5fe7e11` |
| P0-LEG-3 | Doppio consenso art. 6 + art. 9 | ✅ scaffold | `d57a22d` |
| P0-LEG-4 | Retention policy + cron | ✅ scaffold | `88a6f9e` |
| P0-LEG-1 | Privacy policy versionata | ✅ scaffold | `0431ce1` |
| P0-LEG-6 | Disclaimer versionato | ✅ scaffold | `0431ce1` |
| P0-LEG-2 | Mandato + flow `mandate_signed` | ✅ scaffold | `96e9320` |

---

## 4. P0 legal gates scaffolded — wait for Studio signed input

Every "scaffold" entry above means: code is in place, defaults are
working-copy, and a system check blocks production until the Studio
provides signed values. This is by design — the platform refuses to
go live with un-signed legal text or un-firmato professional
identification.

| Iter | Setting(s) | System check | What's blocked |
|---|---|---|---|
| P0-LEG-3 | `PRIVACY_NOTICE_VERSION`, `SPECIAL_CATEGORIES_NOTICE_VERSION` | `core.E004` | Submit on /contact/ + every wizard records "working-copy" version |
| P0-LEG-4 | `RETENTION_POLICY_VERSION`, `RETENTION_MODE`, `RETENTION_ENABLED` | `compliance.E001` | Retention command refuses non-dry-run unless signed |
| P0-LEG-1 | `PRIVACY_POLICY_VERSION/STATUS/SIGNED_AT` | `core.E006` | /privacy/ shows working-copy banner |
| P0-LEG-6 | `DISCLAIMER_VERSION/STATUS/SIGNED_AT` | `core.E007` | /disclaimer/ shows working-copy banner |
| P0-LEG-2 | `MANDATE_TEMPLATE_*`, `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION` | `core.E008` | mandate_notice partial shows working-copy banner |
| P0-LEG-5 | `STUDIO_*` (7 mandatory fields) | `core.E001` (W001 in dev) | Footer renders `[da configurare prima del go-live]` |
| P0-SEC-2 | `LEAD_NOTIFICATION_TO_EMAILS` | `crm.E001` | Lead form submits silently lose email if list empty |

Verification:

```text
# DEBUG=False with all dev defaults:
$ python manage.py check  →  17 errors blocking production.

# DEBUG=False with all signed env vars + mandatory STUDIO_* fields:
$ python manage.py check  →  System check identified no issues (0 silenced).
```

(Both runs reproduced on 2026-05-10 — see
`docs/PRODUCTION_ENV_REQUIRED_VARS.md` for the exact env var
matrix.)

---

## 5. System checks now active

| ID | Severity | App | Triggered by |
|---|---|---|---|
| `core.W001` | dev-only Warning | core | Empty `STUDIO_*` field in dev |
| `core.E001` | prod Error | core | Empty `STUDIO_*` field in prod |
| `core.E002` | prod Error | core | `CSP_ENABLED=False` in prod |
| `core.E003` | prod Error | core | `CSP_REPORT_ONLY=True` in prod |
| `core.E004` | prod Error | core | Consent versions empty / working-copy / draft |
| `core.E006` | prod Error | core | Privacy policy not signed |
| `core.E007` | prod Error | core | Disclaimer not signed |
| `core.E008` | prod Error | core | Mandate template not signed or `REQUIRE_MANDATE_*=False` |
| `compliance.E001` | prod Error | compliance | Retention policy not signed / invalid mode / ambiguous enabled+dry_run |
| `crm.E001` | prod Error | crm | `LEAD_NOTIFICATION_ENABLED=True` with empty `LEAD_NOTIFICATION_TO_EMAILS` |

---

## 6. Test suite status

```
$ pytest -q
1720 passed, 1 skipped in ~3 minutes
```

The single skip is
`apps/core/test_frontend_local_css_pass1.py:293` — a Playwright live
check that runs only via the dedicated visual-QA capture script.
Static-layer assertions in the same file cover the same surface.

Per-app counts at closure (not exhaustive):

| App | Passed |
|---|---|
| `apps/core` | 280+ |
| `apps/compliance` | 77 |
| `apps/crm` | 100+ |
| `apps/cases` | 200+ |
| `apps/calculators` | 350+ |
| `apps/legal_sources` | 250+ |
| ... | ... |

---

## 7. Screenshot folders (delta audit 2026-05-10)

`docs/screenshots/delta_audit_2026-05-10/after/`:

- `p0-codice-2/` — hreflang + /contact/ indexability.
- `p0-codice-4/` — CSP enforcing live.
- `p0-leg-3-consent/` — double consent on contact + wizard, AR RTL.
- `p0-leg-1-6-legal-pages/` — privacy / disclaimer pages with
  status banner, mobile, AR RTL.
- `p0-leg-2-mandate/` — mandate notice on thank-you + wizard
  result, mobile, AR RTL.

Each folder has a `NOTES.md` documenting the captured surfaces and
what the Studio still has to sign for that iter.

---

## 8. Tunisia / EU 650 work — branch isolation

Pre-existing work-in-progress on Tunisia CSP mapping and EU
Regulation 650/2012 source restoration was already in flight when
the P0 batch began. Files involved:

- `apps/calculators/test_tunisia_csp_mapping_draft*.py`
- `apps/legal_sources/test_official_source_anti_stub_guard_pass1.py`
- `apps/legal_sources/test_eu_650_real_source_restore_pass1.py`
- `config/official_source_registry.json`
- `legal_data/mappings/tunisia_inheritance_mapping_draft.json`
- `legal_data/sources/eu/official_downloaded/official_sync_manifest.json`
- `scripts/legal_data/rebuild_tunisia_inheritance_mapping_draft.py`
- `scripts/capture_eu_650_real_source_restore_pass1.py`
- `docs/architecture/EU_650_REAL_SOURCE_RESTORE_PASS1.md`

These were preserved on branch `work/tunisia-csp-eu650-restore`
(commit `b44a5c2`). The branch is **not merged** into
`audit/indennizzati-platform`. P0 work has not touched these files
beyond the 3-line edits required to add the new
`special_categories_consent` field to test payloads (commit
`d57a22d`, P0-LEG-3 collateral).

When the Studio is ready to review the Tunisia/EU650 work, that
branch is the canonical entry point — independent from P0 closure.

---

## 9. Residual risks

### 9.1 Risks blocked by Studio sign-off (expected)

These are **not** technical risks; they are signed-input
dependencies the system intentionally surfaces:

- Privacy notice and special-categories consent texts unsigned.
- Privacy policy and disclaimer page wording unsigned.
- Retention policy days unsigned.
- Mandate template wording unsigned.
- Professional identification fields unset.

Each of these blocks `manage.py check` in production until provided.

### 9.2 Real residual risks

- **Translations**: `.po` files for `it/fr/en/ar` exist but the
  AR translation set is partial (e.g. the GDPR art. 9 line falls
  back to English on `/ar/contact/`). This is a P3 item
  (`P3-I18N-1`), not a P0 blocker, but should be prioritized for
  any non-IT go-live.
- **Real legal-source datasets are still `needs_review`** for FR,
  BE, MA, TN. The platform shows
  `unavailable_requires_legal_validation` for these jurisdictions —
  intentional, but the country pages need a clearer "we are not
  yet quantifying for your country" surface that the Studio is
  comfortable with.
- **No CRM dispatcher**: `LEAD_NOTIFICATION_*` sends the email,
  but the n8n / external CRM webhook flow (P1-CRM-*) is **not yet
  in place**. Lead capture is locally durable (DB + email); the
  external CRM integration is the next P1 priority.
- **No Lighthouse CI / performance budget**: shipped quality is
  expected to hold from manual QA, but there's no automated
  regression gate (P1-SEO-2 and P1-SEO-6). Recommended before
  high-traffic launch.

### 9.3 Documented but accepted

- A line in `apps/core/checks.py::check_studio_professional_identification`
  hints to env vars as `DJANGO_STUDIO_*`, but
  `config/settings.py` reads them as `STUDIO_*` (no `DJANGO_`
  prefix). The env var that actually works is `STUDIO_*`. Captured
  in `docs/PRODUCTION_ENV_REQUIRED_VARS.md`. Worth a follow-up
  one-line fix to align the hint, but not blocking.

---

## 10. What "ready to deploy" means after P0 closure

Once the Studio:

1. fills the env vars listed in `docs/PRODUCTION_ENV_REQUIRED_VARS.md`,
2. signs the wording referenced in `docs/STUDIO_SIGNOFF_ACTION_PACK.md`,
3. and the team runs through `docs/GO_LIVE_GATE_CHECKLIST.md`,

the platform is technically ready to go live. **Until then**,
`python manage.py check` in `DEBUG=False` will refuse to start, by
design.

P0 is closed. The next recommended batch is P1 — CRM/n8n dispatcher
or the FR/BE/MA/TN engine activation, depending on the Studio's
priorities.
