#!/usr/bin/env bash
# Bootstrap one-shot del modulo Italia TUN su staging.
#
# Pre-condizioni:
#   - stack già avviato (./scripts/staging/up.sh);
#   - PDF G.U. in legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf;
#   - CSV TUN in legal_data/sources/italy/tun_2025/tun_2025_rows.csv.
#
# Lo script NON promuove fonte/dataset/formula a `approved`: quella
# resta atto umano da fare via admin o con uno script ad hoc dello
# Studio (vedi STAGING_DEPLOY.md §6).
set -euo pipefail
cd "$(dirname "$0")/../.."

PDF_PATH=legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf
CSV_PATH=legal_data/sources/italy/tun_2025/tun_2025_rows.csv

if [ ! -f "$PDF_PATH" ]; then
  echo "ERROR: PDF G.U. mancante in $PDF_PATH" >&2
  exit 1
fi
if [ ! -f "$CSV_PATH" ]; then
  echo "ERROR: CSV TUN mancante in $CSV_PATH" >&2
  exit 1
fi

run() {
  ./scripts/staging/manage.sh "$@"
}

echo "=== seed_jurisdictions ==="
run seed_jurisdictions --quiet

echo "=== seed_italy_legal_sources ==="
run seed_italy_legal_sources --quiet

echo "=== import_italy_tun_2025 (PDF) ==="
run import_italy_tun_2025 --source-file "/app/$PDF_PATH"

echo "=== import_italy_tun_2025 (CSV) ==="
run import_italy_tun_2025 --csv "/app/$CSV_PATH"

echo
echo "Bootstrap dati TUN completato."
echo
echo "Stato attuale (atteso DRAFT/needs_review fino ad approval umana):"
run shell -c "
from apps.legal_sources.models import LegalSource
from apps.compensation.models import CompensationDataset, CalculationFormula, CompensationTableRow
src = LegalSource.objects.filter(slug='it-dpr-12-2025-tun-danno-biologico').first()
ds  = CompensationDataset.objects.filter(version_label='DPR-12-2025').first()
fm  = CalculationFormula.objects.filter(code='italy_art_138_tun_2025_base').first()
print(f'source.status={src.status} dataset.status={ds.status} formula.status={fm.status}')
print(f'rows={CompensationTableRow.objects.filter(dataset=ds).count()}')
"
echo
echo "Prossimo step (atto umano):"
echo "  1. Admin -> CalculationFormula -> aggiorna parameters runtime."
echo "  2. Admin -> LegalSource -> LegalReview decision=approve."
echo "  3. Promuovi cumulativamente status: source -> dataset -> formula."
echo "  4. Smoke test: ./scripts/staging/smoke.sh"
