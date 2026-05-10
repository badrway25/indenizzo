"""
Tests F-p1-crm-1-webhook-dispatcher.

Coprono l'outbox dispatcher Lead -> CRM/n8n con HMAC, idempotency,
retry e contratto del payload. Tutto l'HTTP e' iniettato via
`http_post` callable: nessun fetch reale.

1.  CRM_WEBHOOK_ENABLED=False -> Lead salvato, nessuna delivery;
2.  CRM_WEBHOOK_ENABLED=True  -> Lead salvato, una delivery `pending`;
3.  enqueue idempotente sulla stessa coppia (lead, event_type);
4.  payload contiene consensi + versioni;
5.  payload NON include special-categories summary se OFF;
6.  payload INCLUDE summary se INCLUDE_SPECIAL_CATEGORY_SUMMARY=True;
7.  signature HMAC verificabile bit-per-bit dal receiver;
8.  signature differente con secret diverso (sanity);
9.  system check `crm.E002` fail in prod con secret vuoto;
10. system check `crm.E002` fail in prod con secret < 32 char;
11. system check `crm.E002` fail in prod con URL non https;
12. system check `crm.E003` fail in prod con timeout <= 0;
13. dispatch 200 -> status `delivered`;
14. dispatch 500 -> retry, attempts++ , next_attempt_at avanzato;
15. dispatch network exception -> retry;
16. dispatch 400 -> status `failed` (non-retriable);
17. attempts == max_attempts e 5xx -> dead;
18. command --dry-run non muta DB;
19. command bulk dispatcha pending pronti;
20. command --delivery-id senza --force rifiuta se non ancora dovuto;
21. command --delivery-id --force forza il dispatch.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone as dt_timezone
from io import StringIO
from unittest.mock import patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from apps.crm.checks import check_crm_webhook_configuration_in_production
from apps.crm.models import Lead, LeadWebhookDelivery
from apps.crm.webhooks import (
    SIGNATURE_HEADER,
    build_lead_payload,
    canonical_json,
    compute_idempotency_key,
    constant_time_signature_check,
    dispatch_one,
    dispatch_pending_webhooks,
    enqueue_lead_webhook,
    sign_payload,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lead(**overrides) -> Lead:
    base = {
        "first_name": "Mario",
        "last_name": "Rossi",
        "email": "mario@example.test",
        "phone_number": "+39000",
        "message": "Test request body",
        "preferred_language": "it",
        "privacy_consent_given": True,
        "privacy_consent_at": timezone.now(),
        "privacy_consent_version": "2026-01-final",
        "special_categories_consent_given": True,
        "special_categories_consent_at": timezone.now(),
        "special_categories_consent_version": "2026-01-final",
    }
    base.update(overrides)
    return Lead.objects.create(**base)


class FakeResponse:
    def __init__(self, status_code: int, text: str = ""):
        self.status_code = status_code
        self.text = text


def http_post_factory(status_code: int, text: str = ""):
    seen: dict = {"calls": 0, "last_url": None, "last_headers": None, "last_body": None}

    def _post(url, *, body, headers, timeout):
        seen["calls"] += 1
        seen["last_url"] = url
        seen["last_headers"] = headers
        seen["last_body"] = body
        seen["last_timeout"] = timeout
        return FakeResponse(status_code, text)

    _post.seen = seen  # type: ignore[attr-defined]
    return _post


def http_post_raises(exc: Exception):
    seen: dict = {"calls": 0}

    def _post(url, *, body, headers, timeout):
        seen["calls"] += 1
        raise exc

    _post.seen = seen  # type: ignore[attr-defined]
    return _post


_ENABLED = dict(
    CRM_WEBHOOK_ENABLED=True,
    CRM_WEBHOOK_URL="https://crm.example.test/hook",
    CRM_WEBHOOK_SECRET="x" * 48,
    CRM_WEBHOOK_TIMEOUT_SECONDS=10,
    CRM_WEBHOOK_MAX_ATTEMPTS=5,
    CRM_WEBHOOK_BACKOFF_SECONDS=300,
    CRM_WEBHOOK_PAYLOAD_VERSION="v1",
)


# ---------------------------------------------------------------------------
# 1-3: enqueue gating + idempotency
# ---------------------------------------------------------------------------


@override_settings(CRM_WEBHOOK_ENABLED=False)
@pytest.mark.django_db
def test_disabled_dispatcher_never_creates_delivery():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    assert delivery is None
    assert LeadWebhookDelivery.objects.count() == 0


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_enabled_dispatcher_creates_pending_delivery():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    assert delivery is not None
    assert delivery.status == LeadWebhookDelivery.Status.PENDING
    assert delivery.payload_version == "v1"
    assert delivery.target_url_domain == "crm.example.test"
    assert delivery.idempotency_key
    # Privacy: full URL must NOT leak into the row.
    assert "https://" not in delivery.target_url_domain
    assert "/hook" not in delivery.target_url_domain


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_enqueue_is_idempotent_per_lead_and_event():
    lead = _make_lead()
    a = enqueue_lead_webhook(lead, event_type="lead.created")
    b = enqueue_lead_webhook(lead, event_type="lead.created")
    assert a.pk == b.pk
    assert LeadWebhookDelivery.objects.filter(lead=lead).count() == 1


# ---------------------------------------------------------------------------
# 4-6: payload contract
# ---------------------------------------------------------------------------


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_payload_contains_consent_fields_and_versions():
    lead = _make_lead()
    payload = build_lead_payload(lead)
    assert payload["payload_version"] == "v1"
    assert payload["lead_public_id"] == str(lead.public_id)
    assert payload["consent"]["privacy_given"] is True
    assert payload["consent"]["privacy_version"] == "2026-01-final"
    assert payload["consent"]["special_categories_given"] is True
    assert payload["consent"]["special_categories_version"] == "2026-01-final"
    assert payload["mandate_status"] == "mandate_required"


@override_settings(**{**_ENABLED, "CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY": False})
@pytest.mark.django_db
def test_payload_excludes_special_categories_summary_by_default():
    lead = _make_lead()
    payload = build_lead_payload(lead)
    assert "special_categories_summary" not in payload["consent"]


@override_settings(**{**_ENABLED, "CRM_WEBHOOK_INCLUDE_SPECIAL_CATEGORY_SUMMARY": True})
@pytest.mark.django_db
def test_payload_includes_special_categories_summary_when_opted_in():
    lead = _make_lead()
    payload = build_lead_payload(lead)
    assert "special_categories_summary" in payload["consent"]
    summary = payload["consent"]["special_categories_summary"]
    assert summary["given"] is True
    assert summary["version"] == "2026-01-final"
    # Must be a *summary*, not raw health/judicial detail.
    assert "scope" in summary


# ---------------------------------------------------------------------------
# 7-8: HMAC signature
# ---------------------------------------------------------------------------


def test_signature_is_round_trip_verifiable():
    body = b'{"event":"lead.created"}'
    secret = "x" * 48
    timestamp = "1715342400"
    sig = sign_payload(body, secret=secret, timestamp=timestamp)
    assert sig.startswith("sha256=")
    assert constant_time_signature_check(
        body=body, secret=secret, timestamp=timestamp, signature_header=sig,
    )


def test_signature_changes_with_different_secret():
    body = b'{"x":1}'
    a = sign_payload(body, secret="aaaa" * 8, timestamp="1")
    b = sign_payload(body, secret="bbbb" * 8, timestamp="1")
    assert a != b


def test_canonical_json_is_deterministic():
    a = canonical_json({"b": 2, "a": 1})
    b = canonical_json({"a": 1, "b": 2})
    assert a == b == b'{"a":1,"b":2}'


def test_idempotency_key_is_stable():
    class FakeLead:
        public_id = "abc-123"

    k1 = compute_idempotency_key(FakeLead(), "lead.created")
    k2 = compute_idempotency_key(FakeLead(), "lead.created")
    k3 = compute_idempotency_key(FakeLead(), "lead.updated")
    assert k1 == k2
    assert k1 != k3


# ---------------------------------------------------------------------------
# 9-12: system check matrix
# ---------------------------------------------------------------------------


@override_settings(
    DEBUG=False, CRM_WEBHOOK_ENABLED=True,
    CRM_WEBHOOK_URL="https://crm.example.test/hook",
    CRM_WEBHOOK_SECRET="",
    CRM_WEBHOOK_TIMEOUT_SECONDS=10, CRM_WEBHOOK_MAX_ATTEMPTS=5,
)
def test_check_E002_empty_secret():
    issues = check_crm_webhook_configuration_in_production(app_configs=None)
    assert any(i.id == "crm.E002" and "SECRET" in i.msg for i in issues)


@override_settings(
    DEBUG=False, CRM_WEBHOOK_ENABLED=True,
    CRM_WEBHOOK_URL="https://crm.example.test/hook",
    CRM_WEBHOOK_SECRET="too-short",
    CRM_WEBHOOK_TIMEOUT_SECONDS=10, CRM_WEBHOOK_MAX_ATTEMPTS=5,
)
def test_check_E002_short_secret():
    issues = check_crm_webhook_configuration_in_production(app_configs=None)
    assert any(i.id == "crm.E002" and "minimum is 32" in i.msg for i in issues)


@override_settings(
    DEBUG=False, CRM_WEBHOOK_ENABLED=True,
    CRM_WEBHOOK_URL="http://crm.example.test/hook",
    CRM_WEBHOOK_SECRET="x" * 48,
    CRM_WEBHOOK_TIMEOUT_SECONDS=10, CRM_WEBHOOK_MAX_ATTEMPTS=5,
)
def test_check_E002_non_https():
    issues = check_crm_webhook_configuration_in_production(app_configs=None)
    assert any(i.id == "crm.E002" and "HTTPS" in i.msg for i in issues)


@override_settings(
    DEBUG=False, CRM_WEBHOOK_ENABLED=True,
    CRM_WEBHOOK_URL="https://crm.example.test/hook",
    CRM_WEBHOOK_SECRET="x" * 48,
    CRM_WEBHOOK_TIMEOUT_SECONDS=0, CRM_WEBHOOK_MAX_ATTEMPTS=5,
)
def test_check_E003_timeout_zero():
    issues = check_crm_webhook_configuration_in_production(app_configs=None)
    assert any(i.id == "crm.E003" for i in issues)


@override_settings(
    DEBUG=False, CRM_WEBHOOK_ENABLED=True,
    CRM_WEBHOOK_URL="https://crm.example.test/hook",
    CRM_WEBHOOK_SECRET="x" * 48,
    CRM_WEBHOOK_TIMEOUT_SECONDS=10, CRM_WEBHOOK_MAX_ATTEMPTS=0,
)
def test_check_E003_attempts_zero():
    issues = check_crm_webhook_configuration_in_production(app_configs=None)
    assert any(i.id == "crm.E003" for i in issues)


@override_settings(DEBUG=False, CRM_WEBHOOK_ENABLED=False)
def test_check_silent_when_dispatcher_disabled():
    assert check_crm_webhook_configuration_in_production(app_configs=None) == []


@override_settings(DEBUG=False, **_ENABLED)
def test_check_passes_with_full_config():
    assert check_crm_webhook_configuration_in_production(app_configs=None) == []


# ---------------------------------------------------------------------------
# 13-17: dispatch state machine
# ---------------------------------------------------------------------------


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_dispatch_2xx_marks_delivered():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    poster = http_post_factory(202, text="ok")

    new_status = dispatch_one(delivery, http_post=poster)
    assert new_status == LeadWebhookDelivery.Status.DELIVERED
    delivery.refresh_from_db()
    assert delivery.delivered_at is not None
    assert delivery.attempts == 1
    assert delivery.last_status_code == 202

    # The signature header was emitted.
    headers = poster.seen["last_headers"]
    assert SIGNATURE_HEADER in headers
    assert headers[SIGNATURE_HEADER].startswith("sha256=")
    # The body is exactly the canonical JSON of the payload.
    decoded = json.loads(poster.seen["last_body"].decode("utf-8"))
    assert decoded["lead_public_id"] == str(lead.public_id)


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_dispatch_500_retries_and_increments_attempts():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    fixed_now = timezone.now()
    poster = http_post_factory(503)

    new_status = dispatch_one(delivery, now=fixed_now, http_post=poster)
    assert new_status == LeadWebhookDelivery.Status.PENDING
    delivery.refresh_from_db()
    assert delivery.attempts == 1
    assert delivery.next_attempt_at is not None
    assert delivery.next_attempt_at > fixed_now
    # Linear backoff: base 300s × attempts (1) = 300s.
    assert (delivery.next_attempt_at - fixed_now) >= timedelta(seconds=299)


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_dispatch_network_exception_retries():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    poster = http_post_raises(TimeoutError("timeout"))

    new_status = dispatch_one(delivery, http_post=poster)
    assert new_status == LeadWebhookDelivery.Status.PENDING
    delivery.refresh_from_db()
    assert delivery.attempts == 1
    assert "TimeoutError" in delivery.last_error


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_dispatch_400_marks_failed_non_retriable():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    poster = http_post_factory(400, text="bad request")

    new_status = dispatch_one(delivery, http_post=poster)
    assert new_status == LeadWebhookDelivery.Status.FAILED
    delivery.refresh_from_db()
    assert delivery.next_attempt_at is None


@override_settings(**{**_ENABLED, "CRM_WEBHOOK_MAX_ATTEMPTS": 2})
@pytest.mark.django_db
def test_dispatch_dead_after_max_attempts():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    delivery.max_attempts = 2  # mirror the override on the row created earlier
    delivery.save(update_fields=["max_attempts"])
    poster = http_post_factory(503)

    # 1st attempt -> retry pending, attempts=1
    s1 = dispatch_one(delivery, http_post=poster)
    assert s1 == LeadWebhookDelivery.Status.PENDING
    delivery.refresh_from_db()
    assert delivery.attempts == 1

    # 2nd attempt -> dead because attempts will become 2 == max_attempts.
    s2 = dispatch_one(delivery, http_post=poster)
    assert s2 == LeadWebhookDelivery.Status.DEAD
    delivery.refresh_from_db()
    assert delivery.attempts == 2
    assert delivery.next_attempt_at is None


# ---------------------------------------------------------------------------
# 18-21: management command
# ---------------------------------------------------------------------------


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_command_dry_run_does_not_mutate():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    out = StringIO()
    call_command("dispatch_crm_webhooks", "--dry-run", stdout=out)
    delivery.refresh_from_db()
    assert delivery.attempts == 0
    assert delivery.status == LeadWebhookDelivery.Status.PENDING
    assert "DRY-RUN" in out.getvalue()
    assert "candidates: 1" in out.getvalue()


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_command_bulk_dispatches_pending():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    out = StringIO()
    poster = http_post_factory(200, text="ok")
    with patch("apps.crm.webhooks._default_http_post", poster):
        call_command("dispatch_crm_webhooks", "--limit", "10", stdout=out)
    delivery.refresh_from_db()
    assert delivery.status == LeadWebhookDelivery.Status.DELIVERED
    assert "delivered:  1" in out.getvalue()


@override_settings(CRM_WEBHOOK_ENABLED=False)
@pytest.mark.django_db
def test_command_refuses_when_disabled_unless_dry_run():
    with pytest.raises(CommandError, match="CRM_WEBHOOK_ENABLED=False"):
        call_command("dispatch_crm_webhooks", stdout=StringIO())


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_command_delivery_id_respects_due_date():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    delivery.next_attempt_at = timezone.now() + timedelta(hours=1)
    delivery.save(update_fields=["next_attempt_at"])
    out = StringIO()
    with pytest.raises(CommandError, match="not yet due"):
        call_command(
            "dispatch_crm_webhooks", "--delivery-id", str(delivery.pk),
            stdout=out,
        )


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_command_delivery_id_force_overrides_due_date():
    lead = _make_lead()
    delivery = enqueue_lead_webhook(lead)
    delivery.next_attempt_at = timezone.now() + timedelta(hours=1)
    delivery.save(update_fields=["next_attempt_at"])
    out = StringIO()
    poster = http_post_factory(200)
    with patch("apps.crm.webhooks._default_http_post", poster):
        call_command(
            "dispatch_crm_webhooks", "--delivery-id", str(delivery.pk),
            "--force", stdout=out,
        )
    delivery.refresh_from_db()
    assert delivery.status == LeadWebhookDelivery.Status.DELIVERED


# ---------------------------------------------------------------------------
# Integration: contact form path
# ---------------------------------------------------------------------------


@override_settings(**_ENABLED)
@pytest.mark.django_db
def test_create_lead_from_form_enqueues_when_enabled():
    """The contact form path enqueues a delivery if the dispatcher is on."""
    from apps.crm.services import create_lead_from_form

    lead = create_lead_from_form(
        form_kwargs={
            "first_name": "Maria",
            "last_name": "Rossi",
            "email": "maria@example.test",
            "phone_number": "",
            "preferred_language": "it",
            "country": None,
            "case_type": "",
            "message": "Test request",
        },
    )
    assert LeadWebhookDelivery.objects.filter(lead=lead).count() == 1
    delivery = LeadWebhookDelivery.objects.get(lead=lead)
    assert delivery.status == LeadWebhookDelivery.Status.PENDING
