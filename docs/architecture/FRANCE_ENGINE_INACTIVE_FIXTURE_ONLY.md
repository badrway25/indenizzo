# France engine — inactive scaffold, fixture-only

**Iter:** `F-france-engine-inactive-fixture-only`.

This document describes the state of the France road-accident calculator
after this iter: the engine code path is fully wired and tested, but the
public DB has zero APPROVED FR sources/datasets/formulas, so a
`run_simulation(FR-NATIONAL, road_accident_bodily_injury)` keeps
returning `unavailable_requires_legal_validation`.

The engine is intentionally inactive on the public path. Only test
fixtures in `apps/calculators/test_france_engine_inactive.py` exercise
the executable branch, with synthetic numeric values that never reflect
real Mornet 2024 / Gazette du Palais 2022 amounts.

---

## What's ready

### `apps/compensation/services.py`

Two registry extensions and one new dispatch helper:

- `SUPPORTED_ENGINES += {"france_road_accident_v1"}`
- `SUPPORTED_AMOUNT_RULES += {"france_dfp_point_value_direct"}`
- `SINGLE_ROW_RANGE_AMOUNT_RULES = {"france_dfp_point_value_direct"}` (new
  category alongside the existing `RANGE_AMOUNT_RULES` for 3-row rules)
- `is_single_row_range_rule(rule)` → True iff the rule reads ONE row
  but emits a (min, mid, max) triple (typically because the row carries
  a range under its `extra` JSON).
- `apply_amount_single_row_range_rule(rule, *, row, input_data, fault_reduction_enabled)`
  → `RangeAmounts`. Currently dispatches only `france_dfp_point_value_direct`.
- `_rule_france_dfp_point_value_direct(...)` — the actual rule:
  `amount_X = point_value_per_point_X × disability%` with
  `point_value_per_point_X` taken from `row.extra.amount_min/mid/max`
  if present (Mornet's full DFP shape), otherwise `row.point_value`
  duplicated. Fault reduction applied uniformly.

### `apps/calculators/engines/france.py`

The placeholder `FranceRoadAccidentBodilyInjuryCalculator` is now a real
engine that mirrors the Italy gating sequence but dispatches to the
single-row range path. Order of evaluation:

1. no APPROVED legal source for FR → `UNAVAILABLE`
2. no APPROVED dataset linked → `UNAVAILABLE` (`compensation_dataset_approved`)
3. no APPROVED formula → `UNAVAILABLE` (`calculation_formula_approved`)
4. unknown `engine` → `UNAVAILABLE` (`formula_engine_unknown`)
5. unknown `amount_rule` → `UNAVAILABLE` (`formula_amount_rule_unknown`)
6. rule is not single-row range → `UNAVAILABLE`
   (`formula_amount_rule_not_single_row_range`)
7. required input missing → `INSUFFICIENT_INPUT`
8. `fault_percentage` out of [0, 100] → `INSUFFICIENT_INPUT`
9. no row matches → `UNAVAILABLE` (`compensation_row_match`)
10. multiple rows match → `UNAVAILABLE` (`compensation_row_disambiguation`)
11. range non-monotone → `UNAVAILABLE` (`compensation_range_inconsistent`)
12. all gates pass → `CALCULATED`

Public DB outcome (today): step 1 fails because no FR `LegalSource`
is `APPROVED`. The engine never reaches the dispatch branches.

---

## What's deliberately inactive

- **No FR `LegalSource` is `APPROVED`.** Mornet 2024
  (`fr-referentiel-mornet-2024`) and Gazette du Palais 2022
  (`fr-bareme-capitalisation-gazette-palais-2022`) stay `needs_review`.
- **No FR `CompensationDataset` is `APPROVED`.** The Mornet and Gazette
  datasets imported in iter `F-france-import-datasets-draft-seed` stay
  `DRAFT`. The verify script `scripts/legal_data/verify_france_candidate_import.py`
  asserts this on every run.
- **No FR `CalculationFormula` exists.** Zero formulas point at the
  `france_road_accident_v1` engine in the public DB.
- **No real Mornet/Gazette numeric values appear in tests.** A static
  guard test (`test_no_real_fr_values_in_this_test_file`) reads the
  upstream CSVs at test time, builds the set of real amounts (ignoring
  trivial values and year-like 4-digit strings), and asserts none
  appear in this test file's source.

The result is the inverse pyramid: the engine code is fully covered, the
gating is fully tested, but the public path runs zero of the executable
branches. This is by design. Activating any of the executable branches
on the public DB requires Studio to climb the four steps below.

---

## Why no real values in tests

The project's contract is "*meglio nessun calcolo che un calcolo falso*".
Tests that hard-code real Mornet/Gazette amounts would create a *second
source of truth* alongside the upstream CSVs:

- a future re-extraction would update the CSVs but leave the test
  amounts stale;
- a regression in the upstream CSVs would still pass tests because the
  test amounts were copied from a now-outdated version;
- developers writing fixtures might inadvertently treat the test
  amounts as the canonical FR bareme.

Using synthetic values (`point_value=100`, `disability=10` →
expected `1000`) makes the math easy to verify by inspection and makes
the test file useless as a data source. The static guard prevents
accidental copy-paste regressions of real numbers into the test file.

---

## Future formula `parameters` schema

When Studio promotes Mornet to APPROVED, the `CalculationFormula` for
the FR DFP scope will declare:

```json
{
  "engine": "france_road_accident_v1",
  "amount_rule": "france_dfp_point_value_direct",
  "row_type": "fr_dfp_per_age_disability_amount_per_point",
  "row_match": ["victim_age", "permanent_disability_percentage"],
  "requires": ["victim_age", "permanent_disability_percentage"],
  "fault_reduction": true
}
```

The engine reads this and dispatches into
`apply_amount_single_row_range_rule`. The first matched row's
`extra.amount_min/mid/max` (or fallback `point_value`) is multiplied by
the input disability%, with optional fault reduction. The result is a
`RangeAmounts(min_amount, mid_amount, max_amount)` that maps directly
onto `Simulation.estimated_min/mid/max`.

This iter does **not** create such a formula in the DB. Any future iter
that does will be subject to a `LegalReview` from a Studio reviewer
before promotion.

---

## What's required to activate FR road-accident on the public path

Each step is a separate iter. Until all five land, FR stays `unavailable`.

1. **Studio legal review** of the Mornet 2024 source →
   `LegalReview.decision=approve` from a real reviewer →
   `LegalSource(slug='fr-referentiel-mornet-2024').status = APPROVED`.
2. **Promote the candidate dataset**: change
   `CompensationDataset(version_label='FR-MORNET-2024-DRAFT')` to a new
   non-DRAFT version label (e.g. `FR-MORNET-2024`) with `status=APPROVED`.
   This is intentionally a status change + relabel: the DRAFT label is
   load-bearing — the import command refuses to write into a
   non-DRAFT dataset, and the verify script asserts the DRAFT one
   stays DRAFT.
3. **Create the FR `CalculationFormula`** with the schema above and
   `status=APPROVED`. Same gating: only an APPROVED formula on an
   APPROVED dataset on an APPROVED source can run.
4. **Smoke test calculator FR** with at least one age × disability ×
   fault tuple committed in `apps/calculators/test_*.py`. The test
   should match the IT 35/10/0 = 26 268 / 27 353 / 28 439 EUR contract
   in spirit: a single canonical tuple, no real-value drift, locked.
5. **Mapping Dintilhac** of the postes de préjudice (`fr-nomenclature-dintilhac-2005`,
   already `needs_review` in DB) — needed to translate the calculator's
   output into the report-layer postes the user sees.

The Gazette du Palais 2022 capitalisation table follows the same
chain but for a separate calculator scope (rente / pertes futures
capitalisation), not the DFP per-point amount.

---

## Cross-references

- Engine: `apps/calculators/engines/france.py`
- Service helpers: `apps/compensation/services.py`
- Tests: `apps/calculators/test_france_engine_inactive.py`
- Candidate dataset import: `apps/compensation/management/commands/import_france_candidate_datasets.py`
- Candidate dataset docs: `docs/legal_sources/FRANCE_CANDIDATE_DATASET_IMPORT.md`
- Source authentication: `docs/legal_sources/FR_BADINTER_OFFICIAL_SOURCE_VALIDATION.md`
- Manual attach pipeline: `docs/legal_sources/MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md`
- Legal review packages: `docs/legal_sources/FRANCE_LEGAL_REVIEW_PACKAGE.md`
