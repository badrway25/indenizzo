# BE — Package di review legale (read-only)

**Iter**: F-belgium-legal-review-package · iter1
**Data**: 2026-04-30
**Stato**: read-only — **nessun import DB, nessuna approvazione,
nessuna creazione di `LegalReview`, `CompensationDataset` o
`CalculationFormula`**.

> Documento operativo che consolida quanto già estratto per il
> Belgio (Tableau Indicatif 2020) e quanto rilevato dallo spike OCR
> sul Tableau Indicatif 2024, in un pacchetto consegnabile allo
> Studio per la review legale. Non sostituisce i report di
> estrazione e di OCR spike: fornisce solo la mappa, la checklist,
> i criteri GO/NO-GO e la sequenza futura proposta. Tutti i CSV
> referenziati sono **candidate read-only** (gitignored). Nessun
> valore numerico è stato approvato.

---

## 0. Avvertenze

- Il presente package **non** approva, **non** importa, **non**
  crea righe DB. Non genera `LegalReview`, `CompensationDataset`,
  `CalculationFormula`. Non modifica calculator, wizard, Italia,
  Tunisia, Marocco, Francia.
- I CSV elencati esistono solo on-disk sotto
  `legal_data/sources/belgium/` e sono **gitignored**
  (`legal_data/sources/**/*.csv`).
- I valori contenuti nei CSV sono il risultato di estrazione
  automatica via `pdfplumber` dal PDF BE 2020 (PDF testuale, non
  scansionato). **Nessuno è legalmente verificato**.
- Il Tableau Indicatif 2024 è image-scanned: lo spike OCR
  documentato in `BELGIUM_TI_2024_OCR_SPIKE_REPORT.md` mostra
  che l'estrazione automatica non è oggi affidabile. **BE 2024 NON
  è pronto per il review e non deve essere importato.**
- La regola fondamentale del progetto (CLAUDE.md) resta valida:
  nessun importo pubblico finché un revisore legale dello Studio
  non approva la fonte. Ogni dato di questo package è oggi
  `needs_review`.
- Disclaimer obbligatorio (CLAUDE.md): "La simulazione è
  indicativa e non costituisce parere legale, medico-legale o
  garanzia di risultato. La valutazione effettiva dipende da
  documenti, perizie, responsabilità, legge applicabile,
  giurisdizione competente, orientamenti giudiziari e prassi
  assicurative."

---

## 1. Inventario CSV candidate (BE 2020)

Ogni file è gitignored. Path relativo al repo root.

| # | File | Header (colonne) | Righe dati | Fonte (PDF) |
|---|---|---|---:|---|
| B1 | `legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-souffrances-endurees.csv` | `row_type, severity_code, severity_label_fr, victim_age_min, victim_age_max, amount_min, amount_mid, amount_max, currency, source_page, source_note` | 63 | TI 2020, p.17 |
| B2 | `legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-prejudice-esthetique.csv` | `row_type, severity_code, severity_label_fr, victim_age_min, victim_age_max, annual_amount, currency, source_page, source_note` | 71 | TI 2020, p.22–23 |
| B3 | `legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-prejudice-deces-affection.csv` | `row_type, relation_code, relation_label_fr, amount_min, amount_mid, amount_max, currency, source_page, source_note` | 13 | TI 2020, p.26 |
| B4 | `legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-vehicule-remplacement.csv` | `row_type, vehicle_type_code, vehicle_type_label_fr, daily_amount_min, daily_amount_mid, daily_amount_max, currency, source_page, source_note` | 19 | TI 2020, p.32 |

**Totale righe**: 166. Tutte le righe portano il flag
`source_is_historical_2020=true` nella `source_note`: il CSV
si rappresenta esplicitamente come **storico/fallback** in
attesa che BE 2024 sia validato.

### 1.1 Note importanti sul contenuto dei CSV

- **B1 — souffrances endurées**: scala Julin 1/7..7/7 × 9 fasce
  d'età (0–10, 11–20, …, ≥81). 7×9 = 63 righe. La
  `source_note` riporta `row_type =
  be_souffrances_endurees_per_age_severity_amount`. Valore
  unico per cella (`amount_min == amount_mid == amount_max`).
- **B2 — préjudice esthétique**: il filename rispetta lo spec
  utente, ma la tabella di p.22–23 del TI 2020 (sezione 3.7) è
  in realtà l'**indennità forfetaria annua per anno per 1 %
  d'incapacité** (`row_type =
  be_indemnite_forfaitaire_per_age_annual_amount`), non un
  préjudice esthétique in senso stretto. Il préjudice
  esthétique BE 2020 condivide la stessa scala Julin di B1
  (sez. 3.4.1.2.b) — vedi report di estrazione,
  `BELGIUM_TI_2020_EXTRACTION_REPORT.md`. **Lo Studio deve
  decidere** se usare B2 come tabella indemnità forfaitaria o
  rinominarla, e se modellare il préjudice esthétique
  riutilizzando B1.
- **B3 — décès / préjudice d'affection**: 13 relazioni
  parentali. Valore unico per riga.
- **B4 — véhicule de remplacement**: 19 tipi di veicolo +
  forfait giornaliero. Lo skip 1 («camions ≥ 3,5 t, +10 €/t»)
  è un caso *formula_amount_per_ton* non auto-estraibile come
  tariffa giornaliera unica — vedi report di estrazione
  `vehicule_skipped_detail`.

---

## 2. Sorgenti PDF e hash

| Slug | PDF | Size (B) | SHA-256 | Pagine | Manifest |
|---|---|---:|---|---:|:-:|
| `be-tableau-indicatif-2020` | `legal_data/sources/belgium/downloaded/be-tableau-indicatif-2020.pdf` | 1 985 686 | `1b073f5c41c8414018e262143d7e67c496bbeeb832e623f406333b3ece0b8222` | testuale (extraction OK) | OK |
| `be-tableau-indicatif-2024` | `legal_data/sources/belgium/downloaded/be-tableau-indicatif-2024.pdf` | 2 373 682 | `37b0a0b4606ec39638db4a81c6074928c2275a09274a11597b8fb17e03bc3a45` | 23 (image-scanned) | OK |

Hash dichiarati nel `download_manifest.json` di
`legal_data/sources/belgium/downloaded/`. Gli script di
estrazione e QA verificano l'hash in apertura: ogni discrepanza
blocca l'esecuzione.

---

## 3. Stato attuale `LegalSource` nel DB

Verificato in locale al momento della stesura di questo
documento. Tutte le 5 fonti BE sono in `needs_review`.

| Slug | Tipo | Reliability | Stato | Note |
|---|---|---|---|---|
| `be-loi-1989-11-21-rc-auto` | `official_law` | `official` | `needs_review` | Solo testo normativo (HTML), nessuna tabella. Riferimento legale per RC auto belga. |
| `be-tableau-indicatif-2020` | `court_table` | `high` | `needs_review` | PDF testuale 32+ pagine. 4 tabelle indicizzate (B1..B4). Consigliato come **historical_fallback** in attesa di BE 2024. |
| `be-tableau-indicatif-2024` | `court_table` | `high` | `needs_review` | PDF 23 pagine, **image-scanned**. OCR non oggi affidabile (`fra`/`nld` lang pack mancanti). NON pronto. |
| `be-tables-schryvers-2026-page` | `court_table` | `high` | `needs_review` | Solo landing HTML. Tableurs Schryvers (mortalità + capitalizzazione). PDF/Excel non scaricati. Fuori scope di questo package. |
| `be-tables-schryvers-tableurs` | `court_table` | `high` | `needs_review` | Solo HTML aggregato. Stesso vincolo del precedente. |

**Invarianti DB BE:**
- 0 `CompensationDataset` con `country=BE`.
- 0 `CalculationFormula` con `dataset.country=BE`.
- 0 `LegalReview` su fonti BE.

---

## 4. Cosa deve verificare lo Studio per ogni file

### 4.1 B1 — Souffrances endurées (63 righe)

**Cosa è:** importo unico per cella nella griglia
`severity (Julin 1/7..7/7) × victim_age (0–10, 11–20, …,
≥81)`. Scala dolore di Julin / Pijn-Schaal.

**Cosa lo Studio deve verificare:**
1. Il TI 2020 (édition Magistrats / Avocats) è la versione di
   riferimento e non un'edizione precedente.
2. Le 7 categorie Julin sono `1_7=minime, 2_7=très léger,
   3_7=léger, 4_7=modéré, 5_7=important, 6_7=très important,
   7_7=insupportable`. Confermare i label francesi usati nel
   wizard.
3. Le 9 fasce d'età coprono l'intero range (0–10, 11–20,
   21–30, 31–40, 41–50, 51–60, 61–70, 71–80, ≥81).
4. Spot-check: `(severity=1_7, age=0–10)` = 540 € e
   `(severity=2_7, age=0–10)` = 2 150 € corrispondono alla
   stampa di p.17.
5. Convenzione decimale: il punto è il separatore decimale
   (es. `540.00`). Confermare.
6. Lo Studio decide se accettare i valori 2020 come
   **historical_fallback** finché BE 2024 non è approved.

### 4.2 B2 — Indennità forfaitaire / préjudice esthétique (71 righe)

**Cosa è:** importo annuo forfettario per 1 % di incapacité,
in funzione di `victim_age_min..max`. Tabella p.22–23 sez. 3.7
del TI 2020.

**Cosa lo Studio deve verificare:**
1. **Decisione tassonomica** (importante): il filename
   `prejudice-esthetique` non corrisponde semanticamente al
   contenuto (`row_type =
   be_indemnite_forfaitaire_per_age_annual_amount`). Lo Studio
   sceglie:
   - (a) tenere il nome attuale e documentare il `row_type` come
     verità tassonomica;
   - (b) rinominare il file in `be-ti-2020-indemnite-forfaitaire.csv`;
   - (c) splittare in due: indemnité forfaitaire (questo
     contenuto) + préjudice esthétique riutilizzando la tabella
     Julin di B1 (la sez. 3.4.1.2.b dichiara che condividono la
     scala).
2. Le 71 fasce d'età coprono il range completo del PDF
   (es. 0–15, 16–16, 17–17, …, ≥97 — granularità 1 anno).
   Confermare bound superiore.
3. Spot-check: `(age=0–15)` = 1 220 €, `(age=16)` = 1 200 €
   coincidono con p.22.
4. Confermare che `1 % d'incapacité × année` è
   l'unità corretta (formula moltiplicativa: la cifra è per
   ogni 1 % e per ogni anno).

### 4.3 B3 — Décès — préjudice d'affection (13 righe)

**Cosa è:** importo unico per relazione parentale in caso di
décès. Tabella p.26 del TI 2020.

**Cosa lo Studio deve verificare:**
1. Le 13 relazioni coprono lo schema completo BE 2020
   (conjoint/partenaires, parent_cohabitant, parent_non_cohabitant,
   enfant_cohabitant, enfant_non_cohabitant, frère/sœur,
   grand-parent, petit-enfant, etc.).
2. Confronto con BE 2024: lo spike OCR (p.14) ha rilevato che
   BE 2024 espone solo **5 relazioni** vs le 13 di BE 2020
   (taxonomy change). Lo Studio decide se mantenere la
   tassonomia BE 2020 (più granulare) come fallback o
   migrare alla tassonomia BE 2024 quando approvata.
3. Spot-check: `conjoint_perte_conjoint` = 15 000 € (valore
   unico). Confronto col PDF p.26.
4. Convenzione: importo unico (no forchetta). Confermare che
   `amount_min == amount_mid == amount_max` è la
   rappresentazione corretta.

### 4.4 B4 — Véhicule de remplacement (19 righe)

**Cosa è:** forfait giornaliero per tipo di veicolo. Tabella
p.32 del TI 2020.

**Cosa lo Studio deve verificare:**
1. I 19 tipi (bicyclette, 2-3 roues motorisées, quad,
   automobile selon classe fiscale, utilitaire selon poids,
   etc.) coprono lo schema BE 2020. Confronto con la stampa.
2. **Caso skipped — camions ≥ 3,5 t**: la riga «50,00 € +
   10,00 €/tonne» è una formula lineare per tonnaggio non
   modellabile come tariffa giornaliera unica. Lo Studio
   decide se introdurre una `CalculationFormula`
   `daily_amount = 50 + 10 * tonnes` o lasciare la voce
   fuori scope MVP.
3. Spot-check: `bicyclette` = 10 €/giorno, `2_3_roues_motorisees`
   = 15 €/giorno. Confronto col PDF p.32.
4. Convenzione: `daily_amount_min == daily_amount_mid ==
   daily_amount_max` (valore unico). Confermare.

### 4.5 BE 2024 — Tableau Indicatif 2024

**Cosa è:** PDF image-scanned di 23 pagine. NON estraibile
automaticamente con `pdfplumber.find_tables()`. Lo spike OCR
(`BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`) ha mostrato:
- Tesseract installato senza language pack `fra` né `nld` →
  errori di trascrizione su segni `≥`, segni di punteggiatura,
  separatore migliaia (`15.000` vs `15,000`).
- Taxonomy change rispetto a BE 2020 (5 relazioni décès vs 13;
  Julin × age table riposizionata sotto «préjudice esthétique
  permanent» invece di «souffrances endurées»).
- Importi BE 2024 ~+15 % vs BE 2020.

**Cosa lo Studio deve verificare / decidere:**
1. ⚠️ **BE 2024 NON è oggi pronto per import.** Nessun CSV
   candidate è stato prodotto (per regola: niente
   pseudo-estrazione automatica priva di review umana).
2. Lo Studio sceglie tra le opzioni di
   `BELGIUM_TI_2024_OCR_SPIKE_REPORT.md` §9:
   - **A** OCR puro → CSV (rifiutata: equivale a
     inventare valori legali);
   - **B** OCR + heavy manual review (medio termine, dopo
     installazione `fra`/`nld`);
   - **C** Trascrizione manuale completa (lenta, sicura);
   - **D** Mantenere BE 2020 come historical_fallback e
     rinviare BE 2024 (proposta corrente).
3. La decisione D + B (raccomandata dal report OCR spike) è
   coerente con questo package: BE 2020 = fallback approvato,
   BE 2024 = re-spike con language pack + review manuale.

### 4.6 Altre fonti BE non coperte dai CSV

| Slug | Stato | Cosa lo Studio deve verificare |
|---|---|---|
| `be-loi-1989-11-21-rc-auto` | `needs_review` | Lettura testo normativo. Decisione: fonte di citazione legale per RC auto, no tabella. Nel MVP serve come riferimento, non come dato calcolabile. |
| `be-tables-schryvers-2026-page` | `needs_review` | Decisione: scaricare i tableurs Schryvers (Excel) o restare con il barème INSEE/Gazette francese (non c'è equivalente belga ufficiale). Nel MVP è ragionevole rinviare. |
| `be-tables-schryvers-tableurs` | `needs_review` | Stesso vincolo del precedente. Tableurs accessibili dal sito ma richiedono scaricamento manuale dei file Excel. |

---

## 5. Checklist di spot-check suggerita

Per ridurre il carico di review, suggerimenti di campionamento.

| File | Sample size suggerita | Strategia |
|---|---|---|
| B1 | 9 righe | 3 severità (1_7, 4_7, 7_7) × 3 fasce età (0–10, 41–50, ≥81) |
| B2 | 7 righe | 7 fasce età estreme (0–15, 16, 30, 50, 70, 90, ≥97) |
| B3 | 13 righe (tutte) | Tabella piccola: rivedere ogni riga |
| B4 | 19 righe (tutte) | Tabella piccola: rivedere ogni riga + decidere caso skipped (camions) |
| BE 2024 | n/a | Decisione strategica D+B + roadmap re-spike OCR |

Per ogni spot-check il revisore registra l'esito nel checklist
template (vedi §6 e
`legal_data/sources/belgium/review/belgium_legal_review_checklist_template.csv`).

---

## 6. Criteri GO / NO-GO per approval

**Una fonte BE può passare a `approved` solo se TUTTI i seguenti
criteri sono verificati dallo Studio:**

### 6.1 Criteri trasversali (qualunque fonte)

- **C-1.** Hash SHA-256 del PDF on-disk == hash dichiarato nel
  `download_manifest.json`.
- **C-2.** Esiste una `LegalReview` (DB) firmata dal revisore
  legale con `decision=reviewed_or_approved` e `comment` non
  vuoto. *(Sarà creata in un iter futuro, NON in questo
  package.)*
- **C-3.** La `source_note` di ogni riga CSV contiene
  `legal_review_required=true` e `no_human_legal_approval=true`
  prima dell'approvazione, e dovrà essere aggiornata a
  `legal_review_required=false; no_human_legal_approval=false;
  reviewer=<nome>; reviewed_at=<data>;
  source_is_historical_2020=true` al momento dell'import
  approvato (il flag historical resta).
- **C-4.** Il revisore è identificato (nome cognome + ruolo +
  data) — registrato in `LegalSource.notes` o equivalente.

### 6.2 GO BE 2020 (historical_fallback)

- **G2020-1.** Spot-check §5 = 100 % match per i blocchi
  selezionati (B1: 9 righe, B2: 7, B3: 13, B4: 19).
- **G2020-2.** Lo Studio conferma per iscritto che BE 2020 è
  utilizzabile **come historical_fallback** (non come riferimento
  attuale) finché BE 2024 non è approved.
- **G2020-3.** Per B2 (filename ambiguo): decisione tassonomica
  documentata (mantenere / rinominare / split). Senza decisione,
  B2 resta in `needs_review`.
- **G2020-4.** Per B4 (caso camions skipped): decisione
  documentata su come gestire la formula
  `50 + 10×tonnes`.
- **G2020-5.** I dataset/formule in DB devono esporre
  `is_historical=true` (o equivalente) nel campo metadati e nel
  report PDF utente: il calcolatore deve segnalare
  esplicitamente che il valore è basato su BE 2020 finché
  BE 2024 non è disponibile.

### 6.3 GO BE 2024 (corrente/ufficiale) — NON in questo iter

- **G2024-0.** ⚠️ **Bloccato finché:**
  - Tesseract dispone di `fra` e `nld` lang pack (oggi mancanti);
  - re-spike OCR è eseguito ed è documentato;
  - decisione D+B (BELGIUM_TI_2024_OCR_SPIKE_REPORT §9) è
    confermata dallo Studio.
- **G2024-1.** Spot-check 100 % manuale (non solo campionario)
  su ogni cella numerica, vista la natura image-scanned.
- **G2024-2.** Allineamento taxonomy con BE 2020 documentato
  (5 vs 13 relazioni décès; Julin riposizionato).

### 6.4 NO-GO automatico (bloccanti)

- **N-1.** Hash PDF non corrispondente al manifest.
- **N-2.** Almeno 1 spot-check §5 con valore differente dal
  PDF.
- **N-3.** Manca la `LegalReview` firmata.
- **N-4.** `source_note` contiene `no_human_legal_approval=false`
  senza review firmata.
- **N-5.** Il revisore non è identificato (nome+data assenti).
- **N-6.** Regressione su test esistenti (Italia, FR, TUN,
  MA, BE-2020-precedente) imputabile all'import.
- **N-7.** Per BE 2024: qualsiasi import basato su OCR senza
  review manuale al 100 % è NO-GO.

---

## 7. Cosa NON deve essere approvato senza review

Lista esplicita per evitare ambiguità.

- ❌ **Nessuna riga di B1, B2, B3, B4 può essere importata
  in `CompensationDataset`** finché lo Studio non ha firmato
  la `LegalReview` corrispondente (criterio C-2).
- ❌ **Nessuna `CalculationFormula` BE può essere creata**
  finché il dataset di riferimento non è approved.
- ❌ **Nessuna feature flag** (`enable_belgium_calculator=true`)
  può essere attivata in produzione finché manca anche una
  sola riga blocco approvata.
- ❌ **Nessun valore numerico estratto in modo automatico
  dovrebbe comparire nel report PDF utente** prima
  dell'approvazione, neppure come "esempio".
- ❌ **Nessun import di BE 2024** basato su OCR (opzione A) —
  vietato dal report di OCR spike. Solo opzioni B/C/D ammesse.
- ❌ **Nessun seed / management command** che marchi `approved`
  in modo programmatico una fonte BE senza passare dal flusso
  di `LegalReview`.
- ❌ **Nessuna sostituzione silenziosa** di BE 2020 con BE 2024:
  quando BE 2024 sarà approved, la migrazione deve essere
  esplicita (`replaced` su BE 2020 con timestamp e ref alla
  nuova versione).

---

## 8. BE 2020 = historical_fallback (chiarimento esplicito)

> **Decisione raccomandata di questo package**: trattare BE 2020
> come **fonte storica/fallback**, non come riferimento corrente.

Motivazioni:
- È l'edizione precedente alla versione 2024 ufficiale del
  Tableau Indicatif (T.Pol./J.J.Pol.). Le decisioni
  giurisprudenziali post-2024 tendono a citare il TI 2024.
- Gli importi BE 2024 sono ~+15 % vs BE 2020 (vedi spike
  OCR §6): usare BE 2020 in produzione sottostima
  sistematicamente il danno.
- La taxonomy BE 2024 differisce (5 vs 13 relazioni décès) e
  richiede una riconciliazione esplicita.

Implicazioni operative:
- Il `source_note` di ogni riga BE 2020 contiene già
  `source_is_historical_2020=true`. Confermato dalla QA.
- Quando il calcolatore BE userà BE 2020, il **report PDF
  utente** deve segnalare *"valore indicativo basato su Tableau
  Indicatif 2020 (édition storica) — la versione 2024 non è
  ancora validata"*. Questo è obbligo esplicito di review.
- Il `LegalSource.status` di `be-tableau-indicatif-2020`
  potrà passare a `approved` ma con `notes` che chiariscono
  l'uso come fallback.

---

## 9. BE 2024 = OCR / manual review NON pronto (chiarimento esplicito)

> ⚠️ **BE 2024 NON è oggi pronto per il review.**

Motivazioni (riassunte da `BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`):
- PDF image-scanned (23 pagine, 0 caratteri estratti, 23
  immagini per pagina).
- Tesseract 5.5.0 installato ma senza i language pack
  necessari (`fra`, `nld`). Solo `eng` + `osd` disponibili.
- Errori sistematici osservati: separatore migliaia
  non-deterministico (`15,000` vs `15.000` per la stessa
  cella), `≥` letto come `2` o `=`, formule spezzate su due
  righe.
- Quality OCR ottenuta sui 3 sample pages (p.9, p.14, p.17):
  PSM 4 cattura il 100 % delle righe, ma con 2-3 errori per
  pagina che richiedono review manuale. **Inaccettabile per
  approval senza review umana al 100 %.**

Cosa NON fare:
- ❌ NON eseguire un'estrazione OCR di tutto il PDF e
  importare il risultato come dataset (opzione A,
  rifiutata).
- ❌ NON chiedere al motore LLM di "trascrivere" il PDF: stessa
  classe di rischio.

Cosa lo Studio deve fare per sbloccare BE 2024:
1. **Decisione strategica**: optare per D+B (raccomandata) o
   per C (manuale completa).
2. **Per D+B**: installare `fra` e `nld` lang pack di
   Tesseract, eseguire un nuovo iter
   `F-belgium-ocr-ti-2024-fra-nld-spike` e confrontare la
   qualità con questo spike. Solo dopo: pianificare
   `F-belgium-ti-2024-extraction` con review manuale al 100 %.
3. **Per C**: assegnare un revisore al PDF stampato e
   trascrivere riga per riga in CSV strutturato. Il template
   M3 di Mornet (FR) può servire da riferimento.
4. In nessun caso BE 2024 può essere `approved` senza
   review manuale al 100 % delle celle (criterio
   G2024-1).

---

## 10. Sequenza futura proposta per import DB

Tutti gli iter sotto sono **proposte**: nessuno è iniziato.
Lo Studio decide quale eseguire e in che ordine.

### 10.1 Iter 1 — Studio review BE 2020 (puramente umano)

- **Nome candidato:** `F-belgium-studio-review-iter1`
- **Output:** completare il file
  `belgium_legal_review_checklist_template.csv` riga per riga
  per i blocchi B1..B4 + decisione tassonomica B2 + decisione
  formula camions B4.
- **Vincoli:** nessun import DB, nessun cambio codice.
- **Esito:** decisione GO / NO-GO per ciascuno dei 4 blocchi
  (souffrances, indemnité forfaitaire, décès affection,
  véhicule).

### 10.2 Iter 2 — DB seed read-only di BE 2020 (historical_fallback)

- **Nome candidato:** `F-belgium-import-datasets-readonly-seed-2020`
- **Trigger:** GO almeno su un blocco BE 2020.
- **Cosa fa:** management command che importa le righe CSV
  approvate in `CompensationDataset` con stato `approved` e
  flag `is_historical=true` (o equivalente nel modello),
  preservando `source_note` aggiornata. Crea `LegalReview`
  registrate. Nessun cambio calculator/wizard.
- **QA:** uno script `qa_belgium_db_post_seed.py` verifica
  conteggi, hash, flag historical, totali per blocco.

### 10.3 Iter 3 — Calculator BE scheletro (consume BE 2020)

- **Nome candidato:** `F-belgium-calculator-skeleton`
- **Trigger:** Iter 2 verde su almeno B1 + B3 (souffrances +
  décès affection: minimo per un wizard "danno biologico" e
  "perdita rapporto parentale" BE).
- **Cosa fa:** crea/aggiorna `apps/calculators/engines/belgium.py`
  consumando `CompensationDataset` BE. Output conforme al
  contract standard. Nessun valore hard-coded. Banner
  "historical_fallback" obbligatorio nel report.
- **Vincoli:** non attiva il calcolatore lato pubblico finché
  non c'è feature flag `enable_belgium_calculator=true`.

### 10.4 Iter 4 — OCR re-spike BE 2024 con `fra`/`nld`

- **Nome candidato:** `F-belgium-ocr-ti-2024-fra-nld-spike`
- **Trigger:** Studio installa Tesseract `fra` + `nld` lang
  pack (operazione extra-Claude).
- **Cosa fa:** ri-esegue lo spike OCR con i language pack
  corretti, su 2-3 sample pages identiche allo spike
  precedente, e confronta numericamente i risultati. Aggiorna
  `BELGIUM_TI_2024_OCR_SPIKE_REPORT.md` (o ne crea uno nuovo
  versione 2).
- **Vincoli:** read-only, niente import DB.

### 10.5 Iter 5 — Estrazione BE 2024 + manual review (heavy)

- **Nome candidato:** `F-belgium-ti-2024-extraction-with-manual-review`
- **Trigger:** Iter 4 verde con qualità OCR sufficiente (≥99 %
  cifre corrette su sample pages).
- **Cosa fa:** estrazione full PDF + revisione manuale al
  100 %. Output: CSV BE 2024 candidate read-only. NON
  approvato automaticamente.
- **Vincoli:** ogni cella numerica deve essere validata
  manualmente da revisore.

### 10.6 Iter 6 — Migrazione BE 2020 → BE 2024

- **Nome candidato:** `F-belgium-migrate-2020-to-2024`
- **Trigger:** Iter 5 verde + LegalReview firmata su BE 2024.
- **Cosa fa:** `LegalSource` `be-tableau-indicatif-2020` passa
  a `replaced` con ref alla nuova versione. Datasets
  historical_2020 restano nel DB ma non sono più la default
  del calcolatore. Il calcolatore BE consuma BE 2024.
- **Vincoli:** migrazione esplicita, mai silenziosa. Test di
  regressione + diff numerico.

### 10.7 Iter 7 — Schryvers (capitalizzazione belga)

- **Nome candidato:** `F-belgium-schryvers-capitalization`
- **Trigger:** dopo iter 5 stabile. Tableurs Schryvers
  scaricati manualmente.
- **Cosa fa:** estrarre tabelle di capitalizzazione belghe
  per rendite viagère/temporanee. Equivalente belga della
  Gazette du Palais 2022 francese.
- **Vincoli:** stesso flusso candidate → review → approved.

### 10.8 Note di sequenza

- È **non accettabile** saltare Iter 1 e andare direttamente
  in Iter 2: l'approval senza review umana viola CLAUDE.md.
- È **non accettabile** saltare Iter 4 e andare direttamente
  in Iter 5: senza fra/nld lang pack lo spike OCR è
  inaffidabile.
- Iter 3 può essere posticipato se lo Studio preferisce un
  calcolatore BE solo dopo BE 2024 (skip historical_fallback).

---

## 11. File del package

### 11.1 Committable (nessun valore legale)

- `docs/legal_sources/BELGIUM_LEGAL_REVIEW_PACKAGE.md` — questo
  file.
- `legal_data/sources/belgium/review/belgium_legal_review_checklist_template.csv`
  — template di checklist (vedi sezione successiva). Nessun
  valore legale; solo header + righe pre-popolate con `pending`.
- `scripts/legal_data/qa_belgium_review_package.py` — QA
  read-only sul package. Nessun import DB.
- `.gitignore` — eccezione già presente (aggiunta in iter
  F-france-legal-review-package: `!legal_data/sources/*/review/*_template.csv`).

### 11.2 Già esistenti (non rigenerati da questo iter)

- `docs/legal_sources/BELGIUM_EXTRACTION_PLANNING.md`
- `docs/legal_sources/BELGIUM_TI_2020_EXTRACTION_REPORT.md`
- `docs/legal_sources/BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`
- `scripts/legal_data/extract_belgium_ti_2020.py`
- `scripts/legal_data/qa_belgium_ti_2020.py`
- `scripts/legal_data/ocr_belgium_ti_2024_spike.py`

### 11.3 Gitignored (path on-disk; nessun PDF/CSV in repo)

- `legal_data/sources/belgium/downloaded/*.pdf`,
  `*.html` (manifest committable; PDF/HTML no).
- `legal_data/sources/belgium/tableau_indicatif_2020/*.csv`
- `legal_data/sources/belgium/tableau_indicatif_2020/extraction_summary.json`
- `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/`
  (PNG, TXT, spike_summary.json).
- `legal_data/sources/belgium/review/` (eccezione: solo i
  `*_template.csv` sono committabili).

---

## 12. Disclaimer

Il presente package non rappresenta una valutazione legale né
una raccomandazione operativa per lo Studio. Costituisce solo
una mappa tecnica dei dati candidati estratti e dei controlli
necessari prima di qualsiasi import DB. Ogni decisione finale
sull'approvazione delle fonti, sui criteri di calcolo e sulla
loro pubblicazione resta in capo allo Studio Legale Internazionale
Badrane. La simulazione, una volta resa pubblica, dovrà comunque
riportare il disclaimer obbligatorio definito in CLAUDE.md.
