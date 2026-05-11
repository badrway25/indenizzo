# GitHub branch protection — runbook

**Iter**: F-p2-ci-2-branch-protection
**Date**: 2026-05-11

This runbook documents the **proposed** GitHub branch protection
posture for the platform's two long-lived branches. It is
**preparation, not applied configuration**: at the time of writing
the repo has no GitHub remote configured (`git remote -v` is
empty), and `gh` CLI is not installed on the dev machine. The
companion dry-run scripts
(`scripts/github/branch_protection_plan.sh|.ps1`) print the plan
that should be applied when the remote and `gh` are in place.

Apply only after explicit Studio + dev lead approval.

---

## 1. Current local state (2026-05-11)

- `git remote -v` — **empty** (no `origin` configured).
- `gh --version` — **not installed**.
- Active workflows in `.github/workflows/`:
  - `ci.yml` (4 jobs: `python-tests`, `production-checks`,
    `lighthouse-desktop`, `lighthouse-mobile`).
  - `public-site-audit.yml` (1 job: legacy Playwright structural
    audit).

When the remote is added (`git remote add origin …`) and `gh` is
installed + authenticated, the rest of this doc becomes
actionable.

---

## 2. Branches to protect

| Branch | Why protected | Hosts the deploy candidate? |
|---|---|---|
| `main` | Default branch by convention; once the team publishes anything, this is the public-facing root. | yes (eventually). |
| `audit/indennizzati-platform` | Long-running integration branch where every `p*/...` batch is merged via `--no-ff`. Today this is the de-facto trunk. | yes (today). |

Short-lived branches (`p*/...`, `work/...`, `feature/...`) are NOT
protected — the workflow merges them via `--no-ff` and they get
deleted after merge. Protecting them would add ceremony without
safety.

---

## 3. Status checks to require

Required (block merge if red or pending):

| Required check | Source workflow | Why blocking |
|---|---|---|
| `Python tests + content hygiene + non-IT readiness` | `.github/workflows/ci.yml` → `python-tests` job | Test regression, hygiene leak, audit-trail break. |
| `Production-like system checks (DEBUG=false)` | `.github/workflows/ci.yml` → `production-checks` job | Deploy-blocking system check would fail on prod. |
| `Lighthouse desktop (perf / a11y / best / seo budgets)` | `.github/workflows/ci.yml` → `lighthouse-desktop` job | Performance / a11y / SEO regression. |
| `Playwright structural audit` | `.github/workflows/public-site-audit.yml` → `audit` job | Legacy but still useful — pins HTML shape + navigation. |

Not required (manual / informational):

| Not required | Source | Why |
|---|---|---|
| `Lighthouse mobile (opt-in)` | `ci.yml` → `lighthouse-mobile` job | `workflow_dispatch`-only. Mobile-throttling jitter (~±0.05 perf) would flap green→red on tight floors. Run manually before merges that plausibly hit mobile rendering. |

**The check names above are the job display names (`name:` keys),
not the YAML job ids.** GitHub matches required checks by display
name. If a job's display name changes, the required-check rule
must be updated too — the dry-run script in §7 prints both pairs
so the operator can paste the exact strings.

---

## 4. Recommended branch-protection policy

For BOTH `main` and `audit/indennizzati-platform`:

| Setting | Recommended | Reason |
|---|---|---|
| Require pull request before merge | **yes** | No direct pushes; every change goes through PR. |
| Required reviews | **1** (minimum) | Single human review catches the obvious; CI catches the rest. Raise to 2 if the team grows. |
| Dismiss stale approvals on new commits | **yes** | A push that adds a regression after approval shouldn't ride on the old green review. |
| Require review from CODEOWNERS | **no** (no CODEOWNERS file today) | Add when the team is large enough to need ownership areas. |
| Require status checks to pass | **yes** | See §3. |
| Require branches to be up to date before merging | **yes** | Forces a rebase/merge of base when CI on the PR's commit was green but base moved. Cheap insurance. |
| Require conversation resolution before merging | **yes** | Reviewer comments that are still "Open" must be Resolved or addressed. |
| Require signed commits | **no** (decision) | Adds operator friction; GitHub-side identity is enough for now. Revisit if a security audit asks. |
| **Require linear history** | **NO** | The project's release cadence relies on `git merge --no-ff` (every `p*/...` batch lands as a non-fast-forward merge commit). Linear history would forbid that. See §5 for the trade-off. |
| Block force pushes | **yes** | Force-pushing to a protected branch should never be needed in this workflow. |
| Block deletions | **yes** | Long-lived branches must not vanish. |
| Restrict who can push | (configure per-team) | At a minimum, deny `everyone`; allow only the dev lead + automation. |
| Enforce for administrators | **yes (recommended)** | If admins can bypass, the gate is performative. Disable only for genuine emergencies; re-enable immediately after. |
| Allow specified actors to bypass | (none) | Same logic — bypass tokens defeat the gate. |

---

## 5. Trade-off: `--no-ff` merges vs. linear history

The project uses `git merge --no-ff p*/... -m "merge: ..."` for
every batch. This creates a merge commit per batch and keeps the
batch's commit history threaded under it, which is the readable
shape for retrospective audit ("when did P0-MVP-1 land? what
commits did it carry?").

GitHub's "Require linear history" rule would forbid this exact
shape — it accepts only fast-forwards or rebases. Two consequences
if we enabled it:

1. We'd be forced to rebase every batch onto main before merging.
   That collapses the merge commit and **loses the batch
   boundary** in the log.
2. The existing `git log --oneline` history would still be valid,
   but new PRs would have to follow a different convention. That's
   a behavioural shift across the team.

**Recommendation: leave "Require linear history" OFF.** Keep
`--no-ff` merges. The readability win on retrospective audits is
real and matches the local convention.

If/when the team later wants a fully linear history (e.g. for a
specific release branch), do it via convention enforcement
("rebase before merge to release") rather than the branch-protection
flag — the flag is too blunt.

---

## 6. Branch Protection (classic) vs. Repository Rulesets

GitHub now offers two ways to express the policy above:

| | Branch Protection (classic) | Repository Rulesets |
|---|---|---|
| Maturity | Long-standing, every doc/script assumes it | Newer (2023+) |
| Granularity | Per-branch | Per-pattern across many branches, with import/export JSON |
| Multiple rules per branch | Single rule | Stacking supported |
| API stability | `repos/.../branches/.../protection` is stable | Rulesets API is stable but newer |
| Bypass logging | Limited | Better audit log |
| Required checks UI | Status-check name dropdown | Same dropdown |
| `gh` CLI support | `gh api` directly; no first-class subcommand | Same — `gh api repos/.../rulesets` |

**Recommendation: start with classic Branch Protection** for the
two branches. It is the lowest-risk option: documented for years,
behaves identically across `gh`/web/Terraform. Move to Rulesets
later only if the team needs cross-branch policies (e.g. "every
branch matching `release/*`").

Both options are equivalent for what this batch wants to enforce.
The dry-run script (§7) supports either path — the operator picks
when applying.

---

## 7. Dry-run scripts

`scripts/github/branch_protection_plan.sh` (bash) and
`scripts/github/branch_protection_plan.ps1` (PowerShell). Both:

- Verify `gh` is installed and authenticated. Print a clear "install
  from https://cli.github.com/" message if not.
- Verify the current repo has an `origin` remote pointing at GitHub.
  Print the `git remote add origin git@github.com:<org>/<repo>.git`
  command if not.
- Print the **plan** for both protected branches (required checks,
  reviews, force-push block, etc.) — what the operator should apply.
- Print the **exact `gh api` calls** that would apply the plan, in
  comment form. Nothing is executed by default.
- Refuse to apply unless **both** `--apply` and
  `--yes-i-understand` are passed. Two flags by design — a single
  typo in one flag shouldn't be enough to trigger remote writes.

Even with both flags, the script first prints the plan and asks
the operator to confirm interactively (`y`/`N`, default `N`). On
non-interactive shells the operator must also set
`BRANCH_PROTECTION_APPLY=1`.

Usage:

```bash
# Dry-run (default — never modifies anything)
bash scripts/github/branch_protection_plan.sh

# What a real apply would look like — STILL DOES NOT APPLY
bash scripts/github/branch_protection_plan.sh --apply

# Actually apply (interactive prompt)
bash scripts/github/branch_protection_plan.sh --apply --yes-i-understand

# Non-interactive apply (CI / automation)
BRANCH_PROTECTION_APPLY=1 bash scripts/github/branch_protection_plan.sh \
    --apply --yes-i-understand
```

The PowerShell variant uses the same flag names with PowerShell
conventions (`-Apply -YesIUnderstand`).

---

## 8. How to verify required checks are active

Once applied (post `--apply`), verify the rule is live:

```bash
# Read-only check
gh api repos/<org>/<repo>/branches/main/protection
gh api repos/<org>/<repo>/branches/audit%2Findennizzati-platform/protection
```

The JSON must list each required check by name, and `enforce_admins`
must be `true` (if you decided to enforce on admins).

In the GitHub web UI:
**Settings → Branches → Branch protection rules → main** —
"Require status checks to pass before merging" must be checked
with the 4 check names present.

---

## 9. What to do if a required check is stuck pending

A pending status check that never resolves blocks the merge
indefinitely. Common causes + fixes:

| Cause | Fix |
|---|---|
| The workflow file changed its job's display name; the protection rule still requires the old name. | Edit the rule, replace the name with the new one. The dry-run script prints the current pair. |
| The workflow file moved to a path that the trigger no longer matches. | Re-check `on: pull_request: paths:` filters in the workflow YAML. Don't add path filters for PRs — they cause exactly this kind of false-pending. |
| The job was skipped (e.g. `if: github.event_name == 'workflow_dispatch'`) so it shows as "Skipped" but the rule treats it as missing. | The rule must NOT require an opt-in job. `lighthouse-mobile` is opt-in for this reason; don't add it to the required list. |
| The runner timed out (free runners have minute caps). | Re-run the job. If it's chronic, split the work or move to a larger runner. |
| GitHub Actions outage. | Wait. https://www.githubstatus.com/ |

---

## 10. Why mobile Lighthouse stays opt-in

Documented at length in `docs/qa/LIGHTHOUSE_MOBILE_BASELINE.md` §7
and `docs/qa/CI_QUALITY_GATE.md` §5. Short form: mobile preset
CPU×4 + simulated 3G introduces ~±0.05 perf jitter; `/ar/` sits at
0.79 against a 0.75 floor — 4 points headroom but jitter alone can
flip green→red. Forcing it as required would generate
false-positive merge blocks. Operators run it explicitly with
`bash scripts/run_quality_gate.sh --mobile-lighthouse` or via the
GitHub Actions "Run workflow" button before merges that plausibly
hit mobile rendering.

---

## 11. Related docs

- `docs/qa/CI_QUALITY_GATE.md` — the CI gate this rule enforces.
- `docs/qa/LIGHTHOUSE_CI.md` — desktop preset runbook.
- `docs/qa/LIGHTHOUSE_MOBILE_BASELINE.md` — mobile preset (opt-in).
- `docs/GO_LIVE_GATE_CHECKLIST.md` — pre-deploy checklist; §1.5
  (this batch) verifies branch protection is active before
  cutting a release.
