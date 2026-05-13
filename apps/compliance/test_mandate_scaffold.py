"""
Tests F-p0-leg-2-mandate.

Coprono lo scaffold del mandato professionale (separazione fra
richiesta in entrata e incarico):

1. Lead creato dal contact form ha mandate_signed=False / status=mandate_required;
2. Simulation creata dal wizard non ha campi mandate (e' pre-contrattuale);
3. mark_mandate_signed imposta i campi denormalizzati e crea MandateAcceptance;
4. mark_mandate_signed e' idempotente sulla stessa versione;
5. mark_mandate_signed promuove lo status del lead a CONVERTED;
6. mark_mandate_signed registra un PrivacyAuditEvent;
7. assert_mandate_signed_for_case_activation solleva senza firma;
8. assert_mandate_signed_for_case_activation e' no-op con flag spento;
9. assert_mandate_signed_for_case_activation e' no-op con lead firmato;
10. core.E008 fail in prod con working-copy version;
11. core.E008 fail in prod con status non-signed;
12. core.E008 fail in prod con REQUIRE_MANDATE flag spento;
13. core.E008 passa in prod con configurazione completa;
14. contact_thank_you mostra il riquadro mandate notice;
15. wizard_result mostra il riquadro mandate notice;
16. admin Lead espone i campi mandate.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from django.test import Client, override_settings
from django.utils import timezone

from apps.cases.models import Simulation
from apps.compliance.mandate import (
    MandateNotSignedError,
    assert_mandate_signed_for_case_activation,
    mark_mandate_signed,
)
from apps.compliance.models import MandateAcceptance, PrivacyAuditEvent
from apps.core.checks import check_mandate_template_signed_in_production
from apps.crm.models import Lead, LeadStatus, MandateStatus

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lead(**overrides) -> Lead:
    base = {
        "first_name": "Mario",
        "last_name": "Rossi",
        "email": "mario@example.test",
        "message": "Test request",
        "privacy_consent_given": True,
        "privacy_consent_at": timezone.now(),
        "privacy_consent_version": "2026-01-final",
        "special_categories_consent_given": True,
        "special_categories_consent_at": timezone.now(),
        "special_categories_consent_version": "2026-01-final",
    }
    base.update(overrides)
    return Lead.objects.create(**base)


# ---------------------------------------------------------------------------
# 1-2: defaults
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_lead_default_mandate_state():
    lead = _make_lead()
    assert lead.mandate_signed is False
    assert lead.mandate_signed_at is None
    assert lead.mandate_version == ""
    assert lead.mandate_status == MandateStatus.REQUIRED
    assert lead.mandate_source == ""


@pytest.mark.django_db
def test_simulation_has_no_mandate_fields():
    """Simulation is always pre-contractual; mandate fields belong on Lead only."""
    sim = Simulation.objects.create(case_type="road_accident", locale="it")
    assert not hasattr(sim, "mandate_signed")
    assert not hasattr(sim, "mandate_status")


# ---------------------------------------------------------------------------
# 3-6: mark_mandate_signed
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_mark_mandate_signed_writes_denormalized_fields_and_acceptance():
    lead = _make_lead()
    signed_at = datetime(2026, 9, 15, 12, 0, 0, tzinfo=UTC)
    acceptance = mark_mandate_signed(
        lead,
        version="2026-09-15-final",
        signed_at=signed_at,
        source="staff",
        client_name_snapshot="Mario Rossi",
        locale="it",
    )
    lead.refresh_from_db()
    assert lead.mandate_signed is True
    assert lead.mandate_signed_at == signed_at
    assert lead.mandate_version == "2026-09-15-final"
    assert lead.mandate_status == MandateStatus.SIGNED
    assert lead.mandate_source == "staff"
    # Acceptance ledger row created.
    assert isinstance(acceptance, MandateAcceptance)
    assert acceptance.lead_id == lead.pk
    assert acceptance.accepted is True
    assert acceptance.signed_at == signed_at
    assert acceptance.client_name_snapshot == "Mario Rossi"


@pytest.mark.django_db
def test_mark_mandate_signed_is_idempotent_on_same_version():
    lead = _make_lead()
    signed_at = timezone.now()
    a = mark_mandate_signed(lead, version="v1", signed_at=signed_at)
    b = mark_mandate_signed(lead, version="v1", signed_at=signed_at)
    assert a.pk == b.pk
    assert MandateAcceptance.objects.filter(lead=lead, mandate_version="v1").count() == 1


@pytest.mark.django_db
def test_mark_mandate_signed_promotes_lead_status_to_converted():
    lead = _make_lead()
    assert lead.status == LeadStatus.RECEIVED
    mark_mandate_signed(lead, version="v1", signed_at=timezone.now())
    lead.refresh_from_db()
    assert lead.status == LeadStatus.CONVERTED
    assert lead.converted_at is not None


@pytest.mark.django_db
def test_mark_mandate_signed_does_not_unarchive_lead():
    lead = _make_lead(status=LeadStatus.ARCHIVED)
    mark_mandate_signed(lead, version="v1", signed_at=timezone.now())
    lead.refresh_from_db()
    assert lead.status == LeadStatus.ARCHIVED


@pytest.mark.django_db
def test_mark_mandate_signed_logs_privacy_audit_event():
    lead = _make_lead()
    mark_mandate_signed(lead, version="v1", signed_at=timezone.now())
    event = PrivacyAuditEvent.objects.filter(
        target_model="crm.Lead",
        target_object_id=str(lead.pk),
        metadata__trigger="mandate_signed",
    ).first()
    assert event is not None
    assert event.metadata["mandate_version"] == "v1"


# ---------------------------------------------------------------------------
# 7-9: activation guard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_guard_raises_when_not_signed():
    lead = _make_lead()
    with pytest.raises(MandateNotSignedError):
        assert_mandate_signed_for_case_activation(lead)


@override_settings(REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=False)
@pytest.mark.django_db
def test_guard_is_noop_when_flag_disabled():
    lead = _make_lead()
    # Must NOT raise.
    assert_mandate_signed_for_case_activation(lead)


@pytest.mark.django_db
def test_guard_is_noop_when_lead_signed():
    lead = _make_lead()
    mark_mandate_signed(lead, version="v1", signed_at=timezone.now())
    lead.refresh_from_db()
    # Must NOT raise.
    assert_mandate_signed_for_case_activation(lead)


# ---------------------------------------------------------------------------
# 10-13: core.E008
# ---------------------------------------------------------------------------


@override_settings(
    DEBUG=False,
    MANDATE_TEMPLATE_VERSION="working-copy-2026-05-10",
    MANDATE_TEMPLATE_STATUS="working_copy",
    MANDATE_TEMPLATE_SIGNED_AT="",
    REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True,
)
def test_E008_fails_with_working_copy_version():
    issues = check_mandate_template_signed_in_production(app_configs=None)
    assert any(i.id == "core.E008" for i in issues)
    assert any("working-copy" in i.msg for i in issues)


@override_settings(
    DEBUG=False,
    MANDATE_TEMPLATE_VERSION="2026-09-15-final",
    MANDATE_TEMPLATE_STATUS="working_copy",
    MANDATE_TEMPLATE_SIGNED_AT="",
    REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True,
)
def test_E008_fails_when_status_not_signed():
    issues = check_mandate_template_signed_in_production(app_configs=None)
    assert any(i.id == "core.E008" and "not 'signed'" in i.msg for i in issues)


@override_settings(
    DEBUG=False,
    MANDATE_TEMPLATE_VERSION="2026-09-15-final",
    MANDATE_TEMPLATE_STATUS="signed",
    MANDATE_TEMPLATE_SIGNED_AT="2026-09-15",
    REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=False,
)
def test_E008_fails_when_require_flag_off():
    issues = check_mandate_template_signed_in_production(app_configs=None)
    assert any(
        i.id == "core.E008" and "REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION" in i.msg
        for i in issues
    )


@override_settings(
    DEBUG=False,
    MANDATE_TEMPLATE_VERSION="2026-09-15-final",
    MANDATE_TEMPLATE_STATUS="signed",
    MANDATE_TEMPLATE_SIGNED_AT="2026-09-15",
    REQUIRE_MANDATE_BEFORE_CASE_ACTIVATION=True,
)
def test_E008_passes_with_signed_and_flag_on():
    assert check_mandate_template_signed_in_production(app_configs=None) == []


# ---------------------------------------------------------------------------
# 14-15: thank-you / result mandate notice
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_thank_you_renders_mandate_notice():
    body = Client().get("/contact/thank-you/").content.decode("utf-8")
    assert "data-mandate-notice" in body
    # The visible English label of the section, present even before
    # translations are populated.
    assert "Professional engagement" in body or "engagement" in body.lower()


@pytest.mark.django_db
def test_wizard_result_renders_mandate_notice():
    sim = Simulation.objects.create(case_type="road_accident", locale="it")
    body = Client().get(f"/wizard/result/{sim.public_id}/").content.decode("utf-8")
    assert "data-mandate-notice" in body


# ---------------------------------------------------------------------------
# 16: admin exposes mandate fields
# ---------------------------------------------------------------------------


def test_lead_admin_exposes_mandate_fields():
    from apps.crm.admin import LeadAdmin

    list_display = LeadAdmin.list_display
    list_filter = LeadAdmin.list_filter
    assert "mandate_signed" in list_display
    assert "mandate_status" in list_display
    assert "mandate_signed" in list_filter
    assert "mandate_status" in list_filter
