# Go-live gate checklist

**Date**: 2026-05-10 (P0 closure baseline).
**Use**: run this checklist immediately before deploy. Every box must
be ticked, otherwise stop and fix.

The order matters: items earlier in the list are cheaper to fix and
catch the most common breakage. Skipping a step always costs more
than running it.

---

## 0. Inputs from the Studio

Before you start: confirm the Studio has provided everything in
`docs/STUDIO_SIGNOFF_ACTION_PACK.md`.

- [ ] All 7 mandatory `STUDIO_*` fields received and verified.
- [ ] Privacy policy page wording signed, with version + signed date.
- [ ] Disclaimer page wording signed, with version + signed date.
- [ ] GDPR art. 6 consent text signed (4 languages, with version).
- [ ] GDPR art. 9 consent text signed (4 languages, with version).
- [ ] Retention policy signed (version + days per scope + mode per scope).
- [ ] Mandate template signed (version + signed date + signing process).
- [ ] At least one non-IT country approved (FR/BE/MA/TN review package signed).

If any of these are missing, **stop**: the platform refuses to start
in production.

---

## 1. Code health

- [ ] `git status` is clean on `audit/indennizzati-platform`.
- [ ] All commits pushed to remote.
- [ ] Pull request reviewed (if applicable).
- [ ] No `WIP`, `TODO P0`, `FIXME`, `XXX` markers in changed files.

---

## 2. System checks (production-like)

```bash
DJANGO_DEBUG=False \
DJANGO_SECRET_KEY=<real prod secret> \
DJANGO_ALLOWED_HOSTS=simulatore.studiolegalebadrane.it \
<all env vars from docs/PRODUCTION_ENV_REQUIRED_VARS.md> \
python manage.py check
```

- [ ] `System check identified no issues (0 silenced).`
- [ ] No `core.E001` (STUDIO_* identification).
- [ ] No `core.E002` / `core.E003` (CSP).
- [ ] No `core.E004` (consent versions).
- [ ] No `core.E006` (privacy policy).
- [ ] No `core.E007` (disclaimer).
- [ ] No `core.E008` (mandate).
- [ ] No `compliance.E001` (retention).
- [ ] No `crm.E001` (lead notification).

---

## 3. Test suite

```bash
pytest -q
```

- [ ] `pytest` reports `1720+ passed, 1 skipped` (numbers may grow with
      new tests; the skip is intentional —
      `apps/core/test_frontend_local_css_pass1.py:293`).
- [ ] Working tree still clean after the suite (no
      timestamp drift, no generated artifacts left behind).
- [ ] No test marked `@pytest.mark.skip` newly added without
      justification in PR.

---

## 4. Migrations

```bash
python manage.py makemigrations --check --dry-run
python manage.py migrate --check
```

- [ ] `--check --dry-run` reports "No changes detected" (no
      pending migration files to generate).
- [ ] `--check` reports all migrations applied on the prod DB.
- [ ] Backup of the production DB taken **before** running
      `migrate` if any migration is non-trivial (RENAME, DROP, data
      migration).

---

## 5. Browser live (manual)

Run on the prod-like staging environment, against the real domain
(or a staging subdomain that mirrors production env vars).

### Desktop (1280×900)

- [ ] `/` (home) renders with hero and footer professional ID
      visible (no `[da configurare prima del go-live]` placeholders).
- [ ] `/contact/` renders form with two consent checkboxes (neither
      pre-checked); link to `/privacy/` works; link to `/disclaimer/`
      works.
- [ ] `/wizard/` (start) renders.
- [ ] `/wizard/it/road-accident/` renders, both consents present, and
      a complete simulation produces a result.
- [ ] `/contact/thank-you/` shows the mandate notice block; meta tag
      `noindex, nofollow` present; no banner mentions "working copy".
- [ ] `/wizard/result/<uuid>/` shows the disclaimer + mandate notice;
      meta tag `noindex, nofollow` present.
- [ ] `/privacy/` shows the **signed** badge (emerald), no
      working-copy banner, signed-on date visible.
- [ ] `/disclaimer/` shows the **signed** badge, no working-copy
      banner.
- [ ] Footer renders the 7 mandatory STUDIO_* values (no amber
      placeholders).
- [ ] Footer links to `/privacy/`, `/disclaimer/`, parent
      institutional site work.

### Mobile (390×844)

- [ ] Repeat the home + contact + wizard IT + privacy + disclaimer +
      thank-you set on mobile viewport. Layout doesn't break, hero
      photo still loads if Pexels enabled, footer wraps cleanly.

### Arabic / RTL

- [ ] `/ar/` renders with `<html dir="rtl">`.
- [ ] `/ar/contact/` consent block reads right-to-left. Sections that
      have AR translation render correctly; sections that fall back
      to English are visually consistent.
- [ ] `/ar/privacy/` renders with `dir="rtl"`.

### Browser DevTools — console

- [ ] No CSP violation errors in the console for the homepage,
      contact, wizard, result, privacy, disclaimer.
- [ ] No JavaScript exception in the console on any of the above.
- [ ] No "Mixed content" warning.

---

## 6. SEO regression spot-check

- [ ] `curl https://simulatore.studiolegalebadrane.it/robots.txt`
      returns the production robots policy (Disallow on private
      paths).
- [ ] `curl https://simulatore.studiolegalebadrane.it/sitemap.xml`
      returns 200 and includes the public pages.
- [ ] View-source on `/` shows `<link rel="alternate" hreflang="it">`,
      `hreflang="fr"`, `hreflang="en"`, `hreflang="ar"` and
      `hreflang="x-default"`.
- [ ] View-source on `/wizard/result/<uuid>/` shows
      `<meta name="robots" content="noindex, nofollow">`.
- [ ] View-source on `/contact/thank-you/` shows
      `<meta name="robots" content="noindex, nofollow">`.

---

## 7. Form smoke test (live)

- [ ] Submit `/contact/` with both consents → 302 → thank-you page.
- [ ] DB row in `crm_lead` created with `privacy_consent_given=True`,
      `special_categories_consent_given=True`,
      `mandate_signed=False`,
      `mandate_status="mandate_required"`.
- [ ] Email reaches at least one recipient in
      `LEAD_NOTIFICATION_TO_EMAILS`.
- [ ] DB row in `compliance_consentrecord` created (two rows: one
      for `lead_contact`, one for `special_categories_processing`).
- [ ] DB row in `compliance_privacyauditevent` created with
      `event_type=consent_given`.

---

## 8. Retention smoke test

```bash
python manage.py run_retention_policy
```

- [ ] Command runs successfully in dry-run mode.
- [ ] Output prints `policy_version: 2026-09-15-final` (or whatever
      signed version is set), `mode: dry_run`, candidate counts.
- [ ] DB row in `compliance_retentionrunlog` created with
      `status="success"`, `dry_run=True`.

---

## 9. Backup + monitoring

- [ ] Database backup is configured and the latest backup is recent
      (≤24 hours).
- [ ] Backup restore procedure documented and tested at least once
      against a non-prod environment.
- [ ] Sentry DSN configured, project receives test exception.
- [ ] Monitoring/alerting configured for: 5xx rate, response time
      p95, lead-form submit rate, retention-job success.
- [ ] Logs flow to a centralized aggregator (or are at least
      retained on the host with rotation).
- [ ] Postgres connection pool sized appropriately
      (`DATABASE_URL` includes pool settings, or pgbouncer in front).

---

## 10. Legal review — non-IT country (if activated)

- [ ] At least one of FR/BE/MA/TN review package
      (`docs/legal_sources/<COUNTRY>_LEGAL_REVIEW_PACKAGE.md`) is
      signed by the Studio.
- [ ] The corresponding `LegalSource` rows are `status=approved`.
- [ ] The corresponding `CalculationFormula` is `status=approved`.
- [ ] The corresponding `CompensationDataset` is `status=approved`.
- [ ] The country page `/countries/<slug>/` no longer surfaces
      "this jurisdiction is not yet available" — or, if the Studio
      decided to ship with `unavailable_requires_legal_validation`
      for now, the messaging is intentional and reviewed.

If no non-IT country is signed off: that's fine, but the country
landings must read consistently as "calculator pending validation".

---

## 11. Rollback plan

Document **before** deploy:

- [ ] Where the previous version's tag / commit hash is stored.
- [ ] How to rollback (re-deploy previous artifact / `git revert`).
- [ ] How to rollback DB migrations if needed
      (`python manage.py migrate <app> <previous_migration>`).
- [ ] Communication plan if rollback happens (who tells the Studio,
      who tells users if any).
- [ ] Test the rollback once on staging. If you can't, document why.

---

## 12. After deploy

- [ ] First HTTP 200 from `/` confirmed via curl.
- [ ] First HTTP 200 from `/healthz/` confirmed (used by uptime
      monitor — `/healthz/` is intentionally outside `i18n_patterns`).
- [ ] Manual submit on `/contact/` produces a Lead in DB, sends an
      email to staff.
- [ ] Sentry shows zero new errors for the first 30 minutes.
- [ ] Studio is informed the platform is live and given the URL.

---

## 13. P0 closure tag

Once 12 is green:

```bash
git tag -a v0-public-launch -m "P0 closure — public launch"
git push --tags
```

This freezes the P0 baseline so any later rollback target is
unambiguous.
