# LOCAL — Product hardening, pass 2 — email lead notification

**Iter**: F-local-product-hardening-pass2-email-lead
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**

> Secondo passaggio di hardening: notifica email transazionale allo
> Studio quando arriva un nuovo Lead dal form pubblico `/contact/`.
> Nessun dato legale è stato modificato. Lo smoke contract Italia
> 35/10/0 → 26 268 / 27 353 / 28 439 EUR è verificato in CI.

---

## 1. Cosa è stato aggiunto

| Area | File | Tipo |
|---|---|---|
| Settings | `config/settings.py` | 4 settings env-driven (email + lead notification) |
| Service | `apps/crm/email_notifications.py` (nuovo) | `send_lead_notification(lead, *, request)` |
| Integrazione | `apps/crm/views.py` (`contact`) | chiamata post-creazione Lead, failure-soft |
| Test | `apps/crm/test_email_notifications.py` (nuovo) | 9 test |
| Docs | questo file | — |

Niente nuovi pacchetti pip. Niente modifiche a calculator, dataset,
formula, engine, wizard form, modelli legali.

---

## 2. Settings email aggiunti

In `config/settings.py`, sezione **Email — notifica transazionale Lead**:

| Setting | Default | Override env |
|---|---|---|
| `EMAIL_BACKEND` | `django.core.mail.backends.console.EmailBackend` se `DEBUG=True`, altrimenti `smtp.EmailBackend` | `DJANGO_EMAIL_BACKEND` |
| `DEFAULT_FROM_EMAIL` | `no-reply@badrane.local` | `DJANGO_DEFAULT_FROM_EMAIL` |
| `EMAIL_SUBJECT_PREFIX` | `[Badrane LegalTech] ` | `DJANGO_EMAIL_SUBJECT_PREFIX` |
| `LEAD_NOTIFICATION_ENABLED` | `True` | `LEAD_NOTIFICATION_ENABLED` |
| `LEAD_NOTIFICATION_TO_EMAILS` | `[]` (lista vuota → nessuna email) | `LEAD_NOTIFICATION_TO_EMAILS` (CSV) |

**Comportamento di default in dev**:
- Backend = `console`: ogni email viene stampata in stdout. Nessuna
  connessione SMTP richiesta.
- `LEAD_NOTIFICATION_TO_EMAILS=[]`: per default nessuna email viene
  inviata neppure in dev — bisogna popolare la lista via env per
  attivare il flusso.
- Effetto netto: il dev **non** è spammato; lo Studio configura una
  inbox sola tramite `.env` quando vuole testare.

**Per produzione (futuro pass 3 deploy):**
- Settare `DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend`.
- Settare `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
  `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS=True` via env.
- `LEAD_NOTIFICATION_TO_EMAILS=studio@studiolegalebadrane.it,segreteria@…`.

---

## 3. Servizio di notifica

**Modulo**: `apps/crm/email_notifications.py`.

**Funzione pubblica**: `send_lead_notification(lead, *, request=None) -> bool`.

**Comportamento:**
1. Se `LEAD_NOTIFICATION_ENABLED=False` → ritorna `False` senza
   chiamare SMTP.
2. Se `LEAD_NOTIFICATION_TO_EMAILS=[]` → ritorna `False` senza
   chiamare SMTP.
3. Altrimenti compone un messaggio plaintext, lo invia con
   `django.core.mail.send_mail(fail_silently=False)`, ritorna `True`.
4. Se `send_mail` solleva: cattura l'eccezione, logga `WARNING` con
   solo `public_id` + `error.__class__.__name__` (mai body, mai
   recipients), ritorna `False`.

**Subject:** `"[Badrane LegalTech] New legal review request"`.

**Body (plaintext):** include solo i campi necessari allo Studio:
- `Lead public_id`
- `Received at (UTC)` (`lead.created_at.isoformat()`)
- `Status` (di default `received`)
- `Name` (`first_name + last_name`)
- `Email`
- `Phone` (o `—` se vuoto)
- `Preferred language`
- `Country` (codice ISO o `—`)
- `Case type` (o `—`)
- `Linked simulation` (solo se presente)
- `Admin link` (URL relativo o assoluto se `request` disponibile)
- footer fisso: *"This is an automated transactional notification.
  Do not reply. Contact details are visible in the Studio admin only."*

---

## 4. Privacy minimization nel body

Sono **deliberatamente esclusi** dal body email:

| Campo modello `Lead` | Perché escluso |
|---|---|
| `ip_address` | Identificativo tecnico; rischio di leak in inbox condivise. Resta in admin. |
| `user_agent` | Stesso ragionamento. Resta in admin. |
| `session_key` | Token di sessione: non deve mai uscire dal sistema. Resta in admin. |
| `internal_notes` | Note Studio destinate al ledger interno, non alla notifica push. |
| `utm_*` | Marketing metadata: non utili per il triage del Lead. Resta in admin. |
| `consent_record` (testo) | Tracciato in admin via FK. Mostrare il testo del consenso in mail aumenta superficie GDPR. |

**Anche `lead.message`** (il testo libero del cliente) **non è
incluso**: contiene PII raw del visitatore (problema legale, dati
salute, ecc.). Lo Studio lo legge in admin tramite `Admin link`.

**Nel logging**: `_build_body()` non viene mai loggato. Su errore
si emette solo `crm.lead.notification.failed public_id=… error=…`
senza email, body, recipients.

---

## 5. Failure mode

**Scenari coperti dai test:**

| Scenario | Comportamento |
|---|---|
| `LEAD_NOTIFICATION_ENABLED=False` | `send_lead_notification` ritorna `False`, zero email, no log warning. |
| `LEAD_NOTIFICATION_TO_EMAILS=[]` | Idem. |
| Backend OK, recipient configurato | Email inviata, ritorna `True`, log INFO con public_id. |
| `send_mail` solleva (es. SMTP outage simulato) | Eccezione assorbita, log WARNING senza PII, ritorna `False`. **Lead resta creato**, view redirige comunque a `/contact/thank-you/`. |

**Garanzia critica**: il funnel utente NON si rompe per problemi
email. Il Lead è già committato (transazione `create_lead_from_form`
chiude PRIMA del `send_lead_notification`), quindi una send
fallita non viene rollback-ata e lo Studio può comunque vedere il
Lead in admin (pur non ricevendo la notifica push).

---

## 6. Integrazione con `/contact/`

In `apps/crm/views.py::contact`:

```python
lead = create_lead_from_form(
    form_kwargs=form.to_lead_kwargs(),
    simulation_public_id=...,
    request=request,
)
send_lead_notification(lead, request=request)
return redirect(reverse("crm:contact_thank_you"))
```

**Honeypot bot path** (`form.is_likely_bot`) **non** chiama
`send_lead_notification` — coerente con il fatto che il Lead non
viene neppure creato.

**Rate-limit** (pass 1): se il limite POST è raggiunto, la view non
viene eseguita affatto, quindi né `create_lead_from_form` né
`send_lead_notification` sono chiamate. Il rate-limit (cache-based)
e la notifica email sono indipendenti per disegno.

---

## 7. Test aggiunti (9)

In `apps/crm/test_email_notifications.py`, tutti con
`override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")`
per evitare invio reale. Inbox `django.core.mail.outbox` azzerata
da fixture autouse.

| # | Test | Verifica |
|---|---|---|
| 1 | `test_notification_disabled_returns_false_and_sends_nothing` | flag off → no email, ritorna False |
| 2 | `test_notification_empty_recipients_returns_false` | recipients vuoti → no email, ritorna False |
| 3 | `test_notification_enabled_sends_one_email_with_correct_subject` | subject prefisso + ricevuti corretti |
| 4 | `test_notification_body_contains_lead_public_id` | body ha public_id + nome + email |
| 5 | `test_notification_body_includes_simulation_public_id_when_present` | body ha simulation public_id se Lead linkato |
| 6 | `test_notification_body_omits_pii_metadata_fields` | NON contiene ip/UA/session/internal_notes |
| 7 | `test_contact_post_creates_lead_and_sends_email` | `/contact/` POST → Lead + email |
| 8 | `test_contact_post_email_failure_does_not_break_lead_creation` | `send_mail` solleva → Lead resta + thank-you |
| 9 | `test_italy_smoke_run_simulation_35_10_0` | smoke contract IT 26 268 / 27 353 / 28 439 |

---

## 8. Cosa resta per produzione

> Pass 2 copre la notifica funzionale. Per il deploy serve:

### 8.1 Provider SMTP / API
- **Postmark / Amazon SES / Mailgun / SendGrid**: scegliere
  provider transazionale con buona deliverability.
- **API key** in `.env` (mai in repo).
- **From-email reale** verificato dal provider (no
  `no-reply@badrane.local`).

### 8.2 Deliverability
- **SPF**: record TXT del dominio mittente che autorizza il
  provider.
- **DKIM**: chiave gestita dal provider.
- **DMARC**: politica `quarantine` o `reject` con report aggregati
  a un'inbox dedicata.
- **Domain warming**: per nuovi domini, partire da volumi bassi.

### 8.3 Async / coda
- **Celery + Redis**: oggi `send_lead_notification` è chiamato
  sincrono nel ciclo request/response. Una send lenta (1–2s) si
  somma al tempo risposta. In prod va spostato in task async:
  `send_lead_notification.delay(lead.pk)`.
- **Retry policy**: 3 tentativi con backoff esponenziale; al
  fallimento finale, il Lead resta in DB con `internal_notes`
  arricchito da `LeadEvent(type=NOTE, message="email retry exhausted")`.

### 8.4 Template
- Oggi è plaintext fisso. In prod può servire una versione HTML
  con branding Studio (logo, colori), pur restando testuale come
  fallback per client email che non rendono HTML.
- I18n: il body è in inglese (lingua interna Studio). Non serve
  tradurlo per gli avvisi allo Studio stesso.

### 8.5 Unsubscribe
- ❌ **Non necessario**: è un'email transazionale 1-to-1 verso
  destinatari interni dello Studio (operatori), non marketing
  verso utenti esterni. Le esenzioni transazionali GDPR/CAN-SPAM
  si applicano. Per le risposte automatiche all'utente
  (es. "abbiamo ricevuto la tua richiesta"), valuteremo
  separatamente — quello sì è marketing-adjacent.

### 8.6 Monitoring
- Metrica `lead_notification.sent` / `lead_notification.failed`
  via Sentry o Prometheus.
- Alert se più del 10% delle send fallisce in 1 ora.

---

## 9. Validazione

```bash
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

Tutti verdi al merge. Smoke contract IT 35/10/0 →
26 268 / 27 353 / 28 439 verificato dal test #9.

---

## 10. Disclaimer

Questo iter aggiunge solo una notifica funzionale operativa per
lo Studio. Non altera dati legali, calcoli, o l'output del
calcolatore Italia. Il disclaimer obbligatorio CLAUDE.md sulla
natura indicativa delle simulazioni resta valido.
