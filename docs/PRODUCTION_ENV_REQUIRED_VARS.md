# Production env vars — required variables

**Date**: 2026-05-10
**Status**: P0 closure baseline.

This is the complete matrix of env vars that, if unset or
working-copy, block `python manage.py check` in production-like
scenario (`DJANGO_DEBUG=False`). Setting all of them with signed
values produces "System check identified no issues (0 silenced)".

Verified empirically on 2026-05-10:

```text
$ DJANGO_DEBUG=False python manage.py check    →  17 errors
$ DJANGO_DEBUG=False <all env vars set>        →  0 issues
```

Convention: env vars are read by `config/settings.py` via
`environ.Env`. **Most are read with their literal name, NOT with a
`DJANGO_` prefix**. The only env vars that use the `DJANGO_*`
prefix are the standard Django ones (`DJANGO_DEBUG`,
`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_EMAIL_*`,
`DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_DEFAULT_FROM_EMAIL`).

> Note: `apps/core/checks.py::check_studio_professional_identification`
> emits a hint that mentions `DJANGO_STUDIO_*` — this is a slightly
> misleading hint. The actual env var name read by the settings is
> `STUDIO_*` (no `DJANGO_` prefix). If you set
> `DJANGO_STUDIO_LEAD_LAWYER_NAME` only, the check still fails.

---

## 1. Django core

| Env var | Description | Dev default | Production-expected | Check that fails if missing |
|---|---|---|---|---|
| `DJANGO_DEBUG` | Toggles debug mode | `False` | `False` | n/a (changes behavior) |
| `DJANGO_SECRET_KEY` | Cryptographic secret | insecure dev default | random ≥50 chars, never `django-insecure-*` prefix | `RuntimeError` at startup if `django-insecure-*` in prod |
| `DJANGO_ALLOWED_HOSTS` | CSV of accepted hosts | `127.0.0.1,localhost` | `simulatore.studiolegalebadrane.it` (or chosen domain) | Django default `DisallowedHost` |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | CSV of trusted CSRF origins (HTTPS reverse proxy) | empty | `https://simulatore.studiolegalebadrane.it` | Django CSRF rejects POST behind proxy |
| `DATABASE_URL` | DB connection string | `sqlite:///db.sqlite3` | `postgres://user:pass@host:5432/dbname` | Django DB error |
| `DJANGO_EMAIL_BACKEND` | SMTP / console / locmem | console (dev) | `django.core.mail.backends.smtp.EmailBackend` | Lead notification logs but never delivers |
| `DJANGO_DEFAULT_FROM_EMAIL` | Sender of transactional emails | `no-reply@badrane.local` | `no-reply@studiolegalebadrane.it` | Email sent but rejected by recipient SMTP |

---

## 2. Lead notification (P0-CODICE-1 / `crm.E001`)

| Env var | Description | Dev default | Production-expected | Check that fails |
|---|---|---|---|---|
| `LEAD_NOTIFICATION_ENABLED` | Toggle email-on-new-lead | `True` | `True` | — |
| `LEAD_NOTIFICATION_TO_EMAILS` | CSV of recipients (Studio inboxes) | `[]` | `staff@studiolegalebadrane.it,backup@…` | `crm.E001` if enabled with empty list |

---

## 3. Studio professional identification (P0-CODICE-3 / `core.E001`)

| Env var | Description | Dev default | Production-expected | Check |
|---|---|---|---|---|
| `STUDIO_LEAD_LAWYER_NAME` | Avvocato responsabile | empty | `Avv. Mario Rossi` | `core.E001` |
| `STUDIO_BAR_ASSOCIATION` | Ordine | empty | `Ordine degli Avvocati di Milano` | `core.E001` |
| `STUDIO_BAR_REGISTRATION_NUMBER` | Numero iscrizione (opt) | empty | `12345` | (optional, not in P0 minimum) |
| `STUDIO_VAT_NUMBER` | P.IVA | empty | `IT01234567890` | `core.E001` |
| `STUDIO_TAX_CODE` | C.F. (opt) | empty | `RSSMRA80A01H501Z` | (optional) |
| `STUDIO_PEC_EMAIL` | PEC | empty | `studio.badrane@pec.example.it` | `core.E001` |
| `STUDIO_PHYSICAL_ADDRESS` | Indirizzo fisico | empty | `Via Tale 1, 20100 Milano` | `core.E001` |
| `STUDIO_PROFESSIONAL_INSURANCE_INSURER` | Compagnia RC | empty | `Generali Italia SpA` | `core.E001` |
| `STUDIO_PROFESSIONAL_INSURANCE_POLICY` | N. polizza | empty | `POL-IT-987654` | `core.E001` |
| `STUDIO_PROFESSIONAL_INSURANCE_CEILING` | Massimale (opt) | empty | `€ 5.000.000` | (optional) |

In dev: `core.W001` warning instead of `core.E001` error.

---

## 4. Content-Security-Policy (P0-CODICE-4 / `core.E002` + `core.E003`)

| Env var | Description | Dev default | Production-expected | Check |
|---|---|---|---|---|
| `CSP_ENABLED` | Emit CSP header | `True` | `True` | `core.E002` if `False` in prod |
| `CSP_REPORT_ONLY` | Report-only mode | `False` | `False` (enforcing) | `core.E003` if `True` in prod |
| `CSP_REPORT_URI` | Optional violation reporting endpoint | empty | (optional) | — |
| `CSP_DEFAULT_SRC` | Override default-src list | `[SELF]` | `[SELF]` | — |
| `CSP_SCRIPT_SRC` | Override script-src list (NONCE auto-added) | `[SELF]` | `[SELF]` | — |
| `CSP_STYLE_SRC` | Override style-src (NONCE auto-added) | `[SELF, https://fonts.googleapis.com]` | tighten if Google Fonts hosted locally (P1-LEG-1) | — |
| `CSP_IMG_SRC` | Override img-src | `[SELF, data:, blob:]` | `[SELF, data:, blob:]` | — |
| `CSP_FONT_SRC` | Override font-src | `[SELF, data:, https://fonts.gstatic.com]` | tighten when fonts local | — |
| `CSP_CONNECT_SRC` | Override connect-src | `[SELF]` | `[SELF, https://sentry.io]` if Sentry on | — |
| `CSP_FRAME_ANCESTORS` | Override frame-ancestors | `[NONE]` | `[NONE]` | — |
| `CSP_BASE_URI` | Override base-uri | `[SELF]` | `[SELF]` | — |
| `CSP_FORM_ACTION` | Override form-action | `[SELF]` | `[SELF]` | — |
| `CSP_OBJECT_SRC` | Override object-src | `[NONE]` | `[NONE]` | — |

---

## 5. Consent text versions (P0-LEG-3 / `core.E004`)

| Env var | Description | Dev default | Production-expected | Check |
|---|---|---|---|---|
| `PRIVACY_NOTICE_VERSION` | GDPR art. 6 base consent text version | `working-copy-2026-05-10` | `2026-09-15-final` (signed by Studio) | `core.E004` if empty / `working-copy` / `draft` |
| `SPECIAL_CATEGORIES_NOTICE_VERSION` | GDPR art. 9 explicit consent text version | `working-copy-2026-05-10` | `2026-09-15-final` | `core.E004` |

---

## 6. Retention policy (P0-LEG-4 / `compliance.E001`)

| Env var | Description | Dev default | Production-expected | Check |
|---|---|---|---|---|
| `RETENTION_POLICY_VERSION` | Signed policy version | `working-copy-2026-05-10` | `2026-09-15-final` | `compliance.E001` if `working-copy` / `draft` / empty |
| `RETENTION_ENABLED` | Enable real retention runs | `False` | `True` (after Studio signs) | `compliance.E001` if `True` with `MODE=dry_run` (ambiguous) |
| `RETENTION_MODE` | `dry_run` / `anonymize` / `delete` | `dry_run` | `anonymize` (per-scope) | `compliance.E001` if invalid value |
| `RETENTION_LEAD_DAYS` | Lead retention days | `365` | (Studio decides) | — |
| `RETENTION_SIMULATION_DAYS` | Simulation retention days | `365` | (Studio decides) | — |
| `RETENTION_CONSENT_RECORD_DAYS` | ConsentRecord retention days | `1825` | (Studio decides) | — |
| `RETENTION_AUDIT_LOG_DAYS` | PrivacyAuditEvent retention days | `1825` | (Studio decides) | — |
| `RETENTION_REQUIRE_SIGNED_VERSION` | Require signed version in prod | `True` | `True` | (skip-flag for staging only) |

---

## 7. Privacy policy page (P0-LEG-1 / `core.E006`)

| Env var | Description | Dev default | Production-expected | Check |
|---|---|---|---|---|
| `PRIVACY_POLICY_VERSION` | Signed page version | `working-copy-2026-05-10` | `2026-09-15-final` | `core.E006` |
| `PRIVACY_POLICY_STATUS` | `working_copy` / `signed` | `working_copy` | `signed` | `core.E006` if not `signed` |
| `PRIVACY_POLICY_SIGNED_AT` | ISO date when Studio signed | empty | `2026-09-15` | `core.E006` if status=signed but empty |

---

## 8. Disclaimer page (P0-LEG-6 / `core.E007`)

| Env var | Description | Dev default | Production-expected | Check |
|---|---|---|---|---|
| `DISCLAIMER_VERSION` | Signed page version | `working-copy-2026-05-10` | `2026-09-15-final` | `core.E007` |
| `DISCLAIMER_STATUS` | `working_copy` / `signed` | `working_copy` | `signed` | `core.E007` |
| `DISCLAIMER_SIGNED_AT` | ISO date when signed | empty | `2026-09-15` | `core.E007` if status=signed but empty |

---

## 9. Mandate template (P0-LEG-2 / `core.E008`)

| Env var | Description | Dev default | Production-expected | Check |
|---|---|---|---|---|
| `MANDATE_TEMPLATE_VERSION` | Signed mandate version | `working-copy-2026-05-10` | `2026-09-15-final` | `core.E008` |
| `MANDATE_TEMPLATE_STATUS` | `working_copy` / `signed` / `deprecated` | `working_copy` | `signed` | `core.E008` |
| `MANDATE_TEMPLATE_SIGNED_AT` | ISO date when signed | empty | `2026-09-15` | `core.E008` |
| `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION` | Block lead → case promotion without mandate | `True` | `True` | `core.E008` if `False` |

---

## 10. Other production-relevant settings (not P0 blocking)

| Env var | Description | Dev default | Production-expected |
|---|---|---|---|
| `DJANGO_SECURE_SSL_REDIRECT` | Redirect HTTP→HTTPS | `True` (when `DEBUG=False`) | `True` |
| `DJANGO_SESSION_COOKIE_SECURE` | Secure cookies | `True` (prod) | `True` |
| `DJANGO_CSRF_COOKIE_SECURE` | Secure CSRF cookies | `True` (prod) | `True` |
| `DJANGO_SECURE_HSTS_SECONDS` | HSTS duration | 30 days | 30+ days, increase progressively |
| `DJANGO_SECURE_HSTS_PRELOAD` | HSTS preload | `False` | `True` once stable |
| `PUBLIC_POST_RATE_LIMIT_*` | Rate limit on public POST | enabled, 20/3600s | tune per WAF |
| `SENTRY_DSN` | Sentry monitoring | empty (no-op) | DSN of project |
| `ADMIN_MFA_REQUIRED` | TOTP for admin/staff | `False` | `True` (recommended) |
| `STAFF_LOGIN_ALERT_*` | Brute-force detector for admin | enabled | enabled, tune thresholds |
| `LEAD_NOTIFICATION_ASYNC_ENABLED` | Use Celery for lead emails | `False` | `True` once Celery worker deployed |
| `CELERY_BROKER_URL` | Redis broker | `redis://localhost:6379/0` | Redis instance URL |
| `PEXELS_API_KEY` | Hero images | empty | optional, controlled rollout |

---

## Reference: minimal env file for go-live

```bash
# config/.env.production
# (file is git-ignored; managed via secret store of choice)

# Django core
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<generate via: python -c "import secrets;print(secrets.token_urlsafe(64))">
DJANGO_ALLOWED_HOSTS=simulatore.studiolegalebadrane.it
DJANGO_CSRF_TRUSTED_ORIGINS=https://simulatore.studiolegalebadrane.it
DATABASE_URL=postgres://app:<password>@db.internal:5432/badrane

# Email
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_DEFAULT_FROM_EMAIL=no-reply@studiolegalebadrane.it
EMAIL_HOST=smtp.example.com
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
EMAIL_PORT=587
EMAIL_USE_TLS=True

# Lead notification
LEAD_NOTIFICATION_ENABLED=True
LEAD_NOTIFICATION_TO_EMAILS=staff@studiolegalebadrane.it

# Studio professional identification
STUDIO_LEAD_LAWYER_NAME=<from Studio>
STUDIO_BAR_ASSOCIATION=<from Studio>
STUDIO_VAT_NUMBER=<from Studio>
STUDIO_PEC_EMAIL=<from Studio>
STUDIO_PHYSICAL_ADDRESS=<from Studio>
STUDIO_PROFESSIONAL_INSURANCE_INSURER=<from Studio>
STUDIO_PROFESSIONAL_INSURANCE_POLICY=<from Studio>

# CSP
CSP_ENABLED=True
CSP_REPORT_ONLY=False

# Consent text versions
PRIVACY_NOTICE_VERSION=2026-09-15-final
SPECIAL_CATEGORIES_NOTICE_VERSION=2026-09-15-final

# Retention
RETENTION_POLICY_VERSION=2026-09-15-final
RETENTION_ENABLED=True
RETENTION_MODE=anonymize
RETENTION_LEAD_DAYS=<Studio decides>
RETENTION_SIMULATION_DAYS=<Studio decides>
RETENTION_CONSENT_RECORD_DAYS=<Studio decides>
RETENTION_AUDIT_LOG_DAYS=<Studio decides>
RETENTION_REQUIRE_SIGNED_VERSION=True

# Privacy policy + disclaimer pages
PRIVACY_POLICY_VERSION=2026-09-15-final
PRIVACY_POLICY_STATUS=signed
PRIVACY_POLICY_SIGNED_AT=2026-09-15
DISCLAIMER_VERSION=2026-09-15-final
DISCLAIMER_STATUS=signed
DISCLAIMER_SIGNED_AT=2026-09-15

# Mandate
MANDATE_TEMPLATE_VERSION=2026-09-15-final
MANDATE_TEMPLATE_STATUS=signed
MANDATE_TEMPLATE_SIGNED_AT=2026-09-15
REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True
```

After loading this env, `python manage.py check` must report
**System check identified no issues (0 silenced)** before deploy.
