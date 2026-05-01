"""
Tests F6 — apps.crm.

Coprono:
- modello Lead/LeadEvent;
- form ContactForm: validazione campi, consenso obbligatorio, message minimo;
- view /contact/ GET e POST con CSRF;
- creazione Lead via service: ConsentRecord + LeadEvent + PrivacyAuditEvent;
- honeypot scarta il submit ma redirige a thank-you;
- collegamento Simulation via public_id;
- thank-you 200;
- CTA partial punta a /contact/;
- form NON crea Simulation;
- message non finisce nei log.
"""

from __future__ import annotations

import logging
import uuid

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators.enums import CaseType
from apps.cases.models import Simulation
from apps.compliance.enums import PrivacyEventType
from apps.compliance.models import ConsentPurpose, ConsentRecord, PrivacyAuditEvent
from apps.crm.forms import MESSAGE_MIN_LENGTH, ContactForm
from apps.crm.models import Lead, LeadEvent, LeadStatus
from apps.crm.services import create_lead_from_form, get_or_create_lead_contact_purpose
from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language


@pytest.fixture
def italy(db) -> Country:
    return Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")


@pytest.fixture
def italy_jurisdiction(db, italy: Country) -> Jurisdiction:
    eur = Currency.objects.create(code="EUR", name="Euro")
    italian = Language.objects.create(code="it", name="Italiano")
    return Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )


VALID_PAYLOAD = {
    "first_name": "Maria",
    "last_name": "Rossi",
    "email": "maria.rossi@example.test",
    "phone_number": "",
    "preferred_language": "it",
    "country": "",
    "case_type": "",
    "message": "Ho avuto un incidente stradale a Milano e vorrei capire i passi.",
    "privacy_accepted": "on",
    "simulation_public_id": "",
    "website": "",
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_lead_public_id_is_uuid(italy: Country):
    lead = Lead.objects.create(
        first_name="A",
        last_name="B",
        email="a@b.test",
        message="placeholder min length 20+ characters here",
        country=italy,
    )
    assert isinstance(lead.public_id, uuid.UUID)
    assert lead.status == LeadStatus.RECEIVED
    assert lead.full_name == "A B"


@pytest.mark.django_db
def test_lead_event_creation():
    lead = Lead.objects.create(
        first_name="A",
        last_name="B",
        email="a@b.test",
        message="placeholder min length 20+ characters here",
    )
    event = LeadEvent.objects.create(
        lead=lead,
        event_type=LeadEvent.EventType.CREATED,
        message="hello",
    )
    assert event.lead == lead
    assert event.event_type == LeadEvent.EventType.CREATED


@pytest.mark.django_db
def test_lead_str_does_not_leak_pii():
    lead = Lead.objects.create(
        first_name="Mario",
        last_name="Rossi",
        email="mario@example.test",
        message="some message of at least twenty characters",
    )
    repr_str = str(lead)
    assert "Mario" not in repr_str
    assert "mario@example.test" not in repr_str


# ---------------------------------------------------------------------------
# Form
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_form_valid_minimal():
    form = ContactForm(data=VALID_PAYLOAD)
    assert form.is_valid(), form.errors
    assert form.is_likely_bot is False


@pytest.mark.django_db
def test_contact_form_rejects_missing_consent():
    payload = {**VALID_PAYLOAD}
    payload.pop("privacy_accepted")
    form = ContactForm(data=payload)
    assert not form.is_valid()
    assert "privacy_accepted" in form.errors


@pytest.mark.django_db
def test_contact_form_rejects_short_message():
    payload = {**VALID_PAYLOAD, "message": "too short"}
    form = ContactForm(data=payload)
    assert not form.is_valid()
    assert "message" in form.errors


@pytest.mark.django_db
def test_contact_form_rejects_invalid_email():
    payload = {**VALID_PAYLOAD, "email": "not-an-email"}
    form = ContactForm(data=payload)
    assert not form.is_valid()
    assert "email" in form.errors


@pytest.mark.django_db
def test_contact_form_honeypot_is_bot():
    payload = {**VALID_PAYLOAD, "website": "http://spam.example/"}
    form = ContactForm(data=payload)
    assert form.is_valid()
    assert form.is_likely_bot is True


def test_message_min_length_constant():
    assert MESSAGE_MIN_LENGTH >= 10  # tutela base contro submit vuoti


# ---------------------------------------------------------------------------
# View /contact/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_get_returns_200():
    response = Client().get(reverse("crm:contact"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'name="email"' in body
    assert 'name="privacy_accepted"' in body


@pytest.mark.django_db
def test_contact_post_valid_creates_lead_and_redirects(italy: Country):
    payload = {
        **VALID_PAYLOAD,
        "country": str(italy.pk),
        "case_type": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    }
    response = Client().post(reverse("crm:contact"), payload)
    assert response.status_code == 302
    assert response.url == reverse("crm:contact_thank_you")
    assert Lead.objects.count() == 1
    lead = Lead.objects.get()
    assert lead.email == "maria.rossi@example.test"
    assert lead.country == italy
    assert lead.case_type == CaseType.ROAD_ACCIDENT_BODILY_INJURY.value


@pytest.mark.django_db
def test_contact_post_creates_consent_record():
    Client().post(reverse("crm:contact"), VALID_PAYLOAD)
    purpose = ConsentPurpose.objects.get(code="lead_contact")
    record = ConsentRecord.objects.filter(purpose=purpose).first()
    assert record is not None
    assert record.accepted is True
    assert Lead.objects.get().consent_record == record


@pytest.mark.django_db
def test_contact_post_creates_privacy_audit_event():
    Client().post(reverse("crm:contact"), VALID_PAYLOAD)
    lead = Lead.objects.get()
    events = PrivacyAuditEvent.objects.filter(
        target_model="crm.Lead",
        target_object_id=str(lead.pk),
        event_type=PrivacyEventType.CONSENT_GIVEN,
    )
    assert events.count() == 1


@pytest.mark.django_db
def test_contact_post_creates_lead_event():
    Client().post(reverse("crm:contact"), VALID_PAYLOAD)
    lead = Lead.objects.get()
    event = LeadEvent.objects.filter(lead=lead, event_type=LeadEvent.EventType.CREATED).first()
    assert event is not None
    assert event.metadata["has_simulation"] is False


@pytest.mark.django_db
def test_contact_post_without_consent_does_not_create_lead():
    payload = {**VALID_PAYLOAD}
    payload.pop("privacy_accepted")
    response = Client().post(reverse("crm:contact"), payload)
    assert response.status_code == 200  # form re-rendered
    assert Lead.objects.count() == 0
    assert ConsentRecord.objects.count() == 0


@pytest.mark.django_db
def test_contact_post_honeypot_drops_lead_but_redirects():
    payload = {**VALID_PAYLOAD, "website": "http://spam/"}
    response = Client().post(reverse("crm:contact"), payload)
    # Redirect alla thank-you per non rivelare la trappola al bot.
    assert response.status_code == 302
    assert response.url == reverse("crm:contact_thank_you")
    assert Lead.objects.count() == 0
    assert ConsentRecord.objects.count() == 0


@pytest.mark.django_db
def test_contact_post_links_simulation(italy_jurisdiction):
    sim = Simulation.objects.create(
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        jurisdiction=italy_jurisdiction,
        country=italy_jurisdiction.country,
    )
    payload = {**VALID_PAYLOAD, "simulation_public_id": str(sim.public_id)}
    Client().post(reverse("crm:contact"), payload)
    lead = Lead.objects.get()
    assert lead.simulation == sim
    event = LeadEvent.objects.get(lead=lead, event_type=LeadEvent.EventType.CREATED)
    assert event.metadata["has_simulation"] is True


@pytest.mark.django_db
def test_contact_post_does_not_create_simulation():
    """REQ-3: il form pubblico non deve mai produrre Simulation."""
    initial = Simulation.objects.count()
    Client().post(reverse("crm:contact"), VALID_PAYLOAD)
    assert Simulation.objects.count() == initial


# ---------------------------------------------------------------------------
# Thank-you page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_thank_you_returns_200():
    response = Client().get(reverse("crm:contact_thank_you"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Accept English source OR Italian translation (default LANGUAGE_CODE=it).
    body_lower = body.lower()
    assert (
        "thank you" in body_lower
        or "received" in body_lower
        or "grazie" in body_lower
        or "ricevuta" in body_lower
    )


@pytest.mark.django_db
def test_cta_partial_points_to_contact_form():
    """REQ-6: il CTA 'Request legal review' nel layout porta a /contact/."""
    response = Client().get(reverse("core:home"))
    body = response.content.decode("utf-8")
    assert reverse("crm:contact") in body


# ---------------------------------------------------------------------------
# Service layer
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_or_create_lead_contact_purpose_is_idempotent():
    p1 = get_or_create_lead_contact_purpose()
    p2 = get_or_create_lead_contact_purpose()
    assert p1 == p2
    assert ConsentPurpose.objects.filter(code="lead_contact").count() == 1


@pytest.mark.django_db
def test_create_lead_from_form_works_without_request():
    form_kwargs = {
        "first_name": "Maria",
        "last_name": "Rossi",
        "email": "m@r.test",
        "phone_number": "",
        "preferred_language": "it",
        "country": None,
        "case_type": "",
        "message": "Vorrei consulenza su una successione internazionale tra Italia e Marocco.",
    }
    lead = create_lead_from_form(form_kwargs=form_kwargs)
    assert lead.pk is not None
    assert lead.consent_record is not None
    assert lead.consent_record.accepted is True


# ---------------------------------------------------------------------------
# Logging — no PII
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_lead_message_does_not_appear_in_logs(caplog):
    secret_message = "TopSecretMedicalDetails-123 minimum twenty chars"
    payload = {**VALID_PAYLOAD, "message": secret_message}
    with caplog.at_level(logging.INFO):
        Client().post(reverse("crm:contact"), payload)
    log_text = "\n".join(record.getMessage() for record in caplog.records)
    assert secret_message not in log_text


# ---------------------------------------------------------------------------
# Seed compliance basics
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_compliance_basics_creates_purposes_and_texts():
    from io import StringIO

    from django.core.management import call_command

    call_command("seed_compliance_basics", "--quiet", stdout=StringIO())
    assert ConsentPurpose.objects.filter(code="lead_contact").exists()
    assert ConsentPurpose.objects.filter(code="simulation_processing").exists()
    # 2 purpose × 4 lingue = 8 text version
    from apps.compliance.models import ConsentTextVersion, DataRetentionPolicy

    assert ConsentTextVersion.objects.count() >= 8
    assert DataRetentionPolicy.objects.count() >= 4


@pytest.mark.django_db
def test_seed_compliance_basics_is_idempotent():
    from io import StringIO

    from django.core.management import call_command

    call_command("seed_compliance_basics", "--quiet", stdout=StringIO())
    counts_after_first = (
        ConsentPurpose.objects.count(),
        __import__(
            "apps.compliance.models", fromlist=["ConsentTextVersion"]
        ).ConsentTextVersion.objects.count(),
    )
    call_command("seed_compliance_basics", "--quiet", stdout=StringIO())
    counts_after_second = (
        ConsentPurpose.objects.count(),
        __import__(
            "apps.compliance.models", fromlist=["ConsentTextVersion"]
        ).ConsentTextVersion.objects.count(),
    )
    assert counts_after_first == counts_after_second
