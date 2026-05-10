# SECURITY INDEX — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Tipo:** index/cross-link.
**Scopo:** mappa concisa di tutti i controlli di sicurezza
implementati in 10 pass `LOCAL_PRODUCT_HARDENING_*`, checklist
`manage.py check --deploy`, posture CSP, e gap aperti.

> Per dettaglio implementativo di ciascun pass vedi i file linkati
> nella sezione 1. Per audit deontologico/GDPR contenuti vedi
> `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md`.

---

## 1. Cosa è stato già messo in atto (10 pass)

| Pass | Area | Documento canonico |
|---|---|---|
| 1 | **Rate limit POST pubblici** (form contact + wizard) cache-based | `docs/architecture/LOCAL_PRODUCT_HARDENING_PASS1.md` |
| 2 | **Email transazionale lead** allo Studio (privacy-minimized, plaintext, fail-soft) | `LOCAL_PRODUCT_HARDENING_PASS2_EMAIL.md` |
| 3 | **Sentry** error monitoring opt-in con scrubber PII custom | `LOCAL_PRODUCT_HARDENING_PASS3_SENTRY.md` |
| 5 | **MFA admin** opt-in via TOTP (django-otp duck-typed verifier) | `LOCAL_PRODUCT_HARDENING_PASS5_MFA_ADMIN.md` |
| 7 | **Celery async dispatch** lead notification (Redis broker, 3 retry × 60s, fallback sync se broker down) | `LOCAL_PRODUCT_HARDENING_PASS7_CELERY.md` |
| 8 | **Audit log staff access** (login_success / login_failed / logout) con username/UA hashati e IP mascherato | `LOCAL_PRODUCT_HARDENING_PASS8_STAFF_AUDIT.md` |
| 9 | **Brute-force detector** admin login (detection-only, no lockout) → `StaffSecurityAlert` | `LOCAL_PRODUCT_HARDENING_PASS9_STAFF_BRUTE_FORCE.md` |
| 10 | **Retention policy** staff audit (90/180 gg dry-run di default) | `LOCAL_PRODUCT_HARDENING_PASS10_STAFF_AUDIT_RETENTION.md` |

> Pass 4 e Pass 6 non esistono come hardening (numerazione storica
> riservata ad altri iter di prodotto).

Inoltre, controlli sparsi:

- **PII redaction nei log** — `config/logging_filters.RedactPIIFilter`
  (email, telefoni, codici fiscali italiani mascherati prima del
  print);
- **HSTS, SSL redirect, secure cookies** — `config/settings.py:50-69`
  attivi quando `DEBUG=False`;
- **Honeypot anti-bot** sul form contatto — `apps/crm/forms.py:75`
  + drop silenzioso in `views.py:84-88`;
- **CSRF** Django default + `CSRF_TRUSTED_ORIGINS` env-driven;
- **`X-Frame-Options: DENY`**, `SECURE_CONTENT_TYPE_NOSNIFF`,
  `SECURE_REFERRER_POLICY=same-origin`;
- **Guardrail SECRET_KEY** — fail-fast se prefisso `django-insecure-`
  in produzione (`settings.py:65-69`);
- **Append-only audit ledger** — `compliance.PrivacyAuditEvent`,
  `crm.LeadEvent`, `cases.SimulationEvent`, `compliance.StaffAccessEvent`,
  `compliance.StaffSecurityAlert`;
- **`simple-history` + `auditlog`** middleware su modelli
  legal/lead/simulation;
- **Test fixture isolation** legali — pytest non scrive sui PDF
  reali (`docs/architecture/LEGAL_DATA_TEST_FIXTURE_ISOLATION_PASS1.md`).

---

## 2. Mappa controllo → settings

Tutto è env-driven con default sicuri. Mai segreti hardcoded.

| Controllo | Settings (env) | Default |
|---|---|---|
| `DEBUG` | `DJANGO_DEBUG` | `False` |
| Allowed hosts | `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` |
| CSRF trusted origins | `DJANGO_CSRF_TRUSTED_ORIGINS` | `[]` |
| SSL redirect | `DJANGO_SECURE_SSL_REDIRECT` | `True` (prod) |
| Session cookie secure | `DJANGO_SESSION_COOKIE_SECURE` | `True` (prod) |
| CSRF cookie secure | `DJANGO_CSRF_COOKIE_SECURE` | `True` (prod) |
| HSTS seconds | `DJANGO_SECURE_HSTS_SECONDS` | `2592000` (30 gg) |
| HSTS subdomains | `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | `True` |
| HSTS preload | `DJANGO_SECURE_HSTS_PRELOAD` | `False` |
| Referrer policy | `DJANGO_SECURE_REFERRER_POLICY` | `same-origin` |
| Email backend | `DJANGO_EMAIL_BACKEND` | console (dev) / smtp (prod) |
| Lead notification enabled | `LEAD_NOTIFICATION_ENABLED` | `True` |
| Lead notification recipients | `LEAD_NOTIFICATION_TO_EMAILS` | `[]` ⚠ vedi P0-SEC-2 |
| Lead notification async | `LEAD_NOTIFICATION_ASYNC_ENABLED` | `False` |
| Celery broker | `CELERY_BROKER_URL` | `redis://localhost:6379/0` |
| Sentry DSN | `SENTRY_DSN` | `""` (no-op) |
| Sentry PII | `SENTRY_SEND_DEFAULT_PII` | `False` |
| Admin MFA required | `ADMIN_MFA_REQUIRED` | `False` |
| Public POST rate limit enabled | `PUBLIC_POST_RATE_LIMIT_ENABLED` | `True` |
| Public POST rate limit window/max | `*_WINDOW_SECONDS`, `*_MAX_ATTEMPTS` | 3600s / 20 |
| Staff login alerts enabled | `STAFF_LOGIN_ALERTS_ENABLED` | `True` |
| Staff login alert threshold | `STAFF_LOGIN_ALERT_THRESHOLD` | `5` (in 900s) |
| Staff audit retention enabled | `STAFF_AUDIT_RETENTION_ENABLED` | `True` |
| Staff audit retention dry-run | `STAFF_AUDIT_RETENTION_DRY_RUN` | `True` (default sicuro) |
| Pexels enabled | `PEXELS_ENABLED` | `False` |

Default in prod: massima cautela; ogni attivazione esplicita richiede
env var settata e un check dello Studio.

---

## 3. `manage.py check --deploy` — checklist

Eseguire nella pipeline di build prima di ogni deploy:

```bash
DJANGO_DEBUG=false \
DJANGO_SECRET_KEY="<real>" \
DJANGO_ALLOWED_HOSTS="simulatore.studiolegalebadrane.it" \
DJANGO_CSRF_TRUSTED_ORIGINS="https://simulatore.studiolegalebadrane.it" \
LEAD_NOTIFICATION_TO_EMAILS="lead@studiolegalebadrane.local" \
.venv/Scripts/python.exe manage.py check --deploy
```

Risultato atteso: **0 issues**. Eventuali warning attesi:

- `security.W008` (SSL redirect) → coperto;
- `security.W009` (HSTS seconds) → 30 giorni minimi;
- `security.W018` (DEBUG) → coperto;
- `security.W020` (allowed hosts) → coperto;
- `security.W021` (HSTS preload) → opt-in se Studio decide.

Se compaiono altri warning, **bloccare il deploy** finché non
risolti.

---

## 4. Gap di sicurezza aperti

### 4.1 P0-SEC-1: Content-Security-Policy non emessa lato Django

Stato: nessuna `CSP_*` setting né middleware csp in
`config/settings.py`. CSP dipenderebbe dal reverse proxy (nginx /
Caddy) davanti a Django.

Conseguenza: senza CSP, la difesa lato browser contro XSS,
clickjacking, mixed content è zero.

**Azioni alternative:**

A. **Reverse proxy emette CSP** (consigliato per semplicità):
   nginx/Caddy aggiunge in risposta:
   ```
   Content-Security-Policy: default-src 'self';
     script-src 'self' 'unsafe-inline';   ← per Alpine inline init
     style-src 'self' 'unsafe-inline' fonts.googleapis.com;
     font-src 'self' fonts.gstatic.com;
     img-src 'self' data: media.studiolegalebadrane.it;
     connect-src 'self';
     frame-ancestors 'none';
     form-action 'self';
     base-uri 'self';
   ```
   Documentare nel runbook deploy
   (`docs/deploy/STAGING_DEPLOY.md` / `VPS_STAGING_RUNBOOK.md`).

B. **Django emette CSP via middleware**:
   `pip install django-csp`, aggiungere al `MIDDLEWARE`,
   configurare `CSP_DEFAULT_SRC` ecc. Vantaggio: viaggia con il
   codice, no dipendenza da configurazione runtime nginx.

> **Decisione DA VALIDARE STUDIO**: opzione A o B. Raccomandazione:
> B (django-csp) per coerenza con il resto della piattaforma
> (env-driven, code-controlled).

### 4.2 P0-SEC-2: `LEAD_NOTIFICATION_TO_EMAILS=[]` non blocca deploy

Stato: se in prod `LEAD_NOTIFICATION_ENABLED=True` ma
`LEAD_NOTIFICATION_TO_EMAILS=[]`, il deploy parte ma:

- `apps/crm/email_notifications.py:107-108` esce silenziosamente
  con return `False`;
- ogni Lead viene comunque salvato in DB;
- **nessuna email allo Studio**: richiesta utente persa nel
  silenzio finché qualcuno non controlla l'admin.

**Azione**: aggiungere Django **system check** che fa fail di
`manage.py check` se la combinazione è incoerente:

```python
# apps/crm/checks.py (nuovo, da scrivere)
from django.core.checks import Error, register

@register("crm")
def check_lead_notification_recipients(app_configs, **kwargs):
    from django.conf import settings
    errors = []
    enabled = bool(getattr(settings, "LEAD_NOTIFICATION_ENABLED", False))
    recipients = list(getattr(settings, "LEAD_NOTIFICATION_TO_EMAILS", []) or [])
    if enabled and not recipients:
        errors.append(Error(
            "LEAD_NOTIFICATION_ENABLED=True but LEAD_NOTIFICATION_TO_EMAILS is empty.",
            id="crm.E001",
            hint="Set DJANGO_LEAD_NOTIFICATION_TO_EMAILS=lead@…",
        ))
    return errors
```

Importato in `apps/crm/apps.py::ready()`.

### 4.3 P1-SEC-1: Cookie banner solo informativo

Vedi `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 2.7. Oggi
nessun consent manager opt-in granulare; conforme finché non si
attivano analytics/tracking. Vincolo da rivalutare al go-live.

### 4.4 P1-SEC-2: Google Fonts da CDN remoto

Vedi `LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 4. Ospitare
localmente per privacy + perf.

### 4.5 P1-SEC-3: Nessun WAF / CDN davanti

Stato: in dev nessuno; in staging dipende da setup VPS. In prod
serve almeno:

- WAF / proxy con regole OWASP CRS (Cloudflare / Caddy + CrowdSec);
- DDoS protection L3/L4;
- DNS over HTTPS / DNSSEC;
- TLS automation (Caddy / certbot).

Documentato in `docs/deploy/VPS_STAGING_RUNBOOK.md` (parziale). Va
esteso pre-prod.

### 4.6 P2-SEC-1: Test penetration / external pentest

Mai eseguito un pen-test esterno. Pre-go-live:

- pen-test su superficie pubblica (form, wizard, result, contact);
- review credenziali Django superuser (rotation, MFA enforced);
- audit upload se attivato;
- audit webhook se attivato (vedi `docs/CRM_INTEGRATION_PLAN.md`).

### 4.7 P2-SEC-2: Account lockout admin

Pass 9 è detection-only. Va aggiunto **lockout** (rate limit per
username + IP, sblocco automatico dopo cooldown).

### 4.8 P2-SEC-3: 2FA per cliente / lawyer (oltre admin)

`accounts.User` ha `role` (client / lawyer / staff / admin). Oggi
solo admin ha MFA opt-in. Per area cliente futura (P3, vedi
`AUDIT_DELTA_2026-05-10.md` Sez. 4.4), serve 2FA anche per client/
lawyer.

### 4.9 P2-SEC-4: Honeytoken / canary in DB

Aggiungere righe canary in tabelle sensibili (es. `LegalSource` con
status `honeytoken`) che non dovrebbero mai essere accedute da
codice pubblico — alert se vengono lette.

### 4.10 P3-SEC-1: HSTS preload submission

Quando il dominio è stabile in prod e HTTPS funziona da > 1 mese,
inviare a https://hstspreload.org/. Pre-requisito: HSTS attivo,
include-subdomains, preload flag, no HTTP redirect. Vedi
`SECURE_HSTS_PRELOAD=True`.

---

## 5. Privacy data flow (collegato)

Riassunto solo: **vedere** `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md`
per dettaglio.

- ✅ minimizzazione: solo i campi necessari;
- ✅ append-only audit;
- ✅ no PII nei log (RedactPIIFilter);
- ✅ no PII nelle email Studio (privacy-minimized body);
- ✅ no PII inviata a Sentry (scrubber custom);
- ❌ retention cron non attivo (P0-LEG-4);
- ❌ doppio consenso art. 6 + art. 9 GDPR per dati particolari
  non implementato (P0-LEG-3);
- ❌ privacy policy completa firmata mancante (P0-LEG-1);
- 🟡 webhook esterni non implementati: ridurranno il transito
  cross-systems quando attivati (P1-CRM-* nel `CRM_INTEGRATION_PLAN.md`).

---

## 6. Strumenti di sicurezza consigliati nel CI

> Ogni PR deve passare:

| Tool | Scope | Comando |
|---|---|---|
| `pip-audit` | dipendenze Python vulnerabili | `pip-audit -r requirements.txt` |
| `bandit` | static security linter Python | `bandit -r apps/ config/` |
| `safety` | alternativa a pip-audit | `safety check` |
| `ruff` | lint generale (incl. `B` security rules) | `ruff check .` (già in `pyproject.toml`) |
| `semgrep` | pattern matching avanzato (opzionale) | `semgrep --config=p/django` |
| Django `check --deploy` | settings | vedi Sez. 3 |
| `pytest -k security` | test dedicati | per aggiungere |

CI workflow proposto: `bandit` + `pip-audit` + `manage.py check
--deploy` come gate obbligatori; `semgrep` advisory.

---

## 7. Tabella riassuntiva — gap di sicurezza

| ID | Voce | Severità | Owner |
|---|---|---|---|
| P0-SEC-1 | CSP non emessa | P0 | dev |
| P0-SEC-2 | `LEAD_NOTIFICATION_TO_EMAILS=[]` no fail-fast | P0 | dev |
| P1-SEC-1 | Cookie banner non opt-in granulare | P1 (a oggi conforme; gate per future tracking) | Studio + dev |
| P1-SEC-2 | Google Fonts CDN remoto | P1 | dev |
| P1-SEC-3 | WAF/CDN/edge security in prod | P1 | DevOps |
| P2-SEC-1 | Pen-test esterno | P2 | Studio (procurement) |
| P2-SEC-2 | Account lockout admin | P2 | dev |
| P2-SEC-3 | 2FA per ruolo client/lawyer | P2 | dev (post area cliente) |
| P2-SEC-4 | Honeytoken canary in DB | P2 (nice-to-have) | dev |
| P3-SEC-1 | HSTS preload submission | P3 | DevOps (post 1 mese stabile prod) |

---

## 8. Per Claude Code che lavora su sicurezza

- **Mai** loggare body, cookie, header authentication, query
  string.
- **Mai** committare `.env`, segreti, token API.
- Ogni nuova feature che introduce input utente o API esterna
  passa da:
  1. analisi del threat model (input/output, auth, transport);
  2. test che le invariants di sicurezza non regrediscano;
  3. aggiornamento di questo index se aggiunge un controllo o
     un gap.
- Quando si attiva una feature flag in prod, monitorare i log
  Sentry/Privacy-audit la prima settimana.
- `manage.py check --deploy` in pipeline build è obbligatorio.
