"""
CRM webhook outbox dispatcher (F-p1-crm-1-webhook-dispatcher).

API:

- ``build_lead_payload(lead)`` -> dict
    Pure builder. Returns the payload the dispatcher will POST to the
    CRM. Privacy-aware: by default does NOT include the special-
    categories detail; toggled via
    ``CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY``.

- ``compute_idempotency_key(lead, event_type)`` -> str
    Stable hash, safe across retries. Receiver uses it to dedupe.

- ``canonical_json(payload)`` -> bytes
    Deterministic JSON encoding (sorted keys, no whitespace) so the
    HMAC signature is stable across runtimes.

- ``sign_payload(body_bytes, *, secret, timestamp)`` -> str
    Returns ``"sha256=<hex>"``. Signs ``timestamp + "." + body``.

- ``enqueue_lead_webhook(lead, *, event_type="lead.created")`` ->
  LeadWebhookDelivery | None
    Creates the outbox row. Returns None if the dispatcher is
    disabled. Idempotent: a second call with the same
    (lead, event_type) returns the existing row.

- ``dispatch_pending_webhooks(*, limit, now=None, dry_run=False, http_post=None)``
    Finds rows ready to ship and dispatches each via ``dispatch_one``.

- ``dispatch_one(delivery, *, now=None, http_post=None)``
    The single-row state machine. Pure-ish: HTTP I/O happens through
    the injected ``http_post`` callable, so tests never reach the
    network.

NEVER stores:
- HMAC secret;
- full URL (only the host is snapshotted onto the row);
- raw payload (regenerated on demand from the Lead).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta
from typing import Any, Callable
from urllib.parse import urlparse

from django.conf import settings
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)


SIGNATURE_HEADER = "X-Indennizzati-Signature"
EVENT_HEADER = "X-Indennizzati-Event"
PAYLOAD_VERSION_HEADER = "X-Indennizzati-Payload-Version"
IDEMPOTENCY_HEADER = "X-Indennizzati-Idempotency-Key"
TIMESTAMP_HEADER = "X-Indennizzati-Timestamp"


def _domain_of(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
    except Exception:
        return ""
    return host[:255]


def canonical_json(payload: dict) -> bytes:
    """
    Deterministic JSON encoding. Sort keys, drop whitespace, ensure
    ASCII so the HMAC signature is stable regardless of Python build.
    """
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def sign_payload(body: bytes, *, secret: str, timestamp: str) -> str:
    """
    HMAC-SHA256 over ``timestamp + "." + body``. Returns ``"sha256=<hex>"``.

    The receiver reconstructs the same string and compares with
    ``hmac.compare_digest`` to avoid timing leaks.
    """
    if not isinstance(secret, str) or not secret:
        raise ValueError("HMAC secret is required")
    if not isinstance(timestamp, str) or not timestamp:
        raise ValueError("timestamp is required")
    msg = timestamp.encode("utf-8") + b"." + body
    digest = hmac.new(secret.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def compute_idempotency_key(lead, event_type: str) -> str:
    """
    Stable across retries: sha256 of ``public_id:event_type``. Receiver
    can dedupe by this key.
    """
    public_id = str(getattr(lead, "public_id", "")) or "anon"
    seed = f"{public_id}:{event_type}".encode("utf-8")
    return hashlib.sha256(seed).hexdigest()


def _bool(name: str, default: bool) -> bool:
    return bool(getattr(settings, name, default))


def _str(name: str, default: str = "") -> str:
    return str(getattr(settings, name, default) or default)


def _int(name: str, default: int) -> int:
    return int(getattr(settings, name, default) or default)


def build_lead_payload(lead) -> dict[str, Any]:
    """Build the ``v1`` payload sent to the CRM. Privacy-aware."""
    payload_version = _str("CRM_WEBHOOK_PAYLOAD_VERSION", "v1")
    include_special = _bool("CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY", False)

    payload: dict[str, Any] = {
        "event_type": "lead.created",
        "payload_version": payload_version,
        "lead_public_id": str(lead.public_id),
        "created_at": lead.created_at.isoformat() if lead.created_at else None,
        "locale": lead.preferred_language or "",
        "country": (lead.country.code if lead.country_id else ""),
        "case_type": lead.case_type or "",
        "contact": {
            "first_name": lead.first_name or "",
            "last_name": lead.last_name or "",
            "email": lead.email or "",
            "phone_number": lead.phone_number or "",
        },
        "message": lead.message or "",
        "consent": {
            "privacy_given": bool(lead.privacy_consent_given),
            "privacy_version": lead.privacy_consent_version or "",
            "privacy_at": (
                lead.privacy_consent_at.isoformat()
                if lead.privacy_consent_at
                else None
            ),
            "special_categories_given": bool(lead.special_categories_consent_given),
            "special_categories_version": lead.special_categories_consent_version or "",
            "special_categories_at": (
                lead.special_categories_consent_at.isoformat()
                if lead.special_categories_consent_at
                else None
            ),
        },
        "mandate_status": getattr(lead, "mandate_status", "") or "",
        "source_form": "contact",
        "utm": {
            "source": lead.utm_source or "",
            "medium": lead.utm_medium or "",
            "campaign": lead.utm_campaign or "",
        },
    }

    if include_special:
        # Opt-in: surface a high-level *summary* (booleans + version)
        # but never raw health/judicial detail. The detail lives only
        # in the encrypted-at-rest Lead row + the audit ledger.
        payload["consent"]["special_categories_summary"] = {
            "given": bool(lead.special_categories_consent_given),
            "version": lead.special_categories_consent_version or "",
            "scope": "health, family events, judicial proceedings (GDPR art. 9.2.a)",
        }

    return payload


@transaction.atomic
def enqueue_lead_webhook(lead, *, event_type: str = "lead.created"):
    """
    Create the outbox row. Returns None if the dispatcher is disabled.

    Idempotent: a second call with the same (lead, event_type) returns
    the existing row.
    """
    if not _bool("CRM_WEBHOOK_ENABLED", False):
        return None

    from .models import LeadWebhookDelivery

    key = compute_idempotency_key(lead, event_type)
    existing = LeadWebhookDelivery.objects.filter(idempotency_key=key).first()
    if existing is not None:
        return existing

    delivery = LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type=event_type,
        payload_version=_str("CRM_WEBHOOK_PAYLOAD_VERSION", "v1"),
        idempotency_key=key,
        target_url_domain=_domain_of(_str("CRM_WEBHOOK_URL", "")),
        status=LeadWebhookDelivery.Status.PENDING,
        max_attempts=_int("CRM_WEBHOOK_MAX_ATTEMPTS", 5),
        next_attempt_at=timezone.now(),
    )
    logger.info(
        "crm.webhook.enqueued lead_public_id=%s event=%s key=%s",
        lead.public_id,
        event_type,
        key[:12],
    )
    return delivery


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


class _HttpResult:
    """Tiny shape returned by the http_post callable. Lets tests
    inject any object with `.status_code`, `.text`, `.elapsed`.
    """

    __slots__ = ("status_code", "text")

    def __init__(self, status_code: int, text: str = "") -> None:
        self.status_code = int(status_code)
        self.text = text or ""


def _default_http_post(url: str, *, body: bytes, headers: dict, timeout: int):
    """Real HTTP POST via `requests` — used when no http_post is injected."""
    import requests  # local import keeps the module importable in test contexts

    resp = requests.post(url, data=body, headers=headers, timeout=timeout)
    return _HttpResult(resp.status_code, resp.text or "")


HttpPostCallable = Callable[..., _HttpResult]


def _backoff_for(attempts: int) -> int:
    """Linear backoff = base * attempts (clamped). Simpler than
    exponential for an audit-trail pattern: failures are visible
    quickly, never over an hour for a healthy retry cycle.
    """
    base = _int("CRM_WEBHOOK_BACKOFF_SECONDS", 300)
    return base * max(1, attempts)


def _is_retriable(status: int) -> bool:
    """5xx + 408 + 429 retry; the rest of 4xx is a permanent failure."""
    if status >= 500:
        return True
    if status in (408, 429):
        return True
    return False


def _record_attempt(
    delivery,
    *,
    now: datetime,
    status_code: int | None,
    error: str = "",
    response_excerpt: str = "",
):
    delivery.attempts = (delivery.attempts or 0) + 1
    delivery.last_attempt_at = now
    delivery.last_status_code = status_code
    delivery.last_error = error[:255]
    delivery.response_excerpt = response_excerpt[:500]


def dispatch_one(
    delivery,
    *,
    now: datetime | None = None,
    http_post: HttpPostCallable | None = None,
) -> str:
    """
    Run a single delivery through the state machine. Returns the new
    status string after the attempt.
    """
    from .models import LeadWebhookDelivery

    now = now or timezone.now()
    http_post = http_post or _default_http_post

    if delivery.status not in (
        LeadWebhookDelivery.Status.PENDING,
        LeadWebhookDelivery.Status.SENDING,
    ):
        return delivery.status

    url = _str("CRM_WEBHOOK_URL", "")
    secret = _str("CRM_WEBHOOK_SECRET", "")
    timeout = _int("CRM_WEBHOOK_TIMEOUT_SECONDS", 10)

    if not url or not secret:
        # The dispatcher refuses to send a delivery the system check
        # would have flagged. Mark dead so the row stops re-trying.
        _record_attempt(
            delivery,
            now=now,
            status_code=None,
            error="config: missing URL or secret",
        )
        delivery.status = LeadWebhookDelivery.Status.DEAD
        delivery.save(
            update_fields=[
                "attempts",
                "last_attempt_at",
                "last_status_code",
                "last_error",
                "response_excerpt",
                "status",
                "updated_at",
            ]
        )
        logger.warning(
            "crm.webhook.dispatch.dead reason=missing_config delivery_id=%s",
            delivery.pk,
        )
        return delivery.status

    payload = build_lead_payload(delivery.lead)
    body = canonical_json(payload)
    timestamp = str(int(now.timestamp()))
    signature = sign_payload(body, secret=secret, timestamp=timestamp)

    headers = {
        "Content-Type": "application/json",
        EVENT_HEADER: delivery.event_type,
        PAYLOAD_VERSION_HEADER: delivery.payload_version,
        IDEMPOTENCY_HEADER: delivery.idempotency_key,
        TIMESTAMP_HEADER: timestamp,
        SIGNATURE_HEADER: signature,
    }

    delivery.status = LeadWebhookDelivery.Status.SENDING
    delivery.save(update_fields=["status", "updated_at"])

    try:
        result = http_post(url, body=body, headers=headers, timeout=timeout)
        status_code = int(result.status_code)
        excerpt = (result.text or "")[:500]
    except Exception as exc:
        status_code = None
        excerpt = ""
        error_msg = f"{exc.__class__.__name__}: {exc}"
        _record_attempt(delivery, now=now, status_code=None, error=error_msg)
        # Network/timeout: always retriable up to max_attempts.
        if delivery.attempts >= delivery.max_attempts:
            delivery.status = LeadWebhookDelivery.Status.DEAD
            delivery.next_attempt_at = None
        else:
            delivery.status = LeadWebhookDelivery.Status.PENDING
            delivery.next_attempt_at = now + timedelta(
                seconds=_backoff_for(delivery.attempts)
            )
        delivery.save(
            update_fields=[
                "attempts",
                "last_attempt_at",
                "last_status_code",
                "last_error",
                "response_excerpt",
                "status",
                "next_attempt_at",
                "updated_at",
            ]
        )
        logger.warning(
            "crm.webhook.dispatch.network_error delivery_id=%s status=%s error=%s",
            delivery.pk,
            delivery.status,
            error_msg,
        )
        return delivery.status

    _record_attempt(
        delivery,
        now=now,
        status_code=status_code,
        response_excerpt=excerpt,
    )

    if 200 <= status_code < 300:
        delivery.status = LeadWebhookDelivery.Status.DELIVERED
        delivery.delivered_at = now
        delivery.next_attempt_at = None
    elif _is_retriable(status_code):
        if delivery.attempts >= delivery.max_attempts:
            delivery.status = LeadWebhookDelivery.Status.DEAD
            delivery.next_attempt_at = None
        else:
            delivery.status = LeadWebhookDelivery.Status.PENDING
            delivery.next_attempt_at = now + timedelta(
                seconds=_backoff_for(delivery.attempts)
            )
    else:
        # Permanent 4xx: stop retrying.
        delivery.status = LeadWebhookDelivery.Status.FAILED
        delivery.next_attempt_at = None

    delivery.save(
        update_fields=[
            "attempts",
            "last_attempt_at",
            "last_status_code",
            "last_error",
            "response_excerpt",
            "status",
            "delivered_at",
            "next_attempt_at",
            "updated_at",
        ]
    )
    logger.info(
        "crm.webhook.dispatch delivery_id=%s status=%s http=%s attempts=%s",
        delivery.pk,
        delivery.status,
        status_code,
        delivery.attempts,
    )
    return delivery.status


def dispatch_pending_webhooks(
    *,
    limit: int = 50,
    now: datetime | None = None,
    dry_run: bool = False,
    http_post: HttpPostCallable | None = None,
) -> dict[str, Any]:
    """
    Find rows whose `status=pending` and `next_attempt_at <= now`,
    dispatch up to `limit`, and return a counts dict.

    Dry-run: count candidates only, do not change DB.
    """
    from .models import LeadWebhookDelivery

    now = now or timezone.now()
    qs = (
        LeadWebhookDelivery.objects.filter(
            status=LeadWebhookDelivery.Status.PENDING,
            next_attempt_at__lte=now,
        )
        .order_by("next_attempt_at", "pk")
    )
    candidates = list(qs[:limit])
    counts: dict[str, int] = {
        "candidates": len(candidates),
        "delivered": 0,
        "failed": 0,
        "dead": 0,
        "retried": 0,
    }

    if dry_run:
        return {
            "now": now,
            "dry_run": True,
            **counts,
        }

    for delivery in candidates:
        new_status = dispatch_one(delivery, now=now, http_post=http_post)
        if new_status == LeadWebhookDelivery.Status.DELIVERED:
            counts["delivered"] += 1
        elif new_status == LeadWebhookDelivery.Status.FAILED:
            counts["failed"] += 1
        elif new_status == LeadWebhookDelivery.Status.DEAD:
            counts["dead"] += 1
        else:
            counts["retried"] += 1

    return {
        "now": now,
        "dry_run": False,
        **counts,
    }


def constant_time_signature_check(
    *, body: bytes, secret: str, timestamp: str, signature_header: str
) -> bool:
    """
    Helper for verification (used by tests + receivers): rebuild the
    signature and compare with `hmac.compare_digest`. Returns False
    on any structural error rather than raising.
    """
    try:
        expected = sign_payload(body, secret=secret, timestamp=timestamp)
    except ValueError:
        return False
    return hmac.compare_digest(expected, signature_header or "")


def fresh_idempotency_for_test() -> str:
    """Test convenience: a random idempotency key for hand-crafted
    deliveries that don't go through `enqueue_lead_webhook`.
    """
    return secrets.token_hex(16)
