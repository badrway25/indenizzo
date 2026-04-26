"""
Service layer per `apps.cases`.

`run_simulation` è il punto di ingresso unico per orchestrare:

  request utente → consenso → calculator → persistenza → audit privacy

Mai esposto direttamente a una view senza un layer di validazione: in
F6 (wizard) la view chiamerà questo service dopo aver verificato/registrato
il consenso GDPR.

Principio di non-crash: anche con calculator mancante, jurisdiction
sconosciuta o input vuoto, il service ritorna sempre una `Simulation`
persistita con `status=unavailable_requires_legal_validation`. Mai
un'eccezione bubble verso l'utente finale.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.calculators.disclaimer import get_disclaimer
from apps.calculators.enums import CalculationStatus, ConfidenceLevel
from apps.calculators.registry import get_calculator
from apps.calculators.schemas import CalculationResult
from apps.compliance.enums import PrivacyEventType
from apps.compliance.services import get_request_meta, log_privacy_event
from apps.jurisdictions.models import Jurisdiction

from .models import Simulation, SimulationEvent

logger = logging.getLogger(__name__)

DEFAULT_CURRENCY = "EUR"


@transaction.atomic
def run_simulation(
    *,
    jurisdiction_code: str,
    case_type: str,
    input_data: dict[str, Any] | None = None,
    request: Any | None = None,
    user: Any | None = None,
    consent_record: Any | None = None,
    locale: str = "it",
) -> Simulation:
    """
    Esegui una simulazione e persistila.

    NON solleva eccezioni in caso di calculator mancante o jurisdiction
    sconosciuta: la `Simulation` viene comunque salvata con status
    `unavailable_requires_legal_validation` e un warning esplicativo.
    """
    locale = (locale or "it").lower()
    payload = dict(input_data or {})

    jurisdiction = (
        Jurisdiction.objects.select_related("country", "default_currency")
        .filter(code=jurisdiction_code)
        .first()
    )

    simulation = Simulation(
        case_type=case_type,
        locale=locale,
        jurisdiction=jurisdiction,
        country=jurisdiction.country if jurisdiction else None,
        input_data=payload,
        consent_record=consent_record,
    )

    # Resolve user (preferenza esplicita, fallback request.user).
    resolved_user = _resolve_user(user, request)
    if resolved_user is not None:
        simulation.user = resolved_user

    # Metadata tecnici dalla request.
    meta = get_request_meta(request)
    simulation.session_key = meta.session_key
    simulation.ip_address = meta.ip_address
    simulation.user_agent = meta.user_agent
    simulation.source_path = meta.path

    # Calcolo.
    calc_cls = get_calculator(jurisdiction_code, case_type)
    result = _compute_or_unavailable(
        calc_cls=calc_cls,
        simulation=simulation,
        jurisdiction=jurisdiction,
        jurisdiction_code=jurisdiction_code,
        case_type=case_type,
        locale=locale,
        payload=payload,
    )

    _apply_result_to_simulation(simulation, result)
    simulation.save()

    # Audit interno (semantico).
    SimulationEvent.objects.create(
        simulation=simulation,
        event_type=SimulationEvent.EventType.COMPUTED,
        message=f"Simulation computed with status={simulation.status}.",
        metadata={
            "calculator_present": calc_cls is not None,
            "sources_count": len(result.sources),
            "warnings_count": len(result.warnings),
        },
    )

    # Audit privacy (cross-modello).
    log_privacy_event(
        event_type=PrivacyEventType.DATA_ACCESSED,
        request=request,
        actor=resolved_user,
        target_model="cases.Simulation",
        target_object_id=simulation.pk,
        metadata={"status": simulation.status, "case_type": case_type},
    )

    logger.info(
        "cases.simulation.created public_id=%s status=%s case_type=%s",
        simulation.public_id,
        simulation.status,
        case_type,
    )
    return simulation


def get_simulation_by_public_id(public_id: str) -> Simulation | None:
    """Lookup pubblico per UUID. None se non trovato."""
    return (
        Simulation.objects.select_related("jurisdiction", "country", "user")
        .filter(public_id=public_id)
        .first()
    )


@transaction.atomic
def anonymize_simulation(simulation: Simulation, *, request: Any | None = None) -> Simulation:
    """
    Rimuovi i dati personali da una simulazione.

    Mantiene `output_data`, `sources_snapshot`, `status`, `confidence`,
    `estimated_*` e `created_at` per audit/statistiche; cancella
    `input_data`, `session_key`, `ip_address`, `user_agent`,
    `source_path` e scollega `user`.
    """
    simulation.input_data = {"_anonymized": True}
    simulation.session_key = ""
    simulation.ip_address = None
    simulation.user_agent = ""
    simulation.source_path = ""
    simulation.user = None
    simulation.consent_record = None
    simulation.anonymized = True
    simulation.anonymized_at = timezone.now()
    simulation.save()

    SimulationEvent.objects.create(
        simulation=simulation,
        event_type=SimulationEvent.EventType.ANONYMIZED,
        message="Personal data removed from simulation (GDPR).",
        metadata={},
    )
    log_privacy_event(
        event_type=PrivacyEventType.DATA_DELETION_COMPLETED,
        request=request,
        target_model="cases.Simulation",
        target_object_id=simulation.pk,
        metadata={"trigger": "anonymize_simulation"},
    )
    return simulation


# ---------------------------------------------------------------------------
# helper interni
# ---------------------------------------------------------------------------


def _resolve_user(user: Any | None, request: Any | None) -> Any | None:
    if user is not None and getattr(user, "is_authenticated", False):
        return user
    if request is not None:
        candidate = getattr(request, "user", None)
        if candidate is not None and getattr(candidate, "is_authenticated", False):
            return candidate
    return None


def _compute_or_unavailable(
    *,
    calc_cls,
    simulation: Simulation,
    jurisdiction: Jurisdiction | None,
    jurisdiction_code: str,
    case_type: str,
    locale: str,
    payload: dict[str, Any],
) -> CalculationResult:
    """
    Orchestrazione del calcolo. Se il calculator non è registrato, costruisce
    un `CalculationResult` "unavailable" coerente, senza chiamare `compute()`.
    """
    if calc_cls is None:
        currency = (
            jurisdiction.default_currency.code
            if jurisdiction and jurisdiction.default_currency_id
            else DEFAULT_CURRENCY
        )
        return CalculationResult(
            simulation_id=str(simulation.public_id),
            jurisdiction=jurisdiction_code,
            case_type=case_type,
            currency=currency,
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            legal_disclaimer=get_disclaimer(locale),
            confidence=ConfidenceLevel.LOW.value,
            warnings=[
                "No calculator is registered for this jurisdiction/case type. "
                "The simulation cannot be performed automatically."
            ],
        )

    calculator = calc_cls(simulation_id=str(simulation.public_id), language=locale)
    return calculator.compute(payload)


def _apply_result_to_simulation(simulation: Simulation, result: CalculationResult) -> None:
    """
    Trascrive il `CalculationResult` sui campi della Simulation.
    `output_data` riceve il dump completo (per il report PDF futuro);
    `sources_snapshot` è una lista di dict per query veloci.
    """
    simulation.output_data = result.to_dict()
    simulation.sources_snapshot = [src.to_dict() for src in result.sources]
    simulation.status = result.status
    simulation.confidence = result.confidence
    simulation.currency = result.currency or DEFAULT_CURRENCY
    simulation.estimated_min = _to_decimal(result.estimated_min)
    simulation.estimated_mid = _to_decimal(result.estimated_mid)
    simulation.estimated_max = _to_decimal(result.estimated_max)


def _to_decimal(value) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))
