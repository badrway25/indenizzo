# Smoke test post-deploy (PowerShell).
# Uso: .\scripts\staging\smoke.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..\..

$code = @"
from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
calc = ItalyRoadAccidentBodilyInjuryCalculator(language='it')
r = calc.compute({'victim_age': 35, 'permanent_disability_percentage': 10, 'fault_percentage': 0})
print('status:', r.status)
print('estimated_min:', r.estimated_min)
print('estimated_mid:', r.estimated_mid)
print('estimated_max:', r.estimated_max)
assert r.status == 'calculated', f'expected calculated, got {r.status}'
assert int(r.estimated_mid) == 21709, f'expected 21709, got {r.estimated_mid}'
print('SMOKE PASSED.')
"@

docker compose -f docker-compose.staging.yml --env-file .env.staging `
    exec web python manage.py shell -c $code
