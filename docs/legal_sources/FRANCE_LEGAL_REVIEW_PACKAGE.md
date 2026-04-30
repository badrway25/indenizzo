# FR — Package di review legale (read-only)

**Iter**: F-france-legal-review-package · iter1
**Data**: 2026-04-30
**Stato**: read-only — **nessun import DB, nessuna approvazione,
nessuna creazione di `LegalReview`, `CompensationDataset` o
`CalculationFormula`**.

> Documento operativo che consolida quanto già estratto per la Francia
> (Gazette du Palais 2022 + Mornet 2024) in un pacchetto consegnabile
> allo Studio per la review legale. Non sostituisce i report di
> estrazione: fornisce solo la mappa, la checklist, i criteri GO/NO-GO
> e la sequenza futura proposta. Tutti i CSV referenziati sono
> **candidate read-only** (gitignored). Nessun valore numerico è
> stato approvato.

---

## 0. Avvertenze

- Il presente package **non** approva, **non** importa, **non** crea
  righe DB. Non genera `LegalReview`, `CompensationDataset`,
  `CalculationFormula`. Non modifica calculator, wizard, Italia,
  Tunisia, Marocco, Belgio.
- I CSV elencati esistono solo on-disk sotto `legal_data/sources/france/`
  e sono **gitignored** (`legal_data/sources/**/*.csv`).
- I valori contenuti nei CSV sono il risultato di estrazione automatica
  (Gazette + tabelle Mornet con tabella stampata) o di scaffold
  manuale (fourchettes Mornet senza tabella stampata): **nessuno è
  legalmente verificato**.
- La regola fondamentale del progetto resta valida: nessun importo
  pubblico finché un revisore legale dello Studio non approva la
  fonte. Ogni dato di questo package è oggi `needs_review` o
  scaffold privo di valore.
- Disclaimer obbligatorio (CLAUDE.md): "La simulazione è indicativa
  e non costituisce parere legale, medico-legale o garanzia di
  risultato. La valutazione effettiva dipende da documenti, perizie,
  responsabilità, legge applicabile, giurisdizione competente,
  orientamenti giudiziari e prassi assicurative."

---

## 1. Inventario CSV candidate

Ogni file è gitignored. Path relativo al repo root.

### 1.1 Gazette du Palais 2022 — capitalisation

| # | File | Header (colonne) | Righe dati | Fonte (PDF) |
|---|---|---|---:|---|
| G1 | `legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-viagere.csv` | `row_type, mortality_table, sex, age, interest_rate_pct, coefficient, source_page, source_note` | 416 | Gazette 2022, p.5–20 |
| G2 | `legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-temporaire.csv` | `row_type, mortality_table, sex, age, interest_rate_pct, target_age, coefficient, source_page, source_note` | 3 752 | Gazette 2022, p.5–20 |
| G3 | `legal_data/sources/france/gazette_2022/fr-gazette-2022-anticipated-payment-years.csv` | `row_type, mortality_table, sex, age, interest_rate_pct, years_value, source_page, source_note` | 20 | Gazette 2022, p.4 |

### 1.2 Mornet 2024 — référentiel indicatif

| # | File | Header (colonne) | Righe dati | Fonte (PDF) |
|---|---|---|---:|---|
| M1 | `legal_data/sources/france/mornet_2024/fr-mornet-2024-dfp-per-age-disability.csv` | `row_type, victim_age_min, victim_age_max, disability_min, disability_max, amount_min, amount_mid, amount_max, currency, source_page, source_note` | 180 | Mornet 2024, p.71 |
| M2 | `legal_data/sources/france/mornet_2024/fr-mornet-2024-prejudice-affection-per-relation.csv` | `row_type, relation_code, relation_label_fr, amount_min, amount_mid, amount_max, currency, source_page, source_note` | 11 | Mornet 2024, p.94 |
| M3 | `legal_data/sources/france/mornet_2024/fr-mornet-2024-manual-fourchettes-template.csv` | `row_type, head_of_loss_code, head_of_loss_label_fr, severity_code, severity_label_fr, victim_age_min, victim_age_max, amount_min, amount_mid, amount_max, unit, currency, source_page, source_quote_short, transcription_status, reviewer_notes, source_note` | 0 (solo header) | Mornet 2024, varie |
| M4 | `legal_data/sources/france/mornet_2024/fr-mornet-2024-manual-fourchettes-review_tasks.csv` | `head_of_loss_code, head_of_loss_label_fr, expected_structure, source_pages, instructions, transcription_status, reviewer, reviewer_notes` | 29 | Mornet 2024, varie (testo) |

**Note sui file:**

- M3 è uno **scaffold vuoto**. Lo Studio compila riga-per-riga le
  voci che ritiene utili in base a M4 (review_tasks).
- M4 è una **lista di task per il revisore**: indica i 29 capi di
  danno descritti narrativamente da Mornet senza tabella numerica
  stampata (es. souffrances endurées 1/7..7/7, dépenses de santé
  actuelles, perte de gains professionnels, etc.). Per ognuno è
  specificato `expected_structure` (`fourchette_per_severity`,
  `case_by_case`, `formula_based`, ecc.) e l'istruzione per il
  revisore.

---

## 2. Sorgenti PDF e hash

| Slug | PDF | Size (B) | SHA-256 | Pagine | Manifest |
|---|---|---:|---|---:|:-:|
| `fr-bareme-capitalisation-gazette-palais-2022` | `legal_data/sources/france/downloaded/fr-bareme-capitalisation-gazette-palais-2022.pdf` | 978 456 | `686a557b23fa9e76fcd30795e61fda1cc2396d230290b93398874203ebbef3ee` | 20 | OK |
| `fr-referentiel-mornet-2024` | `legal_data/sources/france/downloaded/fr-referentiel-mornet-2024.pdf` | 898 965 | `2dd2e760bc057b38275a7a6de24a62c009f6d04dd79573c00ee052f4f6df72b4` | 116 | OK |

Hash dichiarati nel `download_manifest.json` di
`legal_data/sources/france/downloaded/`. Gli script di estrazione e
QA verificano l'hash in apertura: ogni discrepanza blocca l'esecuzione.

---

## 3. Stato attuale `LegalSource` nel DB

Verificato in locale al momento della stesura di questo documento.
Tutte le 5 fonti FR sono in `needs_review` (nessuna `approved`,
nessuna `deprecated`, nessuna `replaced`).

| Slug | Tipo | Reliability | Stato | Note |
|---|---|---|---|---|
| `fr-loi-badinter-1985` | `official_law` | `official` | `needs_review` | Manual download required (Legifrance HTTP 403). Solo testo normativo, nessuna tabella. |
| `fr-nomenclature-dintilhac-2005` | `doctrine` | `official` | `needs_review` | HTML descrittivo. Nessun valore numerico. Riferimento concettuale per la nomenclatura dei préjudices. |
| `fr-referentiel-mornet-2024` | `court_table` | `high` | `needs_review` | PDF 116 pagine. 4 tabelle indicizzate (M1, M2). 29 voci narrative (M4). |
| `fr-bareme-capitalisation-gazette-palais-2022` | `court_table` | `high` | `needs_review` | PDF 20 pagine. 16 pagine tabellari estratte (G1, G2, G3). |
| `fr-bareme-capitalisation-gazette-palais-2025-page` | `court_table` | `high` | `needs_review` | Solo landing page HTML. PDF 2025 NON scaricato (richiede registrazione). Fuori scope di questo package. |

**Invarianti DB FR:**
- 0 `CompensationDataset` con `country=FR`.
- 0 `CalculationFormula` con `dataset.country=FR`.
- 0 `LegalReview` su fonti FR.

---

## 4. Cosa deve verificare lo Studio per ogni file

### 4.1 G1 — Capitalisation viagère (416 righe)

**Cosa è:** coefficiente di capitalizzazione di una rendita viagère
in funzione di `(sex, age, interest_rate_pct)`. Tabella di mortalità
INSEE 2017–2019 (`INSEEF` per donne, `INSEEH` per uomini).

**Cosa lo Studio deve verificare:**
1. La fonte è quella ufficiale Gazette du Palais 2022 (édition
   2022) e non una versione successiva o parallela.
2. Le tabelle di mortalità INSEE 2017–2019 sono ancora la base
   di riferimento al momento dell'eventuale approvazione (la
   Gazette 2025 cambia tabelle: l'approvazione del 2022 è
   esplicitamente "edizione 2022" e va trattata come
   versionata).
3. I 4 tassi attesi (-1.00, 0.00, +0.00, +1.00 ecc.) sono
   coerenti con quanto scritto nel PDF; in particolare il
   range di tassi del 2022 (vs 2018, 2020, 2025).
4. Spot-check: per `(sex=F, age=0, rate=-1.00)` il valore
   coefficiente attuale nel CSV deve corrispondere alla cella
   in alto a sinistra di p.5 del PDF.
5. Convenzione decimale: il punto è il separatore decimale
   (es. `136.868`). Confermare allineamento con la stampa
   originale.

### 4.2 G2 — Capitalisation temporaire (3 752 righe)

**Cosa è:** coefficiente di capitalizzazione di una rendita
temporanea da `age` ad `target_age`, in funzione di
`(sex, age, interest_rate_pct, target_age)`. Stessi tassi e
tabelle di mortalità di G1.

**Cosa lo Studio deve verificare:**
1. La struttura cartesiana (`age × target_age`) è completa per
   le combinazioni attese (4 ranges di età × 4 combinazioni
   sex/rate).
2. `age <= target_age` sempre (il calcolatore userà questo
   invariante).
3. `target_age` massimo è 99 (o 100) — confermare il bound
   superiore della Gazette 2022.
4. Spot-check: `(sex=F, age=20, rate=0.00, target_age=65)` deve
   corrispondere alla riga di p.13 del PDF.
5. Coefficienti decrescenti per età crescente a parità di
   target_age e tasso (sanity check matematico).

### 4.3 G3 — Anticipated payment years (20 righe)

**Cosa è:** anni medi di esperanza di vita per età/sesso/tasso,
usati per i versamenti anticipati. Estratti da p.4 del PDF.

**Cosa lo Studio deve verificare:**
1. Il `mortality_table` riportato (`INSEE-2017-2019`) corrisponde
   al testo di p.4 (il prefisso può variare rispetto a G1/G2:
   confermare se è normalizzato o se va separato per sex).
2. I 20 valori (5 età × 2 sex × 2 rate, indicativamente) sono
   completi.
3. La semantica `years_value` è **anni medi di vita residua**
   e non altro (es. anni di anticipazione). Confermare la
   denominazione legale.

### 4.4 M1 — DFP per età/disabilità (180 righe)

**Cosa è:** valore monetario per punto di Déficit Fonctionnel
Permanent (DFP) in funzione di `(victim_age_min..max,
disability_min..max)`. Estratta da p.71 del PDF Mornet 2024.

**Cosa lo Studio deve verificare:**
1. La tabella di p.71 è quella effettivamente usata da Mornet 2024
   come riferimento operativo (e non un esempio dottrinale o
   un confronto storico).
2. `amount_min == amount_mid == amount_max` (tutte uguali, perché
   la tabella Mornet stampa un valore unico per cella, non una
   forchetta). Confermare che lo Studio interpreta correttamente
   "valore puntuale Mornet" senza forchetta indicativa.
3. Le fasce di età (0–10, 11–20, 21–30, 31–40, 41–50, 51–60,
   61–70, 71–80, 81–90, ≥91) e di invalidità (1–5, 6–10, …,
   91–100) corrispondono esattamente alla griglia di p.71.
4. Spot-check: `(victim_age=0–10, disability=1–5)` = 2 310 €/punto;
   `(victim_age=21–30, disability=1–5)` = 1 960 €/punto.
5. Verificare la non-discriminazione: la struttura Mornet è
   "valore decrescente per età crescente". Lo Studio conferma
   che questo orientamento è ancora pratica corrente nella
   giurisprudenza Cass. Civ. 2.

### 4.5 M2 — Préjudice d'affection per relazione (11 righe)

**Cosa è:** forchetta `(min, mid, max)` di préjudice d'affection
per ciascun grado di parentela in caso di décès. Da p.94 del PDF.

**Cosa lo Studio deve verificare:**
1. Le 11 relazioni estratte coprono lo schema completo di
   Mornet (conjoint, enfant mineur, enfant majeur foyer/hors
   foyer, père/mère, frère/sœur, grand-parent, petit-enfant,
   etc.) e nessuna è duplicata o mancante.
2. Il caso speciale `Préjudice de l'enfant en cas de décès du
   père ou de la mère: foyer — enfant mineur déjà orphelin`
   ("Majoration de 40% à 60%") è stato volutamente **escluso**
   dal CSV automatico (skipped — vedi
   `extraction_summary.json`). Lo Studio decide se trasformarlo
   in una regola di majoration applicata ex-post o se ignorarlo
   nel MVP.
3. I `relation_code` (es. `conjoint_perte_conjoint`,
   `enfant_mineur_perte_parent`) sono coerenti con la
   tassonomia che lo Studio vuole esporre nel wizard.
4. Spot-check: `conjoint_perte_conjoint` = 20000 / 25000 / 30000;
   `enfant_mineur_perte_parent` = 25000 / 27500 / 30000.
5. Le forchette sono **indicative**: confermare che la
   variabilità giurisprudenziale tipica entro queste forchette
   è accettabile per una simulazione "indicativa e non legalmente
   vincolante".

### 4.6 M3 — Manual fourchettes (template vuoto)

**Cosa è:** scaffold vuoto. Lo Studio compila o lascia in
`pending`.

**Cosa lo Studio deve verificare:**
- Per ogni voce di M4 (review_tasks) lo Studio decide se
  compilare almeno una riga in M3, oppure lasciare la voce
  `pending` (= calcolatore non userà alcuna forchetta).
- Per le righe compilate, ogni `transcription_status`
  ammesso è `pending | transcribed | human_checked | rejected
  | needs_clarification`. Lo Studio firma la riga
  (`reviewer_notes`) prima del passaggio a `human_checked`.
- Lo script `qa_france_mornet_manual_fourchettes.py` esegue
  validazioni strutturali. Resta dovere del revisore
  l'allineamento numerico col PDF.

### 4.7 M4 — Review tasks (29 righe)

**Cosa è:** elenco operativo dei 29 capi di danno descritti
testualmente da Mornet senza tabella stampata. Funziona da
to-do list per la review.

**Cosa lo Studio deve verificare:**
- Per ogni `head_of_loss_code` decidere se è `case_by_case`
  (lasciare al calcolo concreto), `formula_based` (estrarre
  formula), `fourchette_per_severity` (compilare M3) o
  `out_of_scope_mvp`.
- Le `instructions` proposte sono **suggerimenti**: il revisore
  può sovrascriverle e annotare in `reviewer_notes`.

### 4.8 LegalSource non coperti dai CSV

| Slug | Stato attuale | Cosa lo Studio deve verificare |
|---|---|---|
| `fr-loi-badinter-1985` | `needs_review` | Recupero PDF consolidato da Legifrance (download manuale). Lettura del testo. Decisione: la Loi Badinter è una fonte di diritto sostanziale (responsabilità accidenti stradali) e non contiene tabelle, quindi nel MVP serve solo come citazione legale, non come dato calcolabile. Lo Studio conferma. |
| `fr-nomenclature-dintilhac-2005` | `needs_review` | Lettura del testo (HTML). Decisione: la nomenclatura Dintilhac è la **base concettuale** dei capi di danno (DFP, DFT, souffrances endurées, ecc.). Lo Studio conferma che il vocabolario del wizard FR mappa 1:1 alla nomenclatura Dintilhac. Nessun valore numerico. |
| `fr-bareme-capitalisation-gazette-palais-2025-page` | `needs_review` | Decisione: scaricare il PDF 2025 (richiede credenziali abbonato gazette-du-palais.fr) o restare con 2022. Nel MVP è ragionevole partire da 2022 e tenere 2025 per F-france-extraction-gazette-2025 (iter futuro). |

---

## 5. Checklist di spot-check suggerita

Per ridurre il carico di review, suggerimenti di campionamento.
La taglia indicata è il minimo per ottenere ragionevole confidenza
statistica e copertura strutturale (estremi + interno della tabella).

| File | Sample size suggerita | Strategia |
|---|---|---|
| G1 | 12 righe | 3 età estreme (0, 50, 99) × 4 combinazioni `(sex, rate)` |
| G2 | 16 righe | `(age=0, target=99)`, `(age=20, target=65)`, `(age=50, target=80)`, `(age=80, target=95)` × 4 `(sex, rate)` |
| G3 | 4 righe | 2 età × 2 sex |
| M1 | 9 righe | 3 fasce età estreme × 3 fasce invalidità (1–5, 21–30, 91–100) |
| M2 | 11 righe (tutte) | Tabella piccola: rivedere ogni riga |
| M3 | n/a | Validazione strutturale via `qa_france_mornet_manual_fourchettes.py`; il numero di righe compilate dipende dalla decisione di copertura dello Studio |
| M4 | 29 righe (tutte) | Decision sheet, ogni voce richiede una decisione esplicita |

Per ogni spot-check il revisore registra l'esito nel checklist
template (vedi §6 e
`legal_data/sources/france/review/france_legal_review_checklist_template.csv`).

---

## 6. Criteri GO / NO-GO per approval

**Una fonte FR può passare a `approved` solo se TUTTI i seguenti
criteri sono verificati dallo Studio:**

### 6.1 Criteri trasversali (qualunque fonte)

- **C-1.** Hash SHA-256 del PDF on-disk == hash dichiarato nel
  `download_manifest.json`. Verificato dagli script di
  estrazione/QA in apertura.
- **C-2.** Esiste una `LegalReview` (DB) firmata dal revisore
  legale con `decision=reviewed_or_approved` e `comment` non
  vuoto. *(Sarà creata in un iter futuro, NON in questo
  package.)*
- **C-3.** La `source_note` di ogni riga CSV contiene
  `legal_review_required=true` e `no_human_legal_approval=true`
  prima dell'approvazione, e dovrà essere aggiornata a
  `legal_review_required=false; no_human_legal_approval=false;
  reviewer=<nome>; reviewed_at=<data>` al momento dell'import
  approvato.
- **C-4.** Il revisore è identificato (nome cognome + ruolo +
  data) — registrato in `LegalSource.notes` o equivalente.

### 6.2 GO Gazette 2022 (G1 + G2 + G3)

- **G-1.** Spot-check §5 = 100 % match (12+16+4 = 32 righe).
- **G-2.** Lo Studio conferma per iscritto che la Gazette 2022
  è la versione di riferimento per il MVP (vs 2025).
- **G-3.** Il calcolatore FR pianificato consuma G1, G2, G3
  con i nomi di colonna attuali (firmware contract).
- **G-4.** Eventuali `interest_rate_pct` da escludere (es. tassi
  storici non più applicati) sono dichiarati esplicitamente.

### 6.3 GO Mornet 2024 (M1 + M2)

- **M1-1.** Spot-check §5 = 100 % match (9 + 11 = 20 righe).
- **M1-2.** Lo Studio conferma che `amount_min == amount_mid ==
  amount_max` per M1 (Mornet stampa valore unico, non forchetta)
  è la rappresentazione corretta.
- **M1-3.** Per M2, le 11 relazioni coprono il fabbisogno del
  wizard MVP. Eventuali relazioni mancanti sono notate ma non
  bloccano il GO (saranno trattate in iter successivo).
- **M1-4.** Caso "Majoration 40 %–60 %" (skipped): lo Studio
  decide se modellarla come regola applicata in fase di calcolo
  o come annotazione.

### 6.4 GO Mornet manual fourchettes (M3 + M4)

**M3 e M4 NON possono entrare in `approved` come blocco unico.**
La granularità è per riga / per `head_of_loss_code`.

- **MF-1.** Per ogni `head_of_loss_code` di M4, lo Studio deve
  prendere una decisione **scritta** (`expected_structure` finale,
  `transcription_status` finale).
- **MF-2.** Le righe `transcribed` o `human_checked` di M3 devono
  passare `qa_france_mornet_manual_fourchettes.py` con exit 0.
- **MF-3.** Almeno il `head_of_loss_code` con cui parte il MVP
  FR (probabilmente `fr_souffrances_endurees` p.68 e
  `fr_prejudice_esthetique_permanent` p.72) deve essere
  `human_checked` con range di valori e citazioni testuali.
- **MF-4.** Ogni riga `human_checked` deve avere
  `source_quote_short` (>= 5 char) che identifica
  inequivocabilmente il passaggio del PDF.

### 6.5 NO-GO automatico (bloccanti)

Si applica indipendentemente dai criteri sopra. Anche un solo
NO-GO blocca l'approval e mantiene la fonte in `needs_review`.

- **N-1.** Hash PDF non corrispondente al manifest.
- **N-2.** Almeno 1 spot-check §5 con valore differente dal PDF.
- **N-3.** Manca la `LegalReview` firmata.
- **N-4.** `source_note` contiene `no_human_legal_approval=true`
  alla riga dell'eventuale dataset DB.
- **N-5.** Il revisore non è identificato (nome+data assenti).
- **N-6.** Regressione su test esistenti (Italia, BE 2020,
  Tunisia) imputabile all'import.

---

## 7. Cosa resta manuale

- **Compilazione M3** per le voci scelte dal Studio (souffrances
  endurées, esthétique permanent, eventualmente altre).
- **Spot-check** sui CSV automatici (G1, G2, G3, M1, M2): è la
  parte non automatizzabile del processo.
- **Decisione tassonomica** per le voci `case_by_case` e
  `formula_based` di M4: lo Studio decide come modellarle nel
  calcolatore (non come dato tabellare ma come regola).
- **Lettura della Loi Badinter** e della **nomenclature Dintilhac**:
  serve a definire il vocabolario legale del wizard FR, non
  a importare dati.
- **Decisione versione Gazette**: 2022 (già scaricata) vs 2025
  (richiede acquisto/abbonamento). Il MVP può partire da 2022.
- **Decisione su tassi di interesse** e **versionamento**: i
  coefficienti di capitalizzazione cambiano con il tasso e con
  le tabelle di mortalità INSEE. Lo Studio definisce la policy
  di "tasso ufficiale per simulazione" (es. tasso 0 % come
  "neutrale" + tasso negativo come "scenario alternativo").

---

## 8. Cosa NON deve essere approvato senza review

Lista esplicita per evitare ambiguità.

- ❌ **Nessuna riga di G1, G2, G3, M1, M2 può essere importata
  in `CompensationDataset`** finché lo Studio non ha firmato
  la `LegalReview` corrispondente (criterio C-2).
- ❌ **Nessuna riga di M3 può essere `approved_for_import`**
  con `transcription_status != human_checked`.
- ❌ **Nessuna `CalculationFormula` FR può essere creata**
  finché il dataset di riferimento non è approved.
- ❌ **Nessuna feature flag** (`enable_france_calculator=true`)
  può essere attivata in produzione finché manca anche una
  sola riga blocco approvata (per la combinazione richiesta).
- ❌ **Nessun valore numerico estratto in modo automatico
  dovrebbe comparire nel report PDF utente** prima
  dell'approvazione, neppure come "esempio".
- ❌ **Nessun import** del PDF 2025 finché non è stato
  scaricato e validato lato manifest.
- ❌ **Nessun seed / management command** che marchi `approved`
  in modo programmatico una fonte FR senza passare dal flusso
  di `LegalReview`.

---

## 9. Sequenza futura proposta per import DB

Tutti gli iter sotto sono **proposte**: nessuno è iniziato.
Lo Studio decide quale eseguire e in che ordine.

### 9.1 Iter 1 — Studio review (puramente umano)

- **Nome candidato:** `F-france-studio-review-iter1`
- **Output:** completare il file
  `france_legal_review_checklist_template.csv` per ogni file di
  §1, riga per riga.
- **Vincoli:** nessun import DB, nessun cambio codice.
- **Esito:** decisione GO / NO-GO per ciascuno dei 4 blocchi
  (Gazette caps, DFP Mornet, affection Mornet, manual fourchettes).

### 9.2 Iter 2 — DB seed read-only delle fonti GO

- **Nome candidato:** `F-france-import-datasets-readonly-seed`
- **Trigger:** GO almeno su Gazette 2022 (G1+G2+G3) o su Mornet
  M1 o su Mornet M2.
- **Cosa fa:** management command che importa le righe CSV
  approvate in `CompensationDataset` con stato `approved`,
  preservando `source_note` aggiornata
  (`no_human_legal_approval=false`, `reviewer=…`,
  `reviewed_at=…`). Crea automaticamente le `LegalReview`
  registrate nello checklist.
- **Vincoli:** read-only sul resto. Nessuna modifica calculator,
  nessuna modifica wizard, nessuna modifica frontend.
- **QA:** uno script `qa_france_db_post_seed.py` verifica
  conteggi, hash, source_note, totali per blocco.

### 9.3 Iter 3 — Calculator FR scheletro

- **Nome candidato:** `F-france-calculator-skeleton`
- **Trigger:** GO + DB seed di almeno **un** blocco completo (es.
  Mornet M1 + M2 → wizard "danno biologico FR" + "perdita
  rapporto parentale FR").
- **Cosa fa:** crea `apps/calculators/engines/france.py` (oggi è
  un placeholder) consumando `CompensationDataset` FR. Output
  conforme al contract standard di CLAUDE.md (estimated_min/mid/max,
  breakdown, sources, assumptions, warnings, missing_documents,
  confidence, legal_disclaimer). Nessun valore hard-coded.
- **Vincoli:** non attiva il calcolatore lato pubblico finché non
  c'è feature flag `enable_france_calculator=true` esplicito.

### 9.4 Iter 4 — Wizard FR

- **Nome candidato:** `F-france-wizard-mvp`
- **Trigger:** Iter 3 verde + Iter 1 chiuso su almeno un capo di
  danno utile per il wizard.
- **Cosa fa:** wizard pubblico `wizard_france_inheritance` o
  `wizard_france_danno_biologico` (a scelta dello Studio) che
  raccoglie input e produce output via `france.py`. Test
  end-to-end. Disclaimer obbligatorio in fondo a ogni report.
- **Vincoli:** attivazione su staging, non su produzione, fino a
  ulteriore conferma dello Studio.

### 9.5 Iter 5 — Cleanup

- **Nome candidato:** `F-france-cleanup`
- **Trigger:** dopo Iter 4 stabile.
- **Cosa fa:** rimuove eventuali `_legacy` o import scaffold,
  documenta le versioni di tabelle di mortalità e tassi attivi,
  aggiorna `docs/architecture/PRODUCT_REQUIREMENTS.md` per
  Francia.

### 9.6 Note di sequenza

- È accettabile saltare Iter 4 e fare prima Iter 5 se lo Studio
  preferisce un calcolatore "back-office" prima del wizard
  pubblico.
- È **non accettabile** saltare Iter 1 e andare direttamente in
  Iter 2: l'approval senza review umana viola CLAUDE.md (regola
  fondamentale: nessun calcolo falso, nessun valore inventato).

---

## 10. File del package

### 10.1 Committable (nessun valore legale)

- `docs/legal_sources/FRANCE_LEGAL_REVIEW_PACKAGE.md` — questo
  file.
- `legal_data/sources/france/review/france_legal_review_checklist_template.csv`
  — template di checklist (vedi sezione successiva). Nessun
  valore legale; solo header + righe pre-popolate con `pending`.
- `scripts/legal_data/qa_france_review_package.py` — QA
  read-only sul package (vedi sezione successiva). Nessun
  import DB.
- `.gitignore` — eccezione per il template di checklist (vedi
  sezione 10.3).

### 10.2 Già esistenti (non rigenerati da questo iter)

- `docs/legal_sources/FRANCE_EXTRACTION_PLANNING.md`
- `docs/legal_sources/FRANCE_GAZETTE_2022_EXTRACTION_REPORT.md`
- `docs/legal_sources/FRANCE_MORNET_2024_EXTRACTION_REPORT.md`
- `docs/legal_sources/FRANCE_MORNET_2024_MANUAL_FOURCHETTES.md`
- `scripts/legal_data/extract_france_gazette_2022.py`
- `scripts/legal_data/qa_france_gazette_2022.py`
- `scripts/legal_data/extract_france_mornet_2024.py`
- `scripts/legal_data/qa_france_mornet_2024.py`
- `scripts/legal_data/seed_france_mornet_manual_fourchettes.py`
- `scripts/legal_data/qa_france_mornet_manual_fourchettes.py`

### 10.3 Gitignored (path on-disk; nessun PDF/CSV in repo)

- `legal_data/sources/france/downloaded/*.pdf`,
  `*.html`, `download_manifest.json` (manifest committable; PDF/HTML no).
- `legal_data/sources/france/gazette_2022/*.csv`
- `legal_data/sources/france/gazette_2022/extraction_summary.json`
- `legal_data/sources/france/mornet_2024/*.csv`
- `legal_data/sources/france/mornet_2024/extraction_summary.json`
- `legal_data/sources/france/mornet_2024/manual_fourchettes_seed_summary.json`
- `legal_data/sources/france/review/` (eccezione: solo il
  `france_legal_review_checklist_template.csv` template è
  committabile).

---

## 11. Disclaimer

Il presente package non rappresenta una valutazione legale né
una raccomandazione operativa per lo Studio. Costituisce solo
una mappa tecnica dei dati candidati estratti e dei controlli
necessari prima di qualsiasi import DB. Ogni decisione finale
sull'approvazione delle fonti, sui criteri di calcolo e sulla
loro pubblicazione resta in capo allo Studio Legale Internazionale
Badrane. La simulazione, una volta resa pubblica, dovrà comunque
riportare il disclaimer obbligatorio definito in CLAUDE.md.
