"""
Tests F-sources-italy — apps.compensation.

Verifichiamo i vincoli strutturali sui dataset di compensazione:
- un dataset APPROVED richiede una fonte APPROVED;
- una formula APPROVED richiede un dataset APPROVED;
- la creazione di un dataset DRAFT è sempre permessa, anche con fonte
  in `needs_review`;
- valid_to deve essere ≥ valid_from;
- nessun valore monetario reale è hardcoded nei test (regola d'oro).

NESSUN test usa importi o coefficienti reali. I `Decimal` qui sono
volutamente segnaposto sintattici per validare la persistenza, mai per
rappresentare un valore legale.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.calculators.enums import CaseType
from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
)
from apps.jurisdictions.models import Country, Jurisdiction
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource


@pytest.fixture
def italy(db) -> Country:
    return Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")


@pytest.fixture
def italy_jurisdiction(db, italy: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


def _approved_source(italy, italy_jurisdiction, italian_language=None):
    from apps.jurisdictions.models import Language

    language = italian_language or Language.objects.create(code="it", name="Italiano")
    return LegalSource.objects.create(
        title="D.P.R. placeholder per test",
        country=italy,
        jurisdiction=italy_jurisdiction,
        language=language,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
    )


def _needs_review_source(italy, italy_jurisdiction):
    return LegalSource.objects.create(
        title="Fonte in revisione",
        country=italy,
        jurisdiction=italy_jurisdiction,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.NEEDS_REVIEW,
    )


# ---------------------------------------------------------------------------
# CompensationDataset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_compensation_dataset_default_status_is_draft(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Placeholder dataset",
    )
    assert dataset.status == DatasetStatus.DRAFT
    assert dataset.is_usable_for_calculations is False


@pytest.mark.django_db
def test_dataset_cannot_be_approved_if_source_is_not_approved(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Premature approval",
        status=DatasetStatus.APPROVED,
    )
    with pytest.raises(ValidationError) as exc:
        dataset.full_clean()
    assert "status" in exc.value.error_dict


@pytest.mark.django_db
def test_dataset_can_be_approved_when_source_is_approved(italy, italy_jurisdiction):
    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Validly approved",
        status=DatasetStatus.APPROVED,
    )
    # Non deve sollevare.
    dataset.full_clean()
    dataset.save()
    assert dataset.is_usable_for_calculations is True


@pytest.mark.django_db
def test_dataset_valid_to_must_be_gte_valid_from(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Bad date range",
        valid_from=date(2025, 6, 1),
        valid_to=date(2025, 1, 1),
    )
    with pytest.raises(ValidationError) as exc:
        dataset.full_clean()
    assert "valid_to" in exc.value.error_dict


# ---------------------------------------------------------------------------
# CompensationTableRow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_table_row_age_max_must_be_gte_age_min(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Dataset with rows",
    )
    row = CompensationTableRow(
        dataset=dataset,
        age_min=40,
        age_max=20,
    )
    with pytest.raises(ValidationError) as exc:
        row.full_clean()
    assert "age_max" in exc.value.error_dict


@pytest.mark.django_db
def test_table_row_disability_max_must_be_gte_disability_min(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Dataset with rows",
    )
    row = CompensationTableRow(
        dataset=dataset,
        disability_min=30,
        disability_max=10,
    )
    with pytest.raises(ValidationError) as exc:
        row.full_clean()
    assert "disability_max" in exc.value.error_dict


@pytest.mark.django_db
def test_table_row_can_persist_decimal_placeholders(italy, italy_jurisdiction):
    """
    Persistenza tecnica di valori decimal: la struttura accetta numeri.
    NON è un test su importi reali — i Decimal qui sono segnaposto.
    """
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Dataset for placeholder",
    )
    row = CompensationTableRow.objects.create(
        dataset=dataset,
        row_type="placeholder_only",
        point_value=Decimal("1.0000"),
        coefficient=Decimal("1.000000"),
    )
    row.full_clean()
    assert row.dataset_id == dataset.pk


# ---------------------------------------------------------------------------
# CalculationFormula
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_formula_cannot_be_approved_when_dataset_is_not(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Draft dataset",
    )
    formula = CalculationFormula(
        dataset=dataset,
        code="placeholder_formula",
        name="Placeholder formula",
        status=DatasetStatus.APPROVED,
    )
    with pytest.raises(ValidationError) as exc:
        formula.full_clean()
    assert "status" in exc.value.error_dict


@pytest.mark.django_db
def test_formula_can_be_approved_when_dataset_is_approved(italy, italy_jurisdiction):
    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Approved dataset",
        status=DatasetStatus.APPROVED,
    )
    formula = CalculationFormula(
        dataset=dataset,
        code="placeholder_formula",
        name="Placeholder formula",
        status=DatasetStatus.APPROVED,
    )
    formula.full_clean()
    formula.save()
    assert formula.pk is not None


@pytest.mark.django_db
def test_formula_unique_code_per_dataset(italy, italy_jurisdiction):
    from django.db import IntegrityError

    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Dataset with formulas",
    )
    CalculationFormula.objects.create(dataset=dataset, code="dup_code", name="First")
    with pytest.raises(IntegrityError):
        CalculationFormula.objects.create(dataset=dataset, code="dup_code", name="Second")


# ---------------------------------------------------------------------------
# Calculator non sblocca importi senza dataset approvato
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_calculator_with_approved_source_but_no_dataset_remains_unavailable(
    italy, italy_jurisdiction
):
    """
    Anche con fonte APPROVED, in assenza di dataset/formule APPROVED il
    calculator placeholder italiano resta `unavailable_requires_legal_validation`.
    Conferma che l'esistenza della fonte da sola NON sblocca importi.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    _approved_source(italy, italy_jurisdiction)
    # Nessun CompensationDataset creato.

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})

    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.estimated_min is None
    assert result.estimated_mid is None
    assert result.estimated_max is None


@pytest.mark.django_db
def test_dataset_with_draft_status_does_not_unlock_calculation(italy, italy_jurisdiction):
    """
    Anche con fonte APPROVED + dataset esistente ma in DRAFT, il
    calculator non produce importi (il placeholder F4 non li produce
    neanche con dataset, e quando arriverà l'engine reale leggerà solo
    `is_usable_for_calculations` == True).
    """
    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Draft dataset",
        status=DatasetStatus.DRAFT,
    )
    assert dataset.is_usable_for_calculations is False


# ---------------------------------------------------------------------------
# Coerenza temporale dataset vs source
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dataset_validity_window_can_predate_today(italy, italy_jurisdiction):
    """
    Un dataset può avere `valid_from` antecedente a oggi: serve per
    simulazioni datate. Test puramente strutturale, nessun importo.
    """
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Past dataset",
        valid_from=date.today() - timedelta(days=365),
        valid_to=date.today() - timedelta(days=1),
    )
    dataset.full_clean()
    assert dataset.valid_to < date.today()
