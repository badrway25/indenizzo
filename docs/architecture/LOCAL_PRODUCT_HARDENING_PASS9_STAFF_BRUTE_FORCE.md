# LOCAL — Product hardening, pass 9 — staff brute-force detector

**Iter**: F-local-product-hardening-pass9-staff-audit-brute-force-detector
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**
**Detection-only**: nessun blocco automatico, nessun lockout.

> Nono passaggio: detector di tentativi ripetuti di login admin
> falliti che produce `StaffSecurityAlert` consultabili in admin
> (e opzionalmente notificati via email). Funziona sopra
> `StaffAccessEvent` (pass 8). Privacy-first, fail-soft, mai
> blocca login. IT smoke 35/10/0 → 26 268 / 27 353 / 28 439 EUR
> verificato.

---

## 1. Cosa è stato aggiunto

| Area | File | Tipo |
|---|---|---|
| Settings | `config/settings.py` | 6 settings env-driven `STAFF_LOGIN_ALERT_*` |
| Model | `apps/compliance/models.py` | `StaffSecurityAlert` |
| Migration | `apps/compliance/migrations/0003_staffsecurityalert.py` | nuova |
| Service | `apps/compliance/staff_security.py` (nuovo) | detector + email opzionale |
| Signals | `apps/compliance/signals.py` | call `create_staff_security_alert_if_needed` post-`login_failed` |
| Admin | `apps/compliance/admin.py` | `StaffSecurityAlertAdmin` read-only |
| Test | `apps/compliance/test_staff_brute_force.py` | 11 test |
| Docs | questo file | — |

Niente nuove dipendenze. Niente touch a calculator/engine/wizard.

---

## 2. Cosa viene rilevato

Il detector è triggerato **dopo** ogni `StaffAccessEvent(event_type=login_failed)`
generato dai signals (pass 8). Conta nella finestra mobile gli
eventi che condividono **lo stesso** `username_hash` **OPPURE**
**lo stesso** `ip_address_masked` dell'evento appena registrato.

Se `count >= STAFF_LOGIN_ALERT_THRESHOLD` E non c'è già un alert
attivo (`cooldown_until > now`) per la stessa combinazione, viene
creato un `StaffSecurityAlert` con:

| Campo | Valore |
|---|---|
| `alert_type` | `admin_login_bruteforce` |
| `severity` | `medium` (oggi unica scelta) |
| `username_hash` | hash dell'evento trigger |
| `ip_address_masked` | IP mascherato dell'evento trigger |
| `event_count` | conteggio nella finestra |
| `window_seconds` | finestra usata per il calcolo |
| `cooldown_until` | now + `STAFF_LOGIN_ALERT_COOLDOWN_SECONDS` |
| `metadata` | `{"reason": "threshold_exceeded", "path": "/admin/login/", "trigger_event_id": <id>}` |

Pattern coperti:
- **Same user, multiple IPs** (account-targeted): `username_hash`
  costante, IP variabili → match per username.
- **Single IP, multiple users** (credential stuffing): IP
  costante, username variabili → match per IP.

---

## 3. Cosa NON viene fatto

**Detection-only**, by design:
- ❌ **Nessun blocco automatico** di utenti.
- ❌ **Nessun ban** di IP.
- ❌ **Nessun lockout** account.
- ❌ **Nessuna interferenza** col flow di autenticazione (`user_login_failed` continua a comportarsi come Django default).
- ❌ **Nessuna lockout policy formale** (vedi §10).

Il detector è un **canarino**: registra il pattern, lo rende
visibile in admin, opzionalmente avvisa lo Studio. La decisione
(bloccare? indagare? ignorare?) resta umana.

---

## 4. Settings

In `config/settings.py`, sezione **Staff brute-force detector**:

| Setting | Default | Override env |
|---|---|---|
| `STAFF_LOGIN_ALERTS_ENABLED` | `True` | `STAFF_LOGIN_ALERTS_ENABLED` |
| `STAFF_LOGIN_ALERT_WINDOW_SECONDS` | `900` (15 min) | `STAFF_LOGIN_ALERT_WINDOW_SECONDS` |
| `STAFF_LOGIN_ALERT_THRESHOLD` | `5` | `STAFF_LOGIN_ALERT_THRESHOLD` |
| `STAFF_LOGIN_ALERT_COOLDOWN_SECONDS` | `3600` (1 ora) | `STAFF_LOGIN_ALERT_COOLDOWN_SECONDS` |
| `STAFF_LOGIN_ALERT_EMAIL_ENABLED` | `False` | `STAFF_LOGIN_ALERT_EMAIL_ENABLED` |
| `STAFF_LOGIN_ALERT_TO_EMAILS` | `[]` | `STAFF_LOGIN_ALERT_TO_EMAILS` |

**Detection attiva di default**, **email disattivata di default**:
in dev gli alert vengono creati ma non inviati (lo Studio li
consulta in admin). Per attivare l'email transazionale: settare
sia `_EMAIL_ENABLED=True` sia popolare `_TO_EMAILS`.

---

## 5. Cooldown

`cooldown_until = now + STAFF_LOGIN_ALERT_COOLDOWN_SECONDS` viene
settato alla creazione dell'alert. Per la durata del cooldown,
nuovi tentativi falliti dello stesso `username_hash` o dello
stesso `ip_address_masked` **non** generano nuovi alert. Questo
evita:
- spam in admin durante un attacco prolungato;
- spam email allo Studio (anche se l'email è disabilitata di
  default).

Una volta scaduto il cooldown, il prossimo evento che supera
nuovamente la soglia genera un nuovo alert (un nuovo "round" di
attacco).

L'alert resta visibile in admin anche dopo la scadenza del
cooldown: è uno storico append-only.

---

## 6. Privacy / redaction

Coerente con il pass 8:

| Campo | Persistito? | Note |
|---|---|---|
| `username_hash` | ✅ SHA-256 troncato | Mai username in chiaro |
| `ip_address_masked` | ✅ es. `203.0.113.x` | Mai IP completo |
| `event_count` | ✅ intero | Aggregato non sensibile |
| `metadata.path` | ✅ `/admin/login/` | Path tecnico |
| Password | ❌ MAI | Non nei `StaffAccessEvent`, non negli alert |
| User-agent raw | ❌ MAI | Solo hash in `StaffAccessEvent` |
| Email utente | ❌ MAI | Mai correlata all'alert |

**Email body** (vedi §7) rispetta gli stessi principi: contiene
solo hash, IP mascherato, count, timestamp.

---

## 7. Email opzionale

Se `STAFF_LOGIN_ALERT_EMAIL_ENABLED=True` E
`STAFF_LOGIN_ALERT_TO_EMAILS != []`, dopo la creazione di un
alert viene inviata un'email plaintext minimale:

**Subject:** `[Badrane LegalTech] Admin login alert`
**From:** `DEFAULT_FROM_EMAIL` (settings)
**Body** (tutto già redatto):
- Alert id (PK numerico)
- alert_type, severity
- event_count, window_seconds
- username_hash, ip_address_masked
- triggered_at ISO + cooldown_until
- footer fisso "detection-only signal, no login was blocked"

**Failure-soft**: se `send_mail` solleva (SMTP outage), si logga
un warning senza PII e si ritorna False. **L'alert resta
creato** in DB anche se l'email fallisce.

---

## 8. Integrazione signals

In `apps/compliance/signals.py`:

```python
def _create_event(*, event_type, request, user, username):
    ...
    event = StaffAccessEvent.objects.create(**kwargs)
    if event_type == "login_failed":
        from .staff_security import create_staff_security_alert_if_needed
        create_staff_security_alert_if_needed(event)
    return event
```

Il detector è chiamato **dopo** la creazione dell'evento (così il
count include già l'evento corrente). Lazy import per non
forzare il caricamento di `staff_security` durante il bootstrap
Django (e per non rompere test isolati su signals).

---

## 9. Admin — `StaffSecurityAlert`

Registrato come **read-only** (riusa `_ReadOnlyAdminMixin` del
pass 8):
- list_display: `triggered_at`, `alert_type`, `severity`,
  `event_count`, `username_hash`, `ip_address_masked`,
  `cooldown_until`.
- list_filter: `alert_type`, `severity`.
- search_fields: `username_hash`, `ip_address_masked`,
  `alert_type` (no email/PII).
- date_hierarchy: `triggered_at`.
- Tutti i campi sono readonly.

---

## 10. Limiti

### 10.1 Non blocca login
Pass 9 è solo detection. Per lockout vero servono:
- `django-axes` (lock account dopo N tentativi);
- captcha pre-login (reCAPTCHA / hCaptcha self-hosted);
- IP allowlist al reverse proxy.

### 10.2 Threshold globale
La soglia è fissa per tutti gli utenti/IP. Per produzione:
- soglia più stringente per IP esterni alla LAN Studio;
- whitelist IP fidati (uffici, VPN);
- soglia bassa (es. 3) per tentativi su `username_hash` di
  utenti privilegiati (superuser).

### 10.3 No clusterizzazione IP
Il match è esatto su `ip_address_masked` (es. `203.0.113.x`).
Un attaccante che ruota fra subnet diverse passa sotto il
radar (count distribuito su più chiavi). Per defense-in-depth:
combinare con WAF / rate-limit reverse proxy (vedi §11).

### 10.4 No retention automatica
`StaffSecurityAlert` cresce indefinitamente come
`StaffAccessEvent`. Cleanup via task Celery (pass 7) — vedi §11.

### 10.5 Email transazionale, no escalation
L'email è una semplice notifica. Per produzione servirà:
- Sentry alert via DSN (pass 3);
- escalation policy (PagerDuty / Slack channel);
- de-duplica più avanzata (oggi è solo cooldown semplice).

---

## 11. Cosa resta per produzione

### 11.1 Rate-limit reverse proxy / WAF
Caddy/Nginx davanti all'app:
- `limit_req` per IP su `/admin/login/`;
- IP allowlist (Studio + VPN);
- Geo-fencing se opportuno.

### 11.2 Lockout policy formale
- `django-axes` con lock 30 min dopo 5 fail consecutivi;
- recovery via email o telefono Studio;
- audit trail dei lockout in `StaffSecurityAlert.metadata`.

### 11.3 Sentry alerting
Ogni `StaffSecurityAlert` di severità `high` (futura) può essere
inoltrato a Sentry come evento speciale, sfruttando il pass 3.

### 11.4 Retention
Task Celery (pass 7) notturno:
- elimina `StaffAccessEvent.created_at < now - 90d`;
- elimina `StaffSecurityAlert.triggered_at < now - 365d`
  (più conservativo perché aggregato).

### 11.5 Severity dinamica
Oggi tutti gli alert sono `medium`. Da introdurre:
- `low`: 5–9 fail;
- `medium`: 10–24 fail;
- `high`: ≥25 fail O target di superuser.

### 11.6 Threshold per ruolo
Differenziare:
- staff normale: threshold 5;
- superuser: threshold 3;
- API key (futuro): 0 (qualunque fail logga).

---

## 12. Test aggiunti (11, tutti passati)

`apps/compliance/test_staff_brute_force.py`:
1. `test_under_threshold_does_not_create_alert` — 4 fail < 5 → 0 alert.
2. `test_threshold_reached_creates_one_alert` — 5 fail → 1 alert (severity=medium).
3. `test_cooldown_suppresses_duplicate_alerts` — altri 5 fail entro cooldown → ancora 1 alert.
4. `test_post_cooldown_creates_new_alert` — cooldown scaduto → 5 fail nuovi creano alert #2.
5. `test_detector_matches_by_ip_even_with_different_usernames` — 5 fail con username diversi ma stesso IP → 1 alert (credential-stuffing).
6. `test_detector_disabled_does_nothing` — `STAFF_LOGIN_ALERTS_ENABLED=False` → 10 fail, 0 alert.
7. `test_email_disabled_alert_created_no_email` — alert creato, `mail.outbox` vuota.
8. `test_email_enabled_alert_creates_one_email` — 1 email con subject corretto e 2 destinatari.
9. `test_email_body_does_not_leak_pii` — body NON contiene `password`, IP raw, UA `Mozilla/5.0`, password text.
10. `test_staff_security_alert_admin_is_read_only` — `has_add/change/delete_permission` tutti `False`.
11. `test_italy_smoke_run_simulation_35_10_0` — 35/10/0 → 26 268 / 27 353 / 28 439 EUR.

I test usano una helper `_make_failed_event()` che crea
`StaffAccessEvent` direttamente (bypassando i signals e il Django
test client) per costruire scenari controllati e veloci.

---

## 13. Validazione

```bash
.venv/Scripts/python.exe manage.py makemigrations --check
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

---

## 14. Disclaimer

Questo iter aggiunge **detection-only**. Non altera dati legali,
calcoli, output del calcolatore Italia. Non blocca login né IP.
La reazione operativa agli alert (indagine, lockout manuale,
contatto utente) resta in capo allo Studio. Il disclaimer
obbligatorio CLAUDE.md sulle simulazioni indicative resta valido.
