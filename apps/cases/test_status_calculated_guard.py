"""
H-1 guard (presentation layer): la result page web mostra gli importi SOLO
quando ``Simulation.status == "calculated"``, oltre a essere non-null.

Difesa in profondità sull'invariante "no calcolo falso": oggi gli importi
si persistono solo nel ramo CALCULATED, quindi il guard non cambia il
comportamento corrente; protegge contro una futura regressione in cui una
Simulation non-``calculated`` portasse comunque un ``estimated_*``
valorizzato (stato incoerente).
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators.enums import CalculationStatus, CaseType
from apps.cases.models import Simulation
from apps.jurisdictions.models import Country, Jurisdiction

# Marcatore stabile: presente SOLO nel ramo `has_estimate` del template
# `templates/public/wizard_result.html`.
_RANGE_MARKER = 'id="result-range-heading"'


@pytest.fixture
def italy_jurisdiction(db) -> Jurisdiction:
    country = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    return Jurisdiction.objects.create(
        country=country,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


def _make_sim(
    jur: Jurisdiction,
    *,
    status: str,
    estimated,
    confidence: str = "medium",
    missing=None,
    assumptions=None,
) -> Simulation:
    output = {
        "status": status,
        "warnings": [],
        "missing_documents": list(missing or []),
        "assumptions": list(assumptions or []),
        "breakdown": [],
        "sources": [],
        "estimated_min": str(estimated[0]) if estimated else None,
        "estimated_mid": str(estimated[1]) if estimated else None,
        "estimated_max": str(estimated[2]) if estimated else None,
        "currency": "EUR" if estimated else "",
        "legal_disclaimer": "Test disclaimer",
    }
    return Simulation.objects.create(
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        locale="it",
        jurisdiction=jur,
        country=jur.country,
        input_data={"victim_age": 35, "permanent_disability_percentage": 10},
        output_data=output,
        sources_snapshot=[],
        status=status,
        confidence=confidence,
        currency="EUR" if estimated else "",
        estimated_min=Decimal(str(estimated[0])) if estimated else None,
        estimated_mid=Decimal(str(estimated[1])) if estimated else None,
        estimated_max=Decimal(str(estimated[2])) if estimated else None,
    )


@pytest.mark.django_db
def test_result_page_shows_range_when_calculated(italy_jurisdiction):
    """Controllo positivo: status `calculated` → la fascia di range è mostrata."""
    sim = _make_sim(
        italy_jurisdiction,
        status=CalculationStatus.CALCULATED.value,
        estimated=(Decimal("1.00"), Decimal("1.00"), Decimal("1.00")),
    )
    resp = Client().get(reverse("cases:wizard_result", kwargs={"public_id": sim.public_id}))
    assert resp.status_code == 200
    assert _RANGE_MARKER in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_result_page_hides_range_when_status_not_calculated(italy_jurisdiction):
    """
    Stato incoerente (status `unavailable` MA `estimated_*` valorizzato):
    la result page NON deve mostrare la fascia di importi.
    """
    sim = _make_sim(
        italy_jurisdiction,
        status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
        estimated=(Decimal("99999.00"), Decimal("99999.00"), Decimal("99999.00")),
    )
    resp = Client().get(reverse("cases:wizard_result", kwargs={"public_id": sim.public_id}))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert _RANGE_MARKER not in html
    # L'importo incoerente non deve comparire da nessuna parte nella pagina.
    assert "99999" not in html


# ---------------------------------------------------------------------------
# H2-2 — transparency: confidence + missing_documents sulla result page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_shows_confidence_badge(italy_jurisdiction):
    """Il livello di confidence dell'engine è mostrato sul percorso calcolato.

    Asserzione locale-indipendente via `data-confidence` (la label testuale è
    tradotta: la pagina rende in italiano)."""
    sim = _make_sim(
        italy_jurisdiction,
        status=CalculationStatus.CALCULATED.value,
        estimated=(Decimal("1.00"), Decimal("1.00"), Decimal("1.00")),
        confidence="medium",
    )
    html = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": sim.public_id}))
        .content.decode("utf-8")
    )
    assert 'data-confidence="medium"' in html


@pytest.mark.django_db
def test_result_page_shows_missing_documents_section_with_none_note(italy_jurisdiction):
    """Percorso calcolato senza missing_documents → sezione presente, stato
    'none' (coerente col PDF)."""
    sim = _make_sim(
        italy_jurisdiction,
        status=CalculationStatus.CALCULATED.value,
        estimated=(Decimal("1.00"), Decimal("1.00"), Decimal("1.00")),
        missing=[],
    )
    html = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": sim.public_id}))
        .content.decode("utf-8")
    )
    assert 'data-testid="missing-documents"' in html
    assert 'data-state="none"' in html


@pytest.mark.django_db
def test_result_page_localizes_engine_missing_documents(italy_jurisdiction):
    """Un codice diagnostico in missing_documents è reso in testo localizzato,
    non come slug grezzo."""
    from apps.calculators.diagnostics import diagnostic_message

    sim = _make_sim(
        italy_jurisdiction,
        status=CalculationStatus.CALCULATED.value,
        estimated=(Decimal("1.00"), Decimal("1.00"), Decimal("1.00")),
        missing=["compensation_row_match"],
    )
    html = (
        Client()
        .get(reverse("cases:wizard_result", kwargs={"public_id": sim.public_id}))
        .content.decode("utf-8")
    )
    # Il view ha trasformato il codice in una frase umana localizzata
    # (lista non vuota → stato 'present'); lo slug grezzo NON deve trapelare.
    # Non asseriamo il testo tradotto esatto: il locale attivo della pagina
    # dipende dall'ordine dei test (i18n), quindi la prova robusta è
    # stato='present' + assenza dello slug.
    assert 'data-state="present"' in html
    assert "compensation_row_match" not in html
    # `diagnostic_message` resta la fonte usata dal view per la resa.
    assert diagnostic_message("compensation_row_match", language="it")


@pytest.mark.django_db
def test_result_page_keeps_disclaimer_visible(italy_jurisdiction):
    """Il disclaimer resta visibile su entrambi i percorsi (testo controllato
    dal test, locale-indipendente)."""
    for status in (
        CalculationStatus.CALCULATED.value,
        CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
    ):
        sim = _make_sim(
            italy_jurisdiction,
            status=status,
            estimated=(
                (Decimal("1.00"), Decimal("1.00"), Decimal("1.00"))
                if status == CalculationStatus.CALCULATED.value
                else None
            ),
        )
        html = (
            Client()
            .get(reverse("cases:wizard_result", kwargs={"public_id": sim.public_id}))
            .content.decode("utf-8")
        )
        assert "Test disclaimer" in html
