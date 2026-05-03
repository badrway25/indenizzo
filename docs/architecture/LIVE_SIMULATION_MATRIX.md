# Live simulation matrix — engine-level run

Generated: `2026-05-03T15:23:16.905757+00:00` (F-product-official-source-automation-and-full-site-functional-upgrade)

Matrice di simulazioni eseguita engine-level via `apps.cases.services.run_simulation`. Niente HTTP, niente DB write non previsto: lo script chiama il motore in modalità simulation save (la persistenza Simulation è una scrittura tracciata, non un side-effect su layer legale).

## Riepilogo

- Italia 35/10/0: **OK** — 26 268 / 27 353 / 28 439 EUR confermato.

## Tabella completa

| Case | Jurisdiction | Status | min | mid | max | Flag |
|------|--------------|--------|-----|-----|-----|------|
| Italy road accident — 35/10/0 (historical contract) | IT-NATIONAL | `calculated` | 26268.0000 | 27353.0000 | 28439.0000 | OK |
| Italy road accident — 35/10/50 (50% fault reduction) | IT-NATIONAL | `calculated` | 13134.0000 | 13676.5000 | 14219.5000 | OK |
| Italy road accident — 0/100/0 (max disability) | IT-NATIONAL | `calculated` | 1555542.0000 | 1607393.0000 | 1659245.0000 | OK |
| France road accident — placeholder | FR-NATIONAL | `unavailable_requires_legal_validation` | — | — | — | OK |
| Belgium road accident — placeholder | BE-NATIONAL | `unavailable_requires_legal_validation` | — | — | — | OK |
| Morocco international inheritance — placeholder | MA-NATIONAL | `unavailable_requires_legal_validation` | — | — | — | OK |
| Tunisia international inheritance — placeholder | TN-NATIONAL | `unavailable_requires_legal_validation` | — | — | — | OK |

## Dettagli per caso

### Italy road accident — 35/10/0 (historical contract)

- Jurisdiction: `IT-NATIONAL`
- Case type: `road_accident_bodily_injury`
- Input: `{'victim_age': 35, 'permanent_disability_percentage': 10, 'fault_percentage': 0}`
- Expected status: `calculated`
- Actual status: `calculated`
- Expected amounts: min=26268 mid=27353 max=28439
- Actual amounts: min=26268.0000 mid=27353.0000 max=28439.0000
- Note: Contratto storico TUN 2025 — non deve mai cambiare.
- Flag: `OK`

### Italy road accident — 35/10/50 (50% fault reduction)

- Jurisdiction: `IT-NATIONAL`
- Case type: `road_accident_bodily_injury`
- Input: `{'victim_age': 35, 'permanent_disability_percentage': 10, 'fault_percentage': 50}`
- Expected status: `calculated`
- Actual status: `calculated`
- Actual amounts: min=13134.0000 mid=13676.5000 max=14219.5000
- Note: Fault reduction 50% → range dimezzato esattamente vs 35/10/0.
- Flag: `OK`

### Italy road accident — 0/100/0 (max disability)

- Jurisdiction: `IT-NATIONAL`
- Case type: `road_accident_bodily_injury`
- Input: `{'victim_age': 0, 'permanent_disability_percentage': 100, 'fault_percentage': 0}`
- Expected status: `calculated`
- Actual status: `calculated`
- Actual amounts: min=1555542.0000 mid=1607393.0000 max=1659245.0000
- Note: Range alto coerente con dataset moral. Dipende da copertura tabellare TUN.
- Flag: `OK`

### France road accident — placeholder

- Jurisdiction: `FR-NATIONAL`
- Case type: `road_accident_bodily_injury`
- Input: `{'victim_age': 35, 'permanent_disability_percentage': 10}`
- Expected status: `unavailable_requires_legal_validation`
- Actual status: `unavailable_requires_legal_validation`
- Actual amounts: min=None mid=None max=None
- Note: Engine placeholder, fonti needs_review.
- Flag: `OK`

### Belgium road accident — placeholder

- Jurisdiction: `BE-NATIONAL`
- Case type: `road_accident_bodily_injury`
- Input: `{'victim_age': 35, 'permanent_disability_percentage': 10}`
- Expected status: `unavailable_requires_legal_validation`
- Actual status: `unavailable_requires_legal_validation`
- Actual amounts: min=None mid=None max=None
- Note: Engine placeholder, Tableau Indicatif/Schryvers needs_review.
- Flag: `OK`

### Morocco international inheritance — placeholder

- Jurisdiction: `MA-NATIONAL`
- Case type: `international_inheritance`
- Input: `{}`
- Expected status: `unavailable_requires_legal_validation`
- Actual status: `unavailable_requires_legal_validation`
- Actual amounts: min=None mid=None max=None
- Note: Engine placeholder, mapping conflitti di legge.
- Flag: `OK`

### Tunisia international inheritance — placeholder

- Jurisdiction: `TN-NATIONAL`
- Case type: `international_inheritance`
- Input: `{}`
- Expected status: `unavailable_requires_legal_validation`
- Actual status: `unavailable_requires_legal_validation`
- Actual amounts: min=None mid=None max=None
- Note: Engine placeholder, CSP Livre IX + Loi 98-97.
- Flag: `OK`

---

Generato da `scripts/live_simulation_matrix.py`. Lo script `run_simulation` persiste una `Simulation` in DB per ogni caso (scrittura attesa). Nessuna `LegalReview`, `CompensationDataset` o `CalculationFormula` viene creata o modificata.
