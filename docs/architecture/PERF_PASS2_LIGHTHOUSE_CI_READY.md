# Public-funnel audit — pass 2 (Lighthouse CLI ready, CI-ready)

Iter: F-perf-pass2-lighthouse-cli-and-ci-ready.
Date: 2026-05-04.
Scope: harden the audit harness so it can run the real Lighthouse CLI
when available, fall back deterministically when it isn't, and be wired
into CI without surprises. **No** changes to legal data, calculator
engines, country activation status, or Italian dataset.

## 1. canonical entrypoint

`scripts/run_public_lighthouse_audit.py` is the single canonical
entrypoint. The repository does **not** have a `package.json` and
pass-2 deliberately does not introduce node tooling — the audit is a
pure-Python script that shells out to `lighthouse` only when a binary
is already on PATH (no network install).

If/when we adopt npm tooling later (e.g. for Tailwind build), an npm
script alias can be added on top of the python entrypoint, without
changing the script's contract.

## 2. local run

The dev server we leave live across iters is the audit target:

```
http://127.0.0.1:48107/
```

If it is not running, bring it up first:

```powershell
# from the repo root
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:48107 --noreload
```

(Pick another free port if 48107 is taken; pass it through with
`--base-url http://127.0.0.1:<port>`.)

Run the audit:

```powershell
python scripts/run_public_lighthouse_audit.py `
    --base-url http://127.0.0.1:48107 `
    --mode auto `
    --out-dir docs/reports/lighthouse/public_site_pass2
```

Outputs:

- `docs/reports/lighthouse/public_site_pass2/audit.json` — raw audit.
- `docs/reports/lighthouse/public_site_pass2/summary.md` — markdown
  table.
- `docs/reports/lighthouse/public_site_pass2/lighthouse/<slug>.{json,html}`
  — only when the real Lighthouse CLI runs.

## 3. CLI flags

| Flag | Default | Meaning |
| --- | --- | --- |
| `--base-url` | `http://127.0.0.1:48107` | URL prefix prepended to each path in `audited_urls`. |
| `--out-dir` | `docs/reports/lighthouse/public_site_pass1` | Directory where `audit.json` + `summary.md` (and per-URL lighthouse reports) are written. Relative paths are resolved against the repo root. |
| `--mode` | `auto` | `auto` → lighthouse if available, else playwright fallback. `lighthouse` → require lighthouse on PATH (exit 2 otherwise). `playwright` → force the structural fallback. |
| `--fail-on-warning` | `false` | Promote warning-level threshold violations to failures. Off by default — performance scores are too host-dependent until the CLI version is pinned. |
| `--force-fallback` | — | Deprecated alias for `--mode playwright`. Still accepted for pass-1 compatibility. |
| `--report-json` | — | Deprecated. Writes a second copy of `audit.json` at the requested path. |

## 4. exit codes

| Code | Meaning |
| ---: | --- |
| `0` | Every required rule passes. |
| `1` | At least one required rule failed (a11y / SEO / best-practices below threshold, or a structural fallback failure). |
| `2` | Configuration error — missing thresholds file, no audited URLs, `--mode lighthouse` with no CLI on PATH, Playwright not installed, etc. |

## 5. CI wiring

Live at `.github/workflows/public-site-audit.yml` (added in
F-ci-public-site-audit-workflow). Triggers: `pull_request` and
`workflow_dispatch`. The job spins up the Django dev server on
`127.0.0.1:48107`, polls `/healthz/`, runs the audit in
`--mode playwright`, and uploads the report directory as the
`public-site-audit` artifact.

### Why `--mode playwright` in CI

We deliberately do **not** rely on the Lighthouse CLI in CI yet:

- The CLI ships a moving target (Chrome version, audit weights) — a
  minor upgrade can shift scores by ±5 points without any code
  change, which would gate PRs on noise.
- We have no pinned Lighthouse version in the repo (no
  `package.json`).
- The structural fallback already enforces the regressions we
  actually want to gate on (missing H1, missing meta, leaking API
  keys, surfacing Pexels attribution, horizontal overflow on a 375 px
  viewport, every `<img>` carrying `alt` + `width` / `height`).

### Migrating to `--mode lighthouse`

Once the CLI is pinned (e.g. via a future `package.json` devDep or a
`tools/install_lighthouse.{sh,ps1}`), bump the workflow to:

```yaml
- name: Run public-funnel audit
  run: |
    python scripts/run_public_lighthouse_audit.py \
      --base-url http://127.0.0.1:48107 \
      --mode lighthouse \
      --out-dir docs/reports/lighthouse/ci_public_site
```

The script will exit 2 if the binary disappears — exactly the
behaviour you want for a CI gate.
`--fail-on-warning` is the additional lever to also fail on
performance-score regressions; keep it off until the runner CPU
profile is stable.

### How to read the artefacts

After the job finishes, download the `public-site-audit` artifact
(retention: 14 days). It contains:

- `audit.json` — raw audit (the same shape the CLI prints to stdout).
- `summary.md` — markdown table; paste-friendly into the PR review.
- `lighthouse/<slug>.{json,html}` — only when `--mode lighthouse` runs.

### Safety env in CI

The workflow sets the following environment variables to keep the
job fully self-contained:

| Env var | Value | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | `true` | Avoids prod-hardening start-up checks. |
| `DJANGO_SECRET_KEY` | dummy CI value | Required when `DEBUG=True`; never reused. |
| `DJANGO_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Locks the audit to the in-job server. |
| `PEXELS_ENABLED` | `false` | Disables the Pexels image flow — no key needed, no external fetch. |
| `LEAD_NOTIFICATION_ENABLED` | `false` | Stops the contact form trying to email anyone. |
| `SENTRY_DSN` | empty | No telemetry to external services. |
| `ADMIN_MFA_REQUIRED` | `false` | Avoids loading the MFA admin guard in CI. |

## 6. policy: warning vs required

Source of truth: `config/public_lighthouse_thresholds.json`
(`_schema_version: 2`).

- **required** — fails the audit:
  - Lighthouse: accessibility ≥ 0.90, best-practices ≥ 0.90, SEO ≥
    0.90.
  - Playwright fallback rules (HTTP 200, title, meta description,
    single H1, no horizontal overflow at 375 px, img alt + width /
    height, no Pexels attribution, no API key leak).
- **warning** — logged but never gates:
  - Lighthouse performance ≥ 0.70 (until the CLI version is pinned).

## 7. why fallback ≠ real perf metrics

The Playwright fallback is a structural audit: it confirms the page
ships with the right semantics (`<title>`, `<h1>`, alt, dimensions,
no leaks). It does **not** measure LCP / CLS / TBT / TTI — those are
runtime metrics that need the Lighthouse engine (or a Chrome DevTools
Protocol-driven measurement) plus a stable host CPU profile. Treat
fallback runs as "regression net" for shipping — and the lighthouse
runs as "perf measurement" for tuning.

## 8. last run (live, pass-2)

| Tool | URL | Verdict |
| --- | --- | :-: |
| playwright_fallback | `/` | PASS |
| playwright_fallback | `/countries/` | PASS |
| playwright_fallback | `/countries/italy/` | PASS |
| playwright_fallback | `/wizard/` | PASS |
| playwright_fallback | `/wizard/it/road-accident/` | PASS |
| playwright_fallback | `/wizard/fr/road-accident/` | PASS |
| playwright_fallback | `/contact/` | PASS |
| playwright_fallback | `/methodology/` | PASS |

Source: `docs/reports/lighthouse/public_site_pass2/{audit.json,summary.md}`.

## 9. validation

- `python manage.py makemigrations --check` — no new migrations.
- `python manage.py check` — 0 issues.
- `pytest -q` — green.
- `ruff check .` — clean.
- `black --check .` — clean.

## 10. summary

| Verdict | Detail |
| --- | --- |
| Audit | OK on all 8 URLs (Playwright fallback). |
| Italia | 35/10/0 → 26 268 / 27 353 / 28 439 EUR — unchanged (smoke test passing). |
| Other countries | FR/BE/MA/TN remain inactive. |
| Server | Live on `127.0.0.1:48107`. |
| Tools added | `--out-dir`, `--mode {auto,lighthouse,playwright}`, `--fail-on-warning`, audit.json + summary.md always emitted, exit 2 on `--mode lighthouse` without CLI. |
