# FUNCTIONAL HANDOVER — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Audience:** collaboratori non-tecnici dello Studio, sviluppatori
nuovi, future istanze di Claude Code che riprendono il progetto.
**Scopo:** spiegare in modo narrativo *cosa fa la piattaforma oggi*,
*cosa vede l'utente passo per passo*, *dove finiscono i dati*, *cosa
vede lo Studio*, e *cosa manca prima di poter dare il sito a un
collaboratore reale*.

> Questo documento si limita allo stato di fatto. Per i requisiti di
> prodotto vedi `docs/architecture/PRODUCT_REQUIREMENTS.md`. Per la
> roadmap vedi `docs/architecture/LOCAL_NEXT_STEPS.md` (e il taglio
> P0-P5 in `docs/ROADMAP_PRIORITIZED.md`).

---

## 1. Cosa è la piattaforma, in 5 righe

È un **simulatore web pubblico** dello Studio Legale Internazionale
Badrane. Permette a un visitatore (cittadino, vittima, familiare) di:

1. scegliere un **paese** (IT, FR, BE, MA, TN);
2. scegliere un **tipo di caso** (incidente stradale RCA, successione
   internazionale, …);
3. compilare un **wizard** con i dati del caso;
4. ricevere una **stima orientativa** (range minimo / medio / massimo)
   con fonti citate, oppure un messaggio di "non ancora disponibile";
5. **richiedere un contatto** allo Studio per una valutazione vera.

Solo l'**Italia / incidente stradale RCA** produce oggi un calcolo
reale (basato su TUN 2025 D.P.R. 13 gennaio 2025 n. 12 + tabelle
art. 138 Codice delle Assicurazioni). Tutti gli altri country/case
combo sono **scaffold**: il wizard accetta input, salva la
simulazione, ma il risultato è un messaggio "richiede validazione
legale" + un invito a contattare lo Studio.

Il sito è multilingua: **italiano, francese, inglese, arabo (RTL)**.

---

## 2. Cosa vede l'utente, passo per passo

### 2.1 Atterraggio sul sito

URL pubblico (sviluppo locale): `http://127.0.0.1:8000/it/`.

URL produzione previsto: `https://simulatore.studiolegalebadrane.it/`
o `https://indennizzo.studiolegalebadrane.it/`. Il sito madre
istituzionale (`https://international.studiolegalebadrane.it/`) è
linkato da header e footer.

**Home (`/it/`, `templates/public/home.html`):**

- hero con foto Pexels (se cache disponibile, altrimenti gradiente
  ink-950) + claim *"Simulazioni indicative su risarcimenti e
  successioni, basate su fonti legali validate"*;
- due CTA: **"Avvia simulazione Italia incidente stradale"** (porta
  al wizard IT) e **"Richiedi valutazione legale"** (porta a
  `/contact/`);
- box "Trust by design" con 4 punti (citazione fonti, no numeri
  inventati, range trasparenti, multilingua);
- "MVP coverage": 5 cartoline IT/FR/BE/MA/TN, ognuna porta alla
  landing del paese;
- 3 colonne metodologia (validated sources, transparent ranges,
  human review);
- CTA finale "Pronto per una valutazione legale reale?".

**Landing paese (`/it/countries/italy/`, ecc.):**

- hero foto + descrizione del modulo paese;
- "Stato del modulo": badge OK per IT (`Calcolo indicativo
  disponibile`); badge sand/oro per FR/BE/MA/TN (`Valutazione legale
  preliminare` / `International inheritance review`);
- elenco fonti citate per quel paese (titolo, anno, autorità);
- CTA "Avvia simulazione" (per IT) o "Richiedi valutazione" (per gli
  altri);
- partial condiviso: `templates/public/partials/_module_status_card.html`
  (centralizzato, vedi `PUBLIC_STATUS_BANNER_PARTIAL_PASS7.md`).

**Header e footer (`templates/partials/header.html`, `footer.html`):**

- header con logo Studio, language switcher, link a Studio madre,
  contatti, methodology, disclaimer, privacy;
- footer con link al sito madre, indirizzo Studio, P.IVA/PEC (vedi
  P0-LEG-3 in `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md` per ciò che
  manca formalmente).

### 2.2 Cookie banner

Banner minimale renderizzato in `templates/partials/cookie_consent_banner.html`,
incluso in fondo a `templates/base.html` (l. 62).

- testo: *"This site uses only strictly necessary technical cookies
  (session, CSRF). No analytics or marketing trackers are active."*;
- CTA "OK" (gold-500), persistenza in `localStorage`
  (`badrane.cookieConsent.v1`);
- nessun reject/customize: la piattaforma **non usa cookie non
  essenziali**, quindi non serve un opt-out per analytics/marketing.
  Il banner è informativo, non di consenso.

> **Vincolo deontologico:** se in futuro vengono attivati Pexels
> tracking, Google Analytics, Hotjar, ecc., il banner deve diventare
> un consent manager con opt-in granulare *prima* dell'attivazione.
> Vedi `docs/LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 4.

### 2.3 Wizard (l'utente sceglie cosa simulare)

**Hub `/it/wizard/` (`templates/public/wizard_start.html`):**

- 5 cartoline con il paese e lo stato (Module ready vs Legal sources
  under review);
- l'utente clicca su una cartolina e arriva alla pagina-wizard del
  paese.

**Wizard Italia incidente stradale (`/it/wizard/it/road-accident/`):**

- form `apps.cases.forms.ItalyRoadAccidentWizardForm`;
- campi tipici: età vittima, percentuale invalidità permanente
  (0-100), giorni ITT/ITP, tipo lesione, danno morale (sì/no), spese
  mediche, perdita reddito, presenza danno parentale, concorso di
  colpa stimato. Il wizard validato lato server rifiuta input
  incoerenti (vedi `ITALY_INPUT_VALIDATION_WARNINGS_PASS1.md`);
- consenso privacy obbligatorio (`ConsentPurpose.code=sim_processing`);
- submit POST → `apps.cases.views.wizard_italy_road_accident()`;
- la view chiama `apps.cases.services.run_simulation()` che:
  1. crea `cases.Simulation` con `input_data` (JSONB);
  2. chiama il calculator (`apps.calculators.engines.italy.ItalyRoadAccidentBodilyInjuryCalculator`);
  3. il calculator legge `compensation.CompensationDataset` approved
     (TUN 2025), applica `compensation.CalculationFormula` approved
     (`italy_art_138_tun_2025_base`), produce `CalculationResult`;
  4. salva `output_data`, `sources_snapshot`, `simulation.status=calculated`;
  5. registra `SimulationEvent(type=CALCULATED)`;
  6. registra `PrivacyAuditEvent(type=DATA_PROCESSED, target=cases.Simulation)`;
- redirect a `/wizard/result/<uuid>/`.

**Wizard FR/BE/MA/TN:**

- stesso pattern di flusso, ma il calculator è placeholder
  (`_FrancePlaceholderCalculator`, ecc.);
- l'output è `CalculationResult.status=unavailable_requires_legal_validation`;
- la `Simulation` viene comunque persistita (utile come lead) con
  `status=unavailable_requires_legal_validation`;
- la pagina-wizard mostra **prima** del form un banner "Module under
  legal validation", e dopo il submit la result page indica che la
  valutazione richiede un avvocato.

### 2.4 Result page (`/wizard/result/<uuid>/`, `templates/public/wizard_result.html`)

**Caso "calculated" (oggi solo IT road accident):**

- card range minimo / medio / massimo (es. `26 268,00 / 27 353,00 /
  28 439,00 EUR`);
- "Cosa significa": paragrafo che spiega che il range è un'ancora
  per la trattativa, non una promessa di pagamento;
- "Prossimi passi": revisione PDF, richiesta consulenza, salvataggio
  ID simulazione;
- "Calculation basis": fonti usate (`LegalSource`), formula
  applicata, ipotesi, documenti mancanti, livello di confidenza;
- "Citazioni": ogni fonte con titolo, autorità, anno;
- card disclaimer (black/gold);
- ID simulazione + timestamp + CTA "Scarica PDF" + CTA "Torna al
  wizard" + CTA "Richiedi valutazione legale".

**Caso "unavailable" (FR/BE/MA/TN, IT inheritance_basic):**

- nessun importo;
- card "Valutazione legale preliminare" / "International inheritance
  review" che spiega che il modulo è in revisione legale;
- "Cosa succede dopo": il caso può essere inviato allo Studio per
  valutazione umana;
- CTA "Richiedi valutazione legale";
- ID simulazione + timestamp + disclaimer.

### 2.5 PDF report (`/reports/simulation/<uuid>/pdf/`)

Generato server-side da `apps.reports.views` usando ReportLab.
Contenuto:

- header Studio + logo;
- ID simulazione + data;
- input forniti (con maschera privacy: niente PII non necessaria);
- range stimato (se calculated);
- fonti citate;
- formule applicate;
- ipotesi e documenti mancanti;
- disclaimer obbligatorio CLAUDE.md;
- link al sito madre + CTA contatto.

Il PDF è registrato in `apps.reports.models.SimulationReport` con
SHA-256 (append-only). Vedi `apps/reports/services.py` per il dettaglio.

### 2.6 Form contatto (`/it/contact/`, `apps/crm/views.py`)

- form `apps.crm.forms.ContactForm`: nome, cognome, email, telefono
  (opt), lingua preferita, paese (opt), case type (opt), messaggio
  (min 20 char), checkbox privacy obbligatoria, hidden
  `simulation_public_id` (auto-popolato da `?sim=<uuid>` se viene
  dalla result page);
- honeypot `website` (hidden, mai compilato da utente reale; bot lo
  compilano e vengono droppati silenziosamente, vedi
  `apps/crm/views.py:84-88`);
- rate limit POST (`apps.core.rate_limit.public_post_rate_limit`,
  20 tentativi / 3600 s di default, settable via env);
- submit:
  1. crea `compliance.ConsentRecord(accepted=True)` con FK a
     `ConsentPurpose.code=lead_contact`;
  2. crea `crm.Lead` (con FK a `Simulation` se collegata);
  3. crea `crm.LeadEvent(type=CREATED)`;
  4. registra `compliance.PrivacyAuditEvent(type=CONSENT_GIVEN)`;
  5. invia email transazionale allo Studio
     (`apps.crm.email_notifications.send_lead_notification`);
     - sync per default;
     - async via Celery task se `LEAD_NOTIFICATION_ASYNC_ENABLED=True`,
       con fallback sync se Redis è down;
- redirect a `/it/contact/thank-you/`.

### 2.7 Lingue e RTL

Il sito è disponibile a:

- `/it/` (italiano, default);
- `/fr/` (francese);
- `/en/` (inglese);
- `/ar/` (arabo, `dir="rtl"` automatico in `templates/base.html` l. 2).

Il language switcher nel header chiama `/i18n/setlang/` (Django
standard). Le stringhe sono in `locale/<lang>/LC_MESSAGES/django.po`.
Stato traduzioni: `docs/architecture/I18N_TRANSLATION_STATUS.md`.

---

## 3. Cosa vede lo Studio (back-office)

### 3.1 Admin Django (`/admin/`)

Login con utente `staff` o `superuser` (ruolo `accounts.User.role`).

Sezioni principali:

- **Legal sources**: `LegalSource`, `LegalSourceVersion`,
  `LegalReview`, `LegalSourceAttachment` (upload PDF G.U.,
  decreti, tabelle). Ogni source ha un `status` (draft / extracted /
  needs_review / reviewed / approved / deprecated / replaced). Il
  `simple-history` permette di rivedere chi ha cambiato cosa quando.
- **Compensation**: `CompensationDataset`, `CompensationTableRow`,
  `CalculationFormula`, `ExtractionLog`. È il layer dei dati legali
  versionati.
- **Cases**: `Simulation`, `SimulationEvent`. Ogni simulazione fatta
  dall'utente è qui (anonima se senza login).
- **CRM**: `Lead`, `LeadEvent`. La pipeline lead.
- **Compliance**: `ConsentPurpose`, `ConsentTextVersion`,
  `ConsentRecord`, `DataDeletionRequest`, `PrivacyAuditEvent`,
  `StaffAccessEvent`, `StaffSecurityAlert`.
- **Jurisdictions**: `Country`, `Currency`, `Language`,
  `Jurisdiction` (anagrafica).
- **Reports**: `SimulationReport` (PDF generati con SHA-256).
- **Accounts**: `User` (multi-ruolo: client / lawyer / staff / admin).

### 3.2 MFA admin

Se `ADMIN_MFA_REQUIRED=True` (env var, default False), gli staff
senza OTP verificato vedono una pagina 403 e devono passare per il
flusso TOTP (`django-otp`). Vedi
`docs/architecture/LOCAL_PRODUCT_HARDENING_PASS5_MFA_ADMIN.md`.

### 3.3 Audit log staff

Ogni login/logout/login_failed è registrato in
`compliance.StaffAccessEvent` (con username/UA *hashati*, IP
mascherato `203.0.113.x`, mai PII raw). Vedi
`docs/architecture/LOCAL_PRODUCT_HARDENING_PASS8_STAFF_AUDIT.md`.

In caso di N=5+ failed login entro 900 s viene generato un
`StaffSecurityAlert` (detection-only, no lockout). Vedi
`docs/architecture/LOCAL_PRODUCT_HARDENING_PASS9_STAFF_BRUTE_FORCE.md`.

### 3.4 Email transazionale

Quando un Lead arriva, lo Studio riceve email (config via
`LEAD_NOTIFICATION_TO_EMAILS`). Body privacy-minimized: solo
public_id Lead, timestamp, nome, email, telefono, paese, case_type,
lingua, public_id simulation se presente. **Niente** ip, ua, session
key, internal_notes, message-body.

> **Bug noto P0-2**: se in produzione `LEAD_NOTIFICATION_TO_EMAILS=[]`
> ma `LEAD_NOTIFICATION_ENABLED=True`, il deploy parte ma le email non
> arrivano. Manca un `Django system check` che blocchi il deploy.
> Vedi `docs/AUDIT_DELTA_2026-05-10.md` Sez. 4.1 P0-2.

### 3.5 Dashboard interna

**Non esiste oggi**. L'app `apps.analytics/` è scaffold vuoto
(`models.py` e `views.py` 1 riga commentata). Tutto si fa via Django
admin e quando lo Studio chiede metriche si interroga il DB
manualmente o via `python manage.py shell`. Una dashboard interna
KPI (lead/giorno, conversion, errori calculator) è P3 in
`docs/AUDIT_DELTA_2026-05-10.md`.

---

## 4. Dove finiscono i dati

| Dato | Modello | Tabella DB | Retention |
|---|---|---|---|
| Input simulazione (campi wizard) | `cases.Simulation.input_data` (JSONB) | `cases_simulation` | TBD (policy `DataRetentionPolicy` dichiarata, cron F11) |
| Output simulazione (range, fonti, ipotesi) | `cases.Simulation.output_data` + `sources_snapshot` (JSONB) | `cases_simulation` | come sopra |
| Eventi simulazione | `cases.SimulationEvent` (append-only) | `cases_simulationevent` | append-only, mai cancellati |
| Lead (nome, email, tel, msg) | `crm.Lead` | `crm_lead` | TBD policy GDPR |
| Eventi lead | `crm.LeadEvent` | `crm_leadevent` | append-only |
| Consensi | `compliance.ConsentRecord` | `compliance_consentrecord` | append-only, FK a versione testo |
| Audit privacy | `compliance.PrivacyAuditEvent` | `compliance_privacyauditevent` | append-only |
| Audit staff | `compliance.StaffAccessEvent` | `compliance_staffaccessevent` | retention `STAFF_ACCESS_EVENT_RETENTION_DAYS=90` (dry-run di default) |
| Alert sicurezza staff | `compliance.StaffSecurityAlert` | `compliance_staffsecurityalert` | `STAFF_SECURITY_ALERT_RETENTION_DAYS=180` |
| Richieste cancellazione GDPR | `compliance.DataDeletionRequest` | `compliance_datadeletionrequest` | finché aperta + audit |
| Fonti legali | `legal_sources.LegalSource` (+ history) | `legal_sources_legalsource` | mai cancellate, `status=deprecated/replaced` |
| Dataset legali | `compensation.CompensationDataset` (+ history) | `compensation_compensationdataset` | come sopra |
| Formule | `compensation.CalculationFormula` (+ history) | `compensation_calculationformula` | come sopra |
| PDF report | `reports.SimulationReport` (path su filesystem + SHA-256) | `reports_simulationreport` | append-only, file su `MEDIA_ROOT/reports/` |
| Cookie consent banner dismissal | `localStorage` browser | — | locale browser |

DB:

- **dev locale**: SQLite (`db.sqlite3` nel repo, gitignored);
- **staging/prod**: PostgreSQL 16 (config via `DATABASE_URL`);
- backup: `backups/db_*.sqlite3` per dev (gitignored). Per prod
  policy DR è descritta in `docs/architecture/LOCAL_NEXT_STEPS.md`
  Sez. 5.5 (placeholder, non ancora implementata).

---

## 5. Cosa manca per dare il sito a un collaboratore reale

Ordine di priorità derivato da `docs/AUDIT_DELTA_2026-05-10.md`.

### 5.1 Bloccanti pre go-live (P0)

1. **CSP non emessa lato Django** (`config/settings.py` non ha
   `Content-Security-Policy`). Senza un reverse proxy che la
   aggiunga, la difesa lato browser contro XSS è zero. → fix in
   `docs/SECURITY_INDEX.md`.
2. **`LEAD_NOTIFICATION_TO_EMAILS=[]` non blocca il deploy**: il
   form arriva in DB ma nessuna email allo Studio. Serve un Django
   `check` fatale.
3. **Cookie banner**: oggi è informativo. Se si vuole attivare
   Pexels/analytics, serve consent manager opt-in. Vedi
   `LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 4.
4. **Cliente non-IT end-to-end**: il vincolo cardinale di
   `LOCAL_NEXT_STEPS.md` è "niente prod deploy finché un caso
   non-IT non è verde". Oggi 0/4 paesi non-IT sono attivi.
   Sblocca lo Studio: deve compilare i 4 review package
   (`FRANCE_LEGAL_REVIEW_PACKAGE.md` etc.).

### 5.2 Importanti (P1)

5. **CRM esterno / n8n / WhatsApp**: oggi il Lead resta in DB +
   email; non esiste webhook firmato verso n8n / CRM Studio /
   WhatsApp Business. Vedi `docs/CRM_INTEGRATION_PLAN.md`.
6. **SEO**: hreflang multi-lingua, schema.org `LegalService`/`FAQ`/
   `Article`, content architecture per case_type non sono pronti.
   Vedi `docs/SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md`.
7. **Privacy policy completa**: `templates/public/privacy.html`
   è un *working summary*. Lo Studio deve firmare la versione
   definitiva, in 4 lingue, e versionarla via
   `compliance.ConsentTextVersion`. Vedi
   `LEGAL_COMPLIANCE_CONTENT_AUDIT.md` Sez. 2.
8. **Disclaimer finale**: `templates/public/disclaimer.html` dice
   esplicitamente *"This text is a working version. The final
   wording will be reviewed and signed off by the Studio's legal
   team."* Anche qui lo Studio deve firmare.
9. **Apps placeholder**: `apps.inheritance/`, `apps.cms_content/`,
   `apps.analytics/` sono `models.py`/`views.py` commentati.
   `IT/inheritance_basic` è registrato ma non implementato. Va
   deciso: implementarli o de-registrarli.
10. **`legal_data/` non versionato**: il bind mount staging fallisce
    se la cartella host non esiste. Serve documentation +
    `.gitkeep`.

### 5.3 Polish (P2)

Dettagli visivi minori (cookie banner che si sovrappone al testo su
mobile @ 375 px, font-weight AR/RTL, crop foto hero TN/MA, label
button "Run simulation" su FR/BE wizard). Vedi
`docs/architecture/PRODUCT_RELEASE_READINESS_AUDIT_PASS1.md` Sez.
"Non-blocking polish" e `docs/architecture/PUBLIC_FUNNELS_UX_AUDIT.md`.

### 5.4 Fuori scope MVP

- area cliente con upload documenti firmato;
- firma incarico online;
- pagamenti / fatturazione;
- mobile app nativa;
- calcolatori multi-giurisdizione automatici (es. successioni con
  asset in IT+MA+FR).

---

## 6. Glossario rapido per non-tecnici

| Termine | Significato in questo progetto |
|---|---|
| **Wizard** | Form a step in cui l'utente inserisce i dati del caso. |
| **Simulation** | L'oggetto-pratica che rappresenta un calcolo richiesto. Ha un `public_id` UUID (URL non indovinabile). |
| **Lead** | Una richiesta di contatto dello Studio. Può essere collegata a una Simulation (se viene dal flusso wizard → contact) o standalone. |
| **Range min/mid/max** | I tre numeri prodotti dal calcolatore. NON sono "il risarcimento" — sono limiti di una stima orientativa. |
| **Fonte legale** (`LegalSource`) | Un decreto, una tabella ministeriale, una sentenza. Lo Studio lo importa, lo cataloga, gli assegna uno status. |
| **Status fonte** | `draft → extracted → needs_review → reviewed → approved → deprecated/replaced`. Solo `approved` alimenta calcoli pubblici. |
| **Dataset** (`CompensationDataset`) | Una raccolta strutturata di righe estratte da una fonte (es. 9 191 righe della TUN 2025 art. 138). |
| **Formula** (`CalculationFormula`) | La regola matematica che combina i dati e produce gli importi. Anche le formule hanno status. |
| **Calculator engine** | Il codice Python (in `apps/calculators/engines/`) che orchestrra: input → formula → dataset → output. |
| **Placeholder** | Calculator non implementato — restituisce sempre "richiede validazione legale". Oggi: tutti tranne IT/road accident. |
| **Disclaimer obbligatorio** | Il testo definito in `CLAUDE.md` che deve apparire in ogni risultato. È un vincolo di prodotto, non un suggerimento. |
| **Consent record** | La registrazione del *fatto* che l'utente ha dato il consenso. Versionato per lingua. Append-only. |
| **Audit ledger** (`PrivacyAuditEvent`, `StaffAccessEvent`) | Log immutabile di chi ha fatto cosa quando. Niente PII raw. |

---

## 7. Per Claude Code che riprende il progetto

**Prima di scrivere codice:**

1. leggi `CLAUDE.md` (regole operative);
2. leggi `docs/architecture/PRODUCT_REQUIREMENTS.md` (i 6 requisiti
   canonici);
3. leggi `docs/architecture/GLOBAL_MVP_STATUS.md` (stato di fatto
   per paese);
4. leggi `docs/architecture/LOCAL_NEXT_STEPS.md` (roadmap A→E);
5. leggi `docs/AUDIT_DELTA_2026-05-10.md` (questo audit) per il
   delta operativo.

**Per ogni iter:**

- inizia *read-only* (script di estrazione/audit, mai DB write);
- candidate CSV restano gitignored finché lo Studio non firma;
- ogni `LegalSource` aggiunto al DB in `approved` deve avere
  almeno una `LegalReview` firmata;
- mai LLM-generated values per dati legali — solo estrazione
  deterministica (`pdfplumber`, parser HTML) o trascrizione manuale;
- `pytest`, `ruff`, `black` verdi al merge;
- "Italia invariata: pytest 328+ passed" è un invariant: ogni iter
  che rompe IT deve essere rifatto.

**Non fare mai (regole non negoziabili):**

- inventare importi, coefficienti, formule;
- promettere risultati nei testi pubblici;
- committare segreti;
- attivare feature flag senza review legale firmata;
- saltare il flusso `LegalReview` per accelerare.
