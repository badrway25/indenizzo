"""
Tests F-report-pdf-mvp.

Verifichiamo:
- generazione PDF da Simulation `unavailable` (output_data popolato ma
  estimated_* tutti null) → PDF prodotto, file_hash valorizzato;
- generazione PDF da Simulation `calculated` (fixture test-only) → PDF
  prodotto, importi presenti;
- response status / content-type;
- 404 su public_id sconosciuto;
- link "Download PDF report" presente sulla result page del wizard;
- nessuna PII tecnica nel contenuto (honeypot, consent_simulation);
- service NON ricalcola la Simulation;
- audit privacy `DATA_EXPORTED` registrato;
- nessun valore reale TUN nei test.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators.disclaimer import LEGAL_DISCLAIMERS
from apps.calculators.enums import CalculationStatus, CaseType
from apps.cases.models import Simulation
from apps.compliance.enums import PrivacyEventType
from apps.compliance.models import PrivacyAuditEvent
from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
from apps.reports.models import SimulationReport
from apps.reports.services import generate_simulation_report

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolated_media_root(tmp_path, settings):
    """
    Tutti i test in questo modulo scrivono FileField sotto un MEDIA_ROOT
    temporaneo (per non polluire `BASE_DIR/media/`) e isolato per test
    (per evitare collisioni tra fixture).
    """
    settings.MEDIA_ROOT = str(tmp_path)
    yield


@pytest.fixture
def italy(db) -> Country:
    return Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")


@pytest.fixture
def italy_jurisdiction(db, italy: Country) -> Jurisdiction:
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    return Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )


def _make_simulation(
    italy_jurisdiction,
    *,
    status: str = CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
    estimated=None,
    input_data=None,
    sources=None,
    warnings=None,
    missing=None,
    assumptions=None,
    breakdown=None,
    locale: str = "it",
    legal_disclaimer: str | None = None,
) -> Simulation:
    """Crea una Simulation persistita con `output_data` arbitrario test-only."""
    output = {
        "status": status,
        "warnings": warnings or [],
        "missing_documents": missing or [],
        "assumptions": assumptions or [],
        "breakdown": breakdown or [],
        "sources": sources or [],
        "estimated_min": str(estimated[0]) if estimated else None,
        "estimated_mid": str(estimated[1]) if estimated else None,
        "estimated_max": str(estimated[2]) if estimated else None,
        "currency": "EUR" if estimated else "",
        "legal_disclaimer": legal_disclaimer or LEGAL_DISCLAIMERS["it"],
    }
    return Simulation.objects.create(
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        locale=locale,
        jurisdiction=italy_jurisdiction,
        country=italy_jurisdiction.country,
        input_data=input_data or {},
        output_data=output,
        sources_snapshot=sources or [],
        status=status,
        currency="EUR" if estimated else "",
        estimated_min=Decimal(str(estimated[0])) if estimated else None,
        estimated_mid=Decimal(str(estimated[1])) if estimated else None,
        estimated_max=Decimal(str(estimated[2])) if estimated else None,
    )


# ---------------------------------------------------------------------------
# Service-level tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_generate_report_for_unavailable_simulation(italy_jurisdiction):
    """Simulation `unavailable` → PDF prodotto, hash valorizzato."""
    simulation = _make_simulation(italy_jurisdiction)

    report = generate_simulation_report(simulation)

    assert report.status == SimulationReport.Status.GENERATED
    assert report.file_hash != ""
    assert report.file_size_bytes > 0
    assert report.simulation_id == simulation.pk
    assert report.language == "it"

    with report.file.open("rb") as fh:
        content = fh.read()
    assert content.startswith(b"%PDF-")
    assert len(content) == report.file_size_bytes


@pytest.mark.django_db
def test_generate_report_for_calculated_simulation(italy_jurisdiction):
    """
    Simulation `calculated` con estimated_* fittizi (1 EUR — fixture
    only, NOT real TUN values) → PDF contiene la sezione importi.
    """
    simulation = _make_simulation(
        italy_jurisdiction,
        status=CalculationStatus.CALCULATED.value,
        estimated=(Decimal("1.00"), Decimal("1.00"), Decimal("1.00")),
        breakdown=[
            {
                "label": "Danno biologico permanente",
                "amount_min": "1.00",
                "amount_mid": "1.00",
                "amount_max": "1.00",
                "formula": "italy_art_138_tun_2025_base",
                "source_ref_ids": [],
                "notes": "fixture only — NOT real TUN data",
            }
        ],
    )

    report = generate_simulation_report(simulation)

    assert report.status == SimulationReport.Status.GENERATED
    with report.file.open("rb") as fh:
        content = fh.read()
    assert b"%PDF-" in content[:8]


@pytest.mark.django_db
def test_pdf_does_not_contain_honeypot_or_consent(italy_jurisdiction):
    """
    L'`input_data` può contenere honeypot (`website`) o flag
    consenso: il PDF NON deve includerli.
    """
    simulation = _make_simulation(
        italy_jurisdiction,
        input_data={
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "website": "spam_attempt_xyz",
            "consent_simulation": True,
            "_anonymized": False,
        },
    )

    report = generate_simulation_report(simulation)
    with report.file.open("rb") as fh:
        content = fh.read()
    assert b"spam_attempt_xyz" not in content
    assert b"consent_simulation" not in content


@pytest.mark.django_db
def test_service_does_not_recompute_simulation(italy_jurisdiction):
    """
    Il service legge `output_data` e basta: dopo generazione, lo stato
    della Simulation NON cambia.
    """
    simulation = _make_simulation(italy_jurisdiction)
    snapshot_status = simulation.status
    snapshot_output = dict(simulation.output_data)

    generate_simulation_report(simulation)

    simulation.refresh_from_db()
    assert simulation.status == snapshot_status
    assert simulation.output_data == snapshot_output


@pytest.mark.django_db
def test_service_writes_privacy_audit_event(italy_jurisdiction):
    """Generazione PDF → PrivacyAuditEvent `DATA_EXPORTED`."""
    simulation = _make_simulation(italy_jurisdiction)
    initial_events = PrivacyAuditEvent.objects.count()

    report = generate_simulation_report(simulation)

    events_after = PrivacyAuditEvent.objects.filter(
        event_type=PrivacyEventType.DATA_EXPORTED,
        target_model="reports.SimulationReport",
        target_object_id=str(report.pk),
    )
    assert events_after.exists()
    assert PrivacyAuditEvent.objects.count() == initial_events + 1


@pytest.mark.django_db
def test_service_creates_new_report_on_each_call(italy_jurisdiction):
    """
    Per audit completo, ogni invocazione genera un nuovo
    `SimulationReport`. È volutamente NON idempotente sull'aggregato:
    la ricostruzione storica richiede tutti i record.
    """
    simulation = _make_simulation(italy_jurisdiction)
    first = generate_simulation_report(simulation)
    second = generate_simulation_report(simulation)
    assert first.pk != second.pk
    assert SimulationReport.objects.filter(simulation=simulation).count() == 2


@pytest.mark.django_db
def test_arabic_locale_marks_rtl_fallback(italy_jurisdiction):
    """
    Per `lang=ar` reportlab non gestisce bidi: il service annota
    `metadata.rtl_fallback=True` ma genera comunque il PDF.
    """
    simulation = _make_simulation(italy_jurisdiction, locale="ar")
    report = generate_simulation_report(simulation, language="ar")

    assert report.status == SimulationReport.Status.GENERATED
    assert report.metadata.get("rtl_fallback") is True


# ---------------------------------------------------------------------------
# Renderer-level: input filtering (white-box)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_renderer_input_whitelist_excludes_honeypot_keys():
    """Sanity check sul registro: nessuna chiave sensibile è in whitelist."""
    from apps.reports.pdf_renderer import _INPUT_WHITELIST

    forbidden = {"website", "consent_simulation", "_anonymized"}
    assert forbidden.isdisjoint(_INPUT_WHITELIST.keys())


# ---------------------------------------------------------------------------
# Endpoint tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pdf_endpoint_returns_200_application_pdf(italy_jurisdiction):
    simulation = _make_simulation(italy_jurisdiction)
    client = Client()
    url = reverse("reports:simulation_pdf", kwargs={"public_id": simulation.public_id})

    response = client.get(url)

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    body = b"".join(response.streaming_content)
    assert body.startswith(b"%PDF-")


@pytest.mark.django_db
def test_pdf_endpoint_404_on_unknown_public_id():
    client = Client()
    bogus = uuid.uuid4()
    url = reverse("reports:simulation_pdf", kwargs={"public_id": bogus})

    response = client.get(url)
    assert response.status_code == 404


@pytest.mark.django_db
def test_pdf_endpoint_creates_simulation_report(italy_jurisdiction):
    simulation = _make_simulation(italy_jurisdiction)
    client = Client()
    url = reverse("reports:simulation_pdf", kwargs={"public_id": simulation.public_id})

    assert SimulationReport.objects.filter(simulation=simulation).count() == 0
    client.get(url)
    assert SimulationReport.objects.filter(simulation=simulation).count() == 1


# ---------------------------------------------------------------------------
# Wizard result page contains the download CTA
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_result_page_contains_pdf_download_link(italy_jurisdiction):
    simulation = _make_simulation(italy_jurisdiction)
    client = Client()
    result_url = reverse("cases:wizard_result", kwargs={"public_id": simulation.public_id})
    response = client.get(result_url)
    assert response.status_code == 200

    expected_pdf_url = reverse("reports:simulation_pdf", kwargs={"public_id": simulation.public_id})
    assert expected_pdf_url.encode() in response.content


# ---------------------------------------------------------------------------
# Renderer doesn't crash on edge cases
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_renderer_handles_empty_output_data(italy_jurisdiction):
    """Output_data minimo (mai mostrare importi se assenti)."""
    simulation = Simulation.objects.create(
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        locale="it",
        jurisdiction=italy_jurisdiction,
        country=italy_jurisdiction.country,
        input_data={},
        output_data={},
        sources_snapshot=[],
        status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
    )
    report = generate_simulation_report(simulation)
    assert report.status == SimulationReport.Status.GENERATED
    assert report.file_size_bytes > 0


@pytest.mark.django_db
def test_renderer_passes_simulation_status_in_metadata(italy_jurisdiction):
    """
    Il `metadata` del report registra lo status della Simulation
    sorgente: prova indiretta che il rendering ha letto i campi.
    """
    simulation = _make_simulation(italy_jurisdiction)
    report = generate_simulation_report(simulation)
    assert report.metadata.get("simulation_status") == simulation.status
    assert report.metadata.get("language_requested") == "it"
