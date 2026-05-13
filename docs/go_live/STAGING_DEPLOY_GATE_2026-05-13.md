# STAGING DEPLOY GATE — 2026-05-13

**Branch:** `product/staging-readiness-p0`
**Audience:** Release manager, DevOps, QA.

> **Cosa è questo documento.** È il **gate operativo** che deve essere
> attraversato il giorno di un deploy in staging. Ogni voce è una
> checkbox; ognuna ha un comando di verifica e un criterio di pass/fail
> oggettivo. Distinzione fra **P0 bloccante**, **P1 importante** e
> **P2 nice-to-have** esplicita per ogni voce.
>
> **Cosa non è.** Non è la guida per provisioning Postgres (vedi
> `POSTGRES_STAGING_RUNBOOK.md`), non è il go-live in produzione (vedi
> `GO_LIVE_GATE_CHECKLIST.md`), non è la matrice strategica P0
> (vedi `GO_LIVE_READINESS_MATRIX_2026-05-13.md`).
>
> Compilare colonna "Esito" + data il giorno del deploy. Se anche
> **una sola voce P0 fallisce** → **NO-GO** automatico.

---

## 0. Convenzioni

- **Stato**: ✅ pass / ❌ fail / ⚠️ warning (P1+) / N/A
- **Severità**: `P0` = blocca staging deploy; `P1` = blocca prima di
  "staging stabile"; `P2` = nice-to-have, non blocca.
- **Tutti i comandi** assumono di girare nella root del repo, dopo
  aver attivato il venv (locale) o `docker compose exec web` (in container).

---

## 1. Pre-flight Git (P0)

| # | Check | Comando | Pass condition |
|---|---|---|---|
| 1.1 | Working tree pulito | `git status -s` | output vuoto |
| 1.2 | Branch sotto deploy noto | `git branch --show-current` | nome atteso (es. `product/staging-readiness-p0` o tag specifico) |
| 1.3 | Commit HEAD documentato | `git log -1 --oneline` | SHA + message in changelog deploy |
| 1.4 | Nessun commit non-pushed sospetto | `git log @{upstream}..HEAD --oneline` | output vuoto o solo commit attesi (skip se non si fa push) |
| 1.5 | Branch derivato da `main`/baseline verificato | `git merge-base --is-ancestor <baseline> HEAD && echo OK` | `OK` |

**Esito:** _____  **Data:** _____

---

## 2. Env required (P0)

Riferimento canonico: `docs/PRODUCTION_ENV_REQUIRED_VARS.md`.
Template safe: `docs/go_live/staging_env_template.example`.

| # | Check | Comando | Pass condition |
|---|---|---|---|
| 2.1 | `.env.staging` esiste in secret store / volume | (provider-specific) | file presente, mai committato |
| 2.2 | `DJANGO_DEBUG=False` | `grep '^DJANGO_DEBUG=' .env.staging` | `False` |
| 2.3 | `DJANGO_SECRET_KEY` non default | `grep '^DJANGO_SECRET_KEY=' .env.staging \| grep -v 'django-insecure'` | output non vuoto (segno: non è default) |
| 2.4 | `DJANGO_ALLOWED_HOSTS` non default | `grep '^DJANGO_ALLOWED_HOSTS=' .env.staging \| grep -v 'localhost'` | output non vuoto |
| 2.5 | `DJANGO_CSRF_TRUSTED_ORIGINS` con https | `grep '^DJANGO_CSRF_TRUSTED_ORIGINS=https://' .env.staging` | output non vuoto |
| 2.6 | `DATABASE_URL=postgres://...` | `grep '^DATABASE_URL=postgres' .env.staging` | output non vuoto |
| 2.7 | `LEAD_NOTIFICATION_TO_EMAILS` settato (almeno 1 mailbox) | `grep '^LEAD_NOTIFICATION_TO_EMAILS=' .env.staging` | valore non vuoto, no `[]` |
| 2.8 | `STUDIO_*` tutti settati | `grep -c '^STUDIO_' .env.staging` | >= 7 |
| 2.9 | Tutte le `*_STATUS=signed` consistenti con firma Studio | inspect manuale | Studio ha firmato realmente (cross-check con `LEGAL_SIGNATURE_PACK_TODO.md`) |
| 2.10 | Email SMTP host/port/credentials | grep `^EMAIL_HOST`, `^EMAIL_PORT`, `^EMAIL_HOST_USER` | tutti settati (valori non in clear nel log) |

**Esito:** _____  **Data:** _____

> **IMPORTANTE**: non stampare i valori reali nei log di deploy. I `grep`
> sopra restituiscono solo se la chiave esiste, ma non devono essere
> seguiti da `cat .env.staging`. Per audit, hash dei valori critici.

---

## 3. Migration check (P0)

| # | Check | Comando | Pass condition |
|---|---|---|---|
| 3.1 | Nessuna migrazione pending | `python manage.py makemigrations --check --dry-run` | `No changes detected` |
| 3.2 | Migrazioni applicate sul DB target | `python manage.py showmigrations \| grep -c '\[ \]'` | `0` (zero non-applicate) |
| 3.3 | Backup DB pre-migrate eseguito | (provider-specific) | snapshot timestamp < 1h dal deploy |

**Esito:** _____  **Data:** _____

---

## 4. Static files (P0/P1)

| # | Check | Comando | Severità | Pass condition |
|---|---|---|---|---|
| 4.1 | `collectstatic` eseguito senza errori | `python manage.py collectstatic --noinput \| tail -1` | P0 | `N static files copied, M post-processed` |
| 4.2 | `staticfiles/` contiene file (>= 50 attesi) | `find staticfiles/ -type f \| wc -l` | P0 | numero > 50 |
| 4.3 | Font locali presenti | `find staticfiles/fonts/ -name '*.woff2'` | P0 | almeno 8 file (Inter 400/500/600, Cormorant 500/600/700, Amiri 700, Tajawal 400/500/700) |
| 4.4 | `MANIFEST` storage per cache busting | `grep STORAGES config/settings.py` | P1 | presente (consigliato `whitenoise.storage.CompressedManifestStaticFilesStorage`) — al 2026-05-13 **non configurato** (P1 follow-up) |

**Esito:** _____  **Data:** _____

---

## 5. `manage.py check --deploy` (P0)

| # | Check | Comando | Pass condition |
|---|---|---|---|
| 5.1 | Deploy check clean | `DJANGO_DEBUG=False python manage.py check --deploy` | `System check identified no issues (0 silenced).` |
| 5.2 | `core.E001..E008` clean | (sotto-set del precedente) | 0 issue legate ai check legali/Studio |
| 5.3 | `compliance.E001` clean | (sotto-set) | 0 issue retention |
| 5.4 | `crm.E001` clean | (sotto-set) | 0 issue lead notification |

**Esito:** _____  **Data:** _____

> Se uno qualunque dei check legali è ancora rosso → **NO-GO**. Tornare
> a Studio per la firma mancante (vedi `LEGAL_SIGNATURE_PACK_TODO.md`).

---

## 6. DB connectivity (P0)

| # | Check | Comando | Pass condition |
|---|---|---|---|
| 6.1 | `pg_isready` | `pg_isready -h <host> -p 5432` | `accepting connections` |
| 6.2 | Connection Django | `python manage.py dbshell -c '\dt' \| head` | lista tabelle non vuota |
| 6.3 | `Simulation` count sano | `python manage.py shell -c "from apps.cases.models import Simulation; print(Simulation.objects.count())"` | numero ragionevole (>0 dopo seed, 0 su DB pulito) |

**Esito:** _____  **Data:** _____

---

## 7. Email smoke (P0/P1)

| # | Check | Comando | Severità | Pass condition |
|---|---|---|---|---|
| 7.1 | SMTP host reachable | `nc -vz <EMAIL_HOST> <EMAIL_PORT>` | P0 | `succeeded` |
| 7.2 | Test send via Django | `python manage.py shell -c "from django.core.mail import send_mail; send_mail('[staging] gate test', 'gate test body', '<FROM>', ['<RECIPIENT>'])"` | P0 | mail arriva entro 5 min, no error |
| 7.3 | Lead notification end-to-end | submit `/contact/` con dati test → verifica mail Studio | P0 | Studio riceve mail con `public_id` lead |
| 7.4 | Celery async (se attivo) | `LEAD_NOTIFICATION_ASYNC_ENABLED=True` → submit + verifica worker | P1 | task eseguito da worker, mail arriva |

**Esito:** _____  **Data:** _____

> **Privacy**: la mail di notifica include solo `public_id`, timestamp,
> nome/email/telefono, country/case_type/lingua, simulation public_id.
> NON include IP/UA/session_key/internal_notes.

---

## 8. Security headers (P0)

| # | Check | Comando | Pass condition |
|---|---|---|---|
| 8.1 | CSP enforced | `curl -sI https://<host>/ \| grep -i content-security-policy` | header presente, NO `unsafe-inline` su script-src |
| 8.2 | X-Frame-Options DENY | `curl -sI https://<host>/ \| grep -i x-frame-options` | `DENY` |
| 8.3 | X-Content-Type-Options nosniff | `curl -sI https://<host>/ \| grep -i x-content-type-options` | `nosniff` |
| 8.4 | Referrer-Policy | `curl -sI https://<host>/ \| grep -i referrer-policy` | `same-origin` o stricter |
| 8.5 | HSTS attivo | `curl -sI https://<host>/ \| grep -i strict-transport-security` | `max-age=2592000` (30gg) o superiore |
| 8.6 | Cookie Secure flag | submit form → ispeziona cookie `csrftoken`, `sessionid` | entrambi hanno `Secure; HttpOnly; SameSite=Lax/Strict` |
| 8.7 | Redirect HTTP→HTTPS | `curl -sI http://<host>/` | `301`/`302` to https |
| 8.8 | `hreflang` global | `curl -s https://<host>/ \| grep -c 'rel="alternate" hreflang'` | 5 (it/fr/en/ar + x-default) |

**Esito:** _____  **Data:** _____

---

## 9. Browser QA (P0)

Strumento: **Playwright Chromium reale** (non curl, non Django Client).
Evidenze: screenshot in `docs/go_live/evidence/staging_readiness_<date>/`.

| # | Pagina | Status | Title corretto | Console errors | Static 404 | Screenshot |
|---|---|---|---|---|---|---|
| 9.1 | `/` desktop | 200 | ✓ | 0 | 0 | ✓ |
| 9.2 | `/countries/` desktop | 200 | ✓ | 0 | 0 | (opt) |
| 9.3 | `/countries/italy/` desktop | 200 | ✓ | 0 | 0 | (opt) |
| 9.4 | `/wizard/` desktop | 200 | ✓ | 0 | 0 | (opt) |
| 9.5 | `/wizard/it/road-accident/` desktop | 200 | ✓ | 0 | 0 | ✓ |
| 9.6 | `/wizard/it/road-accident/` mobile | 200 | ✓ | 0 | 0 | ✓ |
| 9.7 | `/wizard/result/<uuid>/` desktop (canary) | 200 | ✓ | 0 | 0 | ✓ |
| 9.8 | `/wizard/result/<uuid>/` mobile | 200 | ✓ | 0 | 0 | ✓ |
| 9.9 | `/contact/` desktop | 200 | ✓ | 0 | 0 | (opt) |
| 9.10 | `/privacy/` | 200 | ✓ | 0 | 0 | (opt) |
| 9.11 | `/disclaimer/` | 200 | ✓ | 0 | 0 | (opt) |
| 9.12 | `/fr/` desktop | 200 | ✓ | 0 | 0 | (opt) |
| 9.13 | `/ar/` desktop RTL | 200 | `<html dir="rtl">` | 0 | 0 | ✓ |

**Esito:** _____  **Data:** _____

> Esegui lo script `scripts/playwright_staging_qa.py` (vedi
> `docs/go_live/evidence/staging_readiness_2026-05-13/`) sul URL
> staging, non sul dev locale.

---

## 10. Wizard canary E2E (P0)

| # | Step | Comando / azione | Pass condition |
|---|---|---|---|
| 10.1 | Apri form IT RCA | navigate `/wizard/it/road-accident/` | 200, form visible |
| 10.2 | Compila input canary | `victim_age=35, permanent_disability_percentage=10, fault_percentage=0` | form valid |
| 10.3 | Spunta i 2 consensi GDPR | `privacy_accepted=True, special_categories_accepted=True` | form valid |
| 10.4 | Lascia honeypot vuoto | `website=""` | bot guard pass |
| 10.5 | Submit | click submit | 302 → `/wizard/result/<uuid>/` |
| 10.6 | Result page MIN | screenshot result | text contains `26268 EUR` (or local format) |
| 10.7 | Result page MID | screenshot result | text contains `27353 EUR`, **bold/3xl** |
| 10.8 | Result page MAX | screenshot result | text contains `28439 EUR` |
| 10.9 | Sources cited | DOM inspect | at least 1 `<li>` in "Cited legal sources" |
| 10.10 | Disclaimer presente | DOM inspect | testo "indicative" o equivalente lingua |
| 10.11 | CTA "Request legal review" | click → `/contact/?sim=<uuid>` | 200 con `country` + `case_type` precompilati |

**Esito:** _____  **Data:** _____

> **Mai usare dati personali reali** nei test. Usare `Test Tester` /
> `test@example.com`.

---

## 11. Legal gate (P0)

| # | Check | Verifica | Pass condition |
|---|---|---|---|
| 11.1 | Privacy policy page status | visita `/privacy/` | badge "Signed YYYY-MM-DD" visibile, banner working-copy assente |
| 11.2 | Disclaimer page status | visita `/disclaimer/` | badge "Signed", banner working-copy assente |
| 11.3 | Footer placeholders puliti | grep `[da configurare]` su `/` | match vuoto |
| 11.4 | Mandate template version | grep `working-copy` in admin `MandateTemplateVersion` | nessun template attivo è working_copy |
| 11.5 | `RETENTION_REQUIRE_SIGNED_VERSION=True` | env check | True |
| 11.6 | LegalSource approved per IT TUN 2025 | `LegalSource.objects.filter(status='approved', country__code='IT').count()` | >= 1 |
| 11.7 | Nessuna fonte FR/BE/MA/TN promossa senza review | `LegalReview.objects.filter(decision='approve').count()` per FR/BE/MA/TN | come da `NON_IT_COUNTRY_ACTIVATION_PLAN.md` (0 prima di review reale) |

**Esito:** _____  **Data:** _____

---

## 12. Rollback (P0)

Pre-deploy, **dimostrare** che il rollback è eseguibile:

| # | Check | Comando | Pass condition |
|---|---|---|---|
| 12.1 | Tag/commit immagine precedente noto | `docker images badrane-legaltech --format '{{.Tag}}'` | tag previous-build presente |
| 12.2 | DB backup pre-deploy | (vedi POSTGRES_STAGING_RUNBOOK §6.2) | dump file presente con timestamp ultimo 1h |
| 12.3 | Procedura rollback documentata | letta in PR / runbook | leggibile, comandi citati |
| 12.4 | Dry-run rollback (su sub-environment) | `docker compose stop web && docker compose run --rm web sh -c "..."` | comando torna 0 |

**Esito:** _____  **Data:** _____

---

## 13. Backup (P0)

| # | Check | Comando | Pass condition |
|---|---|---|---|
| 13.1 | Strategia backup attiva | provider-specific | snapshot daily configurato |
| 13.2 | Ultimo backup < 25h | `ls -lt /var/backups/badrane/ \| head -2` | timestamp recente |
| 13.3 | Test restore eseguito ultima settimana | vedi log restore | `pg_restore -l` passa su dump più recente |
| 13.4 | Off-site copia | (S3/equivalente) | copia in regione differente esiste |

**Esito:** _____  **Data:** _____

---

## 14. Go / No-Go table

Compilare il giorno del deploy. **Anche un solo P0 fail = NO-GO.**

| Categoria | Severità | Esito | Note |
|---|---|---|---|
| 1. Git pre-flight | P0 | __ | |
| 2. Env required | P0 | __ | |
| 3. Migration check | P0 | __ | |
| 4. Static files | P0 + P1 manifest | __ | |
| 5. `check --deploy` | P0 | __ | |
| 6. DB connectivity | P0 | __ | |
| 7. Email smoke | P0 + P1 celery | __ | |
| 8. Security headers | P0 | __ | |
| 9. Browser QA (Playwright reale) | P0 | __ | |
| 10. Wizard canary | P0 | __ | |
| 11. Legal gate | P0 | __ | |
| 12. Rollback | P0 | __ | |
| 13. Backup | P0 | __ | |
| **OVERALL** | | **GO / NO-GO** | |

---

## 15. Cosa non è in scope di questo gate

- **Pen-test esterno** (P2-SEC-1): consigliato pre go-live PRODUZIONE,
  non per staging.
- **Lighthouse CI** (P1-PERF): `lighthouserc.json` + `.lighthouseci/`
  esistono; eseguire separatamente.
- **Load test / capacity test**: non richiesto per staging primo deploy.
- **Cookie banner Accept/Reject**: oggi solo Accept (corretto se solo
  cookies tecnici).

---

## 16. Linked docs

- `docs/PRODUCTION_ENV_REQUIRED_VARS.md`
- `docs/PRODUCTION_PREFLIGHT.md`
- `docs/GO_LIVE_GATE_CHECKLIST.md` (gate produzione, più ampio)
- `docs/go_live/GO_LIVE_READINESS_MATRIX_2026-05-13.md`
- `docs/go_live/ENV_CONTRACT_GO_LIVE.md`
- `docs/go_live/LEGAL_SIGNATURE_PACK_TODO.md`
- `docs/go_live/NON_IT_COUNTRY_ACTIVATION_PLAN.md`
- `docs/go_live/POSTGRES_STAGING_RUNBOOK.md`
- `docs/go_live/staging_env_template.example`
