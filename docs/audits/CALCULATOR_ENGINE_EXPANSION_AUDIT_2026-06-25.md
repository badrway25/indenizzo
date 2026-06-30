# Calculator engine expansion — technical & legal audit

**Phase**: P6 · 2026-06-25 · author: architecture review grounded in the live DB
and the engine code (`apps/calculators/engines/italy.py`,
`apps/calculators/registry.py`, `apps/compensation`).

## 1. Which engines exist today

Registry `(jurisdiction, case_type) → calculator` (verified in DB):

| Pair | Calculator | Calculates? |
|---|---|---|
| IT-NATIONAL · road_accident_bodily_injury | ItalyRoadAccidentBodilyInjuryCalculator | **YES** |
| IT-NATIONAL · inheritance_basic | ItalyInheritanceBasicCalculator | no (placeholder) |
| FR-NATIONAL · road_accident_bodily_injury | FranceRoadAccident… | no (inert) |
| BE-NATIONAL · road_accident_bodily_injury | BelgiumRoadAccident… | no (inert) |
| MA-NATIONAL · international_inheritance | MoroccoInheritance… | no (placeholder) |
| TN-NATIONAL · international_inheritance | TunisiaInheritance… | no (placeholder) |

## 2. Why ONLY road accident calculates (the 4-gate chain)

The Italy engine is **fully data-driven** — *no monetary value is hardcoded*. A
public number is produced only when **all four gates** pass (from `italy.py`):

1. `LegalSource.approved` for the (jurisdiction, case_type)
2. `CompensationDataset.approved` linked to that source
3. `CalculationFormula.approved` whose `parameters.engine` + `amount_rule` are
   recognised by `apps.compensation.services`
4. a matching `CompensationTableRow` with a **non-null `point_value`**

**Live DB state (verified):**
- Approved `CompensationDataset`: **TUN 2025 danno biologico** (`DPR-12-2025`,
  9 191 rows) + **TUN 2025 danno morale** (`DPR-12-2025-MORAL`, 27 573 rows) —
  both `case_type=road_accident_bodily_injury`.
- Approved `CalculationFormula`: **exactly one** — `italy_art_138_tun_2025_base`
  (engine `italy_tun_point_value_v1`, rule `row_amount_range_direct`).
- `draft` (do NOT calculate): BE Tableau Indicatif 2020, FR Gazette du Palais
  2022, FR Mornet 2024.

➡️ **Road accident is the only complete approved chain.** Everything else is
fail-closed by design: even with an approved *source* present, the placeholder
calculators return `UNAVAILABLE_REQUIRES_LEGAL_VALIDATION` rather than invent a
number. The approved formula is **art. 138** (macrolesioni ≥10% biological
damage); there is **no art. 139 (microlesioni 1–9%) approved chain**.

## 3–8. Per-candidate feasibility (official sources + what is computable)

`can_calc_now`: **yes** (approved chain exists) · **buildable** (official table
values in hand → could create the approved chain) · **no** (no official public
formula, or values not verifiably available).

### IT — microlesioni 1–9% (art. 139 CAP + D.M. MIMIT)
- **Official source:** art. 139 D.Lgs. 209/2005 + annual **D.M. MIMIT** updating
  the *valore punto* and the daily ITT figure (catalogued `needs_review`,
  official URLs on mimit.gov.it / Gazzetta).
- **Computable?** Yes IN PRINCIPLE — art. 139 has a closed national formula
  (point value × age coefficient + ITT). **BLOCKER:** the exact 2025 numeric
  values (valore punto, ITT/day, age demoltiplicatore) live in JS-rendered
  Gazzetta / FlateDecode-compressed MIMIT PDFs and are **not verifiably
  extracted**. Implementing without the verified table = inventing numbers →
  **forbidden**.
- **Verdict: buildable, NOT now.** Need: the official D.M. MIMIT 2025 microlesion
  table (valore punto €, ITT €/day, age coefficient) confirmed from the Gazzetta
  PDF. Then a `CompensationDataset(case_type=road_accident_microlesion)` +
  `CalculationFormula` (engine `italy_micro_art139_v1`) + a new calculator. ~0
  invented values once the table is provided.

### IT — medical liability (TUN-compatible macrolesioni)
- **Official source:** L. 24/2017 art. 7 → biological-damage macrolesioni use the
  **same national TUN** (already approved in DB).
- **Computable?** Yes — the TUN values already exist `approved`. This is the
  **#1 ready candidate** because no new numeric data is invented.
- **BLOCKER (engineering, not legal):** the approved TUN dataset is keyed to
  `case_type=road_accident_bodily_injury`. Enabling medical requires NEW approved
  DB records (a `LegalSource` for the medical chain + a `CompensationDataset`/
  `CalculationFormula` that *reuse the same TUN point values* for
  `case_type=medical_liability_macro`) — a **data migration** + a new calculator
  + wizard + result + i18n + **TUN canary** (must not regress the existing
  26268/27353/28439 road-accident smoke). Output limited to the *biological*
  base only (never causal link / loss-of-chance / extra moral).
- **Verdict: buildable; planned, not implemented this phase** (avoids rushing a
  migration + calculator change that touches the canary at the end of a long
  session). Plan below.

### IT — INAIL / workplace injury (D.M. 12/07/2000, D.M. 45/2019)
- **Official source:** T.U. INAIL D.P.R. 1124/1965 + **D.M. 12/07/2000** (G.U.
  172 of 25/07/2000, tabelle menomazioni/indennizzo/coefficienti) + **D.M. 45 of
  23/04/2019** (danno biologico in capitale).
- **Computable?** Yes in principle (INAIL indemnity has official tables).
  **BLOCKER:** the menomazioni/indennizzo tables are not in the DB and not
  verifiably extracted. Implementing = inventing → forbidden. Must keep INAIL
  indemnity **distinct** from civil/differential damage.
- **Verdict: buildable, NOT now.** Need: an importer + the official D.M. 2000 /
  D.M. 45-2019 tables (menomazione % → indennizzo €, age coefficient). Documented
  as a separate importer task.

### IT — insurance-offer adequacy check
- Depends entirely on the microlesion/TUN engines above. A "verifica congruità"
  tool can compare a received offer to the official estimate **only for cases the
  official engine already covers** (TUN macrolesioni). It invents nothing — it
  reuses the engine output. **Buildable once medical/micro engines land** (or
  immediately for TUN-macro cases, as a thin UI over the existing engine).

### IT — defective product
- **Official source:** D.Lgs. 206/2005, artt. 114–127. **No official national
  amount formula.** → **no calc**, assisted pathway (already premium copy).

### IT — death / parental
- **No official national statutory table** (Milano tables = court practice, not a
  ministry/government primary source). → **no calc**, assisted pathway. (See
  OFFICIAL_SOURCES_NOT_FOUND.)

## 9. Technical plan to add a new engine (template)

1. Obtain the **verified official table** (values from the official portal/PDF).
2. Create a `LegalSource` (approved, with provenance) + `CompensationDataset`
   (approved) + `CompensationTableRow`s carrying the official `point_value`s +
   a `CalculationFormula` (approved) with a registered `engine`/`amount_rule`.
   (DB records → a data migration is justified here.)
3. Add a `Calculator` subclass + `register_calculator((IT, case_type), …)`.
4. Wizard template + result wiring + source drawer + i18n.
5. **Canary tests**: a fixed input → fixed expected € (like the 35/10/0 →
   26268/27353/28439 road-accident smoke) so the engine can never silently drift.
6. Fail-closed everywhere a gate is unmet.

**Priority order (once data is in hand):** medical-TUN macrolesioni →
microlesioni art.139 → INAIL → insurance-offer check.

## 10. Legal risks

- Inventing any coefficient/amount = the cardinal violation (avoided: nothing
  implemented without the verified official table).
- Mixing INAIL indemnity with civil differential would mislead → kept distinct.
- Publishing a medical estimate beyond the biological base (causal link, fault,
  loss-of-chance) would overstate certainty → medical engine, when built, is
  limited to the official TUN biological base only.
- FR/BE/MA/TN stay fail-closed: their candidate datasets are `draft`, never
  approved, so the engines remain inert — correct.
