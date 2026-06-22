"""
Tests F-local-product-hardening-pass10-staff-audit-cleanup-task.

Coprono:
- cutoffs calcolati correttamente da settings;
- dry-run conta expired ma non cancella;
- commit cancella SOLO expired (i recenti restano);
- cleanup non tocca PrivacyAuditEvent / LegalReview / SimulationReport;
- management command dry-run output + zero delete;
- management command --commit cancella expired;
- Celery task default dry-run da settings;
- settings defaults sicuri (dry-run True);
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

# ---------------------------------------------------------------------------
# Helpers: scrivono direttamente i timestamp arbitrari sui record
# (created_at / triggered_at sono `auto_now_add`, ma `update()` li
# bypassa: lo usiamo per simulare "vecchi 100 giorni").
# ---------------------------------------------------------------------------


def _make_access_event(created_at):
    from apps.compliance.models import StaffAccessEvent

    ev = StaffAccessEvent.objects.create(
        event_type="login_success",
        username_hash="hashvalue",
        ip_address_masked="10.0.0.x",
        user_agent_hash="ua-hash",
        path="/admin/",
    )
    StaffAccessEvent.objects.filter(pk=ev.pk).update(created_at=created_at)
    ev.refresh_from_db()
    return ev


def _make_security_alert(triggered_at):
    from apps.compliance.models import StaffSecurityAlert

    alert = StaffSecurityAlert.objects.create(
        alert_type="admin_login_bruteforce",
        severity="medium",
        username_hash="hashvalue",
        ip_address_masked="10.0.0.x",
        event_count=5,
        window_seconds=900,
    )
    StaffSecurityAlert.objects.filter(pk=alert.pk).update(triggered_at=triggered_at)
    alert.refresh_from_db()
    return alert


# ---------------------------------------------------------------------------
# Task F.1 — cutoffs
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_ACCESS_EVENT_RETENTION_DAYS=90,
    STAFF_SECURITY_ALERT_RETENTION_DAYS=180,
)
def test_cutoffs_match_settings():
    from apps.compliance.retention import get_staff_audit_retention_cutoffs

    fixed = timezone.now()
    cutoffs = get_staff_audit_retention_cutoffs(now=fixed)
    assert cutoffs["staff_access_retention_days"] == 90
    assert cutoffs["staff_alert_retention_days"] == 180
    assert cutoffs["staff_access_cutoff"] == fixed - timedelta(days=90)
    assert cutoffs["staff_alert_cutoff"] == fixed - timedelta(days=180)


# ---------------------------------------------------------------------------
# Task F.2 — dry-run conta ma non cancella
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_ACCESS_EVENT_RETENTION_DAYS=90,
    STAFF_SECURITY_ALERT_RETENTION_DAYS=180,
)
@pytest.mark.django_db
def test_dry_run_counts_but_does_not_delete():
    from apps.compliance.models import StaffAccessEvent, StaffSecurityAlert
    from apps.compliance.retention import cleanup_staff_audit_events

    now = timezone.now()
    # 2 expired access (101 days old) + 1 fresh (1 day old)
    _make_access_event(created_at=now - timedelta(days=101))
    _make_access_event(created_at=now - timedelta(days=200))
    _make_access_event(created_at=now - timedelta(days=1))
    # 1 expired alert (200 days) + 1 fresh (10 days)
    _make_security_alert(triggered_at=now - timedelta(days=200))
    _make_security_alert(triggered_at=now - timedelta(days=10))

    result = cleanup_staff_audit_events(dry_run=True, now=now)

    assert result["dry_run"] is True
    assert result["access_expired"] == 2
    assert result["alerts_expired"] == 1
    assert result["access_deleted"] == 0
    assert result["alerts_deleted"] == 0
    # Nessun record cancellato.
    assert StaffAccessEvent.objects.count() == 3
    assert StaffSecurityAlert.objects.count() == 2


# ---------------------------------------------------------------------------
# Task F.3 — commit cancella SOLO expired
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_ACCESS_EVENT_RETENTION_DAYS=90,
    STAFF_SECURITY_ALERT_RETENTION_DAYS=180,
)
@pytest.mark.django_db
def test_commit_deletes_only_expired_records():
    from apps.compliance.models import StaffAccessEvent, StaffSecurityAlert
    from apps.compliance.retention import cleanup_staff_audit_events

    now = timezone.now()
    expired_ev = _make_access_event(created_at=now - timedelta(days=101))
    fresh_ev = _make_access_event(created_at=now - timedelta(days=1))
    expired_alert = _make_security_alert(triggered_at=now - timedelta(days=200))
    fresh_alert = _make_security_alert(triggered_at=now - timedelta(days=10))

    result = cleanup_staff_audit_events(dry_run=False, now=now)

    assert result["dry_run"] is False
    assert result["access_deleted"] == 1
    assert result["alerts_deleted"] == 1
    # I recenti restano:
    assert StaffAccessEvent.objects.filter(pk=fresh_ev.pk).exists()
    assert StaffSecurityAlert.objects.filter(pk=fresh_alert.pk).exists()
    # Gli expired sono spariti:
    assert not StaffAccessEvent.objects.filter(pk=expired_ev.pk).exists()
    assert not StaffSecurityAlert.objects.filter(pk=expired_alert.pk).exists()


# ---------------------------------------------------------------------------
# Task F.4 — cleanup non tocca altri modelli audit
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_ACCESS_EVENT_RETENTION_DAYS=1,
    STAFF_SECURITY_ALERT_RETENTION_DAYS=1,
)
@pytest.mark.django_db
def test_cleanup_does_not_touch_unrelated_audit_models():
    from django.contrib.auth import get_user_model

    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        DatasetStatus,
    )
    from apps.compliance.enums import PrivacyEventType
    from apps.compliance.models import (
        ConsentPurpose,
        ConsentRecord,
        PrivacyAuditEvent,
    )
    from apps.compliance.retention import cleanup_staff_audit_events
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalReview, LegalSource

    now = timezone.now()

    # Crea un PrivacyAuditEvent vecchissimo (nessuna retention deve toccarlo).
    pae = PrivacyAuditEvent.objects.create(
        event_type=PrivacyEventType.DATA_ACCESSED,
        target_model="cases.Simulation",
        target_object_id="42",
        ip_address="203.0.113.42",
        user_agent="Mozilla/5.0",
        path="/wizard/",
        metadata={},
    )
    # Forziamo created_at vecchio.
    PrivacyAuditEvent.objects.filter(pk=pae.pk).update(created_at=now - timedelta(days=1000))

    # ConsentRecord vecchio.
    purpose = ConsentPurpose.objects.create(
        code="test_purpose", name="Test", required_for_simulation=False
    )
    consent = ConsentRecord.objects.create(
        purpose=purpose, accepted=True, accepted_at=now - timedelta(days=1000)
    )

    # LegalReview vecchio.
    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-test-source",
        title="test",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.NEEDS_REVIEW,
    )
    User = get_user_model()
    reviewer = User.objects.create_user(
        username="ret-reviewer",
        email="ret@example.test",
        password="testpass123!",
    )
    review = LegalReview.objects.create(
        source=src,
        reviewer=reviewer,
        decision=LegalReview.Decision.REQUEST_CHANGES,
        comment="audit retention test",
    )

    # Anche un dataset/formula vecchio: la cleanup NON li deve toccare.
    ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type="road_accident_bodily_injury",
        name="test ds",
        version_label="TEST",
        status=DatasetStatus.DRAFT,
        valid_from=None,
    )
    formula = CalculationFormula.objects.create(
        dataset=ds,
        code="test_formula",
        name="test",
        expression_text="x",
        source_reference="x",
        parameters={},
        status=DatasetStatus.DRAFT,
    )

    # Esegui cleanup (commit).
    cleanup_staff_audit_events(dry_run=False, now=now)

    # Tutti gli altri modelli sono invariati.
    assert PrivacyAuditEvent.objects.filter(pk=pae.pk).exists()
    assert ConsentRecord.objects.filter(pk=consent.pk).exists()
    assert LegalReview.objects.filter(pk=review.pk).exists()
    assert CompensationDataset.objects.filter(pk=ds.pk).exists()
    assert CalculationFormula.objects.filter(pk=formula.pk).exists()
    assert LegalSource.objects.filter(pk=src.pk).exists()


# ---------------------------------------------------------------------------
# Task F.5 — management command dry-run output
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_ACCESS_EVENT_RETENTION_DAYS=90,
    STAFF_SECURITY_ALERT_RETENTION_DAYS=180,
)
@pytest.mark.django_db
def test_management_command_dry_run_output():
    from apps.compliance.models import StaffAccessEvent

    now = timezone.now()
    _make_access_event(created_at=now - timedelta(days=200))
    _make_access_event(created_at=now - timedelta(days=1))

    out = StringIO()
    call_command("cleanup_staff_audit", stdout=out)
    output = out.getvalue()

    assert "DRY-RUN" in output
    assert "StaffAccessEvent expired:     1" in output
    assert "Nessuna cancellazione" in output
    # Niente è stato cancellato.
    assert StaffAccessEvent.objects.count() == 2


# ---------------------------------------------------------------------------
# Task F.6 — management command --commit cancella expired
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_ACCESS_EVENT_RETENTION_DAYS=90,
    STAFF_SECURITY_ALERT_RETENTION_DAYS=180,
)
@pytest.mark.django_db
def test_management_command_commit_deletes_expired():
    from apps.compliance.models import StaffAccessEvent

    now = timezone.now()
    expired = _make_access_event(created_at=now - timedelta(days=200))
    fresh = _make_access_event(created_at=now - timedelta(days=1))

    out = StringIO()
    call_command("cleanup_staff_audit", "--commit", stdout=out)
    output = out.getvalue()

    assert "COMMIT" in output
    assert "StaffAccessEvent deleted:     1" in output
    assert StaffAccessEvent.objects.filter(pk=fresh.pk).exists()
    assert not StaffAccessEvent.objects.filter(pk=expired.pk).exists()


# ---------------------------------------------------------------------------
# Task F.7 — Celery task default dry-run
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_AUDIT_RETENTION_ENABLED=True,
    STAFF_AUDIT_RETENTION_DRY_RUN=True,
    STAFF_ACCESS_EVENT_RETENTION_DAYS=90,
    STAFF_SECURITY_ALERT_RETENTION_DAYS=180,
)
@pytest.mark.django_db
def test_celery_task_default_dry_run():
    from apps.compliance.models import StaffAccessEvent
    from apps.compliance.tasks import cleanup_staff_audit_task

    now = timezone.now()
    _make_access_event(created_at=now - timedelta(days=200))

    result = cleanup_staff_audit_task.apply().result
    assert result.get("dry_run") is True
    assert result.get("access_expired") == 1
    assert result.get("access_deleted") == 0
    assert StaffAccessEvent.objects.count() == 1


@override_settings(STAFF_AUDIT_RETENTION_ENABLED=False)
@pytest.mark.django_db
def test_celery_task_skipped_when_disabled():
    from apps.compliance.tasks import cleanup_staff_audit_task

    result = cleanup_staff_audit_task.apply().result
    assert result == {"skipped": "disabled"}


# ---------------------------------------------------------------------------
# Task F.8 — settings defaults sicuri
# ---------------------------------------------------------------------------


def test_settings_defaults_are_safe():
    assert getattr(settings, "STAFF_AUDIT_RETENTION_DRY_RUN", None) is True
    assert getattr(settings, "STAFF_AUDIT_RETENTION_ENABLED", None) is True
    assert getattr(settings, "STAFF_ACCESS_EVENT_RETENTION_DAYS", None) == 90
    assert getattr(settings, "STAFF_SECURITY_ALERT_RETENTION_DAYS", None) == 180


# ---------------------------------------------------------------------------
# Task F.9 — Italia smoke contract invariato
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_stack(db):
    """Pipeline minima IT che produce 26268/27353/28439 per (35,10,0)."""
    from datetime import date

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title="D.P.R. 12/2025 (smoke stub)",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )
    base_ds = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base smoke",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=base_ds,
        row_type="tun_biological_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    moral_ds = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral smoke",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    for kind, amount in (("min", "26268"), ("mid", "27353"), ("max", "28439")):
        CompensationTableRow.objects.create(
            dataset=moral_ds,
            row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=35,
            age_max=35,
            disability_min=10,
            disability_max=10,
            point_value=Decimal(amount),
        )
    CalculationFormula.objects.create(
        dataset=base_ds,
        code="italy_art_138_tun_2025_base",
        name="Smoke range formula",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct",
            "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            "min_row_type": "tun_biological_moral_min_total_amount",
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        },
        status=DatasetStatus.APPROVED,
    )
    return {"country": italy}


@pytest.mark.django_db
def test_italy_smoke_run_simulation_35_10_0(italy_smoke_stack):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("26268")
    assert sim.estimated_mid == Decimal("27353")
    assert sim.estimated_max == Decimal("28439")
