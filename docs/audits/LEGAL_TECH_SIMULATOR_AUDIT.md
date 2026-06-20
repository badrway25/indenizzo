# Legal-Tech Simulator — Audit tecnico

**Data:** 2026-06-19
**Branch:** `product/staging-readiness-p0`
**Tipo:** audit read-only del codice esistente + verifica avversariale degli
invarianti di sicurezza/prodotto, seguito da un primo intervento sicuro e
testato (vedi §6 / §11).
**Metodo:** audit multi-agente (10 mapper per sottosistema + 4 verificatori
avversariali sugli invarianti critici), incrociato con esecuzione reale di
`manage.py check`, `pytest` e lettura diretta dei file citati.

> Questo documento **non** descrive un progetto greenfield. La repository è
> una piattaforma legal-tech **matura** (13 app Django, ~74k LOC di codice
> applicativo, ~1.544 funzioni di test, tooling di staging/deploy, GDPR
> hardening, Lighthouse CI). Il prompt di kickoff assume "audit poi costruisci
> le fondamenta": le fondamenta esistono e sono collaudate. L'audit fotografa
> lo **stato reale** e propone gli interventi residui per il go-live.

---

## 1. Audit repository (struttura attuale)

### 1.1 Stack e versioni
- **Python 3.12**, **Django 5.2 LTS** (`Django>=5.2,<5.3`).
- DRF, django-htmx, django-filter, django-import-export, django-simple-history,
  django-auditlog, Celery 5 + Redis, `psycopg[binary]` (PostgreSQL),
  reportlab (PDF), django-csp 4.x, whitenoise, sentry-sdk 2.x, django-otp,
  pytest + pytest-django + factory-boy, Playwright (dichiarato), ruff/black/mypy.
- Frontend: server-rendered Django templates + **CSS locale** (`static/css/site.css`,
  Tailwind-subset hand-authored; CDN Tailwind rimosso), font vendorizzati
  (Inter/Cormorant/Amiri/Tajawal) con supporto RTL.
- DB: **SQLite in dev**, **PostgreSQL in prod** via `DATABASE_URL`.

### 1.2 App Django (13) — peso indicativo (LOC, migrazioni)
| App | LOC | Migr. | Ruolo |
|---|---:|---:|---|
| `core` | ~20.0k | 0 | home, layout, SEO, health, checks `core.E001..E008`, rate-limit, MFA, observability |
| `calculators` | ~12.3k | 0 | engine registry, schema output, engine per paese (IT reale, FR/BE/MA/TN inert) |
| `legal_sources` | ~11.6k | 1 | fonti legali, versioni, allegati, **LegalReview**, validate/promote commands |
| `cases` | ~8.0k | 3 | Simulation, wizard pubblici, result page, orchestrazione `run_simulation` |
| `compensation` | ~8.0k | 3 | Dataset/Row/Formula, regole importo, `services.py` (gate APPROVED lato read) |
| `crm` | ~5.8k | 5 | Lead, LeadEvent, webhook outbox HMAC, mandate, timeline staff |
| `compliance` | ~5.5k | 5 | consensi, retention, data-deletion, audit privacy, staff security |
| `reports` | ~1.5k | 1 | PDF SimulationReport (reportlab), hash, audit `DATA_EXPORTED` |
| `jurisdictions` | ~1.0k | 1 | Country/Currency/Language/Jurisdiction |
| `accounts` | ~0.1k | 1 | User custom (role, preferred_language) |
| `inheritance` | stub | 0 | **vuota** (logica successioni vive in `calculators`) |
| `cms_content` | stub | 0 | **vuota** (contenuti hard-coded in template/`core`) |
| `analytics` | stub | 0 | **vuota** |

### 1.3 Configurazione
- `config/settings.py` (~799 righe) single-file, env-driven (`django-environ`),
  hardening gated su `if not DEBUG`, guard fatale su `SECRET_KEY` insicura.
- `config/urls.py`: `healthz`/`robots`/`sitemap` fuori da `i18n_patterns`; route
  app dentro `i18n_patterns(prefix_default_language=False)`.
- Docker: `Dockerfile` multi-stage non-root; `docker-compose.staging.yml`
  (postgres+web) e `docker-compose.local.yml` (web+db+redis+celery).
- CI: `.github/workflows/ci.yml` con job **separati** `python-tests` (DEBUG=true)
  e `production-checks` (DEBUG=false, esegue i system check di produzione),
  più Lighthouse e audit Playwright strutturale.

---

## 2. Stato iniziale (cosa funziona davvero)

- **Italia** è l'unico engine **REALE** e source-bound:
  `ItalyRoadAccidentBodilyInjuryCalculator` lega `LegalSource` approved
  (D.P.R. 13/01/2025 n.12) → `CompensationDataset` approved (TUN 2025,
  9.191 + 27.573 righe) → `CalculationFormula` approved (art. 138). Contratto
  canarino bloccato: 35/10/0 → **26.268 / 27.353 / 28.439 €**.
- **FR/BE/MA/TN** sono engine eseguibili **ma inerti**: nessuna `LegalSource`
  approved, quindi il primo gate fallisce e il sistema risponde
  `unavailable_requires_legal_validation`. Per ciascuno esiste un **review
  package** pronto per la firma dello Studio.
- `manage.py check` è **pulito** salvo un solo warning **intenzionale**
  (`core.W001`: campi `STUDIO_*` vuoti → diventa errore bloccante `core.E001`
  in produzione). Migrazioni applicate. 4 locali (it/fr/en/ar).
- I requisiti canonici `docs/architecture/PRODUCT_REQUIREMENTS.md` (REQ-1…6)
  e la roadmap `docs/ROADMAP_PRIORITIZED.md` (P0–P5) sono già in repo.

---

## 3. Problemi trovati (sintesi avversariale)

L'audit ha prodotto **53 finding**: **2 critical, 10 high, 23 medium, 18 low**.
Di seguito i finding High/Critical con evidenza file:linea e fix in una riga.
Medium/Low sono riassunti per dimensione nel §16 (prossimi step) e nella
roadmap collegata.

### 3.1 Critical
| # | Finding | Evidenza | Fix |
|---|---|---|---|
| C1 | **Italiano (mercato primario) ~67% non tradotto**: msgid in inglese, `locale/it` 248/742 msgstr → ~494 stringhe in inglese all'utente IT (FR 246/742, AR 272/742) | `config/settings.py:236`; `locale/it/LC_MESSAGES/django.po` | completare le `.po` (almeno funnel+landing+result+disclaimer), gate CI di copertura, `compilemessages` |
| C2* | **PDF report senza autenticazione** con PII sanitaria | `apps/reports/views.py:38-76` | **Ridimensionato a HIGH/by-design** — vedi §3.4 |

### 3.2 High (selezione per dimensione)
| # | Dimensione | Finding | Evidenza |
|---|---|---|---|
| H1 | Frontend | **Language switcher con `onchange` inline bloccato dalla CSP** → selettore muto in produzione (rompe REQ-1) | `templates/partials/language_switcher.html:11` ✅ **RISOLTO §6** |
| H2 | Frontend | Result page non mostra `confidence` né `missing_documents` benché home/methodology lo promettano | `wizard_result.html`; `home.html:95`; `methodology.html:52` |
| H3 | Legal-data | Promozione ad APPROVED si fida di un blocco JSON **free-text editabile** in `LegalSource.notes` | `promote_official_legal_sources.py:136-163`; `admin.py:108` |
| H4 | Legal-data | `LegalReview` **mutabile e cancellabile**: nessuna firma reale, nessun append-only, reviewer falsificabile | `legal_sources/models.py:297-352`; `admin.py:138-152` |
| H5 | Data model | `LegalSourceVersion` **orfana** dalla catena dataset/formula (nessun FK; `content_hash` mai calcolato) | `compensation/models.py:65-106` vs `legal_sources/models.py:187-244` |
| H6 | CRM | Admin permette di impostare a mano `mandate_signed`/`mandate_status` bypassando il servizio mandato e il suo audit trail | `crm/admin.py:179-184`; `compliance/mandate.py:56-157` |
| H7 | Config | **Nessun backend `CACHES`** definito → rate limiter e brute-force detector per-worker (LocMemCache), non condivisi | `settings.py` (no CACHES); `apps/core/rate_limit.py:34` |
| H8 | Deploy | Staging compose **non deployabile as-is**: no reverse-proxy/TLS, `legal_data` montato read-write | `docker-compose.staging.yml:3-5,64-73` |
| H9 | Deploy | Redis+Celery **assenti** dal compose di staging benché cablati nel codice | `docker-compose.staging.yml` vs `docker-compose.local.yml:43-56` |
| H10 | SEO | Nessun `canonical`/Open Graph sulla home e sulla maggior parte delle pagine indicizzabili | `templates/public/home.html:6-22` |

### 3.3 Calculation engine — finding rilevanti (Medium)
- **NULL `point_value` coalescizzato a `Decimal(0)`**: una riga APPROVED
  incompleta produce `status=CALCULATED` con 0 € invece di `UNAVAILABLE` —
  un "calcolo falso" sottile (0 € presentato come importo calcolato).
  `apps/compensation/services.py:533,612,705,1177,1264,1307`.
- **Audit-trail di calcolo sottile**: nessun hash della riga/formula legato
  alla singola Simulation; le righe APPROVED sono editabili in place →
  una stima storica non è provabilmente riproducibile.

### 3.4 Correzione di un finding dell'audit (PDF non autenticato, C2)
Il mapper "security" ha marcato **CRITICAL** il download PDF non autenticato,
ma con evidenza vuota. La verifica diretta mostra che è una **scelta di design
documentata** (`apps/reports/views.py:14-17`): il `public_id` UUID a 122 bit è
un **capability token**, coerente con il fatto che **anche la result page è
anonima** (`/wizard/result/<uuid>/`, già `noindex`). L'intero funnel è
anonimo-by-design (si simula senza login). Aggiungere auth solo al PDF sarebbe
incoerente e romperebbe il flusso. → **Riclassificato HIGH / by-design**; la
mitigazione (token firmato a scadenza breve, o area cliente autenticata in P5)
è un item di roadmap, **non** un fix drop-in sicuro. Nota residua: l'endpoint
**rigenera** un `SimulationReport` + evento `DATA_EXPORTED` ad ogni GET (rumore
audit / abuso): valutare get-or-create + rate-limit (roadmap).

---

## 4. Architettura proposta (conferma + raffinamenti)

L'architettura **non va riscritta**. Il cuore — catena
`LegalSource → CompensationDataset → CalculationFormula → CalculationResult`
con **doppio gate APPROVED lato read** (`apps/compensation/services.py`) — è
solido e va mantenuto come template per attivare FR/BE/MA/TN e l'eredità.

Raffinamenti consigliati (difesa in profondità, nessuna riscrittura):
1. **Presentation-layer**: legare il rendering degli importi (result page e PDF)
   a `status=='calculated'` **oltre** a `estimated_* is not None`, così la
   regola "no calcolo falso" è imposta anche dal layer di presentazione.
2. **Fail-closed su NULL `point_value`** nell'engine (→ `UNAVAILABLE`).
3. **Integrità della promozione**: ricomputare il verdetto file-hash/marker
   in-process al momento della promozione (non fidarsi di `notes`), e rendere
   `LegalReview` append-only/firmato.
4. **DB CheckConstraint** per gli invarianti oggi solo in `clean()`.

---

## 5. MVP definito (stato vs target)

L'MVP CLAUDE.md (home, scelta paese/caso, wizard IT danno biologico, wizard
successione, risultato, PDF, lead form, admin fonti, dashboard lead, disclaimer,
GDPR consent, test) è **sostanzialmente raggiunto per l'Italia**:

| Voce MVP | Stato |
|---|:--|
| Home simulatore | ✅ |
| Scelta paese / tipo caso | ✅ |
| Wizard IT danno biologico (road accident) | ✅ operativo, source-bound |
| Wizard successione (IT/MA/TN) | ⚠️ scaffold (IT `inheritance_basic` placeholder; MA/TN inert) |
| Risultato simulazione | ✅ (manca surface di `confidence`/`missing_documents`, H2) |
| Report PDF | ✅ (capability-URL; coverage test da estendere) |
| Lead form + dashboard | ✅ (gap: export CSV, lead-360, priorità) |
| Admin fonti | ✅ (gap di integrità H3/H4) |
| Disclaimer | ✅ obbligatorio su web+PDF (verificato, §10) |
| GDPR consent | ✅ doppio consenso art.6+art.9 (verificato) |
| Test minimi | ✅ ampiamente superato (~1.544 test) |

---

## 6. Implementazione eseguita (questo intervento — sicuro e testato)

Due fix piccoli, isolati, ad alto valore, che **non toccano** dati legali né
la matematica dell'engine:

1. **CSP-safe language switcher (H1, REQ-1)** —
   `templates/partials/language_switcher.html`: rimosso l'handler inline
   `onchange="this.form.submit()"` (bloccato dalla CSP enforced → in
   produzione il selettore non sottometteva e il fallback `<noscript>` non
   appariva con JS attivo). Auto-submit ora agganciato da uno `<script>` con
   `nonce` CSP (idioma già usato in 10 template), con bottone "Apply" nel
   `<noscript>` come fallback senza JS. **Bug funzionale di produzione sul
   requisito #1 (multilingua) chiuso.**
   - Test: `apps/core/test_csp_language_switcher.py` (4 test).

2. **Logging PII-safe del fallimento di rendering PDF (GDPR)** —
   `apps/reports/services.py`: sostituito `logger.exception(...)` con
   `logger.error(... error=%s, exc.__class__.__name__)`. Il `logger.exception`
   emetteva il **traceback** del renderer, i cui frame contengono valori
   sensibili della Simulation (età, % invalidità, reddito, dati di decesso);
   il `RedactPIIFilter` scruba solo `getMessage()`, **non** `exc_info`. Il
   dettaglio tecnico resta in `SimulationReport.error_message` (DB
   access-controllato, auditlog).
   - Test: `apps/reports/tests.py::test_render_failure_logs_no_traceback_or_pii`.

---

## 7. Fonti legali recuperate o predisposte

Nessuna nuova fonte recuperata in questa sessione (audit read-only sul dato
legale; nessun import, nessuna promozione). Stato confermato:
- **Approved**: IT `it-dpr-12-2025-tun-danno-biologico` (+ 2 dataset, 1 formula).
- **Needs review**: 4 fonti IT residue + tutte le fonti FR/BE/MA/TN.
- **Review package pronti** (versionati): FR, BE, MA, TN.

---

## 8. Dati demo / non verificati

- I valori "golden" IT nei test sono **seminati dalle fixture** (non legati al
  dataset approved committato) → vedi finding test §11. Non sono dati pubblici.
- Estrazioni candidate FR/BE on-disk sono **gitignored** e marcate non
  validate; non alimentano alcun calcolo (gate APPROVED).

---

## 9. Sicurezza e GDPR (checklist iniziale)

| Controllo | Stato | Note |
|---|:--:|---|
| `SECRET_KEY` da env + guard fatale su default insicuro | ✅ | `settings.py:65-69` |
| Hardening prod (SSL redirect, HSTS 30g, secure cookies, nosniff, X-Frame DENY) gated su `if not DEBUG` | ✅ | `settings.py:50-60` |
| CSP enforced + nonce, no unsafe-inline; check `core.E002/E003` | ✅ | `settings.py:749-799` |
| Consenso esplicito art.6 + art.9 prima dei dati sensibili | ✅ | `crm/forms.py`, `cases/forms.py`, verificato |
| Nessun secret/PII nei log | ⚠️→✅ | unico leak (traceback PDF) **chiuso §6**; `RedactPIIFilter` copre solo email/CF/telefono |
| `.env` escluso da VCS | ✅ | `.gitignore` |
| Audit log accessi admin / azioni sensibili | ✅ | django-auditlog + StaffAccessEvent |
| Retention + cancellazione dati | ✅ scaffold | gate `compliance.E001` |
| Rate limiting / brute-force | ⚠️ | rate limit solo POST pubblici; brute-force admin **detection-only**, `CACHES` non condivisa (H7) |
| MFA admin | ⚠️ | `ADMIN_MFA_REQUIRED` non cablato a django-otp reale |
| `manage.py check --deploy` in CI | ❌ | il job prod esegue solo `check` (manca il tag security) |

Invarianti verificati avversarialmente (§10): **no-calcolo-falso = TIENE
(alta confidenza)**; gli altri tre = **parziali** con gap puntuali.

---

## 10. Verifica avversariale degli invarianti

| Invariante | Verdetto | Sintesi |
|---|:--:|---|
| **Nessun importo pubblico senza fonte APPROVED** | ✅ **YES** (alta conf.) | gli importi si persistono solo nel ramo `CALCULATED`, irraggiungibile senza source+dataset+formula APPROVED con engine/amount_rule whitelisted. Due hardening difensivi consigliati (§4.1-4.2) |
| Nessun secret/PII nei log; consenso gating | ⚠️ PARTIAL | unico gap = traceback PDF (**chiuso §6**); `.env`/SECRET_KEY/consenso tengono |
| Hardening prod (header/cookie/CSP/auth) | ⚠️ PARTIAL | transport/header OK; gap = brute-force enforcement, `CACHES` condivisa, `check --deploy` in CI, SameSite espliciti |
| Disclaimer + fonti + ipotesi + doc mancanti su ogni risultato | ⚠️ PARTIAL | **disclaimer TIENE su web e PDF**; web non mostra `missing_documents` reali dell'engine (usa checklist generica) né `confidence` (H2); PDF completo |

---

## 11. Test eseguiti

| Suite | Risultato |
|---|---|
| `calculators/` + `legal_sources` fixture-isolation + `cases` result-localization | **282 passed** (18s) |
| `apps/core/` + `apps/reports/` (post-fix) | **1145 passed, 1 skipped** (98s) |
| Slice mirato fix (reports + switcher + core) | **53 passed** |
| `manage.py check` | pulito salvo `core.W001` (gate intenzionale) |

Gap di test rilevati (vedi roadmap): nessun layer **Playwright** reale (gli
"e2e" sono test HTTP-client, niente JS/HTMX in browser); golden IT non legato
al dataset approved committato; `apps/reports` con coverage colocato sottile
(disclaimer/no-EUR-leak sul PDF non asseriti).

---

## 12. QA browser

Non eseguita in questa sessione (audit + fix server-side). Il branch contiene
già evidenze Playwright/Lighthouse precedenti (`docs/reports/lighthouse/*`,
`a270961 qa(browser)…`). Da rieseguire dopo il fix del language switcher per
confermare l'auto-submit sotto CSP enforced (raccomandato come test browser).

---

## 13. File modificati (questa sessione)

```
templates/partials/language_switcher.html      # fix CSP (rimosso onchange inline, +script nonce)
apps/reports/services.py                        # logging PII-safe (no traceback)
apps/core/test_csp_language_switcher.py         # NEW — 4 test
apps/reports/tests.py                           # + test_render_failure_logs_no_traceback_or_pii
docs/audits/LEGAL_TECH_SIMULATOR_AUDIT.md       # NEW — questo documento
docs/ROADMAP_LEGAL_TECH_SIMULATOR.md            # NEW — roadmap derivata
```

---

## 14. Comandi eseguiti

```
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py migrate --check
.venv/Scripts/python.exe -m pytest apps/calculators/ apps/legal_sources/test_legal_data_test_fixture_isolation.py apps/cases/test_result_page_localization_pass1.py -q
.venv/Scripts/python.exe -m pytest apps/reports/tests.py apps/core/test_csp_language_switcher.py apps/core/tests.py -q
.venv/Scripts/python.exe -m pytest apps/core/ apps/reports/ -q
```

---

## 15. Rischi residui

1. **i18n incompleto (C1)** — l'utente IT vede UI mista IT/EN: blocco di
   qualità pre-go-live. Bottleneck = traduzione firmata Studio.
2. **Integrità promozione (H3/H4)** — APPROVED falsificabile via `notes`
   editabili / `LegalReview` mutabile: indebolisce la garanzia "no calcolo
   falso" **a livello di workflow** (il gate di runtime regge).
3. **NULL `point_value` → 0 € CALCULATED** — falsità sottile possibile se una
   riga APPROVED è incompleta.
4. **Staging non production-ready** (H8/H9): no TLS/proxy, no Redis/Celery,
   `legal_data` scrivibile, `CACHES` non condivisa.
5. **`STUDIO_*` vuoti** — gate `core.E001` blocca la produzione finché lo
   Studio non valorizza Ordine/P.IVA/PEC/polizza.

---

## 16. Prossimi step consigliati

Dettaglio prioritizzato in **`docs/ROADMAP_LEGAL_TECH_SIMULATOR.md`**.
Sintesi (allineata alla `ROADMAP_PRIORITIZED.md` P0–P5 esistente):

1. **Hardening Bundle H-1 (difesa in profondità, basso rischio)**: guard
   `status=='calculated'` su result+PDF; fail-closed su NULL `point_value`;
   `check --deploy` in CI; `CACHES`/Redis condivisa; `LegalReview` append-only;
   ricalcolo verdetto in promozione.
2. **i18n completamento (C1)** + gate CI di copertura `.po`.
3. **Result page** surface di `confidence` + `missing_documents` (H2) e
   `canonical`/OG in `base.html` (H10).
4. **Staging deployabile** (H8/H9): TLS/proxy, Redis+Celery, mount read-only
   `legal_data/sources`, healthcheck su `/healthz/`.
5. **Back-office** (CRM): export CSV PII-safe, lead-360, priorità/urgenza.
6. **Test**: layer Playwright reale; determinismo IT legato al dataset
   approved; coverage PDF (disclaimer/no-EUR-leak).
7. **Attivazione paesi** FR→BE→MA→TN: solo dopo firma Studio dei review package.

---

## Disclaimer

Snapshot a una data specifica. La "verità di sistema" è il codice + il DB; ogni
dato (fonti approved, dataset, formule, simulazioni) può cambiare. Il disclaimer
obbligatorio CLAUDE.md resta valido per ogni simulazione pubblicata.
