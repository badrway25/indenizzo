#!/usr/bin/env bash
#
# Local Lighthouse CI runner (P1-SEO-2 + P1-QA-1A).
#
# Usage:
#   bash scripts/run_lighthouse_local.sh                  # gate run
#   bash scripts/run_lighthouse_local.sh --update-baseline # refresh baseline
#
# What it does:
# 1. Refuses to run if Django is not already serving on :8000 (the
#    runner does not start the dev server itself — it would race
#    with manage.py reload + leave dangling processes on Windows).
# 2. Drives `npx lighthouse@latest` against every URL in
#    lighthouserc.json's `ci.collect.url` list.
# 3. Output destination depends on mode:
#    - default (gate run): writes JSON into the gitignored
#      `artifacts/lighthouse/latest/` so a normal gate run does NOT
#      dirty the working tree;
#    - `--update-baseline`: writes JSON into the tracked
#      `docs/qa/lighthouse-baseline/` (this IS the only command
#      that intentionally modifies a tracked baseline file).
# 4. Exits non-zero if any score is below the gating threshold
#    (performance 0.80, the rest 0.90).
#
# On Windows the chrome-launcher prints an EPERM during temp-dir
# cleanup. The JSON is fully written before the error fires; the
# script tolerates it explicitly.

set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

UPDATE_BASELINE=0
for arg in "$@"; do
  case "${arg}" in
    --update-baseline) UPDATE_BASELINE=1 ;;
    -h|--help)
      sed -n '2,30p' "$0" | sed 's/^# \{0,1\}//'
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
  OUT_DIR="docs/qa/lighthouse-baseline"
  OUT_MODE="UPDATE-BASELINE (writes tracked files in ${OUT_DIR})"
else
  OUT_DIR="artifacts/lighthouse/latest"
  OUT_MODE="GATE (writes gitignored ${OUT_DIR}/)"
fi
printf '[lighthouse runner] mode: %s\n' "${OUT_MODE}"
mkdir -p "${OUT_DIR}"

if ! curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/" | grep -q "^200$"; then
  echo "ERROR: Django is not responding on http://127.0.0.1:8000/."
  echo "Start it in another terminal:"
  echo "    python manage.py runserver 127.0.0.1:8000"
  exit 2
fi

# P2-PERF-1: ensure pre-compressed .gz companions exist for the static
# CSS / JS / SVG files. WhiteNoise serves them when the client sends
# `Accept-Encoding: gzip`; without them Lighthouse measures uncompressed
# transfer and the perf score is artificially low. Idempotent (skips
# fresh companions). Failure here is non-fatal: it can mean the venv
# isn't active, but the Lighthouse run still surfaces the impact.
python manage.py precompress_static >/dev/null 2>&1 \
  && echo "[lighthouse runner] static .gz companions ready" \
  || echo "[lighthouse runner] WARNING: could not pre-compress static files (venv off?)"

# Pairs of "label:URL_PATH". Keep in sync with lighthouserc.json.
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

PERF_MIN="0.80"
A11Y_MIN="0.90"
BP_MIN="0.90"
SEO_MIN="0.90"

global_failed=0

for entry in "${TARGETS[@]}"; do
  label="${entry%%:*}"
  path="${entry#*:}"
  url="http://127.0.0.1:8000${path}"
  outfile="${OUT_DIR}/${label}-desktop.json"
  printf '\n[%s] %s\n' "${label}" "${url}"

  npx --yes lighthouse@latest "${url}" \
    --output=json \
    --output-path="${outfile}" \
    --preset=desktop \
    --chrome-flags="--headless --no-sandbox" \
    --only-categories=performance,accessibility,best-practices,seo \
    --quiet \
    >/dev/null 2>&1 || true

  if [ ! -f "${outfile}" ]; then
    echo "  FAILED: no JSON written. Aborting."
    exit 3
  fi

  # Parse + gate via Python (already on PATH in this venv).
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
  echo "RESULT: at least one URL failed the Lighthouse gate."
  exit 1
fi

echo
echo "RESULT: all URLs cleared the gate."
