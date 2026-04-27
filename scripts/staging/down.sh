#!/usr/bin/env bash
# Spegne lo stack senza cancellare i volumi (DB + media restano).
# Uso: ./scripts/staging/down.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

docker compose -f docker-compose.staging.yml --env-file .env.staging down
echo "Stack stopped. Data volumes preserved."
