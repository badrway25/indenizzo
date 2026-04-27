#!/usr/bin/env bash
# Build dell'immagine staging.
# Uso: ./scripts/staging/build.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ ! -f .env.staging ]; then
  echo "ERROR: .env.staging mancante. Copia .env.staging.example e popola." >&2
  exit 1
fi

docker compose -f docker-compose.staging.yml --env-file .env.staging build "$@"
echo "Build OK. Run ./scripts/staging/up.sh per avviare."
