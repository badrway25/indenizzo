"""
Calculator France — scaffold (F-france-road-accident-bootstrap).

Scopo:
- registrare la coppia ``FR-NATIONAL × road_accident_bodily_injury`` nel
  registry dei calculator;
- garantire che, anche se chiamato dal funnel pubblico, il calculator
  restituisca SEMPRE ``unavailable_requires_legal_validation`` finché lo
  Studio non avrà promosso ``approved`` la fonte e il dataset
  corrispondenti.

Differenza vs Italia: nessun engine economico è ancora cablato. Quando
arriverà (Référentiel cours d'appel + barème de capitalisation, post
revisione legale dello Studio) potremo specializzare la classe sullo
stesso pattern di ``ItalyRoadAccidentBodilyInjuryCalculator`` —
gating a 4 livelli + ``apply_amount_rule``. Per ora il calculator NON
inventa nulla.

Output atteso del calculator pubblico, oggi:

  Stato                                    | output
  -----------------------------------------+--------------------------------
  Nessuna fonte FR approved                | unavailable, missing_documents=[]
  Fonti FR approved ma dataset/formula     | unavailable, motivo nel warning
  mancanti (futuro)                        |

Tutto JSON-serializzabile. Niente importi inventati. Niente compute()
che restituisca CALCULATED.
"""

from __future__ import annotations

from typing import Any

from apps.legal_sources.models import LegalSource

from ..enums import CalculationStatus, CaseType
from ..registry import register_calculator
from ..schemas import CalculationResult, SourceRef
from .base import BaseCalculator

JURISDICTION_CODE_FR = "FR-NATIONAL"


class _FrancePlaceholderCalculator(BaseCalculator):
    """Base placeholder per i calculator Francia (scaffold).

    Identico nel comportamento al placeholder Italia di F4 prima di
    F-italy-engine-implementation: con o senza fonti ``approved``, il
    calculator NON produce importi. Le fonti vengono ritornate come
    ``SourceRef`` per audit, ma lo status resta ``unavailable``.
    """

    jurisdiction_code = JURISDICTION_CODE_FR

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=[SourceRef.from_legal_source(s) for s in sources],
            warnings=[
                "France calculator engine not yet implemented for this case "
                "type. Even when approved legal sources will be present, the "
                "compute logic is pending Studio validation in a later phase."
            ],
            missing_documents=["calculator_engine_pending_for_jurisdiction"],
        )


class FranceRoadAccidentBodilyInjuryCalculator(_FrancePlaceholderCalculator):
    """France — accident de la circulation, dommages corporels (Loi Badinter)."""

    case_type = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value


# --- registrazioni al momento dell'import ----------------------------------
register_calculator(
    JURISDICTION_CODE_FR,
    CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    FranceRoadAccidentBodilyInjuryCalculator,
)
