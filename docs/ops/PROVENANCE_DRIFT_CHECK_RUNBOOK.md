# Provenance drift check — Ops runbook (H1-10)

How to verify that the legal data underneath stored **calculated** simulations
has not drifted, against a real (staging/prod) database. Builds on
`verify_calculation_provenance` (H1-8.1) and the per-PR canary guard (H1-8.2).

> *Meglio nessun calcolo che un calcolo falso.* This is a safety check, not a
> substitute for legal review. Read-only and PII-safe.

## 1. When to run it

- Before/after **promoting a new legal source** or editing an approved dataset.
- Before a **release** that touches legal data.
- On a **schedule** (e.g. weekly) to catch silent drift.
- Whenever the per-PR canary guard (H1-8.2) flags something.

## 2. How to run it

### Local / shell (against the env's configured DB)

```bash
# All calculated simulations in the current DB; non-zero exit on any drift.
python manage.py verify_calculation_provenance --all-calculated --fail-on-drift

# One simulation; JSON for tooling:
python manage.py verify_calculation_provenance --simulation <public_id> --format json

# Add the engine canary (needs the approved IT data present in that DB):
python manage.py verify_calculation_provenance --canary --all-calculated --fail-on-drift
```

PII-safe flags only — the command never reads or prints `input_data`, victim,
health, IP or user data. Safe to paste into a ticket.

### Manual GitHub Action — "Provenance ops drift check"

A `workflow_dispatch`-only workflow (`.github/workflows/provenance-ops-drift-check.yml`).
It NEVER auto-triggers and NEVER migrates a real DB.

**Prerequisites for a real check:**
1. Configure a repository or environment **secret `OPS_DATABASE_URL`** pointing
   at the staging/prod DB — use a **read replica** where possible (the check is
   read-only, but a replica removes all risk).
2. Run it from the **Actions** tab → "Provenance ops drift check" → *Run workflow*.

Without `OPS_DATABASE_URL` the job runs against an **ephemeral empty DB**
(0 simulations → no drift → passes). That is a documented no-op, not a real
check — set the secret for meaningful results.

## 3. Reading the output

Each simulation gets a status (see the H1-8.2 runbook for the full table):

| status | meaning |
|---|---|
| `reproducible` | all hashes match the current legal data |
| `drifted` | the legal data changed under a historical estimate — **investigate** |
| `incomplete` | the snapshot itself lacks structure |
| `legacy_no_provenance` | predates H1-8 (informational, not a failure) |
| `not_calculated` | nothing to verify |

`--fail-on-drift` exits non-zero on any `drifted` (or a failing canary); it does
NOT fail on `legacy_no_provenance` / `not_calculated`.

## 4. What to do if it reports `drifted`

1. Re-run `--simulation <public_id>` to see which checks failed (source hash, a
   row value, the formula params, or a deleted/unapproved object).
2. Decide whether the change was **legitimate** (a new approved edition — new
   simulations use the new data; old ones correctly read `drifted` and stay
   auditable) or a **mistake** (in-place edit of approved data — restore it and
   re-run until `reproducible`).
3. **Notify** the legal-data owner / Studio reviewer before any
   promotion/correction. Never "fix" a drift by editing provenance.

## 5. What NOT to do

- Do not run it as a blocking per-PR gate against the real DB (use the H1-8.2
  canary guard for per-PR).
- Do not migrate the real DB from this workflow (the workflow doesn't).
- Do not paste secrets or `DATABASE_URL` values into logs/tickets.
- Do not treat `reproducible` as legal correctness — it only means the numbers
  still hash-match their snapshot.

## 6. Limits

- Verifies the **legal-data inputs** (hashes/ids), not the arithmetic (covered
  by the engine tests + the canary).
- Only as useful as the DB it points at; with no `OPS_DATABASE_URL` it is a
  no-op.
