# CRM INTEGRATION PLAN — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Audience:** dev, integrator (n8n / CRM esterno), Studio (referente
operativo lead).
**Scopo:** definire come i Lead generati dalla piattaforma vengono
sincronizzati verso sistemi esterni (n8n / CRM Studio / WhatsApp /
email pipeline) in modo **sicuro, idempotente, auditato**.

> Stato attuale: il `Lead` viene creato in DB e una **email
> transazionale** è inviata allo Studio. **Nessuna** integrazione
> webhook / CRM / WhatsApp è oggi attiva. Questo documento progetta
> il prossimo passo, **senza implementarlo**.

---

## 0. Stato attuale (verificato nel codice)

| Componente | Stato | File |
|---|---|---|
| Modello `crm.Lead` con FK a `Simulation`, `Consent`, `Country`, ecc. | ✅ implementato | `apps/crm/models.py` |
| `crm.LeadEvent` append-only (lifecycle) | ✅ implementato | `apps/crm/models.py:174-216` |
| Form pubblico `/contact/` con honeypot + privacy checkbox | ✅ implementato | `apps/crm/views.py`, `apps/crm/forms.py` |
| Service `create_lead_from_form` (transazionale) | ✅ implementato | `apps/crm/services.py:53-131` |
| Email transazionale plaintext sync | ✅ implementato | `apps/crm/email_notifications.py` |
| Celery task async `send_lead_notification_task` (3 retry, backoff 60s) | ✅ implementato | `apps/crm/tasks.py` |
| Fallback sync se Redis down | ✅ implementato | `apps/crm/views.py:31-70` (`_dispatch_lead_notification`) |
| Audit `PrivacyAuditEvent(CONSENT_GIVEN)` per ogni lead | ✅ | `apps/crm/services.py:117-123` |
| Webhook firmato verso CRM esterno | ❌ assente | — |
| Integrazione n8n | ❌ assente | — |
| Integrazione WhatsApp Business | ❌ assente | — |
| API REST `/api/leads/` per pull esterno | ❌ assente (DRF è installato ma non esposto per `Lead`) | — |
| Idempotency-key in webhook | ❌ assente | — |
| Audit log invio webhook | ❌ assente | — |
| Dashboard/admin filtri lead | 🟡 parziale (Django admin standard) | `apps/crm/admin.py` |

Campi `Lead.utm_source`, `utm_medium`, `utm_campaign` sono già nel
modello ma il form pubblico non li popola: vanno passati via
querystring (`?utm_source=...&utm_medium=...`) e raccolti dalla view.

---

## 1. Obiettivi dell'integrazione

1. **Notificare lo Studio** in tempo reale di ogni nuovo lead (oggi:
   sì via email). Estendere a:
   - n8n workflow (per orchestrare azioni: assegnazione automatica,
     SLA tracking, escalation);
   - CRM esterno (HubSpot / Pipedrive / Bitrix / Folderly Studio
     interno — DA DEFINIRE STUDIO);
   - canale WhatsApp Business per il lead (se ha dato consenso e
     ha lasciato un numero);
2. **Mantenere il DB locale come source-of-truth**: nessuna lead
   resta solo nel CRM esterno. Il DB Django è il libro mastro.
3. **Resilienza**: se l'integrazione esterna è giù, il lead resta
   comunque salvato e si invia con retry. Mai perdere un lead per
   un'integrazione down.
4. **Audit completo**: ogni invio webhook è tracciato (riuscito o
   fallito) con timestamp, retry count, ultimo errore.
5. **Privacy**: il payload webhook contiene solo i dati necessari, mai
   IP/UA/session-key. HTTPS sempre. Firma HMAC obbligatoria.
6. **Idempotenza**: se lo stesso lead viene inviato N volte (retry,
   replay), il CRM esterno deve riconoscerlo come già ricevuto.

---

## 2. Architettura proposta

### 2.1 Diagramma logico

```
[Utente] → POST /contact/
              ↓
         [ContactForm validate]
              ↓
         [create_lead_from_form] (atomic transaction)
            ├── Lead row
            ├── LeadEvent(CREATED)
            ├── ConsentRecord
            └── PrivacyAuditEvent
              ↓
         [_dispatch_lead_notification]
            ├── EMAIL → SMTP Studio (sync o Celery async)
            ├── WEBHOOK → n8n / CRM (Celery async, NEW)
            └── WHATSAPP → WhatsApp Business API (Celery async, NEW)
              ↓
         [redirect /contact/thank-you/]
```

### 2.2 Modelli nuovi

Per gestire webhook e audit:

```python
# apps/crm/models.py — addition (DA SCRIVERE)

class LeadWebhookDelivery(models.Model):
    """
    Tentativo di consegna di un Lead a un endpoint esterno (webhook).
    Append-only. Una riga per ogni tentativo, retry inclusi.
    """

    class Endpoint(models.TextChoices):
        N8N = "n8n", _("n8n workflow")
        CRM = "crm", _("External CRM")
        WHATSAPP = "whatsapp", _("WhatsApp Business")

    class Status(models.TextChoices):
        PENDING = "pending", _("Pending")
        SUCCESS = "success", _("Success")
        FAILED = "failed", _("Failed")
        SKIPPED = "skipped", _("Skipped (disabled)")
        EXHAUSTED = "exhausted", _("Retries exhausted")

    lead = models.ForeignKey(Lead, on_delete=models.CASCADE,
                              related_name="webhook_deliveries")
    endpoint = models.CharField(max_length=16, choices=Endpoint.choices,
                                 db_index=True)
    idempotency_key = models.CharField(max_length=64, db_index=True,
                                        unique=True)
    status = models.CharField(max_length=16, choices=Status.choices,
                               default=Status.PENDING, db_index=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    target_url_hash = models.CharField(max_length=64)  # SHA256 dell'URL
                                                       # (per audit
                                                       # senza esporlo)
    request_payload_hash = models.CharField(max_length=64)
    last_response_status = models.PositiveSmallIntegerField(null=True,
                                                             blank=True)
    last_response_body_excerpt = models.CharField(max_length=512,
                                                    blank=True)
    last_error_class = models.CharField(max_length=128, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
```

> Volutamente **niente** payload raw nel DB: solo hash. Il payload
> contiene PII che non vogliamo duplicare nel DB.

### 2.3 Settings nuovi (`config/settings.py`)

```python
# CRM webhook integration (F-crm-webhook-integration-pass1, DA SCRIVERE)
CRM_WEBHOOK_ENABLED = env.bool("CRM_WEBHOOK_ENABLED", default=False)
CRM_WEBHOOK_URL = env("CRM_WEBHOOK_URL", default="")
CRM_WEBHOOK_HMAC_SECRET = env("CRM_WEBHOOK_HMAC_SECRET", default="")
CRM_WEBHOOK_TIMEOUT_SECONDS = env.int("CRM_WEBHOOK_TIMEOUT_SECONDS",
                                        default=10)
CRM_WEBHOOK_MAX_RETRIES = env.int("CRM_WEBHOOK_MAX_RETRIES", default=5)

N8N_WEBHOOK_ENABLED = env.bool("N8N_WEBHOOK_ENABLED", default=False)
N8N_WEBHOOK_URL = env("N8N_WEBHOOK_URL", default="")
N8N_WEBHOOK_HMAC_SECRET = env("N8N_WEBHOOK_HMAC_SECRET", default="")

WHATSAPP_NOTIFY_ENABLED = env.bool("WHATSAPP_NOTIFY_ENABLED", default=False)
WHATSAPP_BUSINESS_API_URL = env("WHATSAPP_BUSINESS_API_URL", default="")
WHATSAPP_BUSINESS_API_TOKEN = env("WHATSAPP_BUSINESS_API_TOKEN", default="")
```

Tutti **opt-in** con default `False`. Senza env var, niente succede.
Stesso pattern di `LEAD_NOTIFICATION_ASYNC_ENABLED` esistente.

---

## 3. Webhook firmato — protocollo

### 3.1 Contratto

`POST <CRM_WEBHOOK_URL>`

**Headers (obbligatori):**

| Header | Valore | Note |
|---|---|---|
| `Content-Type` | `application/json; charset=utf-8` | |
| `X-Badrane-Signature` | `sha256=<hex>` | HMAC-SHA256 del raw body con `CRM_WEBHOOK_HMAC_SECRET`, prefisso `sha256=` (compatibile con GitHub/Stripe convention). |
| `X-Badrane-Idempotency-Key` | UUID v4 | Stesso lead → stessa key per ogni retry. Il consumer deve dedupare. |
| `X-Badrane-Event-Type` | `lead.created` o `lead.updated` | |
| `X-Badrane-Event-Id` | UUID v4 unico per ciascun delivery | Diverso da idempotency-key: cambia ad ogni retry. |
| `X-Badrane-Source` | `simulatore.studiolegalebadrane.it` | |
| `X-Badrane-Sent-At` | ISO-8601 UTC timestamp | |
| `User-Agent` | `BadraneLegalTech-Webhook/1.0 (+url)` | |

**Body (esempio `lead.created`):**

```json
{
  "event_type": "lead.created",
  "event_id": "5f9c2a7e-8e6f-4a2c-9b0e-3a1d6b4f1c20",
  "idempotency_key": "lead-7b3e9c12-2f4a-4d80-9f1c-04bd3a92a7c0",
  "occurred_at": "2026-05-10T14:23:11Z",
  "source": "simulatore.studiolegalebadrane.it",
  "lead": {
    "public_id": "7b3e9c12-2f4a-4d80-9f1c-04bd3a92a7c0",
    "status": "received",
    "priority": "normal",
    "received_at": "2026-05-10T14:23:11Z",
    "preferred_language": "it",
    "country_code": "IT",
    "case_type": "road_accident_bodily_injury",
    "contact": {
      "first_name": "Mario",
      "last_name": "Rossi",
      "email": "mario.rossi@example.com",
      "phone_number": "+39 333 1234567"
    },
    "message_excerpt": "Salve, ho avuto un incidente in autostrada A4 il 15…",
    "message_excerpt_max_chars": 280,
    "simulation": {
      "public_id": "9a8b7c6d-…",
      "status": "calculated",
      "country_code": "IT",
      "case_type": "road_accident_bodily_injury",
      "result_summary": {
        "estimated_min": "26268.00",
        "estimated_mid": "27353.00",
        "estimated_max": "28439.00",
        "currency": "EUR",
        "confidence": "medium"
      }
    },
    "utm": {
      "source": "google",
      "medium": "cpc",
      "campaign": "rca-italia-2026"
    },
    "consent": {
      "purpose": "lead_contact",
      "accepted_at": "2026-05-10T14:23:10Z",
      "text_version_id": 17,
      "language": "it"
    }
  }
}
```

**Cosa NON è nel payload (privacy by design):**

- `ip_address`, `user_agent`, `session_key`;
- messaggio completo (solo excerpt 280 char + flag truncated);
- `internal_notes`;
- `consent_record.id` raw (solo `text_version_id` per ricostruire);
- token CSRF, cookie, header autenticativi;
- struttura DB interna (PK numerici).

### 3.2 Verifica firma lato consumer

Pseudocodice (Node.js / Python):

```python
import hmac, hashlib
def verify(raw_body: bytes, header_signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), raw_body,
                         hashlib.sha256).hexdigest()
    received = header_signature.split("=", 1)[1]
    return hmac.compare_digest(expected, received)
```

n8n ha un nodo dedicato "HMAC verify" o lo si può fare con un Function
node.

### 3.3 Risposta consumer

| HTTP status | Significato | Azione mittente |
|---|---|---|
| `200` / `201` / `202` / `204` | Success | Marca delivery `success`, completed |
| `400` | Bad request (firma errata, schema invalido) | NO retry. Marca `failed`, alert Sentry, log. |
| `401` / `403` | Unauthorized | NO retry. Probabile secret rotato male. Alert urgente. |
| `404` | Endpoint non esiste | NO retry. Marca `failed`, alert Sentry. |
| `409` | Conflict / duplicate | OK (idempotency-key già visto). Marca `success`. |
| `429` | Rate-limited | Retry con backoff esponenziale (Retry-After). |
| `500` / `502` / `503` / `504` | Server error / temporaneo | Retry. |
| timeout (>10 s) | Network | Retry. |

### 3.4 Retry policy

Backoff esponenziale: 60 s, 120 s, 300 s, 600 s, 1800 s. Massimo
5 tentativi (`CRM_WEBHOOK_MAX_RETRIES=5`). Implementato come
Celery task con `self.retry()` e `default_retry_delay=60`,
`max_retries=5`, custom `retry_jitter`.

Dopo l'ultimo tentativo: `LeadWebhookDelivery.status=exhausted`,
alert Sentry + `StaffSecurityAlert` (riusare il pattern esistente
`compliance.StaffSecurityAlert` con un nuovo `AlertType.CRM_WEBHOOK_EXHAUSTED`).

### 3.5 Idempotency-key

Formato: `lead-<lead.public_id>` per `lead.created`. Per
`lead.updated` (futuro): `lead-<public_id>-<status>-<updated_at_unix>`.

Il consumer (n8n / CRM) **deve** mantenere uno store delle
idempotency-key viste e rispondere `409 Conflict` o `200` con corpo
`{"status": "duplicate"}` se già processata.

---

## 4. Integrazione n8n (consigliata come "smistatore")

### 4.1 Perché n8n

n8n è low-code, self-hostable in UE (privacy-friendly),
estensibile, free per piccoli volumi. Piuttosto che integrare
direttamente con N CRM diversi, integriamo con n8n una sola volta;
n8n smista poi al CRM Studio (HubSpot / Pipedrive / interno) +
WhatsApp + Slack interno + Google Sheets di backup, ecc.

### 4.2 Workflow tipico

```
[Webhook trigger /badrane-lead]
       ↓
[Verify HMAC signature]
       ↓
[Switch by lead.country_code]
       ├── IT → [HubSpot create Contact] → [Slack #leads-it message]
       ├── FR → [Pipedrive create Deal] → [Email to Avv.X@studio]
       ├── BE → idem
       ├── MA/TN → [Email avv. North-Africa@studio]
       └── _ → [Slack #leads-other]
       ↓
[Branch: phone_number present AND consent.whatsapp_optional]
       ├── YES → [WhatsApp Business send template "Acknowledge"]
       └── NO  → skip
       ↓
[Log audit: Google Sheets append (backup)]
       ↓
[Respond 200]
```

### 4.3 Setup n8n self-hosted

- container Docker accanto al simulatore (stesso compose o
  compose dedicato);
- DB: PostgreSQL (può essere lo stesso Postgres del simulatore con
  schema dedicato `n8n_*`);
- HTTPS via reverse proxy (Caddy / nginx);
- backup giornaliero degli workflow JSON in repo separato
  privato dello Studio;
- `N8N_BASIC_AUTH_USER` / `N8N_BASIC_AUTH_PASSWORD` o SSO Studio.

### 4.4 Vincoli GDPR

- n8n self-hostato in UE → no trasferimento extra-UE;
- secret HMAC condiviso solo tra simulatore e n8n; il CRM esterno
  vede solo l'output mappato di n8n (eventualmente con altri
  segreti separati);
- log n8n vanno auditati: niente log in chiaro di message body
  o phone numbers.

---

## 5. Integrazione WhatsApp Business (opzionale, P2)

### 5.1 Vincoli

- Solo se l'utente ha lasciato un numero **e** ha dato consenso
  esplicito al canale WhatsApp;
- WhatsApp Business API richiede approvazione Meta + numero
  business verificato + template pre-approvati;
- Costo per template-message (la prima ora dopo che il cliente
  scrive è gratuita; dopo si paga per "conversation").

### 5.2 Pattern d'uso suggerito

L'utente compila `/contact/` → riceve **prima** una conferma email +
**poi** (se opt-in WhatsApp) un messaggio WhatsApp template
"Acknowledge" del tipo:

> *"Salve {first_name}, abbiamo ricevuto la sua richiesta (rif.
> {public_id_short}). Un avvocato dello Studio le risponderà entro
> 3-5 giorni lavorativi. Per urgenze, risponda a questo messaggio.
> Studio Legale Internazionale Badrane."*

### 5.3 Modifiche richieste al form

Aggiungere campo opt-in:

```python
# apps/crm/forms.py — addition
whatsapp_optin = forms.BooleanField(
    label=_("I agree to receive an acknowledgment via WhatsApp at the number above (optional)."),
    required=False,
)
```

E corrispondente `ConsentPurpose.code=whatsapp_acknowledge` con
versionamento testo per lingua.

### 5.4 Vincoli deontologici

Vedi `LEGAL_COMPLIANCE_CONTENT_AUDIT.md`. WhatsApp è un canale
asincrono accettabile per acknowledge transazionale, **non** per
prima consulenza legale (dovrebbe essere una telefonata o video
con identità verificata). Il template message va firmato dallo
Studio.

---

## 6. CRM esterno — opzioni

### 6.1 Opzioni evaluate

| CRM | Pro | Contro | Nota privacy |
|---|---|---|---|
| **HubSpot** | API ricche, free tier, integrazione email | Trasferimento extra-UE (US) → SCC + DPIA | Privacy vincolante |
| **Pipedrive** | UI semplice, sales pipeline, free tier limitato | Trasferimento extra-UE | SCC + DPIA |
| **Salesforce** | Enterprise, costoso | Overkill per lo Studio | Tier alto |
| **Bitrix24** | All-in-one | Russo (KZ host EU disponibile ma valuta) | Verificare host |
| **EspoCRM** | Self-hosted, open source, free | Servirebbe ops | EU-friendly |
| **SuiteCRM** | Self-hosted, open source | Idem EspoCRM | EU-friendly |
| **Folderly / interno Studio** | Massima privacy | Servirebbe sviluppo custom | Best-case privacy |
| **Solo n8n + email** | Zero CRM esterno; n8n smista a email + Sheets | Manca pipeline visiva | Privacy massima |

> **Decisione DA VALIDARE STUDIO**: quale CRM? Il documento di
> integrazione assume "n8n + qualcosa": se l'opzione è "solo email",
> n8n può comunque arricchire (assegnazione automatica, SLA,
> escalation), e il CRM è il file system + Django admin.

### 6.2 Mapping `Lead` → CRM esterno (esempio HubSpot)

Se HubSpot:

| Campo `Lead` | HubSpot Contact property |
|---|---|
| `email` | `email` |
| `first_name` | `firstname` |
| `last_name` | `lastname` |
| `phone_number` | `phone` |
| `preferred_language` | `hs_language` |
| `country.code` | `hs_country_code` |
| `case_type` | custom property `case_type` (string) |
| `simulation.public_id` | custom property `simulation_id` |
| `utm_source/medium/campaign` | `hs_analytics_source*` |
| `priority` | custom property `lead_priority` |
| `status` | `hs_lifecyclestage` (mapping: received→subscriber, contacted→lead, qualified→marketingqualifiedlead, converted→customer) |
| `public_id` | custom property `badrane_lead_id` (chiave esterna) |

Nota: il mapping è **solo se HubSpot è scelto**. Il pattern reale
deve essere fatto in n8n, non nel codice Django, così il simulatore
resta agnostico.

---

## 7. Reverse webhook — il CRM aggiorna il `Lead` Django

> 🟡 P2 — **da decidere se serve**.

Se lo Studio aggiorna lo status del Lead nel CRM (es. da `received`
a `contacted`), può essere utile sincronizzare il Django DB.

### 7.1 Endpoint Django proposto

`POST /api/v1/leads/<public_id>/events/`

- autenticazione: HMAC firma su body (stesso pattern outbound) +
  IP whitelist (lo Studio IP fisso o range n8n);
- rate limit dedicato;
- body:
  ```json
  {
    "event_type": "contacted",
    "event_id": "<uuid>",
    "occurred_at": "2026-05-10T15:00:00Z",
    "metadata": {"channel": "phone", "agent": "Avv.X"}
  }
  ```
- crea `LeadEvent(event_type=contacted)` + aggiorna
  `Lead.status` + `Lead.contacted_at`;
- audit `PrivacyAuditEvent`.

### 7.2 Decisione

> **Azione DA VALIDARE STUDIO**: serve la sincronizzazione bidirezionale
> oppure il CRM esterno è la "verità" post-handoff e il Django DB
> resta congelato a `status=received`?
>
> Raccomandazione: **non** sincronizzare bidirezionalmente nel MVP.
> Lo Studio gestisce il ciclo nel CRM. Il Django DB resta per
> audit / GDPR / report. Riduce complessità.

---

## 8. Privacy e GDPR

### 8.1 Base giuridica

Trasferimento Lead → CRM esterno: **legittimo interesse** (art.
6.1.f GDPR) o **esecuzione precontrattuale** (art. 6.1.b), purché:

- l'utente sia stato informato nella **privacy policy** (oggi
  assente; vedi `LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 2.5);
- il CRM esterno sia **DPA-compliant** (Data Processor Agreement
  firmato);
- se extra-UE: **SCC** (Standard Contractual Clauses) + DPIA
  (Data Protection Impact Assessment).

### 8.2 Privacy policy update richiesto

Aggiungere alla privacy:

> *"I tuoi dati di contatto vengono trasmessi a sistemi di gestione
> CRM operati per conto dello Studio. Allo stato attuale utilizziamo:
> [n8n self-hosted EU], [CRM XX, host EU/EEA, DPA firmato il
> {data}]. Non utilizziamo strumenti che effettuano trasferimenti di
> dati al di fuori dello Spazio Economico Europeo, salvo previa
> firma di Standard Contractual Clauses (SCC) e DPIA."*

### 8.3 Diritto alla cancellazione (art. 17 GDPR)

Quando un `DataDeletionRequest` viene processato (oggi: workflow
manuale in admin), il sistema deve:

1. cancellare/anonimizzare il `Lead` Django;
2. **propagare** la cancellazione al CRM esterno via webhook
   `lead.deleted`:
   ```json
   {"event_type": "lead.deleted",
    "lead": {"public_id": "...", "deleted_at": "..."}}
   ```
3. il CRM esterno cancella anche il suo record;
4. l'evento è registrato in `PrivacyAuditEvent`.

> **Azione**: aggiungere all'`apps.compliance.services` (futuro pass)
> il dispatcher che propaga la deletion ai webhook.

---

## 9. Implementazione step-by-step (proposta `F-crm-webhook-pass1`)

> Non implementare in questo audit. Solo pianificazione.

### Step 1 — Modello + migration

- aggiungere `LeadWebhookDelivery` a `apps/crm/models.py`;
- migration generata e committata;
- `apps/crm/admin.py` registra il modello come read-only.

### Step 2 — Settings + env example

- aggiungere `CRM_WEBHOOK_*`, `N8N_WEBHOOK_*` a `config/settings.py`;
- aggiungere a `.env.example` con commenti;
- Django system check che fa fail di `manage.py check` se in prod
  `CRM_WEBHOOK_ENABLED=True` ma `CRM_WEBHOOK_HMAC_SECRET=""` o
  `CRM_WEBHOOK_URL` non https.

### Step 3 — Service layer

- nuovo `apps/crm/webhook_dispatcher.py`:
  - `build_lead_payload(lead) -> dict` (privacy-minimized);
  - `sign_payload(payload_bytes, secret) -> str`;
  - `dispatch_lead_webhook(lead, endpoint='crm')` → crea
    `LeadWebhookDelivery(status=pending)` e enqueue Celery task.

### Step 4 — Celery task

- `apps/crm/tasks.py`: aggiungere `send_lead_webhook_task(delivery_id)`
  con retry esponenziale (5 attempt, jitter, backoff base 60s);
- aggiornare `LeadWebhookDelivery` ad ogni attempt;
- emettere `StaffSecurityAlert` su `exhausted`.

### Step 5 — Hook nel funnel

- `apps/crm/views.py::_dispatch_lead_notification`: chiamare anche
  `dispatch_lead_webhook(lead)` dopo l'email.

### Step 6 — Test

- pytest:
  - dispatch payload privacy-minimized (no IP, no UA, no
    message full);
  - HMAC firmato correttamente;
  - retry su 503;
  - no retry su 400 / 401;
  - `exhausted` dopo `max_retries` + alert generato;
  - idempotency-key stabile per lo stesso lead;
- mocked `requests.post` con `responses` library.

### Step 7 — Docs

- aggiornare `apps/crm/admin.py` con view filtrabile
  `LeadWebhookDelivery`;
- aggiornare `docs/architecture/CRM_WEBHOOK_INTEGRATION_PASS1.md`
  con runbook (es. "come ruotare il secret", "come vedere i
  delivery falliti").

### Step 8 — Manuale n8n

- file `docs/integrations/N8N_WORKFLOW_TEMPLATE.json` con il
  workflow esportato (sanitizzato, no secrets);
- runbook per importarlo in un'istanza n8n self-hostata.

### Step 9 — Browser/E2E test (post-deploy staging)

- compilare form `/contact/` con dati fittizi → verifica:
  - lead in DB;
  - email allo Studio (locmem in test);
  - delivery in `LeadWebhookDelivery` con status `success` (n8n
    test endpoint risponde 200);
  - log puliti, niente PII.

---

## 10. Tabella riassuntiva — bloccanti integrazione

| ID | Voce | Severità | Owner | Stato |
|---|---|---|---|---|
| P1-CRM-1 | `LeadWebhookDelivery` model + migration | P1 | dev | non iniziato |
| P1-CRM-2 | Webhook dispatcher firmato HMAC | P1 | dev | non iniziato |
| P1-CRM-3 | Celery task con retry 5×60s exp | P1 | dev | non iniziato |
| P1-CRM-4 | Idempotency-key stabile per delivery | P1 | dev | non iniziato |
| P1-CRM-5 | n8n workflow template + runbook | P1 | dev + Studio (host n8n) | non iniziato |
| P1-CRM-6 | Privacy policy aggiornata con elenco trasferimenti | P1 | Studio + dev | dipende da scelta CRM |
| P1-CRM-7 | DPA firmato con CRM esterno (se non self-hosted) | P1 | Studio | dipende da scelta CRM |
| P2-CRM-1 | WhatsApp Business template "Acknowledge" | P2 | Studio + dev | dipende da approvazione Meta |
| P2-CRM-2 | Reverse webhook `lead.updated` (CRM→Django) | P2 | dev | DA DECIDERE STUDIO |
| P2-CRM-3 | Propagazione `lead.deleted` ai webhook (GDPR art. 17) | P2 | dev | dipende da P1-CRM-* completato |
| P3-CRM-1 | Dashboard interna KPI lead/giorno (oggi `apps.analytics` placeholder) | P3 | dev | non iniziato |

---

## 11. Decisioni DA VALIDARE STUDIO prima dell'implementazione

1. **CRM target**: HubSpot / Pipedrive / EspoCRM / interno / solo
   n8n+email. Da scegliere: impatta DPA, costi, host UE/extra-UE,
   privacy.
2. **n8n hosting**: self-hosted UE accanto al simulatore, oppure
   istanza esterna (es. n8n.cloud)? Self-hosted è raccomandato
   per privacy.
3. **Sincronizzazione bidirezionale** (Sez. 7): SI o NO nel MVP?
4. **WhatsApp Business**: SI o NO nel MVP? Se SI, processo
   approvazione Meta deve partire ora (richiede 2-4 settimane).
5. **Lead routing per paese**: chi è il referente FR / BE / MA / TN
   nello Studio? Va definito per popolare il workflow n8n.
6. **SLA risposta**: oggi `/contact.html` dice "3-5 giorni
   lavorativi". Vuoi alert in n8n se un lead non viene `contacted`
   entro 5gg?
7. **Backup lead**: oltre a Django DB, vogliamo un backup giornaliero
   automatico in Google Sheets / S3 EU / SFTP Studio?

---

## 12. Per Claude Code che riprende

- **Mai** mandare PII (IP, UA, message body completo) al webhook
  esterno. Solo i campi minimi necessari + excerpt.
- **Mai** loggare il payload del webhook in chiaro.
- **Mai** committare `CRM_WEBHOOK_HMAC_SECRET` o token API.
- Ogni nuovo endpoint webhook (verso un nuovo CRM/sistema) richiede:
  1. nuovo `Endpoint` enum in `LeadWebhookDelivery`;
  2. settings env-driven separati;
  3. Django system check;
  4. test pytest con HMAC+retry;
  5. aggiornamento privacy policy.
- Quando si attiva un webhook in prod, monitorare la prima settimana:
  delivery success rate, latenza p95, alert su `exhausted`.
