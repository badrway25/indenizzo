"""
Tests F-p0-leg-4-retention.

Coprono lo scaffold della wide retention policy:

1. system check `compliance.E001` fail in prod con working-copy version;
2. system check `compliance.E001` fail in prod con version vuota;
3. system check `compliance.E001` fail con RETENTION_MODE invalido;
4. system check `compliance.E001` fail con enabled+dry_run in prod;
5. system check passa in prod con version firmata + mode dry_run+disabled;
6. dry_run NON modifica Lead / Simulation;
7. dry_run crea RetentionRunLog con status=success;
8. anonymize oscura PII su Lead candidato;
9. anonymize NON tocca Lead piu' recente del cutoff;
10. anonymize mantiene il consent_record FK e le versioni consenso;
11. delete senza allow_delete fallisce con RuntimeError;
12. management command --mode=anonymize senza --yes-i-understand fallisce;
13. management command --mode=delete senza --allow-delete fallisce;
14. cutoff calcolato correttamente da get_retention_cutoffs.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from io import StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from django.utils import timezone

from apps.cases.models import Simulation
from apps.compliance.checks import check_retention_policy_signed_in_production
from apps.compliance.models import (
    ConsentPurpose,
    ConsentRecord,
    PrivacyAuditEvent,
    RetentionRunLog,
)
from apps.compliance.retention import (
    collect_retention_candidates,
    get_retention_cutoffs,
    run_retention,
)
from apps.crm.models import Lead

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_lead(**overrides) -> Lead:
    base = {
        "first_name": "Mario",
        "last_name": "Rossi",
        "email": "mario@example.test",
        "phone_number": "",
        "message": "Test message",
        "ip_address": "203.0.113.10",
        "user_agent": "ua-test",
        "session_key": "sess-abc",
        "source_path": "/contact/",
        "internal_notes": "staff-only",
        "privacy_consent_given": True,
        "privacy_consent_at": timezone.now(),
        "privacy_consent_version": "2026-01-final",
        "special_categories_consent_given": True,
        "special_categories_consent_at": timezone.now(),
        "special_categories_consent_version": "2026-01-final",
    }
    base.update(overrides)
    return Lead.objects.create(**base)


def _force_created_at(model_obj, *, created_at):
    """Bypass auto_now_add to backdate created_at for retention testing."""
    model_obj.__class__.objects.filter(pk=model_obj.pk).update(created_at=created_at)
    model_obj.refresh_from_db()


# ---------------------------------------------------------------------------
# 1-5: system check compliance.E001
# ---------------------------------------------------------------------------


@override_settings(
    DEBUG=False,
    RETENTION_POLICY_VERSION="working-copy-2026-05-10",
    RETENTION_MODE="dry_run",
    RETENTION_ENABLED=False,
    RETENTION_REQUIRE_SIGNED_VERSION=True,
)
def test_check_E001_fails_with_working_copy_version():
    issues = check_retention_policy_signed_in_production(app_configs=None)
    ids = [i.id for i in issues]
    assert "compliance.E001" in ids
    assert any("working-copy" in i.msg for i in issues)


@override_settings(
    DEBUG=False,
    RETENTION_POLICY_VERSION="",
    RETENTION_MODE="dry_run",
    RETENTION_ENABLED=False,
    RETENTION_REQUIRE_SIGNED_VERSION=True,
)
def test_check_E001_fails_with_empty_version():
    issues = check_retention_policy_signed_in_production(app_configs=None)
    assert any(i.id == "compliance.E001" and "empty" in i.msg.lower() for i in issues)


@override_settings(
    DEBUG=False,
    RETENTION_POLICY_VERSION="2026-09-15-final",
    RETENTION_MODE="banana",
    RETENTION_ENABLED=False,
    RETENTION_REQUIRE_SIGNED_VERSION=True,
)
def test_check_E001_fails_with_invalid_mode():
    issues = check_retention_policy_signed_in_production(app_configs=None)
    assert any(
        i.id == "compliance.E001" and "RETENTION_MODE" in i.msg and "banana" in i.msg
        for i in issues
    )


@override_settings(
    DEBUG=False,
    RETENTION_POLICY_VERSION="2026-09-15-final",
    RETENTION_MODE="dry_run",
    RETENTION_ENABLED=True,
    RETENTION_REQUIRE_SIGNED_VERSION=True,
)
def test_check_E001_fails_when_enabled_with_dry_run_in_prod():
    issues = check_retention_policy_signed_in_production(app_configs=None)
    assert any(
        i.id == "compliance.E001" and "ambiguous" in i.msg.lower() for i in issues
    )


@override_settings(
    DEBUG=False,
    RETENTION_POLICY_VERSION="2026-09-15-final",
    RETENTION_MODE="dry_run",
    RETENTION_ENABLED=False,
    RETENTION_REQUIRE_SIGNED_VERSION=True,
)
def test_check_E001_passes_with_signed_version_disabled():
    issues = check_retention_policy_signed_in_production(app_configs=None)
    assert issues == []


# ---------------------------------------------------------------------------
# 6-7: dry-run does not mutate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dry_run_does_not_modify_lead_or_simulation():
    lead = _make_lead()
    _force_created_at(lead, created_at=timezone.now() - timedelta(days=400))

    sim = Simulation.objects.create(
        case_type="road_accident",
        locale="it",
        input_data={"foo": "bar"},
        ip_address="203.0.113.55",
        session_key="sim-key",
        user_agent="ua-sim",
        source_path="/wizard/it/road-accident/",
    )
    _force_created_at(sim, created_at=timezone.now() - timedelta(days=400))

    result = run_retention(mode="dry_run", executed_by="test")
    assert result["lead_candidates"] == 1
    assert result["simulation_candidates"] == 1
    assert result["anonymized_count"] == 0
    assert result["deleted_count"] == 0

    lead.refresh_from_db()
    sim.refresh_from_db()
    assert lead.first_name == "Mario"
    assert lead.email == "mario@example.test"
    assert lead.anonymized is False
    assert sim.input_data == {"foo": "bar"}
    assert sim.anonymized is False


@pytest.mark.django_db
def test_dry_run_creates_retention_run_log_success():
    result = run_retention(mode="dry_run", executed_by="test")
    log = RetentionRunLog.objects.get(pk=result["log_id"])
    assert log.status == RetentionRunLog.Status.SUCCESS
    assert log.mode == RetentionRunLog.Mode.DRY_RUN
    assert log.dry_run is True
    assert log.executed_by == "test"
    assert log.finished_at is not None


# ---------------------------------------------------------------------------
# 8-10: anonymize behavior
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_anonymize_redacts_pii_on_expired_lead():
    purpose, _ = ConsentPurpose.objects.get_or_create(
        code="lead_contact",
        defaults={"name": "lead", "required_for_contact": True},
    )
    consent = ConsentRecord.objects.create(
        purpose=purpose,
        accepted=True,
        accepted_at=timezone.now(),
        ip_address="203.0.113.10",
        user_agent="ua-test",
    )
    lead = _make_lead(consent_record=consent)
    _force_created_at(lead, created_at=timezone.now() - timedelta(days=400))

    result = run_retention(mode="anonymize", executed_by="test")
    assert result["anonymized_count"] >= 1

    lead.refresh_from_db()
    assert lead.anonymized is True
    assert lead.anonymized_at is not None
    assert lead.first_name == ""
    assert lead.last_name == ""
    assert lead.email == "anonymized@example.invalid"
    assert lead.phone_number == ""
    assert lead.message == ""
    assert lead.ip_address is None
    assert lead.user_agent == ""
    assert lead.session_key == ""
    assert lead.internal_notes == ""


@pytest.mark.django_db
def test_anonymize_skips_lead_inside_retention_window():
    lead = _make_lead()
    # Lead is fresh: NOT a candidate.
    run_retention(mode="anonymize", executed_by="test")
    lead.refresh_from_db()
    assert lead.anonymized is False
    assert lead.first_name == "Mario"


@pytest.mark.django_db
def test_anonymize_keeps_consent_versions_and_record_fk():
    purpose, _ = ConsentPurpose.objects.get_or_create(
        code="lead_contact",
        defaults={"name": "lead", "required_for_contact": True},
    )
    consent = ConsentRecord.objects.create(
        purpose=purpose,
        accepted=True,
        accepted_at=timezone.now(),
    )
    lead = _make_lead(consent_record=consent)
    _force_created_at(lead, created_at=timezone.now() - timedelta(days=400))

    run_retention(mode="anonymize", executed_by="test")
    lead.refresh_from_db()
    assert lead.consent_record_id == consent.pk
    assert lead.privacy_consent_given is True
    assert lead.privacy_consent_version == "2026-01-final"
    assert lead.special_categories_consent_given is True
    assert lead.special_categories_consent_version == "2026-01-final"


# ---------------------------------------------------------------------------
# 11: delete refused without allow_delete
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_delete_mode_refuses_without_allow_delete_flag():
    lead = _make_lead()
    _force_created_at(lead, created_at=timezone.now() - timedelta(days=400))

    with pytest.raises(RuntimeError, match="refused in P0"):
        run_retention(mode="delete", executed_by="test", allow_delete=False)

    lead.refresh_from_db()
    assert lead.first_name == "Mario"
    # The failed run is logged with status=failed.
    failed = RetentionRunLog.objects.filter(
        status=RetentionRunLog.Status.FAILED
    ).first()
    assert failed is not None
    assert "refused" in failed.error_message.lower()


# ---------------------------------------------------------------------------
# 12-13: management command guards
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_command_anonymize_without_confirmation_fails():
    with pytest.raises(CommandError, match="--yes-i-understand"):
        call_command("run_retention_policy", "--mode=anonymize", stdout=StringIO())


@pytest.mark.django_db
def test_command_delete_without_allow_delete_fails():
    with pytest.raises(CommandError, match="--allow-delete"):
        call_command(
            "run_retention_policy",
            "--mode=delete",
            "--yes-i-understand",
            stdout=StringIO(),
        )


@pytest.mark.django_db
def test_command_dry_run_prints_candidate_counts():
    out = StringIO()
    call_command("run_retention_policy", stdout=out)
    text = out.getvalue()
    assert "Candidates:" in text
    assert "Lead:" in text
    assert "Simulation:" in text
    assert "Dry-run" in text


# ---------------------------------------------------------------------------
# 14: cutoff math
# ---------------------------------------------------------------------------


@override_settings(
    RETENTION_LEAD_DAYS=30,
    RETENTION_SIMULATION_DAYS=60,
    RETENTION_CONSENT_RECORD_DAYS=90,
    RETENTION_AUDIT_LOG_DAYS=120,
)
def test_get_retention_cutoffs_uses_settings_days():
    fixed_now = datetime(2026, 5, 10, 12, 0, 0, tzinfo=UTC)
    cutoffs = get_retention_cutoffs(now=fixed_now)
    assert cutoffs.lead_days == 30
    assert cutoffs.simulation_days == 60
    assert cutoffs.consent_days == 90
    assert cutoffs.audit_days == 120
    assert cutoffs.lead_cutoff == fixed_now - timedelta(days=30)
    assert cutoffs.simulation_cutoff == fixed_now - timedelta(days=60)
    assert cutoffs.consent_cutoff == fixed_now - timedelta(days=90)
    assert cutoffs.audit_cutoff == fixed_now - timedelta(days=120)


@pytest.mark.django_db
def test_collect_candidates_counts_audit_and_consent_only():
    """ConsentRecord and PrivacyAuditEvent are counted but not deleted."""
    purpose, _ = ConsentPurpose.objects.get_or_create(
        code="lead_contact",
        defaults={"name": "lead", "required_for_contact": True},
    )
    old_consent = ConsentRecord.objects.create(
        purpose=purpose,
        accepted=True,
        accepted_at=timezone.now() - timedelta(days=2000),
    )
    PrivacyAuditEvent.objects.create(
        event_type="data_accessed",
        target_model="cases.Simulation",
        target_object_id="42",
    )
    PrivacyAuditEvent.objects.filter(pk__gt=0).update(
        created_at=timezone.now() - timedelta(days=2000)
    )

    snap = collect_retention_candidates()
    assert snap["consent_candidates"] >= 1
    assert snap["audit_candidates"] >= 1

    # Anonymize must NOT touch them.
    run_retention(mode="anonymize", executed_by="test")
    assert ConsentRecord.objects.filter(pk=old_consent.pk).exists()
    assert PrivacyAuditEvent.objects.exists()
