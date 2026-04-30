"""
Tests F-local-product-hardening-pass8-audit-log-staff-access.

Coprono:
- mask_ip IPv4 / IPv6 / vuoto;
- hash_text stabile e non reversibile;
- segnale `user_logged_in` su staff → StaffAccessEvent;
- segnale `user_logged_out` su staff → StaffAccessEvent;
- segnale `user_login_failed` su /admin/login/ → StaffAccessEvent
  (senza password);
- login non-staff su path non-admin → nessun evento;
- admin StaffAccessEvent è read-only (no add/change/delete);
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory

User = get_user_model()


# ---------------------------------------------------------------------------
# Task F.1 + F.2 — mask_ip IPv4 / IPv6
# ---------------------------------------------------------------------------


def test_mask_ip_ipv4_masks_last_octet():
    from apps.compliance.privacy_helpers import mask_ip

    assert mask_ip("203.0.113.42") == "203.0.113.x"
    assert mask_ip("10.0.0.1") == "10.0.0.x"
    assert mask_ip("127.0.0.1") == "127.0.0.x"


def test_mask_ip_ipv6_masks_last_group():
    from apps.compliance.privacy_helpers import mask_ip

    assert mask_ip("2001:db8::1") == "2001:db8::x"
    # Zone id (interfaccia) tagliato prima del mask.
    assert mask_ip("fe80::1%eth0") == "fe80::x"


def test_mask_ip_handles_empty_and_none():
    from apps.compliance.privacy_helpers import mask_ip

    assert mask_ip("") == ""
    assert mask_ip(None) == ""


# ---------------------------------------------------------------------------
# Task F.3 — hash_text stabile e non reversibile
# ---------------------------------------------------------------------------


def test_hash_text_is_stable_and_non_reversible():
    """Stabile: stesso input → stesso hash. Non reversibile: il
    testo originale non è ricostruibile dal solo hash."""
    from apps.compliance.privacy_helpers import hash_text

    h1 = hash_text("alice")
    h2 = hash_text("alice")
    h3 = hash_text("bob")
    assert h1 == h2  # stabile
    assert h1 != h3  # collisione improbabile
    assert "alice" not in h1  # non leggibile
    # SHA-256 hex troncato a 24 char.
    assert len(h1) == 24
    assert all(c in "0123456789abcdef" for c in h1)
    # Empty/None → stringa vuota (no hash di niente).
    assert hash_text("") == ""
    assert hash_text(None) == ""


# ---------------------------------------------------------------------------
# Task F.4 — login_success crea StaffAccessEvent
# ---------------------------------------------------------------------------


@pytest.fixture
def staff_user(db):
    return User.objects.create_user(
        username="staffer",
        email="staffer@example.test",
        password="testpass123!",
        is_staff=True,
        is_superuser=False,
    )


@pytest.mark.django_db
def test_admin_login_success_creates_staff_access_event(staff_user):
    from apps.compliance.models import StaffAccessEvent

    client = Client()
    pre_count = StaffAccessEvent.objects.count()
    ok = client.login(username="staffer", password="testpass123!")
    assert ok is True
    # Login programmatico: il segnale `user_logged_in` si attiva con
    # request=None — ma user.is_staff=True, quindi l'evento viene
    # registrato comunque.
    events = StaffAccessEvent.objects.filter(event_type="login_success")
    assert (
        events.count()
        == pre_count
        + 1
        - StaffAccessEvent.objects.filter(event_type="login_success")
        .exclude(user=staff_user)
        .count()
    )
    ev = events.filter(user=staff_user).first()
    assert ev is not None
    assert ev.user == staff_user
    assert ev.username_hash != ""  # hash non vuoto


# ---------------------------------------------------------------------------
# Task F.5 — logout crea StaffAccessEvent
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_logout_creates_staff_access_event(staff_user):
    from apps.compliance.models import StaffAccessEvent

    client = Client()
    client.force_login(staff_user)
    pre_logout = StaffAccessEvent.objects.filter(event_type="logout").count()
    client.logout()
    post_logout = StaffAccessEvent.objects.filter(event_type="logout").count()
    assert post_logout == pre_logout + 1


# ---------------------------------------------------------------------------
# Task F.6 — login_failed su /admin/login/ crea evento, no password
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_admin_login_failed_creates_event_without_password():
    from apps.compliance.models import StaffAccessEvent

    client = Client()
    pre_count = StaffAccessEvent.objects.filter(event_type="login_failed").count()
    # POST credenziali invalide a /admin/login/.
    resp = client.post(
        "/admin/login/",
        data={
            "username": "ghost-user",
            "password": "this-is-not-the-password",
            "next": "/admin/",
        },
    )
    # Login fallito: 200 con form errato (no redirect). Importa la
    # creazione dell'evento.
    assert resp.status_code == 200
    post_count = StaffAccessEvent.objects.filter(event_type="login_failed").count()
    assert post_count == pre_count + 1
    ev = StaffAccessEvent.objects.filter(event_type="login_failed").latest("created_at")
    # User None (login fallito).
    assert ev.user is None
    # Username hash presente, NON in chiaro.
    assert ev.username_hash != ""
    assert "ghost-user" not in ev.username_hash
    # Password mai persistita: niente campo password sul model, ma
    # difensiva: nessun campo testuale dovrebbe contenerla.
    for field_value in (
        ev.username_hash,
        ev.ip_address_masked,
        ev.user_agent_hash,
        ev.path,
        str(ev.metadata),
    ):
        assert "this-is-not-the-password" not in field_value
    # Path di tentativo (può essere /admin/login/ o /admin/login/?next=/admin/)
    assert ev.path.startswith("/admin/login/")


# ---------------------------------------------------------------------------
# Task F.7 — login non-staff su path non-admin → no evento
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_non_staff_login_off_admin_path_does_not_create_event():
    """user_login_failed inviato senza request /admin/ → NO evento."""
    from django.contrib.auth.signals import user_login_failed

    from apps.compliance.models import StaffAccessEvent

    pre_count = StaffAccessEvent.objects.count()
    factory = RequestFactory()
    fake_request = factory.post("/contact/", data={"username": "x", "password": "y"})
    user_login_failed.send(
        sender=None,
        credentials={"username": "x", "password": "y"},
        request=fake_request,
    )
    assert StaffAccessEvent.objects.count() == pre_count


# ---------------------------------------------------------------------------
# Task F.8 — admin model read-only
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_staff_access_event_admin_is_read_only():
    from django.contrib import admin as django_admin

    from apps.compliance.models import StaffAccessEvent

    admin_cls = django_admin.site._registry.get(StaffAccessEvent)
    assert admin_cls is not None, "StaffAccessEvent not registered in admin"
    # Tutte le permission di mutazione devono essere False.
    request = RequestFactory().get("/admin/")
    request.user = type("U", (), {"is_staff": True, "is_superuser": True, "is_active": True})()
    assert admin_cls.has_add_permission(request) is False
    assert admin_cls.has_change_permission(request) is False
    assert admin_cls.has_delete_permission(request) is False


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
