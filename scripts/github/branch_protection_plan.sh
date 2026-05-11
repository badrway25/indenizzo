#!/usr/bin/env bash
#
# GitHub branch protection — dry-run planner (P2-CI-2).
#
# Prints the branch-protection plan for `main` and
# `audit/indennizzati-platform`, matching the proposal in
# `docs/qa/GITHUB_BRANCH_PROTECTION.md`. By default the script
# DOES NOT MODIFY ANY REMOTE STATE — it only prints what would be
# applied.
#
# Applying requires *both* flags:
#   --apply             — opts into the apply path
#   --yes-i-understand  — second confirmation, never combined
#                         accidentally with --apply
#
# Even with both flags, the script prints the plan, then asks the
# operator to type 'y' to proceed. On a non-interactive shell, set
# BRANCH_PROTECTION_APPLY=1 to skip the interactive prompt.
#
# Pre-flight checks:
#   1. `gh` CLI is installed + authenticated (`gh auth status`).
#   2. An `origin` remote exists and points at GitHub.
# Both are advisory in dry-run mode (the script still prints the
# plan) and blocking in apply mode.
#
# Companion: scripts/github/branch_protection_plan.ps1.
# Runbook: docs/qa/GITHUB_BRANCH_PROTECTION.md.

set -u

APPLY=0
CONFIRMED=0
for arg in "$@"; do
  case "${arg}" in
    --apply)             APPLY=1 ;;
    --yes-i-understand)  CONFIRMED=1 ;;
    -h|--help)
      sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown flag: ${arg}" >&2
      echo "Run with --help." >&2
      exit 2
      ;;
  esac
done

# ----------------------------------------------------------------------
# Pre-flight: gh + origin remote
# ----------------------------------------------------------------------

hr() {
  printf '\n%s\n' "============================================================"
  printf '  %s\n' "$1"
  printf '%s\n\n' "============================================================"
}

hr "GitHub branch protection — DRY RUN"

# `gh` may print to stderr when not installed; we want a clear
# diagnostic instead of a noisy shell error.
GH_PRESENT=1
if ! command -v gh >/dev/null 2>&1; then
  GH_PRESENT=0
  printf '[gh] NOT INSTALLED.\n'
  printf '     Install: https://cli.github.com/\n'
  printf '     After install, run `gh auth login`.\n\n'
else
  if gh auth status >/dev/null 2>&1; then
    printf '[gh] installed + authenticated.\n\n'
  else
    GH_PRESENT=0
    printf '[gh] installed but NOT authenticated.\n'
    printf '     Run: gh auth login\n\n'
  fi
fi

REMOTE_URL="$(git remote get-url origin 2>/dev/null || true)"
REMOTE_PRESENT=1
if [ -z "${REMOTE_URL}" ]; then
  REMOTE_PRESENT=0
  printf '[remote] NO `origin` REMOTE CONFIGURED.\n'
  printf '         Add one with:\n'
  printf '             git remote add origin git@github.com:<org>/<repo>.git\n'
  printf '         Then re-run.\n\n'
else
  printf '[remote] origin = %s\n\n' "${REMOTE_URL}"
fi

# ----------------------------------------------------------------------
# The plan (printed regardless of apply mode)
# ----------------------------------------------------------------------

hr "Plan — what would be applied"

cat <<'EOF'
For BOTH branches:
  - main
  - audit/indennizzati-platform

Required status checks (job display names — NOT job ids):
  - Python tests + content hygiene + non-IT readiness
  - Production-like system checks (DEBUG=false)
  - Lighthouse desktop (perf / a11y / best / seo budgets)
  - Playwright structural audit

NOT required (deliberate — opt-in / skipped on PR runs):
  - Lighthouse mobile (opt-in - workflow_dispatch only)

Other settings (per docs/qa/GITHUB_BRANCH_PROTECTION.md §4):
  - require pull request before merge: yes (>= 1 approval)
  - dismiss stale approvals on new commits: yes
  - require status checks: yes (strict — branches must be up to date)
  - require conversation resolution: yes
  - require linear history: NO  (the project uses git merge --no-ff)
  - block force pushes: yes
  - block deletions: yes
  - enforce on administrators: yes (recommended)
EOF

# ----------------------------------------------------------------------
# Concrete commands — printed as a guide, NOT executed.
# ----------------------------------------------------------------------

hr "Concrete commands (run manually if needed)"

if [ "${GH_PRESENT}" -eq 1 ] && [ "${REMOTE_PRESENT}" -eq 1 ]; then
  REPO_SLUG="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || echo '<org>/<repo>')"
else
  REPO_SLUG='<org>/<repo>'
fi

cat <<EOF
# Read current protection (if any) for each branch:
gh api repos/${REPO_SLUG}/branches/main/protection
gh api repos/${REPO_SLUG}/branches/audit%2Findennizzati-platform/protection

# Apply protection on \`main\` (use the JSON body from the runbook):
gh api -X PUT repos/${REPO_SLUG}/branches/main/protection \\
  --input docs/qa/_assets/branch_protection_main.json
# (the assets file does not exist yet — generate it from the plan
# above; documented in docs/qa/GITHUB_BRANCH_PROTECTION.md §7.)

# Apply protection on \`audit/indennizzati-platform\`:
gh api -X PUT \\
  repos/${REPO_SLUG}/branches/audit%2Findennizzati-platform/protection \\
  --input docs/qa/_assets/branch_protection_audit.json

# Read back to verify (must list every required-check name):
gh api repos/${REPO_SLUG}/branches/main/protection \\
  | jq '.required_status_checks.contexts'
EOF

# ----------------------------------------------------------------------
# Apply gate
# ----------------------------------------------------------------------

if [ "${APPLY}" -eq 0 ]; then
  hr "DRY RUN — nothing applied. Pass --apply --yes-i-understand to apply."
  exit 0
fi

if [ "${CONFIRMED}" -eq 0 ]; then
  printf '[apply] --apply was passed but --yes-i-understand was not.\n'
  printf '        Refusing to apply. Both flags are required.\n'
  exit 3
fi

if [ "${GH_PRESENT}" -eq 0 ] || [ "${REMOTE_PRESENT}" -eq 0 ]; then
  printf '[apply] Cannot apply: gh or origin missing (see above).\n'
  exit 4
fi

if [ "${BRANCH_PROTECTION_APPLY:-0}" != "1" ]; then
  printf '\nAbout to apply branch protection on:\n'
  printf '  - main\n'
  printf '  - audit/indennizzati-platform\n\n'
  printf 'Type `y` to proceed, anything else to abort: '
  read -r answer
  if [ "${answer}" != "y" ] && [ "${answer}" != "Y" ]; then
    printf '[apply] Aborted by operator.\n'
    exit 5
  fi
fi

# Intentionally NOT implemented in this batch: the actual `gh api`
# PUT calls. The user spec says "Per ora crea documentazione, script
# dry-run e checklist". Apply-time logic is documented in §7 of the
# runbook so a future iter can wire it without rewriting this guard.
printf '\n[apply] STUB — actual gh api PUT calls intentionally not\n'
printf '        implemented in this batch. See\n'
printf '        docs/qa/GITHUB_BRANCH_PROTECTION.md §7 for the\n'
printf '        commands to run manually.\n'
exit 6
