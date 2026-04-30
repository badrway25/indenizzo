# LOCAL — Product hardening, pass 1

**Iter**: F-local-product-hardening-pass1
**Data**: 2026-04-30
**Stato**: implementato + testato in locale. **Nessun deploy.**

> Primo passaggio di hardening del prodotto in vista di una demo
> locale/staging futura. Nessun dato legale è stato modificato:
> niente nuove `LegalSource` `approved`, niente `CompensationDataset`
> nuovi, niente `CalculationFormula` modificate. Lo smoke
> contract Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR è
> verificato da test dedicato in CI.

---

## 1. Cosa è stato aggiunto

| Area | File toccato | Tipo |
|---|---|---|
| Healthcheck | `config/urls.py`, `apps/core/views.py` | nuovo path `/healthz/` |
| Rate-limit | `apps/core/rate_limit.py` (nuovo), `config/settings.py` | nuovo modulo + 3 settings env-driven |
| Rate-limit | `apps/crm/views.py`, `apps/cases/views.py` | decorator `@public_post_rate_limit` su 6 view |
| Rate-limit | `templates/public/rate_limited.html` (nuovo) | pagina 429 |
| Cookie banner | `templates/partials/cookie_consent_banner.html` (nuovo), `templates/base.html` | partial incluso |
| Test | `apps/core/test_local_product_hardening.py` (nuovo) | 10 test |
| Docs | `docs/architecture/LOCAL_PRODUCT_HARDENING_PASS1.md` (nuovo) | questo file |

Nessun dato legale è stato toccato. Calcolatori, dataset, formule
e wizard form NON sono stati modificati funzionalmente: solo
decorator esterno e include template.

---

## 2. /healthz/ — perché è leggero

**Path**: `GET /healthz/` (top-level, **fuori** da `i18n_patterns`).

**Risposta**: `200 OK` con `Content-Type: application/json` e body
`{"status": "ok"}`.

**Cosa NON fa, di proposito:**
- ❌ Non interroga il database.
- ❌ Non interroga la cache.
- ❌ Non rende un template Django.
- ❌ Non controlla migrations o LegalSource.
- ❌ Non è i18n-prefixed (resta su `/healthz/`, mai `/it/healthz/`).

**Perché:** il loadbalancer / Caddy / Docker healthcheck deve poter
restare verde anche se il database ha un picco di IO o se le
migrations sono in corso. Un check più profondo (DB ping, cache
ping, registry calculator, smoke calcolo) verrà introdotto in
futuro come `/readiness/` separato, dietro autenticazione interna.

**Lato monitoring:** il check va fatto su `GET /healthz/`. Se
serve verificare la lingua corrente o il funnel pubblico è
opportuno usare un altro probe (es. `GET /` con timeout).

---

## 3. Rate-limit — come funziona

**Decoratore**: `apps.core.rate_limit.public_post_rate_limit`.

**Applicato a (6 view):**
- `apps.crm.views.contact` — `POST /contact/`
- `apps.cases.views.wizard_italy_road_accident` — `POST /wizard/it/road-accident/`
- `apps.cases.views.wizard_france_road_accident` — `POST /wizard/fr/road-accident/`
- `apps.cases.views.wizard_belgium_road_accident` — `POST /wizard/be/road-accident/`
- `apps.cases.views.wizard_morocco_inheritance` — `POST /wizard/ma/inheritance/`
- `apps.cases.views.wizard_tunisia_inheritance` — `POST /wizard/tn/inheritance/`

**Settings (env-driven, default sicuri per dev):**

| Setting | Default | Significato |
|---|---|---|
| `PUBLIC_POST_RATE_LIMIT_ENABLED` | `True` | flag globale |
| `PUBLIC_POST_RATE_LIMIT_WINDOW_SECONDS` | `3600` | finestra di conteggio |
| `PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS` | `20` | max POST per (IP, path) nella finestra |

**Chiave cache**: `rl:public_post:{ip}:{path}`.
- `ip` = `request.META["REMOTE_ADDR"]` normalizzato (IPv6 zone-id
  rimosso). **Non** si usa `X-Forwarded-For` per evitare spoofing
  da client; in produzione, dietro reverse proxy fidato, il proxy
  dovrà settare `REMOTE_ADDR` correttamente (oppure si configura
  `SECURE_PROXY_SSL_HEADER` / `USE_X_FORWARDED_HOST` con cura).
- `path` = `request.path` (i18n-prefixed: `/it/contact/`,
  `/fr/wizard/...` contano come path distinti, comportamento
  voluto — un attaccante che cambia lingua paga il limite per ogni
  variante).
- Solo POST: GET pass-through (idempotente, non si crea Lead/Sim).

**Algoritmo:**
1. `cache.add(key, 1, timeout=window)` se la chiave non esiste.
2. Altrimenti `cache.incr(key)`.
3. Se contatore > `max_attempts`: ritorna `HTTP 429` con template
   `public/rate_limited.html` e header `Retry-After: <window>`.
4. Niente PII nei log: solo IP **mascherato** (ultimo octet
   sostituito con `x`) + path + contatore.

**Comportamento sotto limite raggiunto:**
- View **non** chiamata: nessun `Simulation`, nessun `Lead`,
  nessun `ConsentRecord`, nessun `LeadEvent` creato.
- Pagina 429 in HTML accessibile (skip link, focus visibile).

---

## 4. Limiti del rate-limit cache-based

> Questa è una **prima linea** di difesa, non sostituisce un WAF.

| Limite | Implicazione | Mitigazione produzione |
|---|---|---|
| **LocMemCache è per-process** | In multi-worker (gunicorn -w 4), il contatore è separato per worker → max effettivo = workers × max_attempts | Configurare `CACHES` con Redis o Memcached (1 istanza condivisa). |
| **IP-based** | NAT/CDN: utenti diversi dietro lo stesso IP condividono il limite | Combinare con captcha pre-submit, e con WAF/Cloudflare-rule layer-7. |
| **`X-Forwarded-For` ignorato** | Se il reverse proxy non setta correttamente `REMOTE_ADDR`, tutti i request risultano da `127.0.0.1` → 1 limite globale | Configurare il proxy: `proxy_set_header X-Real-IP $remote_addr;` + `USE_X_FORWARDED_HOST` solo se proxy fidato. |
| **Window scorrevole approssimato** | TTL fisso = window: un attaccante che invia 19 POST a fine finestra può inviarne altri 20 subito dopo | OK per uso casuale; per attacco mirato serve token bucket / leaky bucket. |
| **Solo POST** | GET flooding non è coperto | OK per i nostri endpoint: GET pubblici sono idempotenti senza side-effect significativo. |
| **Nessun whitelist staff** | Studio in IP fisso può comunque sbattere contro il limite in demo | Tenere `PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS` alto (default 20/h è già generoso) o disabilitare via env in staging dedicato. |

---

## 5. Cookie consent banner

**Partial**: `templates/partials/cookie_consent_banner.html`,
incluso in `base.html` come ultimo elemento del body.

**Cosa fa:**
- Mostra un banner non-bloccante ai primi accessi della sessione
  (controllato da `localStorage`).
- Comunica chiaramente che:
  - il sito usa **solo** cookie tecnici / di sessione necessari
    (Django session, CSRF token);
  - **nessun** analytics o marketing tracker è attivo.
- Linka alla pagina `/privacy/`.
- Ha bottone **OK / Accetta** che salva
  `localStorage["badrane.cookieConsent.v1"] = "1"` e nasconde
  il banner.

**Cosa NON fa:**
- ❌ **Non** carica script esterni di tracking.
- ❌ **Non** setta cookie di terze parti.
- ❌ **Non** è un consent manager (CMP) completo.
- ❌ **Non** offre un opt-out granulare per categoria (necessari /
  preferenze / statistici / marketing) — lo prevediamo solo se
  attiveremo categorie diverse da "necessari".
- ❌ **Non** è ancora una cookie policy legalmente definitiva
  (vedi §7).

**Accessibilità:**
- `role="region"`, `aria-label="Cookie notice"`, `aria-live="polite"`.
- Bottone con outline focus visibile + classi Tailwind
  `focus-visible:outline-2`.
- Markup HTML statico: il JS solo mostra/nasconde via classe
  `hidden`. Senza JS, il banner resta `hidden` di default
  (graceful degradation).

**Failure-soft localStorage:**
- Se il browser è in privacy mode o ha la quota piena, il banner
  si mostra ad ogni visita ma il sito non si blocca.

---

## 6. Test aggiunti (10)

In `apps/core/test_local_product_hardening.py`:

1. `test_healthz_returns_200_and_status_ok` — JSON shape verificato.
2. `test_healthz_does_not_require_db` — gira senza marker `django_db`.
3. `test_get_endpoints_are_not_rate_limited` — 5 GET con max=1 non
   producono 429.
4. `test_contact_post_under_limit_creates_lead` — il path felice
   resta operativo.
5. `test_contact_post_over_limit_returns_429_and_no_lead` — 429
   + Lead non creato (verificato `Lead.objects.count()`).
6. `test_wizard_italy_post_over_limit_returns_429_and_no_simulation`
   — 429 + Simulation non creata.
7. `test_rate_limit_disable_via_override_settings` —
   `PUBLIC_POST_RATE_LIMIT_ENABLED=False` bypassa il limite.
8. `test_cookie_banner_is_present_on_home` — markup ARIA + JS
   localStorage presente.
9. `test_cookie_banner_links_to_privacy_page` — il link
   `/privacy/` è dentro il blocco banner.
10. `test_italy_smoke_run_simulation_35_10_0` — il contratto
    smoke 35/10/0 → 26 268 / 27 353 / 28 439 è verificato via
    `run_simulation`.

**Fixture utility:**
- `_clear_rate_limit_cache` (autouse) — `cache.clear()` prima e
  dopo ogni test per evitare interferenze.
- `italy_smoke_stack` — stack minimo IT (Country, Jurisdiction,
  LegalSource approved, 2 dataset approved, 3 row moral con i
  valori esatti del contratto, 1 formula approved). Stub
  deterministico, non l'estrazione completa: se la realtà cambia
  questo test va aggiornato esplicitamente — è il canarino.

---

## 7. Cosa resta per produzione

> Questo iter è **pass 1**: copre i blocker basici per una demo
> locale/staging. Per una demo **pubblica** o un deploy in
> produzione, restano i seguenti follow-up.

### 7.1 Rate-limit
- **Reverse proxy/WAF**: spostare il rate-limit primario su
  Caddy/Nginx/Cloudflare (token bucket, blacklist IP, geo-fencing
  se richiesto). Il decorator Django resta come secondo strato.
- **Cache condivisa**: configurare Redis come `CACHES["default"]`
  per coerenza tra worker.
- **CAPTCHA / hCaptcha** sui form ad alto rischio (contact, wizard
  con dati sensibili).

### 7.2 Cookie / privacy
- **Cookie policy legale definitiva**: review legale dello Studio,
  con elenco dettagliato dei cookie tecnici e categorie. Aggiornare
  `/privacy/` con la versione approvata.
- **Granularità del consenso** se in futuro saranno introdotti
  cookie analytics (es. self-hosted Plausible / Matomo). Solo
  allora servirà un CMP più articolato.
- **DPIA** (Data Protection Impact Assessment) prima del deploy
  pubblico, vista la natura sensibile dei dati raccolti dai
  wizard (salute, reddito, famiglia).

### 7.3 Monitoring / errori
- **Sentry** (o equivalente self-hosted): tracking errori
  back-end + front-end. Configurazione via `SENTRY_DSN` env, già
  pattern con il resto delle settings env-driven.
- **Logging strutturato** (JSON) verso aggregatore: oggi il
  logging è verbose plain-text con filtro `RedactPIIFilter`. In
  produzione serve formato JSON + ingest in Loki/CloudWatch/ELK.
- **Metriche**: simulazioni/giorno, lead/giorno, errori
  calculator, latenza p95.

### 7.4 Email lead notification
- Oggi un nuovo `Lead` è solo un record DB.
- Implementare email transazionale (SMTP / Mailgun / SES)
  che notifichi lo Studio entro N minuti dal submit.
- Coda async via Celery + Redis (CLAUDE.md richiede entrambi
  in produzione).
- Template email multi-lingua.

### 7.5 Auth / admin hardening
- **MFA admin**: forzare 2FA per `is_staff=True` (django-otp +
  django-two-factor-auth se serve, oppure soluzione SSO IdP
  esterno).
- **IP allowlist** sull'admin in produzione.
- **Rate-limit specifico** sull'admin login (oltre al global).

### 7.6 Infra / deploy
- **PostgreSQL** in produzione (CLAUDE.md). Migrazione da
  SQLite + test su staging.
- **Celery + Redis** per task async.
- **Docker / docker-compose** per parità dev/prod.
- **Backup giornaliero** PostgreSQL + restore tested.
- **DR plan** documentato.

### 7.7 Healthcheck avanzato
- `/readiness/` separato (dietro auth interna o IP allowlist) che
  pinga DB, cache, registry calculator. Diverso da `/healthz/`
  che resta sempre-on.

---

## 8. Validazione

```bash
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
```

Tutti verdi al merge di questo iter. Il numero totale dei test è
cresciuto di 10 (smoke contract Italia incluso).

---

## 9. Disclaimer

Questo documento descrive un primo passaggio di hardening
**locale**. Non è una checklist completa per il deploy in
produzione, né un audit di sicurezza certificato. Prima di
qualsiasi rilascio pubblico, lo Studio deve completare gli
elementi della §7 e ottenere validazione legale (cookie policy)
e tecnica (security review). Il disclaimer obbligatorio
CLAUDE.md resta valido per ogni simulazione.
