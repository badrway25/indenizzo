#!/usr/bin/env bash
# Backup pg_dump del DB Postgres su file timestampato.
# Output: backups/staging_<YYYYMMDD-HHMMSS>.sql
# Uso: ./scripts/staging/backup_db.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

mkdir -p backups
TS=$(date +%Y%m%d-%H%M%S)
OUT="backups/staging_${TS}.sql"

# shellcheck disable=SC1091
. .env.staging

docker compose -f docker-compose.staging.yml --env-file .env.staging \
    exec -T db pg_dump -U "${POSTGRES_USER:-badrane}" "${POSTGRES_DB:-badrane_staging}" > "$OUT"

echo "Backup written: $OUT ($(wc -c < "$OUT") bytes)"
echo "Move to off-site storage prima del prossimo turno operativo."
