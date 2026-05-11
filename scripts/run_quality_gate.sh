#!/usr/bin/env bash
#
# Consolidated local quality gate (P1-QA-1).
#
# Runs every gate the project expects to be green before a merge or
# deploy, in a single command:
#
#   1. `python manage.py check`                         (~1 s)
#   2. `pytest -q`                                      (~3 min)
#   3. `python scripts/audit_legal_content_hygiene.py --strict`  (~1 s)
#   4. Lighthouse: `bash scripts/run_lighthouse_local.sh`        (~2 min)
#
# Fails fast: the first stage to exit non-zero aborts the gate.
# Each stage emits a clear section header + a duration; the final
# line summarises pass/fail + total wall-clock time.
#
# The wrapper does NOT modify any tracked file. The Lighthouse stage
# *writes* into the gitignored `.lighthouseci/` scratch dir and
# overwrites the committed JSON baseline in
# `docs/qa/lighthouse-baseline/` — those touched files are NOT
# automatically discarded by this script (so the operator can
# inspect them on regression) but the help text reminds the user
# to discard with `git checkout -- docs/qa/lighthouse-baseline/`
# when the run is informational only.
#
# Flags:
#   --no-lighthouse   skip stage 4 (useful in tight inner loops)
#   --no-pytest       skip stage 2 (very rarely useful; documents
#                     the gate is intentionally not split further)
#
# Requirements:
#   - venv activated (or python on PATH pointing at the project env);
#   - Django dev server NOT auto-started by this wrapper; for the
#     Lighthouse stage, run `python manage.py runserver 127.0.0.1:8000`
#     in a separate terminal first. The Lighthouse stage exits 2 if
#     the server is unreachable.
#
# Exit codes:
#   0 — every (non-skipped) stage cleared.
#   1 — at least one stage failed.
#   2 — bad invocation (unknown flag).

set -u

# ---- argument parsing ----
SKIP_LIGHTHOUSE=0
SKIP_PYTEST=0

for arg in "$@"; do
  case "${arg}" in
    --no-lighthouse) SKIP_LIGHTHOUSE=1 ;;
    --no-pytest)     SKIP_PYTEST=1 ;;
    -h|--help)
      sed -n '2,40p' "$0" | sed 's/^# \{0,1\}//'
      exit 0
      ;;
    *)
      echo "Unknown flag: ${arg}" >&2
      echo "Run with --help for usage." >&2
      exit 2
      ;;
  esac
done

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

# Activate the project venv if it exists and is not already on
# PATH. Supports Linux/macOS layout (.venv/bin/) and Windows (.venv/
# Scripts/). Mixing system Python with the project's site-packages
# silently fails — e.g. `csp` only lives in the project venv.
if [ -z "${VIRTUAL_ENV:-}" ]; then
  if [ -f "${REPO_ROOT}/.venv/Scripts/activate" ]; then
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.venv/Scripts/activate"
  elif [ -f "${REPO_ROOT}/.venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source "${REPO_ROOT}/.venv/bin/activate"
  fi
fi

# ---- helper: timed stage ----
GATE_T0=$(date +%s)
GATE_FAILED=""

run_stage() {
  local label="$1"
  shift
  local stage_t0=$(date +%s)

  printf '\n'
  printf '============================================================\n'
  printf '  %s\n' "${label}"
  printf '============================================================\n'

  if "$@"; then
    local stage_t1=$(date +%s)
    printf '\n[OK] %s (%d s)\n' "${label}" "$((stage_t1 - stage_t0))"
    return 0
  fi
  local stage_t1=$(date +%s)
  printf '\n[FAIL] %s (%d s)\n' "${label}" "$((stage_t1 - stage_t0))"
  GATE_FAILED="${label}"
  return 1
}

# ---- 1. manage.py check ----
run_stage "[1/4] Django system checks: python manage.py check" \
  python manage.py check
[ -n "${GATE_FAILED}" ] && exit_now=1 || exit_now=0
if [ "${exit_now}" -eq 1 ]; then
  printf '\nGate aborted at: %s\n' "${GATE_FAILED}"
  exit 1
fi

# ---- 2. pytest ----
if [ "${SKIP_PYTEST}" -eq 0 ]; then
  run_stage "[2/4] Test suite: pytest -q" \
    pytest -q
  [ -n "${GATE_FAILED}" ] && {
    printf '\nGate aborted at: %s\n' "${GATE_FAILED}"
    exit 1
  }
else
  printf '\n[SKIP] [2/4] pytest (flag --no-pytest)\n'
fi

# ---- 3. content hygiene ----
run_stage "[3/4] Deontological content hygiene: --strict" \
  python scripts/audit_legal_content_hygiene.py --strict
[ -n "${GATE_FAILED}" ] && {
  printf '\nGate aborted at: %s\n' "${GATE_FAILED}"
  exit 1
}

# ---- 4. Lighthouse ----
if [ "${SKIP_LIGHTHOUSE}" -eq 0 ]; then
  # Pre-flight: server must be up. Don't try to start it ourselves —
  # runserver on Windows races with the dispatcher's chrome-launcher.
  if ! curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:8000/" \
       2>/dev/null | grep -q "^200$"; then
    printf '\n[SKIP] [4/4] Lighthouse — Django not responding on '
    printf '127.0.0.1:8000.\n'
    printf '       Start it in another terminal:\n'
    printf '           python manage.py runserver 127.0.0.1:8000\n'
    printf '       …then re-run, or pass --no-lighthouse to silence.\n'
    GATE_T1=$(date +%s)
    printf '\n============================================================\n'
    printf '  GATE FAILED — Lighthouse stage prerequisite missing\n'
    printf '  Total: %d s\n' "$((GATE_T1 - GATE_T0))"
    printf '============================================================\n'
    exit 1
  fi

  run_stage "[4/4] Lighthouse: bash scripts/run_lighthouse_local.sh" \
    bash scripts/run_lighthouse_local.sh
  [ -n "${GATE_FAILED}" ] && {
    printf '\nGate aborted at: %s\n' "${GATE_FAILED}"
    exit 1
  }
else
  printf '\n[SKIP] [4/4] Lighthouse (flag --no-lighthouse)\n'
fi

# ---- summary ----
GATE_T1=$(date +%s)
TOTAL=$((GATE_T1 - GATE_T0))
printf '\n============================================================\n'
printf '  ALL GATES CLEARED  (%d s total)\n' "${TOTAL}"
printf '============================================================\n'

# Defensive guard. Stage 4 writes the JSON reports to the gitignored
# `artifacts/lighthouse/latest/`; we never expect the tracked
# baseline at `docs/qa/lighthouse-baseline/` to change unless the
# operator explicitly ran the runner with `--update-baseline`.
if ! git diff --quiet docs/qa/lighthouse-baseline/ 2>/dev/null; then
  printf '\nUnexpected: docs/qa/lighthouse-baseline/ was modified by '
  printf 'the gate.\n'
  printf 'This should only happen if you ran with --update-baseline. '
  printf 'If not intentional, discard with:\n'
  printf '    git checkout -- docs/qa/lighthouse-baseline/\n'
fi
exit 0
