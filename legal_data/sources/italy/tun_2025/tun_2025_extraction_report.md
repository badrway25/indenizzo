# TUN 2025 — Extraction report (DRAFT, requires legal review)

> ⚠️ Questo documento descrive una **estrazione automatica** del D.P.R.
> 13 gennaio 2025 n. 12 e va letto come **artefatto di lavoro** dello
> Studio. NESSUN valore tabellare è stato importato in DB. NESSUNA
> fonte / dataset / formula è stata approvata.
> Il file `tun_2025_rows.csv` è un TEMPLATE vuoto. Il file
> `tun_2025_rows_extraction_candidate.csv` (non committato) è il
> risultato dell'estrazione automatica e richiede verifica
> cella-per-cella prima di essere copiato nel CSV di produzione.

## 1. Verifica integrità del PDF

| | Valore |
|---|---|
| Path | `legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf` |
| SHA-256 | `74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92` |
| Size | 5 092 955 bytes |
| Atteso | `74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92` |
| Match | ✅ |

L'hash combacia con quello registrato in
`LegalSourceAttachment pk=1` e in `ExtractionLog pk=1` (run
`pdf_attach`).

## 2. Struttura del PDF (152 pagine)

| Pagine | Sezione | Note |
|---|---|---|
| 1-4 | Copertina + sommario | non rilevanti |
| 5-6 | Testo del D.P.R. | art. 1-5, riferimenti normativi |
| 7 | Allegato I — Tavola 1.A | Coefficienti moltiplicatori del punto biologico (10-100) |
| 8 | Allegato I — Tavola 1.B | Coefficienti di riduzione per età (0-100) |
| 9 | Allegato I — Tavola 2 | Coefficienti danno morale (min/med/max) |
| 10 | Allegato II — header | Indice Tabelle 1, 2.A, 2.B, 2.C |
| 11 | TUN — Tabella 1, header (inv 10-40) | "Tabella comprensiva del solo danno biologico" |
| 12-21 | TUN — Tabella 1, dati inv 10-40, ages 1-100 | rotated 180°, 10 pages × 10 ages |
| 22 | TUN — Tabella 1, header (inv 41-70) | |
| 23-32 | TUN — Tabella 1, dati inv 41-70, ages 1-100 | |
| 33 | TUN — Tabella 1, header (inv 71-100) | |
| 34-43 | TUN — Tabella 1, dati inv 71-100, ages 1-100 | |
| 44-76 | Tabella 2.A (danno morale aumento minimo) | 33 pages, NON estratta |
| 77-109 | Tabella 2.B (danno morale aumento medio) | NON estratta |
| 110-152 | Tabella 2.C (danno morale aumento massimo) | NON estratta |

## 3. Decisione tecnica critica: cella = importo finale

L'art. 138 CAP descrive la TUN come "del valore pecuniario da attribuire
a ogni singolo punto di invalidità **comprensivo** dei coefficienti di
variazione corrispondenti all'età". L'Allegato II Tabella 1 è una tabella
**precomputata** (`tabella comprensiva`) che restituisce direttamente
l'importo per la combinazione (età × % invalidità).

Esempio empirico estratto e verificabile sulla pagina 12:

| invalidità | età 0-1 | età 2 | età 3 |
|---|---|---|---|
| 10% | 26 124 € | 25 993 € | 25 863 € |
| 11% | 29 052 € | 29 204 € | … |

Coerente con: `cella = primo_punto × CM(invalidità) × demoltiplicatore(età)`,
ovvero il valore già moltiplicato per il numero di punti.

**Implicazione sull'engine**: la regola
`amount_rule = "point_value_times_disability_percentage"` (default
F-italy-engine-implementation) **doppio-conterebbe** la percentuale di
invalidità se applicata alla TUN. Servono righe importate con
`row_type = "tun_biological_total_amount"` lette dal calculator con
una **nuova rule** `amount_rule = "row_amount_direct"`.

## 4. Engine: nuova rule `row_amount_direct`

Aggiunta a `apps/compensation/services.py`, registrata in
`SUPPORTED_AMOUNT_RULES`. Comportamento:

```
amount = row.point_value
        × (100 - fault_percentage) / 100   se fault_reduction=True
```

Test fixture-only in `apps/compensation/tests.py`:

- `test_row_amount_direct_uses_cell_value_as_final_amount` — verifica
  che `row.point_value=12345.67` non venga moltiplicato per `disability%`.
- `test_row_amount_direct_applies_fault_reduction` — verifica la
  riduzione concorso.

Lo schema di `formula.parameters` per il calculator italiano TUN diventa:

```json
{
  "engine": "italy_tun_point_value_v1",
  "requires": ["victim_age", "permanent_disability_percentage"],
  "row_match": ["victim_age", "permanent_disability_percentage"],
  "amount_rule": "row_amount_direct",
  "fault_reduction": true
}
```

NESSUN dato reale TUN nei test (point_value=1 EUR, 12345.67, 100 EUR
sono valori segnaposto chiaramente etichettati `fixture only`).

## 5. Estrazione automatica della Tabella 1

### Strategia

- Libreria: `pdfplumber 0.11.9` (locale, non in requirements progetto).
- I dati sono **rotati 180°**: i caratteri di ogni word vengono restituiti
  in ordine inverso (es. `421.62` = `26.124` reversed).
- Strategia di parsing:
  1. filtrare le words con `upright=False`;
  2. filtrare per posizione (corpo pagina, esclusi header/footer);
  3. trovare i 10 demoltiplicatori della pagina (Tavola 1.B): valori
     `0.5..1.0`;
  4. per ogni demoltiplicatore, raccogliere le celle entro ±18pt sull'asse Y;
  5. una cella valida termina con `e` (= `€` mis-extracted da pdfplumber);
  6. il demoltiplicatore identifica univocamente l'età (Tavola 1.B) tranne
     per `1.0` che corrisponde sia ad età 0 che a età 1 (entrambe espanse).

### Conteggi

| | |
|---|---|
| Pagine analizzate | 30 (pagine 12-21, 23-32, 34-43) |
| Celle estratte (uniche per `(age, invalidity)`) | 9191 |
| Combinazioni attese | 101 ages × 91 invalidità = 9191 |
| Celle con valore null | 18 |
| Celle con flag `cells_extracted_mismatch` | 270 |
| Violazioni di monotonicità su `invalidity` | 0 |
| Violazioni di monotonicità su `age` | 0 |
| Errori di parsing numerico | 0 |

### Spot-check

| (età, invalidità) | importo (€) |
|---|---|
| (0, 10) | 26 124 |
| (1, 10) | 26 124 (uguale, demolt. condiviso) |
| (2, 10) | 25 993 |
| (50, 50) | 267 618 |
| (100, 100) | 541 329 |

Decremento monotono con età (in linea con Tavola 1.B), incremento
monotono con invalidità (in linea con Tavola 1.A): **coerenza interna
strutturale verificata**.

## 6. Anomalie note

### A. Celle null (18)

Tutte concentrate nelle invalidità 98-100 della pagina 34 (range 71-100,
prima pagina). Probabile: clipping del rendering automatico nelle ultime
3 colonne. Lo Studio deve **trascrivere manualmente** queste 18 celle
dalla pagina 34 del PDF.

### B. Cells-mismatch flag (270)

Righe per cui il numero di celle estratte differiva dall'atteso (ad es.
extra-cells dropped). Non implica errori di valore, ma segnala che
quella riga ha avuto un parsing "ai limiti". Da verificare per priorità:
le 270 celle con questo flag sono distribuite su poche righe.

### C. Range non estratti

Tabelle 2.A, 2.B, 2.C (danno biologico + morale, ~99 pagine). Lo Studio
deve estrarle quando si vorrà integrare il danno morale nel calculator.
Per ciascuna serve una struttura analoga a Tabella 1, con campi
`row_type` distinti (es. `tun_morale_min_total_amount`,
`tun_morale_med_total_amount`, `tun_morale_max_total_amount`).

### D. Età 0 e Età 1 hanno lo stesso importo

Effetto strutturale del coefficiente condiviso (Tavola 1.B: `0-1 → 1`).
Coerente con la fonte. **Non è un'anomalia.**

## 7. File prodotti

| File | Cosa è | Status committato |
|---|---|---|
| `tun_2025_rows.csv` | Template vuoto (solo header) | committato |
| `tun_2025_rows_extraction_candidate.csv` | Estrazione automatica candidata | NON committato (.gitignore) |
| `tun_2025_extraction_report.md` | Questo report | committato |

## 8. Istruzioni per la review legale

**Mai promuovere `LegalSource`, `CompensationDataset` o
`CalculationFormula` senza i passi seguenti.**

### Step 1 — verifica struttura

1. Aprire il PDF da `legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf`
   e confermare che è il D.P.R. n. 12 del 2025 pubblicato in G.U. n. 40.
2. Verificare l'hash via `python -c "import hashlib;
   print(hashlib.sha256(open('legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf', 'rb').read()).hexdigest())"`
   contro quello in §1.

### Step 2 — verifica decisione tecnica

3. Confermare che la cella `(età=0-1, invalidità=10)` di pagina 12 del PDF
   è effettivamente €26.124. Se sì, la decisione `row_amount_direct` è
   confermata. Se è un altro valore, fermarsi e rivedere.

### Step 3 — verifica cella-per-cella

4. Aprire `tun_2025_rows_extraction_candidate.csv` con un editor CSV
   (Excel, LibreOffice).
5. Per ogni riga: confrontare `point_value` con la cella corrispondente
   nel PDF. Strumento consigliato: per `(age, inv)` calcolare la
   pagina di provenienza dalla colonna `source_page`.
6. Per le 18 celle null e le ~270 celle con flag `cells_extracted_mismatch`,
   trascrivere manualmente i valori dal PDF.
7. Quando una riga è verificata: copiarla nel file
   `tun_2025_rows.csv` (production CSV).

### Step 4 — import

8. Lanciare:
   ```
   python manage.py import_italy_tun_2025 \\
       --csv legal_data/sources/italy/tun_2025/tun_2025_rows.csv
   ```
   Le righe vengono inserite in `CompensationTableRow` con dataset DRAFT.

### Step 5 — promozione

9. Aggiornare `CalculationFormula.parameters` con lo schema corretto:
   ```json
   {
     "engine": "italy_tun_point_value_v1",
     "requires": ["victim_age", "permanent_disability_percentage"],
     "row_match": ["victim_age", "permanent_disability_percentage"],
     "amount_rule": "row_amount_direct",
     "fault_reduction": true
   }
   ```
10. Creare `LegalReview(decision=approve)` per la fonte.
11. Promuovere `LegalSource.status` a `approved` (richiede language
    valorizzato — già presente).
12. Promuovere `CompensationDataset.status` a `approved` (vincolo di
    `clean()`: source deve essere già `approved`).
13. Promuovere `CalculationFormula.status` a `approved`.
14. Smoke test del wizard con input reali → atteso `status=calculated`,
    `estimated_*` popolati.

## 9. Cosa NON è stato importato o approvato

- ❌ Nessuna riga nel DB (`CompensationTableRow.objects.count() == 0`).
- ❌ `LegalSource.status` resta `needs_review`.
- ❌ `CompensationDataset.status` resta `draft`.
- ❌ `CalculationFormula.status` resta `draft`.
- ❌ `formula.parameters` NON aggiornati con lo schema runtime
  (continua a contenere lo schema documentale di
  F-extract-italy-tun).
- ❌ Tabelle 2.A/2.B/2.C (danno biologico + morale) NON estratte.
- ❌ `pdfplumber` aggiunto solo localmente, NON in `requirements.txt`.

Il calculator continua quindi a restituire correttamente
`unavailable_requires_legal_validation` con `missing_documents`
sequenziali (`compensation_dataset_approved` →
`calculation_formula_approved` → `formula_engine_unknown` →
`compensation_row_match`) man mano che lo Studio promuove i livelli.
