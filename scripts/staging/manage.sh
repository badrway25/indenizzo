#!/usr/bin/env bash
# Wrapper per `manage.py` nel container web.
# Uso: ./scripts/staging/manage.sh <comando django>
# Es : ./scripts/staging/manage.sh migrate
#       ./scripts/staging/manage.sh createsuperuser
#       ./scripts/staging/manage.sh shell
set -euo pipefail
cd "$(dirname "$0")/../.."

docker compose -f docker-compose.staging.yml --env-file .env.staging \
    exec web python manage.py "$@"
