# Local Lighthouse CI runner (P1-SEO-2 + P1-QA-1A) — PowerShell variant.
#
# Usage:
#   pwsh scripts/run_lighthouse_local.ps1
#   pwsh scripts/run_lighthouse_local.ps1 -UpdateBaseline
#
# Mirror of `scripts/run_lighthouse_local.sh`. Drives
# `npx lighthouse@latest` against the URL list, exits non-zero if
# any score is below the gating threshold.
#
# Output destination depends on mode:
# - default (gate run): writes JSON into the gitignored
#   `artifacts/lighthouse/latest/` — a normal gate run does NOT
#   dirty the working tree;
# - -UpdateBaseline: writes JSON into the tracked
#   `docs/qa/lighthouse-baseline/` (the only path that intentionally
#   modifies a tracked baseline file).
#
# The chrome-launcher EPERM during temp-dir cleanup on Windows is
# expected and ignored — the JSON is fully written before the
# cleanup attempt.

param(
    [switch]$UpdateBaseline
)

$ErrorActionPreference = "Continue"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if ($UpdateBaseline) {
    $OutDir = "docs/qa/lighthouse-baseline"
    Write-Host "[lighthouse runner] mode: UPDATE-BASELINE (writes tracked files in $OutDir)" -ForegroundColor Yellow
} else {
    $OutDir = "artifacts/lighthouse/latest"
    Write-Host "[lighthouse runner] mode: GATE (writes gitignored $OutDir/)"
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

try {
    $code = (Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8000/" -TimeoutSec 5).StatusCode
} catch {
    $code = 0
}
if ($code -ne 200) {
    Write-Host "ERROR: Django is not responding on http://127.0.0.1:8000/." -ForegroundColor Red
    Write-Host "Start it in another terminal:"
    Write-Host "    python manage.py runserver 127.0.0.1:8000"
    exit 2
}

$Targets = @(
    @{ Label = "home-it";    Path = "/" },
    @{ Label = "contact";    Path = "/contact/" },
    @{ Label = "wizard";     Path = "/wizard/" },
    @{ Label = "privacy";    Path = "/privacy/" },
    @{ Label = "disclaimer"; Path = "/disclaimer/" },
    @{ Label = "countries";  Path = "/countries/" },
    @{ Label = "case-types"; Path = "/case-types/" },
    @{ Label = "ar-home";    Path = "/ar/" }
)

$PerfMin = 0.80
$A11yMin = 0.90
$BpMin = 0.90
$SeoMin = 0.90
$GlobalFailed = 0

foreach ($t in $Targets) {
    $label = $t.Label
    $url = "http://127.0.0.1:8000$($t.Path)"
    $outfile = Join-Path $OutDir "$label-desktop.json"
    Write-Host ""
    Write-Host "[$label] $url" -ForegroundColor Cyan

    & npx --yes lighthouse@latest $url `
        --output=json `
        --output-path=$outfile `
        --preset=desktop `
        --chrome-flags="--headless --no-sandbox" `
        --only-categories=performance,accessibility,best-practices,seo `
        --quiet 2>$null

    if (-not (Test-Path $outfile)) {
        Write-Host "  FAILED: no JSON written. Aborting." -ForegroundColor Red
        exit 3
    }

    # Parse + gate via Python.
    $py = @"
import json, sys
d = json.load(open(r'$outfile', encoding='utf-8'))
cats = d.get('categories', {})
def g(n): return cats.get(n, {}).get('score') or 0.0
perf, a11y, bp, seo = g('performance'), g('accessibility'), g('best-practices'), g('seo')
print(f'  scores  perf={perf:.2f}  a11y={a11y:.2f}  best={bp:.2f}  seo={seo:.2f}')
fail = []
if perf < $PerfMin: fail.append(f'performance {perf:.2f} < $PerfMin')
if a11y < $A11yMin: fail.append(f'accessibility {a11y:.2f} < $A11yMin')
if bp < $BpMin:    fail.append(f'best-practices {bp:.2f} < $BpMin')
if seo < $SeoMin:  fail.append(f'seo {seo:.2f} < $SeoMin')
if fail:
    print('  GATE FAILED: ' + '; '.join(fail))
    sys.exit(1)
"@
    & python -c $py
    if ($LASTEXITCODE -ne 0) { $GlobalFailed = 1 }
}

Write-Host ""
if ($GlobalFailed -ne 0) {
    Write-Host "RESULT: at least one URL failed the Lighthouse gate." -ForegroundColor Red
    exit 1
}
Write-Host "RESULT: all URLs cleared the gate." -ForegroundColor Green
