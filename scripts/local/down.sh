#!/usr/bin/env bash
# Ferma lo stack docker locale SENZA cancellare volumi.
# Per rimuovere i volumi: aggiungere -v manualmente (con cautela:
# perde i dati Postgres locali). Vedi docs/deploy/LOCAL_DOCKER_COMPOSE.md.
# Uso: ./scripts/local/down.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

docker compose -f docker-compose.local.yml --env-file .env.local.docker down "$@"
