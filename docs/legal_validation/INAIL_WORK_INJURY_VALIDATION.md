# Validation pack — INAIL work injury (Italy)

**Country · category:** IT · work_injury (danno biologico INAIL)
**Status:** `needs_legal_review`
**Public behaviour today:** documental pre-check → dossier (no amount).

## Official source(s)
- **D.Lgs. 38/2000** — introduces danno biologico into the INAIL scheme.
- **D.M. 12/07/2000** — "Tabella delle menomazioni" + "Tabella indennizzo danno
  biologico" (the menomazione% → indemnity mapping) + "Tabella dei coefficienti".
- **D.M. 45/2019** — capital-indemnity values / revaluation.
- **T.U. 1124/1965** — framework.
- Registry ids: `it-dlgs-38-2000`, `it-dm-45-2019`, `it-tu-inail-1124`.

## Official URL / access
- INAIL portal: https://www.inail.it (institutional)
- Normattiva: https://www.normattiva.it (D.Lgs. 38/2000, D.M. 12/07/2000)
- Gazzetta Ufficiale: https://www.gazzettaufficiale.it (D.M. 45/2019)
- **Downloaded file hash:** _(to be filled when the verbatim table PDF is archived)_

## Table / formula present
- **Yes, in principle** — the menomazione% → indennizzo mapping and the capital
  table are official. **Not present in the project DB** and not reliably
  machine-extractable from an accessible primary source today.

## Required inputs (for a future engine)
- grado di menomazione (%), età, data infortunio, tipo prestazione
  (capitale / rendita), reddito (for rendita).

## Canary example (to be provided by the legal reviewer)
```
# Fill with ONE legally-reviewed worked example from the official table:
input:  { menomazione_pct: __, eta: __, prestazione: "capitale" }
expected_indennizzo: __ EUR   # verbatim from D.M. 12/07/2000 / D.M. 45/2019
source_row: "D.M. 12/07/2000, allegato __, riga __"
```
_(No value is invented here. The canary stays empty until the legal team
transcribes a verbatim row.)_

## Blockers before `ready_for_engine`
1. Legal team transcribes the official menomazione/indemnity table verbatim
   (with the 2025 revaluation) and confirms the coefficient/age rules.
2. The danno biologico INAIL differs from the civil differential — the engine
   must model the INAIL head specifically, not reuse the civil art.138/139.
3. Archive the source PDF + record its hash; import as APPROVED dataset.

## Next action
Legal review of the INAIL indemnity table → fill the canary above → engineering
builds an `inail_biological_damage` fail-closed engine + canary, flips
`it-dm-45-2019` to usable, updates the matrix and source library.
