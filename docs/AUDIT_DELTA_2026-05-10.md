# AUDIT DELTA — Indennizzati / Studio Legale Badrane LegalTech Platform

**Data:** 2026-05-10
**Branch:** `audit/indennizzati-platform`
**Modalità:** read-only sul codice, scrittura solo su `docs/`
**Scopo:** consolidare lo stato dell'audit *senza duplicare* lavoro già
firmato in `docs/architecture/`. Mappare i 12 deliverable richiesti dal
brief di onboarding sui file esistenti e identificare i **veri gap** da
colmare in un secondo passaggio.

> Questo documento è il "ponte" tra il brief di audit (che assume un
> codebase greenfield) e lo stato reale del repository (che ha oltre
> 100 file di documentazione architetturale e una baseline operativa
> per Italia + scaffold completo FR/BE/MA/TN).
>
> Niente nuove decisioni di prodotto in questo file: solo mapping,
> verifiche puntuali sui file e backlog gerarchizzato.

---

## 0. Sintesi esecutiva

| Voce | Valore |
|---|---|
| App Django | 13 (3 placeholder: `analytics`, `cms_content`, `inheritance`) |
| Lingue UI configurate | `it`, `fr`, `en`, `ar` (RTL) |
| Calcolatori reali (`_compute_with_sources` override) | **1** (`ItalyRoadAccidentBodilyInjuryCalculator`) |
| Calcolatori placeholder registrati | **5** (FR/BE/MA/TN + IT inheritance_basic) |
| `LegalSource.status=approved` | **2** (entrambe IT) |
| `CalculationFormula.status=approved` | **1** (`italy_art_138_tun_2025_base`) |
| `CompensationDataset.status=approved` | **2** (TUN 2025 danno biologico + danno morale) |
| Pagine pubbliche probate (release-readiness pass1) | 78 (0 con issue, verdict OK) |
| Documenti `docs/` esistenti | 105 file `.md` |
| Audit script riproducibili | 5+ in `scripts/` (audit_global_mvp_status, audit_public_content_hygiene, audit_public_result_messages, audit_calculator_diagnostic_strings, audit_local_css_coverage) |
| Audit di release attuale | `verdict: OK`, IT baseline 35/10/0 invariata |

**Conclusione operativa:** la piattaforma è **NON greenfield**. È in
stato `Fase A — Studio review` della roadmap canonica
(`docs/architecture/LOCAL_NEXT_STEPS.md`): i review package per
FR/BE/MA/TN sono pronti, in attesa che lo Studio compili le checklist.
Non c'è urgenza P0 di natura tecnica scoperta in questo audit; ci
sono **gap documentali** in 5 aree (CRM/n8n integrazione,
SEO multi-lingua, QA matrix utenti, deontologia contenuti pubblici,
functional handover per collaboratori).

---

## 1. Inventario tecnico (essenziale)

### 1.1 Albero `apps/`

| App | Ruolo | Stato |
|---|---|---|
| `accounts` | `User` (AbstractUser) + ruolo (client/lawyer/staff/admin) + `preferred_language` | Operativo |
| `core` | landing, methodology, disclaimer, sitemap, observability (Sentry opt-in), MFA admin middleware, rate-limit | Operativo |
| `jurisdictions` | `Country`, `Currency`, `Language`, `Jurisdiction` (anagrafica F1) | Operativo, seed via `seed_jurisdictions` |
| `legal_sources` | `LegalSource`, `LegalSourceVersion`, `LegalReview`, `LegalSourceAttachment` | Operativo, 25 fonti registrate (2 approved) |
| `compensation` | `CompensationDataset`, `CompensationTableRow`, `CalculationFormula`, `ExtractionLog` | Operativo, 5 dataset / 41 309 righe |
| `calculators` | engines plug-in registry (5 paesi), `BaseCalculator` con guardrail `unavailable_requires_legal_validation` | 1 REAL (IT road accident), 5 placeholder |
| `cases` | `Simulation`, `SimulationEvent` (append-only), wizard views per paese/case_type | Operativo, IT funzionante |
| `crm` | `Lead`, `LeadEvent` (append-only), contact form + honeypot, email transazionale (sync/async fallback) | Operativo, integrazione esterna assente |
| `compliance` | `ConsentPurpose`, `ConsentTextVersion`, `ConsentRecord`, `PrivacyAuditEvent` | Operativo |
| `reports` | `SimulationReport` (append-only, SHA-256 del PDF) | Operativo per IT |
| `inheritance`, `cms_content`, `analytics` | `models.py` + `views.py` commentati a 1 riga | Placeholder F0 |

### 1.2 Routing pubblico (con prefisso lingua, `i18n_patterns`)

| Path | Stato |
|---|---|
| `/{lang}/` | home pubblica (`apps.core.views.home`) |
| `/{lang}/methodology/` `/disclaimer/` `/privacy/` | static legal pages |
| `/{lang}/countries/` + `italy/`, `france/`, `belgium/`, `morocco/`, `tunisia/` | landing SEO per paese (`apps.core`) |
| `/{lang}/wizard/` | router |
| `/{lang}/wizard/it/road-accident/` | **operativo (calcolo TUN 2025)** |
| `/{lang}/wizard/fr/road-accident/`, `/be/road-accident/` | scaffold (calcolo `unavailable`) |
| `/{lang}/wizard/ma/inheritance/`, `/tn/inheritance/` | scaffold (calcolo `unavailable`) |
| `/{lang}/wizard/result/<uuid>/` | viewer simulazione (calculated o unavailable) |
| `/{lang}/contact/` `/contact/thank-you/` | lead form pubblico |
| `/reports/simulation/<uuid>/pdf/` | PDF report (ReportLab) |
| `/sitemap.xml`, `/healthz/` | infrastruttura |
| `/admin/` | Django admin (con MFA opt-in) |

### 1.3 Stack runtime (da `requirements.txt`)

- Django 5.2 LTS · DRF 3.15 · django-htmx 1.21 · psycopg 3.2
- modeltranslation 0.19 · simple-history 3.7 · auditlog 3.0 · import-export 4.1
- celery 5.4 · redis 5.0
- reportlab 4.2 · Pillow 10.4 · beautifulsoup4 + lxml
- sentry-sdk[django] 2.x (opt-in, scrubber PII custom)
- django-otp 1.5 + qrcode 7.4 (admin MFA opt-in)
- pytest 8.3 · pytest-django 4.9 · factory-boy 3.3 · playwright 1.47 · coverage 7.6
- ruff 0.6 · black 24.8 · mypy 1.11

### 1.4 Hardening attivo (`config/settings.py`)

Verificato in `config/settings.py`:

- `DEBUG=False` → SSL redirect, HSTS 30gg, secure cookies, X-Frame-Options DENY,
  REFERRER_POLICY same-origin, NOSNIFF, proxy SSL header (`l. 50–69`)
- guardrail fatale se `SECRET_KEY` parte con `django-insecure-` in prod (`l. 65–69`)
- `LocaleMiddleware` + `i18n_patterns` per lingua via URL
- `simple_history` + `auditlog` middleware globali
- `AdminMFAMiddleware` (opt-in via `ADMIN_MFA_REQUIRED=False` default)
- `RedactPIIFilter` su tutti gli handler logging (email/telefoni/CF mascherati)
- `public_post_rate_limit` cache-based su `/contact/` e wizard POST
- Sentry con `send_default_pii=False` di default + scrubber custom
- Staff brute-force detector → `StaffSecurityAlert` (detection-only, no lockout)
- Staff audit retention con dry-run di default

---

## 2. Mapping 12 deliverable richiesti → file esistenti

> Il brief di audit (FASE 12) chiede 12 documenti. Per ciascuno indico
> **stato** (✅ coperto / 🟡 parziale / ❌ gap), **file canonico
> esistente**, e l'**azione consigliata**.

| # | Deliverable richiesto | Stato | File esistente / proposto |
|---|---|---|---|
| 1 | `docs/AUDIT_REPOSITORY_MAP.md` | 🟡 | `GLOBAL_MVP_STATUS.md` + sez. 1 di **questo file** coprono inventario + flow + dipendenze. **Azione**: nessun nuovo file, citare entrambi nel README delle docs. |
| 2 | `docs/FUNCTIONAL_HANDOVER.md` | ❌ | Nessun file dedicato a "cosa vede l'utente / cosa succede al submit / cosa vede lo staff" in forma narrativa per collaboratori non-tecnici. **Azione**: creare. |
| 3 | `docs/CALCULATION_ENGINE_AUDIT.md` | 🟡 | Distribuito in `TUN_MORAL_RANGE_ENGINE.md`, `CALCULATOR_DIAGNOSTIC_STRINGS_AUDIT.md`, `CALCULATOR_WARNING_STRINGS_TRANSLATABLE_PASS1.md`, `EU_650_APPLICABLE_LAW_DECISION_ENGINE_SKELETON.md`, `APPLICABLE_LAW_ENGINE_INTEGRATION_PASS1.md`, `MOROCCO_ENGINE_ACTIVATION_BLOCKERS_GUARD_PASS1.md`. **Azione**: creare un *index* (`docs/architecture/CALCULATION_ENGINE_INDEX.md`) che linka i 6 file e descrive l'architettura attuale del registry, **senza** duplicare il contenuto. |
| 4 | `docs/CALCULATION_ENGINE_TARGET_ARCHITECTURE.md` | ✅ | `MVP_STATUS.md` + `LOCAL_NEXT_STEPS.md` + `GLOBAL_MVP_STATUS.md` + i 4 `*_MODULE_STATUS.md` definiscono già l'architettura target (engine registry, formule versionate, datasets, fonti). **Azione**: nessun nuovo file. |
| 5 | `docs/MULTI_COUNTRY_ARCHITECTURE.md` | 🟡 | `FRANCE_MODULE_STATUS.md`, `BELGIUM_MODULE_STATUS.md`, `MOROCCO_INHERITANCE_MODULE_STATUS.md`, `TUNISIA_INHERITANCE_MODULE_STATUS.md` esistono, ma manca un *cross-country* doc che descriva il pattern `CalculatorAdapter`, lo schema fonti/dataset/formula, le regole DIP (Reg. 650/2012, Loi 98-97), il lifecycle `draft → reviewed → approved → deprecated → replaced`. **Azione**: creare `docs/architecture/MULTI_COUNTRY_PATTERN.md`. |
| 6 | `docs/UX_UI_AUDIT.md` | ✅ | `PUBLIC_FUNNELS_UX_AUDIT.md` (pass 3, completo per tutti i wizard + result + contact), `PUBLIC_LIGHTHOUSE_VISUAL_QA_PASS1.md`, `PUBLIC_RELEASE_POLISH_PASS5.md`, `PUBLIC_FUNNELS_POLISH_PASS4_A11Y_PERF_I18N.md`, `FRONTEND_LOCAL_CSS_PREMIUM_VISUAL_QA_PASS1.md`, `PUBLIC_SITE_QA_POLISH_PASS1`/`PASS2.md`. **Azione**: nessun nuovo file. |
| 7 | `docs/SECURITY_AUDIT.md` | 🟡 | Distribuito in 7 pass: `LOCAL_PRODUCT_HARDENING_PASS1` (rate-limit), `PASS2_EMAIL`, `PASS3_SENTRY`, `PASS5_MFA_ADMIN`, `PASS7_CELERY`, `PASS8_STAFF_AUDIT`, `PASS9_STAFF_BRUTE_FORCE`, `PASS10_STAFF_AUDIT_RETENTION`. **Azione**: creare `docs/architecture/SECURITY_INDEX.md` che mappa controllo → pass corrispondente + checklist `manage.py check --deploy` + posture CSP (vedi Sez. 4.1 di questo file). |
| 8 | `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md` | ❌ | Nessun documento copre l'**audit deontologico dei contenuti pubblici** (no over-promise, indicazione albo/P.IVA/PEC, assicurazione professionale, conflitto interessi, condizioni incarico scritto, "valutazione gratuita", "casi reali", uso recensioni, claim comparativi, "nessuna spesa anticipata"). `PUBLIC_CONTENT_HYGIENE_AUDIT_PASS5.md` copre solo lessico tecnico/leak ID, non deontologia. **Azione**: creare. |
| 9 | `docs/SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md` | 🟡 | `PRODUCT_COUNTRY_LANDING_SEO.md` copre 5 country landing. Manca: strategia slug multi-lingua, hreflang, FAQ schema, LegalService schema, breadcrumbs, content architecture per case_type (`/it/risarcimento-danni/`, `/it/calcolo-risarcimento-incidente-stradale/`, `/it/tabella-unica-nazionale-2025/`, ecc.), strategia blog/guide. **Azione**: creare. |
| 10 | `docs/CRM_INTEGRATION_PLAN.md` | ❌ | `apps/crm/` ha `Lead` GDPR-aware + email transazionale (sync/async via Celery), ma **nessun documento** descrive: webhook firmato HMAC, idempotency-key, retry policy, integrazione n8n, mapping Lead → CRM esterno, flag privacy per il transit, audit log dell'invio, recovery in caso di failure. **Azione**: creare. |
| 11 | `docs/QA_TEST_PLAN.md` | ❌ | `LIVE_SIMULATION_MATRIX.md` esiste ma è una tabella sintetica di smoke tests; non è la **matrice realistica utente** in 15 casi (italiano 35a 30%, marocchino in IT, famiglia all'estero per decesso IT, offerta assicurativa già ricevuta, INAIL liquidato, errore diagnostico, francese/belga, RTL arabo, form spam, upload troppo grande, input invalidi, mobile Safari, JS off, errore CRM/n8n). **Azione**: creare. |
| 12 | `docs/ROADMAP_PRIORITIZED.md` | 🟡 | `LOCAL_NEXT_STEPS.md` ha 5 fasi A→E *country-by-country*; il brief chiede 6 fasi *P0→P5* per area trasversale. **Azione**: creare `docs/ROADMAP_PRIORITIZED.md` come *vista P0/P1/P2/P3* derivata da LOCAL_NEXT_STEPS (cross-link, non duplicato). |

**Totale gap reali:** 5 file da creare ex-novo (#2, #8, #9, #10, #11)
+ 4 file di indice/cross-link (#3, #5, #7, #12) che linkano e
sintetizzano materiale esistente. Nessun deliverable richiede di
riscrivere documenti già firmati.

---

## 3. Cosa il brief assume vs. cosa il repo ha già

Il brief di onboarding è scritto come se il codebase fosse di
prima scoperta. Per chiarezza, queste assunzioni vanno corrette:

| Assunzione del brief | Realtà nel repo |
|---|---|
| "Verifica se il calcolo è lato client o server" | **Lato server**, sempre. Il frontend (HTMX + Alpine) non contiene formule. |
| "Verifica se i dati TUN sono hardcoded" | **No.** TUN 2025 è in `CompensationDataset` + `CompensationTableRow` (9 191 + 27 573 righe), legato a `LegalSource.status=approved` con 2 `LegalReview` firmate. |
| "Verifica se esiste versionamento delle tabelle" | **Sì.** `LegalSource.status` (draft/extracted/needs_review/reviewed/approved/deprecated/replaced) + `LegalSourceVersion` + `simple-history` su `LegalSource`/`LegalReview`/`Lead`/`Simulation`/`CompensationDataset`. |
| "Verifica se esistono test matematici" | **Sì.** `apps/calculators/test_*.py` (~12 K LOC) + `apps/cases/test_*.py` (~3.9 K LOC). pytest baseline 328+ in CI locale. |
| "Verifica se c'è disclaimer vicino al risultato" | **Sì.** Disclaimer obbligatorio CLAUDE.md è renderizzato in `templates/public/wizard_result.html` come ultima card black/gold. Verificato in `PUBLIC_FUNNELS_UX_AUDIT.md` (status PASS). |
| "Verifica se vengono salvati input/output" | **Sì.** `Simulation.input_data` (JSONB) + `Simulation.output_data` (JSONB) + `sources_snapshot` immutabile. `SimulationReport` registra anche SHA-256 del PDF. |
| "Verifica DEBUG/segreti in repo" | `DEBUG` env-driven default `False`. `SECRET_KEY` env-driven, fail-fast in prod sul prefix insecure (vedi `config/settings.py:65-69`). Nessun `.env` committato (`.gitignore`). |
| "Avvia server, fai screenshot before/" | Già fatto ripetutamente: `docs/screenshots/live_qa/release_readiness_audit_pass1/after/` (23 frame desktop + 8 mobile + 7 RTL/locale, ultima in PASS1). |
| "Imposta CSP" | **Lato Django no.** Si assume CSP gestita da nginx/reverse proxy davanti. **Da verificare** in deploy (vedi P1 sotto). |

---

## 4. Bug list e backlog gerarchizzato

I rischi sotto sono **derivati esclusivamente da file letti** in
questo audit (no invenzione). Ogni voce cita la fonte.

### 4.1 P0 — Bloccanti pre-deploy o pre-uso pubblico

> Il release-readiness audit pass 1 non rileva blocchi. I P0 elencati
> qui sono blocchi *strutturali* per il go-live esterno, **non bug
> attivi sul codice locale corrente**.

| ID | Voce | Fonte | Impatto | Proposta |
|---|---|---|---|---|
| P0-1 | Header CSP non emesso da Django | `config/settings.py` (nessuna `CSP_*` né middleware csp) | XSS/clickjacking lato browser non mitigato in prod se nginx non lo aggiunge | Aggiungere `django-csp` o aggiungere reverse-proxy template che emette `Content-Security-Policy` `default-src 'self'` + esenzioni mirate per font/static/Pexels. **Azione**: documentare nel `docs/architecture/SECURITY_INDEX.md` e creare task. |
| P0-2 | `LEAD_NOTIFICATION_TO_EMAILS` default vuoto | `config/settings.py:289` | Lead arrivati in DB ma email allo Studio non inviata in prod se la env var non è settata | Già coperto da `LEAD_NOTIFICATION_ENABLED=True` ma manca **alert / health check** che segnali `LEAD_NOTIFICATION_TO_EMAILS=[]` come errore di configurazione fatale al deploy. **Azione**: aggiungere check Django in `apps.crm.checks` (Django system checks). |
| P0-3 | Nessun caso d'uso end-to-end **non-IT** funzionante | `GLOBAL_MVP_STATUS.md` Sez. 7.1 | Vincolo cardinale di `LOCAL_NEXT_STEPS.md`: niente prod deploy finché un caso non-IT non è verde. **Stato**: Studio non ha ancora compilato i 4 review package | Tracking in roadmap. **Azione**: nessuna in questo audit; resta blocco *legal review*. |
| P0-4 | Cookie banner: stato attuale | da verificare in template (non risulta in `apps/core` o `templates/_base.html`) | GDPR — se mancante o non opt-in, esposizione consenso non valido | **Azione**: verifica live in FASE 10 e doc in `LEGAL_COMPLIANCE_CONTENT_AUDIT.md`. |

### 4.2 P1 — Importanti per qualità prodotto

| ID | Voce | Fonte | Impatto | Proposta |
|---|---|---|---|---|
| P1-1 | Apps `inheritance`, `cms_content`, `analytics` sono scaffold vuoti | `apps/inheritance/{models,views}.py` 1 riga commentata; idem `cms_content`, `analytics` | Confusione: `inheritance_basic` IT è registrato ma non implementato; CMS e analytics non operativi | **Azione**: documentare scope in `docs/FUNCTIONAL_HANDOVER.md` (out-of-scope MVP) o rimuovere registrazione `IT/inheritance_basic` finché non implementata. |
| P1-2 | Test file con suffix `_pass1`, `_pass2`, `_pass3` non consolidati | `apps/cases/test_*_pass*.py`, `apps/calculators/test_*_draft*.py`, `apps/legal_sources/test_*_pass*.py` | Diff history rumorosa; unclear quale è canonico | **Azione**: backlog tecnico — consolidamento dopo che la feature sottostante è stabile. Non urgente. |
| P1-3 | `legal_data/` non versionato ma referenziato da `docker-compose.staging.yml` | `docker-compose.staging.yml` mount `./legal_data:/app/legal_data` | Build staging fallisce se cartella host non esiste | **Azione**: aggiungere `.gitkeep` + struttura placeholder + runbook (`docs/deploy/STAGING_DEPLOY.md` da estendere). |
| P1-4 | CRM esterno / n8n / WhatsApp non integrati | `apps/crm/views.py` solo email; nessun webhook | Lead resta solo in DB + email — non sincronizzato con CRM Studio | **Azione**: scrivere `docs/CRM_INTEGRATION_PLAN.md` (gap deliverable #10). |
| P1-5 | SEO: hreflang multi-lingua, FAQ/LegalService schema | nessun file in `docs/seo/`; `PRODUCT_COUNTRY_LANDING_SEO.md` non copre schema.org | Visibilità organica IT/FR/AR/EN sub-ottimale | **Azione**: scrivere `docs/SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md` (gap deliverable #9). |

### 4.3 P2 — Polish / consolidamento

| ID | Voce | Fonte | Proposta |
|---|---|---|---|
| P2-1 | Duplicazione `docs/legal-sources` vs `docs/legal_sources` | `find docs -type d` mostra entrambi | Verificare se `docs/legal-sources/` (con trattino) è dead — eventualmente rimuovere. |
| P2-2 | Mobile @ 375 px: cookie banner copre testo card su result IT | `PRODUCT_RELEASE_READINESS_AUDIT_PASS1.md` Sez. "Non-blocking polish" | Tightening spaziature sotto `<sm` viewport. |
| P2-3 | AR/RTL typography weight più pesante | `PRODUCT_RELEASE_READINESS_AUDIT_PASS1.md` Sez. "Non-blocking polish" | font-weight tune-up AR-only. |
| P2-4 | Crop foto hero TN/MA differenti tra desktop/mobile | `PRODUCT_RELEASE_READINESS_AUDIT_PASS1.md` Sez. "Non-blocking polish" | Standardizzare aspect ratio source asset. |
| P2-5 | Banner FR/BE wizard "Run simulation" sembra calculator-ready | `PUBLIC_FUNNELS_UX_AUDIT.md` Sez. `/wizard/fr/...` | Etichetta button → "Submit for legal review". |

### 4.4 P3 — Nice-to-have

| ID | Voce | Proposta |
|---|---|---|
| P3-1 | Area cliente per upload documenti firmato | Out-of-scope MVP per `LOCAL_NEXT_STEPS.md` Sez. 6, ma desiderio prodotto. Tracciare in `docs/ROADMAP_PRIORITIZED.md` come Fase 5 / "ultra premium". |
| P3-2 | Notifiche push / WhatsApp Business | Idem. |
| P3-3 | Dashboard interna per Studio (KPI lead, conversion, errori calculator) | `analytics` app è placeholder. Idem. |

---

## 5. Verifica claim del brief — riassunto puntuale

| Claim brief | Esito |
|---|---|
| "Calcolo lato server, autorevole" | ✅ confermato (`apps/calculators/` + `apps/compensation/services`). |
| "Versionamento fonti / fonte→formula→dataset" | ✅ confermato (`LegalSource.status` lifecycle + `CalculationFormula.status` + `CompensationDataset.status`). |
| "Disclaimer vicino al risultato" | ✅ confermato (`templates/public/wizard_result.html`). |
| "Multi-lingua reale (IT/FR/EN/AR + RTL)" | ✅ confermato (`config/settings.py` LANGUAGES, `i18n_patterns`, locale dir). |
| "Cookie banner / GDPR" | ⚠️ da verificare visivamente in FASE 10. |
| "Honeypot anti-spam" | ✅ confermato (`apps/crm/views.py:84-88`, `is_likely_bot`). |
| "Rate limit form" | ✅ confermato (`apps/core/rate_limit.py` decorator + settings `PUBLIC_POST_RATE_LIMIT_*`). |
| "PII redaction nei log" | ✅ confermato (`config/logging_filters.RedactPIIFilter`). |
| "Admin MFA" | ✅ confermato (opt-in via `ADMIN_MFA_REQUIRED`). |
| "Audit log staff" | ✅ confermato (`StaffAccessEvent`, `StaffSecurityAlert`). |
| "Retention policy" | ✅ scaffold (`STAFF_AUDIT_RETENTION_*` + dry-run di default). |
| "PDF report server-side" | ✅ confermato (`reportlab`, `apps.reports.SimulationReport`). |
| "Docker / Docker Compose" | ✅ confermato (`Dockerfile`, `docker-compose.local.yml`, `docker-compose.staging.yml`). |
| "Tests realistici" | 🟡 esistono test unit + visual QA, **manca matrix utente realistica 15 casi** (gap #11). |
| "CSP" | ❌ assente lato Django (P0-1). |

---

## 6. Proposta primo batch P0

> **Niente codice modificato in questo audit.** Il batch sotto è una
> proposta da confermare prima di passare alla scrittura.

**Batch P0-A (documentale, gap deliverable):**

1. `docs/FUNCTIONAL_HANDOVER.md` — handover funzionale collaboratori (gap #2).
2. `docs/CRM_INTEGRATION_PLAN.md` — webhook firmato + n8n + idempotency + retry (gap #10).
3. `docs/SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md` — hreflang + schema.org + slug (gap #9).
4. `docs/QA_TEST_PLAN.md` — 15 casi utente realistici + screenshot before (gap #11).
5. `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md` — deontologia contenuti pubblici (gap #8).
6. `docs/architecture/MULTI_COUNTRY_PATTERN.md` — index pattern adapter cross-country (gap #5 indexing).
7. `docs/architecture/CALCULATION_ENGINE_INDEX.md` — index 6 file engine esistenti (gap #3 indexing).
8. `docs/architecture/SECURITY_INDEX.md` — index 7 hardening pass + checklist `--deploy` (gap #7 indexing).
9. `docs/ROADMAP_PRIORITIZED.md` — vista P0–P5 derivata da LOCAL_NEXT_STEPS (gap #12).

**Batch P0-B (codice, solo dopo batch A approvato):**

1. `apps/crm/checks.py`: Django system check che fa fail di
   `manage.py check` se in prod `LEAD_NOTIFICATION_TO_EMAILS=[]` con
   `LEAD_NOTIFICATION_ENABLED=True` (P0-2).
2. CSP: scelta tra `django-csp` o reverse-proxy template; documentazione
   poi implementazione minima (P0-1).

**Batch P1 — solo a valle di conferma utente** (consolidamento test
file `_passN`, scaffold cleanup `inheritance`/`cms_content`/`analytics`,
`legal_data/.gitkeep`).

---

## 7. Browser live — stato

Screenshot live esistono già in:

- `docs/screenshots/live_qa/release_readiness_audit_pass1/after/` (78 pagine)
- `docs/screenshots/live_qa/eu_650_real_source_restore_pass1/` (recente)
- vari `docs/screenshots/live_qa/<iter_name>/` per ciascun iter

**Decisione:** in questo audit **non** rifaccio screenshot generici
(coperti da PASS1). Faccio solo screenshot mirati ai 5 deliverable
mancanti se necessario, in `artifacts/screenshots/audit_delta_2026-05-10/`.
Il QA_TEST_PLAN richiederà screenshot specifici per i 15 casi
utente.

---

## 8. Branch e commit

- Branch creato: `audit/indennizzati-platform` (da `master`).
- Modifiche pendenti pre-audit (Tunisia/EU 650/QA pass2) sono state
  portate con sé sul branch (`git status` mostra ancora
  modificati/untracked). **Decisione**: lasciarle in piedi finché
  l'utente non chiede di committare o stashare separatamente.
- Nessun commit ancora effettuato sul branch.

---

## 9. Cosa NON è in questo audit

- ❌ Modifiche al codice Python/template/CSS.
- ❌ Modifiche al DB (no migrations, no fixture import).
- ❌ Riscrittura di file di audit esistenti.
- ❌ Promozione di `LegalSource` o creazione `LegalReview`.
- ❌ Attivazione di feature flag.
- ❌ Esecuzione di `pytest` / `ruff` / `black` (non richiesto in fase audit).

---

## 10. Prossimo step

Attendo conferma utente sui seguenti punti:

1. **OK ai 5 file gap (#2, #8, #9, #10, #11) come priorità di scrittura?**
2. **OK ai 4 file index/cross-link (#3, #5, #7, #12)?** (più leggeri,
   ~1 paginata ciascuno)
3. **Browser live: rifaccio screenshot mirati per i 15 casi del
   QA_TEST_PLAN, oppure riuso quelli esistenti dove sufficienti?**
4. **Batch P0-B (codice CSP + system check): scrivere ora, dopo i doc,
   o dopo conferma utente separata?**

Senza conferma su questi 4 punti non procedo a scrittura ulteriore.
