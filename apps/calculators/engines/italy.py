"""
Calculator Italia — engine economico con gating a 4 livelli.

F-italy-engine-implementation:

  livello 1 — `LegalSource.approved` per la giurisdizione/case_type
  livello 2 — `CompensationDataset.approved` legato a quella fonte
  livello 3 — `CalculationFormula.approved` con `engine` e `amount_rule`
              riconosciuti dal registro `apps.compensation.services`
  livello 4 — riga tabellare unica che soddisfa i predicati di matching

Il calculator pubblico produce importi SOLO quando tutti e quattro i
livelli passano. La differenza rispetto a F-extract-italy-tun è che, una
volta superati i 4 livelli, il calcolo viene davvero eseguito leggendo
i dati dal DB (mai da costanti hardcoded). I valori monetari vivono in
`CompensationTableRow.point_value`; la regola di applicazione vive in
`CalculationFormula.parameters.amount_rule`.

Schema atteso di `CalculationFormula.parameters` per il primo engine:

    {
        "engine": "italy_tun_point_value_v1",
        "requires": ["victim_age", "permanent_disability_percentage"],
        "row_match": ["victim_age", "permanent_disability_percentage"],
        "amount_rule": "point_value_times_disability_percentage",
        "fault_reduction": true | false
    }

Se la formula `parameters` non dichiara questi campi nel modo previsto,
il calculator NON tira a indovinare: restituisce `unavailable` con
`missing_documents=["formula_engine_unknown"]` o
`["formula_amount_rule_unknown"]`.

Priorità degli stati (ordine di valutazione):

  1. nessuna fonte approvata             → UNAVAILABLE
  2. nessun dataset approvato            → UNAVAILABLE (compensation_dataset_approved)
  3. nessuna formula approvata           → UNAVAILABLE (calculation_formula_approved)
  4. formula approvata, engine ignoto    → UNAVAILABLE (formula_engine_unknown)
  5. engine ok, amount_rule ignota       → UNAVAILABLE (formula_amount_rule_unknown)
  6. input minimi mancanti               → INSUFFICIENT_INPUT
  7. fault_percentage fuori range        → INSUFFICIENT_INPUT
  8. nessuna riga match                  → UNAVAILABLE (compensation_row_match)
  9. più righe match                     → UNAVAILABLE (compensation_row_disambiguation)
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

JURISDICTION_CODE_IT = "IT-NATIONAL"


class _ItalyPlaceholderCalculator(BaseCalculator):
    """Base placeholder per i calculator Italia ancora privi di engine."""

    jurisdiction_code = JURISDICTION_CODE_IT

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        # Anche con fonti `approved` presenti, NON inventiamo importi.
        # Restituiamo le fonti per audit ma teniamo `unavailable`.
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=[SourceRef.from_legal_source(s) for s in sources],
            warnings=[
                "Calculator engine not yet implemented for this case type. "
                "Approved legal sources are present but compute logic is "
                "pending validation in a later phase."
            ],
        )


class ItalyRoadAccidentBodilyInjuryCalculator(_ItalyPlaceholderCalculator):
    """
    Italia — incidente stradale, lesioni personali (danno biologico RCA).

    Implementa il flusso completo di gating + esecuzione descritto nel
    docstring del modulo. Il calcolo legge esclusivamente:
    - `LegalSource` approved per la giurisdizione/case_type;
    - `CompensationDataset` approved con `valid_from/valid_to` rispettati;
    - `CalculationFormula` approved con `engine` e `amount_rule` registrati;
    - `CompensationTableRow` del dataset, filtrata sui predicati dichiarati.

    Nessun valore monetario è hardcoded.
    """

    case_type = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        # Lazy import: apps.calculators non dipende staticamente da
        # apps.compensation. La dipendenza è opzionale e runtime-only,
        # così che il modulo calculators resti caricabile anche senza
        # apps.compensation pronta (test isolati, scaffolding).
        from apps.compensation.services import (
            RowMatchKind,
            apply_amount_rule,
            find_matching_row,
            get_approved_dataset_for_sources,
            get_executable_formula,
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
                    "compensation dataset is linked to them for this case "
                    "type. The tabular extraction must be validated by a "
                    "legal reviewer before any estimate can be produced."
                ],
                missing_documents=["compensation_dataset_approved"],
            )

        # --- gate 3 + 4: formula approved con engine/rule riconosciuti
        resolution = get_executable_formula(dataset)
        if resolution.formula is None:
            return self._unavailable_for_formula_status(
                source_refs=source_refs, status=resolution.status
            )

        formula = resolution.formula
        params = formula.parameters or {}

        # --- gate 6: input minimi richiesti dalla formula --------------
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

        # --- gate 7: fault_percentage in range, se fornito -------------
        fault_warning = _validate_fault_percentage(input_data)
        if fault_warning:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[fault_warning],
            )

        # --- gate 8/9: row match unico ---------------------------------
        row_match_fields = params.get("row_match") or []
        match = find_matching_row(
            dataset,
            row_match_fields=row_match_fields,
            input_data=input_data,
        )
        if match.kind == RowMatchKind.NONE:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    "No table row matches the provided input within the "
                    "approved compensation dataset. The dataset may not "
                    "yet cover this combination of age and disability."
                ],
                missing_documents=["compensation_row_match"],
            )
        if match.kind == RowMatchKind.MULTIPLE:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    f"Multiple ({match.candidates}) table rows match the "
                    "provided input. Disambiguation requires legal review: "
                    "the calculator refuses to pick one arbitrarily."
                ],
                missing_documents=["compensation_row_disambiguation"],
            )

        # --- step 10: calcolo vero -------------------------------------
        fault_reduction_enabled = bool(params.get("fault_reduction"))
        amount = apply_amount_rule(
            params["amount_rule"],
            row=match.row,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )

        breakdown = [
            BreakdownItem(
                label="Danno biologico permanente",
                amount_min=amount,
                amount_mid=amount,
                amount_max=amount,
                formula=formula.code,
                source_ref_ids=tuple(s.id for s in source_refs),
                notes=(
                    f"Computed from CompensationTableRow id={match.row.pk} "
                    f"using formula '{formula.code}' "
                    f"(rule='{params['amount_rule']}')."
                ),
            )
        ]

        assumptions = [
            f"Formula applied: {formula.code} ({params['amount_rule']}).",
            f"Source dataset: '{dataset.name}' (version " f"'{dataset.version_label or 'n/a'}').",
        ]
        if fault_reduction_enabled and _has_value(input_data, "fault_percentage"):
            assumptions.append("Fault reduction applied as declared by the formula.")

        warnings_out: list[str] = [
            "Estimated min/mid/max coincide because no approved "
            "personalisation range is configured for this engine yet."
        ]

        # Avvisi informativi su voci di danno non incluse nel calcolo
        # (la formula approvata non le considera; non sommiamo a caso).
        for field in ("medical_expenses", "lost_income"):
            if _has_value(input_data, field):
                warnings_out.append(
                    f"Reported '{field}' is not included in the automatic "
                    "calculation: the approved formula does not aggregate "
                    "it. Verify with legal review for case-specific "
                    "evaluation."
                )

        return self._build_result(
            status=CalculationStatus.CALCULATED.value,
            estimated_min=amount,
            estimated_mid=amount,
            estimated_max=amount,
            breakdown=breakdown,
            sources=source_refs,
            assumptions=assumptions,
            warnings=warnings_out,
            confidence=ConfidenceLevel.MEDIUM.value,
        )

    # ------------------------------------------------------------------
    # helpers privati
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
                    "approved calculation formula is linked to it. The "
                    "formula must be validated by a legal reviewer "
                    "before any estimate can be produced."
                ],
                missing_documents=["calculation_formula_approved"],
            )
        if status == FormulaResolutionStatus.ENGINE_UNKNOWN:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    "An approved formula exists but its `engine` is not "
                    "registered in the calculator's supported list. The "
                    "calculator refuses to execute unknown engines."
                ],
                missing_documents=["formula_engine_unknown"],
            )
        # AMOUNT_RULE_UNKNOWN
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=source_refs,
            warnings=[
                "An approved formula exists with a recognised engine, but "
                "its `amount_rule` is not registered in the calculator's "
                "supported list."
            ],
            missing_documents=["formula_amount_rule_unknown"],
        )


class ItalyInheritanceBasicCalculator(_ItalyPlaceholderCalculator):
    """Italia — successione di base. Placeholder."""

    case_type = CaseType.INHERITANCE_BASIC.value


# ---------------------------------------------------------------------------
# helpers di modulo
# ---------------------------------------------------------------------------


def _has_value(input_data: dict[str, Any], field: str) -> bool:
    """True se `field` è presente con valore non-None / non-stringa-vuota."""
    if field not in input_data:
        return False
    value = input_data[field]
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _validate_fault_percentage(input_data: dict[str, Any]) -> str | None:
    """Validazione locale del fault% (range 0..100). None se ok."""
    if not _has_value(input_data, "fault_percentage"):
        return None
    raw = input_data["fault_percentage"]
    try:
        value = Decimal(str(raw))
    except Exception:
        return "fault_percentage is not a valid number."
    if value < Decimal(0) or value > Decimal(100):
        return "fault_percentage must be between 0 and 100."
    return None


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
