#!/usr/bin/env bash
# Esegue gli script read-only di prep Postgres dentro il container web.
# Uso: ./scripts/local/smoke.sh
#
# 1. check_database_backend.py: stampa engine/vendor/migrations.
# 2. smoke_database_readiness.py: verifica migrate + (se IT approved
#    presente) il contratto smoke 35/10/0 → 26 268 / 27 353 / 28 439.
set -euo pipefail
cd "$(dirname "$0")/../.."

run_in_web() {
    docker compose -f docker-compose.local.yml --env-file .env.local.docker \
        exec -T web python "$@"
}

echo "=== check_database_backend.py ==="
run_in_web scripts/staging/check_database_backend.py
echo
echo "=== smoke_database_readiness.py ==="
run_in_web scripts/staging/smoke_database_readiness.py
