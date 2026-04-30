# LOCAL — Product hardening, pass 3 — Sentry integration (opzionale)

**Iter**: F-local-product-hardening-pass3-sentry
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**

> Terzo passaggio: integrazione Sentry opzionale per error
> monitoring. Non obbliga a usare Sentry in locale (DSN vuoto =
> no-op completo, neppure l'import del pacchetto). Privacy-first:
> tutti i campi sensibili sono redatti tramite un `before_send`
> hook puro testato in unit test. Nessun dato legale toccato. IT
> smoke 35/10/0 → 26 268 / 27 353 / 28 439 EUR verificato.

---

## 1. Cosa è stato aggiunto

| Area | File | Tipo |
|---|---|---|
| Dependency | `requirements.txt` | aggiunto `sentry-sdk[django]>=2.18,<3` |
| Module | `apps/core/observability.py` (nuovo) | `scrub_sentry_event` + `init_sentry_from_settings` |
| Settings | `config/settings.py` | 5 settings env-driven (SENTRY_*) |
| App init | `apps/core/apps.py` | hook `ready()` che chiama `init_sentry_from_settings` |
| Test | `apps/core/test_observability.py` (nuovo) | 9 test |
| Docs | questo file | — |

Niente modifiche a calculator, dataset, formula, engine, modelli
legali, wizard, view CRM. La superficie di rischio è limitata
all'init Django app (`apps.core.ready()`).

---

## 2. Dependency: sentry-sdk

Aggiunto a `requirements.txt`:

```
sentry-sdk[django]>=2.18,<3
```

**Scelta della versione:**
- `>=2.18` perché è la stabile più recente al momento dell'iter
  (gennaio 2026) con supporto Django 5.x.
- `<3` per evitare break-changes maggiori della 3.x quando
  uscirà.
- `[django]` extras: include gli adapter per `DjangoIntegration`,
  che cattura automaticamente errori 500 e middleware. Senza
  extras, l'integrazione viene saltata graziosamente.

**Stato d'installazione:** la dipendenza è dichiarata ma **non
necessariamente installata** in dev locale. Il modulo
`apps/core/observability.py` è progettato per essere caricabile
anche senza il pacchetto: `import sentry_sdk` avviene solo
dentro `init_sentry_from_settings()` e solo se `SENTRY_DSN` non
è vuoto. In dev (DSN vuoto) il pacchetto può non essere
installato senza errori.

In produzione/staging, dopo `pip install -r requirements.txt`,
il pacchetto è disponibile e `init_sentry_from_settings()` lo
importa al primo avvio.

---

## 3. Settings Sentry

In `config/settings.py`, sezione **Sentry — error monitoring opzionale**:

| Setting | Default | Override env |
|---|---|---|
| `SENTRY_DSN` | `""` (vuoto = no-op) | `SENTRY_DSN` |
| `SENTRY_ENVIRONMENT` | `"local"` se `DEBUG=True`, `"production"` altrimenti | `SENTRY_ENVIRONMENT` |
| `SENTRY_TRACES_SAMPLE_RATE` | `0.0` (no performance tracing) | `SENTRY_TRACES_SAMPLE_RATE` |
| `SENTRY_PROFILES_SAMPLE_RATE` | `0.0` (no profiling) | `SENTRY_PROFILES_SAMPLE_RATE` |
| `SENTRY_SEND_DEFAULT_PII` | `False` | `SENTRY_SEND_DEFAULT_PII` |

**Comportamento:**
- DSN vuoto = nessuna chiamata Sentry, nessun import sentry_sdk.
- DSN configurato → `init_sentry_from_settings()` chiama
  `sentry_sdk.init(...)` con i parametri sopra + il scrubber
  `before_send`.

---

## 4. Privacy scrubber — `scrub_sentry_event`

**Cosa è:** funzione pura `scrub_sentry_event(event, hint=None) -> event`.
Modificatore in-place che redige campi sensibili a qualunque
profondità dell'event Sentry (request body, breadcrumbs, extra,
tags, ...).

**Chiavi sensibili (case-insensitive):**

| Categoria | Chiavi |
|---|---|
| PII utente | `email`, `phone`, `phone_number`, `first_name`, `last_name`, `full_name`, `name`, `message`, `internal_notes` |
| Tecniche | `session_key`, `sessionid`, `csrfmiddlewaretoken`, `csrftoken`, `user_agent`, `ip_address`, `remote_addr` |
| Compliance | `consent`, `consent_record`, `privacy_accepted` |
| Auth | `password`, `passwd`, `secret`, `api_key`, `authorization`, `token` |
| Honeypot | `website` |

**Sostituzione:** ogni valore associato a una chiave sensibile
diventa `"[REDACTED]"`. Le chiavi non sensibili restano
invariate (`country`, `case_type`, `simulation_public_id`,
`victim_age`, ecc. passano attraverso).

**Caratteristiche:**
- Pure-Python, **nessuna dipendenza da sentry_sdk** → testabile
  in unit test senza il pacchetto installato.
- Walk ricorsivo su `dict`, `list`, `tuple`.
- **Non solleva mai**: in caso di payload inatteso (non-dict)
  ritorna l'input invariato. Sentry preferisce un evento
  parzialmente filtrato a un crash del client.

---

## 5. Init lazy

`init_sentry_from_settings(*, sentry_init=None, integrations_factory=None) -> bool`:

- Legge `SENTRY_DSN` da `settings`. Vuoto → ritorna `False`,
  nessun import.
- Non vuoto → importa `sentry_sdk` (se `sentry_init` è None) e
  chiama `sentry_sdk.init(...)` con:
  - `dsn`, `environment`
  - `traces_sample_rate`, `profiles_sample_rate`
  - `send_default_pii=False` (default)
  - `before_send=scrub_sentry_event`
  - `integrations=[DjangoIntegration]` (se disponibile)
- Ritorna `True` dopo l'init.

**Dependency injection per i test:**
- `sentry_init`: callable che sostituisce `sentry_sdk.init`. Nei
  test si passa un `MagicMock()` per verificare argomenti.
- `integrations_factory`: callable che produce la lista
  integrations. Nei test si passa `lambda: []` per evitare
  l'import di `sentry_sdk.integrations.django`.

Questo design fa sì che `apps/core/observability.py` resti
testabile **senza sentry-sdk installato**.

**Dove viene chiamato:** `apps/core/apps.py::CoreConfig.ready()`,
con catch difensivo:
- `ImportError` → log warning "Install sentry-sdk to enable
  monitoring", non crash dell'app.
- altre eccezioni → log warning con `error.__class__.__name__`,
  non crash.

Questa scelta è fail-soft di proposito: meglio avviare l'app
senza Sentry che bloccare un management command locale per un
problema di config Sentry.

---

## 6. Cosa viene fatto / cosa NON viene fatto

**Fatto:**
- ✅ Sentry init opzionale, env-driven.
- ✅ Privacy scrubber con whitelist comprehensive.
- ✅ `send_default_pii=False` di default.
- ✅ Lazy import → codebase utilizzabile senza il pacchetto.
- ✅ DjangoIntegration disponibile se installata con extras `[django]`.
- ✅ Test unit puri (no rete, no eventi reali).

**NON fatto (coscientemente, o lasciato a iter futuri):**
- ❌ Nessun DSN reale registrato.
- ❌ Nessun progetto Sentry creato (lo Studio decide quando).
- ❌ Nessun source map upload (frontend Tailwind via CDN per ora).
- ❌ Nessun release tracking automatico.
- ❌ Nessun alert/notification/escalation routing — è
  configurazione lato Sentry UI, non codice.
- ❌ Nessuna performance tracing (`traces_sample_rate=0.0`)
  perché ha costi non banali e va abilitata solo dopo che il
  funnel pubblico ha traffico reale.
- ❌ Nessun user identification (`set_user`) — i Lead/utenti
  pubblici sono volutamente anonimi nel sistema d'errore.

---

## 7. Cosa resta per produzione

### 7.1 Setup progetto Sentry
- Lo Studio crea un account su sentry.io (o self-hosted Sentry).
- Crea un progetto "Studio Legale Badrane LegalTech".
- Ottiene il DSN del progetto.
- Configura `SENTRY_DSN`, `SENTRY_ENVIRONMENT=production`,
  `SENTRY_TRACES_SAMPLE_RATE` (suggerito: 0.05–0.1 in prima
  fase), via env del container.

### 7.2 Release tracking
- Ad ogni deploy, settare la variabile `SENTRY_RELEASE` (sha del
  commit o tag versione) e passarla a `sentry_sdk.init(release=...)`.
- Aggiungere a `init_sentry_from_settings` un parametro
  `release` letto da settings/env, oppure usare il post-deploy
  hook di Sentry CLI.

### 7.3 Source maps (futuro)
- Quando Tailwind / build pipeline frontend sostituirà l'attuale
  CDN, integrare upload source maps via `sentry-cli sourcemaps
  upload` nella pipeline di build.

### 7.4 Alert routing
- Configurazione Sentry-side (UI):
  - alert su `error` level a inbox Studio + Slack;
  - alert su `transaction.duration` > soglia su endpoint critici
    (`/wizard/...`, `/contact/`);
  - rate limiting eventi simili (de-dup) per non saturare
    inbox.
- Suggerimento: tagging `country` / `case_type` / `transaction`
  per filtrare in Sentry.

### 7.5 Privacy review
- Una volta in produzione con traffico reale, raccogliere alcuni
  eventi di esempio e revisionare:
  - cosa è effettivamente in `request.data`, `breadcrumbs`,
    `extra`?
  - il scrubber copre tutti i casi?
- Aggiornare `SENSITIVE_KEYS` se emergono nuovi vettori.

### 7.6 GDPR / DPA con Sentry
- Sentry è un sub-processor: occorre aggiornare la cookie/privacy
  policy con riferimento a Sentry come destinatario di dati
  tecnici (errori, stacktrace), e firmare il DPA con Sentry.

---

## 8. Test aggiunti (9, tutti passati)

In `apps/core/test_observability.py`:

| # | Test | Verifica |
|---|---|---|
| 1 | `test_scrub_redacts_top_level_sensitive_keys` | 9 chiavi sensitive top-level redatte |
| 2 | `test_scrub_redacts_nested_dict_and_list` | scrub ricorsivo su `request.data` e `breadcrumbs[].data` |
| 3 | `test_scrub_does_not_mutate_innocuous_fields` | snapshot deepcopy: tags, level, transaction, extra invariati |
| 4 | `test_scrub_is_case_insensitive` | `EMAIL`, `Phone_Number`, `MESSAGE` → redatti |
| 5 | `test_scrub_handles_non_dict_input_gracefully` | non crasha su string/None |
| 6 | `test_init_returns_false_when_dsn_empty_and_does_not_call_init` | DSN="" → False, `MagicMock` non chiamata |
| 7 | `test_init_returns_true_when_dsn_set_and_calls_init_with_pii_off` | DSN set → True; kwargs verificati: `dsn`, `environment="staging"`, `send_default_pii=False`, `before_send=scrub_sentry_event` |
| 8 | `test_settings_defaults_are_safe` | `SENTRY_DSN==""`, `SENTRY_SEND_DEFAULT_PII==False`, sample rates 0.0 |
| 9 | `test_italy_smoke_run_simulation_35_10_0` | 35/10/0 → 26 268 / 27 353 / 28 439 |

I test 1–7 sono pure-Python (no DB, no `django_db` marker).
Solo il #9 richiede `@pytest.mark.django_db` per la fixture
`italy_smoke_stack`.

---

## 9. Validazione

```bash
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

---

## 10. Disclaimer

Questo iter abilita un'infrastruttura di error monitoring
opzionale. Non altera dati legali, calcoli, o l'output del
calcolatore Italia. Lo Studio decide quando attivare Sentry
configurando il DSN. Il disclaimer obbligatorio CLAUDE.md sulla
natura indicativa delle simulazioni resta valido.
