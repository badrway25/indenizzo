#!/usr/bin/env bash
# Avvia (build se necessario) lo stack docker LOCALE (web+db+redis).
# Uso: ./scripts/local/up.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

if [ ! -f .env.local.docker ]; then
  echo "ERROR: .env.local.docker mancante." >&2
  echo "       Copialo da .env.local.docker.example e riprova:" >&2
  echo "         cp .env.local.docker.example .env.local.docker" >&2
  exit 1
fi

docker compose -f docker-compose.local.yml --env-file .env.local.docker up --build "$@"
