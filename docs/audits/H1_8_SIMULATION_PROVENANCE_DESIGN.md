# H1-8 — Simulation calculation provenance (design only)

**Status:** DESIGN. **Not implemented.** No schema/code change in this branch.
**Date:** 2026-06-22.

> Goal: make every CALCULATED `Simulation` provably reproducible — record which
> dataset/source version and which exact rows/formula produced the stored
> amounts, so a historical estimate can be re-derived and audited even after
> the underlying legal data evolves. Builds on the `source_version` work
> (stacked PR `feature/source-version-approved-datasets`).

---

## 1. Problem

Today a `Simulation` stores `output_data` (amounts, sources snapshot,
breakdown) but **not** a content-addressable link to the exact dataset version
and rows used. If an approved `CompensationTableRow.point_value` or a
`CalculationFormula.parameters` is later edited in place, an old simulation's
`estimated_*` can no longer be re-derived or proven against its inputs. Rows
are mutable; only the import command's DRAFT-overwrite discipline protects them.

## 2. What to capture (per CALCULATED simulation)

A small, append-only provenance record written when (and only when) a
simulation reaches `status == calculated`:

| Field | Source | Why |
|---|---|---|
| `dataset_id` + `dataset_version_label` | the approved `CompensationDataset` used | identify the table edition |
| `source_version_id` + `source_content_hash` | `LegalSourceVersion` (now linked to the dataset) | tie numbers to the authenticated document |
| `formula_code` + `formula_params_hash` | SHA-256 of canonical-JSON `CalculationFormula.parameters` | detect formula drift |
| `matched_rows_hash` | SHA-256 over the ordered (pk, point_value, daily_amount, coefficient, extra) of the rows actually read | detect row drift |
| `engine` + `amount_rule` | from the formula | which code path computed it |
| `computed_at` | timestamp (passed in, not generated in migration) | audit |

Storage options (decide at implementation time):
- **(A) New model** `apps.cases.SimulationProvenance` (OneToOne with
  `Simulation`, append-only, auditlog-registered). Cleanest; queryable.
- **(B) A `provenance` JSON block** inside `Simulation.output_data`. Cheaper, no
  migration, but not independently queryable/auditable.

Recommendation: **(A)** — consistent with the project's append-only audit
pattern (`ExtractionLog`, `LegalReview`, `SimulationEvent`).

## 3. Where to hook it

`apps/cases/services.py::_apply_result_to_simulation` already copies the
engine's `CalculationResult` onto the `Simulation` on the CALCULATED path. The
provenance record is written **there**, in the same transaction, ONLY when
`status == calculated`. The engine (`apps/calculators/engines/italy.py`)
already knows the dataset/formula/rows; it should surface their identifiers in
the `CalculationResult` (extend the dataclass with an optional `provenance`
payload) so the service can persist them without re-querying.

No engine math changes — only emitting identifiers already in hand.

## 4. Reproducible PDF report

The PDF (`apps/reports`) is generated from `Simulation.output_data` (never
recomputed). With provenance present, the PDF footer can cite the dataset
version label + source content hash, making the document self-describing. A
"verify" command could re-read the stored hashes and re-hash the current
rows/formula to report whether the estimate is still re-derivable
(`reproducible` / `drifted`).

## 5. Expired / replaced versions

- `LegalSourceVersion.valid_from/valid_to` already model vigency; the engine
  resolves the dataset valid at the fact date.
- Provenance stores the version actually used, so an estimate computed under an
  edition later `deprecated`/`replaced` remains explainable ("computed under
  DPR-12-2025, superseded on <date>").
- A new simulation always uses the currently-approved version; historical ones
  keep their recorded version. No back-fill of old simulations.

## 6. Not breaking historical simulations

- Provenance is **additive** and written only for NEW calculated simulations.
- Existing simulations (no provenance row) stay valid; the verify command
  reports them as `provenance: absent (legacy)` rather than failing.
- No change to `estimated_*`, no recompute, no migration of stored amounts.

## 7. Out of scope for H1-8

- Making `source_version` mandatory at DB level (separate deferred item).
- Multi-jurisdiction / cross-border provenance.
- Re-hashing the full 41k-row datasets on every calc (only the matched rows are
  hashed).

## 8. Acceptance criteria (when implemented in its own phase)

1. Every newly CALCULATED simulation has a provenance record.
2. A verify command re-derives the IT canary (26 268 / 27 353 / 28 439 €) from
   stored provenance and reports `reproducible`.
3. Editing an approved row in place makes the verify command report `drifted`
   for affected historical simulations (proving detection works).
4. No change to the canary, engine math, or existing simulations.
