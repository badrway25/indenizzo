# Local Lighthouse CI runner — MOBILE preset (P2-SEO-1) — PowerShell variant.
#
# Companion of `scripts/run_lighthouse_local.ps1` (desktop preset).
#
# Usage:
#   pwsh scripts/run_lighthouse_mobile_local.ps1
#   pwsh scripts/run_lighthouse_mobile_local.ps1 -UpdateBaseline
#
# Defaults to writing JSON into the gitignored
# `artifacts/lighthouse-mobile/latest/`. -UpdateBaseline switches
# to the tracked `docs/qa/lighthouse-mobile-baseline/`.

param(
    [switch]$UpdateBaseline
)

$ErrorActionPreference = "Continue"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $RepoRoot

if ($UpdateBaseline) {
    $OutDir = "docs/qa/lighthouse-mobile-baseline"
    Write-Host "[lighthouse mobile runner] mode: UPDATE-BASELINE (writes tracked files in $OutDir)" -ForegroundColor Yellow
} else {
    $OutDir = "artifacts/lighthouse-mobile/latest"
    Write-Host "[lighthouse mobile runner] mode: GATE (writes gitignored $OutDir/)"
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

$PerfMin = 0.75
$A11yMin = 0.90
$BpMin = 0.90
$SeoMin = 0.90
$GlobalFailed = 0

foreach ($t in $Targets) {
    $label = $t.Label
    $url = "http://127.0.0.1:8000$($t.Path)"
    $outfile = Join-Path $OutDir "$label-mobile.json"
    Write-Host ""
    Write-Host "[$label] $url" -ForegroundColor Cyan

    & npx --yes lighthouse@latest $url `
        --output=json `
        --output-path=$outfile `
        --form-factor=mobile `
        --screenEmulation.mobile=true `
        --screenEmulation.width=390 `
        --screenEmulation.height=844 `
        --throttling.cpuSlowdownMultiplier=4 `
        --chrome-flags="--headless --no-sandbox" `
        --only-categories=performance,accessibility,best-practices,seo `
        --quiet 2>$null

    if (-not (Test-Path $outfile)) {
        Write-Host "  FAILED: no JSON written. Aborting." -ForegroundColor Red
        exit 3
    }

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
    Write-Host "RESULT: at least one URL failed the mobile Lighthouse gate." -ForegroundColor Red
    exit 1
}
Write-Host "RESULT: all URLs cleared the mobile gate." -ForegroundColor Green
