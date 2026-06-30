#!/usr/bin/env bash
#
# P54 — Safe staging deploy helper for product/staging-readiness-p0 (after PR #22).
#
# SAFE BY DEFAULT: with no flags it only runs READ-ONLY checks and prints the plan.
# Mutating steps (migrate, collectstatic, precompress, restart) run ONLY with
# APPLY=1. It refuses to run on the wrong branch, refuses a non-fast-forward pull,
# and refuses to apply if the mandatory STUDIO_* env vars are missing. It restarts
# a service ONLY if SERVICE_NAME is set. No secret value is printed or committed.
#
# Usage:
#   bash scripts/deploy_staging_readiness_p54.sh            # dry plan (read-only)
#   APPLY=1 SERVICE_NAME=myapp bash scripts/deploy_staging_readiness_p54.sh
#
# Substitute paths/service for your host. DO NOT run against production blindly.

set -euo pipefail

TARGET_BRANCH="product/staging-readiness-p0"
APPLY="${APPLY:-0}"
SERVICE_NAME="${SERVICE_NAME:-}"
PY="${PY:-python}"

log() { printf '[p54] %s\n' "$*"; }
die() { printf '[p54][ERROR] %s\n' "$*" >&2; exit 1; }

# --- 1. Branch guard (anti-rollback: only this branch, only fast-forward) ------
current="$(git rev-parse --abbrev-ref HEAD)"
[ "$current" = "$TARGET_BRANCH" ] || die "on '$current', expected '$TARGET_BRANCH'"
git fetch origin "$TARGET_BRANCH"
local_sha="$(git rev-parse HEAD)"
remote_sha="$(git rev-parse "origin/$TARGET_BRANCH")"
if [ "$local_sha" != "$remote_sha" ]; then
  git merge-base --is-ancestor "$local_sha" "$remote_sha" \
    || die "local is not behind origin by fast-forward; refusing (no rollback / no force)"
fi

# --- 2. Mandatory STUDIO_* env (names only; never print values) ----------------
REQUIRED_STUDIO=(STUDIO_LEAD_LAWYER_NAME STUDIO_BAR_ASSOCIATION STUDIO_VAT_NUMBER \
  STUDIO_PEC_EMAIL STUDIO_PHYSICAL_ADDRESS STUDIO_PROFESSIONAL_INSURANCE_INSURER \
  STUDIO_PROFESSIONAL_INSURANCE_POLICY)
missing=()
for v in "${REQUIRED_STUDIO[@]}"; do
  [ -n "${!v:-}" ] || missing+=("$v")
done
if [ "${#missing[@]}" -gt 0 ]; then
  log "STUDIO_* missing: ${missing[*]}"
  [ "$APPLY" = "1" ] && die "STUDIO_* required before APPLY (DEBUG=False would error on core.W001)"
fi

# --- 3. Read-only checks (always) ---------------------------------------------
log "git pull --ff-only origin $TARGET_BRANCH"
[ "$APPLY" = "1" ] && git pull --ff-only origin "$TARGET_BRANCH"
log "manage.py check"
"$PY" manage.py check
log "manage.py makemigrations --check --dry-run"
"$PY" manage.py makemigrations --check --dry-run
log "pending migrations:"
"$PY" manage.py showmigrations cases compensation crm | grep -E '\[ \]' || log "  (none pending)"

if [ "$APPLY" != "1" ]; then
  log "DRY PLAN complete. Re-run with APPLY=1 (and STUDIO_* set, DB backed up) to deploy."
  exit 0
fi

# --- 4. Backup reminder (do not invent credentials) ---------------------------
log "REMINDER: ensure a DB backup exists before migrate (see runbook §E). Pausing 5s."
sleep 5 || true

# --- 5. Mutating deploy steps (APPLY=1 only) ----------------------------------
log "migrate"
"$PY" manage.py migrate
log "compilemessages"
"$PY" manage.py compilemessages
log "collectstatic --noinput"
"$PY" manage.py collectstatic --noinput
log "precompress_static"
"$PY" manage.py precompress_static

# --- 6. Restart only if SERVICE_NAME is set -----------------------------------
if [ -n "$SERVICE_NAME" ]; then
  log "systemctl restart $SERVICE_NAME"
  systemctl restart "$SERVICE_NAME"
else
  log "SERVICE_NAME unset — skipping restart (restart your app server manually)."
fi

# --- 7. Smoke placeholder (fill <host>) ---------------------------------------
log "Run HTTP smoke (see runbook §G): /healthz/ /it/ /it/guided/ /ar/ ... expect 200/302, zero 5xx."
log "Deploy steps done. Complete the §I release checklist + browser smoke."
