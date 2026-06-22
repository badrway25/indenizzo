# Provenance Drift Guard — Runbook (H1-8.2)

Operational guide for the calculation-provenance verifier
(`verify_calculation_provenance`, H1-8.1) and its CI guard (H1-8.2).

> *Meglio nessun calcolo che un calcolo falso.* This guard is a safety net, not
> a substitute for legal review.

## 1. What it does

Re-derives the legal-data provenance of CALCULATED simulations from the CURRENT
DB and compares it to the snapshot stored at calculation time (H1-8). It tells
you whether a stored estimate is still **reproducible** or whether the legal
data underneath it has **drifted**. Read-only, PII-safe.

## 2. How to run it manually

```bash
# IT canary: does 35/10/0 still reproduce 26 268 / 27 353 / 28 439?
python manage.py verify_calculation_provenance --canary

# Verify every calculated simulation in this DB (local/staging/prod):
python manage.py verify_calculation_provenance --all-calculated

# Canary + all, JSON, written to a file:
python manage.py verify_calculation_provenance --canary --all-calculated --format json --output report.json

# Gate mode for scripts/cron: non-zero exit on drift or canary failure:
python manage.py verify_calculation_provenance --canary --all-calculated --fail-on-drift
```

Flags: `--simulation <uuid>`, `--all-calculated`, `--limit N`, `--format
text|json|markdown`, `--output <path>`, `--fail-on-drift`, `--include-legacy`,
`--canary`.

## 3. Reading the statuses

| status | meaning | action |
|---|---|---|
| `reproducible` | every hash matches the current legal data | none |
| `drifted` | the legal data changed under a historical estimate | **investigate** (see §5) |
| `incomplete` | the snapshot itself lacks structure / unsupported schema | check how it was recorded |
| `legacy_no_provenance` | calculated before H1-8, no snapshot | informational; not a failure |
| `not_calculated` | the simulation never produced an estimate | none |

## 4. When to use `--fail-on-drift`

Use it whenever you want a **gate** (CI step, cron job, pre-promotion check):
the command exits non-zero on any `drifted` result or a failing canary. It does
NOT fail on `legacy_no_provenance` or `not_calculated`.

## 5. What to do if it reports drift

A `drifted` result means the approved dataset / source version / formula / table
row that produced a stored estimate no longer hash-matches. It does **not** mean
the historical estimate was wrong — it is the record of what was computed then.
Steps:

1. Run `--simulation <uuid>` to see which checks failed (source hash, a row
   value, the formula params, or a deleted/unapproved object).
2. Decide whether the legal data *should* have changed (a legitimate new
   edition) or whether it was changed *by mistake* / in place.
3. If legitimate: new simulations will use the new data; the historical ones
   keep their provenance and read as `drifted` — that is correct and auditable.
4. If a mistake: restore the data; re-run until `reproducible`.

## 6. Use it BEFORE promoting new legal sources

Before approving/promoting a new source or editing an approved dataset, run
`--canary --all-calculated --fail-on-drift` so you know the change does not
silently break existing reproducibility. Treat a new `drifted` as a stop.

## 7. PII safety

The verifier reads only legal-data ids/labels/hashes/statuses and synthetic
canary inputs (35/10/0). It never reads or prints `input_data`, victim data,
health data, IP or user. The result carries `pii_safe: true`. Safe to paste into
tickets and logs.

## 8. The CI guard (H1-8.2)

CI runs `apps/cases/test_provenance_drift_guard.py` as a dedicated, fail-closed
step in the Python-tests job. It seeds the canary via a fixture (synthetic,
rolled back — never a real approval, never a gitignored file) and runs the real
command. It fails if the IT canary stops reproducing or the verifier stops
detecting drift.

**Scope of the CI guard:** it verifies the **engine reproduces the canary from
canonical data** — i.e. the calculation logic hasn't drifted. It does NOT check
the live approved DB (a fresh CI checkout has no approved data; that data comes
from gitignored `legal_data` files). Verifying the **real approved DB** is a
periodic ops check: run `--all-calculated --fail-on-drift` against the
staging/prod DB on a schedule or before a release.

## 9. What it does NOT do

- It does not re-run legal review: `reproducible` only means the numbers still
  hash-match their snapshot, not that they are legally correct.
- It does not repair or re-stamp provenance.
- It does not recompute amounts from sensitive user input.
