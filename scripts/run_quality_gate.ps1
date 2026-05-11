# Consolidated local quality gate (P1-QA-1) — PowerShell variant.
#
# Mirror of `scripts/run_quality_gate.sh`. Runs the four local gates
# in order, fail-fast:
#
#   1. python manage.py check
#   2. pytest -q
#   3. python scripts/audit_legal_content_hygiene.py --strict
#   4. pwsh scripts/run_lighthouse_local.ps1
#
# Usage:
#   pwsh scripts/run_quality_gate.ps1
#   pwsh scripts/run_quality_gate.ps1 -NoLighthouse
#   pwsh scripts/run_quality_gate.ps1 -NoPytest
#
# Exit codes:
#   0 — every (non-skipped) stage cleared.
#   1 — at least one stage failed.

param(
    [switch]$NoLighthouse,
    [switch]$NoPytest
)

$ErrorActionPreference = "Continue"
$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

$GateStart = Get-Date
$GateFailed = $null

function Invoke-Stage {
    param(
        [string]$Label,
        [scriptblock]$Body
    )
    Write-Host ""
    Write-Host ("=" * 60)
    Write-Host "  $Label" -ForegroundColor Cyan
    Write-Host ("=" * 60)
    $stageStart = Get-Date
    & $Body
    $code = $LASTEXITCODE
    $duration = [int]((Get-Date) - $stageStart).TotalSeconds
    if ($code -ne 0) {
        Write-Host ""
        Write-Host "[FAIL] $Label ($duration s)" -ForegroundColor Red
        $script:GateFailed = $Label
        return $false
    }
    Write-Host ""
    Write-Host "[OK]   $Label ($duration s)" -ForegroundColor Green
    return $true
}

# ---- 1 ----
$ok = Invoke-Stage "[1/4] Django system checks: python manage.py check" {
    python manage.py check
}
if (-not $ok) {
    Write-Host ""
    Write-Host "Gate aborted at: $GateFailed" -ForegroundColor Red
    exit 1
}

# ---- 2 ----
if ($NoPytest) {
    Write-Host ""
    Write-Host "[SKIP] [2/4] pytest (flag -NoPytest)" -ForegroundColor Yellow
} else {
    $ok = Invoke-Stage "[2/4] Test suite: pytest -q" {
        pytest -q
    }
    if (-not $ok) {
        Write-Host ""
        Write-Host "Gate aborted at: $GateFailed" -ForegroundColor Red
        exit 1
    }
}

# ---- 3 ----
$ok = Invoke-Stage "[3/4] Deontological content hygiene: --strict" {
    python scripts/audit_legal_content_hygiene.py --strict
}
if (-not $ok) {
    Write-Host ""
    Write-Host "Gate aborted at: $GateFailed" -ForegroundColor Red
    exit 1
}

# ---- 4 ----
if ($NoLighthouse) {
    Write-Host ""
    Write-Host "[SKIP] [4/4] Lighthouse (flag -NoLighthouse)" -ForegroundColor Yellow
} else {
    # Pre-flight: server must respond on 127.0.0.1:8000.
    try {
        $code = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/" -TimeoutSec 5).StatusCode
    } catch { $code = 0 }
    if ($code -ne 200) {
        Write-Host ""
        Write-Host "[SKIP] [4/4] Lighthouse - Django not responding on 127.0.0.1:8000." -ForegroundColor Yellow
        Write-Host "       Start it in another terminal:"
        Write-Host "           python manage.py runserver 127.0.0.1:8000"
        Write-Host "       ...then re-run, or pass -NoLighthouse to silence."
        $total = [int]((Get-Date) - $GateStart).TotalSeconds
        Write-Host ""
        Write-Host ("=" * 60)
        Write-Host "  GATE FAILED - Lighthouse stage prerequisite missing" -ForegroundColor Red
        Write-Host "  Total: $total s"
        Write-Host ("=" * 60)
        exit 1
    }

    $ok = Invoke-Stage "[4/4] Lighthouse: pwsh scripts/run_lighthouse_local.ps1" {
        pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/run_lighthouse_local.ps1
    }
    if (-not $ok) {
        Write-Host ""
        Write-Host "Gate aborted at: $GateFailed" -ForegroundColor Red
        exit 1
    }
}

# ---- summary ----
$total = [int]((Get-Date) - $GateStart).TotalSeconds
Write-Host ""
Write-Host ("=" * 60)
Write-Host "  ALL GATES CLEARED  ($total s total)" -ForegroundColor Green
Write-Host ("=" * 60)

$drift = git diff --quiet docs/qa/lighthouse-baseline/ 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "Unexpected: docs/qa/lighthouse-baseline/ was modified by the gate." -ForegroundColor Yellow
    Write-Host "This should only happen if you ran the lighthouse runner with -UpdateBaseline."
    Write-Host "If not intentional, discard with:"
    Write-Host "    git checkout -- docs/qa/lighthouse-baseline/"
}
exit 0
