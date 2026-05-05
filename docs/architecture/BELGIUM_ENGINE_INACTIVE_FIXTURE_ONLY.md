# Belgium engine — inactive scaffold, fixture-only

**Iter:** `F-belgium-engine-inactive-fixture-only`.

This document describes the state of the Belgium road-accident
calculator after this iter: the engine code path is fully wired and
tested for three pass-1 amount rules, but the public DB has zero
APPROVED BE sources/datasets/formulas, so a
`run_simulation(BE-NATIONAL, road_accident_bodily_injury)` keeps
returning `unavailable_requires_legal_validation`.

The engine is intentionally inactive on the public path. Only test
fixtures in `apps/calculators/test_belgium_engine_inactive.py` exercise
the executable branch, with synthetic numeric values that never reflect
real Tableau Indicatif 2020 amounts.

---

## What's ready

### `apps/compensation/services.py`

Three new amount rules and one engine identifier are registered:

- `SUPPORTED_ENGINES += {"belgium_road_accident_v1"}`
- `SUPPORTED_AMOUNT_RULES += {"belgium_souffrances_age_severity_direct",
  "belgium_forfait_age_annual_direct",
  "belgium_deces_affection_relation_direct"}`
- `SINGLE_ROW_RANGE_AMOUNT_RULES` extended with the same three rules
  (each returns a `RangeAmounts(min, mid, max)` triple from a single
  matched row).

The shared `_row_matches` helper now understands two new predicates
that read from `row.extra` rather than dedicated columns:

- `severity_scale` → matches `row.extra.severity_code` (e.g. `1_7`,
  `7_7`).
- `relation_code` → matches `row.extra.relation_code` (e.g. `spouse`,
  `parent_cohabitant`).

Three rule functions are added:

- `_rule_belgium_souffrances_age_severity_direct(row, ...)` — reads
  `row.extra.amount_min/mid/max` (fallback `row.point_value`),
  returns the triple verbatim, applies optional fault reduction
  uniformly.
- `_rule_belgium_forfait_age_annual_direct(row, ...)` — reads
  `row.extra.annual_amount` and scales linearly by an optional
  `incapacity_percentage` input. The scalar is broadcast across
  (min, mid, max) — Tableau Indicatif emits one value per age, no
  per-cell fourchette.
- `_rule_belgium_deces_affection_relation_direct(row, ...)` — same
  shape as the souffrances rule, but the row is keyed by
  `relation_code` rather than (age × severity).

Vehicule de remplacement is intentionally **out** of pass-1: its
taxonomy of camions / autobus / véhicules spéciaux requires a dedicated
formula schema that the Studio will examine in a later iter (see
*"What's required to activate Belgium"* below).

### `apps/calculators/engines/belgium.py`

The placeholder `BelgiumRoadAccidentBodilyInjuryCalculator` is now a
real engine that mirrors the France gating sequence and dispatches to
the single-row range path. Order of evaluation:

1. no APPROVED legal source for BE → `UNAVAILABLE`
2. no APPROVED dataset linked → `UNAVAILABLE` (`compensation_dataset_approved`)
3. no APPROVED formula → `UNAVAILABLE` (`calculation_formula_approved`)
4. unknown `engine` → `UNAVAILABLE` (`formula_engine_unknown`)
5. unknown `amount_rule` → `UNAVAILABLE` (`formula_amount_rule_unknown`)
6. rule is not single-row range → `UNAVAILABLE`
   (`formula_amount_rule_not_single_row_range`)
7. required input missing → `INSUFFICIENT_INPUT`
8. `fault_percentage` out of [0, 100] → `INSUFFICIENT_INPUT`
9. `row_type` not declared → `UNAVAILABLE` (`formula_row_type_missing`)
10. no row matches → `UNAVAILABLE` (`compensation_row_match`)
11. multiple rows match → `UNAVAILABLE` (`compensation_row_disambiguation`)
12. range non-monotone → `UNAVAILABLE` (`compensation_range_inconsistent`)
13. all gates pass → `CALCULATED`

Public DB outcome (today): step 1 fails because no BE `LegalSource`
is `APPROVED`. The engine never reaches the dispatch branches.

The public status surface is **unchanged**: the BE row of
`apps/core/public_status.py::_RULES` stays at
`("BE", "road_accident", _LEGAL_ASSESSMENT)`, so the
`/wizard/be/road-accident/` panel still reads "Preliminary legal
assessment" with the no-amounts disclaimer.

---

## What's deliberately inactive

- **No BE `LegalSource` is `APPROVED`.** The Tableau Indicatif 2020
  source (`be-tableau-indicatif-2020`) stays `needs_review`.
- **No BE `CompensationDataset` is `APPROVED`.** The DRAFT dataset
  imported by `import_belgium_candidate_datasets`
  (`BE-TABLEAU-INDICATIF-2020-DRAFT`, 166 rows) stays DRAFT. The verify
  script `scripts/legal_data/verify_belgium_candidate_import.py` asserts
  this on every run.
- **No BE `CalculationFormula` exists.** Zero formulas point at the
  `belgium_road_accident_v1` engine in the public DB.
- **No real Tableau Indicatif amounts appear in tests.** A static guard
  test (`test_no_real_be_values_in_this_test_file`) reads the upstream
  BE CSVs at test time, builds the set of real amounts (ignoring
  trivial values and year-like 4-digit strings), and asserts none
  appear in this test file's source.
- **Vehicule de remplacement** is not wired as an engine rule today.
  The CSV has been imported in DRAFT; promotion to a public calculator
  needs its own formula and a taxonomy decision the Studio must drive
  (camions par tonnage, autobus par siège, etc.).

The result is the inverse pyramid: the engine code is fully covered, the
gating is fully tested, but the public path runs zero of the executable
branches. This is by design.

---

## Why no real values in tests

The project's contract is "*meglio nessun calcolo che un calcolo falso*".
Tests that hard-code real Tableau Indicatif amounts would create a
*second source of truth* alongside the upstream CSVs:

- a future re-extraction (e.g. once the 2024 OCR pipeline lands clean)
  would update the CSVs but leave the test amounts stale;
- a regression in the upstream CSVs would still pass tests because the
  test amounts were copied from a now-outdated version;
- developers writing fixtures might inadvertently treat the test
  amounts as the canonical BE bareme.

Using synthetic values (`amount_min=777`, `amount_mid=888`,
`amount_max=999`, `annual_amount=100`, `incapacity=10`) makes the math
easy to verify by inspection and makes the test file useless as a data
source. The static guard prevents accidental copy-paste regressions of
real numbers into the test file.

---

## Why BE 2020 is "historical / candidate"

The Belgian Tableau Indicatif des cours et tribunaux is republished
every few years (2008, 2012, 2016, 2020, 2024...). The 2020 edition is
the most recent edition we have a clean, automated extraction for (see
`docs/legal_sources/BELGIUM_TI_2020_EXTRACTION_REPORT.md`).

The 2024 edition exists in the repo as scanned/OCR material, but the
quality of that pipeline is not yet good enough to feed legal-grade
quantification (see `docs/legal_sources/BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`).

Holding the 2020 corpus in DRAFT lets the Studio review it as the
legitimate "candidate" while the 2024 pipeline matures. The decision
between "promote 2020 first, replace with 2024 later" and "wait for
2024 then promote that directly" is a separate Studio call — see the
last section.

---

## Future formula `parameters` schema

When Studio promotes the Tableau Indicatif source to APPROVED, the
`CalculationFormula`s for the BE pass-1 perimeters will declare:

```json
{
  "engine": "belgium_road_accident_v1",
  "amount_rule": "belgium_souffrances_age_severity_direct",
  "row_type": "be_souffrances_endurees_per_age_severity_amount",
  "row_match": ["victim_age", "severity_scale"],
  "requires": ["victim_age", "severity_scale"],
  "fault_reduction": true
}
```

```json
{
  "engine": "belgium_road_accident_v1",
  "amount_rule": "belgium_forfait_age_annual_direct",
  "row_type": "be_indemnite_forfaitaire_per_age_annual_amount",
  "row_match": ["victim_age"],
  "requires": ["victim_age"],
  "fault_reduction": true
}
```

```json
{
  "engine": "belgium_road_accident_v1",
  "amount_rule": "belgium_deces_affection_relation_direct",
  "row_type": "be_prejudice_deces_affection_per_relation_amount",
  "row_match": ["relation_code"],
  "requires": ["relation_code"],
  "fault_reduction": true
}
```

This iter does **not** create any of these formulas in the public DB.
Any future iter that does will be subject to a `LegalReview` from a
Studio reviewer before promotion.

---

## What's required to activate Belgium on the public path

Each step is a separate iter. Until all five land, BE stays
`unavailable` and the public status panel keeps reading
"Preliminary legal assessment".

1. **Studio legal review** of the Tableau Indicatif 2020 source →
   `LegalReview.decision=approve` from a real reviewer →
   `LegalSource(slug='be-tableau-indicatif-2020').status = APPROVED`.
2. **Promote the candidate dataset**: change
   `CompensationDataset(version_label='BE-TABLEAU-INDICATIF-2020-DRAFT')`
   to a non-DRAFT version label (e.g. `BE-TABLEAU-INDICATIF-2020`) with
   `status=APPROVED`. The DRAFT label is load-bearing — the import
   command refuses to write into a non-DRAFT dataset.
3. **Create three BE `CalculationFormula`s** (one per pass-1
   perimeter), each with the schema above and `status=APPROVED`. Same
   gating: only an APPROVED formula on an APPROVED dataset on an
   APPROVED source can run.
4. **Smoke test calculator BE** with at least one canonical tuple per
   perimeter, locked in `apps/calculators/test_*.py` like the IT
   35/10/0 = 26 268 / 27 353 / 28 439 EUR contract. The smoke values
   must come from the legal-reviewed 2020 / 2024 Tableau Indicatif and
   be cited explicitly in the test, not invented.
5. **Decision on BE 2024 vs 2020 fallback.** If by activation time the
   2024 OCR pipeline is clean, the Studio should choose between:
   - importing 2024 as a sibling DRAFT
     (`BE-TABLEAU-INDICATIF-2024-DRAFT`) and promoting it instead of
     the 2020 corpus, or
   - promoting 2020 first and migrating to 2024 in a follow-up iter.
   Either path is legitimate; the calculator wiring is identical.
6. **Vehicule de remplacement formula** + taxonomy decision (camions
   par tonnage, autobus par nombre de sièges, véhicules spéciaux) →
   add a fourth amount rule
   (`belgium_vehicule_remplacement_per_type_per_day_direct` or
   similar) and a fourth approved formula.

After step 4, flip the public status: change
`("BE", "road_accident", _LEGAL_ASSESSMENT)` → `_AVAILABLE` in
`apps/core/public_status.py`. That's the single-line public-facing
edit that activates the BE wizard panel; everything else is data-layer
work.

---

## Cross-references

- Engine: `apps/calculators/engines/belgium.py`
- Service helpers: `apps/compensation/services.py`
- Tests: `apps/calculators/test_belgium_engine_inactive.py`
- Candidate dataset import:
  `apps/compensation/management/commands/import_belgium_candidate_datasets.py`
- Candidate dataset docs:
  `docs/legal_sources/BELGIUM_CANDIDATE_DATASET_IMPORT.md`
- Source extraction: `docs/legal_sources/BELGIUM_TI_2020_EXTRACTION_REPORT.md`
- 2024 OCR spike: `docs/legal_sources/BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`
- Legal review package: `docs/legal_sources/BELGIUM_LEGAL_REVIEW_PACKAGE.md`
