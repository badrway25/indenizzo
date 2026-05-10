# n8n / CRM webhook integration

**Iter**: F-p1-crm-1-webhook-dispatcher
**Date**: 2026-05-10

This document is the runbook for the receiver side of the
`LeadWebhookDelivery` outbox: how to wire an n8n workflow (or any
HTTP endpoint) so that the platform can ship a Lead event securely.

The dispatcher itself is documented in `apps/crm/webhooks.py`.

---

## 1. What the dispatcher sends

For every `Lead` created via `/contact/`, when `CRM_WEBHOOK_ENABLED=True`,
the dispatcher creates a `LeadWebhookDelivery` row with:

- `event_type = "lead.created"`
- `payload_version = "v1"`
- a stable `idempotency_key` = `sha256(public_id + ":" + event_type)`

A management command (`python manage.py dispatch_crm_webhooks`)
runs from cron and POSTs the row to `CRM_WEBHOOK_URL`. Each POST
carries:

### HTTP method

`POST` with `Content-Type: application/json`.

### Headers

| Header | Description |
|---|---|
| `X-Indennizzati-Event` | event name, e.g. `lead.created` |
| `X-Indennizzati-Payload-Version` | currently `v1` |
| `X-Indennizzati-Idempotency-Key` | stable across retries — receiver MUST dedupe |
| `X-Indennizzati-Timestamp` | unix epoch seconds, used in the HMAC string |
| `X-Indennizzati-Signature` | `sha256=<hex>` HMAC over `timestamp + "." + body` |

### Body — payload `v1` example

```json
{
  "case_type": "",
  "consent": {
    "privacy_at": "2026-05-10T17:30:12+00:00",
    "privacy_given": true,
    "privacy_version": "2026-09-15-final",
    "special_categories_at": "2026-05-10T17:30:12+00:00",
    "special_categories_given": true,
    "special_categories_version": "2026-09-15-final"
  },
  "contact": {
    "email": "maria@example.test",
    "first_name": "Maria",
    "last_name": "Rossi",
    "phone_number": "+39 0000000"
  },
  "country": "",
  "created_at": "2026-05-10T17:30:12+00:00",
  "event_type": "lead.created",
  "lead_public_id": "00000000-1111-2222-3333-444444444444",
  "locale": "it",
  "mandate_status": "mandate_required",
  "message": "Vorrei una consulenza per un incidente.",
  "payload_version": "v1",
  "source_form": "contact",
  "utm": {"campaign": "", "medium": "", "source": ""}
}
```

The body is **canonical JSON**: keys are sorted alphabetically and
there is no whitespace. This is what the HMAC signature is computed
against — any normalization (re-pretty-print) on the receiver side
will break verification.

### What is NEVER sent

- Health/judicial detail beyond consent flags + version (unless
  `CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY=True`).
- IP address, user-agent, session key.
- Internal staff notes, audit metadata.

---

## 2. Verifying the HMAC signature in n8n

n8n has a Code node that exposes the request as JSON + raw body. The
verification step is straightforward.

### Reference Python verifier

```python
import hashlib, hmac

def verify(body_bytes: bytes, *, secret: str, timestamp: str, signature_header: str) -> bool:
    msg = timestamp.encode("utf-8") + b"." + body_bytes
    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"), msg, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header or "")
```

### Reference JavaScript verifier (for n8n Code node)

```javascript
const crypto = require('crypto');

function verify({ rawBody, secret, timestamp, signatureHeader }) {
  const expected =
    'sha256=' +
    crypto
      .createHmac('sha256', secret)
      .update(timestamp + '.')
      .update(rawBody)
      .digest('hex');
  // constant-time compare
  const a = Buffer.from(expected, 'utf8');
  const b = Buffer.from(signatureHeader || '', 'utf8');
  return a.length === b.length && crypto.timingSafeEqual(a, b);
}
```

In an n8n Webhook trigger:

1. Set the trigger to **Raw Body** so the body bytes are not
   re-serialized.
2. In a Code node, read
   `$json.headers['x-indennizzati-signature']`,
   `$json.headers['x-indennizzati-timestamp']`,
   and the raw body.
3. Reject with HTTP 401 if `verify(...)` is false.
4. Otherwise process the lead and respond with 2xx.

### Replay protection

- The `X-Indennizzati-Timestamp` is unix epoch seconds. The receiver
  SHOULD reject signatures older than e.g. 5 minutes from the
  receiver clock. The platform is currently lenient by design (the
  outbox can sit in `pending` for a long time before cron drains
  it), but the receiver is free to reject stale stamps.
- The `X-Indennizzati-Idempotency-Key` is the dedup key. Receivers
  MUST accept the same key only once per lifetime — a retry after
  network loss carries the same key.

---

## 3. What the receiver MUST return

| HTTP status | Dispatcher reaction |
|---|---|
| 2xx | Mark `delivered`. Stop. |
| 408, 429 | Retry with linear backoff. |
| 5xx | Retry with linear backoff. |
| Other 4xx | Mark `failed` (non-retriable). The Studio operator
  reviews the row in admin. |

The dispatcher reads up to `CRM_WEBHOOK_MAX_ATTEMPTS` attempts;
after that, the row is marked `dead` and never retried. Linear
backoff = `CRM_WEBHOOK_BACKOFF_SECONDS × attempts`.

Recommended receiver behavior:

- 2xx as fast as possible after a successful enqueue (don't block
  on synchronous downstream work — the Studio is monitoring its
  own pipeline anyway).
- Return a small body (under 500 bytes); the dispatcher stores at
  most the first 500 bytes as `response_excerpt` for debugging.
- Use 4xx (e.g. `400 invalid signature`) for permanent rejection.
  Use 5xx for transient downstream failure.

---

## 4. Secret rotation

The HMAC secret lives in `CRM_WEBHOOK_SECRET` (env var on the
dispatcher side and on n8n side). Rotation steps:

1. Generate a new secret:

   ```
   python -c "import secrets;print(secrets.token_urlsafe(48))"
   ```

2. **Receiver side first** — make n8n accept BOTH old and new
   secrets temporarily.
3. Update the dispatcher env var. Restart the dispatcher / cron
   runner.
4. Confirm next deliveries are signed with the new secret.
5. Remove the old secret from the receiver.

Never commit the secret to git, never log it, never echo it in CI
output. The platform's system check `crm.E002` requires at least
32 chars in production.

---

## 5. Manual test in staging

```bash
# 1. With dispatcher enabled but no real receiver yet, the row stays
#    pending and `attempts` increments on every cron tick.

DJANGO_DEBUG=True \
CRM_WEBHOOK_ENABLED=True \
CRM_WEBHOOK_URL=https://requestbin.example/yourbin \
CRM_WEBHOOK_SECRET=$(python -c "import secrets;print(secrets.token_urlsafe(48))") \
python manage.py dispatch_crm_webhooks --dry-run
# → counts the pending rows, no POST

# 2. Send a real POST to a public requestbin to inspect the headers.
python manage.py dispatch_crm_webhooks --limit 1
```

In production, replace `requestbin.example` with the real n8n
webhook URL.

---

## 6. What is sensitive

- `contact.first_name`, `contact.last_name`, `contact.email`,
  `contact.phone_number`, `message` — these are PII. The receiver
  must store them in a system that complies with the platform's
  privacy policy (P0-LEG-1).
- `consent.special_categories_*` — the booleans + version are
  enough to **prove** the consent was given. Detail of what the
  consent covers (health / family / judicial) is **not** in the
  payload by default.
- The HMAC secret itself.

The dispatcher does NOT send IP, user-agent, source path, session
key. If a CRM use case requires those, extend `build_lead_payload`
in `apps/crm/webhooks.py` and add a corresponding settings flag
similar to `CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY`.

---

## 7. Failure modes seen by the Studio

In Django admin, `LeadWebhookDelivery` rows surface `status`,
`attempts/max_attempts`, `last_status_code`, `last_error`,
`response_excerpt`. A typical investigation flow:

- `pending` with `attempts > 0` → the receiver returned 5xx or
  network failed. `last_error` says which. The dispatcher will
  retry.
- `failed` → the receiver returned a 4xx (e.g. signature mismatch
  after a rotation gone wrong). Fix the receiver, then either
  delete the row to give up, or set `status=pending` and
  `next_attempt_at=now()` to retry by hand.
- `dead` → max_attempts reached. Same recovery as `failed`.

In all cases the Lead itself remains intact in `/admin/crm/lead/`
— the dispatcher is strictly an outbound consequence of the Lead,
never a precondition for it.
