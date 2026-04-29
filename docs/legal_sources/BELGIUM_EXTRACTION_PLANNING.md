# BE — Piano tecnico di estrazione (read-only planning)

**Iter**: F-france-belgium-extraction-planning · iter1
**Data**: 2026-04-29
**Stato**: planning — **nessuna estrazione, nessun import DB,
nessuna approvazione**.

> Documento di lavoro per il prossimo iter di parsing
> (F-belgium-extraction-tableau-indicatif). Nessuna fonte BE è ancora
> `approved`, nessun `CompensationDataset` e nessuna `CalculationFormula`
> esiste per la giurisdizione `BE-NATIONAL`.

---

## 1. PDF analizzati e verifica integrità

Hash SHA-256 calcolato in locale e confrontato col `download_manifest.json`
di `legal_data/sources/belgium/downloaded/`.

| Slug | File | Size (B) | SHA-256 | Match manifest |
|---|---|---:|---|:-:|
| `be-tableau-indicatif-2024` | `be-tableau-indicatif-2024.pdf` | 2.373.682 | `37b0a0b4606ec39638db4a81c6074928c2275a09274a11597b8fb17e03bc3a45` | OK |
| `be-tableau-indicatif-2020` | `be-tableau-indicatif-2020.pdf` | 1.985.686 | `1b073f5c41c8414018e262143d7e67c496bbeeb832e623f406333b3ece0b8222` | OK |

Le altre fonti BE già scaricate sono HTML (Loi RC Auto 1989-11-21, due
landing Schryvers) e contengono solo testo normativo / link a
tableurs Excel. Il PDF Tableau Indicatif resta la fonte primaria di
valori indicativi.

Script di analisi: `scripts/legal_data/analyze_fr_be_pdfs.py` (condiviso
FR + BE, read-only).

---

## 2. Struttura PDF — Tableau Indicatif 2024

### 2.1. **CRITICO — il PDF 2024 è un'immagine scansionata**

Per ogni pagina (1..23) `pdfplumber` rileva:
- `text_chars = 0`
- `images = 1`

**Il PDF non contiene testo estraibile**: ogni pagina è una bitmap.
Nessuna tabella è rilevabile via `pdfplumber.find_tables()` (0 su 23).

### 2.2. Conseguenze

L'estrazione automatica **non è possibile via parser PDF testuale**.
Le opzioni concrete:

| Opzione | Pro | Contro |
|---|---|---|
| **A. OCR con Tesseract** (`pytesseract` + `pdf2image`) | preserva pipeline automatica; multilingue NL/FR già supportato da Tesseract | richiede installazione Tesseract OCR sul host (pacchetto di sistema, non solo `pip`); accuracy ~95% su tabelle bilingui (tipicamente tra 1% e 5% celle da correggere a mano); rischio confusione `€/euro`, `1` vs `l` |
| **B. Transcrizione manuale Studio** | accuracy 100%; pieno controllo legale su ogni cella | richiede ~4-8 ore/uomo per 23 pagine bilingui; non scalabile su edizioni successive |
| **C. Cross-check via Tableau Indicatif 2020 (testuale)** | il PDF 2020 è parseable e ha la **stessa struttura** del 2024; usare 2020 come "scaffolding strutturale" e poi solo aggiornare i valori monetari | richiede ancora una fonte 2024 per i numeri aggiornati |

**Raccomandazione**: combinare **A** + **C** — eseguire OCR del 2024
solo per **estrarre i numeri**, e usare 2020 come **template
strutturale** (header, label NL/FR, layout colonne). Successivamente
**B** per cross-check delle 5-10 celle/pagina dove l'OCR ha confidence
< 0.95.

---

## 3. Struttura PDF — Tableau Indicatif 2020

### 3.1. Profilo generale

- **Pagine**: 46
- **Layout**: bilingue NL (sinistra) / FR (destra), parallelo riga per
  riga. **Stesso valore monetario** appare in entrambe le lingue
  (i numeri non sono tradotti, solo le label).
- **Pagine con tabella reale (`pdfplumber.find_tables()`, ≥3 righe ×
  ≥2 colonne)**: 7 (p.17, 22, 23, 25, 26, 31, 32). Note: il numero
  reale di tabelle parseable è probabilmente più alto se si abbassa
  la soglia a 2 righe — molte sub-sezioni hanno mini-tabelle 2-righe
  embedded nel testo (p.es. `"Jusque 15 ans / tot 15 jaar  €1.220,00"`
  in p.22 = 41 righe rilevate, ma molte sono coppie label/valore, non
  vere matrici).

### 3.2. Sommario (TOC bilingue p.1-3)

Capitolo I — Schade aan personen / Dommage aux personnes:
- 2. Préjudice temporaire (frais médicaux, aides matérielles, aides
  tiers, incapacité personnelle, ménagère, économique, scolaire) —
  pp. 65-70
- 3. Préjudice permanent (modes d'indemnisation, frais médicaux,
  aides, incapacités personnelle/ménagère/économique, douleur,
  esthétique, sexuel, agrément) — pp. 70-78
- 3.5. Schade geleden door naastbestaanden / Préjudice des proches
  — p.78
- 4. Préjudice par décès — pp. 79-85

Capitolo II — Schade aan voorwerpen / Dommage aux objets:
- 1. Voertuigschade (TVA, gardiennage, indisponibilité,
  remplacement) — pp. 86-90
- 2. Frais de déplacement — p.90
- 3. Frais administratifs — p.91
- 4. Vêtements — p.91

Capitolo III — Intérêts et provisions: pp. 92-93.

Allegato — mission expert: p.94.

### 3.3. Tabelle reali — contenuto

| Pagina | Tipo | Estraibilità |
|---|---|---|
| **p.17** | Souffrances endurées — `[classe d'âge] × [Julin 1/7..7/7] → €` | OK — tabella 11 righe × 9 colonne, una NL e una FR (2 tabelle). Età: 0-10 / 11-20 / … / 81+. Scala Julin: minime → exception. grave. |
| **p.22-23** | Préjudice esthétique — `[âge en années] → €/an` | OK — età anno per anno (Jusque 15 ans, 16 ans, …, 95+ ans?). Tabelle 41+32 righe. |
| **p.25-26** | Préjudice par décès — `[victime décédée] × [bénéficiaire] → €` | OK — beneficiario per relazione (cohabitant/non cohabitant, conjoint, parent, enfant orphelin, …). 16+17 righe. |
| **p.31-32** | Indemnité véhicule de remplacement — `[type véhicule] → €/jour` | OK — bicyclette, 2/3 roues, remorque, voiture, mobilhome, etc. 16+18 righe. |

### 3.4. Conteggi keyword (case-insensitive, p.1-46)

| Keyword | Hits | Note |
|---|---:|---|
| `incapacité` | 65 | tema centrale |
| `préjudice` | 51 | tema centrale |
| `ITT` | 49 | abbreviazione presente |
| `consolidation` | 17 | concetto temporale |
| `économique` | 29 | sotto-categoria |
| `esthétique` | 7 | tabelle rilevate |
| `sexuel` | 7 | sotto-categoria |
| `agrément` | 6 | sotto-categoria |
| `scolaire` | 3 | sotto-categoria |
| `douleurs` | 6 | scala Julin |

---

## 4. BE 2020 → storico/fallback (proposta)

Il **Tableau Indicatif 2024** è l'edizione corrente di riferimento
giurisprudenziale (pubblicato dall'Union nationale des magistrats de
police / Vereniging Nationale van politierechters), ma è in formato
immagine e quindi **non è la fonte primaria di valori live** per
iter1.

Il **Tableau Indicatif 2020** è l'edizione precedente, parseable
testualmente. Proposta:

- **NON** usare il 2020 per simulazioni di sinistri datati post-2024
  (lo Studio rischierebbe di sotto-stimare il preavviso di causa).
- **SÌ** usare il 2020 come `dataset_version_label = "TABLEAU-INDICATIF-2020"`
  in stato `historical` (subset dello stato `replaced` quando il
  2024 sarà importato), valido per cause con data del fatto
  generatore precedente alla pubblicazione del 2024.
- **SÌ** usare il 2020 come **template strutturale** per il parser
  del 2024 (vedi §2.2 opzione C).

Quando il 2024 sarà importato e approvato, il dataset 2020 verrà
marcato `replaced_by_id = <pk del 2024>` ma resterà query-able per
cause storiche.

---

## 5. Schema CSV candidato — BE Tableau Indicatif 2024

> **NB**: lo schema sotto è quello target. L'effettivo file CSV può
> essere prodotto solo dopo OCR (opzione A) o transcrizione manuale
> (opzione B), quindi questo è uno schema **proposto, non un CSV
> esistente**.

### 5.1. `be-ti-2024-souffrances-endurees`

`row_type = "be_souffrances_endurees_per_age_scale_amount"`.

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `country_code` | str | `BE` | costante |
| `jurisdiction_code` | str | `BE-NATIONAL` | costante |
| `dataset_version_label` | str | `TABLEAU-INDICATIF-2024` | candidate |
| `row_type` | str | `be_souffrances_endurees_per_age_scale_amount` | costante |
| `age_min` | int | `0` | classe d'età min |
| `age_max` | int | `10` | classe d'età max |
| `julin_scale_num` | int | `1` | numeratore (1/7 → 7/7) |
| `julin_scale_den` | int | `7` | denominatore (sempre 7) |
| `julin_scale_label_fr` | str | `minime` / `très léger` / … | utile per esplicabilità |
| `julin_scale_label_nl` | str | `miniem` / `zeer licht` / … | etichetta NL |
| `point_value` | decimal | `540.00` | € |
| `currency` | str | `EUR` | costante |

**Stima righe**: 9 classi d'età × 7 livelli Julin = **63 righe**.

### 5.2. `be-ti-2024-prejudice-esthetique`

`row_type = "be_prejudice_esthetique_per_age_scale_amount"`.

| Colonna | Tipo | Esempio |
|---|---|---|
| `age` | int | `25` |
| `julin_scale_num` | int | `1..7` |
| `point_value` | decimal | `1140.00` |

**Stima righe**: ~80 età (15-95) × 7 scala = ~**560 righe** (se 2024
struttura come 2020 a singola età; da confermare in OCR).

### 5.3. `be-ti-2024-prejudice-deces`

`row_type = "be_prejudice_deces_per_relation_amount"`.

| Colonna | Tipo | Esempio |
|---|---|---|
| `victim_relation_code` | str | `parent_cohabitant` |
| `beneficiary_relation_code` | str | `enfant_cohabitant` |
| `condition` | str | `default` / `orphelin` |
| `amount` | decimal | `15000.00` |

**Stima righe**: 16-20.

### 5.4. `be-ti-2024-vehicule-remplacement`

`row_type = "be_vehicule_remplacement_per_type_per_day_amount"`.

| Colonna | Tipo | Esempio |
|---|---|---|
| `vehicle_type_code` | str | `voiture_750kg_ou_plus` |
| `vehicle_type_label_fr` | str | `voiture (usage professionnel)` |
| `vehicle_type_label_nl` | str | `personenwagen` |
| `daily_amount` | decimal | `20.00` |

**Stima righe**: ~10-15.

### 5.5. Restanti voci 2024 → manuale o OCR + review

I valori monetari **non in tabella** (forfaits incapacité personnelle/
ménagère/économique citati nel testo, taux di rivalutazione,
forfaits per consolidation, …) richiedono transcrizione manuale del
Studio anche dopo OCR.

---

## 6. Schema CSV candidato — BE Tableau Indicatif 2020 (storico)

Stessi schemi della §5 con:
- `dataset_version_label = "TABLEAU-INDICATIF-2020"`;
- `dataset.status = "historical"` (subset `replaced` post-2024);
- `dataset.notes = "Edizione 2020. Sostituita dall'edizione 2024 per cause con fatto generatore post-2024-XX-XX."` (data esatta da confermare in iter di import).

I valori in tabella vanno presi dalle pagine identificate al §3.3.

---

## 7. Cosa è estraibile automaticamente vs. richiede review umana

### 7.1. Tableau Indicatif 2024 — automaticità per fase

| Fase | Modalità | Confidence |
|---|---|---|
| **OCR pagina-per-pagina** | Tesseract NL+FR, output → testo grezzo | ~95% righe corrette |
| **Riconoscimento layout tabella** | template-based via 2020 (stesso layout colonne) | ~90% allineamento corretto |
| **Estrazione celle numeriche** | regex `r'€\s*([\d\.,]+)'` | ~98% (numeri sono pattern semplice) |
| **Estrazione label bilingui** | dictionary-based 2020 → 2024 (il vocabolario non cambia tra le due edizioni) | ~95% |
| **Cross-check 2020 vs 2024** | per ogni cella, verificare che `val_2024 ≥ val_2020` (ipotesi inflazione) | property test |

### 7.2. Tableau Indicatif 2020 — automaticità

Le 4 famiglie di tabelle nel §3.3 sono direttamente estraibili con
`pdfplumber.find_tables()` + post-processing. Le restanti voci nel
testo (incapacité personnelle/ménagère/économique forfaitaire,
forfaits scolaire, taux interesse, …) richiedono regex sul corpo
testuale + verifica manuale.

### 7.3. Richiede legal review **prima** di approvazione

- Verifica integrità OCR su almeno il 20% delle righe estratte dal
  2024 (campionamento random + spot di celle "borderline" come
  tabelle dense).
- Verifica giurisprudenziale: i tribunali belgi seguono Tableau
  Indicatif solo come **base indicativa**; il Studio deve dichiarare
  esplicitamente che il dataset è "indicativo, non vincolante".
- Verifica edizione: confermare che il PDF 2024 è l'edizione
  pubblicata ufficialmente (non draft / proposta).
- Allineamento NL/FR: per ogni `relation_code` /
  `vehicle_type_code`, confermare che label NL e FR si riferiscono
  allo stesso concetto.

---

## 8. Rischi e ostacoli di parsing

| Rischio | Probabilità | Mitigazione |
|---|---|---|
| **2024 senza testo (image-scanned)** | confermato | OCR Tesseract o transcrizione manuale (vedi §2.2) |
| 2020 — tabelle bilingui con celle vuote interleaved | alta | usare estrazione tabelle "lattice" (line-aware) e drop colonne tutte-vuote |
| 2020 — header multi-linea (`miniem` su 1 riga, label su 2 righe) | alta | normalizzazione header pre-extract |
| 2020 — separatore numerico FR `€ 540,00` con spazio interno | media | regex `r'€\s*([\d\.]+)[,\.]?(\d*)'` |
| Tesseract OCR — confusione `0/O`, `1/l/I`, `B/8` | alta | post-process: tutti i valori dopo `€` devono matcheare `[\d.,]+`; se no, FAIL |
| 2024 vs 2020 — etichette cambiate tra edizioni | media | dictionary `code_normalizzato → (label_2020, label_2024)` con override |
| Tesseract NL+FR su pagina mista | media | usare `lang=nld+fra` per Tesseract |
| Inflazione/aggiornamenti tassi tra 2020 e 2024 ≠ uniformi | nota | non è un rischio di parsing; è una verifica oracolare a posteriori |

---

## 9. Prossimi step consigliati (ordine)

1. **iter F-belgium-extraction-ti-2020** — parser per le 4 famiglie
   di tabelle 2020 identificate al §3.3 (souffrances, esthétique,
   décès, véhicule). Output CSV in `legal_data/extracted/belgium/`,
   `ExtractionLog`, dataset in `historical`. Funziona anche senza
   OCR.
2. **iter F-belgium-ocr-ti-2024-spike** — POC con `pytesseract` su
   2-3 pagine campione del 2024 (souffrances + esthétique). Misurare
   accuracy reale rispetto al 2020 (oracolo strutturale). Decidere
   se procedere con OCR completo o switch a manuale.
3. **iter F-belgium-extraction-ti-2024** — in base al risultato del
   POC: OCR completo (con Studio review delle celle low-confidence)
   o transcrizione manuale Studio.
4. **iter F-belgium-legal-review** — Studio crea `LegalReview` per
   le 5 LegalSource BE (Tableau Indicatif 2024, 2020, Loi RC Auto
   1989, Schryvers landing × 2). Confermare valori spot.
5. **iter F-belgium-engine** — solo dopo `approved`: implementare
   `apps/calculators/engines/belgium.py` (registry, input schema,
   output schema, breakdown). Wizard BE in fase separata.

---

## 10. File creati e committabili

- `docs/legal_sources/BELGIUM_EXTRACTION_PLANNING.md` (questo file)
- `scripts/legal_data/analyze_fr_be_pdfs.py` (script read-only di
  ispezione, condiviso FR + BE)

**File NON committabili** (gitignored ai sensi del repo policy):
- i PDF in `legal_data/sources/belgium/downloaded/`
- il `download_manifest.json`

**File NON modificati**:
- nessun calcolatore (nessun `apps/calculators/engines/belgium.py`)
- nessun wizard
- nessun template
- nessun seeder Italia/TUN
- nessun `apps/compensation/models.py`
- nessun `.env`
- nessuna fonte BE è stata `approved` (rimangono **needs_review**)

---

## 11. Disclaimer

> Questo documento descrive una **proposta tecnica di estrazione**
> per i due PDF BE archiviati. Nessuna delle tabelle proposte
> costituisce ancora una "fonte legalmente validata" ai sensi della
> regola fondamentale di prodotto: ogni `CompensationTableRow`
> derivata dovrà attraversare il flusso `draft → extracted →
> needs_review → reviewed → approved` con `LegalReview` esplicito
> del Studio prima di poter alimentare un calcolo pubblico.
>
> Specificamente per il Tableau Indicatif 2024, la natura
> image-scanned del PDF richiederà uno **step OCR + review umana**
> aggiuntivo prima di qualsiasi `approved`.
