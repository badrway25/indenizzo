# H1-10 — CI/Ops Hardening: Lighthouse stability + provenance ops check — Plan

**Branch:** `feature/h1-10-ci-ops-hardening` (from `product/staging-readiness-p0` @ `ed6f038`).
**Date:** 2026-06-22.

> Infra-only phase. No engine/formula/amount/approved-source/source_version
> change. Goal: stop the recurring Lighthouse-desktop flake (PRs #4/#5/#8 went
> green only after a manual re-run) and give ops a documented, PII-safe drift
> check against a real DB.

## Scope A — Lighthouse desktop flakiness

**Root cause.** The gate runs `scripts/run_lighthouse_local.sh`, which per URL
calls `npx lighthouse@latest --chrome-flags="--headless --no-sandbox"`. When
Chrome fails to launch / crashes during temp-dir handling (a known CI flake),
**no JSON is written** and the script immediately `exit 3`s. There is **no
retry**, and it lacks the single most important CI-stability flag
`--disable-dev-shm-usage` (the default 64 MB `/dev/shm` on CI runners makes
headless Chrome crash). The CI logs matched this exactly: "No files were found …
artifacts/lighthouse/latest/" + orphaned `chrome` processes.

**Fix.** In `run_lighthouse_local.sh` (and the twin mobile script):
1. More stable Chrome flags: add `--disable-dev-shm-usage --disable-gpu`.
2. A controlled retry (max 2 attempts) around **report collection only** — i.e.
   retry only when no valid Lighthouse JSON was produced (Chrome/infra flake),
   killing leftover Chrome processes between attempts.
3. The **gate** (the Python score check) stays **single-shot, never retried** —
   a real budget miss is still a hard failure. This is the key invariant: retry
   the flake, never the verdict.
4. Clear log messages distinguishing a transient retry from a real gate failure.
5. Artifacts/logs are still uploaded on failure (the workflow already uses
   `if: always()` on the upload step).

**Not done:** no `continue-on-error`, no removal/skip of the gate, no relaxed
budgets, no bypass. The gate stays serious; only infra flakiness is absorbed.

## Scope B — Provenance ops drift check

`verify_calculation_provenance --all-calculated --fail-on-drift` is the ops
check. It must NOT run as a per-PR gate (a fresh CI DB is empty → on real data
it would be meaningless). Instead:

- A **manual** `workflow_dispatch` workflow `Provenance ops drift check` that
  never auto-triggers. It runs the command read-only and PII-safe.
- It reads `DATABASE_URL` from a repo/environment secret (`OPS_DATABASE_URL`).
  With a real (read-replica recommended) staging/prod DB it does a real check;
  with no secret it runs against an ephemeral empty DB (migrated locally) and is
  a no-op pass — documented, not fragile, never touching a real DB's schema.
- `--skip-checks` avoids the go-live STUDIO_* system-check gate (irrelevant to a
  read-only drift check) under prod-like settings.
- A runbook documents prerequisites, reading the output, and reacting to drift.

## Compatibility / safety

- Bash scripts: POSIX-ish, run on the ubuntu-latest runner. Validated with
  `bash -n`. The retry uses `pkill`/`sleep` (present on the runner).
- The ops workflow is valid YAML, manual-only, and never migrates a real DB.
- No PII: the verify command is PII-free by design; the workflow prints no
  secrets (`DATABASE_URL` is referenced via `${{ secrets.* }}`, never echoed).

## Tests

- `bash -n` on both lighthouse scripts.
- YAML validation of the new + edited workflows.
- A static guard test asserting the lighthouse runner keeps the retry + stable
  flags (so the hardening can't silently regress) and that the gate stays
  single-shot.
- The standard gate (check / migrations / verify canary / coverage / canary /
  full suite) stays green.

## Risks

- The retry can mask a *consistently* failing Chrome only if it fails the same
  way twice — then the job correctly stays red. A genuinely flaky run (fail then
  pass) is absorbed, which is the intent.
- The ops workflow is only as useful as the DB the operator points it at; with
  no secret it is a documented no-op.
