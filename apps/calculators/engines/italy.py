"""
Calculator placeholder per Italia con gating a 3 livelli.

F-extract-italy-tun aggiunge il **gating progressivo**:

  livello 1 — `LegalSource.approved` per la giurisdizione/case_type
  livello 2 — `CompensationDataset.approved` legato a quella fonte
  livello 3 — `CalculationFormula.approved` legata a quel dataset

Il calculator pubblico produce importi SOLO quando tutti e tre i
livelli sono soddisfatti. In F-extract-italy-tun il livello 3 non viene
mai raggiunto in pratica: l'estrazione tabellare e la legal review sono
attività umane che producono `approved` solo dopo verifica. Fino ad
allora, il calculator restituisce `unavailable_requires_legal_validation`
con un warning specifico ("manca formula approvata", ecc.) così che lo
Studio veda esattamente in quale punto del workflow è bloccato.

Quando in fase successiva il livello 3 sarà raggiunto, l'effettiva
matematica del calcolo verrà aggiunta in `_compute_economic_estimate`,
e SOLO ALLORA il calculator smetterà di restituire `unavailable`. Per
ora `_compute_economic_estimate` resta volutamente non implementato:
non vogliamo lasciare in piedi una path silenziosa che inventa numeri
appena un dataset venga (anche per errore) marcato `approved`.
"""

from __future__ import annotations

from typing import Any

from apps.legal_sources.models import LegalSource

from ..enums import CalculationStatus, CaseType
from ..registry import register_calculator
from ..schemas import CalculationResult, SourceRef
from .base import BaseCalculator

JURISDICTION_CODE_IT = "IT-NATIONAL"


class _ItalyPlaceholderCalculator(BaseCalculator):
    """Base placeholder per i calculator Italia."""

    jurisdiction_code = JURISDICTION_CODE_IT

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        # Anche con fonti `approved` presenti, NON inventiamo importi.
        # Restituiamo le fonti per audit ma teniamo `unavailable`.
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION,
            sources=[SourceRef.from_legal_source(s) for s in sources],
            warnings=[
                "Calculator engine not yet implemented for this case type. "
                "Approved legal sources are present but compute logic is "
                "pending validation in a later phase."
            ],
        )


class ItalyRoadAccidentBodilyInjuryCalculator(_ItalyPlaceholderCalculator):
    """
    Italia — incidente stradale, lesioni personali.

    Override del template per aggiungere il gating dataset/formula.
    Continua a NON produrre importi: l'engine economico verrà attivato
    in fase successiva, dopo che fonte + dataset + formula saranno
    `approved` *e* la matematica sarà stata implementata e testata.
    """

    case_type = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        source_refs = [SourceRef.from_legal_source(s) for s in sources]

        # Lazy import: apps.calculators non dipende staticamente da
        # apps.compensation. La dipendenza è opzionale e runtime-only.
        from apps.compensation.models import (
            CompensationDataset,
            DatasetStatus,
        )

        approved_dataset = (
            CompensationDataset.objects.filter(
                source__in=sources,
                case_type=self.case_type,
                status=DatasetStatus.APPROVED,
            )
            .select_related("source")
            .first()
        )

        if approved_dataset is None:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION,
                sources=source_refs,
                warnings=[
                    "Approved legal sources are present, but no approved "
                    "compensation dataset is linked to them. The "
                    "tabular extraction is in DRAFT/NEEDS_REVIEW and "
                    "must be validated by a legal reviewer before any "
                    "estimate can be produced."
                ],
                missing_documents=["compensation_dataset_approved"],
            )

        approved_formula = approved_dataset.formulas.filter(status=DatasetStatus.APPROVED).first()

        if approved_formula is None:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION,
                sources=source_refs,
                warnings=[
                    "Approved compensation dataset is present, but no "
                    "approved calculation formula is linked to it. The "
                    "formula must be validated by a legal reviewer "
                    "before any estimate can be produced."
                ],
                missing_documents=["calculation_formula_approved"],
            )

        # Tutti i tre livelli sono `approved`. In fase successiva qui
        # entrerà il vero engine economico, che leggerà
        # approved_dataset.rows e approved_formula. Per ora il punto
        # bloccante è esplicito: l'engine non è implementato, e
        # dichiararlo è meglio che inventare un importo.
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION,
            sources=source_refs,
            warnings=[
                "All three legal validation levels (source, dataset, "
                "formula) are APPROVED, but the economic engine is not "
                "yet implemented. No estimate will be produced until the "
                "matching computation is added and tested."
            ],
            missing_documents=["economic_engine_implementation"],
        )


class ItalyInheritanceBasicCalculator(_ItalyPlaceholderCalculator):
    """Italia — successione di base. Placeholder F4."""

    case_type = CaseType.INHERITANCE_BASIC.value


# --- registrazioni al momento dell'import ----------------------------------
register_calculator(
    JURISDICTION_CODE_IT,
    CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    ItalyRoadAccidentBodilyInjuryCalculator,
)
register_calculator(
    JURISDICTION_CODE_IT,
    CaseType.INHERITANCE_BASIC.value,
    ItalyInheritanceBasicCalculator,
)
