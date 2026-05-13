# ENV CONTRACT — GO-LIVE

**Branch:** `product/go-live-readiness-p0`
**Data:** 2026-05-13
**Riferimento canonico:** `docs/PRODUCTION_ENV_REQUIRED_VARS.md`

> Questo documento è la **vista deploy gate** delle variabili d'ambiente.
> Esiste già un documento esaustivo (`PRODUCTION_ENV_REQUIRED_VARS.md`)
> che descrive ogni env var, defaults, check Django collegato e l'env
> minimo. Qui lo **curiamo per il go-live**: per ogni variabile diciamo
> obbligatorietà per ambiente, errore atteso se manca, e come la si verifica
> in 1 comando. Nessun valore reale, nessun segreto.
>
> In caso di conflitto fra i due documenti, **prevale
> `PRODUCTION_ENV_REQUIRED_VARS.md`** (è quello sincronizzato con il
> codice). Quando aggiorni `config/settings.py` aggiorna entrambi.

---

## Filosofia del contract

1. **Defaults dev sicuri**: il codice gira fuori dalla box su SQLite + console email + working-copy legale, e in dev tutto è warning non errore.
2. **Promozione esplicita**: per andare in staging/prod, **ogni variabile P0 deve essere settata esplicitamente** — non ci si affida ai default.
3. **System check bloccanti**: Django `manage.py check` rifiuta lo start in `DEBUG=False` se le condizioni P0 non sono soddisfatte (vedi colonna "Check Django").
4. **Mai segreti nel repo**: `.env*` produzione gestiti via secret store dell'host (Vault, AWS Secrets Manager, Docker secrets, Kubernetes secrets, env del provider).

---

## Tabella contratto

Colonne:
- **Var**: nome variabile letto da `config/settings.py` via `environ.Env`.
- **Dev / Staging / Prod**: `req` (obbligatoria), `opt` (opzionale), `def` (default codice ok).
- **Esempio non sensibile**: forma del valore, mai dati reali.
- **Descrizione**: scopo a frase singola.
- **Errore se manca / errata**: cosa succede in `DEBUG=False`.
- **Check Django**: id del check (`core.E001`, ecc.) che blocca.
- **Verifica**: comando di smoke.

### 1. Django core

| Var | Dev | Stag | Prod | Esempio non sensibile | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `DJANGO_DEBUG` | def | req | req | `False` | Abilita pagine debug; in prod sempre `False` | espone stack trace + dati sensibili | n/a |
| `DJANGO_SECRET_KEY` | def | req | req | output di `python -c "import secrets;print(secrets.token_urlsafe(64))"` | Chiave crittografica sessioni/CSRF | `RuntimeError` allo start se prefisso `django-insecure-` in prod | guard in `settings.py:65-69` |
| `DJANGO_ALLOWED_HOSTS` | def | req | req | `simulatore.studiolegalebadrane.it` (CSV) | Hostnames accettati | `DisallowedHost` 400 | Django built-in |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | def | req | req | `https://simulatore.studiolegalebadrane.it` (CSV) | Origin trusted per CSRF dietro reverse proxy | CSRF refuse 403 su POST | Django built-in |
| `DATABASE_URL` | def | req | req | `postgres://app:****@host:5432/dbname` | Connection string DB | Connection error allo start | Django built-in |
| `LANGUAGE_CODE` | def | def | def | `it` | Lingua default (no prefisso URL) | — | n/a |
| `TIME_ZONE` | def | def | def | `Europe/Brussels` | Timezone server | — | n/a |

### 2. Email transazionale

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `DJANGO_EMAIL_BACKEND` | def | req | req | `django.core.mail.backends.smtp.EmailBackend` | Backend invio email | mail console-only | n/a |
| `DJANGO_DEFAULT_FROM_EMAIL` | def | req | req | `no-reply@<dominio>` | Sender transazionale | mail rifiutate dal recipient | n/a |
| `EMAIL_HOST` | opt | req | req | `smtp.<provider>` | SMTP host | mail non spedite | provider-specific |
| `EMAIL_HOST_USER` | opt | req | req | `apikey` o user provider | Autenticazione SMTP | mail rifiutate | provider |
| `EMAIL_HOST_PASSWORD` | opt | req | req | `***` (segreto) | Password / API key | mail rifiutate | provider |
| `EMAIL_PORT` | opt | req | req | `587` | Porta SMTP | mail rifiutate | provider |
| `EMAIL_USE_TLS` | opt | req | req | `True` | TLS STARTTLS | downgrade attack | provider |

### 3. Lead notification (P0 — `crm.E001`)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `LEAD_NOTIFICATION_ENABLED` | def | req | req | `True` | Master toggle notifica | — | — |
| `LEAD_NOTIFICATION_TO_EMAILS` | def | req | req | `staff@<dominio>,backup@<dominio>` (CSV) | Caselle Studio destinatarie | `crm.E001` blocca `check` | `apps/crm/checks.py` E001 |

### 4. Studio professional identification (P0 — `core.E001`/`W001`)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `STUDIO_LEAD_LAWYER_NAME` | def(W) | req | req | `Avv. <Nome>` | Avvocato responsabile | E001 in prod | `core.E001`/`W001` |
| `STUDIO_BAR_ASSOCIATION` | def(W) | req | req | `Ordine degli Avvocati di <Città>` | Ordine | E001 | E001 |
| `STUDIO_BAR_REGISTRATION_NUMBER` | def | opt | opt | `<numero>` | Numero iscrizione (opt) | warning soft | — |
| `STUDIO_VAT_NUMBER` | def(W) | req | req | `IT<11 cifre>` | P.IVA | E001 | E001 |
| `STUDIO_TAX_CODE` | def | opt | opt | `<16 caratteri>` | C.F. (opt) | warning soft | — |
| `STUDIO_PEC_EMAIL` | def(W) | req | req | `<studio>@pec.<dominio>` | PEC | E001 | E001 |
| `STUDIO_PHYSICAL_ADDRESS` | def(W) | req | req | `Via X 1, 20100 Milano` | Sede | E001 | E001 |
| `STUDIO_PROFESSIONAL_INSURANCE_INSURER` | def(W) | req | req | `<Compagnia>` | Compagnia assic. RC | E001 | E001 |
| `STUDIO_PROFESSIONAL_INSURANCE_POLICY` | def(W) | req | req | `<numero polizza>` | Numero polizza | E001 | E001 |
| `STUDIO_PROFESSIONAL_INSURANCE_CEILING` | def | opt | opt | `<massimale>` | Massimale (opt) | — | — |

`def(W)` = default vuoto, in dev emette warning `core.W001`, in prod diventa errore `core.E001`.

### 5. Content-Security-Policy (P0 — `core.E002`/`E003`)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca / errata | Check |
|---|---|---|---|---|---|---|---|
| `CSP_ENABLED` | def | req | req | `True` | Emette header CSP | `core.E002` se False in prod | `core.E002` |
| `CSP_REPORT_ONLY` | def | req | req | `False` | Modalità report-only | `core.E003` se True in prod | `core.E003` |
| `CSP_REPORT_URI` | def | opt | opt | `https://csp-reports.<dominio>/csp/` | Endpoint reporting | — | — |
| `CSP_*_SRC` overrides | def | opt | opt | `<csv>` | Override direttive | — | — |

### 6. Consent versions (P0 — `core.E004`)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `PRIVACY_NOTICE_VERSION` | def | req | req | `YYYY-MM-DD-final` (post-firma) | Versione testo consenso art. 6 | `core.E004` se `working-copy`/`draft` | `core.E004` |
| `SPECIAL_CATEGORIES_NOTICE_VERSION` | def | req | req | `YYYY-MM-DD-final` | Versione testo consenso art. 9 | `core.E004` | `core.E004` |

### 7. Privacy policy / disclaimer (P0 — `core.E006`/`E007`)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `PRIVACY_POLICY_VERSION` | def | req | req | `YYYY-MM-DD-final` | Versione pagina /privacy/ | `core.E006` | E006 |
| `PRIVACY_POLICY_STATUS` | def | req | req | `signed` | `working_copy` / `signed` | `core.E006` se non `signed` | E006 |
| `PRIVACY_POLICY_SIGNED_AT` | def | req | req | `YYYY-MM-DD` | Data firma | E006 se status=signed ma vuoto | E006 |
| `DISCLAIMER_VERSION` | def | req | req | `YYYY-MM-DD-final` | Versione pagina /disclaimer/ | `core.E007` | E007 |
| `DISCLAIMER_STATUS` | def | req | req | `signed` | working_copy / signed | E007 | E007 |
| `DISCLAIMER_SIGNED_AT` | def | req | req | `YYYY-MM-DD` | Data firma | E007 | E007 |

### 8. Mandato (P0 — `core.E008`)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `MANDATE_TEMPLATE_VERSION` | def | req | req | `YYYY-MM-DD-final` | Versione testo mandato | `core.E008` | E008 |
| `MANDATE_TEMPLATE_STATUS` | def | req | req | `signed` | working_copy / signed / deprecated | E008 | E008 |
| `MANDATE_TEMPLATE_SIGNED_AT` | def | req | req | `YYYY-MM-DD` | Data firma | E008 | E008 |
| `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION` | def | req | req | `True` | Blocca lead → case se no mandato | E008 se False | E008 |

### 9. Retention policy (P0 — `compliance.E001`)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `RETENTION_POLICY_VERSION` | def | req | req | `YYYY-MM-DD-final` | Versione policy | `compliance.E001` | E001 |
| `RETENTION_ENABLED` | def | req | req | `True` | Master toggle cron retention | E001 se incongruente | E001 |
| `RETENTION_MODE` | def | req | req | `anonymize` (consigliato) o `dry_run` | Mode esecuzione | E001 se valore non in {dry_run, anonymize, delete} | E001 |
| `RETENTION_LEAD_DAYS` | def | req | req | `<int>` (Studio decide) | Retention Lead | — | — |
| `RETENTION_SIMULATION_DAYS` | def | req | req | `<int>` | Retention Simulation | — | — |
| `RETENTION_CONSENT_RECORD_DAYS` | def | req | req | `<int>` | Retention ConsentRecord | — | — |
| `RETENTION_AUDIT_LOG_DAYS` | def | req | req | `<int>` | Retention PrivacyAuditEvent | — | — |
| `RETENTION_REQUIRE_SIGNED_VERSION` | def | req | req | `True` | Richiede policy `signed` in prod | E001 | E001 |

### 10. HTTPS / hardening (P0)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `DJANGO_SECURE_SSL_REDIRECT` | def | def | req | `True` | Redirect HTTP→HTTPS | downgrade | Django |
| `DJANGO_SESSION_COOKIE_SECURE` | def | def | req | `True` | Session cookie Secure | leak cookie HTTP | Django |
| `DJANGO_CSRF_COOKIE_SECURE` | def | def | req | `True` | CSRF cookie Secure | leak token HTTP | Django |
| `DJANGO_SECURE_HSTS_SECONDS` | def | def | req | `2592000` (30gg) | HSTS duration | downgrade | Django |
| `DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS` | def | def | req | `True` | Estende HSTS sub | — | — |
| `DJANGO_SECURE_HSTS_PRELOAD` | def | def | opt | `True` (dopo stabilizzazione) | Permette HSTS preload list | — | — |
| `DJANGO_SECURE_REFERRER_POLICY` | def | def | def | `same-origin` | Referrer | — | — |

### 11. Observability (P1)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `SENTRY_DSN` | def | opt | opt | `https://<key>@<org>.ingest.sentry.io/<project>` | Sentry DSN | senza DSN no-op | — |
| `SENTRY_ENVIRONMENT` | def | opt | opt | `production` | Tag env | — | — |
| `SENTRY_TRACES_SAMPLE_RATE` | def | opt | opt | `0.05` | Traces sampling | — | — |
| `SENTRY_PROFILES_SAMPLE_RATE` | def | opt | opt | `0.0` | Profiles sampling | — | — |
| `SENTRY_SEND_DEFAULT_PII` | def | def | def | `False` | NO PII a Sentry | — | — |

### 12. Async (P1)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `LEAD_NOTIFICATION_ASYNC_ENABLED` | def | opt | req | `True` (con worker live) | Celery vs sync | sync fallback | — |
| `CELERY_BROKER_URL` | def | req(se async) | req(se async) | `redis://<host>:6379/0` | Redis broker | task non eseguiti | — |
| `CELERY_RESULT_BACKEND` | def | opt | opt | `` (vuoto) | Result backend (non richiesto per lead) | — | — |
| `CELERY_TASK_ALWAYS_EAGER` | def | def | def | `False` | Run inline (test only) | — | — |

### 13. Admin hardening (P1/P2)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `ADMIN_MFA_REQUIRED` | def | req | req | `True` | Forza TOTP admin | accesso senza 2FA | — |
| `STAFF_LOGIN_ALERTS_ENABLED` | def | req | req | `True` | Brute-force detector | — | — |
| `STAFF_LOGIN_ALERT_*` | def | def | def | sane defaults | Thresholds | — | — |
| `STAFF_AUDIT_RETENTION_*` | def | req | req | sane defaults + DRY_RUN=False post-firma | Retention staff audit | — | — |

### 14. Pexels images (opt)

| Var | Dev | Stag | Prod | Esempio | Descrizione | Errore se manca | Check |
|---|---|---|---|---|---|---|---|
| `PEXELS_API_KEY` | def | opt | opt | `<key>` | API key Pexels | senza key, fallback SVG | — |
| `PEXELS_ENABLED` | def | opt | opt | `True` solo se key set | Master toggle | — | — |

---

## Verifica deploy gate in 3 comandi

Una volta caricato l'env di produzione (file `.env.production` mai committato, gestito dal secret store):

```bash
# 1. System check Django — deve essere clean
DJANGO_DEBUG=False python manage.py check --deploy
# Output atteso: "System check identified no issues (0 silenced)."

# 2. Migrazioni — nessuna pending
DJANGO_DEBUG=False python manage.py makemigrations --check --dry-run
# Output atteso: "No changes detected"

# 3. Canarino IT — il calculator gira con dati reali
DJANGO_DEBUG=False python -c "
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
django.setup()
from apps.cases.services import run_simulation
sim = run_simulation('IT-NATIONAL','road_accident_bodily_injury',
    {'victim_age':35,'permanent_disability_percentage':10,'fault_percentage':0})
assert (int(sim.estimated_min), int(sim.estimated_mid), int(sim.estimated_max)) == (26268, 27353, 28439)
print('OK canary:', sim.estimated_min, sim.estimated_mid, sim.estimated_max)
"
# Output atteso: "OK canary: 26268.0000 27353.0000 28439.0000"
```

Se tutti e tre comandi passano, il **deploy gate è verde** dal punto di vista env-contract.

---

## Anti-pattern da evitare

1. **Settare `DJANGO_DEBUG=True` in produzione "per debug rapido"** → espone stack trace, settings, segreti.
2. **Mettere `*_STATUS=signed` senza firma reale** → bypassa il check, viola GDPR.
3. **Committare `.env.production`** → segreti su Git.
4. **Riusare `DJANGO_SECRET_KEY` di dev** → guard a `settings.py:65-69` solleva `RuntimeError`.
5. **Lasciare `RETENTION_REQUIRE_SIGNED_VERSION=False` in prod** → bypassa il gating policy.
6. **Settare `LEAD_NOTIFICATION_ASYNC_ENABLED=True` senza worker Celery vivo** → task in coda mai eseguiti, mail mai inviate.

---

## Riferimenti

- `docs/PRODUCTION_ENV_REQUIRED_VARS.md` — fonte canonica.
- `docs/PRODUCTION_PREFLIGHT.md` — checklist tecnica deploy.
- `docs/GO_LIVE_GATE_CHECKLIST.md` — 13-section gate check pre-deploy.
- `docs/go_live/GO_LIVE_READINESS_MATRIX_2026-05-13.md` — matrice 20 aree.
- `docs/go_live/LEGAL_SIGNATURE_PACK_TODO.md` — process firma per Studio.
