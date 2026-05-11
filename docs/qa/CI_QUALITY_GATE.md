# CI quality gate — runbook

**Iter**: F-p1-ci-1-ci-quality-gate
**Date**: 2026-05-11

This runbook covers `.github/workflows/ci.yml` — the GitHub Actions
port of the local consolidated quality gate
(`docs/qa/LOCAL_QUALITY_GATE.md`).

The intent is **parity with the local gate, not a different gate**:
every check on a PR also runs locally via
`bash scripts/run_quality_gate.sh`. CI exists to enforce that the
local gate was honestly run, not to invent rules nobody can
reproduce.

---

## 1. Jobs

| # | Job | Trigger | Time | Blocks merge? |
|---|-----|---------|------|---------------|
| 1 | `python-tests` | `pull_request`, `push` to `main`, `workflow_dispatch` | ~3–5 min | **yes** |
| 2 | `production-checks` | `pull_request`, `push` to `main`, `workflow_dispatch` | ~1–2 min | **yes** |
| 3 | `lighthouse-desktop` | `pull_request`, `push` to `main`, `workflow_dispatch` | ~5–8 min | **yes** |
| 4 | `lighthouse-mobile` | `workflow_dispatch` **only** | ~6–10 min | manual |

The three blocking jobs run in parallel — total wall-clock for a PR
is the longest of the three (~8 min, bounded by `lighthouse-desktop`).
`production-checks` finishes in 1–2 min so it never widens the
critical path.

---

## 2. What each job runs

### `python-tests` — fast, deterministic checks (dev / test env)

Runs with `DJANGO_DEBUG=true` so the test suite exercises the
placeholder state (working-copy mandate, working-copy disclaimer,
etc.). The production-only system checks (`core.E001/E002/E003/E004/E006/E007/E008`,
`compliance.E001`, `jurisdictions.E001`) are skipped here — they
get their own job (see `production-checks` below) so the gate
verifies the deploy path with one eye, and the test path with the
other.

| Step | Command | Why |
|---|---|---|
| Django system check | `python manage.py check` | Catches missing migrations, broken settings, every error that fires in DEBUG=true. |
| Migrations | `python manage.py migrate --noinput` | Required so the next steps can hit the DB. SQLite in CI; the project supports Postgres in prod via `DATABASE_URL`. |
| Tests | `pytest -q` | The full ~1900 test suite. |
| Content hygiene | `python scripts/audit_legal_content_hygiene.py --strict` | Six categories of deontology phrasing (see `docs/qa/PUBLIC_CONTENT_HYGIENE.md`). |
| Non-IT readiness | `python scripts/legal_data/audit_non_it_readiness.py` | Verifies the FR/BE/MA/TN chain integrity: every APPROVED LegalSource must have a matching APPROVE LegalReview audit row. Exits 1 on `APPROVED-INCONSISTENT`. The system check `jurisdictions.E001` enforces the same contract in prod. |

### `production-checks` — production-like Django system check

Runs **`python manage.py check` only**, with `DJANGO_DEBUG=false`
and a complete set of plausible-shaped (but fictitious) signed env
values. The point is to exercise the production-blocking system
checks against the *real* code path that fires on deploy, instead
of accepting "they're skipped in CI, we'll find out in prod".

What it catches: a `core.W001` → `core.E001` promotion that breaks
because a new STUDIO_* field was added but not threaded through the
deploy gate. Same shape for CSP enforcing
(`core.E002/E003`), consent versions (`core.E004`), legal pages
signed (`core.E006/E007`), mandate signed (`core.E008`), retention
policy (`compliance.E001`), and non-IT chain (`jurisdictions.E001`).

| Step | Command | Why |
|---|---|---|
| Install deps | `pip install -r requirements.txt` | |
| Production-like Django check | `python manage.py check` | All env vars below are placeholders chosen to pass each check. If a new prod-blocking check lands and this job goes red, the deploy gate would fail too. |

**No real secret is present in this job.** Specifically:

- `DJANGO_SECRET_KEY` is a CI-only placeholder (50+ chars, no
  `django-insecure-` prefix so the runtime accepts it under
  DEBUG=false, but the value itself is not used to sign real
  sessions).
- `STUDIO_*` fields are placeholder names/numbers, not real Studio
  identity.
- `*_NOTICE_VERSION` / `*_POLICY_VERSION` / `MANDATE_TEMPLATE_VERSION`
  are dated strings shaped like `2026-05-10-final` — enough to clear
  the "no draft / working-copy marker" check; the real signed
  values come from the Studio.
- `LEAD_NOTIFICATION_TO_EMAILS` resolves only to `ci@example.invalid`
  (RFC 6761 — the `.invalid` TLD never reaches a real mailbox).
- `CRM_WEBHOOK_ENABLED=false`, `PEXELS_ENABLED=false`, `SENTRY_DSN=""`,
  `ADMIN_MFA_REQUIRED=false` — no external service is contacted.

This job intentionally does **not** run pytest or Lighthouse;
adding either would make it duplicate `python-tests` /
`lighthouse-desktop` while increasing the CI bill. The
production-only system checks are the single deliverable.

### `lighthouse-desktop` — public-surface budgets

| Step | Command | Why |
|---|---|---|
| Migrations | `python manage.py migrate --noinput` | Same as above. |
| Translations | `python manage.py compilemessages -l fr -l ar -l it` | `.mo` files must exist for the wizard's i18n rendering to score on `/ar/` and other localised pages. |
| Start server | `python manage.py runserver 127.0.0.1:8000 --noreload &` | Lighthouse needs a live server. We use the runner backgrounded + PID file pattern, mirroring `public-site-audit.yml`. |
| Health probe | `curl /healthz/` retry loop | The Lighthouse runner refuses to start if `/` isn't 200; the health probe gives the server up to 30 s to come up. |
| Lighthouse | `bash scripts/run_lighthouse_local.sh` | Gates 8 public URLs against the desktop budget (perf ≥ 0.80, a11y/best/seo ≥ 0.90). See `docs/qa/LIGHTHOUSE_CI.md`. |
| Artefacts | `actions/upload-artifact@v4` | On every run (pass or fail), the per-URL JSON reports in `artifacts/lighthouse/latest/` are uploaded with 14-day retention. |

### `lighthouse-mobile` — opt-in, manual dispatch only

Same shape as `lighthouse-desktop` but with `run_lighthouse_mobile_local.sh`.
**Runs only on `workflow_dispatch`** (the "Run workflow" button or
`gh workflow run ci.yml`). PRs never trigger this job — see §5 for
why.

---

## 3. What blocks a merge, what is informational

| What | Blocks merge? | Notes |
|---|---|---|
| `python-tests` failure | yes | Test regression or hygiene/audit failure. |
| `production-checks` failure | yes | A production-blocking system check would fail on deploy. Most common cause: a new check landed in `apps/*/checks.py` but its required env var was not added to this job. |
| `lighthouse-desktop` failure | yes | Perf/a11y/best/seo regression on the public surface. |
| `lighthouse-mobile` failure | no | Manual dispatch only; treated as informational. |
| `public-site-audit.yml` (legacy Playwright structural audit) | yes — separately | Orthogonal to this gate; runs on PRs and uploads its own artefacts. |

**Important**: "blocks merge?" above describes the *intent* of each
job. Whether GitHub actually enforces it depends on the
branch-protection rule being live — without a protection rule, a
red check is just a red square next to a merge button that still
works. See `docs/qa/GITHUB_BRANCH_PROTECTION.md` for the proposed
rule, the dry-run scripts, and the read-back verification command.
At the time of writing (2026-05-11) no GitHub remote is wired and
the protection rule is documented but not applied.

### Required-check names (paste exactly into the protection rule)

GitHub matches required checks by the job's display name
(`name:` field in the workflow), not the YAML id:

| Job id | Display name to require |
|---|---|
| `python-tests` (in `ci.yml`) | `Python tests + content hygiene + non-IT readiness` |
| `production-checks` (in `ci.yml`) | `Production-like system checks (DEBUG=false)` |
| `lighthouse-desktop` (in `ci.yml`) | `Lighthouse desktop (perf / a11y / best / seo budgets)` |
| `audit` (in `public-site-audit.yml`) | `Playwright structural audit` |
| `lighthouse-mobile` (in `ci.yml`) | **Do NOT require** — opt-in / skipped on PR runs |

If a workflow's `name:` changes, update the protection rule at
the same time — otherwise the rule becomes "pending forever". The
script `scripts/github/branch_protection_plan.sh` prints the
current pairs so the operator can paste them verbatim.

### How to verify required checks are active

After a protection rule is applied via
`scripts/github/branch_protection_plan.{sh,ps1}` (see §1 of
`docs/qa/GITHUB_BRANCH_PROTECTION.md`):

```bash
gh api repos/<org>/<repo>/branches/main/protection | jq '.required_status_checks.contexts'
gh api repos/<org>/<repo>/branches/audit%2Findennizzati-platform/protection | jq '.required_status_checks.contexts'
```

Both calls must list the 4 required display names from the table
above. If a name is missing, the rule is incomplete.

### What to do if a required check is stuck pending

Documented in `docs/qa/GITHUB_BRANCH_PROTECTION.md` §9. Most common
cause: a workflow's `name:` was renamed and the rule still requires
the old string.

The two parallel CI workflows complement each other:
- `ci.yml` = **functional + perf budget gate** (this doc).
- `public-site-audit.yml` = **structural Playwright audit** (HTML
  shape, navigation, accessibility tree). Older; predates the
  pinned-CLI Lighthouse runner.

---

## 4. Reproducing failures locally

Every CI job has a 1:1 local reproduction:

```
# Job 1 — python-tests
python manage.py check
pytest -q
python scripts/audit_legal_content_hygiene.py --strict
python scripts/legal_data/audit_non_it_readiness.py

# Job 2 — lighthouse-desktop
python manage.py runserver 127.0.0.1:8000           # terminal A
bash scripts/run_lighthouse_local.sh                 # terminal B

# Job 3 — lighthouse-mobile (opt-in)
bash scripts/run_lighthouse_mobile_local.sh

# All four blocking checks in one go
bash scripts/run_quality_gate.sh                     # full
bash scripts/run_quality_gate.sh --no-lighthouse     # python-tests only
bash scripts/run_quality_gate.sh --mobile-lighthouse # full + mobile
```

For Windows operators, `pwsh scripts/run_quality_gate.ps1`
mirrors the bash wrapper.

---

## 5. Why mobile Lighthouse is opt-in

Captured empirically (2026-05-11 baseline, see
`docs/qa/lighthouse-mobile-baseline/SUMMARY.md`):

- Mobile preset uses CPU throttling ×4 + simulated 3G;
- run-to-run perf jitter is ~±0.05 (vs ~±0.02 on desktop);
- worst URL (`/ar/`) sits at perf 0.79 against a 0.75 floor —
  4 points of headroom, but the jitter alone can flip a green run
  red on the same code.

Forcing the mobile audit on every PR would generate false-positive
failures roughly **15-20% of the time** based on the local jitter
distribution. That noise erodes the gate's value faster than the
extra coverage adds value.

The mobile audit therefore lives behind an explicit "Run workflow"
button. The local convention matches:
`bash scripts/run_quality_gate.sh --mobile-lighthouse` is the
operator's explicit opt-in.

When the team reaches a steadier perf baseline (lazy-loaded hero,
critical-CSS inline, etc.), tightening to default-on becomes
defensible. The runbook §7 lists the metric to watch for.

---

## 6. Env vars used by CI

The workflow keeps CI fully self-contained — no real production
secrets, no external services. The env block at the top of each job:

| Var | Value | Why |
|---|---|---|
| `DJANGO_DEBUG` | `"true"` | Skips production-only system checks (`core.E001/E002/...`, `compliance.E001`, `jurisdictions.E001`) so the test DB can exercise placeholder state. The same checks DO run in the prod deploy. |
| `DJANGO_SECRET_KEY` | `"django-insecure-ci-quality-gate-dummy-key"` | Dummy key — never use this in prod. The `django-insecure-` prefix is enforced as a runtime error in prod (`config/settings.py`). |
| `DJANGO_ALLOWED_HOSTS` | `"127.0.0.1,localhost"` | Tight whitelist for the runserver/Lighthouse client. |
| `PEXELS_ENABLED` | `"false"` | Disables the runtime image-cache download; CI never hits the Pexels API. |
| `LEAD_NOTIFICATION_ENABLED` | `"false"` | Disables CRM webhook dispatch; CI never hits any external CRM. |
| `SENTRY_DSN` | `""` | Sentry stays offline in CI. |
| `ADMIN_MFA_REQUIRED` | `"false"` | Smoke tests can authenticate without MFA setup in the test DB. |

No real API key, no real database password, no real webhook URL is
present in either workflow file. The smoke test pinned in
`apps/core/test_ci_quality_gate_p1_ci_1.py` enforces this.

---

## 7. Reading a failed CI run

### `python-tests` red

1. Open the failed run, click `python-tests` → "Show all checks".
2. Identify which step failed (Django check / migrations / pytest /
   hygiene / non-IT audit).
3. Reproduce locally with the exact command from §4.
4. Common patterns:
   - **`pytest` failure**: open the failing test in IDE, run
     `pytest path::test_name -q` for fast iteration.
   - **`audit_legal_content_hygiene.py --strict`**: a banned-phrase
     leak. See `docs/qa/PUBLIC_CONTENT_HYGIENE.md` §6–7 for the
     inline ignore marker.
   - **`audit_non_it_readiness.py` exit 1**: a non-IT LegalSource
     has been promoted to APPROVED without a matching APPROVE
     LegalReview row. Either record the LegalReview or demote the
     source.

### `lighthouse-desktop` red

1. Open the failed run, click `lighthouse-desktop`.
2. Download the `lighthouse-desktop-reports` artefact (top right
   of the run page). Contains one JSON per URL.
3. Open the failing URL's JSON, search for `"score": 0.xx` near
   the top — that's the failing category.
4. Drill into `audits` to find the specific failing audit
   (e.g. `unused-css-rules`, `color-contrast`, `meta-description`).
5. Local repro:
   `bash scripts/run_lighthouse_local.sh` against your local
   runserver.

The Lighthouse runner tolerates Windows-only chrome-launcher
EPERMs (see `docs/qa/LIGHTHOUSE_CI.md` §7) — those won't fire on
Ubuntu CI, so a failure there is a real regression.

### `lighthouse-mobile` red (manual dispatch)

Same as desktop. **Before treating it as a real regression**, check
the variance:
- mobile perf jitters ±0.05 between runs;
- if the failing score is within 0.05 of the floor, re-dispatch the
  workflow once. A second failure is signal; a single failure
  on a tight floor is jitter.

---

## 8. What CI does NOT cover

| What | Where | Notes |
|---|---|---|
| Per-PR preview deploys | n/a | Not configured. The team operates against the local dev server + the staging environment. |
| Real CRM webhook smoke | n/a | `LEAD_NOTIFICATION_ENABLED=false` in CI. The local CRM dispatcher tests are unit-level (signed payloads, retry budget, outbox state machine). |
| Real Pexels image fetch | n/a | `PEXELS_ENABLED=false`. The cache mechanism is unit-tested. |
| Production deploy checks (`core.E001`, `compliance.E001`, `jurisdictions.E001`, etc.) | **covered** by `production-checks` (P1-CI-1A) | The deploy-gate `manage.py check` is exercised with `DJANGO_DEBUG=false` and simulated signed env values in CI, separately from `python-tests`. Real prod values come from the Studio. |
| Cross-browser visual regression | n/a | Out of scope — pinned Lighthouse desktop + mobile preset is the perf-discipline lever. |

---

## 9. Adding a new CI step

When a new local gate emerges (e.g. a future security scanner, a
mypy strict pass, a docstring linter), the workflow integration is:

1. Add the new check as a stand-alone script that exits non-zero on
   failure (same shape as `audit_legal_content_hygiene.py` /
   `audit_non_it_readiness.py`).
2. Add it to `scripts/run_quality_gate.{sh,ps1}` as a new
   `run_stage "[N/M] …"` block.
3. Add a step to the `python-tests` job in `ci.yml`.
4. Update §2 and §7 of this doc.
5. Update the static smoke test
   `apps/core/test_ci_quality_gate_p1_ci_1.py` so the new step is
   pinned in CI as well.

The local gate must always be at-or-ahead-of CI — never the other
way around. Operators should be able to reproduce every CI failure
locally with a single command.

---

## 10. Relationship with other docs

- `docs/qa/LOCAL_QUALITY_GATE.md` — the local-runnable form of the
  same gate.
- `docs/qa/LIGHTHOUSE_CI.md` — desktop preset runbook (the file
  this doc references for Lighthouse-specific guidance).
- `docs/qa/LIGHTHOUSE_MOBILE_BASELINE.md` — mobile preset runbook
  (the file that explains why the mobile gate is opt-in here).
- `docs/qa/PUBLIC_CONTENT_HYGIENE.md` — the rules the hygiene step
  enforces.
- `docs/NON_IT_MVP_READINESS_2026-05-10.md` — the chain the
  non-IT readiness audit step protects.
- `.github/workflows/public-site-audit.yml` — the orthogonal
  Playwright structural audit (NOT modified by this batch).
- `docs/qa/GITHUB_BRANCH_PROTECTION.md` — proposed branch-protection
  rule + dry-run scripts to apply it. **Read before assuming
  CI red blocks a merge** — without the rule active, it doesn't.
