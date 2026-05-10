# QA TEST PLAN — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Audience:** dev, QA, Studio (validazione output legale).
**Scopo:** matrice di **15 casi utente realistici** che lo Studio
testerebbe prima di accettare il go-live, con dati fittizi, step
operativi, output atteso, screenshot pianificati, severità in caso
di bug.

> Questo piano integra (non sostituisce) la matrice tecnica già
> presente in `docs/architecture/LIVE_SIMULATION_MATRIX.md` (focus
> engine-level, 7 casi tecnici). Qui il taglio è **utente reale e
> situazione operativa**.

---

## 0. Setup

### 0.1 Server locale

```bash
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

Per QA con webhook (`QA-15`), abilitare:
```
DJANGO_DEBUG=true
LEAD_NOTIFICATION_ENABLED=true
LEAD_NOTIFICATION_TO_EMAILS=qa@studiolegalebadrane.local
EMAIL_BACKEND=django.core.mail.backends.locmem.EmailBackend
```

### 0.2 DB di test

DB SQLite con seed legale corrente (`legal_data/sources/italy/...`
+ `python manage.py import_italy_tun_2025` + `import_italy_tun_2025_moral`).
Verifica baseline:

```python
.venv/Scripts/python.exe -c "
from apps.cases.services import run_simulation
res = run_simulation('IT', 'road_accident_bodily_injury',
                      {'victim_age': 35, 'permanent_disability_percentage': 10, 'fault_percentage': 0})
print(res)
"
# atteso: 26268.00 / 27353.00 / 28439.00 EUR (canarino)
```

### 0.3 Browser

- Playwright MCP (Chrome 130+) per la maggior parte;
- Safari mobile reale (iPhone) per QA-12 se possibile;
- Firefox 128+ per QA-09/QA-14 (controllo cross-browser);
- Chrome DevTools "Slow 3G" throttling per QA-13;
- Chrome con JavaScript disabilitato per QA-14
  (`chrome://settings/javascript`).

### 0.4 Output atteso per ogni caso

Ogni QA ha:

- **obiettivo**;
- **dati fittizi** (mai dati reali);
- **step**;
- **risultato atteso**;
- **screenshot** in `docs/screenshots/delta_audit_2026-05-10/before/`;
- **log** rilevanti (URL chiamati, eventi DB, email/webhook);
- **severità** se bug (P0 bloccante / P1 importante / P2 polish / P3 nice).

---

## 1. La matrice (15 casi)

| ID | Slug | Persona | Paese caso | Lingua UI | Calc available | Screenshot già? |
|---|---|---|---|---|---|---|
| QA-01 | `italian-road-30pct` | Italiano residente IT | IT | it | ✅ | parziale (PASS1) |
| QA-02 | `moroccan-pedestrian-no-docs` | Marocchino in IT | IT | fr | ✅ | no |
| QA-03 | `family-abroad-wrongful-death` | Famiglia all'estero | IT | en | ❌ (decesso non implementato) | no |
| QA-04 | `insurance-offer-already-received` | Italiano post-offerta assicurativa | IT | it | ✅ | no |
| QA-05 | `inail-already-paid` | Lavoratore italiano | IT | it | 🟡 (workplace non implementato) | no |
| QA-06 | `late-diagnosis-medical` | Paziente italiano | IT | it | 🟡 (medical_malpractice non implementato) | no |
| QA-07 | `french-belgian-cross-border` | Francese sinistro in BE | FR/BE | fr | ❌ scaffold | parziale |
| QA-08 | `arab-user-rtl-morocco-inheritance` | Cittadino marocchino | MA | ar | ❌ scaffold | parziale (PASS1) |
| QA-09 | `form-spam-attempt` | Bot generico | — | — | n/a | no |
| QA-10 | `oversized-upload` | (riservato area cliente futura) | — | — | n/a (P3) | non testabile oggi |
| QA-11 | `invalid-calculator-inputs` | Utente che inserisce input incoerenti | IT | it | ✅ (path errore) | no |
| QA-12 | `mobile-safari-390-result` | Utente iPhone | IT | it | ✅ | parziale (PASS1) |
| QA-13 | `slow-3g-connection` | Utente connessione lenta | IT | it | ✅ | no |
| QA-14 | `no-javascript` | Utente con JS off | IT | it | ✅ | no |
| QA-15 | `crm-webhook-failure` | (riservato webhook futuro) | IT | it | n/a (P1) | non testabile oggi |

`✅` calculator funzionante · `🟡` case_type non ancora implementato
ma il flusso "unavailable" deve mostrarsi correttamente · `❌` scaffold
deliberato.

---

## 2. Casi dettagliati

### QA-01 — Utente italiano, incidente stradale, 35 anni, invalidità 30%

> Canarino del calcolatore IT. Verifica che il flusso end-to-end
> "happy path" non sia regredito.

**Persona**: Mario Rossi, 35 anni, residente Milano, italiano. Tamponato
in autostrada il 2026-04-15. Refertata invalidità permanente 30%, ITT
60 giorni, ITP 30%, danno morale concesso, niente concorso di colpa.

**Dati fittizi**:

| Field | Value |
|---|---|
| URL | `/it/wizard/it/road-accident/` |
| Età vittima | 35 |
| % invalidità permanente | 30 |
| ITT giorni | 60 |
| ITP % residua | 30 |
| Danno morale | sì |
| Spese mediche | 4 500 EUR |
| Perdita reddito | 8 000 EUR |
| Danno parentale | no |
| Concorso di colpa | 0% |
| Privacy checkbox | ✅ |
| Email contatto (post wizard) | qa01@example.com |

**Step**:

1. apri `/it/`;
2. clicca "Avvia simulazione Italia incidente stradale";
3. compila form;
4. submit;
5. arriva a `/wizard/result/<uuid>/`;
6. clicca "Scarica PDF report";
7. clicca "Richiedi valutazione legale";
8. compila contact form, submit;
9. arriva a `/contact/thank-you/`.

**Risultato atteso**:

- result page mostra range min/mid/max in EUR (con virgola decimale
  italiana);
- "Calculation basis" cita `D.P.R. 12/2025 — Tabella Unica Nazionale 2025`;
- PDF scarica, `%PDF` magic bytes;
- ID simulazione UUID visibile;
- contact form pre-popolato con `?sim=<uuid>`;
- thank-you page rinforza disclaimer.

**Verifiche backend** (Django shell):

```python
Simulation.objects.latest('created_at').status == 'calculated'
Lead.objects.latest('created_at').simulation_id is not None
LeadEvent.objects.filter(event_type='created').exists()
ConsentRecord.objects.filter(purpose__code='lead_contact').exists()
PrivacyAuditEvent.objects.filter(event_type='consent_given').exists()
```

**Screenshot pianificati**:

- `QA-01_italian_road_30pct_step1_form.png` (form pre-submit)
- `QA-01_italian_road_30pct_step2_result.png` (range + sources card)
- `QA-01_italian_road_30pct_step3_pdf.png` (snapshot prima pagina PDF)
- `QA-01_italian_road_30pct_step4_thankyou.png`

**Severità se fail**: **P0 bloccante** (regression IT è
inammissibile).

---

### QA-02 — Marocchino residente in IT, pedone investito, documenti incompleti

> Verifica che il flusso "missing documents" sia chiaro e
> deontologicamente corretto. Lingua UI: francese (target marocchino
> francofono in IT).

**Persona**: Yassine El Amrani, 42 anni, residente Bologna, cittadino
marocchino con permesso di soggiorno. Investito sulle strisce pedonali
2026-03-10. Non ha ancora copia del verbale, né cartella clinica
completa.

**Dati fittizi**:

| Field | Value |
|---|---|
| URL | `/fr/wizard/it/road-accident/` (lingua FR, caso IT) |
| Età vittima | 42 |
| % invalidità | 0 (non ancora certificata) |
| ITT giorni | 90 |
| ITP % residua | sconosciuta |
| Spese mediche | 2 800 EUR |
| Concorso di colpa | 0% (pedone) |

**Step**:

1. switcher lingua → FR;
2. compila wizard con `permanent_disability_percentage=0`;
3. submit;
4. result page;
5. compila contact form aggiungendo "documents pending".

**Risultato atteso**:

- result page mostra range basato su 0% invalidità (solo ITT/spese
  mediche), con warning esplicito "Documenti mancanti: certificato
  medico definitivo, verbale di sinistro";
- la `missing_documents` array nell'output engine è popolato;
- testi UI in francese (verificare che `methodology`, `disclaimer`
  siano tradotti — oggi parzialmente, vedi `I18N_TRANSLATION_STATUS.md`);
- contact form propone di allegare documenti **solo come testo** (no
  upload oggi).

**Screenshot pianificati**:

- `QA-02_moroccan_pedestrian_step1_lang_switcher.png`
- `QA-02_moroccan_pedestrian_step2_result_missing_docs.png`

**Severità se fail**:

- traduzioni mancanti su pagine chiave: P1 (i18n);
- `missing_documents` array vuoto quando dovrebbe essere popolato:
  P0 (output engine non veritiero);
- testo "garanzia di risultato" trapelato in FR: P0 deontologico.

---

### QA-03 — Famiglia all'estero, decesso in Italia, più aventi diritto

> Verifica messaggio "case type non disponibile". Decesso/perdita
> parentale è case_type non implementato (vedi
> `PRODUCT_REQUIREMENTS.md` REQ-4 A — `danno da morte`,
> `danno parentale`).

**Persona**: famiglia Diop residente in Senegal. Padre Aliou Diop
deceduto in incidente stradale Roma-Napoli 2026-02-20. 2 figli minori
+ moglie a Dakar.

**Step**:

1. UI in inglese (`/en/`);
2. cerca "wrongful death", "loss of relative" sulla home, sul case-types;
3. constata che il case-type non è in elenco oggi (case_type
   `wrongful_death` non è registrato nel calculator registry);
4. clicca "Request legal review" (`/en/contact/`);
5. compila contact form con descrizione caso.

**Risultato atteso**:

- pagina `/en/case-types/` non promette il case_type "wrongful death"
  (verificare assenza claim falso);
- `/en/wizard/` non mostra un wizard per "wrongful death";
- contact form accetta la richiesta, salva Lead con
  `case_type=""` o `case_type=other`;
- email allo Studio arriva con il messaggio.

**Screenshot pianificati**:

- `QA-03_family_abroad_step1_case_types_en.png`
- `QA-03_family_abroad_step2_contact_form.png`

**Severità se fail**:

- la pagina case-types promette in modo implicito che il calculator
  esiste: P0 deontologico (ingannevole).

---

### QA-04 — Offerta assicurativa già ricevuta

> L'utente ha già un'offerta dall'assicurazione e vuole capire se è
> congrua. Caso comune nello Studio.

**Persona**: Giulia Bianchi, 28 anni, Milano. Sinistro 2025-12-10
(in autostrada). Offerta assicurazione: 14 500 EUR. Dichiara
invalidità permanente 12% in perizia medica.

**Step**:

1. wizard IT, compila come QA-01 ma con percentuale 12% e ITT 30 giorni;
2. result page;
3. confronta range con offerta assicurazione (14 500 EUR).

**Risultato atteso**:

- range mid presumibilmente sopra 14 500 EUR (dipende da TUN: indicativo);
- nessun claim "l'assicurazione ti ha sottostimato" automatico
  (deontologicamente off);
- "Cosa significa" paragrafo deve essere chiaro: il range è
  un'**ancora di trattativa**, non una verità assoluta;
- contact form con pre-fill `?sim=<uuid>` e messaggio scritto
  dall'utente "Ho ricevuto offerta di 14 500 EUR, vorrei sapere se
  procedere".

**Screenshot pianificati**:

- `QA-04_insurance_offer_step1_result.png`
- `QA-04_insurance_offer_step2_contact_with_message.png`

**Severità se fail**:

- claim aggressivo "your offer is too low" comparso: P0 deontologico;
- range non coerente o non spiegato: P1.

---

### QA-05 — Infortunio sul lavoro con INAIL già liquidato

> Verifica messaggio "case type non disponibile" con caso comune
> di lavoratore italiano.

**Persona**: Carlo Verdi, 50 anni, Brescia. Infortunio 2025-08-05
in cantiere. INAIL ha liquidato 18 000 EUR per IP 25%. Vuole capire
il **danno differenziale** verso il datore di lavoro.

**Step**:

1. cerca "infortunio sul lavoro" nel sito;
2. case-types page non lo elenca come implementato;
3. legge methodology;
4. va a contact, descrive il caso.

**Risultato atteso**:

- nessun calculator pubblicato per workplace_injury;
- contact form salva Lead con descrizione "INAIL già liquidato
  18 000 EUR, IP 25%, vuole valutare danno differenziale";
- email allo Studio.

**Screenshot pianificati**:

- `QA-05_inail_step1_no_workplace_calculator.png`
- `QA-05_inail_step2_contact_form_with_inail_details.png`

**Severità se fail**:

- promessa implicita di calcolatore workplace: P0.

---

### QA-06 — Responsabilità medica con diagnosi tardiva

> Caso comune. Verifica messaggio coerente.

**Persona**: Sara Russo, 40 anni, Bari. Cancro mammario diagnosticato
solo 2025-09 dopo che mammografia 2024-03 era stata refertata
"normale". Stadio II al momento della diagnosi tardiva. Cerca
risarcimento.

**Step**:

1. cerca "responsabilità medica" sul sito;
2. nessun calculator dedicato (`medical_malpractice` non implementato);
3. contact form con descrizione caso e domanda "che documenti
   servono?".

**Risultato atteso**:

- contact form invita a non condividere referti medici **nel
  messaggio** (vedi `contact.html:98`: *"Avoid sharing sensitive
  medical details now — we will request them only if needed"*);
- Lead salvato, email allo Studio, descrizione caso senza dati
  sanitari nel body inviato (privacy minimization);
- consenso art. 9 GDPR **non** richiesto qui (l'utente non ha
  inserito dati medici, solo descrizione narrativa).

**Screenshot pianificati**:

- `QA-06_late_diagnosis_step1_contact_with_warning.png`

**Severità se fail**:

- form accetta dati medici senza warning aria: P0 GDPR;
- email body conteine il messaggio in chiaro (oggi NON lo include —
  verificato in `email_notifications.py`): P0 privacy se diverso.

---

### QA-07 — Utente francese/belga con caso internazionale

> Stato scaffold per FR/BE. Verifica che il flusso "preliminary
> review" sia chiaro e che NON appaia un calcolatore.

**Persona**: Pierre Dubois, 55 anni, Lille (FR). Sinistro
auto in Belgio (Liège) il 2026-01-15. Assicurazione belga (Ethias).
ITT 45 giorni, IP 18%.

**Step**:

1. UI in francese (`/fr/`);
2. countries → France;
3. legge stato "Sources légales en cours de revue";
4. clicca CTA "Submit a France case to the Studio";
5. compila wizard FR road accident;
6. submit;
7. result page mostra "preliminary legal assessment" — niente cifre.

**Risultato atteso**:

- in tutto il flusso **NESSUN importo numerico in EUR**;
- testo "no automatic estimate" presente;
- result page card "International / preliminary legal assessment" sand-tone;
- CTA "Request direct legal review";
- Simulation salvata con `status=unavailable_requires_legal_validation`;
- nessuna `LegalReview` per FR (verificare in admin che il "Calculation basis" *non* citi una formula approved che non esiste).

**Screenshot pianificati**:

- `QA-07_french_belgian_step1_country_france_fr.png`
- `QA-07_french_belgian_step2_wizard_fr_banner.png`
- `QA-07_french_belgian_step3_result_unavailable_fr.png`

**Severità se fail**:

- importo numerico EUR appare: **P0 critico** (regola "non inventare");
- claim "calcolo disponibile" trapela in FR: P0;
- traduzione FR rotta: P1.

---

### QA-08 — Utente arabo RTL — successione internazionale Marocco

> Verifica RTL + traduzione AR. Caso esistenziale per il prodotto
> (target arabofono in Italia/Francia/Belgio).

**Persona**: محمد العلوي (Mohamed Alaoui), 60 anni, Casablanca, MA.
Padre deceduto a Bruxelles, beni in Marocco e in Francia. Vuole
capire diritto applicabile alla successione.

**Step**:

1. UI in arabo (`/ar/`);
2. countries → Morocco;
3. legge breve descrizione + status;
4. clicca CTA wizard inheritance;
5. compila wizard MA inheritance (qualitativo);
6. submit;
7. result page.

**Risultato atteso**:

- `<html dir="rtl" lang="ar">` (verificato in `templates/base.html:2`);
- layout mirrored (status card a sinistra, breadcrumb da destra);
- font Tajawal/Amiri (AR fallback stack);
- nessun importo numerico;
- testi tradotti in AR (anche se molti `.po` non compilati oggi:
  almeno hreflang + dir corretti);
- Simulation salvata `status=unavailable_requires_legal_validation`.

**Screenshot pianificati**:

- `QA-08_arab_user_rtl_step1_home_ar.png`
- `QA-08_arab_user_rtl_step2_country_morocco_ar.png`
- `QA-08_arab_user_rtl_step3_wizard_ma_ar.png`
- `QA-08_arab_user_rtl_step4_result_ar.png`

**Severità se fail**:

- layout LTR-style su `/ar/`: P0;
- importo EUR appare: P0 (come QA-07);
- testo IT/FR trapela in pagine AR critiche: P1.

---

### QA-09 — Form spam (bot)

> Verifica honeypot + rate limit + drop silenzioso.

**Persona**: bot ipotetico (curl + headless Chrome).

**Step**:

1. apri DevTools / curl con compilazione automatica del campo
   `website` (honeypot, hidden CSS):

```bash
curl -X POST 'http://127.0.0.1:8000/it/contact/' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  --data 'first_name=Bot&last_name=Test&email=bot@example.com&phone_number=&preferred_language=it&country=&case_type=&message=I+am+interested+in+legal+services+please+visit+my+site&privacy_accepted=on&website=http://spam.example.com&csrfmiddlewaretoken=...'
```

2. ripeti 25 volte in 60 secondi (oltre il rate limit `PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS=20/3600s`);
3. verifica DB e log.

**Risultato atteso**:

- prima chiamata: 302 → `/it/contact/thank-you/` ma **nessun Lead in
  DB** (honeypot droppato silenziosamente, `apps/crm/views.py:84-88`);
- log: `crm.lead.dropped reason=honeypot path=/it/contact/`;
- chiamata 21+: 429 (o redirect a rate-limit page) → `/it/wizard/rate-limited/`
  (verificare se esiste o redirect default Django) — **DA VERIFICARE**
  che pagina viene servita;
- dopo 25 tentativi, `Lead.objects.count()` ancora a 0.

**Screenshot pianificati**:

- `QA-09_form_spam_step1_curl_log.png` (terminal con curl)
- `QA-09_form_spam_step2_rate_limit_response.png`

**Severità se fail**:

- Lead bot creato in DB: P0 (honeypot rotto);
- rate limit non scatta: P1.

---

### QA-10 — Upload documento troppo grande

> Riservato area cliente futura (P3, fuori scope MVP — `apps.cases`
> non ha campo upload). Skipped per ora; riservato slot.

**Stato**: non testabile oggi. Quando sarà implementata l'area
cliente, lo scope è:

- limite file 10 MB di default;
- mime type whitelist (PDF, JPG, PNG, DOCX);
- AV scanning (ClamAV o servizio esterno);
- privacy review post-upload prima dello storage permanente.

---

### QA-11 — Input calcolatore invalidi

> Verifica che il wizard rifiuti input incoerenti con messaggi chiari
> (vedi `ITALY_INPUT_VALIDATION_WARNINGS_PASS1.md`).

**Persona**: utente che inserisce dati impossibili.

**Step**:

1. wizard IT, prova:
   - età = -5;
   - invalidità = 150%;
   - invalidità = "abc";
   - ITT giorni = 99 999;
   - concorso di colpa = 110%;
   - tutti i campi vuoti.

**Risultato atteso**:

- form lato server rifiuta con messaggi tradotti chiaramente, non
  log Django;
- il template wizard mostra errori per campo;
- nessuna Simulation creata se il form non è valido;
- log puliti senza traceback (errori validati, non crash).

**Screenshot pianificati**:

- `QA-11_invalid_inputs_step1_negative_age.png`
- `QA-11_invalid_inputs_step2_disability_150.png`
- `QA-11_invalid_inputs_step3_all_empty.png`

**Severità se fail**:

- errore 500: P0;
- messaggi non tradotti / tecnici (es. "invalid literal for int()"): P1;
- form passa con dati impossibili e produce simulation: P0
  (range falso).

---

### QA-12 — Mobile Safari iPhone (390 px)

> Verifica responsive sul layout reale Safari mobile, non Chrome
> emulato.

**Persona**: utente iPhone 13.

**Step**:

1. apri sito su iPhone reale (o Safari macOS modalità responsive);
2. visita home → wizard IT → result;
3. valuta:
   - cookie banner non si sovrappone a CTA risultato (oggi P2 noto
     di sovrapposizione lieve);
   - input numerici non sono troppo piccoli;
   - tabella range non scrolla orizzontalmente;
   - bottoni hanno area touch ≥ 44 × 44 pt.

**Risultato atteso**:

- layout single-column;
- font readable senza zoom;
- result min/mid/max stack verticale;
- PDF download funziona (apre Safari reader o app PDF).

**Screenshot pianificati**:

- `QA-12_mobile_safari_390_step1_home.png`
- `QA-12_mobile_safari_390_step2_wizard.png`
- `QA-12_mobile_safari_390_step3_result.png`

**Severità se fail**:

- layout rotto (overflow X): P1;
- bottoni < 44 pt: P2 a11y;
- cookie banner copre CTA: P2 (già noto, non bloccante).

---

### QA-13 — Connessione lenta (3G slow)

> Verifica perceived performance e progressive enhancement.

**Step**:

1. Chrome DevTools → Network → throttling "Slow 3G";
2. apri home → wizard IT → result;
3. cronometra LCP, FID;
4. verifica che hero image non blocchi il rendering;
5. verifica che il contenuto principale appaia entro 5 secondi
   (target su 3G slow).

**Risultato atteso**:

- LCP < 5 s (su 3G slow è accettabile più alto del benchmark 4G);
- contenuto critico visibile prima dei Pexels image;
- nessun layout shift importante (CLS < 0.2);
- font fallback applicato finché Google Fonts non carica;
- form submission non timeout (POST tollera latenza).

**Screenshot pianificati**:

- `QA-13_slow_3g_step1_lcp_timeline.png`
  (DevTools Performance tab)
- `QA-13_slow_3g_step2_layout_shift.png`

**Severità se fail**:

- LCP > 8 s: P1 perf;
- pagina non leggibile finché Google Fonts loaded: P1 (e P1-LEG-1 in
  `LEGAL_COMPLIANCE_CONTENT_AUDIT.md`).

---

### QA-14 — JavaScript disabilitato

> Verifica che il funnel critico funzioni senza JS.

**Step**:

1. Chrome → Settings → "Block JavaScript" su `127.0.0.1:8000`;
2. apri home;
3. visita country landing;
4. apri wizard IT;
5. compila e submit form;
6. verifica result page;
7. apri contact form;
8. submit.

**Risultato atteso**:

- home/country landing/methodology/disclaimer/privacy/contact
  funzionano (sono semi-statiche);
- wizard IT submit POST funziona (Django form lato server);
- result page si renderizza;
- cookie banner: senza JS resta nascosto (`hidden` di default in
  `cookie_consent_banner.html:15` — verificato), e nessun JS lo
  rivela;
- contact form submit senza JS: HTML form standard, deve funzionare.

**Risultato non atteso (degradazione accettabile)**:

- HTMX swap interactions non funzionano → tutto fallback a full
  page reload (è il design di HTMX);
- Pexels lazy-loading immagini non lazy → caricano subito (ok).

**Screenshot pianificati**:

- `QA-14_no_js_step1_home_no_banner.png`
- `QA-14_no_js_step2_wizard_form_works.png`

**Severità se fail**:

- form submit non funziona senza JS: **P0 a11y + UX**;
- pagina vuota o stuck su loading: P0.

---

### QA-15 — Errore CRM/n8n (webhook failure)

> Riservato P1 — webhook esterno non implementato oggi
> (vedi `docs/CRM_INTEGRATION_PLAN.md`). Quando attivato:

**Step (futuro)**:

1. configura `CRM_WEBHOOK_ENABLED=True`, `CRM_WEBHOOK_URL=http://127.0.0.1:9999/`
   (endpoint inesistente);
2. compila e submit `/contact/`;
3. verifica che:
   - Lead viene comunque creato in DB;
   - email allo Studio inviata regolarmente;
   - thank-you page raggiunta;
   - `LeadWebhookDelivery` registrato con status `pending`;
   - Celery task fa retry secondo backoff;
   - dopo 5 attempt: `LeadWebhookDelivery.status=exhausted`;
   - `StaffSecurityAlert` (o equivalente) creato;
   - **niente errori 500 lato utente** (failure isolata al backend).

**Severità se fail (futuro)**:

- failure webhook causa errore 500 utente: P0 (utente non deve sapere);
- Lead non creato in DB perché webhook fallito: P0 (must persist
  comunque);
- nessun alert dopo exhausted: P1.

---

## 3. Catalogo persona fittizie (privacy-safe)

Da usare **solo** per i test sopra. Mai usare dati reali.

| ID | Nome fittizio | Email | Telefono | Note |
|---|---|---|---|---|
| qa01 | Mario Rossi | qa01@example.com | +39 333 1111111 | Italiano, IT |
| qa02 | Yassine El Amrani | qa02@example.com | +39 333 2222222 | Marocchino in IT |
| qa03 | Aliou Diop (deceased) / Famiglia Diop | qa03@example.com | +221 33 8000000 | Senegal |
| qa04 | Giulia Bianchi | qa04@example.com | +39 333 4444444 | Italiana, post-offerta |
| qa05 | Carlo Verdi | qa05@example.com | +39 333 5555555 | Lavoratore IT |
| qa06 | Sara Russo | qa06@example.com | +39 333 6666666 | Paziente IT |
| qa07 | Pierre Dubois | qa07@example.com | +33 6 77 77 77 77 | Francese in BE |
| qa08 | Mohamed Alaoui (محمد العلوي) | qa08@example.com | +212 6 88 88 88 88 | Marocchino |
| qa09 | Bot Test (honeypot) | bot@example.com | — | curl spam |

---

## 4. Tabella riassuntiva — esecuzione QA

| QA | Operatore | Strumento | Output |
|---|---|---|---|
| QA-01 | dev | Playwright MCP / Chrome | screenshot + log canarino |
| QA-02 | dev + Studio i18n | Playwright + revisione FR | screenshot + verifica testi FR |
| QA-03 | Studio | manuale | screenshot + Lead in admin |
| QA-04 | Studio | manuale | screenshot + revisione tono response |
| QA-05 | Studio | manuale | screenshot + Lead in admin |
| QA-06 | Studio | manuale | screenshot + verifica privacy banner |
| QA-07 | dev + Studio FR | Playwright | screenshot + verifica no importi |
| QA-08 | dev + revisore AR | Playwright | screenshot + verifica RTL |
| QA-09 | dev | curl + Playwright | log + DB count |
| QA-10 | — | — | rinviato (no upload oggi) |
| QA-11 | dev | Playwright | screenshot + log Django |
| QA-12 | Studio | iPhone reale | screenshot Safari |
| QA-13 | dev | Chrome DevTools throttling | timeline + screenshot |
| QA-14 | dev | Chrome JS off | screenshot |
| QA-15 | — | — | rinviato (no webhook oggi) |

---

## 5. Quando ripetere il QA

1. **Prima di ogni go-live di un paese** non-IT: tutti i 15 (3, 5, 6,
   10, 15 possono essere skipped finché out-of-scope MVP).
2. **Dopo modifiche al calculator IT**: minimo QA-01 + QA-04 + QA-11.
3. **Dopo modifiche al form `/contact/`**: QA-01, QA-02, QA-09, QA-14.
4. **Dopo modifiche ai template `_base.html` / cookie banner**:
   QA-12, QA-13, QA-14.
5. **Prima di ogni release i18n** (compilazione `.po`): QA-02, QA-07,
   QA-08.

---

## 6. Tracking risultati QA

Ogni esecuzione QA produce:

1. screenshot in `docs/screenshots/delta_audit_2026-05-10/before/`
   (struttura definita nel `README.md` della cartella);
2. note testuali in `docs/screenshots/delta_audit_2026-05-10/notes/QA-NN.md`
   (1 file per caso, anche se solo 2-3 righe);
3. eventuale bug aperto come iter `F-bug-fix-QA-NN-<slug>` con:
   - severità (P0/P1/P2/P3);
   - titolo e descrizione;
   - fix proposto;
   - test di regressione da aggiungere.

I risultati QA aggregati alimentano la sezione 4 di
`docs/AUDIT_DELTA_2026-05-10.md` (bug list).

---

## 7. Per Claude Code che riprende il QA

- **Non saltare** mai QA-01 (canarino IT).
- Quando aggiungi un nuovo case_type al calculator registry, aggiungi
  il caso QA corrispondente in questo file.
- Quando aggiungi un nuovo paese, aggiungi 1 caso QA per il flusso
  scaffold + 1 caso QA per il flusso calculated (se attivo).
- Le persona fittizie sopra sono il **catalogo unico**: non
  inventarne altre.
- Mai committare screenshot con dati reali. Se PII compaiono per
  errore, screenshot va eliminato e rifatto con persona fittizia.
