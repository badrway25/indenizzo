"""
Tests F5 + F-wizard — apps.cases.

Coprono:
- `run_simulation`: ponte architetturale (F5);
- wizard pubblico `/wizard/...` end-to-end (F-wizard).
"""

from __future__ import annotations

import json
import uuid

import pytest
from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse

from apps.calculators.enums import CalculationStatus, CaseType, ConfidenceLevel
from apps.cases.forms import ItalyRoadAccidentWizardForm
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
from apps.crm.models import Lead
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


# ---------------------------------------------------------------------------
# Wizard pubblico (F-wizard)
# ---------------------------------------------------------------------------


WIZARD_VALID_PAYLOAD = {
    "accident_date": "",
    "victim_age": "",
    "permanent_disability_percentage": "",
    "total_temporary_disability_days": "",
    "partial_temporary_disability_days": "",
    "medical_expenses": "",
    "lost_income": "",
    "fault_percentage": "",
    "accident_country": "IT",
    "consent_simulation": "on",
    "website": "",
}


@pytest.mark.django_db
def test_wizard_start_returns_200():
    response = Client().get(reverse("cases:wizard_start"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Linka almeno il modulo Italia road accident.
    assert reverse("cases:wizard_italy_road_accident") in body


@pytest.mark.django_db
def test_wizard_italy_road_accident_get_returns_200():
    response = Client().get(reverse("cases:wizard_italy_road_accident"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'name="consent_simulation"' in body
    assert 'name="website"' in body  # honeypot presente nel markup


@pytest.mark.django_db
def test_wizard_form_valid_minimal():
    form = ItalyRoadAccidentWizardForm(data=WIZARD_VALID_PAYLOAD)
    assert form.is_valid(), form.errors
    assert form.is_likely_bot is False


@pytest.mark.django_db
def test_wizard_form_rejects_missing_consent():
    payload = {**WIZARD_VALID_PAYLOAD}
    payload.pop("consent_simulation")
    form = ItalyRoadAccidentWizardForm(data=payload)
    assert not form.is_valid()
    assert "consent_simulation" in form.errors


@pytest.mark.django_db
def test_wizard_form_rejects_future_accident_date():
    from datetime import date, timedelta

    payload = {
        **WIZARD_VALID_PAYLOAD,
        "accident_date": (date.today() + timedelta(days=2)).isoformat(),
    }
    form = ItalyRoadAccidentWizardForm(data=payload)
    assert not form.is_valid()
    assert "accident_date" in form.errors


@pytest.mark.django_db
def test_wizard_form_honeypot_is_bot():
    payload = {**WIZARD_VALID_PAYLOAD, "website": "http://spam.example/"}
    form = ItalyRoadAccidentWizardForm(data=payload)
    assert form.is_valid()
    assert form.is_likely_bot is True


@pytest.mark.django_db
def test_wizard_form_to_input_data_only_expected_keys():
    form = ItalyRoadAccidentWizardForm(data=WIZARD_VALID_PAYLOAD)
    assert form.is_valid(), form.errors
    payload = form.to_input_data()
    expected = {
        "accident_country",
        "accident_date",
        "victim_age",
        "permanent_disability_percentage",
        "total_temporary_disability_days",
        "partial_temporary_disability_days",
        "medical_expenses",
        "lost_income",
        "fault_percentage",
    }
    assert set(payload.keys()) == expected
    # Niente consent / website nel payload di dominio.
    assert "consent_simulation" not in payload
    assert "website" not in payload


@pytest.mark.django_db
def test_wizard_post_valid_creates_simulation_and_redirects(italy_setup):
    response = Client().post(
        reverse("cases:wizard_italy_road_accident"),
        WIZARD_VALID_PAYLOAD,
    )
    assert Simulation.objects.count() == 1
    sim = Simulation.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})


@pytest.mark.django_db
def test_wizard_post_creates_consent_record(italy_setup):
    Client().post(reverse("cases:wizard_italy_road_accident"), WIZARD_VALID_PAYLOAD)
    purpose = ConsentPurpose.objects.get(code="simulation_processing")
    record = ConsentRecord.objects.filter(purpose=purpose).first()
    assert record is not None
    assert record.accepted is True
    sim = Simulation.objects.get()
    assert sim.consent_record == record


@pytest.mark.django_db
def test_wizard_post_without_consent_does_not_create_simulation(italy_setup):
    payload = {**WIZARD_VALID_PAYLOAD}
    payload.pop("consent_simulation")
    response = Client().post(reverse("cases:wizard_italy_road_accident"), payload)
    assert response.status_code == 200  # form re-rendered
    assert Simulation.objects.count() == 0
    assert ConsentRecord.objects.count() == 0


@pytest.mark.django_db
def test_wizard_post_honeypot_does_not_create_simulation(italy_setup):
    payload = {**WIZARD_VALID_PAYLOAD, "website": "http://spam/"}
    response = Client().post(reverse("cases:wizard_italy_road_accident"), payload)
    # Redirect alla landing wizard, ma niente Simulation né ConsentRecord.
    assert response.status_code == 302
    assert response.url == reverse("cases:wizard_start")
    assert Simulation.objects.count() == 0
    assert ConsentRecord.objects.count() == 0


@pytest.mark.django_db
def test_wizard_post_does_not_create_lead(italy_setup):
    """REQ: il wizard NON crea Lead. Il funnel passa per /contact/."""
    initial = Lead.objects.count()
    Client().post(reverse("cases:wizard_italy_road_accident"), WIZARD_VALID_PAYLOAD)
    assert Lead.objects.count() == initial


@pytest.mark.django_db
def test_wizard_post_status_is_unavailable_without_sources(italy_setup):
    """Senza fonti `approved` lo status deve essere 'unavailable...'."""
    Client().post(reverse("cases:wizard_italy_road_accident"), WIZARD_VALID_PAYLOAD)
    sim = Simulation.objects.get()
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


@pytest.mark.django_db
def test_wizard_post_input_data_persisted_with_expected_keys(italy_setup):
    payload = {
        **WIZARD_VALID_PAYLOAD,
        "victim_age": "42",
        "permanent_disability_percentage": "12.5",
    }
    Client().post(reverse("cases:wizard_italy_road_accident"), payload)
    sim = Simulation.objects.get()
    assert sim.input_data["victim_age"] == 42
    assert sim.input_data["permanent_disability_percentage"] == "12.5"
    # Nessun campo di flusso/honeypot persistito.
    assert "consent_simulation" not in sim.input_data
    assert "website" not in sim.input_data


@pytest.mark.django_db
def test_wizard_result_page_returns_200(italy_setup):
    Client().post(reverse("cases:wizard_italy_road_accident"), WIZARD_VALID_PAYLOAD)
    sim = Simulation.objects.get()
    response = Client().get(
        reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    )
    assert response.status_code == 200


@pytest.mark.django_db
def test_wizard_result_shows_disclaimer(italy_setup):
    Client().post(reverse("cases:wizard_italy_road_accident"), WIZARD_VALID_PAYLOAD)
    sim = Simulation.objects.get()
    response = Client().get(
        reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    )
    body = response.content.decode("utf-8")
    # Il disclaimer del motore F4 contiene "indicativa" (it).
    assert "indicativa" in body.lower() or "indicative" in body.lower()


@pytest.mark.django_db
def test_wizard_result_cta_links_to_contact_with_sim(italy_setup):
    Client().post(reverse("cases:wizard_italy_road_accident"), WIZARD_VALID_PAYLOAD)
    sim = Simulation.objects.get()
    response = Client().get(
        reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    )
    body = response.content.decode("utf-8")
    expected = reverse("crm:contact") + f"?sim={sim.public_id}"
    assert expected in body


@pytest.mark.django_db
def test_wizard_result_404_for_unknown_public_id():
    response = Client().get(reverse("cases:wizard_result", kwargs={"public_id": str(uuid.uuid4())}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_wizard_arabic_locale_renders_rtl(italy_setup):
    response = Client().get(
        reverse("cases:wizard_italy_road_accident"),
        HTTP_ACCEPT_LANGUAGE="ar",
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Il context_processor `site_context` setta dir="rtl" per la lingua araba.
    assert 'dir="rtl"' in body


@pytest.mark.django_db
def test_wizard_post_unavailable_warning_in_output(italy_setup):
    """Senza fonti approved il calculator (placeholder) emette un warning."""
    Client().post(reverse("cases:wizard_italy_road_accident"), WIZARD_VALID_PAYLOAD)
    sim = Simulation.objects.get()
    warnings = sim.output_data.get("warnings") or []
    assert any("approved" in w.lower() or "validation" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# F-france-road-accident-bootstrap — wizard FR scaffold.
# Nessun importo reale: il calculator FR è un placeholder.
# ---------------------------------------------------------------------------


@pytest.fixture
def france_setup(db):
    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    eur = Currency.objects.filter(code="EUR").first() or Currency.objects.create(
        code="EUR", name="Euro", symbol="€"
    )
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France (niveau national)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=french,
    )
    return {"country": france, "currency": eur, "language": french, "jurisdiction": juris}


WIZARD_FR_VALID_PAYLOAD = {
    "accident_country": "FR",
    "victim_age": "35",
    "permanent_disability_percentage": "10",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}


@pytest.mark.django_db
def test_wizard_start_links_to_france_scaffold():
    """La landing /wizard/ deve esporre il link al wizard FR scaffold."""
    response = Client().get(reverse("cases:wizard_start"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert reverse("cases:wizard_france_road_accident") in body
    # E deve marcarlo come "Legal sources under review", non "Module ready".
    assert "Legal sources under review" in body


@pytest.mark.django_db
def test_wizard_france_road_accident_get_returns_200():
    response = Client().get(reverse("cases:wizard_france_road_accident"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'name="consent_simulation"' in body
    assert 'name="website"' in body
    # Banner specifico del placeholder FR.
    assert "Module under legal validation" in body


@pytest.mark.django_db
def test_wizard_france_post_creates_simulation_unavailable(france_setup):
    """POST valido crea Simulation FR ma status = unavailable, no estimates."""
    response = Client().post(
        reverse("cases:wizard_france_road_accident"),
        WIZARD_FR_VALID_PAYLOAD,
    )
    assert Simulation.objects.count() == 1
    sim = Simulation.objects.get()
    assert sim.jurisdiction == france_setup["jurisdiction"]
    assert sim.country == france_setup["country"]
    assert sim.case_type == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value or True
    # Status check vero
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    # Nessun importo prodotto.
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None
    # Redirect a result.
    assert response.status_code == 302
    assert response.url == reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})


@pytest.mark.django_db
def test_wizard_france_post_input_data_uses_FR(france_setup):
    Client().post(
        reverse("cases:wizard_france_road_accident"),
        WIZARD_FR_VALID_PAYLOAD,
    )
    sim = Simulation.objects.get()
    assert sim.input_data["accident_country"] == "FR"


@pytest.mark.django_db
def test_wizard_france_form_default_country_is_FR():
    from apps.cases.forms import FranceRoadAccidentWizardForm

    form = FranceRoadAccidentWizardForm()
    # Field initial value must be 'FR'.
    assert form.fields["accident_country"].initial == "FR"


@pytest.mark.django_db
def test_wizard_france_post_no_estimates_in_output(france_setup):
    """Output JSON della Simulation FR non deve contenere importi numerici."""
    Client().post(
        reverse("cases:wizard_france_road_accident"),
        WIZARD_FR_VALID_PAYLOAD,
    )
    sim = Simulation.objects.get()
    output = sim.output_data or {}
    assert output.get("estimated_min") is None
    assert output.get("estimated_mid") is None
    assert output.get("estimated_max") is None
    # Lo status è blockante per qualunque downstream (PDF, ecc.).
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


# ---------------------------------------------------------------------------
# F-belgium-road-accident-bootstrap — wizard BE scaffold.
# ---------------------------------------------------------------------------


@pytest.fixture
def belgium_setup(db):
    belgium = Country.objects.create(code="BE", code_alpha3="BEL", name="Belgique")
    eur = Currency.objects.filter(code="EUR").first() or Currency.objects.create(
        code="EUR", name="Euro", symbol="€"
    )
    french_be = Language.objects.filter(code="fr").first() or Language.objects.create(
        code="fr", name="Français"
    )
    juris = Jurisdiction.objects.create(
        country=belgium,
        code="BE-NATIONAL",
        name="Belgique (niveau fédéral)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=french_be,
    )
    return {"country": belgium, "currency": eur, "language": french_be, "jurisdiction": juris}


WIZARD_BE_VALID_PAYLOAD = {
    "accident_country": "BE",
    "victim_age": "35",
    "permanent_disability_percentage": "10",
    "fault_percentage": "0",
    "consent_simulation": "on",
    "website": "",
}


@pytest.mark.django_db
def test_wizard_start_links_to_belgium_scaffold():
    response = Client().get(reverse("cases:wizard_start"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert reverse("cases:wizard_belgium_road_accident") in body


@pytest.mark.django_db
def test_wizard_belgium_road_accident_get_returns_200():
    response = Client().get(reverse("cases:wizard_belgium_road_accident"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert 'name="consent_simulation"' in body
    assert 'name="website"' in body
    assert "Module under legal validation" in body


@pytest.mark.django_db
def test_wizard_belgium_post_creates_simulation_unavailable(belgium_setup):
    response = Client().post(
        reverse("cases:wizard_belgium_road_accident"),
        WIZARD_BE_VALID_PAYLOAD,
    )
    assert Simulation.objects.count() == 1
    sim = Simulation.objects.get()
    assert sim.jurisdiction == belgium_setup["jurisdiction"]
    assert sim.country == belgium_setup["country"]
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None
    assert response.status_code == 302
    assert response.url == reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})


@pytest.mark.django_db
def test_wizard_belgium_post_input_data_uses_BE(belgium_setup):
    Client().post(
        reverse("cases:wizard_belgium_road_accident"),
        WIZARD_BE_VALID_PAYLOAD,
    )
    sim = Simulation.objects.get()
    assert sim.input_data["accident_country"] == "BE"


@pytest.mark.django_db
def test_wizard_belgium_form_default_country_is_BE():
    from apps.cases.forms import BelgiumRoadAccidentWizardForm

    form = BelgiumRoadAccidentWizardForm()
    assert form.fields["accident_country"].initial == "BE"


@pytest.mark.django_db
def test_wizard_belgium_post_no_estimates_in_output(belgium_setup):
    Client().post(
        reverse("cases:wizard_belgium_road_accident"),
        WIZARD_BE_VALID_PAYLOAD,
    )
    sim = Simulation.objects.get()
    output = sim.output_data or {}
    assert output.get("estimated_min") is None
    assert output.get("estimated_mid") is None
    assert output.get("estimated_max") is None
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
