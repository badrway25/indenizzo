#!/usr/bin/env bash
# Wrapper per `manage.py` nel container web LOCALE.
# Uso: ./scripts/local/manage.sh <comando django>
# Es : ./scripts/local/manage.sh migrate
#       ./scripts/local/manage.sh createsuperuser
#       ./scripts/local/manage.sh shell
set -euo pipefail
cd "$(dirname "$0")/../.."

docker compose -f docker-compose.local.yml --env-file .env.local.docker \
    exec web python manage.py "$@"
