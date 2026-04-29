# Page 34 — Assisted review report

> ⚠️ **Assistant review is not legal approval.** Lo Studio deve eseguire
> verifica finale cella-per-cella prima di promuovere fonte / dataset /
> formula a `approved`. Questo report è un artefatto di lavoro per
> velocizzare la review umana, non una sua sostituzione.

## Scope

- File rivisto: `legal_data/sources/italy/tun_2025/tun_2025_review_tasks.csv`
- Pagina PDF analizzata: pagina **34** del D.P.R. 13 gennaio 2025 n. 12
  (prima pagina del range invalidità 71-100, età 0-10).
- Hash PDF: `74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92`.

## Conteggio righe esaminate

| Categoria | Conteggio |
|---|---|
| Totale righe review su pagina 34 | 270 |
| `assistant_verified` | **252** |
| `assistant_corrected` | **18** |
| `needs_human_review` | **0** |
| Restano `pending` | 0 |

## Causa unica delle 18 nulle

Le 18 celle null erano **tutti importi superiori a €1 000 000** (es.
`1.007.514`). Il parser dell'estrattore F-tun-csv-extraction-assistant
gestiva un solo punto come separatore migliaia (es. `26.124` → 26 124),
ma non i valori a milione che hanno **due punti** (`1.000.000+`). Il
PDF contiene tutti i valori; pdfplumber li ha letti correttamente; solo
il parser locale li scartava silenziosamente.

In questa review assistita ho usato un parser potenziato che accetta più
punti come separatori migliaia (`split(".") + join`) e ho rimappato le
18 celle alla loro posizione `(età, invalidità)` via:
- ancore Y = demoltiplicatori `Tavola 1.B`;
- ancore X = posizioni colonne dei valori `< 1M` su righe complete (età 9, 10).

Il numero totale di celle rimappate per pagina 34 è 330 = 11 età (0-10)
× 30 invalidità (71-100) — copertura completa.

## 18 celle completate (`assistant_corrected`)

Distribuzione triangolare (i valori più alti — milioni — si trovano
nell'angolo "giovane × invalidità grave"):

| età | inv 98 | inv 99 | inv 100 |
|---:|---:|---:|---:|
| 0 | 1 007 514 | 1 022 271 | 1 037 028 |
| 1 | 1 007 514 | 1 022 271 | 1 037 028 |
| 2 | 1 002 477 | 1 017 160 | 1 031 843 |
| 3 | (già OK) | 1 012 048 | 1 026 658 |
| 4 | (già OK) | 1 006 937 | 1 021 473 |
| 5 | (già OK) | 1 001 826 | 1 016 287 |
| 6 | (già OK) | (già OK) | 1 011 102 |
| 7 | (già OK) | (già OK) | 1 005 917 |
| 8 | (già OK) | (già OK) | 1 000 732 |
| 9 | (già OK) | (già OK) | (già OK) |
| 10 | (già OK) | (già OK) | (già OK) |

Età 0 ed età 1 condividono il demoltiplicatore 1.0 → stesso valore
(coerente con Tavola 1.B). I valori decrescono al crescere dell'età
(coerenza con il coefficiente di riduzione) e crescono al crescere
dell'invalidità (coerenza con CM punto biologico).

## 252 righe `assistant_verified`

Tutte le 252 celle che il candidate aveva con `point_value` valorizzato
sono state confrontate con il valore letto dal PDF e **coincidono al
centesimo**. Il flag `cells_extracted_mismatch` era applicato all'intera
riga (tutte e 30 le invalidità) ogni volta che un'età aveva meno di 30
celle estratte. Il flag NON significa che le celle effettivamente
estratte fossero sbagliate — significa solo che alcune celle (quelle
sopra il milione) erano mancanti. Verificate 252/252.

## Anomalie da verificare umanamente

**Nessuna.** Tutte le 270 righe di review sono ora in stato deciso
(`assistant_verified` o `assistant_corrected`).

## Cosa NON è stato fatto

- ❌ `tun_2025_rows_extraction_candidate.csv` non modificato.
- ❌ `tun_2025_rows.csv` non modificato (resta template vuoto).
- ❌ Nessun import nel DB.
- ❌ `LegalSource.status`, `CompensationDataset.status`,
  `CalculationFormula.status` non promossi: restano rispettivamente
  `needs_review`, `draft`, `draft`.
- ❌ Nessun commit automatico (review CSV è in `legal_data/sources/**`,
  coperto da `.gitignore`).

## Workflow consigliato per la legal review finale

1. Aprire `tun_2025_review_tasks.csv` con un editor CSV.
2. Per le 18 righe `assistant_corrected` (priority `high`):
   - aprire il PDF a pagina 34;
   - localizzare visivamente la cella `(età, invalidità)`;
   - confrontare con `reviewer_corrected_value`;
   - se coincide, cambiare `reviewer_status` da `assistant_corrected` a
     `human_approved`;
   - aggiornare `reviewer_notes`.
3. Per le 252 righe `assistant_verified`:
   - sample-check su ~10-20 celle a campione (5%-8%);
   - se tutte coincidono con il PDF → considerare "human-checked
     batch", marcare `reviewer_status=human_sample_approved`;
   - alternativa: full-review.
4. Una volta tutte le righe in stato `human_approved`:
   - copiare nel CSV produzione `tun_2025_rows.csv`;
   - lanciare `python manage.py import_italy_tun_2025 --csv tun_2025_rows.csv`;
   - aggiornare `CalculationFormula.parameters` con lo schema runtime
     (`engine`, `requires`, `row_match`, `amount_rule="row_amount_direct"`,
     `fault_reduction`);
   - creare `LegalReview(decision=approve)` per la fonte;
   - promuovere status a `approved` nei tre livelli.

## Suggerimento tecnico per estensione futura

Quando lo Studio estrarrà le altre tabelle (2.A, 2.B, 2.C — danno
biologico + morale), conviene aggiornare il parser di
`_extract_tun_full.py` per gestire fin da subito i numeri >€1M. Il fix
è una riga: `Decimal("".join(parts))` invece di `Decimal(t.replace(".", ""))`
che falliva quando il replace non era applicato (ramo decimal).
La nuova logica `parse_amount_v2` di questo report è la versione
corretta.

## Nota legale

L'assistente automatico **non sostituisce** la responsabilità professionale
dello Studio sulla coerenza dei valori importati. Ogni cella deve essere
verificata da un occhio umano competente prima dell'approvazione finale.
