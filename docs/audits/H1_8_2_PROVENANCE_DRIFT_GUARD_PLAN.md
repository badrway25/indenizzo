# H1-8.2 — Provenance Drift Guard in CI — Plan

**Branch:** `feature/h1-8-2-provenance-drift-guard` (from `product/staging-readiness-p0` @ `774048d`).
**Date:** 2026-06-22.

> Goal: wire the H1-8.1 verifier into the quality pipeline so CI catches a
> non-reproducible IT canary or detectable legal-data drift — without changing
> any calculation and without becoming flaky.

## 1. What CAN be verified stably in CI

- **The IT canary reproduces** (35/10/0 → 26 268 / 27 353 / 28 439) given the
  canonical approved data — i.e. the *engine logic* hasn't drifted.
- **The verifier itself catches drift** (a tampered hash/row/formula → `drifted`
  → `--fail-on-drift` exits non-zero).

These run deterministically because the data is seeded by a **pytest fixture**
(synthetic, transaction-rolled-back — never a real-DB approval, never a
gitignored `legal_data` file). The guard runs the *real* command
(`verify_calculation_provenance --canary --fail-on-drift`) in-process.

## 2. What is NOT safe to verify in CI

- **The REAL approved DB data** (the production/staging `CompensationDataset`
  rows). A fresh CI checkout has an empty DB after `migrate` (no seed); the
  approved IT data is created from **gitignored** `legal_data` files via the
  import commands, which are absent in CI. So a raw `manage.py … --canary`
  shell step against the CI DB would fail for *lack of data*, not for drift —
  that is flaky/misleading. Verifying the real approved data belongs to a
  **periodic ops check** against the staging/prod DB (runbook), not the per-PR CI.

## 3. `--canary` vs `--all-calculated`

- `--canary`: controlled, synthetic 35/10/0 recompute (no PII), no persistence.
  Safe everywhere. **This is the CI guard.**
- `--all-calculated`: scans existing calculated simulations in the DB. Useful
  **locally/ops** where real simulations exist; in a fresh CI DB there are none
  (or none deterministic), so it is NOT used as the CI gate.

## 4. Why no personal data in CI

The verifier and the canary are PII-free by design (legal-data ids/labels/hashes
+ synthetic 35/10/0). The guard never touches `input_data` of real users. The
fixture inputs (35/10/0) are canonical synthetic values, not personal data.

## 5. Fail-closed without flakiness

- The guard is a **pytest test** run as a dedicated, named CI step in the
  existing Python-tests job. It seeds its own data → deterministic → not flaky.
- It is **not optional**: if the canary stops reproducing or the verifier stops
  detecting drift, the step (and the job) fail.
- It does NOT depend on Lighthouse/Chrome (the only known-flaky CI surface).
- It does NOT depend on gitignored assets or network.

## 6. Deliverables

- `apps/cases/test_provenance_drift_guard.py` — the guard: canary reproduces via
  the real command; a tampered scenario is caught (`--fail-on-drift` → exit≠0);
  empty-DB canary fails (documents why a raw real-DB step would be fragile).
- A named CI step `Provenance drift guard (canary)` in `ci.yml` running that file.
- `docs/audits/H1_8_2_PROVENANCE_DRIFT_GUARD.md` — operational runbook.

## 7. Limits

- The CI guard proves the **engine reproduces the canary from canonical data**;
  it does NOT prove the live approved DB is intact (that's the ops check).
- It does not replace legal review: a `reproducible` result only means the
  numbers still hash-match their snapshot, not that they are legally correct.
