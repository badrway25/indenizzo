# LOCAL — Product hardening, pass 8 — staff access audit log

**Iter**: F-local-product-hardening-pass8-audit-log-staff-access
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**

> Ottavo passaggio: audit log degli accessi staff/admin (login
> success/failed/logout) tramite il modello `StaffAccessEvent`.
> Privacy-minimized (IP mascherato, username/UA hashati, password
> mai persistite). Read-only in admin. Non blocca il login: è
> osservabilità, non gating. IT smoke 35/10/0 → 26 268 / 27 353
> / 28 439 EUR verificato.

---

## 1. Cosa è stato aggiunto

| Area | File | Tipo |
|---|---|---|
| Helpers | `apps/compliance/privacy_helpers.py` (nuovo) | `mask_ip` + `hash_text` + `build_staff_access_event_kwargs` |
| Model | `apps/compliance/models.py` | aggiunto `StaffAccessEvent` |
| Migration | `apps/compliance/migrations/0002_staffaccessevent.py` (nuovo) | crea tabella |
| Signals | `apps/compliance/signals.py` (nuovo) | handler `user_logged_in/out/failed` |
| App ready | `apps/compliance/apps.py` | import `signals` per registrare i receiver |
| Admin | `apps/compliance/admin.py` | `StaffAccessEventAdmin` read-only |
| Test | `apps/compliance/test_staff_access_event.py` (nuovo) | 10 test |
| Docs | questo file | — |

Niente nuove dipendenze. Niente touch a calculator/engine/wizard.
Una sola tabella in più nel DB (`compliance_staffaccessevent`),
inizialmente vuota.

---

## 2. Cosa viene tracciato

Per ogni evento (login_success / login_failed / logout) il modello
salva:

| Campo | Tipo | Esempio |
|---|---|---|
| `event_type` | choice | `login_success` |
| `user` | FK SET_NULL | utente Django (NULL per login_failed) |
| `username_hash` | CharField | `5e884898da28047151d0e56f8…` (24 char) |
| `ip_address_masked` | CharField | `203.0.113.x` |
| `user_agent_hash` | CharField | `c0535e4be2b79ffd93291305…` (24 char) |
| `path` | CharField | `/admin/login/` |
| `metadata` | JSONField | `{}` (estendibile) |
| `created_at` | DateTimeField (UTC) | `2026-04-30T14:23:11Z` |

**Filtro di scope:**
- `login_success` / `logout`: registrato SOLO se il request ha
  `path` che inizia con `/admin/` **OPPURE** `user.is_staff` o
  `is_superuser`. Il funnel pubblico (`/contact/`,
  `/wizard/...`) NON viene loggato qui (lo coprono già
  `Lead`/`ConsentRecord`).
- `login_failed`: registrato SOLO se il request ha `path` che
  inizia con `/admin/`. Tentativi di brute-force su altri
  endpoint sono fuori scope (ci sarà eventualmente un audit
  separato per il funnel pubblico).

---

## 3. Cosa NON viene tracciato (mai)

| Mai persistito | Motivazione |
|---|---|
| Password (raw o hashed) | Sicurezza: non deve esistere copia di password fuori dal modello User. |
| Username in chiaro | Privacy: solo hash SHA-256 troncato. Permette di correlare eventi dello stesso username senza esporlo. |
| IP completo | Privacy: ultimo octet IPv4 / ultimo gruppo IPv6 mascherato a `x`. |
| User-agent raw | Privacy: solo hash. Permette di correlare sessioni dallo stesso UA senza salvare la stringa identificante. |
| Body della richiesta | Privacy + storage: il body può contenere PII utente o credenziali parziali. |
| Cookie / CSRF token | Sicurezza. |

---

## 4. Privacy helpers

### 4.1 `mask_ip(ip)`
Pure-function. Non solleva. Casi:
- `"203.0.113.42"` → `"203.0.113.x"`
- `"2001:db8::1"` → `"2001:db8::x"`
- `"fe80::1%eth0"` → `"fe80::x"` (zone id rimosso prima del mask)
- `""` o `None` → `""`

Non risolve hostname, non fa lookup. Coerente col rate-limit
pass 1 che usa solo `REMOTE_ADDR`.

### 4.2 `hash_text(value)`
SHA-256 hex troncato a 24 caratteri. Pure-function:
- Stabile: `hash_text("alice") == hash_text("alice")`.
- Non reversibile: dal solo hash non si recupera il testo.
- Empty/None → `""` (no "hash di niente").

24 hex char ≈ 96 bit di entropia: collisioni inutili in pratica.

### 4.3 `build_staff_access_event_kwargs(...)`
Helper pure che compone il dict di kwargs per
`StaffAccessEvent.objects.create(**kwargs)`. Estrae IP/UA/path da
`request.META`, applica `mask_ip` + `hash_text`, deriva username
da `user.get_username()` se non passato esplicitamente. Non
scrive su DB: il caller decide.

---

## 5. Segnali Django auth

Tre receiver in `apps/compliance/signals.py`:

| Segnale Django | Receiver | Filtro |
|---|---|---|
| `user_logged_in` | `_on_user_logged_in` | path `/admin/...` OR `user.is_staff` |
| `user_logged_out` | `_on_user_logged_out` | path `/admin/...` OR `user.is_staff` |
| `user_login_failed` | `_on_user_login_failed` | path `/admin/...` (user è None per definizione) |

**Mai bloccano il flow auth**: i receiver sono read-only sul flow
e wrappati in `try/except` che assorbono eccezioni di scrittura
DB (loggate come `WARNING` senza PII).

I receiver sono registrati in `apps.compliance.apps.ready()` con
un `from . import signals  # noqa: F401`.

---

## 6. Admin — `StaffAccessEvent`

Registrato come **read-only**:
- `has_add_permission` → False
- `has_change_permission` → False
- `has_delete_permission` → False

Visualizza:
- list_display: `created_at`, `event_type`, `user`,
  `username_hash`, `ip_address_masked`, `path`.
- list_filter: `event_type`.
- search_fields: `username_hash`, `user__id`,
  `ip_address_masked`, `path`. **Niente search su email** per
  evitare leak via guess.
- date_hierarchy: `created_at`.

Per cercare l'hash di uno username noto da admin, lo Studio può
calcolare l'hash in `manage.py shell`:

```python
from apps.compliance.privacy_helpers import hash_text
print(hash_text("alice"))
# 5e884898da28047151d0e56f8…
```

E incollare nel campo search.

---

## 7. Limiti

### 7.1 Solo audit, no enforcement
Il modello registra eventi ma **non blocca** alcun login. Per
gating su brute-force serve un meccanismo separato:
- `django-axes` (lock-out account dopo N tentativi falliti);
- captcha pre-login;
- IP allowlist al reverse proxy.

### 7.2 Filter sul path admin
I segnali registrano login_failed solo se il path è `/admin/...`.
Tentativi di credential-stuffing su API custom (es. DRF token
auth) **non** vengono loggati. Sarà necessario un middleware
specifico se introdurremo API protette.

### 7.3 Risoluzione IP
Solo `REMOTE_ADDR`. Dietro reverse proxy va configurato il proxy
per popolare correttamente `REMOTE_ADDR` (vedi
`POSTGRES_LOCAL_STAGING_PREP.md` §11 e i settings
`SECURE_PROXY_SSL_HEADER`).

### 7.4 Time precision
`created_at` ha precisione DB (sub-secondo). Per ordinamento
deterministico in test con timer Windows ~15.6ms, l'ordering
include `-pk` come tiebreak.

### 7.5 No retention policy automatica
Il modello cresce indefinitamente. Per produzione (vedi §10)
serve una policy retention. Una `DataRetentionPolicy` con
`applies_to=staff_audit, retention_days=N` è la naturale strada
ma richiede un task Celery di cleanup.

---

## 8. Retention futura

In produzione, la tabella `staff_access_events` può accumulare
volumi alti (decine di K eventi al mese su un admin attivo).
Strategia consigliata:

1. **Retention 90 giorni** (configurabile via
   `DataRetentionPolicy` esistente o via env). Cleanup notturno.
2. **Cold storage** dei vecchi eventi: prima della cancellazione
   DB, dump su file `staff_access_YYYY-MM.jsonl.gz` archiviato
   offline (S3 / NAS Studio). Recuperabile in caso di indagine
   ma non interrogabile in admin.
3. **Eccezioni legali** se serve preservare eventi più a lungo
   per audit GDPR / DPA con cliente.

---

## 9. Alert brute-force futuro

`StaffAccessEvent` è la base per un alert su brute-force. Logica
proposta (NON implementata in pass 8):

- Sliding window: `count(event_type='login_failed' AND
  ip_address_masked=X AND created_at >= now() - 10min) >= 5`.
- Alert via Sentry (pass 3) o email allo Studio.
- Lock-out via `django-axes` o middleware dedicato.

Il modello già supporta `metadata: JSONField` per arricchire
gli eventi con tag tipo `brute_force_suspect=true` quando il
detector lo decide.

---

## 10. Cosa resta per produzione

### 10.1 Retention policy + cleanup task
Vedi §8. Da combinare con il pass 7 (Celery): task notturno
`cleanup_staff_access_events` con argomento `older_than_days`.

### 10.2 Brute-force detection
Vedi §9. Pass futuro candidato:
`F-staff-audit-brute-force-detector`.

### 10.3 Dashboard staff
Mini-dashboard in `/staff/project-status/` (pass 0 dell'iter
F-staff-status) che mostra:
- ultimi 20 login_failed;
- ultimi 5 login_success;
- top 5 IP per login_failed nelle 24h.
Read-only, dietro `is_staff` + MFA (pass 5).

### 10.4 Integrazione Sentry
I `WARNING` dei receiver (write_failed, ecc.) finiscono
automaticamente in Sentry dal pass 3 — basta configurare il DSN.

### 10.5 Audit log per altre app
Lo schema `StaffAccessEvent` può essere riutilizzato per
audit di:
- modifiche `LegalSource.status` (chi ha approvato cosa);
- accessi a `Lead` records (chi ha letto un lead).
Queste sono già parzialmente coperte da `auditlog`/`simple-history`
ma con scope più stretto (modifiche ai modelli, non accessi).

---

## 11. Validazione

```bash
.venv/Scripts/python.exe manage.py makemigrations --check
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

Smoke contract IT verificato dal test #10:
`run_simulation` 35/10/0 → 26 268 / 27 353 / 28 439 EUR.

---

## 12. Disclaimer

Questo iter aggiunge solo audit log degli accessi staff. Non
altera dati legali, calcoli, output del calcolatore Italia. Non
blocca alcun flow di autenticazione. Il disclaimer obbligatorio
CLAUDE.md sulle simulazioni indicative resta valido. La gestione
operativa di questo audit log (retention, alert, cleanup) resta
in capo allo Studio.
