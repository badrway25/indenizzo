"""
Tests F-local-product-hardening-pass9-staff-audit-brute-force-detector.

Coprono:
- 4 failed login sotto threshold non crea alert;
- 5 failed login entro window crea 1 StaffSecurityAlert;
- tentativi successivi dentro cooldown non creano duplicati;
- tentativi oltre cooldown creano nuovo alert;
- detector usa username_hash OR ip_address_masked;
- STAFF_LOGIN_ALERTS_ENABLED=False disattiva detector;
- email alert disabled → alert creato, nessuna email;
- email alert enabled → alert creato + 1 email locmem;
- email body non contiene password, IP raw, user agent raw;
- StaffSecurityAlert admin read-only;
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

import pytest
from django.core import mail
from django.test import RequestFactory, override_settings
from django.utils import timezone

LOCMEM_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def _clear_outbox():
    mail.outbox = []
    yield
    mail.outbox = []


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_failed_event(
    username_hash: str = "uhash-1",
    ip_address_masked: str = "203.0.113.x",
    user_agent_hash: str = "uahash-1",
    path: str = "/admin/login/",
):
    """Crea un StaffAccessEvent(login_failed) senza passare dai signals.

    Permette di costruire scenari controllati sul detector, evitando
    dipendenza dal Django test client (più lento e ricorsivo).
    """
    from apps.compliance.models import StaffAccessEvent

    return StaffAccessEvent.objects.create(
        event_type="login_failed",
        username_hash=username_hash,
        ip_address_masked=ip_address_masked,
        user_agent_hash=user_agent_hash,
        path=path,
        metadata={},
    )


# ---------------------------------------------------------------------------
# Task H.1 — 4 failed sotto threshold → no alert
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_LOGIN_ALERTS_ENABLED=True,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
    STAFF_LOGIN_ALERT_WINDOW_SECONDS=900,
    STAFF_LOGIN_ALERT_COOLDOWN_SECONDS=3600,
)
@pytest.mark.django_db
def test_under_threshold_does_not_create_alert():
    from apps.compliance.models import StaffSecurityAlert
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    last = None
    for _ in range(4):
        last = _make_failed_event()
    create_staff_security_alert_if_needed(last)
    assert StaffSecurityAlert.objects.count() == 0


# ---------------------------------------------------------------------------
# Task H.2 — 5 failed → 1 alert
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_LOGIN_ALERTS_ENABLED=True,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
    STAFF_LOGIN_ALERT_WINDOW_SECONDS=900,
    STAFF_LOGIN_ALERT_COOLDOWN_SECONDS=3600,
)
@pytest.mark.django_db
def test_threshold_reached_creates_one_alert():
    from apps.compliance.models import StaffSecurityAlert
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    last = None
    for _ in range(5):
        last = _make_failed_event()
    alert = create_staff_security_alert_if_needed(last)
    assert alert is not None
    assert StaffSecurityAlert.objects.count() == 1
    assert alert.alert_type == "admin_login_bruteforce"
    assert alert.severity == "medium"
    assert alert.event_count >= 5
    assert alert.username_hash == "uhash-1"
    assert alert.ip_address_masked == "203.0.113.x"
    assert alert.cooldown_until is not None


# ---------------------------------------------------------------------------
# Task H.3 — cooldown blocca duplicati
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_LOGIN_ALERTS_ENABLED=True,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
    STAFF_LOGIN_ALERT_WINDOW_SECONDS=900,
    STAFF_LOGIN_ALERT_COOLDOWN_SECONDS=3600,
)
@pytest.mark.django_db
def test_cooldown_suppresses_duplicate_alerts():
    from apps.compliance.models import StaffSecurityAlert
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    for _ in range(5):
        last = _make_failed_event()
    create_staff_security_alert_if_needed(last)
    assert StaffSecurityAlert.objects.count() == 1
    # Altri 5 tentativi entro cooldown: nessun nuovo alert.
    for _ in range(5):
        last2 = _make_failed_event()
    create_staff_security_alert_if_needed(last2)
    assert StaffSecurityAlert.objects.count() == 1


# ---------------------------------------------------------------------------
# Task H.4 — post-cooldown crea nuovo alert
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_LOGIN_ALERTS_ENABLED=True,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
    STAFF_LOGIN_ALERT_WINDOW_SECONDS=900,
    STAFF_LOGIN_ALERT_COOLDOWN_SECONDS=3600,
)
@pytest.mark.django_db
def test_post_cooldown_creates_new_alert():
    from apps.compliance.models import StaffSecurityAlert
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    for _ in range(5):
        last = _make_failed_event()
    create_staff_security_alert_if_needed(last)
    assert StaffSecurityAlert.objects.count() == 1

    # Forziamo cooldown scaduto (manipoliamo il record esistente).
    StaffSecurityAlert.objects.update(cooldown_until=timezone.now() - timedelta(minutes=1))

    for _ in range(5):
        last2 = _make_failed_event()
    create_staff_security_alert_if_needed(last2)
    assert StaffSecurityAlert.objects.count() == 2


# ---------------------------------------------------------------------------
# Task H.5 — detector usa username_hash OR ip_address_masked
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_LOGIN_ALERTS_ENABLED=True,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
    STAFF_LOGIN_ALERT_WINDOW_SECONDS=900,
    STAFF_LOGIN_ALERT_COOLDOWN_SECONDS=3600,
)
@pytest.mark.django_db
def test_detector_matches_by_ip_even_with_different_usernames():
    """Stesso IP, username diversi → conta come stesso aggregato."""
    from apps.compliance.models import StaffSecurityAlert
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    for i in range(5):
        last = _make_failed_event(username_hash=f"uhash-{i}", ip_address_masked="10.0.0.x")
    create_staff_security_alert_if_needed(last)
    assert StaffSecurityAlert.objects.count() == 1
    alert = StaffSecurityAlert.objects.first()
    # L'alert ha l'username dell'ultimo evento (uhash-4) ma ha contato
    # tutti i 5 perché lo stesso IP li accomuna.
    assert alert.event_count >= 5
    assert alert.ip_address_masked == "10.0.0.x"


# ---------------------------------------------------------------------------
# Task H.6 — STAFF_LOGIN_ALERTS_ENABLED=False disattiva detector
# ---------------------------------------------------------------------------


@override_settings(
    STAFF_LOGIN_ALERTS_ENABLED=False,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
)
@pytest.mark.django_db
def test_detector_disabled_does_nothing():
    from apps.compliance.models import StaffSecurityAlert
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    for _ in range(10):
        last = _make_failed_event()
    create_staff_security_alert_if_needed(last)
    assert StaffSecurityAlert.objects.count() == 0


# ---------------------------------------------------------------------------
# Task H.7 — email disabled: alert creato, no email
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    STAFF_LOGIN_ALERTS_ENABLED=True,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
    STAFF_LOGIN_ALERT_WINDOW_SECONDS=900,
    STAFF_LOGIN_ALERT_COOLDOWN_SECONDS=3600,
    STAFF_LOGIN_ALERT_EMAIL_ENABLED=False,
    STAFF_LOGIN_ALERT_TO_EMAILS=["studio@example.test"],
)
@pytest.mark.django_db
def test_email_disabled_alert_created_no_email():
    from apps.compliance.models import StaffSecurityAlert
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    for _ in range(5):
        last = _make_failed_event()
    create_staff_security_alert_if_needed(last)
    assert StaffSecurityAlert.objects.count() == 1
    assert len(mail.outbox) == 0


# ---------------------------------------------------------------------------
# Task H.8 — email enabled: alert creato + 1 email
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    STAFF_LOGIN_ALERTS_ENABLED=True,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
    STAFF_LOGIN_ALERT_WINDOW_SECONDS=900,
    STAFF_LOGIN_ALERT_COOLDOWN_SECONDS=3600,
    STAFF_LOGIN_ALERT_EMAIL_ENABLED=True,
    STAFF_LOGIN_ALERT_TO_EMAILS=["studio@example.test", "ops@example.test"],
    EMAIL_SUBJECT_PREFIX="[Badrane LegalTech] ",
)
@pytest.mark.django_db
def test_email_enabled_alert_creates_one_email():
    from apps.compliance.models import StaffSecurityAlert
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    for _ in range(5):
        last = _make_failed_event()
    create_staff_security_alert_if_needed(last)
    assert StaffSecurityAlert.objects.count() == 1
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "[Badrane LegalTech] Admin login alert"
    assert set(msg.to) == {"studio@example.test", "ops@example.test"}


# ---------------------------------------------------------------------------
# Task H.9 — email body non contiene password / IP raw / UA raw
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    STAFF_LOGIN_ALERTS_ENABLED=True,
    STAFF_LOGIN_ALERT_THRESHOLD=5,
    STAFF_LOGIN_ALERT_WINDOW_SECONDS=900,
    STAFF_LOGIN_ALERT_COOLDOWN_SECONDS=3600,
    STAFF_LOGIN_ALERT_EMAIL_ENABLED=True,
    STAFF_LOGIN_ALERT_TO_EMAILS=["studio@example.test"],
)
@pytest.mark.django_db
def test_email_body_does_not_leak_pii():
    from apps.compliance.staff_security import create_staff_security_alert_if_needed

    for _ in range(5):
        last = _make_failed_event(
            username_hash="uhash-secret",
            ip_address_masked="203.0.113.x",
            user_agent_hash="uahash-secret",
            path="/admin/login/",
        )
    create_staff_security_alert_if_needed(last)
    assert len(mail.outbox) == 1
    body = mail.outbox[0].body
    # Hash sì (sono già redatti).
    assert "uhash-secret" in body
    assert "203.0.113.x" in body
    # Cose che NON devono mai apparire (anche se simulate):
    forbidden = (
        "password",  # nessuna parola "password" nel body — solo
        "201.45.67.89",  # IP raw fittizio
        "Mozilla/5.0",
        "this-is-not-the-password",
    )
    for s in forbidden:
        assert s not in body, f"forbidden token in alert email body: {s!r}"


# ---------------------------------------------------------------------------
# Task H.10 — StaffSecurityAlert admin read-only
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_staff_security_alert_admin_is_read_only():
    from django.contrib import admin as django_admin

    from apps.compliance.models import StaffSecurityAlert

    admin_cls = django_admin.site._registry.get(StaffSecurityAlert)
    assert admin_cls is not None, "StaffSecurityAlert not registered in admin"
    request = RequestFactory().get("/admin/")
    request.user = type("U", (), {"is_staff": True, "is_superuser": True, "is_active": True})()
    assert admin_cls.has_add_permission(request) is False
    assert admin_cls.has_change_permission(request) is False
    assert admin_cls.has_delete_permission(request) is False


# ---------------------------------------------------------------------------
# Task H.11 — Italia smoke contract invariato
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
