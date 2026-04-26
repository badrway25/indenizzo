"""
Tests F5 — apps.cases.

Verifichiamo il "ponte" architetturale:
- `run_simulation` crea una `Simulation` con UUID + scrive output engine;
- comportamento difensivo: calculator mancante non fa crash;
- senza fonti `approved` lo status è `unavailable_requires_legal_validation`;
- con fonti approved (placeholder F4) lo status resta unavailable ma le
  fonti vengono snapshot-ate;
- consent_record viene linkato se passato;
- request metadata (IP, UA, path, session_key) viene salvata;
- anonimizzazione cancella i dati personali e crea evento + privacy log;
- get_simulation_by_public_id funziona;
- output_data è JSON serializzabile.
"""

from __future__ import annotations

import json
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory

from apps.calculators.enums import CalculationStatus, CaseType, ConfidenceLevel
from apps.cases.models import Simulation, SimulationEvent
from apps.cases.services import (
    anonymize_simulation,
    get_simulation_by_public_id,
    run_simulation,
)
from apps.compliance.enums import PrivacyEventType
from apps.compliance.models import (
    ConsentPurpose,
    ConsentRecord,
    PrivacyAuditEvent,
)
from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource

User = get_user_model()


@pytest.fixture
def italy_setup(db):
    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    jurisdiction = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    return {
        "country": italy,
        "currency": eur,
        "language": italian,
        "jurisdiction": jurisdiction,
    }


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


# ---------------------------------------------------------------------------
# run_simulation — comportamento base
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_run_simulation_creates_simulation_with_uuid(italy_setup):
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"age": 35},
    )
    assert isinstance(sim, Simulation)
    assert isinstance(sim.public_id, uuid.UUID)
    assert sim.case_type == CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
    assert sim.jurisdiction == italy_setup["jurisdiction"]
    assert sim.country == italy_setup["country"]


@pytest.mark.django_db
def test_simulation_public_ids_are_unique(italy_setup):
    sim1 = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    sim2 = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    assert sim1.public_id != sim2.public_id


@pytest.mark.django_db
def test_run_simulation_without_approved_sources_is_unavailable(italy_setup):
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None
    assert sim.confidence == ConfidenceLevel.LOW.value
    assert sim.currency == "EUR"


@pytest.mark.django_db
def test_run_simulation_with_approved_source_snapshots_but_no_amounts(italy_setup):
    """Il placeholder F4 non inventa importi anche con fonti approved."""
    LegalSource.objects.create(
        title="Codice Assicurazioni Private (placeholder)",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert len(sim.sources_snapshot) == 1
    assert sim.sources_snapshot[0]["title"].startswith("Codice")


@pytest.mark.django_db
def test_run_simulation_missing_calculator_does_not_crash(italy_setup):
    """case_type non registrato → nessuna eccezione, status unavailable."""
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.MEDICAL_MALPRACTICE.value,
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.case_type == CaseType.MEDICAL_MALPRACTICE.value
    assert any("No calculator" in w for w in sim.output_data["warnings"])


@pytest.mark.django_db
def test_run_simulation_unknown_jurisdiction_does_not_crash():
    """Anche con jurisdiction non in DB la simulazione viene salvata."""
    sim = run_simulation(
        jurisdiction_code="ZZ-NOPE",
        case_type=CaseType.GENERIC_LEGAL_ASSESSMENT.value,
    )
    assert sim.jurisdiction is None
    assert sim.country is None
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.currency == "EUR"


@pytest.mark.django_db
def test_run_simulation_output_data_is_json_serializable(italy_setup):
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    # output_data è già un dict, ma dev'essere json.dumps-able.
    payload = json.dumps(sim.output_data)
    assert "legal_disclaimer" in payload
    assert "estimated_min" in payload


# ---------------------------------------------------------------------------
# request metadata + consent + audit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_run_simulation_persists_request_metadata(italy_setup, request_factory):
    request = request_factory.post(
        "/wizard/compute",
        HTTP_USER_AGENT="pytest-agent/1.0",
        HTTP_X_FORWARDED_FOR="203.0.113.42, 10.0.0.1",
    )
    request.LANGUAGE_CODE = "it"
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        request=request,
    )
    assert sim.ip_address == "203.0.113.42"
    assert sim.user_agent == "pytest-agent/1.0"
    assert sim.source_path == "/wizard/compute"


@pytest.mark.django_db
def test_run_simulation_links_authenticated_user(italy_setup, request_factory):
    user = User.objects.create_user(username="alice", password="pw")
    request = request_factory.get("/wizard/compute")
    request.user = user
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.INHERITANCE_BASIC.value,
        request=request,
    )
    assert sim.user == user


@pytest.mark.django_db
def test_run_simulation_links_consent_record(italy_setup):
    purpose = ConsentPurpose.objects.create(
        code="simulation_processing",
        name="Trattamento dati per simulazione",
        required_for_simulation=True,
    )
    user = User.objects.create_user(username="bob", password="pw")
    consent = ConsentRecord.objects.create(
        user=user,
        purpose=purpose,
        accepted=True,
        accepted_at=__import__("django").utils.timezone.now(),
    )
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        user=user,
        consent_record=consent,
    )
    assert sim.consent_record == consent


@pytest.mark.django_db
def test_run_simulation_creates_simulation_event(italy_setup):
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    events = SimulationEvent.objects.filter(simulation=sim)
    assert events.count() == 1
    event = events.first()
    assert event.event_type == SimulationEvent.EventType.COMPUTED
    assert event.metadata["calculator_present"] is True


@pytest.mark.django_db
def test_run_simulation_creates_privacy_audit_event(italy_setup):
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    events = PrivacyAuditEvent.objects.filter(
        target_model="cases.Simulation",
        target_object_id=str(sim.pk),
    )
    assert events.count() == 1
    assert events.first().event_type == PrivacyEventType.DATA_ACCESSED


# ---------------------------------------------------------------------------
# locale
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_run_simulation_locale_disclaimer_coherent(italy_setup):
    sim_fr = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        locale="fr",
    )
    assert sim_fr.locale == "fr"
    disclaimer = sim_fr.output_data["legal_disclaimer"]
    assert "simulation" in disclaimer.lower()
    assert "indicative" in disclaimer.lower()


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_simulation_by_public_id(italy_setup):
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    fetched = get_simulation_by_public_id(str(sim.public_id))
    assert fetched == sim


@pytest.mark.django_db
def test_get_simulation_by_public_id_returns_none_when_missing():
    assert get_simulation_by_public_id(str(uuid.uuid4())) is None


# ---------------------------------------------------------------------------
# anonymize_simulation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_anonymize_simulation_clears_personal_data(italy_setup, request_factory):
    user = User.objects.create_user(username="charlie", password="pw")
    request = request_factory.post(
        "/wizard/compute",
        HTTP_USER_AGENT="agent/1",
        REMOTE_ADDR="198.51.100.7",
    )
    request.user = user
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"age": 35, "city": "Milano"},
        request=request,
    )
    assert sim.ip_address == "198.51.100.7"
    assert sim.user == user
    assert sim.input_data == {"age": 35, "city": "Milano"}

    anonymize_simulation(sim)
    sim.refresh_from_db()

    assert sim.anonymized is True
    assert sim.anonymized_at is not None
    assert sim.user is None
    assert sim.ip_address is None
    assert sim.user_agent == ""
    assert sim.source_path == ""
    assert sim.session_key == ""
    assert sim.input_data == {"_anonymized": True}
    # output_data e sources_snapshot conservati per audit.
    assert sim.output_data
    assert "legal_disclaimer" in sim.output_data


@pytest.mark.django_db
def test_anonymize_simulation_creates_event_and_privacy_log(italy_setup):
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    )
    anonymize_simulation(sim)

    events = SimulationEvent.objects.filter(simulation=sim).order_by("created_at", "pk")
    assert events.count() == 2
    assert events.last().event_type == SimulationEvent.EventType.ANONYMIZED

    privacy_events = PrivacyAuditEvent.objects.filter(
        target_model="cases.Simulation",
        target_object_id=str(sim.pk),
        event_type=PrivacyEventType.DATA_DELETION_COMPLETED,
    )
    assert privacy_events.count() == 1
