"""
Calculator Belgium — scaffold (F-belgium-road-accident-bootstrap).

Identico nel design al calculator Francia: registra la coppia
``BE-NATIONAL × road_accident_bodily_injury`` ma il
``_compute_with_sources`` non inventa importi e ritorna sempre
``unavailable_requires_legal_validation`` con missing-document
``calculator_engine_pending_for_jurisdiction``.

Il calcolatore reale richiederà:
- estrazione del Tableau indicatif des cours et tribunaux per voce di
  danno (incapacité temporaire totale, pretium doloris, dommage
  esthétique, perte de revenus, aide d'une tierce personne, ecc.);
- Barème de capitalisation Schryvers per la conversione delle rendite;
- nuova ``amount_rule`` registrata in ``SUPPORTED_AMOUNT_RULES`` di
  ``apps.compensation.services``;
- ``CalculationFormula`` approvata con ``parameters`` runtime;
- LegalReview umana e promozione cumulativa source → dataset →
  formula a ``approved``.

Fino ad allora il calculator NON inventa nulla.
"""

from __future__ import annotations

from typing import Any

from apps.legal_sources.models import LegalSource

from ..enums import CalculationStatus, CaseType
from ..registry import register_calculator
from ..schemas import CalculationResult, SourceRef
from .base import BaseCalculator

JURISDICTION_CODE_BE = "BE-NATIONAL"


class _BelgiumPlaceholderCalculator(BaseCalculator):
    """Base placeholder per i calculator Belgio (scaffold)."""

    jurisdiction_code = JURISDICTION_CODE_BE

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=[SourceRef.from_legal_source(s) for s in sources],
            warnings=[
                "Belgium calculator engine not yet implemented for this case "
                "type. Even when approved legal sources will be present, the "
                "compute logic is pending Studio validation in a later phase."
            ],
            missing_documents=["calculator_engine_pending_for_jurisdiction"],
        )


class BelgiumRoadAccidentBodilyInjuryCalculator(_BelgiumPlaceholderCalculator):
    """Belgium — accident de la circulation, dommages corporels."""

    case_type = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value


# --- registrazioni al momento dell'import ----------------------------------
register_calculator(
    JURISDICTION_CODE_BE,
    CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    BelgiumRoadAccidentBodilyInjuryCalculator,
)
