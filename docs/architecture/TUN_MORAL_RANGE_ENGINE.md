# TUN — Range engine per il danno morale (Tabelle 2.A/2.B/2.C)

> Fase tecnica F-italy-moral-range-engine. Il codice del calculator è
> stato esteso per **supportare** la regola `row_amount_range_direct`,
> ma il calcolo pubblico **NON la usa ancora**: la formula approvata in
> produzione resta su `row_amount_direct` e il dataset morale è in
> stato `draft`. Questo documento spiega cosa è cambiato e cosa serve
> per attivare il range nel funnel pubblico.

## 1. Cosa sono Tabelle 2.A / 2.B / 2.C

Sono gli allegati II del **D.P.R. 13 gennaio 2025 n. 12** che estendono
la Tabella 1 (danno biologico) sommando il danno morale. Per ogni cella
`(età, % invalidità)`:

- **Tabella 1** → `A` = valore punto biologico.
- **Tabella 2.A** → `A + B(min)` = danno biologico + danno morale con
  aumento **minimo** previsto dalla legge.
- **Tabella 2.B** → `A + B(med)` = aumento **medio**.
- **Tabella 2.C** → `A + B(max)` = aumento **massimo**.

Per la stessa `(età, invalidità)`:

```
A           ≤   A+B(min)   ≤   A+B(med)   ≤   A+B(max)
biologico   ≤   minimo     ≤   medio      ≤   massimo
```

Esempio (età 0, inv 10): biologico 26 124 € — minimo 31 610 € — medio
32 916 € — massimo 34 222 €. Le tre celle morali sono `point_value`
"comprensivi" (= valori finali, non incrementi separati): si leggono
così come sono e si emettono come `estimated_min/mid/max`.

## 2. Perché il dataset morale è in `draft` separato dal base `approved`

La Tabella 1 base è approvata in produzione come `CompensationDataset
DPR-12-2025` con 9 191 righe `tun_biological_total_amount`. Il
calculator pubblico legge questo dataset oggi, attraverso una
`CalculationFormula` con `amount_rule = "row_amount_direct"`.

Le 27 573 righe morali sono importate in un dataset **separato**:

| | base | morale |
|---|---|---|
| `version_label` | `DPR-12-2025` | `DPR-12-2025-MORAL` |
| `status` | `approved` | **`draft`** |
| `source` | stessa LegalSource `it-dpr-12-2025-tun-danno-biologico` (approved) | stessa LegalSource (riusata) |
| `case_type` | `road_accident_bodily_injury` | uguale |
| Righe | 9 191 (`tun_biological_total_amount`) | 27 573 (3 × 9 191) |
| `row_type` | `tun_biological_total_amount` | `tun_biological_moral_{min,mid,max}_total_amount` |

Motivi della separazione:

1. **Rollback granulare**: revocare l'approval del moral non tocca le
   9 191 righe del base — il calculator pubblico continua a funzionare
   come prima.
2. **Isolamento stato**: il command `import_italy_tun_2025_moral` lavora
   esclusivamente sul `version_label="DPR-12-2025-MORAL"` e non può
   contaminare `DPR-12-2025`. La regola viene anche difesa da test AST
   (`test_command_source_has_no_destructive_delete`).
3. **Gating progressivo**: il calculator può supportare il range
   tecnicamente PRIMA che lo Studio promuova il moral a `approved` —
   nessun rischio di esporre dati non validati al pubblico.

## 3. Schema futuro di `CalculationFormula.parameters`

Quando lo Studio approverà le tabelle morali, l'attivazione del range
**non** richiede una nuova formula: basta editare `parameters` della
formula esistente (`code = italy_art_138_tun_2025_base`).

### Stato corrente (range NON attivo)

```json
{
  "engine": "italy_tun_point_value_v1",
  "requires": ["victim_age", "permanent_disability_percentage"],
  "row_match": ["victim_age", "permanent_disability_percentage"],
  "amount_rule": "row_amount_direct",
  "fault_reduction": true
}
```

Effetto: `estimated_min == estimated_mid == estimated_max` (un solo
valore, dal dataset base).

### Schema futuro (range attivo)

```json
{
  "engine": "italy_tun_point_value_v1",
  "requires": ["victim_age", "permanent_disability_percentage"],
  "row_match": ["victim_age", "permanent_disability_percentage"],
  "amount_rule": "row_amount_range_direct",
  "fault_reduction": true,
  "range_dataset_version_label": "DPR-12-2025-MORAL",
  "min_row_type": "tun_biological_moral_min_total_amount",
  "mid_row_type": "tun_biological_moral_mid_total_amount",
  "max_row_type": "tun_biological_moral_max_total_amount"
}
```

Effetto: `estimated_min < estimated_mid < estimated_max`, valori letti
dalle 3 row_type del dataset moral (che a quel punto deve essere
`approved`).

## 4. Difese applicative — perché il range non si attiva "per sbaglio"

Anche con `parameters` modificato in admin, il calculator si rifiuta di
emettere un range se uno qualsiasi dei seguenti non è soddisfatto:

1. **Dataset moral non `approved`**:
   `get_approved_dataset_by_version_label(...)` filtra a livello SQL
   per `status = APPROVED`. Se il moral è ancora `draft`, ritorna
   `None` → `unavailable_requires_legal_validation`,
   `missing_documents=["range_dataset_approved"]`.

2. **Parametri range incompleti**: manca `range_dataset_version_label`,
   `min_row_type`, `mid_row_type` o `max_row_type` →
   `missing_documents=["formula_range_parameters_incomplete"]`.

3. **Riga mancante per uno dei 3 row_type** sulla cella richiesta →
   `missing_documents=["compensation_row_match"]`.

4. **Range non monotone** (es. `mid < min`) → la sanità è verificata in
   `RangeAmounts.is_monotone()` →
   `missing_documents=["compensation_range_inconsistent"]`. Il
   calculator non pubblica mai un range incoerente.

Questi controlli sono coperti dai test in
`apps/compensation/test_range_engine.py` (19 test fixture-only).

## 5. Backward compatibility

La regola single-row `row_amount_direct` resta funzionante e produce
ancora `estimated_min == estimated_mid == estimated_max`. Il flag
`is_range_rule(rule)` decide a runtime quale path eseguire, senza
duplicare il codice di gating sopra (gates 1-7 sono comuni).

Smoke contract storico:
```
calc.compute(victim_age=35, permanent_disability_percentage=10, fault_percentage=0)
→ estimated_min == estimated_mid == estimated_max == 21 709,00 €
```
Resta valido finché `formula.parameters.amount_rule = "row_amount_direct"`.

## 6. Passi per attivare il range pubblicamente

Sequenza richiesta (atti umani dello Studio in **maiuscolo**, atti
tecnici in minuscolo):

1. **Sample-review umana** sui ~3 751 cells in
   `tun_2025_moral_review_tasks.csv` (priority `medium` su `hot_page`
   + `over_one_million`). Marcare `reviewer_status = human_sample_approved`.
2. **`LegalReview(decision=approve)`** sulla `LegalSource` del D.P.R.
   12/2025 (la fonte è già `approved`: la nuova review documenta
   l'estensione di scope alle Tabelle 2.x e cita il sample-check).
3. **Promuovi** `CompensationDataset(version_label="DPR-12-2025-MORAL")`
   da `draft` a `approved`. Vincolo `clean()`: la fonte deve essere
   `approved` (è già). Nessuna nuova migrazione.
4. **Aggiorna `CalculationFormula.parameters`** della formula esistente
   `italy_art_138_tun_2025_base` con lo schema §3 (range attivo).
   La formula resta sulla stessa `code` e sullo stesso dataset base —
   è un'edit di `parameters`, non una nuova formula. Status resta
   `approved`.
5. **Smoke verifica**: `calc.compute(35, 10, 0)` deve ora restituire
   `min < mid < max` con tre valori distinti, tutti > 21 709.
   - `min` ≈ A+B(min) cella (35, 10) — letto da `DPR-12-2025-MORAL`.
   - `mid` ≈ A+B(med) cella (35, 10).
   - `max` ≈ A+B(max) cella (35, 10).
6. **Rollback contingenza**: se uno qualsiasi degli step 1-5 fallisce,
   ripristinare `parameters.amount_rule = "row_amount_direct"`. Il
   calculator torna immediatamente a min=mid=max sul base, senza
   dipendere dallo stato del moral. Il moral può restare `approved`
   senza essere usato — è un dataset secondario.

Niente di tutto questo è stato eseguito da F-italy-moral-range-engine.
Lo step di codice fatto qui è solo l'aggiunta della regola al registro
e la sua dispatching nel calculator.

## 7. File modificati / introdotti in F-italy-moral-range-engine

| File | Modifiche |
|---|---|
| `apps/compensation/services.py` | nuovi: `RANGE_AMOUNT_RULES`, `is_range_rule`, `get_approved_dataset_by_version_label`, `find_matching_row_by_type`, `RangeAmounts`, `apply_amount_range_rule`, `_rule_row_amount_range_direct`. Aggiornato: `SUPPORTED_AMOUNT_RULES` include `row_amount_range_direct`; `get_approved_dataset_for_sources` preferisce il dataset con formula approvata. |
| `apps/calculators/engines/italy.py` | aggiunto branch `is_range_rule` con `_compute_range`; il branch single-row resta identico. |
| `apps/compensation/test_range_engine.py` | 19 test fixture-only sulla regola, sui resolver e sull'integrazione calculator. |
| `docs/architecture/TUN_MORAL_RANGE_ENGINE.md` | questo documento. |

Niente migrazioni Django. Nessuna modifica a modelli, admin, wizard,
PDF report, formula `parameters` reali, dataset reali, status reali.
