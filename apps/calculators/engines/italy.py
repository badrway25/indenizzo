"""
Calculator placeholder per Italia.

F4 — questi calculator esistono come *segnaposto architetturali*. Non
producono importi. Anche se trovano fonti `approved` per la propria
giurisdizione, restituiscono `unavailable_requires_legal_validation`
con un warning chiaro che indica "engine not yet implemented".

Le formule reali (Tabelle Milano per danno biologico, regole sulla
legittima per le successioni, ecc.) saranno cablate in F5+ dopo che
le fonti corrispondenti saranno caricate, validate e marcate `approved`.
Quel momento richiede un commit dedicato per ogni modulo, perché il
contenuto delle fonti dichiarerà coefficienti vincolanti per il calcolo.

Convenzione: se in futuro vogliamo blindare ulteriormente, possiamo
spostare il flag "non operativo" su un attributo `is_operational` letto
dal `BaseCalculator.compute()`. In F4 manteniamo il pattern semplice.
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
                "pending validation in a later phase (F5+)."
            ],
        )


class ItalyRoadAccidentBodilyInjuryCalculator(_ItalyPlaceholderCalculator):
    """Italia — incidente stradale, lesioni personali. Placeholder F4."""

    case_type = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value


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
