# Local quality gate — runbook

**Iter**: F-p1-qa-1-quality-gate
**Date**: 2026-05-11

One wrapper, four stages: this document describes
`scripts/run_quality_gate.{sh,ps1}` — the single command a developer
runs before opening / merging / shipping a change.

The gate composes existing tooling, **adds no new test surface**, and
fails fast on the first stage that exits non-zero.

---

## 1. What the gate runs

In order, with fail-fast:

| # | Stage | Command | Time | Why |
|---|-------|---------|------|-----|
| 1 | Django system checks | `python manage.py check` | ~1 s | Catches missing migrations, broken settings, every `core.*` / `crm.*` / `compliance.*` check that blocks production. |
| 2 | Test suite | `pytest -q` | ~3 min | The 1800+ tests that pin behaviour. |
| 3 | Deontological content hygiene | `python scripts/audit_legal_content_hygiene.py --strict` | ~1 s | Six categories of prohibited public phrasing (see `docs/qa/PUBLIC_CONTENT_HYGIENE.md`). |
| 4 | Lighthouse desktop | `bash scripts/run_lighthouse_local.sh` (or `.ps1`) | ~2 min | Perf ≥ 0.80, a11y/best/seo ≥ 0.90 on the indexable URLs (see `docs/qa/LIGHTHOUSE_CI.md`). |

Total wall-clock on a current dev box: **~5 minutes**.

The wrapper prints a section header per stage and a per-stage
duration; the final line reports total elapsed time + pass/fail.

---

## 2. When to use it

| Scenario | Run the gate? |
|---|---|
| Before opening a PR | yes (skip Lighthouse with `--no-lighthouse` if iterating fast — but run the full gate before review). |
| Before merging to `audit/indennizzati-platform` | yes — full gate. |
| Before tagging / cutting a release | yes — full gate; if any step fails the release stops. |
| Inner loop, exploring a bug | only stage 1 + 2: `bash scripts/run_quality_gate.sh --no-lighthouse` (typical) or run pytest alone. |
| Tweaking docs / NOTES only | no — content hygiene + a sanity `pytest` is plenty. |

---

## 3. Requirements

- A Python venv at `.venv/` with the project dependencies installed.
  The wrapper auto-`source`s `.venv/Scripts/activate` (Windows) or
  `.venv/bin/activate` (Linux/macOS) if it isn't already active.
- Node.js + npm on PATH (Lighthouse uses `npx lighthouse@latest` —
  no committed `node_modules/`).
- For stage 4: a Django dev server already listening on
  `127.0.0.1:8000`. The wrapper does NOT start the server itself —
  see §5.

---

## 4. Flags

| Flag | Effect |
|---|---|
| `--no-lighthouse` (bash) / `-NoLighthouse` (PowerShell) | Skip stage 4. Useful for inner-loop runs where you'll do the Lighthouse pass once at the end. |
| `--no-pytest` (bash) / `-NoPytest` (PowerShell) | Skip stage 2. Rare — typically only when running the gate from an environment that has already run pytest. |
| `--help` (bash) | Print usage. |

---

## 5. Why the wrapper does NOT start the dev server

On Windows the Lighthouse chrome-launcher races with `manage.py
runserver` reload: starting+killing the server from the same script
leaves orphan Python and Chrome processes behind. The wrapper takes
the cautious path:

1. Operator opens a **second terminal**.
2. `source .venv/Scripts/activate && python manage.py runserver 127.0.0.1:8000`.
3. Operator runs the gate.

If stage 4 finds the server unreachable, it exits 1 with a clear
hint to start the server (or pass `--no-lighthouse`).

---

## 6. Differences between the gate and Lighthouse alone

| | gate | Lighthouse alone |
|---|---|---|
| Catches missing migrations | yes (stage 1) | no |
| Catches broken settings (CSP, mandate, retention) | yes (stage 1) | no |
| Catches Django test regressions | yes (stage 2) | no |
| Catches deontology phrasing | yes (stage 3) | no |
| Catches perf / a11y / SEO regression | yes (stage 4) | yes |

The gate is the comprehensive local check. Lighthouse alone is the
front-end-only spot check.

---

## 7. Expected output

A successful run looks like:

```
============================================================
  [1/4] Django system checks: python manage.py check
============================================================
System check identified 1 issue (0 silenced).      # core.W001 STUDIO_* — dev-only warning

[OK] [1/4] Django system checks: python manage.py check (2 s)

============================================================
  [2/4] Test suite: pytest -q
============================================================
.............. 1795 passed, 1 skipped in 162.62s

[OK] [2/4] Test suite: pytest -q (162 s)

============================================================
  [3/4] Deontological content hygiene: --strict
============================================================
OK: no hygiene findings on the scanned surface.

[OK] [3/4] Deontological content hygiene: --strict (1 s)

============================================================
  [4/4] Lighthouse: bash scripts/run_lighthouse_local.sh
============================================================
[home-it] http://127.0.0.1:8000/
  scores  perf=1.00  a11y=0.97  best=1.00  seo=1.00
...
RESULT: all URLs cleared the gate.

[OK] [4/4] Lighthouse: bash scripts/run_lighthouse_local.sh (122 s)

============================================================
  ALL GATES CLEARED  (296 s total)
============================================================
```

---

## 8. Keeping `git status` clean

The gate regenerates the JSON files under
`docs/qa/lighthouse-baseline/` (stage 4 always overwrites them with
the fresh Lighthouse output). If your run was **informational only**
— i.e. you didn't intentionally re-baseline — discard the
working-copy drift:

```bash
git checkout -- docs/qa/lighthouse-baseline/
```

The wrapper prints a reminder when this drift is detected. The
`.lighthouseci/` scratch dir is already in `.gitignore`.

The other three stages do not touch tracked files. `pytest` writes
to `.pytest_cache/` (gitignored); the content-hygiene script writes
nothing unless `--json` is passed.

To **intentionally re-baseline** (e.g. after a Studio-approved
visual change that legitimately moves the scores): keep the regen,
inspect, update `docs/qa/lighthouse-baseline/SUMMARY.md` to match,
commit. See `docs/qa/LIGHTHOUSE_CI.md` §8.

---

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ModuleNotFoundError: No module named 'csp'` on stage 1 | venv not activated (bash subprocess picked up system Python). | The wrapper auto-activates `.venv/Scripts/activate`; if you see this, your venv path differs — activate manually before running. |
| `[SKIP] [4/4] Lighthouse — Django not responding on 127.0.0.1:8000.` | Dev server not running. | Open a second terminal, run `python manage.py runserver 127.0.0.1:8000`, then re-run the gate. Or pass `--no-lighthouse`. |
| `EPERM, Permission denied … lighthouse.XXXX` mid-stage 4 | chrome-launcher temp-dir cleanup race on Windows. | Benign — the JSON report is fully written before the cleanup attempt fires. The wrapper tolerates it. |
| Stage 4 fails with `[gate failed]` on one URL | Real regression. | Open the JSON in `docs/qa/lighthouse-baseline/<label>-desktop.json`, find the failing audit, fix the underlying issue (see `docs/qa/LIGHTHOUSE_CI.md` §6). |
| Stage 3 flags a phrase that is legitimate | False positive on a disclaimer phrasing. | Add a negated-form entry to `ALLOWLIST_PATTERNS` in `scripts/audit_legal_content_hygiene.py`, or use the inline `hygiene-ignore: <category>` marker (see `docs/qa/PUBLIC_CONTENT_HYGIENE.md` §6–7). |

---

## 10. Pre-commit hook (decision)

The repo does **not** ship a `.pre-commit-config.yaml`. Reason: the
gate's two heavy stages (pytest + Lighthouse) take long enough that
turning them into a pre-commit would slow down routine `git commit`.

Recommendation:

- Use the gate **before opening/merging** (manual / CI step), not on
  every commit.
- If a team member wants a faster check before every commit, they
  can add a personal pre-commit calling only stage 1 + stage 3:
  ```yaml
  # .pre-commit-config.yaml (personal — not committed)
  repos:
    - repo: local
      hooks:
        - id: django-check
          name: manage.py check
          entry: python manage.py check
          language: system
          pass_filenames: false
        - id: content-hygiene
          name: deontological hygiene
          entry: python scripts/audit_legal_content_hygiene.py
          language: system
          pass_filenames: false
  ```
  Each runs in ~1 s and gives 80% of the safety net at near-zero
  cost. This snippet is documented here, not committed, so the team
  can opt in without forcing the workflow on everyone.

---

## 11. Adding stages

The gate intentionally only runs the four production-blocking
checks the project ships today. When new stages emerge (e.g. a
future security scanner, a future schema migrator), add them via:

1. Implement the new check as a standalone script that exits
   non-zero on failure.
2. Add a new `run_stage "[N/M] …"` block in both
   `scripts/run_quality_gate.sh` and `scripts/run_quality_gate.ps1`.
3. Update §1 + §3 of this doc.
4. Update the smoke test in
   `apps/core/test_quality_gate_p1_qa_1.py` so the new stage's
   command surface is pinned.

Don't add stages that take more than 30 seconds without first
proposing them — the gate's value depends on its sub-5-minute
total.
