"""Calculator Tunisia — engine inattivo, scaffold pronto per fixture-only.

Iter:

- F-ma-tn-international-inheritance-bootstrap: registrazione del
  calculator + ritorno ``unavailable_requires_legal_validation``
  permanente.
- F-tunisia-inheritance-engine-inactive-fixture-only: aggiunta del
  *path eseguibile* per il caso fixture-only (test DB con
  source/dataset/formula APPROVED). Sul DB pubblico nulla cambia:
  nessun ``LegalSource`` TN è ``APPROVED`` → il gating impedisce
  l'esecuzione e il calculator pubblico continua a restituire
  ``unavailable``.

Engine identity (registrato in ``apps.compensation.services.SUPPORTED_ENGINES``):

    "tunisia_inheritance_v1"

Amount rule (registrata in
``apps.compensation.services.SUPPORTED_AMOUNT_RULES`` e nella sotto-
famiglia ``INHERITANCE_SHARE_AMOUNT_RULES``):

    "tunisia_inheritance_fixed_share_direct"

Schema atteso di ``CalculationFormula.parameters`` per attivare l'engine
quando lo Studio promuoverà sorgente + dataset (mapping Code du statut
personnel Livre IX + Loi n° 98-97 + decisione su Reg. UE 650/2012):

    {
        "engine": "tunisia_inheritance_v1",
        "amount_rule": "tunisia_inheritance_fixed_share_direct",
        "requires": ["heirs"],
        "shares": {
            "spouse":          "1/8",
            "mother":          "1/6",
            "sons_group":      "remainder_2_to_1",
            "daughters_group": "remainder_2_to_1"
        }
    }

NOTE — non è una codifica giuridica completa: il diritto tunisino delle
successioni include 'awl, radd, hajb e una tassonomia famigliare ricca
che questa rule non modella. La rule attuale serve a preparare la
struttura tecnica per future formule legal-reviewed; il calculator
pubblico resta inattivo finché lo Studio non avrà mappato CSP Livre IX
(coordinato con la Loi n° 98-97 di diritto internazionale privato).

Ordine di valutazione (specchia France/Belgium/Morocco):

  1. nessuna fonte approvata             → UNAVAILABLE
  2. nessun dataset approvato            → UNAVAILABLE (compensation_dataset_approved)
  3. nessuna formula approvata           → UNAVAILABLE (calculation_formula_approved)
  4. engine ignoto                       → UNAVAILABLE (formula_engine_unknown)
  5. amount_rule ignota                  → UNAVAILABLE (formula_amount_rule_unknown)
  6. amount_rule non inheritance-share   → UNAVAILABLE (formula_amount_rule_not_inheritance_share)
  7. input minimi mancanti               → INSUFFICIENT_INPUT
  8. estate_value invalido (negativo)    → INSUFFICIENT_INPUT
  9. share spec strutturalmente invalida → UNAVAILABLE (shares_spec_invalid)
 10. nessuna allocazione (heirs vuoti)   → INSUFFICIENT_INPUT
 11. tutto ok                            → CALCULATED
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.legal_sources.models import LegalSource

from .. import diagnostics as _diag
from ..enums import CalculationStatus, CaseType, ConfidenceLevel
from ..registry import register_calculator
from ..schemas import BreakdownItem, CalculationResult, SourceRef
from .base import BaseCalculator

JURISDICTION_CODE_TN = "TN-NATIONAL"


class _TunisiaPlaceholderCalculator(BaseCalculator):
    """Base placeholder per i calculator Tunisia non ancora cablati."""

    jurisdiction_code = JURISDICTION_CODE_TN

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=[SourceRef.from_legal_source(s) for s in sources],
            warnings=[_diag.diagnostic_to_internal_warning(_diag.CALCULATOR_ENGINE_PENDING)],
            missing_documents=[_diag.CALCULATOR_ENGINE_PENDING],
        )


class TunisiaInternationalInheritanceCalculator(_TunisiaPlaceholderCalculator):
    """Tunisie — succession internationale (engine inattivo, fixture-only).

    Esegue il calcolo SOLO se tutte le condizioni di gating sono
    soddisfatte: fonte ``approved``, dataset ``approved``, formula
    ``approved`` con engine ``tunisia_inheritance_v1``, ``shares`` spec
    valida e heirs presenti. Sul DB pubblico oggi nessuna fonte TN è
    ``APPROVED`` quindi il gating fallisce al primo livello e il
    calcolatore restituisce ``unavailable``. Solo i test fixture-only
    seedano sorgenti+dataset+formula APPROVED in test DB per esercitare
    il path eseguibile.
    """

    case_type = CaseType.INTERNATIONAL_INHERITANCE.value

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        # Lazy import: stesso pattern di Italy/France/Belgium/Morocco.
        from apps.compensation.services import (
            InvalidInheritanceShareSpec,
            apply_amount_inheritance_share_rule,
            get_approved_dataset_for_sources,
            get_executable_formula,
            is_inheritance_share_rule,
        )

        source_refs = [SourceRef.from_legal_source(s) for s in sources]

        # --- gate 2: dataset approved ---------------------------------
        dataset = get_approved_dataset_for_sources(sources, self.case_type)
        if dataset is None:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_DATASET_NOT_APPROVED)
                ],
                missing_documents=[_diag.COMPENSATION_DATASET_NOT_APPROVED],
            )

        # --- gate 3 + 4 + 5: formula approved + engine + amount_rule
        resolution = get_executable_formula(dataset)
        if resolution.formula is None:
            return self._unavailable_for_formula_status(
                source_refs=source_refs,
                status=resolution.status,
            )

        formula = resolution.formula
        params = formula.parameters or {}

        # --- gate 6: only inheritance-share rules supported by TN engine
        rule = params.get("amount_rule")
        if not is_inheritance_share_rule(rule):
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(
                        _diag.FORMULA_AMOUNT_RULE_NOT_INHERITANCE_SHARE
                    )
                ],
                missing_documents=[_diag.FORMULA_AMOUNT_RULE_NOT_INHERITANCE_SHARE],
            )

        # --- gate 7: input minimi richiesti dalla formula
        required = params.get("requires") or []
        missing_inputs = [field for field in required if not _has_value(input_data, field)]
        if missing_inputs:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_public_warning(
                        _diag.ITALY_REQUIRED_INPUT_MISSING,
                        context={"fields": tuple(missing_inputs)},
                    )
                ],
            )

        # --- gate 8: estate_value (se fornito) deve essere non-negativo
        estate_warning = _validate_estate_value(input_data)
        if estate_warning:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[estate_warning],
            )

        # --- gate 9a: applicable-law decision skeleton (fixture-only).
        # Twin of the Morocco gate: even with an APPROVED stack, the
        # engine refuses to compute when the decision flags manual
        # review, insufficient context, low confidence or a missing
        # preliminary law country.
        block = _gate_inheritance_engine_on_applicable_law(input_data)
        if block is not None:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.APPLICABLE_LAW_REVIEW_REQUIRED)
                ],
                missing_documents=[block],
            )

        # --- gate 9b: dispatch della rule inheritance-share, intercetta
        #            spec strutturalmente invalida
        try:
            share_result = apply_amount_inheritance_share_rule(
                rule,
                formula_params=params,
                input_data=input_data,
            )
        except InvalidInheritanceShareSpec:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.INHERITANCE_SHARE_SPEC_INVALID)
                ],
                missing_documents=[_diag.INHERITANCE_SHARE_SPEC_INVALID],
            )

        # --- gate 10: heirs vuoti / nessuna allocazione → insufficient
        if not share_result.allocations:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[_diag.diagnostic_to_internal_warning(_diag.INPUT_NO_HEIR_ALLOCATION)],
            )

        # --- step 11: build breakdown + result
        breakdown: list[BreakdownItem] = []
        for alloc in share_result.allocations:
            breakdown.append(
                BreakdownItem(
                    label=(
                        f"{alloc.label} " f"({alloc.share_numerator}/{alloc.share_denominator})"
                    ),
                    amount_min=alloc.amount,
                    amount_mid=alloc.amount,
                    amount_max=alloc.amount,
                    formula=formula.code,
                    source_ref_ids=tuple(s.id for s in source_refs),
                    notes=(
                        f"Heir class={alloc.heir_class!r}, head_count="
                        f"{alloc.head_count}, share="
                        f"{alloc.share_numerator}/{alloc.share_denominator}."
                    ),
                )
            )

        total_allocated: Decimal | None
        if share_result.estate_total is None:
            total_allocated = None
        else:
            total_allocated = sum(
                (a.amount for a in share_result.allocations if a.amount is not None),
                Decimal(0),
            )

        assumptions = [
            f"Formula applied: {formula.code} ({rule}).",
            f"Source dataset: '{dataset.name}' (version '{dataset.version_label or 'n/a'}').",
        ]
        for alloc in share_result.allocations:
            assumptions.append(
                f"{alloc.label}: {alloc.share_numerator}/{alloc.share_denominator} "
                f"(head_count={alloc.head_count})."
            )

        warnings_out: list[str] = []
        if share_result.residual_numerator > 0:
            warnings_out.append(
                "A residual fraction of "
                f"{share_result.residual_numerator}/{share_result.residual_denominator} "
                "of the estate is not allocated by the approved share "
                "specification. Manual legal review is required to "
                "determine the recipient (radd, public treasury, "
                "applicable-law remand)."
            )
        if share_result.estate_total is None:
            warnings_out.append(
                "No estate_value provided — only fractional shares are "
                "shown. Provide estate_value to compute absolute amounts."
            )

        return self._build_result(
            status=CalculationStatus.CALCULATED.value,
            estimated_min=total_allocated,
            estimated_mid=total_allocated,
            estimated_max=total_allocated,
            breakdown=breakdown,
            sources=source_refs,
            assumptions=assumptions,
            warnings=warnings_out,
            confidence=ConfidenceLevel.LOW.value,
        )

    # ------------------------------------------------------------------
    # helpers privati (specchio di Morocco)
    # ------------------------------------------------------------------

    def _unavailable_for_formula_status(
        self,
        *,
        source_refs: list[SourceRef],
        status,
    ) -> CalculationResult:
        from apps.compensation.services import FormulaResolutionStatus

        if status == FormulaResolutionStatus.NO_APPROVED:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.CALCULATION_FORMULA_NOT_APPROVED)
                ],
                missing_documents=[_diag.CALCULATION_FORMULA_NOT_APPROVED],
            )
        if status == FormulaResolutionStatus.ENGINE_UNKNOWN:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[_diag.diagnostic_to_internal_warning(_diag.FORMULA_ENGINE_UNKNOWN)],
                missing_documents=[_diag.FORMULA_ENGINE_UNKNOWN],
            )
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=source_refs,
            warnings=[_diag.diagnostic_to_internal_warning(_diag.FORMULA_AMOUNT_RULE_UNKNOWN)],
            missing_documents=[_diag.FORMULA_AMOUNT_RULE_UNKNOWN],
        )


# ---------------------------------------------------------------------------
# helpers di modulo
# ---------------------------------------------------------------------------


def _has_value(input_data: dict[str, Any], field: str) -> bool:
    if field not in input_data:
        return False
    value = input_data[field]
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    if isinstance(value, dict) and not value:
        return False
    return True


def _validate_estate_value(input_data: dict[str, Any]) -> str | None:
    if "estate_value" not in input_data or input_data.get("estate_value") in (None, ""):
        return None
    raw = input_data["estate_value"]
    try:
        value = Decimal(str(raw))
    except Exception:
        return "estate_value is not a valid number."
    if value < Decimal(0):
        return "estate_value must be non-negative."
    return None


def _gate_inheritance_engine_on_applicable_law(input_data: dict[str, Any]) -> str | None:
    """Twin of the Morocco gate: route the engine to UNAVAILABLE when
    the pre-attached applicable-law decision blocks the share-engine
    path. See ``apps/calculators/engines/morocco.py`` for the full
    rationale.
    """
    from apps.calculators.inheritance_applicable_law import (
        ApplicableLawDecision,
        can_run_inheritance_share_engine,
        inheritance_engine_block_reason,
    )

    raw = input_data.get("applicable_law_decision")
    decision: ApplicableLawDecision | None = None
    if isinstance(raw, dict):
        try:
            decision = ApplicableLawDecision(
                decision_key=raw.get("decision_key", ""),
                preliminary_law_country=raw.get("preliminary_law_country"),
                confidence=raw.get("confidence", "low"),
                requires_manual_review=bool(raw.get("requires_manual_review")),
                reasons=tuple(raw.get("reasons") or ()),
                warnings=tuple(raw.get("warnings") or ()),
                applied_rules=tuple(raw.get("applied_rules") or ()),
            )
        except (TypeError, ValueError):
            decision = None
    if can_run_inheritance_share_engine(decision):
        return None
    return inheritance_engine_block_reason(decision)


# --- registrazioni al momento dell'import ----------------------------------
register_calculator(
    JURISDICTION_CODE_TN,
    CaseType.INTERNATIONAL_INHERITANCE.value,
    TunisiaInternationalInheritanceCalculator,
)
