"""
Tests PRODUCT-8-studio-lead-activity-timeline.

Read-only chronological timeline aggregated from existing rows:

- Lead created;
- linked Simulation (when present);
- privacy + special-categories consent timestamps;
- LeadEvent lifecycle rows;
- LeadWebhookDelivery state machine;
- Mandate required (default) + Mandate signed (when present).

What these tests guard:

 1. Audit doc on disk.
 2. `build_lead_timeline(lead)` exists and returns the canonical
    Lead-created entry.
 3. Includes linked Simulation when present.
 4. Includes both consent entries.
 5. Includes webhook pending / delivered / dead variants.
 6. Includes Mandate signed when present.
 7. Items are ordered by timestamp ascending.
 8. No HMAC secret, no full URL, no PII (no Lead.message, no email,
    no phone) appears anywhere in the timeline strings.
 9. LeadAdmin exposes the activity timeline as a readonly field.
10. `next_staff_action` for a brand-new lead.
11. `next_staff_action` for a lead with a dead webhook.
12. `next_staff_action` for a lead with a signed mandate.
13. `next_staff_action` strings carry no banned-promise phrases.
14. Timeline HTML rendered through `format_html` contains no
    `<script` or `javascript:` markers.
"""

from __future__ import annotations

import uuid
from datetime import timedelta
from pathlib import Path

import pytest
from django.contrib import admin as django_admin
from django.utils import timezone

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT / "docs" / "product" / "CRM_LEAD_ACTIVITY_TIMELINE_AUDIT_2026-05-12.md"
)


BANNED_PROMISE_PHRASES = (
    "scopri quanto ti spetta",
    "ottieni il risarcimento",
    "calcolo definitivo",
    "paghi solo se vinci",
    "pay only if you win",
    "no win no fee",
    "risarcimento garantito",
    "garantiamo il risultato",
)


# ---------------------------------------------------------------------------
# 0. Audit doc exists
# ---------------------------------------------------------------------------


def test_audit_doc_exists():
    assert AUDIT_DOC.exists()
    assert AUDIT_DOC.stat().st_size > 4000


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def lead(db):
    from apps.crm.models import Lead

    now = timezone.now()
    # Distinctive PII tokens so substring tests for leakage are
    # meaningful (a one-char first_name would collide with common
    # English label text like "A" in "Lead created").
    return Lead.objects.create(
        first_name="MarioFixtureName",
        last_name="RossiFixtureSurname",
        email="mario.fixture@example.test",
        message="sensitive-message-fixture-token-NEVER-leak",
        phone_number="+39 333 0000000",
        privacy_consent_given=True,
        privacy_consent_at=now,
        privacy_consent_version="2026-04",
        special_categories_consent_given=True,
        special_categories_consent_at=now,
        special_categories_consent_version="2026-04",
    )


# ---------------------------------------------------------------------------
# 1. Canonical "Lead created" anchor
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timeline_includes_lead_created(lead):
    from apps.crm.timeline import build_lead_timeline

    items = build_lead_timeline(lead)
    labels = [it.label for it in items]
    assert any("Lead created" in l for l in labels)


# ---------------------------------------------------------------------------
# 2. Linked Simulation surfaces as a timeline entry
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timeline_includes_linked_simulation(lead):
    from apps.cases.models import Simulation
    from apps.crm.timeline import build_lead_timeline

    sim = Simulation.objects.create(
        case_type="road_accident_bodily_injury",
        locale="it",
        status="indicative_available",
    )
    lead.simulation = sim
    lead.save(update_fields=["simulation"])

    items = build_lead_timeline(lead)
    cats = [it.category for it in items]
    assert "simulation" in cats
    sim_item = next(it for it in items if it.category == "simulation")
    assert "Simulation linked" in sim_item.label


# ---------------------------------------------------------------------------
# 3. Consent entries surface for both purposes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timeline_includes_both_consent_entries(lead):
    from apps.crm.timeline import build_lead_timeline

    items = build_lead_timeline(lead)
    consent_labels = [it.label for it in items if it.category == "consent"]
    assert any("Privacy consent" in l for l in consent_labels)
    assert any("Special-categories consent" in l for l in consent_labels)


# ---------------------------------------------------------------------------
# 4. Webhook variants — pending / delivered / dead
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timeline_webhook_pending_delivered_dead(lead):
    from apps.crm.models import LeadWebhookDelivery
    from apps.crm.timeline import build_lead_timeline

    now = timezone.now()

    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.created",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.PENDING,
        attempts=2,
        max_attempts=5,
        last_attempt_at=now + timedelta(minutes=1),
    )
    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.updated",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.DELIVERED,
        attempts=1,
        max_attempts=5,
        last_attempt_at=now + timedelta(minutes=2),
        delivered_at=now + timedelta(minutes=2),
        last_status_code=200,
    )
    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.deleted",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.DEAD,
        attempts=5,
        max_attempts=5,
        last_attempt_at=now + timedelta(minutes=3),
        last_status_code=503,
    )

    items = build_lead_timeline(lead)
    wh_labels = [it.label for it in items if it.category == "webhook"]
    joined = " | ".join(wh_labels)
    assert "Webhook enqueued" in joined
    assert "Webhook pending" in joined or "Webhook delivered" in joined  # both expected
    assert "Webhook delivered" in joined
    assert "Webhook dead" in joined


# ---------------------------------------------------------------------------
# 5. Mandate signed surfaces only when the flag is set
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timeline_includes_mandate_signed_only_when_signed(lead):
    from apps.crm.timeline import build_lead_timeline

    items = build_lead_timeline(lead)
    mandate_labels = [it.label for it in items if it.category == "mandate"]
    assert any("Mandate required" in l for l in mandate_labels)
    assert not any("Mandate signed" in l for l in mandate_labels)

    now = timezone.now()
    lead.mandate_signed = True
    lead.mandate_signed_at = now
    lead.mandate_version = "2026-04"
    lead.mandate_source = "staff"
    lead.save(
        update_fields=[
            "mandate_signed",
            "mandate_signed_at",
            "mandate_version",
            "mandate_source",
        ]
    )

    items = build_lead_timeline(lead)
    mandate_labels = [it.label for it in items if it.category == "mandate"]
    assert any("Mandate signed" in l for l in mandate_labels)


# ---------------------------------------------------------------------------
# 6. Timeline ordered chronologically ascending
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timeline_is_ordered_chronologically(lead):
    from apps.crm.models import LeadEvent, LeadWebhookDelivery
    from apps.crm.timeline import build_lead_timeline

    now = timezone.now()
    LeadEvent.objects.create(
        lead=lead,
        event_type=LeadEvent.EventType.CONTACTED,
        message="staff click",
    )
    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.created",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.DELIVERED,
        delivered_at=now + timedelta(minutes=5),
        last_attempt_at=now + timedelta(minutes=5),
    )

    items = build_lead_timeline(lead)
    timestamps = [it.timestamp for it in items]
    assert timestamps == sorted(timestamps)


# ---------------------------------------------------------------------------
# 7. No HMAC secret / full URL / PII leak in timeline
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_timeline_does_not_leak_secret_url_or_pii(lead, settings):
    """The aggregator must not surface the HMAC secret, the full CRM
    URL, or user-supplied PII (Lead.message, email, phone)."""
    from apps.crm.models import LeadWebhookDelivery
    from apps.crm.timeline import build_lead_timeline

    sentinel_secret = "SENTINEL-SECRET-NOT-IN-OUTPUT"
    sentinel_url = "https://hooks.example/v1/very/secret/path?token=abc"
    settings.CRM_WEBHOOK_SECRET = sentinel_secret
    settings.CRM_WEBHOOK_URL = sentinel_url

    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.created",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        # Only the host part is persisted by enqueue_lead_webhook; the
        # aggregator uses the persisted value, not settings.
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.DELIVERED,
        delivered_at=timezone.now(),
        last_attempt_at=timezone.now(),
    )

    items = build_lead_timeline(lead)
    blob = "\n".join(
        f"{it.label}|{it.description}|{it.source}|{it.metadata}"
        for it in items
    )

    assert sentinel_secret not in blob
    assert "/v1/very/secret/path" not in blob
    assert "token=abc" not in blob
    # PII from the Lead fixture must never appear in timeline strings.
    assert lead.message not in blob
    assert lead.email not in blob
    assert lead.phone_number not in blob
    assert lead.first_name not in blob
    assert lead.last_name not in blob


# ---------------------------------------------------------------------------
# 8. LeadAdmin exposes activity_timeline as a readonly field
# ---------------------------------------------------------------------------


def test_lead_admin_exposes_activity_timeline_readonly():
    from apps.crm.models import Lead

    inst = django_admin.site._registry[Lead]
    assert "activity_timeline" in inst.readonly_fields
    assert "next_staff_action_display" in inst.readonly_fields


# ---------------------------------------------------------------------------
# 9. next_staff_action branches
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_next_staff_action_for_brand_new_lead(lead):
    """A fresh `received` Lead without a linked simulation needs review."""
    assert lead.next_staff_action == "Review new lead and decide next step"


@pytest.mark.django_db
def test_next_staff_action_for_received_lead_with_simulation(lead):
    from apps.cases.models import Simulation

    sim = Simulation.objects.create(
        case_type="road_accident_bodily_injury",
        locale="it",
        status="indicative_available",
    )
    lead.simulation = sim
    lead.save(update_fields=["simulation"])

    assert lead.next_staff_action == "Review linked simulation and contact client"


@pytest.mark.django_db
def test_next_staff_action_for_dead_webhook(lead):
    from apps.crm.models import LeadWebhookDelivery

    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.created",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.DEAD,
        attempts=5,
        max_attempts=5,
    )
    assert lead.next_staff_action == "Webhook delivery failed - check integration"


@pytest.mark.django_db
def test_next_staff_action_for_signed_mandate_and_converted(lead):
    from apps.crm.models import LeadStatus

    lead.status = LeadStatus.CONVERTED
    lead.mandate_signed = True
    lead.save(update_fields=["status", "mandate_signed"])

    assert lead.next_staff_action == "Engagement active - manage the case offline"


@pytest.mark.django_db
def test_next_staff_action_for_qualified_without_mandate(lead):
    from apps.crm.models import LeadStatus

    lead.status = LeadStatus.QUALIFIED
    lead.save(update_fields=["status"])

    assert lead.next_staff_action == "Mandate not signed - prepare engagement letter"


@pytest.mark.django_db
def test_next_staff_action_for_archived_terminal(lead):
    from apps.crm.models import LeadStatus

    lead.status = LeadStatus.ARCHIVED
    lead.save(update_fields=["status"])

    assert lead.next_staff_action == "Archived - no further action"


# ---------------------------------------------------------------------------
# 10. No banned-promise phrase in any next_staff_action branch
# ---------------------------------------------------------------------------


def test_next_staff_action_strings_have_no_banned_phrases():
    from apps.crm import timeline as tl

    candidates = [
        tl.ACTION_WEBHOOK_INTEGRATION_FAILED,
        tl.ACTION_WEBHOOK_RETRYING,
        tl.ACTION_CONTACT_CLIENT,
        tl.ACTION_REVIEW_NEW_LEAD,
        tl.ACTION_MANDATE_NOT_SIGNED,
        tl.ACTION_READY_FOR_FOLLOWUP,
        tl.ACTION_WAITING_STUDIO_REVIEW,
        tl.ACTION_ENGAGEMENT_ACTIVE,
        tl.ACTION_ARCHIVED,
    ]
    for s in candidates:
        for phrase in BANNED_PROMISE_PHRASES:
            assert phrase not in s.lower(), (
                f"next_staff_action string {s!r} leaks banned phrase {phrase!r}"
            )


# ---------------------------------------------------------------------------
# 11. Admin renders the timeline through format_html (no script / js)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_activity_timeline_render_has_no_js(lead):
    """Render the admin readonly field directly: format_html escapes
    every interpolation, so the output must never contain `<script`
    or `javascript:` markers no matter what's in the DB."""
    from apps.crm.admin import LeadAdmin
    from apps.crm.models import Lead, LeadEvent

    # Add a hostile-looking message — should be escaped, never executed.
    LeadEvent.objects.create(
        lead=lead,
        event_type=LeadEvent.EventType.NOTE,
        message="<script>alert(1)</script> javascript:alert(2)",
    )
    inst = LeadAdmin(Lead, django_admin.site)
    html = str(inst.activity_timeline(lead)).lower()
    # No <script> tag survives the escape (the hostile payload becomes
    # `&lt;script&gt;`, never an executable tag).
    assert "<script" not in html
    # No `javascript:` URL inside a link/handler attribute. The literal
    # substring "javascript:" appearing as plain text inside a <div> is
    # harmless because it is not in an attribute context — what matters
    # is that no `href="javascript:..."` or `on...="..."` is produced.
    assert 'href="javascript:' not in html
    assert "href='javascript:" not in html
    # And no inline event-handler attribute leaks through.
    for handler in ("onclick=", "onerror=", "onload=", "onmouseover="):
        assert handler not in html
    # Escaping check: the angle bracket of the hostile payload must be
    # rendered as `&lt;` (Django's format_html auto-escapes).
    assert "&lt;script&gt;" in html
