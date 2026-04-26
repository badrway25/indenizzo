"""
`BaseCalculator` — classe astratta del motore.

Implementa il template method `compute()` con il contratto difensivo del
progetto:

  1. valida l'input (subclassi possono ridefinire `validate_input`);
  2. risolve le fonti `approved` via `services.find_approved_sources`;
  3. se non ci sono fonti, ritorna `unavailable_requires_legal_validation`
     SENZA inventare importi;
  4. se ci sono fonti, delega a `_compute_with_sources` (subclasse).

Le sottoclassi di F4 sono *placeholder*: anche quando trovano fonti,
NON producono numeri (vedi `engines.italy`). Le formule reali entreranno
in F5+ con coefficienti ricavati dai contenuti delle fonti.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Any, ClassVar

from apps.legal_sources.models import LegalSource

from ..disclaimer import get_disclaimer
from ..enums import CalculationStatus, CaseType, ConfidenceLevel
from ..schemas import BreakdownItem, CalculationResult, SourceRef
from ..services import find_approved_sources

DEFAULT_CURRENCY = "EUR"


class BaseCalculator(ABC):
    """Template method per i calculator paese × case_type."""

    # --- contratto di sottoclasse ---------------------------------------
    case_type: ClassVar[str]
    jurisdiction_code: ClassVar[str]
    required_source_types: ClassVar[tuple[str, ...]] = ()
    fallback_to_country: ClassVar[bool] = True

    # --- istanza ---------------------------------------------------------
    def __init__(self, *, simulation_id: str = "", language: str = "it") -> None:
        self.simulation_id = simulation_id
        self.language = (language or "it").lower()

    # --- entry point pubblico -------------------------------------------
    def compute(self, input_data: dict[str, Any] | None = None) -> CalculationResult:
        data = dict(input_data or {})

        validation_warnings = self.validate_input(data)
        if validation_warnings:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT,
                warnings=validation_warnings,
            )

        sources = self.resolve_sources()
        if not sources:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION,
                warnings=[
                    "No approved legal sources are available for this "
                    "jurisdiction/case type. The simulation cannot produce "
                    "an estimate without legally validated sources."
                ],
            )

        return self._compute_with_sources(data, sources)

    # --- hook per sottoclassi -------------------------------------------
    def validate_input(self, input_data: dict[str, Any]) -> list[str]:
        """
        Ritorna messaggi se l'input è insufficiente. Lista vuota = OK.

        Default: nessuna validazione (placeholder F4). Subclassi reali in
        F5+ controlleranno presenza di campi richiesti per il calcolo.
        """
        return []

    def resolve_sources(self) -> list[LegalSource]:
        country_code = self._infer_country_code() if self.fallback_to_country else None
        return find_approved_sources(
            jurisdiction_code=self.jurisdiction_code,
            country_code=country_code,
            source_types=list(self.required_source_types) or None,
        )

    @abstractmethod
    def _compute_with_sources(
        self, input_data: dict[str, Any], sources: list[LegalSource]
    ) -> CalculationResult:
        """Calcolo vero. Subclassi placeholder lo lasciano "unavailable"."""

    # --- helper interni --------------------------------------------------
    def _infer_country_code(self) -> str | None:
        """`IT-NATIONAL` → `IT`. `FR-PARIS` → `FR`. Vuoto se non parsabile."""
        if not self.jurisdiction_code:
            return None
        return self.jurisdiction_code.split("-", 1)[0] or None

    def get_currency(self) -> str:
        """
        Valuta del risultato. Deriva dalla `Jurisdiction.default_currency`,
        fallback `EUR`. Importazione lazy del modello per non rompere
        l'import del modulo se l'app non è ancora pronta (es. unit test
        di sole funzioni).
        """
        try:
            from apps.jurisdictions.models import Jurisdiction

            jurisdiction = (
                Jurisdiction.objects.select_related("default_currency")
                .filter(code=self.jurisdiction_code)
                .first()
            )
            if jurisdiction and jurisdiction.default_currency_id:
                return jurisdiction.default_currency.code
        except Exception:  # pragma: no cover — solo se DB non c'è
            pass
        return DEFAULT_CURRENCY

    def get_disclaimer(self) -> str:
        return get_disclaimer(self.language)

    def _build_result(
        self,
        *,
        status: str,
        estimated_min: Decimal | None = None,
        estimated_mid: Decimal | None = None,
        estimated_max: Decimal | None = None,
        breakdown: list[BreakdownItem] | None = None,
        sources: list[SourceRef] | None = None,
        assumptions: list[str] | None = None,
        warnings: list[str] | None = None,
        missing_documents: list[str] | None = None,
        confidence: str = ConfidenceLevel.LOW.value,
    ) -> CalculationResult:
        return CalculationResult(
            simulation_id=self.simulation_id,
            jurisdiction=self.jurisdiction_code,
            case_type=self.case_type,
            currency=self.get_currency(),
            status=status,
            estimated_min=estimated_min,
            estimated_mid=estimated_mid,
            estimated_max=estimated_max,
            breakdown=list(breakdown or []),
            sources=list(sources or []),
            assumptions=list(assumptions or []),
            warnings=list(warnings or []),
            missing_documents=list(missing_documents or []),
            confidence=confidence,
            legal_disclaimer=self.get_disclaimer(),
        )


# Esposto qui per comodità d'import dai test.
__all__ = ["BaseCalculator", "CaseType", "CalculationStatus", "ConfidenceLevel"]
