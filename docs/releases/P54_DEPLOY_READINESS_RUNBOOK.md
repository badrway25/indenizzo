# P54 — Staging Deploy Readiness Runbook

_Date: 2026-06-30 · For `product/staging-readiness-p0 @ edbb462` (after PR #22
merge). **This document plans a deploy; it does not perform one.** No command
here was run against any server. Replace every `<placeholder>` before use._

> Cardinal rule unchanged in this release: only IT road / danno biologico /
> medical produce a real figure; no unvalidated engine; no invented amount.

## 0. Release identity
- Base branch: `product/staging-readiness-p0`
- HEAD: `edbb462` (merge commit of PR #22)
- Integrated feature: `feature/p3-public-ux-redesign @ f4ab1e4` (P28→P50)
- Local gates at packaging time: `check` → only `core.W001` (STUDIO_* unset in
  dev); `makemigrations --check` → clean; `compilemessages` → ok.

## A. Pre-deploy verification (on the server, before anything)
```bash
cd /srv/<project>
source <venv>/bin/activate
git fetch origin product/staging-readiness-p0
git checkout product/staging-readiness-p0
git pull --ff-only origin product/staging-readiness-p0
git rev-parse --short HEAD              # expect edbb462 (or later)
python manage.py check                 # under DEBUG=False, W001 becomes an ERROR → STUDIO_* must be set first
python manage.py makemigrations --check --dry-run   # must say "No changes detected"
```

## B. Migration inventory (apply at deploy)
All three are `AlterField` on a `CharField` (`case_type`) — a choices refresh.
**Non-destructive** (no column drop, no data loss; existing values are preserved).

| App | Migration | Operation | Destructive? | Expected impact | Rollback note | Verify |
|-----|-----------|-----------|--------------|-----------------|---------------|--------|
| cases | `0005_alter_simulation_case_type` | AlterField `Simulation.case_type` (choices, max_length=64) | **No** | metadata-only; no row rewrite | reverse migration restores prior choices; data unaffected | `showmigrations cases` |
| compensation | `0007_alter_compensationdataset_case_type` | AlterField `CompensationDataset.case_type` | **No** | metadata-only | reversible | `showmigrations compensation` |
| crm | `0006_alter_lead_case_type` | AlterField `Lead.case_type` | **No** | metadata-only | reversible | `showmigrations crm` |

```bash
python manage.py showmigrations cases compensation crm   # the 3 above show [ ] until migrate
python manage.py migrate                                 # apply (after a DB backup — see §E)
python manage.py showmigrations cases compensation crm   # now all [X]
```

## C. Environment readiness
**Never print secret values.** Confirm only present/absent. Settings:
`config/settings.py` (single module). `DJANGO_DEBUG=False` in staging/prod.

### C.1 Required before go-live (DEBUG=False) — these 7 trigger `core.W001` → ERROR
- `STUDIO_LEAD_LAWYER_NAME`
- `STUDIO_BAR_ASSOCIATION`
- `STUDIO_VAT_NUMBER`
- `STUDIO_PEC_EMAIL`
- `STUDIO_PHYSICAL_ADDRESS`
- `STUDIO_PROFESSIONAL_INSURANCE_INSURER`
- `STUDIO_PROFESSIONAL_INSURANCE_POLICY`
- (optional companions: `STUDIO_BAR_REGISTRATION_NUMBER`, `STUDIO_TAX_CODE`,
  `STUDIO_PROFESSIONAL_INSURANCE_CEILING`)

### C.2 Core Django / security (required for a real deploy)
- `DJANGO_SECRET_KEY` (required) · `DJANGO_DEBUG=False`
- `DJANGO_ALLOWED_HOSTS` · `DJANGO_CSRF_TRUSTED_ORIGINS`
- `DATABASE_URL` (PostgreSQL in prod/staging)
- `DJANGO_SECURE_SSL_REDIRECT`, `DJANGO_SECURE_HSTS_SECONDS`,
  `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS`, `DJANGO_SECURE_HSTS_PRELOAD`,
  `DJANGO_SECURE_REFERRER_POLICY` · `CSP_REPORT_URI` (optional)
- `SITE_DOMAIN`, `SITE_NAME` · `SENTRY_DSN` (optional) · `REDIS_URL`/`CACHE_URL`/
  `CELERY_RESULT_BACKEND` (only if async/Celery is enabled)

### C.3 Feature flags — decide explicitly
- **OpenAI document AI — keep OFF unless authorised:** leave
  `OPENAI_DOCUMENT_AI_ENABLED` unset/false. (`OPENAI_API_KEY`,
  `OPENAI_DOCUMENT_AI_MODEL`, `OPENAI_DOCUMENT_AI_DEV_MODE` only matter if enabled.)
- **Pexels — env only, never a key in the repo:** `PEXELS_ENABLED`,
  `PEXELS_API_KEY`, `PEXELS_DEFAULT_ORIENTATION`. Used only by offline
  `fetch_pexels_site_images` / `compress_pexels_images`, never at request time.
- Document intake: `DOCUMENT_INTAKE_MAX_FILES`, `DOCUMENT_INTAKE_MAX_UPLOAD_MB`.
- Email/lead: `DJANGO_EMAIL_BACKEND`/`EMAIL_BACKEND`, `LEAD_NOTIFICATION_ENABLED`,
  `LEAD_NOTIFICATION_ASYNC_ENABLED`, `LEAD_NOTIFICATION_TO_EMAILS`.
- CRM webhook: `CRM_WEBHOOK_ENABLED`, `CRM_WEBHOOK_URL`, `CRM_WEBHOOK_SECRET`,
  `CRM_WEBHOOK_PAYLOAD_VERSION`.

Rule: no secret values in this repo or in logs; `STUDIO_*` mandatory pre-go-live;
OpenAI off unless explicitly authorised; Pexels only from env.

## D. Deploy command plan (DO NOT run blindly — placeholders + backup first)
```bash
cd /srv/<project>
source <venv>/bin/activate

git fetch origin product/staging-readiness-p0
git checkout product/staging-readiness-p0
git pull --ff-only origin product/staging-readiness-p0

# ---- backup DB first (see §E) ----
python manage.py check                              # must pass (STUDIO_* set!)
python manage.py makemigrations --check --dry-run   # must be "No changes detected"
python manage.py migrate                            # applies the 3 AlterField migrations
python manage.py compilemessages                    # it/fr/en/ar .mo
python manage.py collectstatic --noinput
python manage.py precompress_static                 # this project HAS this command (apps/core)

systemctl restart <service>                         # only with the real service name
```
Notes: substitute `<project>`/`<venv>`/`<service>`; do not run if env is not
configured; `precompress_static` exists in this project (no fallback needed).

## E. Backup plan (before `migrate`)
```bash
# PostgreSQL logical backup (no password on the command line — use ~/.pgpass or PGPASSWORD env)
pg_dump --no-owner --format=custom --file="/var/backups/<project>_$(date +%F_%H%M).dump" "$DATABASE_NAME"
ls -lh /var/backups/<project>_*.dump        # verify the file is non-trivial in size
```
- Back up media too if locally stored (uploads are stateless here, but Pexels
  WebP under `media/pexels/` can be re-fetched, not restored).
- Keep a tested **restore** path: `pg_restore --clean --no-owner -d <db> <dump>`.
- **Never commit a backup** to the repo.

## F. Static / media plan
- `collectstatic --noinput` then `precompress_static` so WhiteNoise serves fresh
  `.css.gz` / `.js.gz` (CSS + JS changed in this release).
- Verify the static manifest resolves (e.g. `site.css`, `design-system.css`,
  `site.js` are collected + compressed).
- **No external CDN** (self-hosted fonts + CSS/JS).
- **No heavy Pexels media in the repo**: `media/` is gitignored; images are
  reproducible from `config/pexels_image_overrides.json` (pinned photo ids) via
  `fetch_pexels_site_images` + `compress_pexels_images`.
- `media/legal_harvest/` (harvest provenance manifest) is gitignored; no official
  PDFs are committed.

## G. Post-deploy smoke-test plan
### HTTP (expect 200/302, zero 5xx)
`/healthz/` (monitoring, outside i18n) · `/` · `/it/` · `/it/guided/` ·
`/it/documents/` · `/it/sources/` · `/it/documentation/` · `/ar/` · `/ar/guided/`
· `/ar/sources/`.
```bash
for u in /healthz/ / /it/ /it/guided/ /it/documents/ /it/sources/ /it/documentation/ /ar/ /ar/guided/ /ar/sources/; do
  printf "%-22s %s\n" "$u" "$(curl -s -o /dev/null -w '%{http_code}' https://<host>$u)"
done
```
### Browser
home desktop · guided custom select (keyboard + value-sync) · document upload ·
sources search/filter · documentation · result page · mobile 390 · RTL Arabic.
### Checks
expected 200/302, **zero 5xx**, **zero site console errors**, no mobile overflow,
custom select keyboard works, matrix truthful (only IT "estimate available"), **no
amount without a validated estimate**, sources rendered elegantly, the "why no
amount" explanation present, OpenAI OFF unless authorised.

## H. Rollback plan
The 3 migrations are non-destructive `AlterField`, so a DB rollback is **usually
not required**. Order: code first, DB only if a migration misbehaves.
```bash
# code rollback to the previous release commit
git checkout product/staging-readiness-p0
git reset --hard <previous_release_commit>      # e.g. 6a100a0 (pre-merge) — coordinate, do not force-push shared history
python manage.py collectstatic --noinput && python manage.py precompress_static
systemctl restart <service>
# DB rollback ONLY if needed (reverse the 3 migrations):
python manage.py migrate crm 0005
python manage.py migrate compensation 0006
python manage.py migrate cases 0004
```
Post-rollback: re-run §G smoke; confirm zero 5xx.

## I. Release checklist
1. ☐ DB backup completed (§E)  2. ☐ `STUDIO_*` (7) configured  3. ☐ OpenAI flag
decided (off unless authorised)  4. ☐ Pexels env decided  5. ☐ correct branch
pulled (`edbb462`+)  6. ☐ `check` green (DEBUG=False)  7. ☐ `migrate` applied
8. ☐ `compilemessages` ok  9. ☐ `collectstatic` ok  10. ☐ `precompress_static` ok
11. ☐ service restarted  12. ☐ HTTP smoke (no 5xx)  13. ☐ browser smoke
14. ☐ mobile 390  15. ☐ RTL  16. ☐ no 5xx  17. ☐ no console errors
18. ☐ matrix truthful  19. ☐ no unvalidated amounts  20. ☐ final report.
