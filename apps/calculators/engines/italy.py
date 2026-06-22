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

from .. import diagnostics as _diag
from ..enums import CalculationStatus, CaseType, ConfidenceLevel
from ..provenance import build_calculation_provenance
from ..registry import register_calculator
from ..schemas import BreakdownItem, CalculationResult, SourceRef
from .base import BaseCalculator

JURISDICTION_CODE_IT = "IT-NATIONAL"

# H1-8: version tag of this engine's calculation logic, recorded in the
# provenance snapshot. Bump when the calculation behaviour changes.
ITALY_ENGINE_VERSION = "italy-1.0"


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
            warnings=[_diag.diagnostic_to_internal_warning(_diag.CALCULATOR_ENGINE_PENDING)],
            missing_documents=[_diag.CALCULATOR_ENGINE_PENDING],
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
            apply_amount_range_rule,
            apply_amount_rule,
            find_matching_row,
            find_matching_row_by_type,
            get_approved_dataset_by_version_label,
            get_approved_dataset_for_sources,
            get_executable_formula,
            is_range_rule,
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
                    _diag.diagnostic_to_public_warning(
                        _diag.ITALY_REQUIRED_INPUT_MISSING,
                        context={"fields": tuple(missing_inputs)},
                    )
                ],
            )

        # --- gate 7: fault_percentage in range, se fornito -------------
        fault_code = _validate_fault_percentage(input_data)
        if fault_code is not None:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[_diag.diagnostic_to_public_warning(fault_code)],
            )

        # --- branch: range rule vs single-row rule --------------------
        # Backward compat: single-row rules (row_amount_direct,
        # point_value_times_disability_percentage) preservano il flusso
        # storico (estimated_min == estimated_mid == estimated_max).
        # La nuova rule row_amount_range_direct usa un dataset secondario
        # APPROVED (DPR-12-2025-MORAL) per produrre min/mid/max distinti.
        rule = params["amount_rule"]
        row_match_fields = params.get("row_match") or []
        fault_reduction_enabled = bool(params.get("fault_reduction"))

        if is_range_rule(rule):
            return self._compute_range(
                input_data=input_data,
                source_refs=source_refs,
                dataset=dataset,
                formula=formula,
                params=params,
                row_match_fields=row_match_fields,
                fault_reduction_enabled=fault_reduction_enabled,
                # Inject service helpers (already imported in outer scope)
                _apply=apply_amount_range_rule,
                _find=find_matching_row_by_type,
                _get_secondary_dataset=get_approved_dataset_by_version_label,
                _RowMatchKind=RowMatchKind,
            )

        # --- gate 8/9: row match unico (single-row rule) ---------------
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
                    _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_ROW_MATCH_MISSING)
                ],
                missing_documents=[_diag.COMPENSATION_ROW_MATCH_MISSING],
            )
        if match.kind == RowMatchKind.MULTIPLE:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_ROW_DISAMBIGUATION)
                ],
                missing_documents=[_diag.COMPENSATION_ROW_DISAMBIGUATION],
            )

        # --- gate 9.5: la riga matchata DEVE avere il valore monetario.
        # Fail-closed: una riga APPROVED con `point_value` NULL non deve
        # produrre un CALCULATED 0 € (sarebbe un "calcolo falso" sottile).
        # Vedi diagnostics.COMPENSATION_ROW_VALUE_MISSING.
        if _row_amount_value_missing(match.row):
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_ROW_VALUE_MISSING)
                ],
                missing_documents=[_diag.COMPENSATION_ROW_VALUE_MISSING],
            )

        # --- step 10: calcolo vero (single-row rule) -------------------
        amount = apply_amount_rule(
            rule,
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
                    f"(rule='{rule}')."
                ),
            )
        ]

        assumptions = [
            _diag.diagnostic_to_public_warning(
                _diag.ITALY_ASSUMPTION_FORMULA_APPLIED,
                context={"formula": formula.code, "rule": rule},
            ),
            _diag.diagnostic_to_public_warning(
                _diag.ITALY_ASSUMPTION_SOURCE_DATASET,
                context={"dataset": dataset.name, "version": dataset.version_label or "n/a"},
            ),
        ]
        if fault_reduction_enabled and _has_value(input_data, "fault_percentage"):
            assumptions.append(
                _diag.diagnostic_to_public_warning(_diag.ITALY_FAULT_REDUCTION_APPLIED)
            )

        warnings_out: list[str] = [_diag.diagnostic_to_public_warning(_diag.ITALY_RANGE_COLLAPSED)]

        # Avvisi informativi su voci di danno non incluse nel calcolo
        # (la formula approvata non le considera; non sommiamo a caso).
        for field in ("medical_expenses", "lost_income"):
            if _has_value(input_data, field):
                warnings_out.append(
                    _diag.diagnostic_to_public_warning(
                        _diag.ITALY_FIELD_NOT_AGGREGATED,
                        context={"field": field},
                    )
                )

        provenance = build_calculation_provenance(
            engine=str(formula.parameters.get("engine") or ""),
            engine_version=ITALY_ENGINE_VERSION,
            amount_rule=rule,
            dataset=dataset,
            formula=formula,
            rows=[match.row],
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
            provenance=provenance,
        )

    # ------------------------------------------------------------------
    # Range engine — usa un dataset secondario APPROVED per min/mid/max.
    # Mai esegue se quel dataset è DRAFT (caso di moral non ancora
    # approvato dallo Studio): fallisce in modo controllato.
    # ------------------------------------------------------------------

    def _compute_range(
        self,
        *,
        input_data: dict[str, Any],
        source_refs,
        dataset,
        formula,
        params: dict[str, Any],
        row_match_fields: list[str],
        fault_reduction_enabled: bool,
        _apply,
        _find,
        _get_secondary_dataset,
        _RowMatchKind,
    ) -> CalculationResult:
        # I parametri necessari per il range devono essere TUTTI presenti.
        version_label = params.get("range_dataset_version_label")
        min_rt = params.get("min_row_type")
        mid_rt = params.get("mid_row_type")
        max_rt = params.get("max_row_type")
        if not (version_label and min_rt and mid_rt and max_rt):
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.FORMULA_RANGE_PARAMETERS_INCOMPLETE)
                ],
                missing_documents=[_diag.FORMULA_RANGE_PARAMETERS_INCOMPLETE],
            )

        # Lookup del dataset secondario APPROVED. Se è DRAFT (caso moral
        # non promosso), ritorna None e qui blocchiamo: il pubblico non
        # vede mai un dataset draft.
        range_dataset = _get_secondary_dataset(
            source=dataset.source,
            case_type=self.case_type,
            version_label=version_label,
        )
        if range_dataset is None:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[_diag.diagnostic_to_internal_warning(_diag.RANGE_DATASET_NOT_APPROVED)],
                missing_documents=[_diag.RANGE_DATASET_NOT_APPROVED],
            )

        # Match unico riga per ciascun row_type del range.
        matches: dict[str, Any] = {}
        for kind, rt in (("min", min_rt), ("mid", mid_rt), ("max", max_rt)):
            m = _find(
                range_dataset,
                row_type=rt,
                row_match_fields=row_match_fields,
                input_data=input_data,
            )
            if m.kind == _RowMatchKind.NONE:
                return self._build_result(
                    status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                    sources=source_refs,
                    warnings=[
                        _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_ROW_MATCH_MISSING)
                    ],
                    missing_documents=[_diag.COMPENSATION_ROW_MATCH_MISSING],
                )
            if m.kind == _RowMatchKind.MULTIPLE:
                return self._build_result(
                    status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                    sources=source_refs,
                    warnings=[
                        _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_ROW_DISAMBIGUATION)
                    ],
                    missing_documents=[_diag.COMPENSATION_ROW_DISAMBIGUATION],
                )
            matches[kind] = m.row

        # Fail-closed anche sul range: ognuna delle righe min/mid/max deve
        # esporre il valore monetario. Una riga APPROVED con `point_value`
        # NULL blocca il calcolo invece di produrre uno 0 € fittizio.
        if any(_row_amount_value_missing(row) for row in matches.values()):
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_ROW_VALUE_MISSING)
                ],
                missing_documents=[_diag.COMPENSATION_ROW_VALUE_MISSING],
            )

        amounts = _apply(
            params["amount_rule"],
            row_min=matches["min"],
            row_mid=matches["mid"],
            row_max=matches["max"],
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )
        if not amounts.is_monotone():
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_RANGE_INCONSISTENT)
                ],
                missing_documents=[_diag.COMPENSATION_RANGE_INCONSISTENT],
            )

        breakdown = [
            BreakdownItem(
                label="Danno biologico + morale",
                amount_min=amounts.min_amount,
                amount_mid=amounts.mid_amount,
                amount_max=amounts.max_amount,
                formula=formula.code,
                source_ref_ids=tuple(s.id for s in source_refs),
                notes=(
                    f"Computed from approved range dataset "
                    f"'{range_dataset.version_label}' "
                    f"(rule='{params['amount_rule']}')."
                ),
            )
        ]
        assumptions = [
            _diag.diagnostic_to_public_warning(
                _diag.ITALY_ASSUMPTION_FORMULA_APPLIED,
                context={"formula": formula.code, "rule": params["amount_rule"]},
            ),
            _diag.diagnostic_to_public_warning(
                _diag.ITALY_ASSUMPTION_RANGE_DATASET,
                context={
                    "dataset": range_dataset.name,
                    "version": range_dataset.version_label,
                },
            ),
        ]
        if fault_reduction_enabled and _has_value(input_data, "fault_percentage"):
            assumptions.append(
                _diag.diagnostic_to_public_warning(_diag.ITALY_FAULT_REDUCTION_APPLIED_UNIFORM)
            )
        warnings_out: list[str] = []
        for field in ("medical_expenses", "lost_income"):
            if _has_value(input_data, field):
                warnings_out.append(
                    _diag.diagnostic_to_public_warning(
                        _diag.ITALY_FIELD_NOT_AGGREGATED,
                        context={"field": field},
                    )
                )
        provenance = build_calculation_provenance(
            engine=str(formula.parameters.get("engine") or ""),
            engine_version=ITALY_ENGINE_VERSION,
            amount_rule=str(params["amount_rule"]),
            dataset=dataset,
            formula=formula,
            rows=[matches["min"], matches["mid"], matches["max"]],
            range_dataset=range_dataset,
        )

        return self._build_result(
            status=CalculationStatus.CALCULATED.value,
            estimated_min=amounts.min_amount,
            estimated_mid=amounts.mid_amount,
            estimated_max=amounts.max_amount,
            breakdown=breakdown,
            sources=source_refs,
            assumptions=assumptions,
            warnings=warnings_out,
            confidence=ConfidenceLevel.MEDIUM.value,
            provenance=provenance,
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
        # AMOUNT_RULE_UNKNOWN
        return self._build_result(
            status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
            sources=source_refs,
            warnings=[_diag.diagnostic_to_internal_warning(_diag.FORMULA_AMOUNT_RULE_UNKNOWN)],
            missing_documents=[_diag.FORMULA_AMOUNT_RULE_UNKNOWN],
        )


class ItalyInheritanceBasicCalculator(_ItalyPlaceholderCalculator):
    """Italia — successione di base. Placeholder."""

    case_type = CaseType.INHERITANCE_BASIC.value


# ---------------------------------------------------------------------------
# helpers di modulo
# ---------------------------------------------------------------------------


def _row_amount_value_missing(row: Any) -> bool:
    """True se la riga matchata non espone il valore monetario letto dalle
    amount rule IT (``point_value``).

    Guard fail-closed: un ``point_value`` NULL su una riga di un dataset
    APPROVED deve produrre ``UNAVAILABLE_REQUIRES_LEGAL_VALIDATION``, MAI un
    ``CALCULATED`` con importo 0 €. Le regole condivise in
    ``apps.compensation.services`` fanno ancora il coalesce a ``Decimal(0)``
    per gli engine inerti (FR/BE/MA/TN, privi di dati approved): questo
    gate protegge la sola superficie pubblica, l'engine IT.
    """
    return getattr(row, "point_value", None) is None


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
    """Validazione locale del fault% (range 0..100).

    Returns one of the diagnostic codes when invalid, ``None`` when ok.
    The engine wraps the code with
    :func:`apps.calculators.diagnostics.diagnostic_to_public_warning`
    to surface a localised, premium message.
    """
    if not _has_value(input_data, "fault_percentage"):
        return None
    raw = input_data["fault_percentage"]
    try:
        value = Decimal(str(raw))
    except Exception:
        return _diag.ITALY_INVALID_PERCENTAGE_INPUT
    if value < Decimal(0) or value > Decimal(100):
        return _diag.ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE
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
