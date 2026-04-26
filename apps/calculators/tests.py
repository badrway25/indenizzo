"""
Tests F4 — apps.calculators.

Coprono il contratto difensivo del motore:
- registry: register/get/missing/list/clear;
- output schema: JSON serializzabile, disclaimer sempre presente;
- compute(): no fonti → unavailable, draft non abilita, approved sblocca
  resolve ma il placeholder non inventa importi;
- source resolver: usa `LegalSource.objects.approved()` e fallback
  jurisdiction → country;
- currency derivata da `Jurisdiction.default_currency`;
- case_type non registrato → registry restituisce None (no crash).
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from decimal import Decimal

import pytest

from apps.calculators.disclaimer import LEGAL_DISCLAIMERS, get_disclaimer
from apps.calculators.engines.base import BaseCalculator
from apps.calculators.engines.italy import (
    ItalyInheritanceBasicCalculator,
    ItalyRoadAccidentBodilyInjuryCalculator,
)
from apps.calculators.enums import CalculationStatus, CaseType, ConfidenceLevel
from apps.calculators.exceptions import (
    CalculatorAlreadyRegistered,
    CalculatorNotRegistered,
    InvalidCalculatorClass,
)
from apps.calculators.registry import (
    CalculatorRegistry,
    get_calculator,
    list_available_calculators,
)
from apps.calculators.schemas import BreakdownItem, CalculationResult, SourceRef
from apps.calculators.services import find_approved_sources
from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource

# ---------------------------------------------------------------------------
# Disclaimer + schema
# ---------------------------------------------------------------------------


def test_disclaimer_supports_four_languages():
    assert {"it", "fr", "en", "ar"}.issubset(LEGAL_DISCLAIMERS.keys())
    for lang in ("it", "fr", "en", "ar"):
        text = get_disclaimer(lang)
        assert text and len(text) > 40


def test_disclaimer_falls_back_to_italian():
    assert get_disclaimer("xx") == LEGAL_DISCLAIMERS["it"]
    assert get_disclaimer(None) == LEGAL_DISCLAIMERS["it"]


def test_calculation_result_is_json_serializable():
    result = CalculationResult(
        simulation_id="sim-1",
        jurisdiction="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        currency="EUR",
        status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
        legal_disclaimer=get_disclaimer("it"),
    )
    payload = json.loads(result.to_json())
    assert payload["simulation_id"] == "sim-1"
    assert payload["estimated_min"] is None
    assert payload["estimated_mid"] is None
    assert payload["estimated_max"] is None
    assert payload["legal_disclaimer"]
    assert payload["status"] == "unavailable_requires_legal_validation"
    assert payload["confidence"] == ConfidenceLevel.LOW.value
    assert payload["breakdown"] == []
    assert payload["sources"] == []


def test_calculation_result_preserves_decimal_precision():
    item = BreakdownItem(
        label="placeholder",
        amount_min=Decimal("1234.56"),
        amount_mid=Decimal("2345.67"),
        amount_max=Decimal("3456.78"),
    )
    payload = item.to_dict()
    # Conversione via str preserva la precisione, niente float drift.
    assert payload["amount_min"] == "1234.56"
    assert payload["amount_mid"] == "2345.67"
    assert payload["amount_max"] == "3456.78"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


class _DummyCalculator(BaseCalculator):
    case_type = "dummy_case"
    jurisdiction_code = "XX-DUMMY"

    def _compute_with_sources(self, input_data, sources):  # pragma: no cover
        return self._build_result(status=CalculationStatus.CALCULATED.value)


def test_registry_register_and_get():
    reg = CalculatorRegistry()
    reg.register("XX-DUMMY", "dummy_case", _DummyCalculator)
    assert reg.get("XX-DUMMY", "dummy_case") is _DummyCalculator
    # Case-insensitive su jurisdiction, case-sensitive su case_type.
    assert reg.get("xx-dummy", "dummy_case") is _DummyCalculator
    assert reg.get("XX-DUMMY", "other_case") is None


def test_registry_rejects_non_calculator_class():
    reg = CalculatorRegistry()
    with pytest.raises(InvalidCalculatorClass):
        reg.register("XX-DUMMY", "dummy_case", object)


def test_registry_rejects_duplicate_registration():
    reg = CalculatorRegistry()
    reg.register("XX-DUMMY", "dummy_case", _DummyCalculator)
    with pytest.raises(CalculatorAlreadyRegistered):
        reg.register("XX-DUMMY", "dummy_case", _DummyCalculator)


def test_registry_replace_allows_overwrite():
    reg = CalculatorRegistry()
    reg.register("XX-DUMMY", "dummy_case", _DummyCalculator)
    reg.register("XX-DUMMY", "dummy_case", _DummyCalculator, replace=True)
    assert reg.get("XX-DUMMY", "dummy_case") is _DummyCalculator


def test_registry_require_raises_when_missing():
    reg = CalculatorRegistry()
    with pytest.raises(CalculatorNotRegistered):
        reg.require("XX-DUMMY", "missing_case")


def test_registry_get_missing_returns_none_no_crash():
    """case_type non supportato non deve crashare: ritorna None."""
    assert get_calculator("ZZ-NOPE", "totally_missing_case") is None


def test_global_registry_has_italy_placeholders():
    """All'import di engines.italy le due classi sono già registrate."""
    available = list_available_calculators()
    assert ("IT-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value) in available
    assert ("IT-NATIONAL", CaseType.INHERITANCE_BASIC.value) in available

    cls = get_calculator("IT-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    assert cls is ItalyRoadAccidentBodilyInjuryCalculator


# ---------------------------------------------------------------------------
# compute() — fonti, fallback, currency
# ---------------------------------------------------------------------------


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


@pytest.mark.django_db
def test_compute_returns_unavailable_without_approved_sources(italy_setup):
    calc = ItalyRoadAccidentBodilyInjuryCalculator(simulation_id="sim-1")
    result = calc.compute({})

    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.estimated_min is None
    assert result.estimated_mid is None
    assert result.estimated_max is None
    assert result.legal_disclaimer  # sempre presente
    assert result.warnings  # almeno un warning esplicativo
    assert result.sources == []


@pytest.mark.django_db
def test_compute_draft_source_does_not_unlock_calculation(italy_setup):
    LegalSource.objects.create(
        title="Fonte in bozza",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.DRAFT,  # non approved
    )
    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})
    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.sources == []


@pytest.mark.django_db
def test_compute_with_approved_source_resolves_but_placeholder_does_not_invent(
    italy_setup,
):
    """
    Anche con fonte approved la classe placeholder F4 NON inventa importi:
    `estimated_*` restano None e lo `status` resta unavailable, ma la
    fonte appare in `sources` per audit.
    """
    LegalSource.objects.create(
        title="Codice Assicurazioni Private (placeholder)",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        publication_date=date.today() - timedelta(days=30),
    )
    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})

    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.estimated_min is None
    assert result.estimated_mid is None
    assert result.estimated_max is None
    assert len(result.sources) == 1
    assert result.sources[0].title.startswith("Codice Assicurazioni Private")
    assert result.warnings  # spiegazione "engine not yet implemented"


@pytest.mark.django_db
def test_compute_currency_derives_from_jurisdiction(italy_setup):
    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})
    assert result.currency == "EUR"


@pytest.mark.django_db
def test_compute_currency_falls_back_when_jurisdiction_missing():
    """Senza Jurisdiction in DB il calculator usa EUR di default."""
    calc = ItalyInheritanceBasicCalculator()
    result = calc.compute({})
    assert result.currency == "EUR"


@pytest.mark.django_db
def test_compute_output_is_json_serializable_in_real_run(italy_setup):
    LegalSource.objects.create(
        title="Fonte approved",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="fr")
    result = calc.compute({})
    payload = json.loads(result.to_json())
    assert payload["legal_disclaimer"] == LEGAL_DISCLAIMERS["fr"]
    assert payload["jurisdiction"] == "IT-NATIONAL"
    assert payload["case_type"] == CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
    assert payload["status"] == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


# ---------------------------------------------------------------------------
# Source resolver
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_find_approved_sources_uses_approved_manager(italy_setup):
    LegalSource.objects.create(
        title="Approved",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    LegalSource.objects.create(
        title="Draft",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.DRAFT,
    )

    found = find_approved_sources(jurisdiction_code="IT-NATIONAL")
    titles = [s.title for s in found]
    assert "Approved" in titles
    assert "Draft" not in titles


@pytest.mark.django_db
def test_find_approved_sources_falls_back_to_country(italy_setup):
    """Una fonte taggata solo `country` (no jurisdiction) è raggiungibile via fallback."""
    LegalSource.objects.create(
        title="National-level only",
        country=italy_setup["country"],
        jurisdiction=None,
        language=italy_setup["language"],
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    found = find_approved_sources(jurisdiction_code="IT-NATIONAL", country_code="IT")
    assert len(found) == 1
    assert found[0].title == "National-level only"


@pytest.mark.django_db
def test_find_approved_sources_filters_by_source_type(italy_setup):
    LegalSource.objects.create(
        title="Tabella corte",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.COURT_TABLE,
        status=SourceStatus.APPROVED,
    )
    LegalSource.objects.create(
        title="Linea guida",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.ADMINISTRATIVE_GUIDELINE,
        status=SourceStatus.APPROVED,
    )
    only_tables = find_approved_sources(
        jurisdiction_code="IT-NATIONAL",
        source_types=[SourceType.COURT_TABLE],
    )
    assert [s.title for s in only_tables] == ["Tabella corte"]


@pytest.mark.django_db
def test_source_ref_from_legal_source_snapshot(italy_setup):
    source = LegalSource.objects.create(
        title="X",
        country=italy_setup["country"],
        jurisdiction=italy_setup["jurisdiction"],
        language=italy_setup["language"],
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        publication_date=date(2024, 1, 15),
    )
    ref = SourceRef.from_legal_source(source)
    assert ref.id == source.pk
    assert ref.country == "IT"
    assert ref.jurisdiction == "IT-NATIONAL"
    assert ref.language == "it"
    assert ref.publication_date == "2024-01-15"
