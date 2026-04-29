# TUN 2025 — Tabelle 2.A / 2.B / 2.C extraction report (DRAFT)

> ⚠️ **Estrazione automatica candidata — non è validazione legale.**
>
> - Nessun import nel DB.
> - Nessuna modifica a `LegalSource.status`, `CompensationDataset.status`,
>   `CalculationFormula.status`.
> - Nessuna nuova fonte / formula creata.
> - Le 9 191 righe Tabella 1 già `approved` non sono state toccate.
> - I CSV candidate generati hanno `legal_review_required=true` e
>   `no_human_legal_approval=true` in ogni riga.
>
> Questo report serve a valutare se l'estrazione è abbastanza pulita
> per giustificare il prossimo step (review assistita / human review +
> import in dataset DRAFT).

## 1. Pagine individuate

PDF source: `legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf`
SHA-256: `74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92`
(invariato — stesso file di F-extract-italy-tun.)

Layout verificato pagina-per-pagina con `_find_demoltiplicatori` +
`_find_inv_columns`:

| Tabella | Title page | Inv 10-40 | Sep | Inv 41-70 | Sep | Inv 71-100 | Tail blanks |
|---|---|---|---|---|---|---|---|
| 2.A min | 44 | 45-54 | 55 | 56-65 | 66 | 67-76 | 77 |
| 2.B mid | 77 | 78-87 | 88 | 89-98 | 99 | 100-109 | — |
| 2.C max | 110 | 111-120 | 121 | 122-131 | 132 | 133-142 | 143-152 |

Totale data pages per tabella: 30 (10 per ciascuna delle 3 fasce di
invalidità). Le pagine "sep" sono blanks senza testo rotato e non
contengono dati. La 2.C è seguita da 10 pagine vuote (back/copertina
G.U.) — coerente con la fine del Supplemento.

## 2. Struttura tabelle

Ogni cella `(età, invalidità)` contiene **tre valori sovrapposti**, non
uno solo come Tabella 1:

| Etichetta | Significato | Magnitudo |
|---|---|---|
| **A** | valore punto danno biologico | medio |
| **B** | incremento valore punto per danno morale | piccolo |
| **A+B** | totale danno biologico + morale | maggiore di A |

**Implicazione importante**: il campo `A` è **identico** alla cella
corrispondente in Tabella 1 (verificato sui 5 spot-check, vedi §5).
Tabella 1 è incorporata in Tabelle 2.A/2.B/2.C — non è un dataset
indipendente. La differenza tra le 3 tabelle è SOLO nel `B` (e quindi
in `A+B`):

- **2.A** → `B` con percentuale aumento "minimo" (es. 21,0% per inv 10)
- **2.B** → `B` con percentuale aumento "medio"
- **2.C** → `B` con percentuale aumento "massimo"

**Target import**: campo `A+B` (= `tun_biological_moral_{min,mid,max}_total_amount`),
quello che entra come `point_value` nel `CompensationTableRow`. I valori
`A` e `B` separati restano in `source_note` per audit ma non sono usati
dal calculator.

### Layout fisico (verificato su pag. 45)

Per ogni cella la pagina contiene 5-7 frammenti pdfplumber distribuiti
in 2 sub-cluster x:
- **left cluster** (x_center − 6pt..x_center): valore `A+B`
  spezzato su 2 righe (es. `'31'` + `'.610'`).
- **right cluster** (x_center..x_center + 6pt): valore `A` su 1 riga
  in alto (es. `'26.124'`) + valore `B` spezzato su 2 righe sotto
  (es. `'5'` + `'.486e'`).

Più i marker `'e'` (= `€`) sparsi, ignorabili in fase di parsing.

Sanity check inerente: `A + B == A+B` con tolleranza ±0,05 EUR per
arrotondamento centesimi.

### Tavola 1.B (page 8) re-verificata

L'estrattore precedente (Tabella 1) usava una mappa `demoltiplicatore →
età` ricostruita a mente. Per le moral tables ho riestratto Tavola 1.B
da pagina 8 del PDF: la granularità reale è **non-uniforme** (es. età
21 = 0,901 invece del lineare 0,9; età 80 = 0,612 invece di 0,6). La
mappa attuale in `extract_tun_moral_tables.py:_TAVOLA_1B` è la
trascrizione fedele della pagina 8.

## 3. File candidate creati

Tutti in `legal_data/sources/italy/tun_2025/` (esclusi da git per
`.gitignore` su `*.csv`):

| File | Righe | Status |
|---|---|---|
| `tun_2025_moral_min_extraction_candidate.csv` | 9 191 | candidate, draft |
| `tun_2025_moral_mid_extraction_candidate.csv` | 9 191 | candidate, draft |
| `tun_2025_moral_max_extraction_candidate.csv` | 8 891 | candidate, draft (300 mancanti) |

Schema CSV identico a `import_italy_tun_2025`:
`row_type, age_min, age_max, disability_min, disability_max, point_value,
coefficient, daily_amount, source_page, source_note`.

`row_type` per riga:
- 2.A → `tun_biological_moral_min_total_amount`
- 2.B → `tun_biological_moral_mid_total_amount`
- 2.C → `tun_biological_moral_max_total_amount`

`source_note` per ogni riga contiene:
```
extraction=automated_pdfplumber ;
legal_review_required=true ;
no_human_legal_approval=true ;
a_value=<biological> ;
b_value=<moral_increment> ;
ab_value=<total> ;
flags=<ok|ab_check_fail|missing_value|...> ;
pdf_page_index=<N>
```

## 4. Numero righe candidate

| Tabella | Atteso (91×101) | Estratto | Delta |
|---|---|---|---|
| 2.A min | 9 191 | **9 191** | 0 |
| 2.B mid | 9 191 | **9 191** | 0 |
| 2.C max | 9 191 | 8 891 | **−300** |

Le 300 righe mancanti di 2.C corrispondono all'ultimo gruppo di età
(91-100) della pagina 142 (G.U. 137), ultima pagina dati di 2.C inv
71-100. La pagina ha 14 demoltiplicatori detected vs. 10 attesi e solo
29 colonne inv (vs 30) — il layout fisico devia dal pattern delle altre
pagine. Da indagare sotto.

## 5. QA — anomalie

### 5.1. Status counts

| Tabella | consistent | inconsistent (ab_check_fail) | empty | missing_value |
|---|---|---|---|---|
| 2.A min | 7 516 (81,8%) | 1 515 | 160 | — |
| 2.B mid | 7 586 (82,5%) | 1 441 | 164 | — |
| 2.C max | 7 425 (80,8%) | 1 326 | 140 | — |

`consistent` = A + B == A+B entro ±0,05 EUR.
`inconsistent` = i tre valori sono stati estratti ma la check
sommatoria fallisce (probabile cattivo cluster di frammenti).
`empty` = almeno un valore tra A, B, A+B non estratto.

### 5.2. Spot-check `A` vs Tabella 1 (verifica struttura)

Le celle `(età, invalidità)` per cui Tabella 1 ha valori certi:

| (età, inv) | Tabella 1 | 2.A min `A` | 2.B mid `A` | 2.C max `A` |
|---|---|---|---|---|
| (0, 10) | 26 124 | 26 124 ✓ | 26 124 ✓ | 26 124 ✓ |
| (1, 10) | 26 124 | 26 124 ✓ | 26 124 ✓ | 26 124 ✓ |
| (2, 10) | 25 993 | 25 993 ✓ | 25 993 ✓ | 25 993 ✓ |
| (50, 50) | 267 618 | 267 618 ✓ | 267 618 ✓ | 267 618 ✓ |
| (100, 100) | 541 329 | 541 329 ✓ | 541 329 ✓ | **MISSING** (in 2.C) |

**Conferma forte**: l'estrattore legge correttamente la colonna `A`
(quella che è già in DB approved). Il MISSING su (100,100) di 2.C è
parte delle 300 righe non estratte (vedi §6).

### 5.3. Duplicati / negativi / null

| Tabella | Duplicati `(age,inv)` | Negativi | Null |
|---|---|---|---|
| 2.A | 0 | 0 | 160 |
| 2.B | 0 | 0 | 164 |
| 2.C | 0 | 0 | 140 |

### 5.4. Monotonicità

| Tabella | Violazioni vs invalidità (età fissa) | Violazioni vs età (invalidità fissa) |
|---|---|---|
| 2.A | 326 / ~9 100 (3,6%) | 35 / ~9 100 (0,4%) |
| 2.B | 299 / ~9 030 (3,3%) | 42 / ~9 030 (0,5%) |
| 2.C | 290 / ~8 750 (3,3%) | 42 / ~8 750 (0,5%) |

Tutte le violazioni si concentrano sulle righe `inconsistent`. Le righe
`consistent` (~80%) sono internamente monotone — segno che il valore
estratto è genuinamente quello del PDF, non un artefatto.

### 5.5. Pagine problematiche

Tre pagine in posizione strutturalmente analoga in ognuna delle 3
tabelle accumulano l'82,4% di issues:

| Tabella | Pagina G.U. | PDF page | Issues / Totale | % |
|---|---|---|---|---|
| 2.A min | 63 | 67 | 272 / 330 | 82,4% |
| 2.B mid | 95 | 100 | 272 / 330 | 82,4% |
| 2.C max | 128 | 133 | 272 / 330 | 82,4% |

Tutte e tre sono la **prima pagina della fascia inv 71-100** della
rispettiva tabella, quella con valori massimi (>1 000 000 EUR per le
celle giovani × invalidità grave). È lo stesso problema già visto in
F-extract-italy-tun: il parser dei numeri >1M deve gestire DUE punti
separatori migliaia (`1.007.514` ha tre componenti, non due). Il
parser corrente lo gestisce ma il clustering di frammenti su quella
pagina è più fragile per la maggiore lunghezza dei numeri.

Pagine con tasso 50-56% issues: G.U. 41/52, 84/85, 117/118 — sono le
prime pagine di ciascuna fascia inv (10-40, 41-70). Stessa famiglia di
problema.

Le altre ~24 pagine per tabella hanno tasso issues 0-20%, in linea con
quello visto in Tabella 1 prima della review assistita di pag. 34.

## 6. Raccomandazione import

**NO — non importare automaticamente in stato approved né in dataset
APPROVED.**

Motivi:
- 80% di celle `consistent` non basta. Sotto Tabella 1 (post-review
  assistita) eravamo a 100% `human_approved` per le 9 191 righe; il
  bar per le moral tables deve essere lo stesso.
- 1 300-1 500 celle per tabella restano `ab_check_fail`. Vanno
  riprocessate con un parser più robusto (clustering migliore o
  approccio assistito sulle pagine "calde" come F-page-34-assisted-review
  ha fatto per Tabella 1).
- 140-160 celle empty per tabella, prevedibilmente concentrate in 3
  pagine — risolvibili con review assistita pagine-by-pagina.
- 300 celle mancanti in 2.C — bisogna capire la deviazione del layout
  di pag. 142.

**SÌ — l'estrazione è abbastanza buona per giustificare i prossimi
passi**: i 7 500 cells `consistent` per tabella sono praticamente
certi (`A + B == A+B`, `A` coincide con Tabella 1 sui 5 spot, range di
valori plausibile, monotonicità rispettata).

### Cosa farei prima di un import in DRAFT (proposta sequenziale)

1. **Iterare il parser**: handling più robusto per frammenti di numeri
   >1M e per il clustering Y dei sub-bands. Target: portare
   `consistent` da 80% a >95%.
2. **Review assistita** sulle ~6 pagine calde (G.U. 63/95/128 + le
   prime di fascia) come fatto per Tabella 1 pag. 34 — file
   `tun_2025_moral_review_tasks.csv` analogo.
3. **Recovery** delle 300 celle mancanti di 2.C (un singolo passaggio
   dedicato sulla pag. 142).
4. **Human legal review** sui flag `human_approved` (anche solo
   sample-based al 5-8% per le righe `consistent`).
5. SOLO ALLORA: **import nel dataset esistente** (vincolo a §7).

## 7. Vincolo critico per l'import — `import_italy_tun_2025` distrugge le
   Tabella 1 rows

**`import_italy_tun_2025._import_csv_rows`** (riga 367) esegue
`dataset.rows.all().delete()` prima di inserire le nuove righe.

Implicazione: importare i CSV moral nello **stesso** `CompensationDataset`
TUN-2025 (preferenza utente) cancellerebbe le 9 191 righe Tabella 1
`approved`. Inaccettabile.

Inoltre il command rifiuta di operare su dataset non `DRAFT`. Il
dataset TUN-2025 è `APPROVED` → il command si rifiuta a priori, anche
se non ci fosse il `delete()`.

### Opzioni per attivare l'import senza perdere Tabella 1

A. **Modificare `_import_csv_rows`** per essere additivo: filtrare
   il delete per `row_type` letti dal CSV (es. cancella solo righe
   con `row_type IN (csv_row_types)`). Cambia di pochissimo la
   semantica di idempotenza per Tabella 1 (riavvio = stesso CSV →
   stesse righe). Richiede: aggiunta di un flag esplicito
   `--additive` o dispatch automatico.

B. **Nuovo command** `import_italy_tun_2025_moral` che:
   - accetta dataset in stato `APPROVED` (senza promuovere/declassare);
   - aggiunge righe con `row_type = tun_biological_moral_*_total_amount`
     senza toccare le altre;
   - lascia status di dataset/formula intoccato.
   Più sicuro, zero rischio per Tabella 1.

C. **Dataset separato** per le moral tables. Significa migrazione
   concettuale (3 dataset per stessa fonte) e wiring engine cross-
   dataset. Sconsigliato dall'utente; lo riporto solo per completezza.

**Raccomandazione**: **B** (nuovo command), con codice riusato dal
command esistente per attach PDF / log audit. Modifica zero al command
attuale — nessun rischio di regressione per Tabella 1.

## 8. Cosa serve per attivare il range pubblico min/mid/max

Quando le moral rows saranno `approved` nel DB:

1. **Engine** — nuova rule `row_amount_range_direct` in
   `apps/compensation/services.py`:
   ```python
   # Pseudo-spec
   amount_min = row_with_row_type("tun_biological_moral_min_total_amount").point_value
   amount_mid = row_with_row_type("tun_biological_moral_mid_total_amount").point_value
   amount_max = row_with_row_type("tun_biological_moral_max_total_amount").point_value
   # Tutti × (100 - fault_percentage) / 100 se fault_reduction=True
   ```
   Test fixture-only (no valori reali TUN), ad esempio:
   - `test_row_amount_range_direct_uses_three_row_types`
   - `test_row_amount_range_direct_applies_fault_reduction`
   - `test_row_amount_range_direct_falls_back_to_base_when_moral_missing`
     (per non far sparire la stima quando solo le moral mancano —
     comportamento da concordare con lo Studio).

2. **Formula `parameters`** aggiornati su staging via admin Django:
   ```json
   {
     "engine": "italy_tun_point_value_v1",
     "requires": ["victim_age", "permanent_disability_percentage"],
     "row_match": ["victim_age", "permanent_disability_percentage"],
     "amount_rule": "row_amount_range_direct",
     "moral_min_row_type": "tun_biological_moral_min_total_amount",
     "moral_mid_row_type": "tun_biological_moral_mid_total_amount",
     "moral_max_row_type": "tun_biological_moral_max_total_amount",
     "fault_reduction": true
   }
   ```
   La modifica di `parameters` è atto di configurazione, non di
   approvazione → non richiede nuovo `LegalReview`. Ma DEVE essere
   fatta DOPO l'import + approval delle moral rows, mai prima.

3. **Nessuna modifica** al wizard / al PDF / ai template:
   `estimated_min/mid/max` sono già emessi dal calculator e
   già renderizzati. Cambiare la rule cambia solo i numeri, non il
   contratto di output.

4. **Smoke test ampliato**: il test `(35, 10, 0)` oggi ritorna
   `21709 / 21709 / 21709`. Dopo il switch alla nuova rule deve
   ritornare tre valori distinti, MIN < MID < MAX. Aggiungere
   un assert su questo (con valori reali TUN, presi dal CSV
   approvato dallo Studio).

## 9. File creati / modificati in F-italy-tabelle-morali

| File | Tipo | Stato |
|---|---|---|
| `scripts/legal_data/extract_tun_moral_tables.py` | nuovo | committable |
| `scripts/legal_data/qa_tun_moral_tables.py` | nuovo | committable |
| `legal_data/sources/italy/tun_2025/moral_tables_extraction_report.md` | nuovo | committable |
| `legal_data/sources/italy/tun_2025/tun_2025_moral_*_extraction_candidate.csv` | × 3 | NON committable (gitignore) |

Niente modifiche a:
- `apps/compensation/models.py` — nessuna migrazione necessaria
  (`row_type` è già libero, multipli row_types per stesso dataset
  non hanno vincoli).
- `apps/compensation/management/commands/import_italy_tun_2025.py` —
  intatto. La modifica per supportare moral tables sarà un command
  separato (vedi §7B).
- `apps/calculators/engines/italy.py` — intatto. La nuova rule
  `row_amount_range_direct` arriverà solo quando le moral rows
  saranno `approved` (vedi §8).
- `formula.parameters` runtime — intatto.
- `LegalSource.status`, `CompensationDataset.status`,
  `CalculationFormula.status` — intatti.

## 10. Cosa NON è stato fatto (esplicito)

- ❌ Nessun import nel DB.
- ❌ Nessuna `CompensationTableRow` con `row_type =
  tun_biological_moral_*` esiste in DB.
- ❌ `LegalSource.status` non cambia.
- ❌ `CompensationDataset.status` non cambia (resta `approved` per
  Tabella 1).
- ❌ `CalculationFormula.status` non cambia.
- ❌ Nessuna `LegalReview` registrata.
- ❌ Nessuna modifica al PDF originale.
- ❌ Nessuna chiamata di rete / fonti esterne (estrazione 100%
  off-line dal PDF locale).
- ❌ `pdfplumber` resta solo locale (non in `requirements.txt`).
- ❌ Nessun nuovo paese / case_type / engine.

## 11. Test/lint suite — verde

- `python manage.py check` → System check identified no issues (0 silenced).
- `pytest -q` → 216 passed in 10.67s.
- `ruff check .` → All checks passed!
- `black --check .` → 132 files would be left unchanged.
