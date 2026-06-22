# H1-8.1 — Provenance Reproducibility Verification — Plan

**Branch:** `feature/h1-8-1-provenance-verification` (from `product/staging-readiness-p0` @ `ae550ca`).
**Date:** 2026-06-22.

> Goal: a **read-only** service + command that, given a calculated `Simulation`,
> re-derives the provenance hashes from the CURRENT DB and reports whether the
> result is still `reproducible` or has `drifted` — without exposing PII and
> without recomputing amounts from sensitive input.

## 1. What is verified

For a CALCULATED simulation carrying a provenance snapshot (H1-8), re-derive the
legal-data side from the current DB and compare to the stored snapshot:

- `simulation.status == "calculated"`,
- provenance present + `schema_version` supported + `engine`/`engine_version` present,
- dataset id still exists, still `approved`, same `version_label`,
- dataset's `source_version_id` + `source_content_hash` unchanged,
- formula id still exists, same `code`/`status`, same `params_hash`,
- each table row id still exists, same `value_hash`,
- `range_dataset` (when present) same as above,
- `calculated_at` present.

## 2. What is NOT verified

- **Amounts are NOT recomputed in the general command** — that needs the user's
  input (`input_data`), which can be sensitive. The verifier only checks the
  hash/identity of the legal-data side. Reproducibility of *amounts* is covered
  by `--canary` (synthetic 35/10/0 inputs, no PII) and by tests.
- No legal interpretation, no source authenticity, no network.

## 3. PII safety

The provenance snapshot is PII-free by H1-8 design (legal-data ids + hashes).
The verifier reads ONLY the snapshot + current legal-data objects; it never
reads or emits `input_data`, victim data, health data, IP, user. All output
(text/json/markdown) is derived from ids/labels/hashes/statuses only. The result
carries `pii_safe: true` as a contract marker, asserted by tests.

## 4. Statuses

| status | meaning |
|---|---|
| `not_calculated` | simulation status != calculated (nothing to verify) |
| `legacy_no_provenance` | calculated but `calculation_provenance == {}` (predates H1-8) — NOT a fatal error by default |
| `incomplete` | provenance present but missing required keys / unsupported schema |
| `drifted` | a re-derived hash/id/status differs, or a referenced object was deleted/unapproved |
| `reproducible` | every check matches the snapshot |

## 5. Legacy simulations

`legacy_no_provenance` is informational, not an error. `--include-legacy` lists
them; default summary counts them separately. `--fail-on-drift` does NOT fail on
legacy (only on `drifted`).

## 6. Missing dataset / source_version

- Dataset/formula/row id no longer in DB → that check fails → `drifted` (the
  inputs that produced the estimate are gone/changed).
- Snapshot recorded `source_version_present: false` (legacy approved dataset
  without a source version): the source-hash check is reported `skipped`
  (honest — there was never a hash to anchor), NOT a drift. This mirrors the
  H1-8 fail-closed-but-honest rule.

## 7. Drift vs incompleteness

- **incomplete** = the *snapshot* lacks structure (missing keys, unsupported
  schema_version) — a problem with how it was recorded.
- **drifted** = the snapshot is complete but the *current DB* no longer matches
  it — the legal data changed under a historical estimate.
These are distinct statuses so the Studio can tell "badly recorded" from
"data changed".

## 8. How re-derivation stays consistent with H1-8

The verifier reuses the exact hashing helpers from
`apps/calculators/provenance.py` (`_dataset_snapshot`, `_formula_snapshot`,
`_row_snapshot`) so a re-derived hash is byte-identical to how it was first
computed. No re-implementation of the hash logic (single source of truth).

## 9. Limits

- Verifies the *legal-data inputs*, not the arithmetic (covered by `--canary` +
  the engine's own tests).
- A drift means "re-verify needed", not "the historical estimate was wrong" —
  the stored estimate remains the record of what was computed at the time.
- Read-only: it never repairs or re-stamps provenance.

## 10. Deliverables

- `apps/cases/provenance_verifier.py` — pure `verify_simulation(sim) -> dict`.
- `verify_calculation_provenance` management command (`--simulation`,
  `--all-calculated`, `--limit`, `--format`, `--output`, `--fail-on-drift`,
  `--include-legacy`, `--canary`). Read-only, PII-safe.
- Admin: a read-only "provenance status" display + a read-only action (low risk).
- Tests for each status + PII-safety + `--fail-on-drift` exit code + canary.
