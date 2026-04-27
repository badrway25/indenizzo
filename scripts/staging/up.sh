#!/usr/bin/env bash
# Avvia (build se necessario) lo stack staging.
# Uso: ./scripts/staging/up.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ ! -f .env.staging ]; then
  echo "ERROR: .env.staging mancante." >&2
  exit 1
fi

docker compose -f docker-compose.staging.yml --env-file .env.staging up -d --build
echo
echo "Stack started. Verifica health:"
echo "  docker compose -f docker-compose.staging.yml ps"
echo "  docker compose -f docker-compose.staging.yml logs -f web"
