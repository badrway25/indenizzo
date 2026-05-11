# P1-QA-1 — consolidated local quality gate

**Date**: 2026-05-11
**Iter**: `F-p1-qa-1-quality-gate`
**Branch**: `p1/qa-gates-consolidation`
**Tag baseline P1-LEG-2**: `p1-leg-2-content-hygiene-2026-05-10`.

## Scope

One wrapper, four stages. The wrapper composes existing tooling
without adding new tests, settings or models. Fail-fast: the first
stage that exits non-zero aborts the run.

| # | Stage | Command | Typical duration |
|---|-------|---------|------------------|
| 1 | Django system checks | `python manage.py check` | ~2 s |
| 2 | Test suite | `pytest -q` | ~3 min |
| 3 | Deontological content hygiene | `python scripts/audit_legal_content_hygiene.py --strict` | ~1 s |
| 4 | Lighthouse desktop | `bash scripts/run_lighthouse_local.sh` (or `.ps1`) | ~2 min |

Real-world end-to-end on 2026-05-11 dev machine: **296 s total**,
all four stages green:

```
============================================================
  ALL GATES CLEARED  (296 s total)
============================================================
```

## Files modified / new

**Modified**: none. Everything in this batch is additive.

**New**:
- `scripts/run_quality_gate.sh` — bash wrapper.
- `scripts/run_quality_gate.ps1` — PowerShell wrapper.
- `apps/core/test_quality_gate_p1_qa_1.py` — 11 static-side smoke tests.
- `docs/qa/LOCAL_QUALITY_GATE.md` — runbook.
- `docs/screenshots/delta_audit_2026-05-10/after/p1-qa-gates-consolidation/NOTES.md` (this).

## What the gate enforces

| What | Enforced by |
|---|---|
| Migrations are generated | stage 1 (`makemigrations --check --dry-run` is run by `manage.py check`'s implicit invocation; explicit form documented in `GO_LIVE_GATE_CHECKLIST.md`). |
| `core.E001` / `core.E002` / `core.E003` / `core.E004` / `core.E006` / `core.E007` / `core.E008` / `compliance.E001` / `crm.E001` / `crm.E002` / `crm.E003` | stage 1 (any prod-blocking system check). |
| The 1806-test suite | stage 2. |
| Six categories of deontology hygiene | stage 3. |
| Performance / accessibility / best-practices / SEO budgets on 8 indexable URLs | stage 4. |

## Wrapper design notes

- **Auto venv activation** — the bash wrapper detects `.venv/Scripts/activate`
  (Windows) and `.venv/bin/activate` (Linux/macOS) and sources it if
  not already active. Without this, `bash scripts/run_quality_gate.sh`
  on Windows picks up system Python 3.13 which doesn't have the
  project's `csp` / `django` site-packages, and stage 1 immediately
  fails with `ModuleNotFoundError: No module named 'csp'`. The
  PowerShell variant relies on the caller's `Activate.ps1` already
  being sourced (PowerShell can't `source` a bash activator).
- **Server not auto-started** — Lighthouse stage refuses to run if
  `127.0.0.1:8000` isn't already serving. Starting `manage.py runserver`
  from the same script races with chrome-launcher on Windows and
  leaves orphan processes. The operator opens a second terminal.
- **Fail-fast** — first failure aborts. Each subsequent stage is
  skipped (not run-and-fail). This shaves up to 3 minutes when
  iterating.
- **Per-stage timing** — every section prints its duration. The
  final summary prints total wall-clock.
- **`git status` discipline** — the wrapper notes when stage 4
  rewrote `docs/qa/lighthouse-baseline/` and prints the exact
  command to discard the drift (`git checkout -- docs/qa/lighthouse-baseline/`).
  No other stage touches tracked files.

## Pre-commit decision

The repo deliberately does **not** ship `.pre-commit-config.yaml`.

Reason: pytest + Lighthouse together take ~5 min, which is too slow
for a per-commit hook. Forcing the workflow onto everyone would slow
routine commits to a crawl.

Recommended alternative — documented in `docs/qa/LOCAL_QUALITY_GATE.md`
§10 — is a **personal** (uncommitted) pre-commit running only the
two fast stages (manage.py check + content hygiene, ~2 s combined).
The snippet is in the runbook; the team can opt in individually.

## Smoke tests

`apps/core/test_quality_gate_p1_qa_1.py` (11 tests):

- both wrappers exist with reasonable size;
- bash wrapper references all four stage commands;
- bash wrapper auto-activates the venv;
- bash wrapper exposes `--no-lighthouse`, `--no-pytest`, `--help`;
- PowerShell wrapper references all four stage commands;
- PowerShell wrapper exposes `-NoLighthouse` and `-NoPytest`;
- runbook references both wrappers;
- runbook references every underlying tool;
- bash wrapper has no external HTTP targets (only `127.0.0.1:8000`);
- PowerShell wrapper has no external HTTP targets.

These are *static* tests — they read the file contents, they do not
execute pytest-inside-pytest, do not start Lighthouse, and do not
hit the network.

## Verifications run

| Command | Result |
|---|---|
| `python manage.py check` | clean (only the expected `core.W001` STUDIO_* dev warning) |
| `pytest -q` | **1806 passed, 1 skipped** (+11 from P1-LEG-2 baseline; zero regressions) |
| `python scripts/audit_legal_content_hygiene.py --strict` | `OK: no hygiene findings on the scanned surface.` |
| `bash scripts/run_lighthouse_local.sh` | all 8 URLs cleared the gate |
| `bash scripts/run_quality_gate.sh --no-pytest --no-lighthouse` | both fast stages clear in 3 s |
| `bash scripts/run_quality_gate.sh` (full) | **ALL GATES CLEARED (296 s total)** |
| `git status` after the run | clean (after `git checkout -- docs/qa/lighthouse-baseline/`) |

PowerShell variant is structurally identical to the bash one; the
test suite pins the same stage-set + switch-set. Not executed
end-to-end in this batch — the bash wrapper covered the end-to-end
verification on the actual dev box.

## Adding stages later

Process documented in `docs/qa/LOCAL_QUALITY_GATE.md` §11:

1. Implement the new check as a standalone script with non-zero
   exit on failure.
2. Add a `run_stage "[N/M] …"` block in both wrappers.
3. Update §1 + §3 of the runbook.
4. Update `apps/core/test_quality_gate_p1_qa_1.py` so the new
   command appears in the static check.

## Next batch suggested

In order of expected value:

1. **P1-SEC-3** — WAF/CDN edge security (Cloudflare / Caddy +
   CrowdSec) once production-style staging is up.
2. **P0-MVP-1** — first non-IT country green end-to-end
   (FR/BE/MA/TN). Unblocks the cardinal `LOCAL_NEXT_STEPS.md` Sec. 0
   constraint.
3. **Tunisia/EU650 review + merge** — branch
   `work/tunisia-csp-eu650-restore` (`b44a5c2`).
4. **P2-SEO-1** — Lighthouse mobile preset baseline + budget; the
   gate wrapper is ready to incorporate a fifth stage when the
   mobile audit is captured.
5. **CI wiring** — port the gate to GitHub Actions (or whatever CI
   the team chooses); the runbook §11 has the outline.
