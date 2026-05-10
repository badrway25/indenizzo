"""
Tests F-local-product-hardening-pass2-email-lead.

Coprono:
- send_lead_notification con flag disabled / recipient vuoto / abilitato;
- subject + body privacy-minimization;
- integrazione /contact/ POST → email + Lead;
- failure-soft: send_mail eccezione non blocca creazione Lead né thank-you;
- smoke Italia 35/10/0 invariato.

Tutti i test usano `locmem.EmailBackend` via `override_settings` per non
inviare email reali. La inbox (`django.core.mail.outbox`) è azzerata
all'inizio di ogni test.
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse

LOCMEM_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def _clear_cache_and_outbox():
    cache.clear()
    mail.outbox = []
    yield
    cache.clear()
    mail.outbox = []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_country(db):
    from apps.jurisdictions.models import Country

    return Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")


@pytest.fixture
def lead_factory(db, italy_country):
    """Costruisce un Lead minimale persistito su DB."""
    from apps.crm.models import Lead

    def _make(**overrides):
        defaults = {
            "first_name": "Maria",
            "last_name": "Rossi",
            "email": "maria.rossi@example.test",
            "phone_number": "+39 333 0000000",
            "preferred_language": "it",
            "country": italy_country,
            "case_type": "road_accident_bodily_injury",
            "message": "placeholder message of sufficient length for the model",
            # Campi che NON devono finire nel body email:
            "ip_address": "203.0.113.42",
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
            "session_key": "abcdef0123456789abcdef0123456789",
            "internal_notes": "TOP SECRET STAFF NOTE — do not leak",
        }
        defaults.update(overrides)
        return Lead.objects.create(**defaults)

    return _make


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
    for kind, amount in (
        ("min", "26268"),
        ("mid", "27353"),
        ("max", "28439"),
    ):
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


CONTACT_PAYLOAD = {
    "first_name": "Maria",
    "last_name": "Rossi",
    "email": "maria.rossi@example.test",
    "phone_number": "",
    "preferred_language": "it",
    "country": "",
    "case_type": "",
    "message": "Ho avuto un incidente stradale a Milano e vorrei capire i passi.",
    "privacy_accepted": "on",
    "special_categories_accepted": "on",
    "simulation_public_id": "",
    "website": "",
}


# ---------------------------------------------------------------------------
# Task E.1 — disabled returns False, no email
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=False,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
)
@pytest.mark.django_db
def test_notification_disabled_returns_false_and_sends_nothing(lead_factory):
    from apps.crm.email_notifications import send_lead_notification

    lead = lead_factory()
    result = send_lead_notification(lead)
    assert result is False
    assert len(mail.outbox) == 0


# ---------------------------------------------------------------------------
# Task E.2 — enabled but empty recipients
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=[],
)
@pytest.mark.django_db
def test_notification_empty_recipients_returns_false(lead_factory):
    from apps.crm.email_notifications import send_lead_notification

    lead = lead_factory()
    result = send_lead_notification(lead)
    assert result is False
    assert len(mail.outbox) == 0


# ---------------------------------------------------------------------------
# Task E.3, E.4, E.5, E.6 — enabled + recipient: subject, body content,
# privacy minimization
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test", "ops@example.test"],
    EMAIL_SUBJECT_PREFIX="[Badrane LegalTech] ",
    DEFAULT_FROM_EMAIL="no-reply@badrane.local",
)
@pytest.mark.django_db
def test_notification_enabled_sends_one_email_with_correct_subject(lead_factory):
    from apps.crm.email_notifications import send_lead_notification

    lead = lead_factory()
    result = send_lead_notification(lead)
    assert result is True
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.subject == "[Badrane LegalTech] New legal review request"
    assert msg.from_email == "no-reply@badrane.local"
    assert set(msg.to) == {"studio@example.test", "ops@example.test"}


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
)
@pytest.mark.django_db
def test_notification_body_contains_lead_public_id(lead_factory):
    from apps.crm.email_notifications import send_lead_notification

    lead = lead_factory()
    send_lead_notification(lead)
    body = mail.outbox[0].body
    assert str(lead.public_id) in body
    assert "Maria Rossi" in body
    assert "maria.rossi@example.test" in body


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
)
@pytest.mark.django_db
def test_notification_body_includes_simulation_public_id_when_present(
    db, italy_country, lead_factory
):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.models import Simulation
    from apps.crm.email_notifications import send_lead_notification
    from apps.jurisdictions.models import Currency, Jurisdiction, Language

    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy_country,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    sim = Simulation.objects.create(
        jurisdiction=juris,
        country=italy_country,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
        input_data={},
        output_data={},
    )
    lead = lead_factory(simulation=sim)
    send_lead_notification(lead)
    body = mail.outbox[0].body
    assert str(sim.public_id) in body


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
)
@pytest.mark.django_db
def test_notification_body_omits_pii_metadata_fields(lead_factory):
    """Privacy minimization: ip/UA/session_key/internal_notes NON nel body."""
    from apps.crm.email_notifications import send_lead_notification

    lead = lead_factory()
    send_lead_notification(lead)
    body = mail.outbox[0].body
    assert "203.0.113.42" not in body  # ip_address
    assert "Mozilla/5.0" not in body  # user_agent
    assert "abcdef0123456789" not in body  # session_key
    assert "TOP SECRET STAFF NOTE" not in body  # internal_notes


# ---------------------------------------------------------------------------
# Task E.7 — /contact/ POST sends email when enabled
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
)
@pytest.mark.django_db
def test_contact_post_creates_lead_and_sends_email():
    from apps.crm.models import Lead

    client = Client()
    resp = client.post(reverse("crm:contact"), data=CONTACT_PAYLOAD)
    assert resp.status_code == 302
    assert Lead.objects.count() == 1
    lead = Lead.objects.first()
    assert len(mail.outbox) == 1
    msg = mail.outbox[0]
    assert msg.to == ["studio@example.test"]
    assert str(lead.public_id) in msg.body


# ---------------------------------------------------------------------------
# Task E.8 — send_mail exception → Lead still created, redirect thank-you
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
)
@pytest.mark.django_db
def test_contact_post_email_failure_does_not_break_lead_creation(monkeypatch):
    """Se send_mail solleva eccezione, /contact/ deve comunque creare il
    Lead e redirigere all thank-you. Il Lead non viene rollback-ato."""
    from apps.crm.models import Lead

    def _raise(*args, **kwargs):
        raise RuntimeError("simulated SMTP outage")

    # Pacha il send_mail usato dal modulo email_notifications.
    monkeypatch.setattr("apps.crm.email_notifications.send_mail", _raise)

    client = Client()
    resp = client.post(reverse("crm:contact"), data=CONTACT_PAYLOAD)
    assert resp.status_code == 302
    assert resp.url == reverse("crm:contact_thank_you")
    assert Lead.objects.count() == 1
    # Outbox vuoto perché send_mail ha sollevato.
    assert len(mail.outbox) == 0


# ---------------------------------------------------------------------------
# Task E.9 — IT smoke contract invariato (regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_smoke_run_simulation_35_10_0(italy_smoke_stack):
    """run_simulation IT-NATIONAL/road_accident 35/10/0 → 26268/27353/28439."""
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
