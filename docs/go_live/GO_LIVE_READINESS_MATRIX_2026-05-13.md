# GO-LIVE READINESS MATRIX — 2026-05-13

**Branch di lavoro:** `product/go-live-readiness-p0`
**HEAD di partenza:** `05186ad` (da `product/studio-lead-activity-timeline`)
**Audit di riferimento:** sessione del 2026-05-13 — read-only, 2148 test verdi.

> Documento curato lato dev per dare allo Studio + DevOps + Project
> Manager una **vista unica P0** di ciò che frena il go-live.
> Non sostituisce i documenti tecnici esistenti
> (`docs/PRODUCTION_ENV_REQUIRED_VARS.md`, `docs/PRODUCTION_PREFLIGHT.md`,
> `docs/GO_LIVE_GATE_CHECKLIST.md`, `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md`):
> li **mappa** in formato matrice azionabile. In caso di conflitto, i
> documenti di dettaglio prevalgono.
>
> Regola d'oro: **nulla è marcato "completato" se non lo è davvero**.
> Le firme dello Studio non si auto-impostano. Le promozioni a `approved`
> richiedono review legale umana.

---

## Legenda

- **Stato**: `BLOCCANTE` (deploy impossibile), `ATTESO` (firma/azione esterna), `DA FARE` (azione tecnica disponibile), `OK` (verificato).
- **Owner**: `Studio` (firma legale), `Dev` (codice/config), `DevOps` (infrastruttura), `Studio+Dev` (coordinato).
- **Comando di test**: il singolo comando che, se ritorna verde, dimostra che l'area non è più un blocker.

---

## Matrice P0

### Area 1 — Privacy policy firmata

| Campo | Valore |
|---|---|
| **Stato attuale** | `PRIVACY_POLICY_STATUS=working_copy`, `PRIVACY_POLICY_VERSION=working-copy-2026-05-10`, `PRIVACY_POLICY_SIGNED_AT=` (vuoto). System check `core.E006` blocca prod. |
| **Bloccante?** | Sì |
| **Owner** | Studio (firma) + Dev (env setting dopo firma) |
| **File/config coinvolti** | `templates/public/privacy.html`, `config/settings.py:669-671`, `apps/core/checks.py` (E006) |
| **Azione richiesta** | Studio rivede e firma il testo privacy in IT/FR/EN/AR. Dev setta `PRIVACY_POLICY_STATUS=signed`, `PRIVACY_POLICY_VERSION=YYYY-MM-DD-final`, `PRIVACY_POLICY_SIGNED_AT=YYYY-MM-DD`. |
| **Come verificare** | `manage.py check` (in `DEBUG=False`) restituisce 0 issue per `core.E006`. La pagina `/privacy/` non mostra banner working-copy. |
| **Comando di test** | `DJANGO_DEBUG=False PRIVACY_POLICY_STATUS=signed PRIVACY_POLICY_VERSION=2026-XX-XX-final PRIVACY_POLICY_SIGNED_AT=2026-XX-XX python manage.py check 2>&1 \| grep -i core.E006` (output vuoto = pass) |
| **Rischio se ignorato** | Sanzione GDPR per assenza informativa firmata; perdita di fiducia clienti; campagna marketing non possibile. |

### Area 2 — Disclaimer firmato

| Campo | Valore |
|---|---|
| **Stato attuale** | `DISCLAIMER_STATUS=working_copy`, `DISCLAIMER_VERSION=working-copy-2026-05-10`. Check `core.E007` blocca prod. |
| **Bloccante?** | Sì |
| **Owner** | Studio + Dev |
| **File/config coinvolti** | `templates/public/disclaimer.html`, `config/settings.py:672-674`, `apps/core/checks.py` (E007) |
| **Azione richiesta** | Studio firma il testo disclaimer (8 sezioni). Dev setta `DISCLAIMER_STATUS=signed`, `DISCLAIMER_VERSION=YYYY-MM-DD-final`, `DISCLAIMER_SIGNED_AT=YYYY-MM-DD`. |
| **Come verificare** | Pagina `/disclaimer/` mostra badge "Signed YYYY-MM-DD". `manage.py check --deploy` clean per E007. |
| **Comando di test** | `DJANGO_DEBUG=False DISCLAIMER_STATUS=signed ... python manage.py check 2>&1 \| grep -i core.E007` (vuoto) |
| **Rischio se ignorato** | Esposizione deontologica: simulazione potrebbe essere interpretata come parere legale. |

### Area 3 — Mandato professionale

| Campo | Valore |
|---|---|
| **Stato attuale** | `MANDATE_TEMPLATE_STATUS=working_copy`, template PDF non fornito dallo Studio. `MandateAcceptance` modello pronto, `REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True`. |
| **Bloccante?** | Sì (per attivazione casi reali) |
| **Owner** | Studio (testo + firma) + Dev (env + flow) |
| **File/config coinvolti** | `apps/compliance/models.py` (`MandateTemplateVersion`, `MandateAcceptance`), `config/settings.py:642-649`, `apps/core/checks.py` (E008) |
| **Azione richiesta** | Studio fornisce template mandato professionale (PDF + testo in 4 lingue). Dev crea record `MandateTemplateVersion` con `status=signed`. Setta env `MANDATE_TEMPLATE_VERSION/STATUS/SIGNED_AT`. |
| **Come verificare** | `manage.py check` clean per E008. Lead non può essere "promosso a pratica" senza `mandate_signed=True`. |
| **Comando di test** | `DJANGO_DEBUG=False MANDATE_TEMPLATE_STATUS=signed ... python manage.py check 2>&1 \| grep -i core.E008` (vuoto) |
| **Rischio se ignorato** | Pratica iniziata senza incarico scritto; nullità deontologica. |

### Area 4 — Consenso GDPR art. 9

| Campo | Valore |
|---|---|
| **Stato attuale** | `SPECIAL_CATEGORIES_NOTICE_VERSION=working-copy-2026-05-10`. UI già raccoglie il consenso (`special_categories_accepted` su contact form e wizard, verificato live). |
| **Bloccante?** | Sì (firma testo) |
| **Owner** | Studio + Dev |
| **File/config coinvolti** | `templates/partials/consent_checkboxes.html`, `config/settings.py:592-597`, `apps/core/checks.py` (E004) |
| **Azione richiesta** | Studio firma testo dei due consensi (art. 6 + art. 9). Dev aggiorna `PRIVACY_NOTICE_VERSION` e `SPECIAL_CATEGORIES_NOTICE_VERSION` a versione finale firmata. |
| **Come verificare** | Check `core.E004` clean. `ConsentRecord` nuovi hanno `text_version` finale. |
| **Comando di test** | `DJANGO_DEBUG=False PRIVACY_NOTICE_VERSION=2026-XX-XX-final SPECIAL_CATEGORIES_NOTICE_VERSION=2026-XX-XX-final python manage.py check 2>&1 \| grep -i core.E004` (vuoto) |
| **Rischio se ignorato** | Trattamento dati sensibili senza consenso esplicito tracciabile → violazione art. 9 GDPR. |

### Area 5 — Retention policy

| Campo | Valore |
|---|---|
| **Stato attuale** | `RETENTION_POLICY_VERSION=working-copy-2026-05-10`, `RETENTION_MODE=dry_run`, `RETENTION_ENABLED=False`. Check `compliance.E001` blocca prod. Cron non attivo. |
| **Bloccante?** | Sì |
| **Owner** | Studio (decide giorni per scope) + Dev (cron + env) |
| **File/config coinvolti** | `config/settings.py:699-712`, `apps/compliance/checks.py` (E001), `apps/compliance/management/commands/run_retention_policy.py` |
| **Azione richiesta** | Studio decide retention days per `RETENTION_LEAD_DAYS`, `RETENTION_SIMULATION_DAYS`, `RETENTION_CONSENT_RECORD_DAYS`, `RETENTION_AUDIT_LOG_DAYS`. Firma policy. Dev setta env, abilita `RETENTION_ENABLED=True`, sposta `RETENTION_MODE` a `anonymize`, schedula cron Celery Beat o cronjob shell. |
| **Come verificare** | `manage.py run_retention_policy --dry-run` produce log atteso. `RetentionRunLog` registra l'esecuzione. |
| **Comando di test** | `python manage.py run_retention_policy --dry-run 2>&1 \| tail -5` (verifica candidati conteggiati, status=SUCCESS) |
| **Rischio se ignorato** | Dati personali conservati oltre necessità → violazione GDPR art. 5(1)(e). |

### Area 6 — Identificativi Studio nel footer

| Campo | Valore |
|---|---|
| **Stato attuale** | Footer mostra `[da configurare prima del go-live]` per tutti i campi. Check `core.W001` in dev, diventa `core.E001` in prod. |
| **Bloccante?** | Sì (E001 in DEBUG=False) |
| **Owner** | Studio (dati) + Dev (env) |
| **File/config coinvolti** | `templates/partials/footer.html`, `config/settings.py:318-333`, `apps/core/checks.py` (E001/W001) |
| **Azione richiesta** | Vedi Aree 7-11 (per-variabile). |
| **Come verificare** | Pagina `/` mostra footer pulito (nessun `[da configurare]`). |
| **Comando di test** | `curl -s http://<host>/ \| grep -c 'da configurare'` deve restituire 0 |
| **Rischio se ignorato** | Footer non a norma art. 17-bis Cod. deont. forense + D.Lgs. 70/2003 art. 7. |

### Area 7 — STUDIO_LEAD_LAWYER_NAME

| Campo | Valore |
|---|---|
| **Stato attuale** | Vuoto |
| **Bloccante?** | Sì (E001 in prod) |
| **Owner** | Studio |
| **File/config coinvolti** | `config/settings.py:318` |
| **Azione richiesta** | Studio fornisce nome avvocato responsabile (es. "Avv. <Nome Cognome>"). Dev setta env. |
| **Come verificare** | `/` footer mostra nome reale. |
| **Comando di test** | `DJANGO_DEBUG=False STUDIO_LEAD_LAWYER_NAME="Avv. X Y" ... python manage.py check 2>&1 \| grep STUDIO_LEAD_LAWYER_NAME` (vuoto) |
| **Rischio se ignorato** | Footer non a norma. |

### Area 8 — STUDIO_BAR_ASSOCIATION

| Campo | Valore |
|---|---|
| **Stato attuale** | Vuoto |
| **Bloccante?** | Sì |
| **Owner** | Studio |
| **File/config coinvolti** | `config/settings.py:319` |
| **Azione richiesta** | Studio fornisce Ordine degli Avvocati di iscrizione (es. "Ordine degli Avvocati di X"). |
| **Come verificare** | `/` footer mostra dato reale. |
| **Comando di test** | `DJANGO_DEBUG=False STUDIO_BAR_ASSOCIATION="..." ... python manage.py check` clean per E001 |
| **Rischio se ignorato** | Footer non a norma. |

### Area 9 — STUDIO_VAT_NUMBER

| Campo | Valore |
|---|---|
| **Stato attuale** | Vuoto |
| **Bloccante?** | Sì |
| **Owner** | Studio |
| **File/config coinvolti** | `config/settings.py:321` |
| **Azione richiesta** | Studio fornisce P.IVA (formato `ITxxxxxxxxxxx` o equivalente UE). |
| **Come verificare** | Footer mostra P.IVA. |
| **Comando di test** | Vedi Area 6. |
| **Rischio se ignorato** | Violazione D.Lgs. 70/2003 art. 7 (commercio elettronico). |

### Area 10 — STUDIO_PEC_EMAIL

| Campo | Valore |
|---|---|
| **Stato attuale** | Vuoto |
| **Bloccante?** | Sì |
| **Owner** | Studio |
| **File/config coinvolti** | `config/settings.py:323` |
| **Azione richiesta** | Studio fornisce PEC ufficiale dello Studio (formato `@pec.<dominio>`). |
| **Come verificare** | Footer mostra PEC. |
| **Comando di test** | Vedi Area 6. |
| **Rischio se ignorato** | Obbligo di legge per attività professionale. |

### Area 11 — Assicurazione professionale

| Campo | Valore |
|---|---|
| **Stato attuale** | `STUDIO_PROFESSIONAL_INSURANCE_INSURER` e `_POLICY` vuoti. `_CEILING` opzionale. |
| **Bloccante?** | Sì (insurer + policy) |
| **Owner** | Studio |
| **File/config coinvolti** | `config/settings.py:325-333` |
| **Azione richiesta** | Studio fornisce: compagnia assicurativa RC professionale, numero polizza, massimale. |
| **Come verificare** | Footer mostra "Assicurazione professionale: <insurer> — polizza <policy>". |
| **Comando di test** | `manage.py check` clean per E001 (assicurazione + polizza obbligatori). |
| **Rischio se ignorato** | Violazione art. 12 L. 247/2012 (obbligo trasparenza copertura RC). |

### Area 12 — LEAD_NOTIFICATION_TO_EMAILS

| Campo | Valore |
|---|---|
| **Stato attuale** | `LEAD_NOTIFICATION_ENABLED=True` (default), `LEAD_NOTIFICATION_TO_EMAILS=[]`. Check `crm.E001` blocca prod. |
| **Bloccante?** | Sì |
| **Owner** | Studio (decide caselle) + Dev (env) |
| **File/config coinvolti** | `config/settings.py:382-383`, `apps/crm/checks.py` (E001) |
| **Azione richiesta** | Studio decide quali caselle Studio devono ricevere notifica lead. Dev setta `LEAD_NOTIFICATION_TO_EMAILS=staff@...,backup@...`. |
| **Come verificare** | `manage.py check` clean per `crm.E001`. Submit del form `/contact/` invia mail. |
| **Comando di test** | `LEAD_NOTIFICATION_TO_EMAILS=test@example.com DJANGO_DEBUG=False python manage.py check 2>&1 \| grep crm.E001` (vuoto) |
| **Rischio se ignorato** | Lead pubblici salvati ma nessuno avvisato → perdita opportunità + dati raccolti senza scopo legittimo di follow-up. |

### Area 13 — SMTP reale

| Campo | Valore |
|---|---|
| **Stato attuale** | `EMAIL_BACKEND=console` in dev. In prod default `smtp.EmailBackend` ma `EMAIL_HOST` non documentato negli env letti via `environ.Env`. Verificare se `apps.crm.services` usa configurazione personalizzata. |
| **Bloccante?** | Sì |
| **Owner** | DevOps |
| **File/config coinvolti** | `config/settings.py:363-375`, `apps/crm/tasks.py`, `apps/crm/services.py` |
| **Azione richiesta** | DevOps sceglie provider SMTP (es. Mailgun, SendGrid, AWS SES, Postmark). Configura `EMAIL_HOST/PORT/USER/PASSWORD/USE_TLS` come env. |
| **Come verificare** | Submit `/contact/` su staging → mail arriva alla casella `LEAD_NOTIFICATION_TO_EMAILS`. |
| **Comando di test** | `python manage.py shell -c "from django.core.mail import send_mail; send_mail('test', 'body', 'no-reply@…', ['<your-staff-mailbox>'])"` |
| **Rischio se ignorato** | Lead non notificati. |

### Area 14 — Celery / async email

| Campo | Valore |
|---|---|
| **Stato attuale** | `LEAD_NOTIFICATION_ASYNC_ENABLED=False` default. Stack pronto (`apps/crm/tasks.py`, settings `CELERY_BROKER_URL`). Fallback sincrono attivo. |
| **Bloccante?** | No (P1: il sync funziona, ma con tempi di latenza visibili al submit) |
| **Owner** | DevOps + Dev |
| **File/config coinvolti** | `config/celery.py`, `docker-compose.staging.yml`, `config/settings.py:469-491` |
| **Azione richiesta** | DevOps deploya Redis broker + container `celery-worker`. Setta `LEAD_NOTIFICATION_ASYNC_ENABLED=True`, `CELERY_BROKER_URL=redis://...`. |
| **Come verificare** | Submit `/contact/` → response immediata; mail arriva entro 30s. `celery -A config inspect active` mostra worker live. |
| **Comando di test** | `python manage.py shell -c "from apps.crm.tasks import send_lead_notification_task; send_lead_notification_task.delay(<lead_pk>)"` |
| **Rischio se ignorato** | Latenza submit fino a ~2s su Studio firewall. Non bloccante per go-live. |

### Area 15 — Postgres staging

| Campo | Valore |
|---|---|
| **Stato attuale** | Dev su SQLite (77 MB in repo dir, gitignored). `docker-compose.staging.yml` ha skeleton Postgres ma Dockerfile final non committato. |
| **Bloccante?** | Sì (deploy non possibile su SQLite) |
| **Owner** | DevOps |
| **File/config coinvolti** | `Dockerfile`, `docker-compose.staging.yml`, `.env.staging.example` |
| **Azione richiesta** | DevOps provisiona Postgres (managed o self-hosted), genera credenziali. `DATABASE_URL=postgres://app:pass@host:5432/badrane`. Esegue `manage.py migrate` su DB vuoto + `pytest -q` con `DATABASE_URL` settato per smoke. |
| **Come verificare** | `manage.py migrate` apply tutte le migrazioni (0 pending). `pytest -q` verde su Postgres. |
| **Comando di test** | `DATABASE_URL=postgres://... python manage.py migrate --check && DATABASE_URL=postgres://... pytest -q --tb=short` |
| **Rischio se ignorato** | Nessun deploy possibile. |

### Area 16 — HTTPS / reverse proxy

| Campo | Valore |
|---|---|
| **Stato attuale** | Settings HSTS/Secure cookies pronti (attivati quando `DEBUG=False`). Reverse proxy non in scope del repo. |
| **Bloccante?** | Sì |
| **Owner** | DevOps |
| **File/config coinvolti** | Hosting (Caddy/nginx/Cloudflare), `config/settings.py:51-59` |
| **Azione richiesta** | DevOps configura Caddy o nginx + Let's Encrypt sul dominio scelto (es. `simulatore.studiolegalebadrane.it`). Setta `DJANGO_CSRF_TRUSTED_ORIGINS=https://<dominio>`, `DJANGO_ALLOWED_HOSTS=<dominio>`. Verifica `X-Forwarded-Proto: https`. |
| **Come verificare** | `curl -I https://<host>/` mostra `HTTP/2 200`, header `Strict-Transport-Security` presente. |
| **Comando di test** | `curl -sIL https://<host>/ \| grep -iE "strict-transport-security\|x-frame-options\|content-security-policy"` |
| **Rischio se ignorato** | Browser blocca cookies Secure, CSRF rifiutato dietro proxy non firmato. |

### Area 17 — Backup DB

| Campo | Valore |
|---|---|
| **Stato attuale** | Backup non documentato. `backups/` dir esiste in repo (gitignored). |
| **Bloccante?** | Sì (per produzione) |
| **Owner** | DevOps |
| **File/config coinvolti** | Provider-specific (RDS automated, pg_dump cron, ecc.) |
| **Azione richiesta** | DevOps configura backup automatico (consigliato: snapshot daily + WAL streaming). Test restore su DB pulito. Documenta in `docs/deploy/BACKUP_RUNBOOK.md`. |
| **Come verificare** | Snapshot più recente <24h. Test restore eseguito almeno una volta. |
| **Comando di test** | `pg_dump --version && <provider-specific restore command>` |
| **Rischio se ignorato** | Disaster recovery impossibile; perdita totale dati legali in caso di failure. |

### Area 18 — Sentry DSN

| Campo | Valore |
|---|---|
| **Stato attuale** | `SENTRY_DSN=` (vuoto). Codice `apps/core/observability.py` no-op senza DSN. Scrubber PII pronto. |
| **Bloccante?** | No (P1: forte raccomandazione) |
| **Owner** | DevOps |
| **File/config coinvolti** | `config/settings.py:397-404`, `apps/core/observability.py` |
| **Azione richiesta** | DevOps crea progetto Sentry, configura `SENTRY_DSN=<dsn>`, `SENTRY_ENVIRONMENT=production`, `SENTRY_TRACES_SAMPLE_RATE=0.05` (5% per costi). |
| **Come verificare** | Solleva eccezione di test via management command. Evento appare in Sentry entro 30s. |
| **Comando di test** | `python manage.py shell -c "raise RuntimeError('sentry-test')"` (vedi Sentry events) |
| **Rischio se ignorato** | Errori 5xx in prod non visibili in tempo reale. |

### Area 19 — Paese non-IT da promuovere

| Campo | Valore |
|---|---|
| **Stato attuale** | 5 fonti FR + 5 fonti BE in `needs_review`. Dataset DRAFT esistono per FR (Mornet, Gazette); BE ha CSV su disco ma nessun dataset DB. Engine + amount_rule registrati per entrambi. Vedi `docs/go_live/NON_IT_COUNTRY_ACTIVATION_PLAN.md`. |
| **Bloccante?** | No per il go-live tecnico (IT è sufficiente); Sì per promettere "multi-paese" all'esterno |
| **Owner** | Studio (legal review) + Dev (promozione + engine override) |
| **File/config coinvolti** | `apps/calculators/engines/france.py`, `apps/calculators/engines/belgium.py`, `apps/legal_sources/models.py`, dataset import commands |
| **Azione richiesta** | Vedi piano dedicato `NON_IT_COUNTRY_ACTIVATION_PLAN.md`. |
| **Come verificare** | `run_simulation(jurisdiction_code='FR-NATIONAL' o 'BE-NATIONAL', ...).status == 'calculated'` |
| **Comando di test** | Vedi `NON_IT_COUNTRY_ACTIVATION_PLAN.md` § "Smoke test post-attivazione". |
| **Rischio se ignorato** | Marketing parla di multi-paese ma solo IT calcola: dissonanza commerciale. |

### Area 20 — Smoke QA staging

| Campo | Valore |
|---|---|
| **Stato attuale** | `docs/QA_TEST_PLAN.md` definisce 15 scenari. Pass1 screenshots in `docs/screenshots/`. Runner automatico non in CI. |
| **Bloccante?** | Sì (almeno QA-01 canarino IT + QA-04 deontologico) |
| **Owner** | QA / Dev |
| **File/config coinvolti** | `docs/QA_TEST_PLAN.md`, `apps/cases/test_*.py` |
| **Azione richiesta** | Su staging, eseguire manualmente: QA-01 (35/10/0 → 26 268/27 353/28 439), QA-04 (offerta assicurazione), QA-08 (RTL AR), QA-09 (honeypot), QA-11 (input invalidi), QA-14 (no JS). Documentare risultati in `docs/qa/STAGING_SMOKE_<date>.md`. |
| **Come verificare** | Tutti gli scenari critici (P0) passano su staging URL. |
| **Comando di test** | `python -c "from apps.cases.services import run_simulation; sim = run_simulation('IT-NATIONAL', 'road_accident_bodily_injury', {'victim_age':35,'permanent_disability_percentage':10,'fault_percentage':0}); assert (sim.estimated_min, sim.estimated_mid, sim.estimated_max) == (26268, 27353, 28439)"` |
| **Rischio se ignorato** | Bug ovvi scoperti dal primo cliente. |

---

## Riepilogo numerico

| Categoria | Aree | Bloccanti |
|---|---|---|
| **Legale firma Studio** | 5 (Privacy, Disclaimer, Mandato, Art.9, Retention) | 5 |
| **Dati Studio footer** | 6 (W001 + 5 var) | 6 |
| **Operative tecniche** | 7 (LeadEmails, SMTP, Postgres, HTTPS, Backup, ...) | 5 (+1 P1 Celery, +1 P1 Sentry) |
| **Funzionali** | 2 (paese non-IT, smoke QA) | 1 |
| **TOTALE** | 20 | **17** |

**Stima time-to-go-live se Studio firma in 1 settimana:**
- Setup env + Postgres + HTTPS + backup + Sentry: **3-5 giorni dev/DevOps**
- Smoke QA staging: **1-2 giorni**
- **Totale realistico: ~2 settimane dal momento delle firme.**

---

## Note finali

- Questo documento sarà rivisitato post sprint corrente. Non considerare "OK" alcuna riga senza verifica diretta.
- Le firme non si fingono. Ogni `*_STATUS=signed` deve corrispondere a un atto reale dello Studio.
- I valori esempio (`Avv. X Y`, `2026-XX-XX-final`) sono placeholder DI DOCUMENTAZIONE, non valori da inserire in env.
