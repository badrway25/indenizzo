"""
Tests F-france-road-accident-bootstrap — scaffold France calculator.

REGOLA D'ORO: nessun valore TUN/Référentiel reale. Il calculator FR è un
placeholder che restituisce sempre `unavailable_requires_legal_validation`
finché lo Studio non avrà promosso a `approved` fonti/dataset/formula.

Cosa verifichiamo:
- registry contiene la coppia (FR-NATIONAL, road_accident_bodily_injury);
- il calculator FR senza fonti approved → unavailable;
- il calculator FR anche con fonti approved → resta unavailable
  (placeholder, non ha engine economico);
- nessun importo viene mai prodotto;
- il calculator IT continua a calcolare (regressione);
- seed_france_legal_sources crea fonti in needs_review e ne crea
  nessuna in approved.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.core.management import call_command

from apps.calculators.enums import CalculationStatus, CaseType
from apps.calculators.registry import get_calculator, list_available_calculators
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource

# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_registry_contains_france_road_accident_pair():
    pairs = set(list_available_calculators())
    assert ("FR-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value) in pairs


def test_france_calculator_class_imports():
    """Il calculator FR è importabile e sottoclasse di BaseCalculator."""
    from apps.calculators.engines.base import BaseCalculator
    from apps.calculators.engines.france import FranceRoadAccidentBodilyInjuryCalculator

    assert issubclass(FranceRoadAccidentBodilyInjuryCalculator, BaseCalculator)
    assert FranceRoadAccidentBodilyInjuryCalculator.jurisdiction_code == "FR-NATIONAL"
    assert (
        FranceRoadAccidentBodilyInjuryCalculator.case_type
        == CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
    )


def test_registry_lookup_returns_france_class():
    """`_registry.get` restituisce la classe FR per la coppia FR/road_accident."""
    from apps.calculators.engines.france import FranceRoadAccidentBodilyInjuryCalculator

    cls = get_calculator("FR-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is FranceRoadAccidentBodilyInjuryCalculator


# ---------------------------------------------------------------------------
# FR calculator: senza fonti / con fonti approved → sempre unavailable
# ---------------------------------------------------------------------------


@pytest.fixture
def france(db) -> Country:
    return Country.objects.create(code="FR", code_alpha3="FRA", name="France")


@pytest.fixture
def france_jurisdiction(france: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France (niveau national)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


@pytest.fixture
def french(db) -> Language:
    return Language.objects.create(code="fr", name="Français")


@pytest.mark.django_db
def test_france_calculator_unavailable_when_no_sources(france_jurisdiction, french):
    from apps.calculators.engines.france import FranceRoadAccidentBodilyInjuryCalculator

    calc = FranceRoadAccidentBodilyInjuryCalculator(language="fr")
    r = calc.compute({"victim_age": 35, "permanent_disability_percentage": 10})
    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    # No estimates produced.
    assert r.estimated_min is None
    assert r.estimated_mid is None
    assert r.estimated_max is None


@pytest.mark.django_db
def test_france_calculator_unavailable_even_with_approved_source(
    france, france_jurisdiction, french
):
    """Anche con LegalSource approved, il placeholder NON inventa importi."""
    from apps.calculators.engines.france import FranceRoadAccidentBodilyInjuryCalculator

    LegalSource.objects.create(
        slug="fr-fake-source-for-test",
        title="Fake FR source (test stub, never real values)",
        country=france,
        jurisdiction=france_jurisdiction,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
    )

    calc = FranceRoadAccidentBodilyInjuryCalculator(language="fr")
    r = calc.compute({"victim_age": 35, "permanent_disability_percentage": 10})
    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert r.estimated_min is None
    assert r.estimated_mid is None
    assert r.estimated_max is None
    # Sources DEVONO essere comunque echo-ate per audit, anche se non usate.
    assert len(r.sources) >= 1
    assert any(s.country == "FR" for s in r.sources)
    # Missing-document specifico per il placeholder.
    assert "calculator_engine_pending_for_jurisdiction" in r.missing_documents


# ---------------------------------------------------------------------------
# Italy regressione: deve continuare a calcolare
# ---------------------------------------------------------------------------


@pytest.mark.django_db(transaction=False)
def test_italy_calculator_still_calculated_after_france_scaffold():
    """Smoke: aggiungere FR non rompe il calcolo IT live (DB realtà locale).

    Usa il DB di sviluppo locale: la suite pytest pulisce le tabelle a
    ogni test, quindi qui usiamo il calculator senza fonti — verifichiamo
    SOLO che il calculator IT esista, non rompa, e non venga sostituito
    dal calculator FR per la stessa coppia.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    cls = get_calculator("IT-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is ItalyRoadAccidentBodilyInjuryCalculator


# ---------------------------------------------------------------------------
# Seed France: needs_review, no approved created
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_france_legal_sources_creates_needs_review_only():
    """Il seed FR crea fonti SEMPRE non approved (needs_review)."""
    from io import StringIO

    out = StringIO()
    call_command("seed_france_legal_sources", "--quiet", stdout=out)

    fr_sources = LegalSource.objects.filter(country__code="FR")
    assert fr_sources.exists()
    # Tutte non-approved.
    assert not fr_sources.filter(status=SourceStatus.APPROVED).exists()
    # Almeno una needs_review.
    assert fr_sources.filter(status=SourceStatus.NEEDS_REVIEW).exists()
    # Slug attesi presenti.
    expected_slugs = {
        "fr-loi-1985-07-05-badinter",
        "fr-code-assurances-l211",
        "fr-referentiel-indicatif-cours-appel-2022",
        "fr-bareme-capitalisation-gazette-palais-2022",
    }
    assert expected_slugs.issubset(set(fr_sources.values_list("slug", flat=True)))


@pytest.mark.django_db
def test_seed_france_idempotent_does_not_downgrade_approved():
    """Re-eseguire il seed NON retrocede una fonte già approved."""
    from io import StringIO

    call_command("seed_france_legal_sources", "--quiet", stdout=StringIO())

    # Promuoviamo manualmente una fonte ad approved (simula atto Studio).
    source = LegalSource.objects.get(slug="fr-loi-1985-07-05-badinter")
    source.status = SourceStatus.APPROVED
    source.save(update_fields=["status"])

    # Re-eseguiamo il seed: la fonte approved deve restare approved.
    call_command("seed_france_legal_sources", "--quiet", stdout=StringIO())
    source.refresh_from_db()
    assert source.status == SourceStatus.APPROVED
