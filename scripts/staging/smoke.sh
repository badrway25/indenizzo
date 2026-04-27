#!/usr/bin/env bash
# Smoke test post-deploy: crea una Simulation con (35, 10, 0) e verifica
# che il calculator restituisca 21.709 €.
# Uso: ./scripts/staging/smoke.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

./scripts/staging/manage.sh shell -c "
from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
calc = ItalyRoadAccidentBodilyInjuryCalculator(language='it')
r = calc.compute({'victim_age': 35, 'permanent_disability_percentage': 10, 'fault_percentage': 0})
print(f'status: {r.status}')
print(f'estimated_min: {r.estimated_min}')
print(f'estimated_mid: {r.estimated_mid}')
print(f'estimated_max: {r.estimated_max}')
print(f'sources count: {len(r.sources)}')
print(f'breakdown items: {len(r.breakdown)}')
assert r.status == 'calculated', f'expected calculated, got {r.status}'
assert int(r.estimated_mid) == 21709, f'expected 21709, got {r.estimated_mid}'
print('SMOKE PASSED.')
"
