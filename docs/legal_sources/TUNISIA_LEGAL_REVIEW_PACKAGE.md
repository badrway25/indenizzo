# TN — Package di review legale (read-only)

**Iter**: F-maghreb-legal-review-packages · iter1
**Data**: 2026-04-30
**Stato**: read-only — **nessun import DB, nessuna approvazione,
nessuna creazione di `LegalReview`, `CompensationDataset`,
`CalculationFormula`, nessun calculator engine reale, nessun
mapping legale definitivo**.

> Documento operativo che consolida le fonti legali tunisine
> già scaricate o registrate (Code du statut personnel — Livre
> IX, Code de droit international privé Loi 98-97, JORT
> storico, Reg. UE 650/2012) in un pacchetto consegnabile allo
> Studio per la review legale. **Questa fase è solo review
> package / mapping checklist — non si scrive un singolo
> coefficiente né una singola quota faraïd.**

---

## 0. Avvertenze

- Il presente package **non** approva, **non** importa, **non**
  crea righe DB. Non genera `LegalReview`, `CompensationDataset`,
  `CalculationFormula`. Non modifica calculator, wizard, Italia,
  Marocco, Francia, Belgio.
- Le successioni tunisine sono regolate dal **Code du statut
  personnel (CSP), Livre IX «De la succession»** (1956,
  modificato successivamente). Le quote farḍ tunisine sono
  storicamente basate sul fiqh malikita, ma il CSP introduce
  alcune deviazioni codificate (es. enfants nés hors mariage,
  rappresentanza, ecc.) che lo distinguono dalla Moudawana
  marocchina.
- La Tunisia ha un **Code de droit international privé** del
  1998 (Loi n°98-97) — più articolato del Marocco — che
  fornisce le proprie regole di conflitto di leggi.
- Questo iter produce solo una checklist; nessun valore è
  estratto.
- I file scaricati non sono committati (gitignored). Il
  manifest JSON e il presente documento sono committabili.
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

## 1. Inventario fonti registrate (LegalSource TN)

Verificato sul DB locale + manifest
`legal_data/sources/tunisia/downloaded/download_manifest.json`.

| Slug | Tipo | Reliability | Stato | File on-disk | Manual? |
|---|---|---|---|---|:-:|
| `tn-code-statut-personnel-livre-ix-succession` | `official_law` | `high` | `needs_review` | HTML (36 KB) | no |
| `tn-code-dip-loi-98-97` | `official_law` | `official` | `needs_review` | HTML (181 KB) | no |
| `tn-jort-code-statut-personnel-1956` | `official_law` | `official` | `needs_review` | — | **YES** |
| `tn-code-statut-personnel-compiled` | `official_law` | `high` | `needs_review` | — | **YES** |
| `eu-regulation-650-2012-successions-fr-tn` | `official_law` | `official` | `needs_review` | — | **YES** |

### 1.1 Sorgenti HTML — hash e size

| Slug | Path | Size (B) | SHA-256 | Manifest |
|---|---|---:|---|:-:|
| `tn-code-statut-personnel-livre-ix-succession` | `legal_data/sources/tunisia/downloaded/tn-code-statut-personnel-livre-ix-succession.html` | 36 183 | `ab8078968ccfa07eaefc34bb38a1ec49071d000dfe0ffd85b1410d343a348ffd` | OK |
| `tn-code-dip-loi-98-97` | `legal_data/sources/tunisia/downloaded/tn-code-dip-loi-98-97.html` | 181 484 | `9a37ed5e5a28403f9760050b435aecfc5dd4e798fcbf0f962fd1af05352cddbe` | OK |

### 1.2 Manuale richiesto (3 fonti)

- `tn-jort-code-statut-personnel-1956`: `pist.tn` non
  raggiungibile dal datacenter (ConnectTimeout). Lo Studio
  scarica manualmente il fascicolo JORT 1956 da `pist.tn` o
  `iort.gov.tn` e attacca via Django admin.
- `tn-code-statut-personnel-compiled`: SSL hostname mismatch
  su `jafbase.fr`. Lo Studio scarica la versione consolidata
  completa da `legislation.tn` o `iort.gov.tn` se serve la
  copertura completa (per il Livre IX `tn-code-statut-personnel-livre-ix-succession`
  HTML è già disponibile).
- `eu-regulation-650-2012-successions-fr-tn`: stesso problema
  EUR-Lex visto in MA. Download manuale richiesto.

### 1.3 Stato DB (invarianti)

- 5 `LegalSource` TN, **tutte** in `needs_review`.
- 0 `CompensationDataset` TN.
- 0 `CalculationFormula` con `dataset.country=TN`.
- 0 `LegalReview` su fonti TN.

---

## 2. Distinzione fra diritto interno e conflitto di leggi

Le successioni di un cittadino tunisino o di un caso con
elementi tunisini possono essere regolate da norme **di natura
diversa**. Il revisore deve tenere distinte:

### 2.1 Diritto interno tunisino (legge sostanziale)

- **Code du statut personnel (CSP)** — promulgato dal Décret
  beylical du 13 août 1956, applicato dal 1° janvier 1957.
  Modificato successivamente (legge 81-7 del 1981 sulla
  successione enfants nés hors mariage, ecc.). Livre IX
  «De la succession» è la fonte normativa primaria.
- **CSP — version compilée** (slug
  `tn-code-statut-personnel-compiled`): edizione consolidata
  con tutte le modifiche; manuale, da scaricare da
  `legislation.tn`.
- **JORT 1956** (slug `tn-jort-code-statut-personnel-1956`):
  promulgazione originale. Utile per validare la versione
  storica e tracciare il versioning. **Manuale.**

### 2.2 Conflitto di leggi / DIP

- **Loi n°98-97 du 27 novembre 1998 portant Code de droit
  international privé** (slug `tn-code-dip-loi-98-97`). HTML
  disponibile. Articoli rilevanti per le successioni:
  - **art. 49 e ss.** sulla legge applicabile alla
    successione (regola di principio: legge nazionale del
    defunto al momento del decesso, salvo eccezioni).
  - **art. 27** ordine pubblico tunisino.
  - **art. 36** ʿAdaptation / qualification.
  - **art. 50** ʿforma del testamento.
  - **art. 51** trasmissione successoria di immobili
    (lex situs in alcuni casi).
- **Reg. UE n°650/2012**: si applica quando il foro è UE
  (es. defunto residente in Italia con eredi/asset in Tunisia).
  La Tunisia non è Stato membro UE, quindi reg. 650/2012 non
  vincola i giudici tunisini ma vincola quelli italiani.
  Articoli chiave: **art. 21** (residenza abituale), **art. 22**
  (professio juris), **art. 23** (ambito), **art. 31**
  (adattamento dei diritti reali), **art. 34** (renvoi),
  **art. 35** (ordine pubblico).
- Convenzione bilaterale Italia–Tunisia di assistenza
  giudiziaria (1968): rilevante per riconoscimento di atti e
  sentenze, **non** per la legge applicabile.

### 2.3 Implicazione operativa

> Un calcolatore TN non può limitarsi a "applicare le quote
> CSP Livre IX": deve prima qualificare il caso (defunto
> nazionalità tunisina? residenza dove? professio juris?
> immobili dove?) e selezionare la legge applicabile
> incrociando la Loi 98-97 (foro tunisino) e/o il reg. UE
> 650/2012 (foro UE). La presenza di una **doppia regola di
> conflitto** rende la qualifica più articolata che per il
> Marocco.

---

## 3. Cosa deve verificare lo Studio

### 3.1 Per ogni LegalSource TN

| Slug | Cosa lo Studio deve verificare |
|---|---|
| `tn-code-statut-personnel-livre-ix-succession` | HTML estratto da `jurisitetunisie.com` — non ufficiale. Confronto con la versione consolidata `compiled` (manuale). Gli articoli devono coincidere. |
| `tn-code-dip-loi-98-97` | HTML da `legislation-securite.tn` — semi-ufficiale. Versione consolidata? Gli articoli rilevanti per la successione (49 ss., 50, 51, 27, 36) sono completi? |
| `tn-jort-code-statut-personnel-1956` | Recupero PDF JORT 1956 (manuale, `pist.tn` o `iort.gov.tn`). Versione storica per tracciare l'evoluzione. |
| `tn-code-statut-personnel-compiled` | Recupero PDF consolidato (manuale, `legislation.tn` o `iort.gov.tn`). Versione di riferimento per il mapping. |
| `eu-regulation-650-2012-successions-fr-tn` | Recupero PDF EUR-Lex. Versione consolidata. Decisione esplicita renvoi/ordine pubblico per casi TN. |

### 3.2 Articoli/temi da mappare (CSP Livre IX)

Per ogni argomento sotto, il revisore conferma articolo,
contenuto, casi-limite. **Nessun valore numerico è
trascritto da Claude in questo iter.**

| # | Tema | Articoli TN (indicativi) | Nota review |
|---|---|---|---|
| 1 | Definizione di erede e vocazione | 85–87 | Condizioni della vocation, capacità a succedere. |
| 2 | Cause di esclusione | 88–90 | Differenza musulmano/non-musulmano, omicidio. Particolarità TN: la giurisprudenza tunisina ha attenuato alcune esclusioni rispetto al fiqh classico (rilevante). |
| 3 | Eredi farḍ (quote fisse) | 91 ss. | Coniuge, padre, madre, figli, fratelli. |
| 4 | Eredi ʿaṣaba (residuari) | 100 ss. | Linea agnatica. |
| 5 | Eredi misti (farḍ + ʿaṣaba) | varie | Es. padre con discendenti vs senza. |
| 6 | ʿawl (réduction proportionnelle) | varie | Quando le quote farḍ superano l'unità. |
| 7 | Radd (restitution du résidu) | varie | Trattamento del coniuge nel radd: confronto con la Moudawana MA (lo Studio deve documentare la differenza). |
| 8 | Eredi figli nati fuori dal matrimonio | Loi 98-75 sulla filiation; CSP modif. | Particolarità tunisina: la legge tunisina riconosce diritti successori in alcune condizioni (rilevante). |
| 9 | Successione tra cittadini stranieri / non musulmani | CSP + Loi 98-97 | Coordinamento con DIP. |
| 10 | Testamento (waṣiyya) | varie | Limite 1/3, divieto a favore di erede salvo accordo. |
| 11 | Dette e charges successorie | varie | Ordine: spese funerarie, debiti, legato, eredi. |
| 12 | Liquidazione dell'indivision (chouyou) | CSP + Code obligations | Diritto di prélation tra coeredi. |

> ⚠️ Le quote numeriche specifiche (1/2, 1/4, 1/6, 1/8, 1/3,
> 2/3) NON sono in questo documento. Saranno trascritte solo
> dopo che il revisore avrà confermato lo schema completo in
> un iter successivo (vedi §6).

### 3.3 Articoli/temi da mappare (Code DIP Loi 98-97)

| # | Tema | Articoli TN (indicativi) | Nota review |
|---|---|---|---|
| 1 | Definizione legge applicabile alla successione | 49 ss. | Default: legge nazionale del defunto al momento del decesso. Eccezioni. |
| 2 | Forma del testamento | 50 | Validità formale: lex loci o legge scelta. |
| 3 | Trasmissione successoria di immobili | 51 | Lex situs in casi specifici. |
| 4 | Ordine pubblico tunisino | 27 | Limite all'applicazione di leggi straniere. |
| 5 | Qualification / adattamento | 36 | Quando le categorie giuridiche straniere non corrispondono. |
| 6 | Coordinamento con reg. UE 650/2012 | n/a | La Loi 98-97 vincola il foro TN; reg. 650/2012 vincola il foro UE. Casi di disallineamento e cosa fare. |

---

## 4. Checklist suggerita di review

| Fonte | Azioni |
|---|---|
| CSP Livre IX (HTML) | Verificare ogni macro-tema della tabella §3.2 (12 voci). Per ognuno: conferma articolo, conferma applicabilità, identificazione di casi-limite. Confronto HTML vs compiled. |
| CSP compiled (manuale) | Lo Studio scarica la versione consolidata. Validazione completezza vs HTML. |
| JORT 1956 (manuale) | Lo Studio scarica il fascicolo originale. Tracciamento delle modifiche post-1956. |
| Loi 98-97 (HTML) | Verificare i 6 macro-temi della tabella §3.3. Decisione esplicita su renvoi/ordine pubblico (art. 27, 36) per casi UE. |
| Reg. UE 650/2012 (manuale) | Recupero EUR-Lex. Decisione su come gestire il rinvio TN→UE e UE→TN. |

Per ogni voce il revisore registra l'esito nel checklist
template (vedi §5 e
`legal_data/sources/tunisia/review/tunisia_legal_review_checklist_template.csv`).

---

## 5. Criteri GO / NO-GO

### 5.1 Criteri trasversali

- **C-1.** SHA-256 del file on-disk == manifest (per HTML
  scaricati e PDF se ricaricati manualmente).
- **C-2.** Esiste una `LegalReview` (DB) firmata dal revisore
  legale con `decision=reviewed_or_approved` e `comment` non
  vuoto. *(Sarà creata in un iter futuro, NON in questo
  package.)*
- **C-3.** Il revisore è identificato (nome cognome + ruolo +
  data) — registrato in `LegalSource.notes`.
- **C-4.** L'HTML estratto da `jurisitetunisie.com` o
  `legislation-securite.tn` è qualificato come **fonte
  documentale, non ufficiale**, e accompagnato dal documento
  ufficiale (JORT/IORT) per le approvazioni che richiedono
  reliability `official`.

### 5.2 GO mapping (per fonte)

- **G-1.** Tutti i 12 macro-temi §3.2 hanno almeno un articolo
  CSP confermato.
- **G-2.** Tutti i 6 macro-temi §3.3 hanno almeno un articolo
  Loi 98-97 confermato.
- **G-3.** Lo Studio ha una posizione documentata su renvoi e
  ordine pubblico per casi TN sia in foro TN (art. 27, 36
  Loi 98-97) sia in foro UE (art. 34, 35 reg. 650/2012).
- **G-4.** L'edizione di riferimento CSP è dichiarata e
  versionata (es. "CSP, version au DD/MM/YYYY, da JORT
  consolidato, comprensiva di Loi 81-7, Loi 93-74, Loi 98-75
  ecc.").
- **G-5.** Lo Studio prende posizione **scritta** sul
  trattamento delle particolarità tunisine (enfants nés hors
  mariage, attenuazioni giurisprudenziali sulle esclusioni,
  filiazione).

### 5.3 NO-GO automatico

- **N-1.** Hash file non corrispondente al manifest.
- **N-2.** Manca `LegalReview` firmata.
- **N-3.** Revisore non identificato.
- **N-4.** Tentativo di importare quote farḍ come
  `CompensationDataset` numerico **senza** mapping degli
  articoli CSP corrispondenti riga per riga.
- **N-5.** Tentativo di attivare il calcolatore TN in
  produzione finché manca un singolo macro-tema §3.2 o §3.3.
- **N-6.** Uso dell'HTML `jurisitetunisie.com` o
  `legislation-securite.tn` come fonte primaria senza la
  versione ufficiale JORT/IORT consolidata.
- **N-7.** Regressione su test esistenti (Italia, FR, BE, MA)
  imputabile a questo iter.

---

## 6. Warning operativo: nessun calculator prima della mappatura

> ⚠️ **Nessun calculator engine reale può essere implementato
> finché questo mapping legale non è completato e firmato dallo
> Studio.**

Stato attuale del calcolatore TN (`apps/calculators/engines/tunisia.py`):
- `_TunisiaPlaceholderCalculator` ritorna sempre
  `unavailable_requires_legal_validation`;
- `TunisiaInternationalInheritanceCalculator` registrato sulla
  coppia `TN-NATIONAL × international_inheritance` ma
  comportamento = placeholder.
- Il funnel pubblico `/wizard/tn/inheritance/` raccoglie input
  qualitativi (parentela, status civile, professio juris,
  paesi degli asset) ma **non** calcola alcuna quota.

Cosa è esplicitamente vietato in questo iter:
- ❌ Tradurre nel codice quote farḍ (1/2 al coniuge senza
  figli, 1/4 al coniuge con figli, ecc.) prima del mapping.
- ❌ Hard-codare schemi di esclusione nel motore.
- ❌ Aggiungere `CalculationFormula` TN nel DB.
- ❌ Rimuovere il flag `unavailable_requires_legal_validation`
  dal placeholder.
- ❌ Sostituire l'HTML come fonte primaria.
- ❌ Implementare la qualificazione DIP (art. 49 Loi 98-97 vs
  art. 21 reg. 650/2012) prima che lo Studio prenda posizione
  scritta sul renvoi.

Cosa lo Studio deve approvare prima di abilitare un calcolatore
TN reale:
1. Mapping completato (criteri G-1, G-2, G-5 di §5.2).
2. Trascrizione strutturata delle quote in un CSV candidate
   (iter futuro: `F-tunisia-csp-quotes-extraction-manual`).
3. Review legale e `LegalReview` firmata.
4. Posizione documentata sulla qualificazione DIP per casi
   con foro UE.

---

## 7. Cosa NON deve essere approvato senza review

- ❌ **Nessuna `LegalSource` TN** può passare a `approved`
  senza review firmata + mapping articolato.
- ❌ **Nessuna `CompensationDataset` TN** senza dataset
  derivato dal mapping.
- ❌ **Nessuna `CalculationFormula` TN** senza dataset
  approvato di riferimento.
- ❌ **Nessuna feature flag** (`enable_tunisia_inheritance_calculator=true`)
  in produzione finché il placeholder non è sostituito da un
  motore basato su mapping firmato.
- ❌ **Nessun valore numerico (quota, percentuale)** nel
  report PDF utente prima dell'approvazione.
- ❌ **Nessuna trascrizione del CSP** generata da modello LLM
  senza review umana riga per riga.
- ❌ **Nessun import** del Reg. UE 650/2012, JORT 1956 o CSP
  compiled finché lo Studio non li recupera manualmente.

---

## 8. Sequenza futura proposta

Tutti gli iter sotto sono **proposte**: nessuno è iniziato.

### 8.1 Iter 1 — Recupero fonti manuali

- **Nome candidato:** `F-tunisia-manual-downloads-attach`
- **Output:** lo Studio scarica manualmente JORT 1956, CSP
  compiled, reg. UE 650/2012 e attacca via Django admin
  (`LegalSourceAttachment`). Stato: `needs_review`.
- **Vincoli:** nessun import DB.

### 8.2 Iter 2 — Studio review TN (mapping articoli)

- **Nome candidato:** `F-tunisia-studio-mapping-iter1`
- **Output:** completare il file
  `tunisia_legal_review_checklist_template.csv` riga per riga.
  Verifica versione CSP, mapping di tutti i 12 macro-temi §3.2
  e dei 6 macro-temi §3.3, decisione su HTML vs JORT, posizione
  su renvoi/ordine pubblico.
- **Vincoli:** nessun import DB.
- **Esito:** GO/NO-GO al mapping per CSP Livre IX e Loi 98-97.

### 8.3 Iter 3 — Trascrizione quote farḍ (manual fourchettes-style)

- **Nome candidato:** `F-tunisia-csp-quotes-extraction-manual`
- **Trigger:** Iter 2 verde su CSP.
- **Cosa fa:** estrazione strutturata delle quote in CSV
  candidate (read-only), seguendo lo schema visto per Mornet
  manual fourchettes (FR). Header esplicito;
  `transcription_status` per cella; `source_quote_short`
  (citazione testuale dell'articolo CSP);
  `legal_review_required=true` su tutte le righe.
  Specificità tunisine documentate (enfants nés hors mariage,
  giurisprudenza attenuativa).
- **Vincoli:** nessun automatismo LLM. Trascrizione manuale
  o estrazione `pdfplumber`/HTML parser con review riga per
  riga.

### 8.4 Iter 4 — DB seed read-only

- **Nome candidato:** `F-tunisia-import-datasets-readonly-seed`
- **Trigger:** Iter 3 verde + LegalReview firmata.
- **Cosa fa:** management command che importa le righe CSV
  approvate in `CompensationDataset` TN. Crea `LegalReview`.
  Nessuna modifica calculator/wizard.

### 8.5 Iter 5 — Calculator engine reale TN

- **Nome candidato:** `F-tunisia-inheritance-calculator-engine`
- **Trigger:** Iter 4 verde su CSP + Loi 98-97 mappata.
- **Cosa fa:** sostituisce `_TunisiaPlaceholderCalculator` con
  un engine che applica le quote farḍ partendo dai dataset
  approvati e dalla qualifica del caso (Loi 98-97 + reg.
  650/2012). Output conforme al contract standard.
- **Vincoli:** non attiva il calcolatore lato pubblico finché
  feature flag `enable_tunisia_inheritance_calculator=true`
  non è esplicito.

### 8.6 Iter 6 — Wizard TN pubblico

- **Nome candidato:** `F-tunisia-inheritance-wizard-public`
- **Trigger:** Iter 5 verde + dry-run su casi-pilota.
- **Cosa fa:** abilitazione del wizard pubblico
  `/wizard/tn/inheritance/` con calcolo reale, report PDF
  con disclaimer obbligatorio, banner "fonte: CSP Livre IX
  + Loi 98-97 + reg. UE 650/2012 (qualifica preliminare)".

### 8.7 Note di sequenza

- È **non accettabile** saltare Iter 2 e andare direttamente
  in Iter 3.
- È **non accettabile** saltare Iter 1 prima di chiudere casi
  con foro tunisino o foro UE: senza JORT 1956 / CSP compiled
  / reg. 650/2012, la base autoritativa è insufficiente.
- A differenza del Marocco, la Tunisia ha un **codice DIP
  proprio**: lo Studio deve esplicitamente decidere come
  coordinare Loi 98-97 e reg. 650/2012 quando entrambi
  potenzialmente applicabili. Questo è un blocker reale.

---

## 9. File del package

### 9.1 Committable

- `docs/legal_sources/TUNISIA_LEGAL_REVIEW_PACKAGE.md` —
  questo file.
- `legal_data/sources/tunisia/review/tunisia_legal_review_checklist_template.csv`
  — template di checklist (vedi sezione successiva).
- `scripts/legal_data/qa_maghreb_review_packages.py` — QA
  read-only su MA + TN (condiviso con il package Marocco).
- `.gitignore` — eccezione per template review già presente
  da iter F-france-legal-review-package.

### 9.2 Già esistenti (non rigenerati)

- `docs/architecture/TUNISIA_INHERITANCE_MODULE_STATUS.md`
- `apps/calculators/engines/tunisia.py` (placeholder)
- `apps/legal_sources/management/commands/seed_tunisia_inheritance_legal_sources.py`
- `templates/public/wizard_tunisia_inheritance.html`
- `legal_data/sources/tunisia/downloaded/download_manifest.json`

### 9.3 Gitignored

- `legal_data/sources/tunisia/downloaded/*.html`,
  `*.pdf` (manifest committable; HTML/PDF no).
- `legal_data/sources/tunisia/review/` (eccezione: solo i
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
