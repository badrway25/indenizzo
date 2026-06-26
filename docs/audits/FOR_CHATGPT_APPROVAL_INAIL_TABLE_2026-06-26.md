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

---

## P11 — verified extraction evidence (2026-06-26)

Genuine fetch+parse attempt (tools available in this env: pdfplumber, pdftotext,
tesseract, pandas, PIL). Network to official sources confirmed reachable.

**Authoritative current-table chain (verified via the INAIL portal):**

- Original table: **D.M. Lavoro 12/07/2000** (GU 25/07/2000 n. 172, atto
  `000A9926`) — applies to infortuni/MP dal 25/07/2000, gradi **6%–15%** in
  capitale, **≥16%** in rendita.
  - GU permalink: https://www.gazzettaufficiale.it/eli/id/2000/07/25/000A9926/sg
- **Current table (in force):** *Nuova tabella di indennizzo del danno biologico
  in capitale*, **Determinazione Presidenziale INAIL n. 2 del 09/01/2019**,
  approvata con **D.M. Lavoro n. 45 del 23/04/2019** — sostituisce la tabella
  del 2000, +~40%, assorbe le rivalutazioni straordinarie 2008 (8,68%) e 2014
  (7,57%) = +16,25% cumulato.
- **Latest revaluation:** **Delibera INAIL C.d.A. n. 43 del 26/03/2025**,
  efficace **01/07/2025** (rivalutazione annuale).
- Portal page (verified, no downloadable value table attached):
  `.../prestazioni-economiche/indennizzo-in-capitale-per-la-menomazione-...html`

**What was downloaded and hashed (kept OUT of the repo, in temp):**

- `Allegato 5.pdf` from INAIL circolari — SHA256
  `046b823c9a8b3ae8a05fb3d78f713f59739976143dd980d0ba61b8e317c245de` —
  **identified as MOD 16/TER S.A. 2024 (modulo di calcolo agli eredi), NOT the
  value table.** It references *"Importo dell'indennizzo da tabella"* but does
  not contain the grado×età values.
- The lavoro.gov.it decree mirror returned an HTML stub (179 B), not the PDF.

**Conclusion:** the grado×età capital values are NOT published on the portal as
a clean parseable file; the live values require the **2019 table revalued to the
26/03/2025 delibera (eff. 01/07/2025)**. Extracting+verifying them
cell-by-cell autonomously would risk false figures — so the engine stays unbuilt
and the public section stays a guided path until the values below are validated.

## Precise ask (so an engine can be built)

> Fornisci la **tabella indennizzo danno biologico in capitale** vigente
> (Det. Pres. INAIL 2/2019 + D.M. 45/2019, rivalutata alla Delibera CdA 43 del
> 26/03/2025, eff. 01/07/2025): per ogni **grado 6–15%** e **fascia d'età**
> l'importo in euro (specifica se il genere incide ancora o se è stato
> unificato dal 2019). Indica la fonte/pagina di ciascuna riga.

## Canary required

Almeno un esempio ufficiale (grado, età → importo in capitale €) verificabile,
asserito al centesimo, prima di attivare `inail_biological_damage_capital`.

---

## P12 — table search hardening (2026-06-26)

Re-attempt to locate a clean, parseable PDF of the **value table** (not a form):

- The current values = the **2019 table (Det. Pres. 2/2019 + D.M. 45/2019)**
  revalued to **Delibera CdA 43 del 26/03/2025 (eff. 01/07/2025)**.
- The INAIL portal page does not attach a downloadable value table; the only
  table-named asset reachable was "Allegato 5" = MOD 16/TER (heirs form), already
  hashed and ruled out.
- OCR fallback is unavailable in this environment (no PDF→image rasterizer:
  pdftoppm/gs/fitz missing; tesseract eng-only), so a scanned table could not be
  processed even if located.

**Therefore the values must be supplied/validated by ChatGPT/owner** (10 sample
rows minimum: grado 6–15% × fascia d'età → importo €), then imported via
`import_inail_biological_damage` with a canary. Public INAIL stays a guided path
until then. Tracked in `CHATGPT_APPROVAL_QUEUE_2026-06-26.md` (row 3).
