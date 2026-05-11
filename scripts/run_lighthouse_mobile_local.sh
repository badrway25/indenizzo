#!/usr/bin/env bash
#
# Local Lighthouse CI runner — MOBILE preset (P2-SEO-1).
#
# Companion of `scripts/run_lighthouse_local.sh` (desktop preset).
#
# Usage:
#   bash scripts/run_lighthouse_mobile_local.sh                  # gate run
#   bash scripts/run_lighthouse_mobile_local.sh --update-baseline # refresh
#
# Defaults to writing JSON into the gitignored
# `artifacts/lighthouse-mobile/latest/` so a routine gate run does
# NOT dirty the working tree. With `--update-baseline` the runner
# writes into the tracked `docs/qa/lighthouse-mobile-baseline/`.
#
# Mobile budget (in `lighthouserc.mobile.json`):
#   performance >= 0.75
#   accessibility >= 0.90
#   best-practices >= 0.90
#   seo >= 0.90
#
# The performance floor is intentionally lower than the desktop
# preset (0.80) because mobile CPU throttling x4 + 3G-like network
# emulation introduce real-world variance the desktop preset hides.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

UPDATE_BASELINE=0
for arg in "$@"; do
  case "${arg}" in
    --update-baseline) UPDATE_BASELINE=1 ;;
    -h|--help)
      sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown flag: ${arg}" >&2
      echo "Run with --help for usage." >&2
      exit 2
      ;;
  esac
done

if [ "${UPDATE_BASELINE}" -eq 1 ]; then
  OUT_DIR="docs/qa/lighthouse-mobile-baseline"
  OUT_MODE="UPDATE-BASELINE (writes tracked files in ${OUT_DIR})"
else
  OUT_DIR="artifacts/lighthouse-mobile/latest"
  OUT_MODE="GATE (writes gitignored ${OUT_DIR}/)"
fi
printf '[lighthouse mobile runner] mode: %s\n' "${OUT_MODE}"
mkdir -p "${OUT_DIR}"

if ! curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/" \
     2>/dev/null | grep -q "^200$"; then
  echo "ERROR: Django is not responding on http://127.0.0.1:8000/."
  echo "Start it in another terminal:"
  echo "    python manage.py runserver 127.0.0.1:8000"
  exit 2
fi

# P2-PERF-1: pre-compress static .css/.js/.svg so WhiteNoise serves
# `Accept-Encoding: gzip` responses. Idempotent. Mirror of the
# desktop runner.
python manage.py precompress_static >/dev/null 2>&1 \
  && echo "[lighthouse mobile runner] static .gz companions ready" \
  || echo "[lighthouse mobile runner] WARNING: could not pre-compress static files (venv off?)"

# P2-IMG-1: same WebP-companion generation as the desktop runner.
python manage.py compress_pexels_images >/dev/null 2>&1 \
  && echo "[lighthouse mobile runner] pexels WebP companions ready" \
  || echo "[lighthouse mobile runner] WARNING: could not generate WebP variants"

# Pairs of "label:URL_PATH". Keep in sync with lighthouserc.mobile.json.
TARGETS=(
  "home-it:/"
  "contact:/contact/"
  "wizard:/wizard/"
  "privacy:/privacy/"
  "disclaimer:/disclaimer/"
  "countries:/countries/"
  "case-types:/case-types/"
  "ar-home:/ar/"
)

# Budgets — keep in sync with lighthouserc.mobile.json.
PERF_MIN="0.75"
A11Y_MIN="0.90"
BP_MIN="0.90"
SEO_MIN="0.90"

global_failed=0

for entry in "${TARGETS[@]}"; do
  label="${entry%%:*}"
  path="${entry#*:}"
  url="http://127.0.0.1:8000${path}"
  outfile="${OUT_DIR}/${label}-mobile.json"
  printf '\n[%s] %s\n' "${label}" "${url}"

  npx --yes lighthouse@latest "${url}" \
    --output=json \
    --output-path="${outfile}" \
    --form-factor=mobile \
    --screenEmulation.mobile=true \
    --screenEmulation.width=390 \
    --screenEmulation.height=844 \
    --throttling.cpuSlowdownMultiplier=4 \
    --chrome-flags="--headless --no-sandbox" \
    --only-categories=performance,accessibility,best-practices,seo \
    --quiet \
    >/dev/null 2>&1 || true

  if [ ! -f "${outfile}" ]; then
    echo "  FAILED: no JSON written. Aborting."
    exit 3
  fi

  python - <<EOF || global_failed=1
import json, sys
d = json.load(open("${outfile}", encoding="utf-8"))
cats = d.get("categories", {})
def g(name): return cats.get(name, {}).get("score") or 0.0
perf, a11y, bp, seo = g("performance"), g("accessibility"), g("best-practices"), g("seo")
print(f"  scores  perf={perf:.2f}  a11y={a11y:.2f}  best={bp:.2f}  seo={seo:.2f}")
fail = []
if perf < ${PERF_MIN}: fail.append(f"performance {perf:.2f} < ${PERF_MIN}")
if a11y < ${A11Y_MIN}: fail.append(f"accessibility {a11y:.2f} < ${A11Y_MIN}")
if bp < ${BP_MIN}:    fail.append(f"best-practices {bp:.2f} < ${BP_MIN}")
if seo < ${SEO_MIN}:  fail.append(f"seo {seo:.2f} < ${SEO_MIN}")
if fail:
    print("  GATE FAILED: " + "; ".join(fail))
    sys.exit(1)
EOF
done

if [ "${global_failed}" -ne 0 ]; then
  echo
  echo "RESULT: at least one URL failed the mobile Lighthouse gate."
  exit 1
fi

echo
echo "RESULT: all URLs cleared the mobile gate."
