#!/usr/bin/env bash
# Export JSON dello stato approvato su staging (no PII).
# Output finisce in /app/legal_data/exports/ dentro il container,
# montato sul host come ./legal_data/exports/.
# Uso: ./scripts/staging/export_approved.sh
set -euo pipefail
cd "$(dirname "$0")/../.."

./scripts/staging/manage.sh export_italy_tun_dataset
echo
echo "Export disponibile sul host in legal_data/exports/"
