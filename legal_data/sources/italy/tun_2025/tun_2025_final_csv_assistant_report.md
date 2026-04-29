# `tun_2025_rows.csv` — Assistant-assisted technical CSV report

> ⚠️ **Questo CSV NON è una validazione legale.** È stato prodotto da
> un assistente AI a partire da una pipeline di estrazione automatica
> + review tecnica assistita. Tutte le righe portano nei
> `source_note` i flag `legal_review_required=true` e
> `no_human_legal_approval=true`.
>
> **Restano vincoli espliciti:**
> - `LegalSource.status` deve restare `needs_review`;
> - `CompensationDataset.status` deve restare `draft`;
> - `CalculationFormula.status` deve restare `draft`;
> - il CSV può essere importato **solo nel contesto di un dataset
>   DRAFT** per la successiva legal review.

## Provenienza

| | Valore |
|---|---|
| PDF di origine | `legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf` |
| SHA-256 PDF | `74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92` |
| Estrazione automatica | F-tun-csv-extraction-assistant (pdfplumber 0.11.9) |
| Review assistita | F-page-34-assisted-review |

## File risultante

| | Valore |
|---|---|
| Path | `legal_data/sources/italy/tun_2025/tun_2025_rows.csv` |
| Righe dati | **9 191** (101 età × 91 invalidità) |
| Header | conforme a schema `import_italy_tun_2025` |
| Tipo righe | tutte `tun_biological_total_amount` |
| Stato git | NON committato (escluso da `.gitignore`) |

## Provenienza per riga

| Origine | Conteggio | Flag in `source_note` |
|---|---|---|
| Estrazione candidate clean (29 pagine) | 8 921 | `automated_extraction=true ; legal_review_required=true ; no_human_legal_approval=true` |
| Pagina 34, `assistant_verified` (Claude) | 252 | `assistant_review_applied=true ; assistant_review_status=assistant_verified ; legal_review_required=true ; no_human_legal_approval=true` |
| Pagina 34, `assistant_corrected` (Claude) | **18** | `assistant_review_applied=true ; assistant_review_status=assistant_corrected ; reviewer_corrected_value=<X> ; legal_review_required=true ; no_human_legal_approval=true` |

Nessuna riga è marcata `human_approved` o `legal_approved`.

## 18 valori corretti da Claude (assistant_corrected)

Tutti corrispondono a celle del PDF dove l'importo supera €1 000 000.
Causa originaria: il parser dell'estrattore automatico respingeva i
numeri italiani con due punti separatori migliaia (es. `1.007.514`).
La review assistita ha riletto le 18 celle dal PDF con un parser
potenziato e propagato i valori.

| età | inv 98 | inv 99 | inv 100 |
|---:|---:|---:|---:|
| 0 | 1 007 514 | 1 022 271 | 1 037 028 |
| 1 | 1 007 514 | 1 022 271 | 1 037 028 |
| 2 | 1 002 477 | 1 017 160 | 1 031 843 |
| 3 | (originale OK) | 1 012 048 | 1 026 658 |
| 4 | (originale OK) | 1 006 937 | 1 021 473 |
| 5 | (originale OK) | 1 001 826 | 1 016 287 |
| 6 | (originale OK) | (originale OK) | 1 011 102 |
| 7 | (originale OK) | (originale OK) | 1 005 917 |
| 8 | (originale OK) | (originale OK) | 1 000 732 |

I valori sono coerenti con la struttura della Tavola 1.B (decremento
con età) e Tavola 1.A (incremento con invalidità). Verifica:
- inv 100, età 0 = 1 037 028 → età 1 = 1 037 028 (demolt condiviso 1.0)
  → età 2 = 1 031 843 → … → età 8 = 1 000 732 (decremento monotono ✓)
- età 0, inv 98 = 1 007 514 < inv 99 = 1 022 271 < inv 100 = 1 037 028
  (incremento monotono ✓)

## 252 valori verificati da Claude (assistant_verified)

Tutte le 252 righe della pagina 34 il cui `point_value` era già
valorizzato nel candidate sono state confrontate con il valore letto
dal PDF: corrispondono esattamente. Non è stata applicata alcuna
modifica al valore numerico.

## QA finale superato

| Controllo | Esito |
|---|---|
| Header conforme | ✅ |
| Righe dati totali = 9 191 | ✅ |
| Duplicati per `(row_type, age, disability)` | 0 ✅ |
| `point_value` vuoti | 0 ✅ |
| `point_value` negativi | 0 ✅ |
| `source_page` vuoti | 0 ✅ |
| `source_note` vuoti | 0 ✅ |
| Violazioni monotonicità invalidità (età fissa) | 0 ✅ |
| Violazioni monotonicità età (invalidità fissa) | 0 ✅ |
| Verifica 18 celle corrette | 18/18 ✅ |

## Cosa NON è stato fatto

- ❌ Nessuna verifica legale umana cella-per-cella.
- ❌ Nessun import nel DB (`CompensationTableRow.objects.count()` resta 0).
- ❌ `LegalSource.status` non cambia (resta `needs_review`).
- ❌ `CompensationDataset.status` non cambia (resta `draft`).
- ❌ `CalculationFormula.status` non cambia (resta `draft`).
- ❌ `formula.parameters` non aggiornati con lo schema runtime
  (`engine`, `requires`, `row_match`, `amount_rule="row_amount_direct"`,
  `fault_reduction`).
- ❌ Nessuna `LegalReview` registrata.
- ❌ Nessun commit automatico (CSV escluso da `.gitignore`).

## Workflow consigliato dopo questo report

1. **Import DRAFT (consentito)**:
   ```
   python manage.py import_italy_tun_2025 \
       --csv legal_data/sources/italy/tun_2025/tun_2025_rows.csv
   ```
   Il command rifiuta automaticamente di importare se il dataset non è
   in stato `DRAFT` (vincolo già implementato in F-extract-italy-tun).
   Le righe vengono inserite, i flag `legal_review_required=true` nei
   `source_note` restano per audit.

2. **Aggiornamento `formula.parameters`** in admin con lo schema
   runtime (atto di configurazione, non di approvazione):
   ```json
   {
     "engine": "italy_tun_point_value_v1",
     "requires": ["victim_age", "permanent_disability_percentage"],
     "row_match": ["victim_age", "permanent_disability_percentage"],
     "amount_rule": "row_amount_direct",
     "fault_reduction": true
   }
   ```

3. **Legal review umana** (richiesta esplicita, non eseguibile da
   assistente):
   - revisione cella-per-cella o sample-based;
   - aggiornamento `reviewer_status` nelle 270 righe di
     `tun_2025_review_tasks.csv` da `assistant_*` a `human_*`;
   - registrazione di `LegalReview(decision=approve)` per la fonte;
   - solo allora promozione cumulativa di `LegalSource.status`,
     `CompensationDataset.status`, `CalculationFormula.status` a
     `approved`.

4. **Solo dopo lo step 3** il calculator pubblico inizierà a produrre
   `status=calculated` con importi reali. Fino ad allora il wizard
   continua correttamente a restituire
   `unavailable_requires_legal_validation` con il `missing_documents`
   appropriato a ogni livello di gating.

## Avviso finale

Il CSV è il miglior risultato che un assistente AI può produrre dato
solo il PDF. **Non sostituisce** la responsabilità professionale dello
Studio sulla coerenza dei valori e sulla loro aderenza al testo
ufficiale del D.P.R. 12/2025. Ogni futura promozione a `approved` è un
atto umano discrezionale e tracciato in `LegalReview`.
