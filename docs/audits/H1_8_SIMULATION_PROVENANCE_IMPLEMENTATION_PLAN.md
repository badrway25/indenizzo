# H1-8 — Simulation Calculation Provenance — Implementation Plan

**Branch:** `feature/h1-8-simulation-calculation-provenance` (from `product/staging-readiness-p0` @ `73b849c`).
**Date:** 2026-06-22.
**Design:** Option A — deterministic JSON provenance snapshot (per the brief's preference).

> Goal: every CALCULATED `Simulation` records *which* dataset version, source
> version + content hash, formula, and table rows produced its amounts — so the
> estimate is auditable and re-derivable even after the underlying legal data
> evolves. No change to engines, formulas, amounts, or the IT canary.

---

## 1. What is already saved today

- `Simulation.output_data` (JSONField): full `CalculationResult.to_dict()` —
  estimated_min/mid/max, breakdown, **sources snapshot**, assumptions, warnings,
  missing_documents, confidence, legal_disclaimer.
- `Simulation.sources_snapshot` (JSONField): immutable `SourceRef` list.
- `Simulation.estimated_min/mid/max`, `status`, `confidence`, `currency`.
- `SimulationEvent` (append-only): `event_type="computed"` with small metadata.
- `BreakdownItem.notes` already mentions the matched `CompensationTableRow id=…`
  and `formula '<code>'` (free text — not structured/queryable).

## 2. What is missing

A **structured, queryable** record of the calculation inputs on the legal-data
side: dataset id + `version_label`, `source_version_id` + `content_hash`,
formula id + `code` + a hash of its parameters, and the exact matched table rows
(ids + monetary value hashes). Today this is only in free-text `notes`.

## 3. Where provenance is built and saved

- **Built in the engine** (`apps/calculators/engines/italy.py`), at the two
  CALCULATED return points (single-row ~L286, range ~L451), where `dataset`,
  `formula`, the matched row(s) and `range_dataset` are already in scope. A new
  pure helper `apps/calculators/provenance.py::build_calculation_provenance(...)`
  assembles the dict from those objects. **No amount/logic change** — it only
  reads identifiers already materialised.
- **Carried** on `CalculationResult.provenance` (new optional dataclass field).
  Kept **out of `output_data`** so existing readers/tests are unaffected.
- **Persisted** in `apps/cases/services.py::_apply_result_to_simulation`: when
  `status == calculated` and `result.provenance` is present, write
  `simulation.calculation_provenance = {**result.provenance, "calculated_at": <iso>}`.
  Otherwise the field stays `{}` (fail-closed — no fake provenance).

## 4. Provenance payload (deterministic, PII-safe)

```json
{
  "schema_version": 1,
  "engine": "italy_tun_point_value_v1",
  "engine_version": "italy-1.0",
  "amount_rule": "row_amount_range_direct",
  "dataset": {
    "id": 1, "version_label": "DPR-12-2025", "status": "approved",
    "source_id": 1, "source_version_id": 1, "source_version_label": "DPR-12-2025",
    "source_content_hash": "74d4d4f7…", "source_version_present": true
  },
  "range_dataset": { "id": 2, "version_label": "DPR-12-2025-MORAL", "...": "..." },
  "formula": { "id": 1, "code": "italy_art_138_…", "params_hash": "<sha256>" },
  "table_rows": [
    { "id": 123, "row_type": "…", "age_min": 35, "age_max": 35,
      "disability_min": 10, "disability_max": 10, "value_hash": "<sha256>" }
  ],
  "calculated_at": "2026-06-22T…Z"
}
```

- **No user PII**: the victim's inputs are NOT duplicated here (they already live
  in `Simulation.input_data`). Reproducibility = `input_data` (stored) +
  provenance (legal-data side). Row `age_min/max` etc. are *table bands*, not the
  user's data.
- **No secrets / `.env` / tokens / health data.**
- `params_hash` = SHA-256 of canonical-JSON `formula.parameters`.
- `value_hash` = SHA-256 of the row's monetary value(s) (`point_value` / `extra`
  amounts) — detects in-place edits of an approved row.
- `source_version_present` is honest: when an approved dataset has no
  `source_version` (e.g. legacy/test fixtures), it is recorded `false` with
  `source_content_hash: null` — **not faked, not failed** (the canary fixture's
  approved dataset has no source_version; failing would break it).

## 5. Migrations

One migration adding `Simulation.calculation_provenance = JSONField(default=dict,
blank=True, null=False)`. Additive, nullable-free with a default → safe on
existing rows (they get `{}`). No data migration. Reversible (RemoveField).

## 6. JSON vs FK

JSON snapshot (Option A) chosen over a relational `CalculationProvenance` model
because: (a) it stays valid when datasets/sources later change or are deleted
(snapshot, not live FK); (b) historical audit must be immutable; (c) it mirrors
the existing `output_data`/`sources_snapshot` pattern; (d) no FK churn. A
relational model would re-introduce the very coupling we want to snapshot away
from.

## 7. SQLite / PostgreSQL compatibility

`JSONField` with `default=dict` is fully supported on both (Django 5.2 native
`JSONField`). No backend-specific features. The migration is a plain `AddField`.

## 8. Historical simulations

Provenance is **additive** and written only for NEW calculated simulations.
Existing simulations keep `calculation_provenance == {}`. Result page / PDF show
the provenance block **only when present** (`{% if … %}` / `.get()` guards), so
legacy simulations render unchanged. No back-fill.

## 9. Rollback

`migrate cases <prev>` drops the column (RemoveField). The engine/service code
degrade gracefully (provenance simply not persisted). Reversibility tested by
rollback + re-apply.

## 10. Result page / PDF / Admin

- **Result page**: a small, optional "Calcolo tracciato e riproducibile" block
  (source version label + abbreviated content hash + calculated date), guarded
  on `has_estimate` AND provenance presence; i18n via `{% translate %}`. Never
  dumps raw JSON.
- **PDF**: an optional provenance line in the report (labels via the existing
  `apps/reports/labels.py` 4-language dict, not gettext, per that file's policy).
- **Admin**: `calculation_provenance` added read-only to `SimulationAdmin`.

## 11. Risks

- Engine edit near the canary path → mitigated: provenance builder is pure,
  defensive (never raises), and does not touch amounts; canary asserted unchanged.
- `source_version` absent on legacy approved datasets → handled honestly
  (`source_version_present: false`), not faked, not failing.
- i18n: a few new IT strings on the result page → add to `it` `.po`; FR/AR get
  the source string until Studio translation (coverage gate already tolerates).
