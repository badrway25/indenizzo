# Approval pack — INAIL indemnity table (danno biologico)

Date: 2026-06-26 · Section: INAIL / infortunio sul lavoro (#6) · Target state:
`numeric_estimate_approved` (today `official_guided_path_approved`).

## Why this pack exists

The INAIL biological-damage indemnity is governed by an **official** table, but
it has **not** been imported as an approved `CompensationDataset` in this repo,
so no numeric engine is published — the public section ships as an official
guided path. To activate `inail_biological_damage_capital` I need the exact
table values approved by the owner/ChatGPT (same procedure used for art.
138/139, where the owner supplied the coefficients).

## Official source

- **D.P.R. 30/06/1965 n. 1124** — Testo Unico INAIL.
- **D.Lgs. 23/02/2000 n. 38, art. 13** — introduces danno biologico INAIL.
- **D.M. Lavoro 12/07/2000** — two official tables:
  1. *Tabella delle menomazioni* (0–100% degree per impairment);
  2. *Tabella indennizzo danno biologico* — the capital/annuity value;
  3. *Tabella dei coefficienti* (for the patrimonial component ≥16%).
- Channels: Gazzetta Ufficiale / Normattiva / INAIL istituzionale.
- URLs (to be confirmed by ChatGPT against the official PDF, not a portal):
  Normattiva D.M. 12/07/2000; INAIL "Danno biologico — tabelle".

## Extraction status

- Attempted in-repo: the official D.M. 2000 indemnity table is **not present**
  under approved sources; it was not extracted/verified to the cent in this
  environment. No file hash is recorded because the official PDF was not
  retrieved into the repo (no heavy PDF committed, per policy).

## Exact data needed (so it can be imported like art. 139)

Provide, as owner-approved official values:

1. **Indennizzo in capitale** — for permanent biological damage **6%–15%**:
   value (EUR) **per degree of impairment**, by **age band** (the table is
   age-decreasing). Format: rows `(degree %, age_band, capital_eur)`.
2. **Rendita / annual value** — for permanent biological damage **≥16%**: the
   annual biological-damage amount per degree, plus the patrimonial coefficient
   table (`coefficiente` by degree band) used for the patrimonial component.
3. **Revaluation** — the latest official revaluation/index applied to the 2000
   values (which decree, which year, which multiplier).

### Expected data format (matches CompensationTableRow)

```
row_type=inail_capital_indemnity   degree_min, degree_max, age_min, age_max, point_value(EUR)
row_type=inail_annuity_value       degree_min, degree_max, daily_amount or point_value(EUR/anno)
row_type=inail_patrimonial_coeff   degree_min, degree_max, coefficient
```

## Precise question for ChatGPT

> Fornisci la tabella ufficiale di indennizzo del danno biologico INAIL
> (D.M. 12/07/2000, art. 13 D.Lgs. 38/2000), valori in capitale 6–15% per
> grado ed età, e i valori in rendita ≥16% con i coefficienti, inclusa l'ultima
> rivalutazione ufficiale (decreto e anno). Indica per ogni riga: grado %,
> fascia d'età, importo in euro, fonte/articolo.

## How it would be implemented

- `import_inail_biological_damage_2000` management command → approved
  `LegalSource` (D.M. 12/07/2000) + `LegalSourceVersion` + approved
  `CompensationDataset(case_type="work_injury_inail")` + rows above + approved
  `CalculationFormula(engine="inail_biological_damage_capital")`.
- Engine output must be labelled **"indennizzo INAIL"**, distinct from
  **"risarcimento civile"** (danno differenziale). Strong public disclaimer.

## Required canary test

At least one official worked example: e.g. *grado 10%, età X → indennizzo in
capitale Y €*, asserted to the cent (mirrors `test_italy_art139_micro`).
Until that canary is green the engine stays fail-closed and the public stays on
the guided path.
