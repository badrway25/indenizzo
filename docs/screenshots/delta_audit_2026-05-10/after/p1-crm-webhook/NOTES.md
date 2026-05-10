# P1-CRM-1 — signed lead webhook outbox dispatcher

**Date**: 2026-05-10
**Iter**: `F-p1-crm-1-webhook-dispatcher`
**Branch**: `p1/crm-webhook-dispatcher`

## Scope

Outbox pattern. The platform creates a `LeadWebhookDelivery` row for
every Lead (when the dispatcher is enabled), then a cron-friendly
management command drains the outbox by POSTing each row to a CRM
endpoint (n8n, custom CRM, etc.). The POST is HMAC-SHA256 signed
over `timestamp + "." + body`, idempotency-keyed, retried with
linear backoff up to `CRM_WEBHOOK_MAX_ATTEMPTS`.

No real CRM endpoint is configured by this commit. Tests inject a
fake HTTP poster — zero network access during pytest.

## Files modified / new

**Modified**:
- `config/settings.py` — 8 `CRM_WEBHOOK_*` env-driven settings.
- `apps/crm/checks.py` — `crm.E002` (URL/secret) + `crm.E003`
  (timeout/attempts) production checks.
- `apps/crm/models.py` — `LeadWebhookDelivery` outbox model (no
  PII secret/payload stored).
- `apps/crm/services.py::create_lead_from_form` — failure-soft
  enqueue at the end of the lead creation path.

**New**:
- `apps/crm/webhooks.py` — pure-function dispatcher (build, sign,
  enqueue, dispatch_one, dispatch_pending_webhooks).
- `apps/crm/management/commands/dispatch_crm_webhooks.py`.
- `apps/crm/management/__init__.py`,
  `apps/crm/management/commands/__init__.py`.
- `apps/crm/migrations/0005_leadwebhookdelivery.py`.
- `apps/crm/test_webhook_dispatcher.py` (28 tests).
- `docs/integrations/N8N_CRM_WEBHOOK.md` — full receiver runbook.
- `docs/screenshots/delta_audit_2026-05-10/after/p1-crm-webhook/NOTES.md` (this).

## Settings

| Env var | Default | Purpose |
|---|---|---|
| `CRM_WEBHOOK_ENABLED` | `False` | Master toggle |
| `CRM_WEBHOOK_URL` | empty | Receiver URL (must be `https://` in prod) |
| `CRM_WEBHOOK_SECRET` | empty | HMAC secret (≥32 chars in prod) |
| `CRM_WEBHOOK_TIMEOUT_SECONDS` | `10` | per-POST timeout |
| `CRM_WEBHOOK_MAX_ATTEMPTS` | `5` | dead after this |
| `CRM_WEBHOOK_BACKOFF_SECONDS` | `300` | linear backoff base |
| `CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY` | `False` | privacy-aware summary opt-in |
| `CRM_WEBHOOK_PAYLOAD_VERSION` | `v1` | payload schema marker |

## System checks

| ID | Trigger |
|---|---|
| `crm.E002` | `ENABLED=True` with empty/non-HTTPS URL or empty/<32char secret |
| `crm.E003` | timeout ≤ 0 or max_attempts < 1 |

Both silent in `DEBUG=True`. `crm.E001` (lead notification email
recipients) pre-existing, unchanged.

## Payload schema (`v1`)

Keys (sorted, canonical): `case_type`, `consent`, `contact`,
`country`, `created_at`, `event_type`, `lead_public_id`, `locale`,
`mandate_status`, `message`, `payload_version`, `source_form`,
`utm`.

`consent` includes `privacy_given/at/version` and
`special_categories_given/at/version`. `consent.special_categories_summary`
appears ONLY when `CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY=True`,
and is itself a *summary* (booleans + scope label), never raw
health/judicial detail.

Full reference example in `docs/integrations/N8N_CRM_WEBHOOK.md`.

## HMAC signature

- Algorithm: `HMAC-SHA256`.
- Signed string: `timestamp + "." + canonical_body`.
- Header format: `X-Indennizzati-Signature: sha256=<hex>`.
- Companion headers: `X-Indennizzati-Event`,
  `X-Indennizzati-Payload-Version`,
  `X-Indennizzati-Idempotency-Key`,
  `X-Indennizzati-Timestamp`.

`canonical_json()` enforces sorted keys and no whitespace so the
signature is byte-stable across runtimes. `constant_time_signature_check()`
is exposed for receivers and tests.

## Retry / idempotency behavior

- `idempotency_key = sha256(public_id + ":" + event_type)` — stable
  across retries; `enqueue_lead_webhook` is a no-op on the second
  call with the same `(lead, event_type)`.
- 2xx → `delivered`. 408/429/5xx → `pending` with
  `next_attempt_at = now + (backoff_base × attempts)`. Other 4xx →
  `failed` (non-retriable). Network/timeout exception → same as 5xx.
- `attempts` increments on every dispatch attempt (including the
  network-error path). When `attempts >= max_attempts`, status
  becomes `dead` and `next_attempt_at=None`.

The `LeadWebhookDelivery` row stores `target_url_domain` (host only,
audit-friendly) but never the full URL or any secret.

## Management command

`python manage.py dispatch_crm_webhooks`

| Flag | Purpose |
|---|---|
| `--limit N` | drain up to N rows (default 50) |
| `--dry-run` | count candidates, no DB mutation, no POST |
| `--delivery-id ID` | dispatch one row by primary key |
| `--force` | bypass `next_attempt_at` (only with --delivery-id) |
| `--now ISO` | clock pin for cron / tests |

Refuses to operate (except in dry-run) if `CRM_WEBHOOK_ENABLED=False`.

Smoke output (default dev settings, no rows):

```
================================================================
CRM webhook dispatcher [DRY-RUN] limit=50
================================================================
now:        2026-05-10T18:57:58.275940+00:00
candidates: 0
Dry-run: no row dispatched. Drop --dry-run to actually send.
```

## Tests

`apps/crm/test_webhook_dispatcher.py` — **28 tests**, all green:

- enqueue gating (disabled / enabled / idempotent);
- payload contract (consent fields, special-categories OFF/ON);
- signature round-trip + key sensitivity;
- canonical JSON determinism + idempotency-key stability;
- system check matrix (`crm.E002` × 3, `crm.E003` × 2,
  silent-when-disabled, passes-with-full-config);
- dispatch state machine (2xx → delivered, 5xx → retry, network
  exception → retry, 4xx → failed, dead-after-max-attempts);
- management command: dry-run, bulk dispatch, refuse-when-disabled,
  delivery-id due-date enforcement, --force override;
- integration: `create_lead_from_form` enqueues when enabled.

| Run | Result |
|-----|--------|
| `pytest apps/crm/test_webhook_dispatcher.py -q` | 28 passed |
| `pytest apps/crm -q` | 76 passed |
| `pytest apps/core apps/crm apps/compliance apps/cases -q` | 1214 passed, 1 skipped |
| `pytest -q` (full) | **1767 passed, 1 skipped** (zero regressions, +28 from P1-SEC-1 baseline) |
| `python manage.py check` | clean (only the expected `core.W001` STUDIO_* dev warning) |

## Browser live

Not a UI batch — no screenshot captured. Verified that the integration
into `create_lead_from_form` does not break the contact funnel via the
test `test_create_lead_from_form_enqueues_when_enabled` (which exercises
the full service path, asserts the Lead is created and the delivery is
enqueued).

The CSP, fonts, consent block and mandate notice from prior iters are
all unchanged on this branch.

## What the Studio still has to do

Before enabling the dispatcher in production:

1. Stand up the n8n workflow following
   `docs/integrations/N8N_CRM_WEBHOOK.md`.
2. Generate a strong shared secret:
   ```
   python -c "import secrets;print(secrets.token_urlsafe(48))"
   ```
3. Set the env vars in production:
   - `CRM_WEBHOOK_ENABLED=True`
   - `CRM_WEBHOOK_URL=https://<n8n-host>/webhook/lead-created`
   - `CRM_WEBHOOK_SECRET=<the-generated-string>`
4. Schedule a cron (every 1-5 minutes is sane):
   ```
   */5 * * * * cd /app && python manage.py dispatch_crm_webhooks --limit 50
   ```
5. Optional: enable
   `CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY=True` if the n8n
   workflow needs the boolean+version summary of GDPR art. 9 consent
   (the platform never sends raw health/judicial detail).

## Next batch suggested

1. **P1-SEO-2** — Lighthouse CI gating (performance budget +
   accessibility regression). With local fonts shipped (P1-SEC-1) the
   first-paint metric should improve; gating now prevents future
   regressions.
2. **P1-SEC-3** — WAF/CDN edge security (Cloudflare / Caddy +
   CrowdSec) once the platform reaches production-style staging.
3. **Tunisia/EU650 review + merge** — branch
   `work/tunisia-csp-eu650-restore` (`b44a5c2`) waits for Studio
   review.
