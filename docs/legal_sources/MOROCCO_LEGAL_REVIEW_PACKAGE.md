# MA — Package di review legale (read-only)

**Iter**: F-maghreb-legal-review-packages · iter1
**Data**: 2026-04-30
**Stato**: read-only — **nessun import DB, nessuna approvazione,
nessuna creazione di `LegalReview`, `CompensationDataset`,
`CalculationFormula`, nessun calculator engine reale, nessun
mapping legale definitivo**.

> Documento operativo che consolida le fonti legali marocchine
> già scaricate o registrate (Moudawana, Code des droits réels,
> Reg. UE 650/2012) in un pacchetto consegnabile allo Studio
> per la review legale. **Questa fase è solo review package /
> mapping checklist — non si scrive un singolo coefficiente né
> una singola quota faraïd.**

---

## 0. Avvertenze

- Il presente package **non** approva, **non** importa, **non**
  crea righe DB. Non genera `LegalReview`, `CompensationDataset`,
  `CalculationFormula`. Non modifica calculator, wizard, Italia,
  Tunisia, Francia, Belgio.
- Le successioni marocchine sono regolate dal **diritto
  musulmano codificato nella Moudawana** (Code de la famille,
  Loi n°70-03, 2004): le quote faraïd sono altamente
  combinatoriali (status civile × parentela × presenza/assenza
  di altri eredi × genere). **Il rischio di errore di
  trascrizione è elevato.** Per questo motivo questo iter
  produce solo una checklist; nessun valore è estratto.
- I PDF scaricati non sono committati (gitignored). Il manifest
  JSON e il presente documento sono committabili.
- La regola fondamentale (CLAUDE.md): nessun calcolo finché un
  revisore legale dello Studio non valida le quote e
  l'orientamento applicabile. Ogni fonte è oggi `needs_review`.
- Disclaimer obbligatorio (CLAUDE.md): "La simulazione è
  indicativa e non costituisce parere legale, medico-legale o
  garanzia di risultato. La valutazione effettiva dipende da
  documenti, perizie, responsabilità, legge applicabile,
  giurisdizione competente, orientamenti giudiziari e prassi
  assicurative."

---

## 1. Inventario fonti registrate (LegalSource MA)

Verificato sul DB locale + manifest
`legal_data/sources/morocco/downloaded/download_manifest.json`.

| Slug | Tipo | Reliability | Stato | File on-disk | Manual? |
|---|---|---|---|---|:-:|
| `ma-code-famille-moudawana-fr-pdf` | `official_law` | `high` | `needs_review` | PDF (489 KB) | no |
| `ma-code-droits-reels-loi-39-08` | `official_law` | `high` | `needs_review` | PDF (282 KB) | no |
| `ma-code-droits-reels-traduction-aute` | `official_law` | `medium` | `needs_review` | PDF (548 KB) | no |
| `eu-regulation-650-2012-successions-fr-ma` | `official_law` | `official` | `needs_review` | — | **YES** |

### 1.1 Sorgenti PDF — hash e size

| Slug | Path | Size (B) | SHA-256 | Manifest |
|---|---|---:|---|:-:|
| `ma-code-famille-moudawana-fr-pdf` | `legal_data/sources/morocco/downloaded/ma-code-famille-moudawana-fr-pdf.pdf` | 489 071 | `41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96` | OK |
| `ma-code-droits-reels-loi-39-08` | `legal_data/sources/morocco/downloaded/ma-code-droits-reels-loi-39-08.pdf` | 282 302 | `55e190cfd1b1c236d7ab0a7f1eb2508f62018646dc55c300e5880c6546710799` | OK |
| `ma-code-droits-reels-traduction-aute` | `legal_data/sources/morocco/downloaded/ma-code-droits-reels-traduction-aute.pdf` | 548 484 | `605d1a65fcce7a3ca882a23eb7c5d43dfcfae525a1441389051885ea0188e72d` | OK |

### 1.2 Manuale richiesto

- `eu-regulation-650-2012-successions-fr-ma`: scaricamento
  automatico fallito (EUR-Lex restituisce HTTP 202 con body
  vuoto per richieste non-browser). Lo Studio deve scaricare
  manualmente il PDF/HTML ufficiale dalla pagina EUR-Lex e
  attaccarlo via Django admin (`LegalSourceAttachment`).

### 1.3 Stato DB (invarianti)

- 4 `LegalSource` MA, **tutte** in `needs_review`.
- 0 `CompensationDataset` MA.
- 0 `CalculationFormula` con `dataset.country=MA`.
- 0 `LegalReview` su fonti MA.

---

## 2. Distinzione fra diritto interno e conflitto di leggi

Le successioni di un cittadino marocchino o di un caso con
elementi marocchini possono essere regolate da norme
**di natura diversa**. Il revisore deve tenere distinte:

### 2.1 Diritto interno marocchino (legge sostanziale)

Si applica quando, dopo qualifica del case-type, la legge
applicabile è quella marocchina. Fonti di questo package:

- **Moudawana / Code de la famille** (Loi n°70-03, 2004) —
  Livre III «Successions». Quote faraïd, vocations
  successorales, regole sull'eredità tra musulmani e
  non-musulmani, dispositif di parità incompleta, ḥajb
  (esclusione parziale), ʿawl (riduzione proporzionale), radd
  (rest), ecc.
- **Code des droits réels** (Loi n°39-08, 2011) — disposizioni
  patrimoniali su immobili che intervengono nella liquidazione
  successoria (proprietà, copropriété, indivision, melk,
  habous).
- **Code des droits réels — traduction**: traduzione non
  ufficiale, da usare come strumento di lavoro ma **mai come
  fonte legale autoritativa**. Reliability `medium` (vs `high`
  della versione FAO/legifrance ufficiale).

### 2.2 Conflitto di leggi / DIP

Si applica quando il caso è transfrontaliero (defunto
residente in Italia, asset in Marocco, eredi in Francia, ecc.).

- **Reg. UE n° 650/2012** (Successions internationales) —
  determina la legge applicabile alla successione di una
  persona la cui ultima residenza abituale è in uno Stato
  membro UE. Articolo chiave: **art. 21** (legge della
  residenza abituale come default; lex situs per immobili in
  certi casi); **art. 22** (professio juris — scelta della
  legge nazionale); **art. 23** (ambito della legge
  applicabile); **art. 31** (adattamento dei diritti reali).
- Il Marocco **non** è uno Stato membro UE: il reg. 650/2012
  vincola i giudici UE (es. italiani) ma non quelli
  marocchini. Per gli aspetti di **renvoi** (art. 34) e di
  ordine pubblico (art. 35) lo Studio deve avere un'opinione
  documentata.
- Convenzione bilaterale Italia–Marocco di assistenza
  giudiziaria (1971): rilevante per riconoscimento di atti e
  sentenze, ma **non** disciplina la legge applicabile.

### 2.3 Implicazione operativa

> Un calcolatore MA non può limitarsi a "applicare le quote
> Moudawana": deve prima qualificare il caso (defunto residente
> dove? professio juris? immobili dove?) e selezionare la
> legge applicabile in base al reg. 650/2012 quando il foro è
> UE. Senza questa qualifica, anche una quota faraïd corretta
> applicata al caso sbagliato è una decisione legale errata.

---

## 3. Cosa deve verificare lo Studio

### 3.1 Per ogni LegalSource MA

| Slug | Cosa lo Studio deve verificare |
|---|---|
| `ma-code-famille-moudawana-fr-pdf` | Versione: l'edizione 2004 (Loi 70-03) è quella vigente al momento del review? Esistono modifiche successive (es. Dahirs, jurisprudence Cour de Cassation MA)? Lingua: la versione FR è ufficialmente promulgata o è una traduzione? |
| `ma-code-droits-reels-loi-39-08` | Loi 39-08 promulgata il 22 novembre 2011: ancora vigente? Confronto con la versione araba ufficiale (BORM). |
| `ma-code-droits-reels-traduction-aute` | Traduzione non ufficiale (sito aute.gov.ma). NON usare come autoritativa. Reliability `medium`. Decisione: tenerla come strumento di lavoro o degradarla a `deprecated`? |
| `eu-regulation-650-2012-successions-fr-ma` | Recupero PDF/HTML EUR-Lex. Versione consolidata (con eventuali rettifiche/atti modificativi) o versione originale? Decisione esplicita su come gestire renvoi e ordine pubblico nei casi MA. |

### 3.2 Articoli/temi da mappare (Moudawana, Livre III)

Per ogni argomento sotto, il revisore conferma articolo,
contenuto, casi-limite. **Nessun valore numerico è
trascritto da Claude in questo iter.**

| # | Tema | Articoli MA (indicativi) | Nota review |
|---|---|---|---|
| 1 | Vocazione ereditaria — definizione | 322–323 | Definizione di erede, condizioni della vocation. |
| 2 | Cause di esclusione (ḥajb totale) | 327–331 | Differenza musulmano/non-musulmano (art. 332), persona di diversa religione, omicidio. |
| 3 | Eredi farḍ (quote fisse) | 337 ss. | Coniuge, padre, madre, figli, fratelli, ecc. |
| 4 | Eredi ʿaṣaba (residuari) | 343 ss. | Linea agnatica. |
| 5 | Eredi misti (farḍ + ʿaṣaba) | varie | Es. padre con discendenti vs senza. |
| 6 | ʿawl (réduction proportionnelle) | 358 | Quando le quote farḍ superano l'unità. |
| 7 | Radd (restitution du résidu) | 359 | Eccezione coniuge: il radd al coniuge è dibattuto. |
| 8 | Eredità in caso di assenza di erede farḍ/ʿaṣaba | 360 ss. | Bayt al-māl o Stato. |
| 9 | Dette e charges successorie | 322, 326 | Ordine: spese funerarie, debiti, legato (max 1/3), eredi. |
| 10 | Testamento (waṣiyya) | 277 ss. (Livre VI) | Limite 1/3, divieto a favore di erede salvo accordo unanime. |
| 11 | Eredità degli enfants nés hors mariage | varie | Statut filial e ricostruzione della filiation. |
| 12 | Eredità mista (cittadini stranieri) | 332 + reg. 650/2012 | Coordinamento con DIP. |

> ⚠️ Le quote numeriche specifiche (1/2, 1/4, 1/6, 1/8, 1/3,
> 2/3) NON sono in questo documento. Saranno trascritte solo
> dopo che il revisore avrà confermato lo schema completo in
> un iter successivo (vedi §6).

### 3.3 Articoli/temi da mappare (Code des droits réels)

| # | Tema | Articoli MA (indicativi) | Nota review |
|---|---|---|---|
| 1 | Tipologie di proprietà foncier (melk, habous public/famille) | varie | Impatto su massa successoria. |
| 2 | Indivision (chouyou) | varie | Diritto di prélation tra coeredi. |
| 3 | Trasferimento successorio della propriété | varie | Atti di notorietà, certificat d'hérédité, conservation foncière. |

---

## 4. Checklist suggerita di review

Dimensione minima per il primo round (poi iterabile).

| Fonte | Azioni |
|---|---|
| Moudawana, Livre III | Verificare ogni macro-tema della tabella §3.2 (12 voci). Per ognuno: conferma articolo, conferma applicabilità, identificazione di casi-limite. |
| Code des droits réels | Verificare i 3 macro-temi della tabella §3.3. |
| Code des droits réels — traduction | Decisione: tenere come supporto o degradare. |
| Reg. UE 650/2012 | Recuperare PDF EUR-Lex, validare versione consolidata, decidere policy renvoi/ordine pubblico per casi MA. |

Per ogni voce il revisore registra l'esito nel checklist
template (vedi §5 e
`legal_data/sources/morocco/review/morocco_legal_review_checklist_template.csv`).

---

## 5. Criteri GO / NO-GO

### 5.1 Criteri trasversali

- **C-1.** SHA-256 del PDF on-disk == manifest.
- **C-2.** Esiste una `LegalReview` (DB) firmata dal revisore
  legale con `decision=reviewed_or_approved` e `comment` non
  vuoto. *(Sarà creata in un iter futuro, NON in questo
  package.)*
- **C-3.** Il revisore è identificato (nome cognome + ruolo +
  data) — registrato in `LegalSource.notes`.
- **C-4.** La traduzione (`ma-code-droits-reels-traduction-aute`)
  non può essere usata da sola come fonte autoritativa: deve
  essere accompagnata dalla versione ufficiale.

### 5.2 GO mapping (per fonte)

- **G-1.** Tutti i 12 macro-temi §3.2 hanno almeno un articolo
  Moudawana confermato.
- **G-2.** Tutti i 3 macro-temi §3.3 hanno almeno un articolo
  Code des droits réels confermato.
- **G-3.** Lo Studio ha una posizione documentata su renvoi e
  ordine pubblico per casi MA (rilevante per casi con foro
  italiano).
- **G-4.** L'edizione di riferimento Moudawana è dichiarata e
  versionata (es. "Loi 70-03 promulgata il 3 février 2004,
  Dahir n° 1-04-22, BO n° 5184, version au DD/MM/YYYY").

### 5.3 NO-GO automatico

- **N-1.** Hash PDF non corrispondente al manifest.
- **N-2.** Manca `LegalReview` firmata.
- **N-3.** Revisore non identificato.
- **N-4.** Tentativo di importare quote faraïd come
  `CompensationDataset` numerico **senza** mapping degli
  articoli Moudawana corrispondenti riga per riga.
- **N-5.** Tentativo di attivare il calcolatore MA in
  produzione finché manca un singolo macro-tema §3.2.
- **N-6.** Uso della traduzione `aute` come fonte primaria
  (deve essere sempre incrociata con la versione ufficiale).
- **N-7.** Regressione su test esistenti (Italia, FR, BE, TN)
  imputabile a questo iter.

---

## 6. Warning operativo: nessun calculator prima della mappatura

> ⚠️ **Nessun calculator engine reale può essere implementato
> finché questo mapping legale non è completato e firmato dallo
> Studio.**

Stato attuale del calcolatore MA (`apps/calculators/engines/morocco.py`):
- `_MoroccoPlaceholderCalculator` ritorna sempre
  `unavailable_requires_legal_validation`;
- `MoroccoInternationalInheritanceCalculator` registrato sulla
  coppia `MA-NATIONAL × international_inheritance` ma
  comportamento = placeholder.
- Il funnel pubblico `/wizard/ma/inheritance/` raccoglie input
  qualitativi (parentela, status civile, professio juris,
  paesi degli asset) ma **non** calcola alcuna quota.

Cosa è esplicitamente vietato in questo iter:
- ❌ Tradurre nel codice quote faraïd (1/2 al coniuge senza
  figli, 1/4 al coniuge con figli, ecc.) prima del mapping.
- ❌ Hard-codare schemi di esclusione (ḥajb) nel motore.
- ❌ Aggiungere `CalculationFormula` MA nel DB.
- ❌ Rimuovere il flag `unavailable_requires_legal_validation`
  dal placeholder.
- ❌ Sostituire la traduzione `aute` come fonte primaria.

Cosa lo Studio deve approvare prima di abilitare un calcolatore
MA reale:
1. Mapping completato (criteri G-1, G-2 di §5.2).
2. Trascrizione strutturata delle quote in un CSV candidate
   (iter futuro: `F-morocco-moudawana-extraction-tables`),
   con la stessa disciplina usata per FR/BE (no_human_legal_approval=true,
   legal_review_required=true, ecc.).
3. Review legale e `LegalReview` firmata.

---

## 7. Cosa NON deve essere approvato senza review

- ❌ **Nessuna `LegalSource` MA** può passare a `approved`
  senza review firmata + mapping articolato.
- ❌ **Nessuna `CompensationDataset` MA** senza dataset
  derivato dal mapping.
- ❌ **Nessuna `CalculationFormula` MA** senza dataset
  approvato di riferimento.
- ❌ **Nessuna feature flag** (`enable_morocco_inheritance_calculator=true`)
  in produzione finché il placeholder non è sostituito da un
  motore basato su mapping firmato.
- ❌ **Nessun valore numerico (quota, percentuale)** nel report
  PDF utente prima dell'approvazione, neppure come "esempio".
- ❌ **Nessuna trascrizione della Moudawana** generata da
  modello LLM senza review umana riga per riga.
- ❌ **Nessun import** del Reg. UE 650/2012 finché lo Studio
  non lo recupera manualmente.

---

## 8. Sequenza futura proposta

Tutti gli iter sotto sono **proposte**: nessuno è iniziato.

### 8.1 Iter 1 — Recupero Reg. UE 650/2012

- **Nome candidato:** `F-eu-650-2012-manual-download-attach`
- **Output:** lo Studio scarica manualmente da EUR-Lex e
  carica via Django admin
  (`LegalSourceAttachment`). Stato: `needs_review`.
- **Vincoli:** nessun import DB, nessun cambio codice.

### 8.2 Iter 2 — Studio review MA (mapping articoli)

- **Nome candidato:** `F-morocco-studio-mapping-iter1`
- **Output:** completare il file
  `morocco_legal_review_checklist_template.csv` riga per riga.
  Verifica versione Moudawana, mapping di tutti i 12 macro-temi
  §3.2 e dei 3 macro-temi §3.3, decisione su traduzione, policy
  renvoi/ordine pubblico.
- **Vincoli:** nessun import DB.
- **Esito:** GO/NO-GO al mapping per Moudawana e Code des
  droits réels.

### 8.3 Iter 3 — Trascrizione quote faraïd (manual fourchettes-style)

- **Nome candidato:** `F-morocco-moudawana-quotes-extraction-manual`
- **Trigger:** Iter 2 verde su Moudawana.
- **Cosa fa:** estrazione strutturata delle quote in CSV
  candidate (read-only), seguendo lo schema visto per Mornet
  manual fourchettes (FR): `head_of_loss_code` →
  `inheritance_case_code`, `severity_code` → `family_situation_code`,
  ecc. Header esplicito; `transcription_status` per cella;
  `source_quote_short` (citazione testuale dell'articolo);
  `legal_review_required=true` su tutte le righe.
- **Vincoli:** nessun automatismo LLM. Trascrizione manuale
  o estrazione `pdfplumber` con review riga per riga.

### 8.4 Iter 4 — DB seed read-only delle fonti GO + dataset MA

- **Nome candidato:** `F-morocco-import-datasets-readonly-seed`
- **Trigger:** Iter 3 verde + LegalReview firmata.
- **Cosa fa:** management command che importa le righe CSV
  approvate in `CompensationDataset` MA con flag e
  `source_note` aggiornati. Crea `LegalReview`. Nessuna
  modifica calculator/wizard.

### 8.5 Iter 5 — Calculator engine reale MA

- **Nome candidato:** `F-morocco-inheritance-calculator-engine`
- **Trigger:** Iter 4 verde su Moudawana.
- **Cosa fa:** sostituisce `_MoroccoPlaceholderCalculator` con
  un engine che applica le quote faraïd partendo dai dataset
  approvati e dalla qualifica del caso (DIP / professio juris).
  Output conforme al contract standard.
- **Vincoli:** non attiva il calcolatore lato pubblico finché
  feature flag `enable_morocco_inheritance_calculator=true`
  non è esplicito.

### 8.6 Iter 6 — Wizard MA pubblico

- **Nome candidato:** `F-morocco-inheritance-wizard-public`
- **Trigger:** Iter 5 verde + dry-run su casi-pilota.
- **Cosa fa:** abilitazione del wizard pubblico
  `/wizard/ma/inheritance/` con calcolo reale, report PDF
  con disclaimer obbligatorio, banner "fonte: Moudawana
  Livre III + reg. UE 650/2012 (qualifica preliminare)".

### 8.7 Note di sequenza

- È **non accettabile** saltare Iter 2 e andare direttamente
  in Iter 3: la trascrizione delle quote senza mapping legale
  preliminare è proibita dalla regola fondamentale di CLAUDE.md.
- È **non accettabile** saltare Iter 1 prima di chiudere casi
  con foro italiano (la qualifica della legge applicabile
  passa dal reg. 650/2012).

---

## 9. File del package

### 9.1 Committable

- `docs/legal_sources/MOROCCO_LEGAL_REVIEW_PACKAGE.md` — questo
  file.
- `legal_data/sources/morocco/review/morocco_legal_review_checklist_template.csv`
  — template di checklist (vedi sezione successiva).
- `scripts/legal_data/qa_maghreb_review_packages.py` — QA
  read-only su MA + TN.
- `.gitignore` — eccezione per template review già presente
  da iter F-france-legal-review-package.

### 9.2 Già esistenti (non rigenerati)

- `docs/architecture/MOROCCO_INHERITANCE_MODULE_STATUS.md`
- `apps/calculators/engines/morocco.py` (placeholder)
- `apps/legal_sources/management/commands/seed_morocco_inheritance_legal_sources.py`
- `templates/public/wizard_morocco_inheritance.html`
- `legal_data/sources/morocco/downloaded/download_manifest.json`

### 9.3 Gitignored

- `legal_data/sources/morocco/downloaded/*.pdf`,
  `*.html` (manifest committable; PDF/HTML no).
- `legal_data/sources/morocco/review/` (eccezione: solo i
  `*_template.csv` sono committabili).

---

## 10. Disclaimer

Il presente package non rappresenta una valutazione legale né
una raccomandazione operativa per lo Studio. Costituisce solo
una mappa tecnica delle fonti scaricate o registrate e dei
controlli necessari prima di qualsiasi import DB o
implementazione di calcolatore reale. Ogni decisione finale
sull'approvazione delle fonti, sul mapping delle quote
successorie e sulla loro pubblicazione resta in capo allo
Studio Legale Internazionale Badrane. La simulazione, una
volta resa pubblica, dovrà comunque riportare il disclaimer
obbligatorio definito in CLAUDE.md.
