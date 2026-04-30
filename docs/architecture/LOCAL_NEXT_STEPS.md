# LOCAL — Roadmap concreta locale-first

**Iter**: F-global-mvp-status-consolidation · iter1
**Data**: 2026-04-30
**Stato**: roadmap di lavoro — **nessuna fase è iniziata
oltre quanto già consolidato in `GLOBAL_MVP_STATUS.md`**.

> Roadmap operativa per l'MVP Studio Legale Badrane LegalTech.
> Principio: tutto va validato in locale (sviluppo/staging
> locale) **prima** del deploy. Il deploy in produzione è la
> fase finale, non un punto intermedio. Si privilegia la
> correttezza legale rispetto alla velocità di rilascio.

---

## 0. Principio cardine

> **Niente production deploy finché un caso d'uso end-to-end
> non-Italia non è funzionante in staging con fonti legali
> approvate dallo Studio.**

L'Italia è già parzialmente operativa (calculator road accident
+ TUN 2025 approved + 2 LegalReview firmate), ma il valore
del progetto sta nella **piattaforma multi-paese**: deploy con
solo IT funzionante non è un MVP credibile.

---

## 1. Fase A — Studio review legale (in parallelo per paese)

**Durata stimata:** dipende dal carico Studio. Bloccante per
tutto il resto.

**Cosa succede:**
- Lo Studio compila i 4 checklist consegnati (FR + BE + MA + TN)
  riga per riga, registrando per ogni voce: `status`
  (`pending → checked_ok / needs_correction / rejected /
  approved_for_import|mapping`), `reviewer`, `notes`,
  `reviewed_at`.
- Per FR/BE (forchette numeriche): spot-check per blocco
  (12+16+4 righe FR, 9+7+13+19 righe BE). Decisioni
  tassonomiche: B2 BE (prejudice esthétique vs indemnité
  forfaitaire), B4 BE (formula camions ≥3.5 t).
- Per MA/TN (mapping articoli): conferma articoli per ogni
  macro-tema (Moudawana 12 + Code droits réels 3; CSP Livre IX
  12 + Loi 98-97 6). Decisione su renvoi e ordine pubblico
  per casi cross-border. Per TN: posizione esplicita su
  doppia regola di conflitto Loi 98-97 vs Reg. 650/2012.

**Cosa è in carico Claude:**
- nessuna implementazione finché non c'è almeno un blocco GO
  firmato per un paese.
- al massimo: produrre nuovi review package se emerge una
  fonte non coperta (es. tabelle Schryvers BE non ancora
  scaricate) o re-spike OCR BE 2024 dopo installazione
  language pack.

**Cosa è in carico Studio:**
- Recupero manuale fonti `manual_required` (4 fonti):
  Loi Badinter, Reg. UE 650/2012 ×2, JORT 1956, CSP compiled.
- Compilazione checklist riga per riga.
- Decisioni tassonomiche e DIP.

**Output di fase A:**
- 4 checklist completati con almeno una porzione GO per ciascun
  paese.
- LegalSource cross-promosse a `approved` solo dopo creazione
  delle relative `LegalReview` firmate (criterio C-2 dei
  package). **Bloccante**: nessuna promozione DB senza Review
  firmata.

**No-go fase A:**
- Nessun import DB.
- Nessuna creazione di `CompensationDataset` o
  `CalculationFormula`.
- Nessuna modifica calculator/wizard/templates.
- Nessuna feature flag attivata.

---

## 2. Fase B — Import FR/BE post-review

**Trigger:** GO Studio su almeno un blocco FR e/o BE.

**Cosa succede (FR):**

1. `F-france-import-datasets-readonly-seed`: management command
   idempotente che:
   - crea le `LegalReview` firmate registrate nei checklist;
   - promuove le LegalSource a `approved`;
   - importa le righe CSV approvate in `CompensationDataset`
     (con `source_note` aggiornata: `legal_review_required=false;
     no_human_legal_approval=false; reviewer=…; reviewed_at=…`);
   - aggiunge `CalculationFormula` con `parameters.engine` solo
     dopo conferma del mapping `amount_rule`.
   - Esegue dry-run + verifica conteggi vs spot-check.
2. `F-france-calculator-skeleton`: sostituisce
   `_FrancePlaceholderCalculator._compute_with_sources` con
   logica reale che:
   - legge `CompensationDataset` approved;
   - applica la formula approved tramite il service esistente
     `apps.compensation.services` (riusato da Italia);
   - produce `CalculationResult` con sources, breakdown,
     warnings, missing_documents, confidence, legal_disclaimer
     (contract standard).
   - **Nessun valore hard-coded**.
3. Test pytest dedicati al calculator FR (regression + edge
   cases). Aggiornamento del registry test `test_registry_*`.

**Cosa succede (BE):**

Stesso pattern di FR, ma con vincolo addizionale:
- Le righe BE 2020 sono **historical_fallback**: il dataset
  importato deve avere `is_historical=true` (o equivalente nei
  metadata) e il `source_note` deve riportare
  `source_is_historical_2020=true`. Il calculator BE deve
  emettere un `warning` esplicito *"valore basato su Tableau
  Indicatif 2020 — édition storica; la versione 2024 non è
  ancora validata"*.
- Il caso B4 (formula camions) è una `CalculationFormula`
  parametrica `daily_amount = 50 + 10 * tonnes`, oppure è
  fuori scope MVP. Decisione documentata nel checklist BE.

**Output di fase B:**
- Calculator FR e BE diventano **REAL** (override
  `_compute_with_sources`).
- Wizard `/wizard/fr/road-accident/` e `/wizard/be/road-accident/`
  producono risultati reali (non più
  `unavailable_requires_legal_validation`).
- Test E2E in locale verdi.

**No-go fase B:**
- Nessun feature flag in produzione.
- Nessun report PDF utente con valori reali pubblicato esternamente
  finché staging non è verde.
- Nessun by-pass del flusso `LegalReview`.

---

## 3. Fase C — Mapping MA/TN e trascrizione quote

**Trigger:** GO Studio su mapping (Iter 2 dei package MA/TN).

**Cosa succede (MA):**

1. `F-eu-650-2012-manual-download-attach` (Studio): recupero
   PDF EUR-Lex e attach via Django admin (LegalSourceAttachment).
2. `F-morocco-moudawana-quotes-extraction-manual`: trascrizione
   strutturata delle quote faraïd in CSV candidate read-only.
   Schema simile al template Mornet (FR) ma adattato:
   - `inheritance_case_code` (es. `coniuge_con_figli_1_figlio`,
     `coniuge_senza_figli_padre_vivente`, ...)
   - `heir_relation_code`, `heir_count`, `share_numerator`,
     `share_denominator`, `share_decimal`, `notes`,
     `transcription_status`, `source_quote_short`, `source_note`.
   - Trascrizione manuale per ogni combinazione, mai LLM.
   - Header esplicito: `legal_review_required=true;
     no_human_legal_approval=true`.
3. QA read-only `qa_morocco_moudawana_quotes.py`: verifica
   coerenza (somma quote = 1 entro tolleranza, no quote
   negative, ecc.).
4. `F-morocco-import-datasets-readonly-seed`: come fase B
   per FR/BE, ma con dataset MA.
5. `F-morocco-inheritance-calculator-engine`: sostituisce
   `_MoroccoPlaceholderCalculator._compute_with_sources` con
   un engine che:
   - prima qualifica il caso (DIP / Reg. 650/2012 / professio
     juris);
   - poi applica le quote farḍ partendo dal dataset approved.
   - Output conforme al contract standard.

**Cosa succede (TN):**

Stesso pattern MA, con specificità:
- Doppia regola di conflitto Loi 98-97 (foro TN) vs Reg.
  650/2012 (foro UE): l'engine deve gestire entrambi i casi
  con una decisione documentata nel codice e una warning
  esplicita all'utente.
- Particolarità tunisine: enfants nés hors mariage (Loi 98-75),
  giurisprudenza attenuativa sulle esclusioni, trattamento
  radd al coniuge (diverso dal MA).

**Output di fase C:**
- Wizard `/wizard/ma/inheritance/` e `/wizard/tn/inheritance/`
  producono risultati reali.
- Test E2E in locale verdi.

**No-go fase C:**
- Nessuna trascrizione quote LLM-generated.
- Nessuna pubblicazione di quote senza review riga per riga.
- Nessuno skip della qualifica DIP (legge applicabile selezionata
  prima delle quote).

---

## 4. Fase D — Hardening prodotto

**Trigger:** Fasi A + B + C completate per almeno 1 caso d'uso
non-IT (preferibilmente FR road accident, perché il dataset
Gazette + Mornet è più maturo).

**Cosa succede:**

### 4.1 Infrastruttura
- Migrazione da SQLite a **PostgreSQL** (CLAUDE.md richiede
  PostgreSQL in produzione).
- Setup **Redis + Celery** per task async (generazione PDF
  pesanti, invio email lead).
- **Dockerfile + docker-compose** per produzione/staging.
- Variabili `.env` versionate via `.env.example` (no secrets
  in repo).

### 4.2 Reportistica
- Generazione PDF lato server con disclaimer obbligatorio
  CLAUDE.md, branding Studio, link al sito madre.
- Multi-lingua per il PDF (IT, FR, EN, NL all'occorrenza).

### 4.3 GDPR / Compliance
- Consenso esplicito al trattamento dati sensibili (salute,
  reddito, famiglia).
- Data minimization sui form wizard.
- Retention policy: cancellazione dopo N giorni se non
  trasformato in lead.
- Audit log degli accessi staff.
- Esclusione `.env`, segreti dai log.

### 4.4 SEO / multilingua
- Landing per paese/case_type con testi tradotti.
- Sitemap + robots.txt.
- Meta tag, schema.org structured data.
- Coordinamento URL con sito madre
  (`international.studiolegalebadrane.it`).

### 4.5 Test
- pytest unitari + integrazione su engine, services, views.
- Playwright E2E sui wizard principali.
- Test di regressione su Italia (baseline 328 test, da
  aggiornare con i nuovi paesi).

### 4.6 Lint / formatting
- `ruff check .` clean.
- `black --check .` clean.
- Pre-commit hooks.

**Output di fase D:**
- Build container deployable.
- Staging environment sul cloud Studio.
- Test E2E verdi su staging con dati validati.
- Accessibility audit base (WCAG 2.1 AA min).

**No-go fase D:**
- Nessun deploy in produzione finché la suite test E2E non è
  verde su staging.
- Nessun key/secret in repo.
- Nessun dato utente reale in staging (usare seed dataset
  legali approved + dati sintetici per simulazioni).

---

## 5. Fase E — Deploy finale (paese per paese)

**Trigger:** Fase D verde su staging.

**Cosa succede:**

### 5.1 Production rollout per paese
Ordine consigliato:
1. **IT** (già operativo localmente — minimo rischio).
2. **FR** (dataset più maturo dopo review).
3. **BE** (con banner "historical_fallback" attivo).
4. **MA** + **TN** in coda (richiedono mapping più profondo).

### 5.2 Feature flag per paese
- `enable_italy_calculator=true` solo dopo prima settimana
  staging verde.
- Feature flag separati per ciascun country/case_type.
- Possibilità di disabilitare un calcolatore senza redeploy.

### 5.3 Monitoring
- Logs strutturati (JSON) verso un aggregatore.
- Metriche: simulazioni/giorno, conversione a lead, errori
  calculator.
- Alert su:
  - calculator che ritorna `error_legal_data_missing` (fonte
    rimossa per errore);
  - hash PDF non corrispondente a quanto registrato in DB
    (fonte modificata);
  - leak di dati sensibili nei log.

### 5.4 Audit log
- Ogni accesso staff a un caso utente è loggato (audit trail
  GDPR).
- Ogni modifica `LegalSource.status` è auditata
  (`previous_status → new_status`, reviewer, timestamp).

### 5.5 Disaster recovery
- Backup giornaliero PostgreSQL.
- Restore tested almeno una volta in pre-production.

**Output di fase E:**
- `simulatore.studiolegalebadrane.it` o
  `indennizzo.studiolegalebadrane.it` live.
- Disclaimer obbligatorio CLAUDE.md visibile su ogni report.
- Lead inviati allo Studio.

**No-go fase E:**
- Production senza monitoring attivo.
- Production senza piano DR.
- Production senza GDPR compliance verificata.
- Sostituzione retroattiva di datasets approved senza
  `LegalSource.status = replaced` + new approved version.

---

## 6. Cosa NON è in roadmap (espliciti out-of-scope MVP)

- ❌ Calcolatori pluri-giurisdizione automatici (es.
  successioni con asset in IT + MA + FR contemporaneamente).
  Resta un caso "richiede consulenza" (lead) finché lo Studio
  non valida la combinazione.
- ❌ Integrazione real-time con sistemi assicurativi /
  databases pubblici.
- ❌ Pagamenti / fatturazione (lo Studio gestisce offline).
- ❌ Mobile app nativa.
- ❌ Calcolatori per casi che richiedono perizia medica
  obbligatoria (devono restare scaffold con `missing_documents`).

---

## 7. Stima dipendenze critiche

| Dipendenza | Tipo | Bloccante per | Owner |
|---|---|---|---|
| Studio review FR checklist | Manuale | Fase B FR | Studio |
| Studio review BE checklist | Manuale | Fase B BE | Studio |
| Studio mapping MA Moudawana | Manuale | Fase C MA | Studio |
| Studio mapping TN CSP + DIP | Manuale | Fase C TN | Studio |
| Tesseract `fra`/`nld` lang pack | Setup macchina | BE 2024 OCR re-spike | Studio (DevOps) |
| EUR-Lex Reg. 650/2012 download manuale | Manuale | Fase C MA + TN | Studio |
| JORT 1956 / CSP compiled download manuale | Manuale | Fase C TN | Studio |
| PostgreSQL setup | Infra | Fase D | DevOps |
| Redis/Celery setup | Infra | Fase D | DevOps |
| Production cloud (host + dominio) | Infra | Fase E | Studio + DevOps |

---

## 8. Pattern operativi da rispettare

Riassumo i pattern già consolidati in iter precedenti, da
mantenere costanti per ogni futura attività:

1. **Read-only first**: ogni nuovo iter inizia con script
   read-only (estrazione, OCR, audit) prima di toccare il DB.
2. **Candidate read-only on-disk**: i CSV estratti restano
   gitignored finché lo Studio non li approva. Il flusso
   "candidate → review → approved" è obbligatorio.
3. **`source_note` strutturato**: ogni riga di dataset legale
   ha `legal_review_required=…; no_human_legal_approval=…;
   reviewer=…; reviewed_at=…` o equivalenti. Niente importi
   "puliti" senza tracciabilità.
4. **Hash SHA-256**: ogni PDF/HTML scaricato ha un hash che
   deve coincidere col manifest in apertura degli script.
5. **No LLM-generated values**: tutti i valori legali vengono
   da estrazione automatica deterministica (`pdfplumber`,
   parser HTML) o trascrizione manuale. Mai da modello
   linguistico.
6. **Test verde prima di tutto**: pytest, ruff, black sempre
   verdi al merge. La baseline di 328 test passed deve crescere
   ad ogni nuovo paese, non rompersi.
7. **No regressioni Italia**: ogni iter chiude con
   "Italia invariata: pytest 328+ passed".

---

## 9. Disclaimer

La presente roadmap è una proposta di lavoro: ogni passo va
validato dallo Studio prima di essere intrapreso. Le date e i
nomi degli iter sono indicativi. Il principio non negoziabile
è: nessun calcolo pubblico senza fonte legale approvata e
review umana firmata. Il disclaimer obbligatorio definito in
CLAUDE.md resta valido per ogni simulazione e per ogni report.
