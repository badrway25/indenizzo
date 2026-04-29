"""
Tests F-belgium-road-accident-bootstrap — scaffold Belgium calculator.

REGOLA D'ORO: nessun valore reale del Tableau indicatif belga / barème
Schryvers nei test. Il calculator BE è un placeholder che restituisce
sempre `unavailable_requires_legal_validation` finché lo Studio non
avrà promosso a `approved` fonti/dataset/formula.

Cosa verifichiamo:
- registry contiene la coppia (BE-NATIONAL, road_accident_bodily_injury);
- il calculator BE senza fonti approved → unavailable;
- il calculator BE anche con fonti approved → resta unavailable
  (placeholder, missing-document `calculator_engine_pending_for_jurisdiction`);
- nessun importo viene mai prodotto;
- il calculator IT continua a calcolare (regressione);
- il calculator FR scaffold resta invariato (regressione);
- seed_belgium_legal_sources crea fonti needs_review e ne crea
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


def test_registry_contains_belgium_road_accident_pair():
    pairs = set(list_available_calculators())
    assert ("BE-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value) in pairs


def test_belgium_calculator_class_imports():
    """Il calculator BE è importabile e sottoclasse di BaseCalculator."""
    from apps.calculators.engines.base import BaseCalculator
    from apps.calculators.engines.belgium import BelgiumRoadAccidentBodilyInjuryCalculator

    assert issubclass(BelgiumRoadAccidentBodilyInjuryCalculator, BaseCalculator)
    assert BelgiumRoadAccidentBodilyInjuryCalculator.jurisdiction_code == "BE-NATIONAL"
    assert (
        BelgiumRoadAccidentBodilyInjuryCalculator.case_type
        == CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
    )


def test_registry_lookup_returns_belgium_class():
    from apps.calculators.engines.belgium import BelgiumRoadAccidentBodilyInjuryCalculator

    cls = get_calculator("BE-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is BelgiumRoadAccidentBodilyInjuryCalculator


# ---------------------------------------------------------------------------
# BE calculator: senza fonti / con fonti approved → sempre unavailable
# ---------------------------------------------------------------------------


@pytest.fixture
def belgium(db) -> Country:
    return Country.objects.create(code="BE", code_alpha3="BEL", name="Belgique")


@pytest.fixture
def belgium_jurisdiction(belgium: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=belgium,
        code="BE-NATIONAL",
        name="Belgique (niveau fédéral)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


@pytest.fixture
def french(db) -> Language:
    return Language.objects.create(code="fr", name="Français")


@pytest.mark.django_db
def test_belgium_calculator_unavailable_when_no_sources(belgium_jurisdiction, french):
    from apps.calculators.engines.belgium import BelgiumRoadAccidentBodilyInjuryCalculator

    calc = BelgiumRoadAccidentBodilyInjuryCalculator(language="fr")
    r = calc.compute({"victim_age": 35, "permanent_disability_percentage": 10})
    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert r.estimated_min is None
    assert r.estimated_mid is None
    assert r.estimated_max is None


@pytest.mark.django_db
def test_belgium_calculator_unavailable_even_with_approved_source(
    belgium, belgium_jurisdiction, french
):
    """Anche con LegalSource approved, il placeholder NON inventa importi."""
    from apps.calculators.engines.belgium import BelgiumRoadAccidentBodilyInjuryCalculator

    LegalSource.objects.create(
        slug="be-fake-source-for-test",
        title="Fake BE source (test stub, never real values)",
        country=belgium,
        jurisdiction=belgium_jurisdiction,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
    )

    calc = BelgiumRoadAccidentBodilyInjuryCalculator(language="fr")
    r = calc.compute({"victim_age": 35, "permanent_disability_percentage": 10})
    assert r.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert r.estimated_min is None
    assert r.estimated_mid is None
    assert r.estimated_max is None
    assert len(r.sources) >= 1
    assert any(s.country == "BE" for s in r.sources)
    assert "calculator_engine_pending_for_jurisdiction" in r.missing_documents


# ---------------------------------------------------------------------------
# Regressione: Italy + France calculators non rotti dall'aggiunta BE
# ---------------------------------------------------------------------------


def test_italy_calculator_still_registered_after_belgium_scaffold():
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    cls = get_calculator("IT-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is ItalyRoadAccidentBodilyInjuryCalculator


def test_france_calculator_still_registered_after_belgium_scaffold():
    from apps.calculators.engines.france import FranceRoadAccidentBodilyInjuryCalculator

    cls = get_calculator("FR-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is FranceRoadAccidentBodilyInjuryCalculator


# ---------------------------------------------------------------------------
# Seed Belgium: needs_review only, idempotent
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_belgium_legal_sources_creates_needs_review_only():
    from io import StringIO

    call_command("seed_belgium_legal_sources", "--quiet", stdout=StringIO())

    be_sources = LegalSource.objects.filter(country__code="BE")
    assert be_sources.exists()
    assert not be_sources.filter(status=SourceStatus.APPROVED).exists()
    assert be_sources.filter(status=SourceStatus.NEEDS_REVIEW).exists()
    expected_slugs = {
        "be-loi-1989-11-21-assurance-rc-auto",
        "be-code-civil-art-1382-1383",
        "be-tableau-indicatif-cours-tribunaux-2020",
        "be-bareme-capitalisation-schryvers-2020",
    }
    assert expected_slugs.issubset(set(be_sources.values_list("slug", flat=True)))


@pytest.mark.django_db
def test_seed_belgium_idempotent_does_not_downgrade_approved():
    from io import StringIO

    call_command("seed_belgium_legal_sources", "--quiet", stdout=StringIO())

    source = LegalSource.objects.get(slug="be-loi-1989-11-21-assurance-rc-auto")
    source.status = SourceStatus.APPROVED
    source.save(update_fields=["status"])

    call_command("seed_belgium_legal_sources", "--quiet", stdout=StringIO())
    source.refresh_from_db()
    assert source.status == SourceStatus.APPROVED
