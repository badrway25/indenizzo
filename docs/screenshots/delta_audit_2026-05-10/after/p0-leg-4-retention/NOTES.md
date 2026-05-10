# P0-LEG-4 — retention policy + cron scaffold

**Date**: 2026-05-10
**Iter**: `F-p0-leg-4-retention`
**Branch**: `audit/indennizzati-platform`

## Scope

Technical scaffold only. NO legal retention policy is signed. NO real
data is deleted. Everything is dry-run by default; anonymize requires
explicit confirmation; physical delete is double-gated and refused
in P0 unless the operator passes both `--yes-i-understand` and
`--allow-delete` and the caller passes `allow_delete=True` to
`run_retention()`.

## What changed

### Settings (`config/settings.py`)

- `RETENTION_POLICY_VERSION` (default `working-copy-2026-05-10`)
- `RETENTION_ENABLED` (default `False`)
- `RETENTION_MODE` (default `dry_run`; allowed: `dry_run|anonymize|delete`)
- `RETENTION_LEAD_DAYS` (dev default 365)
- `RETENTION_SIMULATION_DAYS` (dev default 365)
- `RETENTION_CONSENT_RECORD_DAYS` (dev default 1825)
- `RETENTION_AUDIT_LOG_DAYS` (dev default 1825)
- `RETENTION_REQUIRE_SIGNED_VERSION` (default `True`)

The day defaults are SCAFFOLD VALUES, not legal advice.

### Models / migrations

- `apps/compliance/models.py::RetentionRunLog` (new)
- `apps/compliance/migrations/0004_retentionrunlog.py`
- `apps/crm/models.py::Lead.anonymized` + `anonymized_at` (new)
- `apps/crm/migrations/0003_lead_anonymized_lead_anonymized_at.py`

`Simulation.anonymized` already existed.

### Service (`apps/compliance/retention.py`)

Extended with the wide-retention API:

- `RETENTION_MODES = ("dry_run", "anonymize", "delete")`
- `DRAFT_MARKERS = ("working-copy", "draft")`
- `get_retention_cutoffs(now=None) -> RetentionCutoffs`
- `collect_retention_candidates(now=None) -> dict`
- `run_retention(mode, now=None, executed_by="system", notes="", allow_delete=False)`

Behavior matrix:

| mode | Lead | Simulation | ConsentRecord | PrivacyAuditEvent |
|------|------|-----------|---------------|-------------------|
| `dry_run` | count | count | count | count |
| `anonymize` | redact PII fields, set `anonymized=True` | redact `input_data`/PII | count only | count only |
| `delete` | refused unless `allow_delete=True` (and even then only Lead+Simulation) | refused unless `allow_delete=True` | NEVER deleted | NEVER deleted |

Anonymize keeps:
- `public_id`, `created_at`,
- `country_id`, `case_type`, `preferred_language`, `status`, `priority`,
- `utm_*`,
- consent versions/timestamps/given flags,
- the `consent_record` FK so the ledger trail survives.

Anonymize redacts:
- `first_name`, `last_name`, `email` (→ `anonymized@example.invalid`),
- `phone_number`, `message`,
- `ip_address`, `user_agent`, `source_path`, `session_key`,
- `internal_notes`, `assigned_to`, `user`.

### Management command

`python manage.py run_retention_policy`

Flags: `--dry-run`, `--mode=dry_run|anonymize|delete`, `--now=ISO`,
`--yes-i-understand`, `--allow-delete`, `--executed-by=…`.

Refuses:
- any non-dry-run mode without `--yes-i-understand`,
- `--mode=delete` without `--allow-delete`.

Output prints policy version, cutoffs, per-scope candidate counts,
the `RetentionRunLog.id`, and the action performed.

### System check `compliance.E001`

In `DEBUG=False` AND `RETENTION_REQUIRE_SIGNED_VERSION=True`, blocks
`manage.py check` (and the deploy) when:

1. `RETENTION_POLICY_VERSION` is empty,
2. `RETENTION_POLICY_VERSION` contains `working-copy` or `draft`,
3. `RETENTION_MODE` is not in the allowed set,
4. `RETENTION_ENABLED=True` AND `RETENTION_MODE=dry_run` (ambiguous).

Silent in dev (`DEBUG=True`).

### Tests (`apps/compliance/test_retention_policy.py`)

16 tests covering:

- system check matrix (working-copy / empty / invalid mode / enabled+dry_run / signed-and-disabled);
- dry-run mutates nothing on Lead/Simulation;
- dry-run creates a `RetentionRunLog` with `status=success`;
- anonymize redacts PII on expired Lead;
- anonymize skips Lead inside the retention window;
- anonymize keeps consent versions and the `consent_record` FK;
- delete mode refuses without `allow_delete=True`, logs the failure;
- management command rejects `--mode=anonymize` without `--yes-i-understand`;
- management command rejects `--mode=delete` without `--allow-delete`;
- management command dry-run prints candidate counts;
- `get_retention_cutoffs` honours `RETENTION_*_DAYS` settings;
- `collect_retention_candidates` counts ConsentRecord and PrivacyAuditEvent
  but anonymize does not delete them.

## Browser smoke

No UI changes were introduced. Verified the public pages still serve
200 OK after the migration:

```
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/contact/
200
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/wizard/it/road-accident/
200
$ curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8000/
200
```

Consent block (P0-LEG-3 work) still renders on `/contact/`. Footer
identification (P0-CODICE-3) still renders. No new screenshots
captured because no UI surface changed.

## What the Studio still has to sign

Before `RETENTION_ENABLED=True` can ship to production:

1. Sign the wording of the retention policy (per scope):
   - Lead → days, anonymize-vs-delete decision;
   - Simulation → days;
   - ConsentRecord → likely retained for the limitation period of
     contractual / GDPR claims (study with legal);
   - PrivacyAuditEvent → audit traceability period.
2. Set `RETENTION_POLICY_VERSION=2026-XX-XX-final` env var (else
   `compliance.E001` blocks `manage.py check`).
3. Decide `RETENTION_MODE` for production:
   - `anonymize` (recommended once policy is signed),
   - `delete` ONLY for scopes where the policy explicitly allows it
     (and `--allow-delete` passed by the operator each time).
4. Decide `RETENTION_*_DAYS` real values (the dev defaults are
   placeholders, never numbers we negotiated).
5. Wire a cron / Celery beat schedule to invoke
   `run_retention_policy` automatically (out of scope for P0-LEG-4 —
   this is the cron scaffold, not the cron itself).

## Suite

`pytest`: 1679 passed, 1 skipped (zero regressions).
`python manage.py check`: clean (only the expected `core.W001` warning
about empty STUDIO_* fields in dev).

## Files touched (P0-LEG-4 only)

- `config/settings.py`
- `apps/compliance/models.py`
- `apps/compliance/migrations/0004_retentionrunlog.py` (new)
- `apps/compliance/retention.py`
- `apps/compliance/checks.py` (new)
- `apps/compliance/apps.py`
- `apps/compliance/management/commands/run_retention_policy.py` (new)
- `apps/compliance/test_retention_policy.py` (new)
- `apps/crm/models.py`
- `apps/crm/migrations/0003_lead_anonymized_lead_anonymized_at.py` (new)
