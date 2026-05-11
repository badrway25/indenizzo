# GitHub branch protection — dry-run planner (P2-CI-2) — PowerShell variant.
#
# Mirror of `scripts/github/branch_protection_plan.sh`. Prints the
# branch-protection plan; never modifies any remote state in this
# batch.
#
# Usage:
#   pwsh scripts/github/branch_protection_plan.ps1
#   pwsh scripts/github/branch_protection_plan.ps1 -Apply
#   pwsh scripts/github/branch_protection_plan.ps1 -Apply -YesIUnderstand
#
# Even with both flags, the script asks for an interactive `y`
# confirmation. Set $env:BRANCH_PROTECTION_APPLY = "1" to skip the
# prompt in automation contexts.
#
# Runbook: docs/qa/GITHUB_BRANCH_PROTECTION.md.

param(
    [switch]$Apply,
    [switch]$YesIUnderstand
)

$ErrorActionPreference = "Continue"

function Write-HR {
    param([string]$Title)
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "  $Title"
    Write-Host ("=" * 60)
    Write-Host ""
}

Write-HR "GitHub branch protection - DRY RUN"

# ---- pre-flight: gh + origin ----

$GhPresent = $true
try {
    $null = Get-Command gh -ErrorAction Stop
} catch {
    $GhPresent = $false
    Write-Host "[gh] NOT INSTALLED."
    Write-Host "     Install: https://cli.github.com/"
    Write-Host "     After install, run ``gh auth login``."
    Write-Host ""
}

if ($GhPresent) {
    & gh auth status *> $null
    if ($LASTEXITCODE -ne 0) {
        $GhPresent = $false
        Write-Host "[gh] installed but NOT authenticated."
        Write-Host "     Run: gh auth login"
        Write-Host ""
    } else {
        Write-Host "[gh] installed + authenticated."
        Write-Host ""
    }
}

$RemoteUrl = (& git remote get-url origin 2>$null)
$RemotePresent = $true
if (-not $RemoteUrl) {
    $RemotePresent = $false
    Write-Host "[remote] NO ``origin`` REMOTE CONFIGURED."
    Write-Host "         Add one with:"
    Write-Host "             git remote add origin git@github.com:<org>/<repo>.git"
    Write-Host "         Then re-run."
    Write-Host ""
} else {
    Write-Host "[remote] origin = $RemoteUrl"
    Write-Host ""
}

# ---- plan ----

Write-HR "Plan - what would be applied"

@"
For BOTH branches:
  - main
  - audit/indennizzati-platform

Required status checks (job display names - NOT job ids):
  - Python tests + content hygiene + non-IT readiness
  - Production-like system checks (DEBUG=false)
  - Lighthouse desktop (perf / a11y / best / seo budgets)
  - Playwright structural audit

NOT required (deliberate - opt-in / skipped on PR runs):
  - Lighthouse mobile (opt-in - workflow_dispatch only)

Other settings (per docs/qa/GITHUB_BRANCH_PROTECTION.md section 4):
  - require pull request before merge: yes (>= 1 approval)
  - dismiss stale approvals on new commits: yes
  - require status checks: yes (strict - branches must be up to date)
  - require conversation resolution: yes
  - require linear history: NO  (project uses git merge --no-ff)
  - block force pushes: yes
  - block deletions: yes
  - enforce on administrators: yes (recommended)
"@ | Write-Host

# ---- concrete commands ----

Write-HR "Concrete commands (run manually if needed)"

if ($GhPresent -and $RemotePresent) {
    $RepoSlug = (& gh repo view --json nameWithOwner --jq .nameWithOwner 2>$null)
    if (-not $RepoSlug) { $RepoSlug = "<org>/<repo>" }
} else {
    $RepoSlug = "<org>/<repo>"
}

@"
# Read current protection (if any) for each branch:
gh api repos/$RepoSlug/branches/main/protection
gh api repos/$RepoSlug/branches/audit%2Findennizzati-platform/protection

# Apply protection on ``main`` (use the JSON body from the runbook):
gh api -X PUT repos/$RepoSlug/branches/main/protection ``
  --input docs/qa/_assets/branch_protection_main.json

# Apply protection on ``audit/indennizzati-platform``:
gh api -X PUT ``
  repos/$RepoSlug/branches/audit%2Findennizzati-platform/protection ``
  --input docs/qa/_assets/branch_protection_audit.json

# Read back to verify (must list every required-check name):
gh api repos/$RepoSlug/branches/main/protection ``
  | ConvertFrom-Json ``
  | Select-Object -ExpandProperty required_status_checks
"@ | Write-Host

# ---- apply gate ----

if (-not $Apply) {
    Write-HR "DRY RUN - nothing applied. Pass -Apply -YesIUnderstand to apply."
    exit 0
}

if (-not $YesIUnderstand) {
    Write-Host "[apply] -Apply was passed but -YesIUnderstand was not."
    Write-Host "        Refusing to apply. Both switches are required."
    exit 3
}

if (-not $GhPresent -or -not $RemotePresent) {
    Write-Host "[apply] Cannot apply: gh or origin missing (see above)."
    exit 4
}

if ($env:BRANCH_PROTECTION_APPLY -ne "1") {
    Write-Host ""
    Write-Host "About to apply branch protection on:"
    Write-Host "  - main"
    Write-Host "  - audit/indennizzati-platform"
    Write-Host ""
    $answer = Read-Host "Type 'y' to proceed, anything else to abort"
    if ($answer -ne "y" -and $answer -ne "Y") {
        Write-Host "[apply] Aborted by operator."
        exit 5
    }
}

# Intentionally NOT implemented in this batch (mirror of the bash
# version). See docs/qa/GITHUB_BRANCH_PROTECTION.md section 7.
Write-Host ""
Write-Host "[apply] STUB - actual gh api PUT calls intentionally not"
Write-Host "        implemented in this batch. See"
Write-Host "        docs/qa/GITHUB_BRANCH_PROTECTION.md section 7 for"
Write-Host "        the commands to run manually."
exit 6
