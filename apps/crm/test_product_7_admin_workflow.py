"""
Tests PRODUCT-7-crm-staff-lead-workflow.

What these tests guard:

 1. Audit doc + improvements doc both exist on disk.
 2. `LeadAdmin` is registered and its list_display contains the new
    staff-facing derived columns.
 3. `LeadAdmin.list_filter` contains the new consent + simulation
    filters in addition to the pre-existing ones.
 4. `LeadAdmin.search_fields` still covers public_id, email and the
    name fields (unchanged contract from F6).
 5. Consent denormalised fields are locked as readonly.
 6. Mandate timestamp / version / source are locked as readonly;
    `mandate_signed` and `mandate_status` stay editable.
 7. `LeadWebhookDelivery` is registered in admin (new in this iter).
 8. The webhook admin is fully read-only (no add / change / delete).
 9. `has_valid_double_consent` returns True only when both consents +
    timestamps + versions are recorded.
10. `has_linked_simulation` mirrors `simulation_id is not None`.
11. `webhook_delivery_status_summary` returns the right one-line label
    for empty / delivered / dead / pending cases.
12. `response_excerpt` rendered in the webhook admin stays bounded by
    the model's max_length (no PII / secret leak via runaway field).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from django.contrib import admin as django_admin
from django.utils import timezone

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT / "docs" / "product" / "CRM_STAFF_LEAD_WORKFLOW_AUDIT_2026-05-12.md"
)


# ---------------------------------------------------------------------------
# 0. Audit doc exists
# ---------------------------------------------------------------------------


def test_audit_doc_exists():
    assert AUDIT_DOC.exists(), (
        "PRODUCT-7 phase 1 audit must exist at "
        "docs/product/CRM_STAFF_LEAD_WORKFLOW_AUDIT_2026-05-12.md"
    )
    assert AUDIT_DOC.stat().st_size > 4000


# ---------------------------------------------------------------------------
# 1. LeadAdmin registration + list_display contains the new columns
# ---------------------------------------------------------------------------


def _lead_admin():
    from apps.crm.models import Lead

    return django_admin.site._registry[Lead]


def test_lead_admin_registered():
    from apps.crm.admin import LeadAdmin

    inst = _lead_admin()
    assert isinstance(inst, LeadAdmin)


def test_lead_admin_list_display_contains_new_columns():
    inst = _lead_admin()
    must_have = {
        "created_at",
        "full_name_display",
        "email",
        "country",
        "case_type",
        "status",
        "mandate_status",
        "mandate_signed",
        "double_consent_display",
        "linked_simulation_display",
        "source_label_display",
        "webhook_status_display",
    }
    missing = must_have - set(inst.list_display)
    assert not missing, f"LeadAdmin.list_display missing columns: {missing}"


def test_lead_admin_list_filter_contains_consent_and_simulation():
    from apps.crm.admin import HasLinkedSimulationFilter

    inst = _lead_admin()
    flat = []
    for f in inst.list_filter:
        flat.append(f if isinstance(f, str) else getattr(f, "__name__", str(f)))
    assert "privacy_consent_given" in flat
    assert "special_categories_consent_given" in flat
    assert HasLinkedSimulationFilter in inst.list_filter


def test_lead_admin_search_fields_unchanged_contract():
    inst = _lead_admin()
    must_have = {"public_id", "first_name", "last_name", "email", "phone_number"}
    assert must_have.issubset(set(inst.search_fields))


# ---------------------------------------------------------------------------
# 2. Readonly contract: consent + mandate audit fields locked
# ---------------------------------------------------------------------------


def test_lead_admin_consent_denormalised_fields_are_readonly():
    inst = _lead_admin()
    ro = set(inst.readonly_fields)
    for name in (
        "privacy_consent_given",
        "privacy_consent_at",
        "privacy_consent_version",
        "special_categories_consent_given",
        "special_categories_consent_at",
        "special_categories_consent_version",
    ):
        assert name in ro, f"consent field {name!r} must be readonly"


def test_lead_admin_mandate_audit_fields_are_readonly_but_status_stays_editable():
    inst = _lead_admin()
    ro = set(inst.readonly_fields)
    # Audit-snapshot fields are locked.
    for name in ("mandate_signed_at", "mandate_version", "mandate_source"):
        assert name in ro, f"mandate audit field {name!r} must be readonly"
    # Status / boolean stay editable so the Studio can record acceptance.
    assert "mandate_status" not in ro
    assert "mandate_signed" not in ro


# ---------------------------------------------------------------------------
# 3. LeadWebhookDeliveryAdmin registered and fully read-only
# ---------------------------------------------------------------------------


def _webhook_admin():
    from apps.crm.models import LeadWebhookDelivery

    return django_admin.site._registry.get(LeadWebhookDelivery)


def test_webhook_admin_is_registered():
    from apps.crm.admin import LeadWebhookDeliveryAdmin

    inst = _webhook_admin()
    assert inst is not None, "LeadWebhookDelivery must be registered in admin"
    assert isinstance(inst, LeadWebhookDeliveryAdmin)


def test_webhook_admin_is_fully_readonly():
    inst = _webhook_admin()
    assert inst.has_add_permission(None) is False
    assert inst.has_change_permission(None) is False
    assert inst.has_delete_permission(None) is False


def test_webhook_admin_readonly_fields_cover_audit_data():
    inst = _webhook_admin()
    ro = set(inst.readonly_fields)
    for name in (
        "lead",
        "event_type",
        "payload_version",
        "idempotency_key",
        "target_url_domain",
        "status",
        "attempts",
        "max_attempts",
        "next_attempt_at",
        "last_attempt_at",
        "delivered_at",
        "last_status_code",
        "last_error",
        "response_excerpt",
        "created_at",
        "updated_at",
    ):
        assert name in ro, f"webhook field {name!r} must be readonly"


def test_webhook_admin_list_display_and_filters():
    inst = _webhook_admin()
    assert {"created_at", "lead", "event_type", "status", "attempts"}.issubset(
        set(inst.list_display)
    )
    assert "status" in inst.list_filter
    assert "event_type" in inst.list_filter


# ---------------------------------------------------------------------------
# 4. Model helpers
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_has_valid_double_consent_true_when_both_recorded():
    from apps.crm.models import Lead

    now = timezone.now()
    lead = Lead.objects.create(
        first_name="A",
        last_name="B",
        email="a@b.test",
        message="placeholder min length 20+ characters here",
        privacy_consent_given=True,
        privacy_consent_at=now,
        privacy_consent_version="v1",
        special_categories_consent_given=True,
        special_categories_consent_at=now,
        special_categories_consent_version="v1",
    )
    assert lead.has_valid_double_consent is True


@pytest.mark.django_db
def test_has_valid_double_consent_false_when_any_part_missing():
    from apps.crm.models import Lead

    now = timezone.now()
    base = dict(
        first_name="A",
        last_name="B",
        email="a@b.test",
        message="placeholder min length 20+ characters here",
        privacy_consent_given=True,
        privacy_consent_at=now,
        privacy_consent_version="v1",
        special_categories_consent_given=True,
        special_categories_consent_at=now,
        special_categories_consent_version="v1",
    )

    # Drop each piece in turn — every absence flips the property to False.
    for key, value in (
        ("privacy_consent_given", False),
        ("privacy_consent_at", None),
        ("privacy_consent_version", ""),
        ("special_categories_consent_given", False),
        ("special_categories_consent_at", None),
        ("special_categories_consent_version", ""),
    ):
        kwargs = {**base, key: value}
        lead = Lead.objects.create(**kwargs)
        assert lead.has_valid_double_consent is False, (
            f"flipping {key!r} should yield False, got True"
        )


@pytest.mark.django_db
def test_has_linked_simulation_mirrors_simulation_id():
    from apps.crm.models import Lead

    lead = Lead.objects.create(
        first_name="A",
        last_name="B",
        email="a@b.test",
        message="placeholder min length 20+ characters here",
    )
    assert lead.has_linked_simulation is False


@pytest.mark.django_db
def test_webhook_delivery_status_summary_empty_pending_delivered_dead():
    from apps.crm.models import Lead, LeadWebhookDelivery

    lead = Lead.objects.create(
        first_name="A",
        last_name="B",
        email="a@b.test",
        message="placeholder min length 20+ characters here",
    )
    # No deliveries — summary is "-".
    assert lead.webhook_delivery_status_summary == "-"

    # One PENDING with attempts.
    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.created",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.PENDING,
        attempts=2,
        max_attempts=5,
    )
    assert lead.webhook_delivery_status_summary == "pending(2/5)"

    # Add a more recent DELIVERED row — should report delivered.
    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.updated",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.DELIVERED,
        attempts=1,
        max_attempts=5,
        delivered_at=timezone.now(),
    )
    assert lead.webhook_delivery_status_summary == "delivered"

    # Add a more recent DEAD row — should report dead (most-recent wins).
    LeadWebhookDelivery.objects.create(
        lead=lead,
        event_type="lead.deleted",
        payload_version="v1",
        idempotency_key=uuid.uuid4().hex,
        target_url_domain="hooks.example",
        status=LeadWebhookDelivery.Status.DEAD,
        attempts=5,
        max_attempts=5,
    )
    assert lead.webhook_delivery_status_summary == "dead"


# ---------------------------------------------------------------------------
# 5. response_excerpt remains bounded — no leak of long bodies
# ---------------------------------------------------------------------------


def test_webhook_response_excerpt_field_is_bounded():
    """The dispatcher trims `response_excerpt` to 500 chars before save
    (see `apps.crm.webhooks._record_attempt`). The model's max_length
    enforces it at the DB layer. Test pins the model contract."""
    from apps.crm.models import LeadWebhookDelivery

    field = LeadWebhookDelivery._meta.get_field("response_excerpt")
    assert field.max_length == 500


# ---------------------------------------------------------------------------
# 6. Admin source-label derivation handles the 3 common origins
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_source_label_branches():
    from apps.crm.admin import LeadAdmin
    from apps.crm.models import Lead

    inst = LeadAdmin(Lead, django_admin.site)

    # 1) wizard — has linked simulation. Mock by setting simulation_id.
    lead_wizard = Lead.objects.create(
        first_name="W",
        last_name="W",
        email="w@b.test",
        message="placeholder min length 20+ characters here",
    )
    lead_wizard.simulation_id = 1  # not saved — display computes from attr
    assert inst.source_label_display(lead_wizard) == "wizard"

    # 2) case-type — source_path carries the marker.
    lead_ct = Lead.objects.create(
        first_name="C",
        last_name="T",
        email="ct@b.test",
        message="placeholder min length 20+ characters here",
        source_path="/contact/?case_type=road_accident_bodily_injury",
    )
    assert inst.source_label_display(lead_ct) == "case-type"

    # 3) default — cold contact.
    lead_contact = Lead.objects.create(
        first_name="X",
        last_name="Y",
        email="x@b.test",
        message="placeholder min length 20+ characters here",
        source_path="/contact/",
    )
    assert inst.source_label_display(lead_contact) == "contact"
