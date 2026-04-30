#!/usr/bin/env bash
# Tail dei log dei servizi locali.
# Uso: ./scripts/local/logs.sh           # tutti
#       ./scripts/local/logs.sh web      # solo web
#       ./scripts/local/logs.sh db redis # selezione
set -euo pipefail
cd "$(dirname "$0")/../.."

docker compose -f docker-compose.local.yml --env-file .env.local.docker logs -f "$@"
