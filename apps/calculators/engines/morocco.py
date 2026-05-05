"""Calculator Morocco — engine inattivo, scaffold pronto per fixture-only.

Iter:

- F-ma-tn-international-inheritance-bootstrap: registrazione del
  calculator + ritorno ``unavailable_requires_legal_validation``
  permanente.
- F-morocco-inheritance-engine-inactive-fixture-only: aggiunta del
  *path eseguibile* per il caso fixture-only (test DB con
  source/dataset/formula APPROVED). Sul DB pubblico nulla cambia:
  nessun ``LegalSource`` MA è ``APPROVED`` → il gating impedisce
  l'esecuzione e il calculator pubblico continua a restituire
  ``unavailable``.

Engine identity (registrato in ``apps.compensation.services.SUPPORTED_ENGINES``):

    "morocco_inheritance_v1"

Amount rule (registrata in
``apps.compensation.services.SUPPORTED_AMOUNT_RULES`` e nella sotto-
famiglia ``INHERITANCE_SHARE_AMOUNT_RULES``):

    "morocco_inheritance_fixed_share_direct"

Schema atteso di ``CalculationFormula.parameters`` per attivare l'engine
quando lo Studio promuoverà sorgente + dataset (mapping Moudawana
Livre III + decisione su Reg. UE 650/2012):

    {
        "engine": "morocco_inheritance_v1",
        "amount_rule": "morocco_inheritance_fixed_share_direct",
        "requires": ["heirs"],
        "shares": {
            "spouse":          "1/8",
            "father":          "1/6",
            "mother":          "1/6",
            "sons_group":      "remainder_2_to_1",
            "daughters_group": "remainder_2_to_1"
        }
    }

NOTE — non è una codifica giuridica completa: i ``faraïd`` reali
includono hajb (esclusioni), 'awl (riduzione proporzionale quando le
quote fisse superano l'unità), radd (devoluzione del residuo) e una
tassonomia di status familiari ben più ricca. La rule attuale serve a
preparare la struttura tecnica per future formule legal-reviewed; il
calculator pubblico resta inattivo finché lo Studio non avrà mappato
Livre III in tabelle promovibili.

Ordine di valutazione (specchia France/Belgium):

  1. nessuna fonte approvata             → UNAVAILABLE
  2. nessun dataset approvato            → UNAVAILABLE (compensation_dataset_approved)
  3. nessuna formula approvata           → UNAVAILABLE (calculation_formula_approved)
  4. engine ignoto                       → UNAVAILABLE (formula_engine_unknown)
  5. amount_rule ignota                  → UNAVAILABLE (formula_amount_rule_unknown)
  6. amount_rule non inheritance-share   → UNAVAILABLE (formula_amount_rule_not_inheritance_share)
  7. input minimi mancanti               → INSUFFICIENT_INPUT
  8. estate_value invalido (negativo)    → INSUFFICIENT_INPUT
  9. nessuna allocazione (heirs vuoti)   → INSUFFICIENT_INPUT
  10. tutto ok                           → CALCULATED
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.legal_sources.models import LegalSource

from ..enums import CalculationStatus, CaseType, ConfidenceLevel
from ..registry import register_calculator
from ..schemas import BreakdownItem, CalculationResult, SourceRef
from .base import BaseCalculator

JURISDICTION_CODE_MA = "MA-NATIONAL"


class _MoroccoPlaceholderCalculator(BaseCalculator):
    """Base placeholder per i calculator Marocco non ancora cablati."""

    jurisdiction_code = JURISDICTION_CODE_MA

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=[SourceRef.from_legal_source(s) for s in sources],
            warnings=[
                "Morocco calculator engine not yet implemented for this case "
                "type. Inheritance shares (faraïd) under Moudawana require "
                "Studio legal validation before any computation can be "
                "exposed publicly."
            ],
            missing_documents=["calculator_engine_pending_for_jurisdiction"],
        )


class MoroccoInternationalInheritanceCalculator(_MoroccoPlaceholderCalculator):
    """Maroc — succession internationale (engine inattivo, fixture-only).

    Esegue il calcolo SOLO se tutte le condizioni di gating sono
    soddisfatte: fonte ``approved``, dataset ``approved``, formula
    ``approved`` con engine ``morocco_inheritance_v1``, ``shares`` spec
    valida e heirs presenti. Sul DB pubblico oggi le fonti MA sono
    ``needs_review`` quindi il gating fallisce al primo livello e il
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
        # Lazy import: evita dipendency edge statico fra apps.calculators
        # e apps.compensation. Stesso pattern di Italy/France/Belgium.
        from apps.compensation.services import (
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
                    "Approved legal sources are present, but no approved "
                    "compensation dataset is linked to them for MA "
                    "international inheritance. The Moudawana Livre III "
                    "candidate dataset must be promoted to APPROVED by a "
                    "Studio reviewer before any estimate can be produced."
                ],
                missing_documents=["compensation_dataset_approved"],
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

        # --- gate 6: only inheritance-share rules supported by MA engine
        rule = params.get("amount_rule")
        if not is_inheritance_share_rule(rule):
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    f"Approved formula declares amount_rule={rule!r}, but the "
                    "MA engine only supports inheritance-share rules today "
                    "(morocco_inheritance_fixed_share_direct). Other rule "
                    "families do not apply to inheritance allocation."
                ],
                missing_documents=["formula_amount_rule_not_inheritance_share"],
            )

        # --- gate 7: input minimi richiesti dalla formula
        required = params.get("requires") or []
        missing_inputs = [field for field in required if not _has_value(input_data, field)]
        if missing_inputs:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[
                    "Required input fields are missing for this calculation: "
                    + ", ".join(missing_inputs)
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

        # --- step 10: dispatch della rule inheritance-share
        share_result = apply_amount_inheritance_share_rule(
            rule,
            formula_params=params,
            input_data=input_data,
        )

        # --- gate 9: heirs vuoti / nessuna allocazione → insufficient
        if not share_result.allocations:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[
                    "No heir class with a positive head count matches the "
                    "approved share specification. Provide at least one "
                    "heir (spouse / father / mother / sons / daughters) "
                    "covered by the formula."
                ],
            )

        # --- step 10: build breakdown + result
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

        # Totale allocato (somma delle quote convertite in importi). Quando
        # ``estate_value`` è fornito e lo spec copre l'intera unità, la
        # somma coincide con l'estate. La esponiamo come estimated_min/
        # mid/max (collapse to scalar): inheritance non ha fourchette in
        # questa rule fixture-only.
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
    # helpers privati (specchio di quelli France/Belgium, riadattati a MA)
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
                    "Approved compensation dataset is present, but no "
                    "approved calculation formula is linked to it. The MA "
                    "formula must be validated by a legal reviewer before "
                    "any estimate can be produced."
                ],
                missing_documents=["calculation_formula_approved"],
            )
        if status == FormulaResolutionStatus.ENGINE_UNKNOWN:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    "An approved formula exists but its `engine` is not "
                    "registered in the MA calculator's supported list "
                    "(expected 'morocco_inheritance_v1')."
                ],
                missing_documents=["formula_engine_unknown"],
            )
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=source_refs,
            warnings=[
                "An approved formula exists with a recognised engine, but "
                "its `amount_rule` is not registered in the MA calculator's "
                "supported list."
            ],
            missing_documents=["formula_amount_rule_unknown"],
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


# --- registrazioni al momento dell'import ----------------------------------
register_calculator(
    JURISDICTION_CODE_MA,
    CaseType.INTERNATIONAL_INHERITANCE.value,
    MoroccoInternationalInheritanceCalculator,
)
