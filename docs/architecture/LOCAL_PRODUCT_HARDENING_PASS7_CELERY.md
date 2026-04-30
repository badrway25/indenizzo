# LOCAL — Product hardening, pass 7 — Celery async lead notification

**Iter**: F-local-product-hardening-pass7-celery-async
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**
**Default**: `LEAD_NOTIFICATION_ASYNC_ENABLED=False` ⇒ flusso
sincrono (pass 2) inalterato.

> Settimo passaggio: Celery + Redis cablati come broker per la
> notifica email Lead, con fallback sincrono se il broker è giù.
> Il flusso utente NON può rompersi né per Celery né per SMTP.
> IT smoke 35/10/0 → 26 268 / 27 353 / 28 439 EUR verificato.

---

## 1. Cosa è stato aggiunto

| Area | File | Tipo |
|---|---|---|
| Celery app | `config/celery.py` (nuovo) | `Celery("badrane_legaltech")` + autodiscover |
| Celery export | `config/__init__.py` (modificato) | espone `celery_app` per la discovery |
| Settings | `config/settings.py` | 6 settings env-driven (CELERY_*) + `LEAD_NOTIFICATION_ASYNC_ENABLED` |
| Task CRM | `apps/crm/tasks.py` (nuovo) | `send_lead_notification_task(lead_id)` con retry |
| View dispatch | `apps/crm/views.py` | `_dispatch_lead_notification` con sync/async + fallback |
| Compose | `docker-compose.local.yml` | servizio `celery-worker` |
| Docs | `docs/architecture/LOCAL_PRODUCT_HARDENING_PASS7_CELERY.md` (nuovo) | questo file |
| Docs | `docs/deploy/LOCAL_DOCKER_COMPOSE.md` | §10 aggiornata con flusso Celery |
| Test | `apps/crm/test_celery_tasks.py` (nuovo) | 9 test |

`celery>=5.4` e `redis>=5.0` erano **già** in `requirements.txt`
(da F0 scaffolding). Niente nuove dipendenze. Niente DB schema
change.

---

## 2. Settings Celery

In `config/settings.py`, sezione **Celery**:

| Setting | Default | Override env |
|---|---|---|
| `CELERY_BROKER_URL` | `REDIS_URL` (env) → `redis://localhost:6379/0` | `CELERY_BROKER_URL` |
| `CELERY_RESULT_BACKEND` | `""` (disabled, fire-and-forget) | `CELERY_RESULT_BACKEND` |
| `CELERY_TASK_ALWAYS_EAGER` | `False` | `CELERY_TASK_ALWAYS_EAGER` |
| `CELERY_TASK_EAGER_PROPAGATES` | `True` | `CELERY_TASK_EAGER_PROPAGATES` |
| `CELERY_TASK_SERIALIZER` | `"json"` | (hardcoded) |
| `CELERY_RESULT_SERIALIZER` | `"json"` | (hardcoded) |
| `CELERY_ACCEPT_CONTENT` | `["json"]` | (hardcoded) |
| `CELERY_TIMEZONE` | `TIME_ZONE` (Europe/Rome) | (derivato) |
| `LEAD_NOTIFICATION_ASYNC_ENABLED` | `False` | `LEAD_NOTIFICATION_ASYNC_ENABLED` |

**Comportamento applicativo:**
- `LEAD_NOTIFICATION_ASYNC_ENABLED=False` (default dev): la view
  `contact` chiama `send_lead_notification` sincronamente (pass 2,
  invariato).
- `=True`: la view chiama `send_lead_notification_task.delay(lead.pk)`.
  Se `delay()` solleva (broker down), fallback automatico al send
  sincrono.

`CELERY_RESULT_BACKEND=""` perché il task è fire-and-forget: non
serve tracciare il risultato. Quando in futuro avremo task che
producono output (es. PDF report jobs), basterà settare
`CELERY_RESULT_BACKEND=redis://...` o `db+postgresql://...` via env.

---

## 3. Celery app — `config/celery.py`

```python
import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
app = Celery("badrane_legaltech")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
```

**Caratteristiche:**
- Pattern standard Celery + Django.
- Nome app `badrane_legaltech` — riconoscibile in flower / log.
- `namespace="CELERY"` carica solo i settings con prefisso
  `CELERY_*` (no leak di altri settings).
- `autodiscover_tasks()` cerca `apps/<app>/tasks.py` per ogni
  `INSTALLED_APPS`.

`config/__init__.py` espone `celery_app` per garantire che
`shared_task` funzioni anche senza un worker attivo.

**Avvio worker (in Docker compose locale):**

```bash
docker compose -f docker-compose.local.yml logs -f celery-worker
# oppure dentro il container:
celery -A config worker -l INFO --concurrency 2
```

---

## 4. Task CRM — `apps/crm/tasks.py`

```python
@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="apps.crm.tasks.send_lead_notification_task",
)
def send_lead_notification_task(self, lead_id: int) -> bool:
    ...
```

**Algoritmo:**
1. Lazy import di `Lead` + `send_lead_notification` (evita
   problemi di circular import durante autodiscover).
2. `Lead.objects.get(pk=lead_id)` — se `DoesNotExist`: log warning
   senza PII + return False (no retry: il Lead potrebbe essere
   stato cancellato).
3. `send_lead_notification(lead)`: già failure-soft (pass 2). Il
   task la richiama in modo idempotente.
4. Eccezioni inattese: `self.retry(exc=...)` con backoff 60s,
   max 3 tentativi. Dopo `MaxRetriesExceededError`: return False
   (loggato da Celery come task FAIL).

**Privacy/logging:**
- I log emettono solo `lead_id` (PK numerico) + classe
  dell'errore. Mai email, telefono, message, ip, user_agent.
- Lo scrubber Sentry del pass 3 redarebbe comunque eventuali leak
  in `request.body` / breadcrumbs.

**Idempotency note:**
- Il task è idempotente solo a livello di "best-effort": multipli
  retry possono inviare la stessa email N volte allo Studio.
  Preferiamo questo al silent loss. Per idempotency forte (es. una
  sola mail per `lead.public_id`) servirà una idempotency key in
  Redis o in DB — vedi §10.4.

---

## 5. Integrazione contact view

In `apps/crm/views.py`:

```python
def _dispatch_lead_notification(lead, *, request) -> None:
    use_async = getattr(settings, "LEAD_NOTIFICATION_ASYNC_ENABLED", False)
    if use_async:
        try:
            from .tasks import send_lead_notification_task
            send_lead_notification_task.delay(lead.pk)
            return
        except Exception as exc:
            logger.warning(
                "crm.lead.notification.delay_failed pk=%s error=%s — fallback sync",
                lead.pk, exc.__class__.__name__,
            )
    # Sync path (default o fallback)
    try:
        send_lead_notification(lead, request=request)
    except Exception as exc:
        logger.warning(
            "crm.lead.notification.sync_failed pk=%s error=%s",
            lead.pk, exc.__class__.__name__,
        )
```

**Garanzie:**
1. Il `redirect(reverse("crm:contact_thank_you"))` viene **sempre**
   raggiunto post-creazione Lead. Né Celery né SMTP possono
   romperlo.
2. Il Lead resta in DB anche in presenza di errori sull'email
   (la transazione `create_lead_from_form` chiude prima del
   dispatch).
3. Il fallback sync→broker-down preserva il behaviour del
   pass 2 in caso di disastro infrastrutturale.

**Lazy import** della tasks module: il path sync resta totalmente
indipendente da Celery. Un dev che non usa Celery in locale può
operare senza neanche importare il modulo.

---

## 6. Docker compose locale — servizio `celery-worker`

Aggiunto a `docker-compose.local.yml`:

```yaml
celery-worker:
  build:
    context: .
    dockerfile: Dockerfile
  image: badrane-legaltech:local
  depends_on:
    db: { condition: service_healthy }
    redis: { condition: service_healthy }
  environment:
    DATABASE_URL: ${DATABASE_URL:-postgres://...}
    REDIS_URL: ${REDIS_URL:-redis://redis:6379/0}
    CELERY_BROKER_URL: ${CELERY_BROKER_URL:-redis://redis:6379/0}
    LEAD_NOTIFICATION_ENABLED: ${LEAD_NOTIFICATION_ENABLED:-False}
    LEAD_NOTIFICATION_TO_EMAILS: ${LEAD_NOTIFICATION_TO_EMAILS:-}
    LEAD_NOTIFICATION_ASYNC_ENABLED: ${LEAD_NOTIFICATION_ASYNC_ENABLED:-False}
    SENTRY_DSN: ${SENTRY_DSN:-}
  volumes:
    - .:/app
    - media_local_data:/app/media
  command: celery -A config worker -l INFO --concurrency 2
```

**Note:**
- Stessa immagine `badrane-legaltech:local` del web (same Dockerfile).
- Stessi bind mount per hot reload del codice.
- `--concurrency 2` ragionevole per dev (2 task paralleli). Prod
  scalerà al numero vCPU.
- Il worker NON riceve messaggi finché
  `LEAD_NOTIFICATION_ASYNC_ENABLED=False`: è un rehearsal del
  setup prod.

Per testare end-to-end:

```bash
# 1. Modifica .env.local.docker:
#    LEAD_NOTIFICATION_ENABLED=True
#    LEAD_NOTIFICATION_TO_EMAILS=studio@example.test
#    LEAD_NOTIFICATION_ASYNC_ENABLED=True
# 2. Restart:
./scripts/local/down.sh && ./scripts/local/up.sh
# 3. Submit /contact/ form (browser).
# 4. Tail worker logs:
docker compose -f docker-compose.local.yml logs -f celery-worker
```

---

## 7. Privacy / logging

Coerente con il pass 3 (Sentry scrubber):

| Campo | Loggato dal task? | Note |
|---|---|---|
| `lead.pk` | ✅ Sì | PK numerico interno, non PII |
| `lead.public_id` | ✅ Già loggato dal pass 2 send | UUID, non PII |
| `lead.email` / `phone` / `name` | ❌ Mai | Privacy minimization |
| `lead.message` | ❌ Mai | Body utente PII |
| `lead.ip_address` / `user_agent` / `session_key` | ❌ Mai | Pass 2 + 3 |
| Eccezioni | ✅ Solo `error.__class__.__name__` | Mai stack trace con valori |

Sentry (pass 3) riceverà eventuali eccezioni del task ma il
`scrub_sentry_event` redige automaticamente i campi sensibili.

---

## 8. Flusso sync vs async (riassunto)

```
┌────────────────────────────────────────────────────────────────┐
│ POST /contact/                                                 │
└──────────────────────┬─────────────────────────────────────────┘
                       │
                       ▼
              ┌────────────────────┐
              │ rate-limit (pass 1)│
              └──────────┬─────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ form.is_valid()    │───┐ no
              └──────────┬─────────┘   ▼ render form
                         │ yes
                         ▼
              ┌────────────────────┐
              │ honeypot check     │───┐ bot
              └──────────┬─────────┘   ▼ redirect
                         │
                         ▼
              ┌────────────────────┐
              │ create_lead_from_   │
              │ form() (atomic)    │
              └──────────┬─────────┘
                         │ Lead committed
                         ▼
              ┌────────────────────────────────┐
              │ _dispatch_lead_notification()  │
              ├────────────────────────────────┤
              │ if ASYNC_ENABLED:              │
              │   try: task.delay(lead.pk)     │
              │   except: fall through to sync │
              │                                │
              │ # sync path                    │
              │ try: send_lead_notification()  │
              │ except: log + swallow          │
              └──────────┬─────────────────────┘
                         │
                         ▼
              ┌────────────────────┐
              │ redirect thank-you │  (sempre raggiunto)
              └────────────────────┘
```

---

## 9. Test aggiunti (9, tutti passati)

`apps/crm/test_celery_tasks.py`:
1. `test_celery_app_is_importable` — `from config.celery import
   app` senza eccezioni.
2. `test_task_returns_false_when_lead_does_not_exist` — task con
   `lead_id=999999` ritorna False, niente email, log warning.
3. `test_task_in_eager_mode_sends_email` — `CELERY_TASK_ALWAYS_EAGER=True`
   + lead reale → email in `mail.outbox`.
4. `test_contact_post_sync_path_sends_email` — flag async OFF,
   `mail.outbox` ha 1 email post-POST.
5. `test_contact_post_async_path_calls_delay` — flag async ON,
   `delay()` chiamato (mock), Lead creato, sync NON triggered.
6. `test_contact_post_async_delay_exception_falls_back_to_sync` —
   mock `delay()` solleva `RuntimeError("broker down")`, redirect
   thank-you avviene comunque, Lead resta, fallback sync invia
   email.
7. `test_compose_local_includes_celery_worker_service` — file
   compose contiene `celery-worker:` + `command: celery -A config
   worker`.
8. `test_pass7_doc_contains_required_sentinels` — doc cita
   `Celery`, `Redis`, `fallback`, `LEAD_NOTIFICATION_ASYNC_ENABLED`.
9. `test_italy_smoke_run_simulation_35_10_0` — smoke contract IT
   35/10/0 → `26268` / `27353` / `28439` EUR (canarino di
   regressione: nessun cambio in calculator engine causato dal
   pass 7).

Niente broker reale richiesto: i test usano `EAGER` mode + mock
di `delay()` per simulare il path async.

---

## 10. Cosa resta per produzione

### 10.1 Celery Beat (scheduler)
Non necessario oggi (nessun task ricorrente). Sarà necessario
quando aggiungeremo:
- Cleanup retention GDPR (cancellazione Lead/ConsentRecord scaduti).
- Audit periodico fonti legali (notifica scadenza `valid_to`).
- Health check approfondito DB/cache + alert.

### 10.2 Monitoring queue
- **Flower** UI (`pip install flower; celery -A config flower`).
- **Prometheus** exporter per metriche queue length, task
  duration, fail rate.
- Alert su:
  - queue length > soglia (broker congestionato);
  - fail rate > 5%/h (provider SMTP down);
  - task duration p95 > 30s (lentezza SMTP).

### 10.3 Retry policy fine
Oggi: 3 retry, backoff fisso 60s. Per produzione:
- Backoff esponenziale (`2 ** retries * base`).
- Jitter per evitare thundering herd.
- Distinguere errori transient (timeout, 5xx) da permanenti (4xx
  email rejected): no retry sui permanenti.

### 10.4 Idempotency keys
Oggi: best-effort. Multiple delivery possibili in caso di retry.
Per idempotency forte:
- Cache key `lead_notif:sent:{lead.public_id}` in Redis con TTL
  24h: il task verifica la chiave, salta se presente.
- Oppure flag DB `Lead.notification_sent_at` settato post-send.

### 10.5 Dead-letter / failed task tracking
- Dead-letter exchange RabbitMQ se si passa a Rabbit.
- Con Redis broker, usare un task `on_failure` callback che salva
  task ID + payload + traceback in una tabella DB
  (`FailedLeadNotification`).
- Sentry (pass 3) cattura già eccezioni del task ma manca
  l'aggregato per replay manuale.

### 10.6 Worker concurrency tuning
- `--concurrency=4` o `--concurrency={vCPU}` in prod.
- `--prefetch-multiplier=1` per evitare hoarding di task lenti.
- `--max-tasks-per-child=100` per workaround memory leak.

---

## 11. Validazione

```bash
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

---

## 12. Disclaimer

Questo iter aggiunge un'infrastruttura async opt-in. Non altera
dati legali, calcoli, o l'output del calcolatore Italia. Lo
Studio decide quando attivare il flusso async configurando
`LEAD_NOTIFICATION_ASYNC_ENABLED=True` + popolando
`LEAD_NOTIFICATION_TO_EMAILS`. Il disclaimer obbligatorio
CLAUDE.md sulle simulazioni indicative resta valido.
