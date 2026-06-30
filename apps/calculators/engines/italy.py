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

from dataclasses import dataclass
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


# ---------------------------------------------------------------------------
# P8 — Official art. 139 CAP micropermanenti (1–9%) engine.
#
# Source-approved by the owner (CHATGPT_SOURCE_APPROVALS): art. 139 CAP +
# D.M. MIMIT 18/07/2025 (G.U. n.176 del 31/07/2025, decorrenza aprile 2025).
# ALL numeric values are read from approved CompensationTableRow rows (the 9
# progression coefficients, the first-point value, the ITT daily value) — never
# hardcoded here. The formula (art. 139 co.1 + co.6) lives in code:
#
#   danno permanente = primo_punto × coeff(P) × P × (1 − max(0, età−10)×0,005)
#   danno temporaneo = giorni_ITT_assoluta × itt_daily
#                      (+ giorni_parziale × itt_daily × percentuale/100)
#
# Row layout of the approved micro dataset (case_type road_accident_microlesions):
#   row_type="disability_coefficient", disability_min=disability_max=P, coefficient=coeff
#   row_type="first_point_value",      point_value=primo_punto
#   row_type="itt_daily_absolute",     daily_amount=itt_daily
# ---------------------------------------------------------------------------

ITALY_MICRO_ENGINE_VERSION = "italy-art139-micro-1.0"
_AGE_REDUCTION_PER_YEAR = Decimal("0.005")
_MICRO_MIN_PCT = 1
_MICRO_MAX_PCT = 9


def _age_demultiplier(age: int) -> Decimal | None:
    """art. 139: −0,5% per anno dall'11° anno di età. Floor a 0; None se età
    fuori da un range plausibile (fail-closed, mai un demoltiplicatore assurdo)."""
    if age < 0 or age > 120:
        return None
    reduction = _AGE_REDUCTION_PER_YEAR * Decimal(max(0, age - 10))
    demult = Decimal(1) - reduction
    return demult if demult > 0 else Decimal(0)


@dataclass
class _MicroComputation:
    permanent: Decimal
    temporary: Decimal
    total: Decimal
    coeff: Decimal
    primo_punto: Decimal
    itt_daily: Decimal


def _compute_art139_micro(dataset, input_data: dict[str, Any]) -> _MicroComputation | None:
    """Apply the official art. 139 formula reading values from the approved
    micro dataset rows. Returns None when any required approved row/value is
    missing (the caller then fails closed — never a guessed amount)."""
    from decimal import ROUND_HALF_UP

    pct = _to_int(input_data.get("permanent_disability_percentage"))
    if pct is None or pct < _MICRO_MIN_PCT or pct > _MICRO_MAX_PCT:
        return None
    age = _to_int(input_data.get("victim_age"))
    if age is None:
        return None
    demult = _age_demultiplier(age)
    if demult is None:
        return None

    rows = dataset.rows.all()
    coeff_row = next(
        (r for r in rows
         if r.row_type == "disability_coefficient"
         and (r.disability_min is None or r.disability_min <= pct)
         and (r.disability_max is None or r.disability_max >= pct)),
        None,
    )
    base_row = next((r for r in rows if r.row_type == "first_point_value"), None)
    itt_row = next((r for r in rows if r.row_type == "itt_daily_absolute"), None)
    if coeff_row is None or base_row is None or itt_row is None:
        return None
    coeff = getattr(coeff_row, "coefficient", None)
    primo_punto = getattr(base_row, "point_value", None)
    itt_daily = getattr(itt_row, "daily_amount", None)
    if coeff is None or primo_punto is None or itt_daily is None:
        return None

    cents = Decimal("0.01")
    permanent = (primo_punto * coeff * Decimal(pct) * demult).quantize(cents, ROUND_HALF_UP)

    itt_abs = _to_int(input_data.get("total_temporary_disability_days")) or 0
    itt_partial = _to_int(input_data.get("partial_temporary_disability_days")) or 0
    # Partial ITT is conventionally weighted at 50% of a day of absolute ITT when
    # no explicit per-day percentage is collected; this is documented and shown.
    temporary = (
        (Decimal(itt_abs) * itt_daily)
        + (Decimal(itt_partial) * itt_daily * Decimal("0.5"))
    ).quantize(cents, ROUND_HALF_UP)

    total = (permanent + temporary).quantize(cents, ROUND_HALF_UP)
    return _MicroComputation(permanent, temporary, total, coeff, primo_punto, itt_daily)


class _ItalyArt139MicroMixin:
    """Shared art. 139 micro computation for road-accident and medical-liability
    biological damage. Reads the approved micro dataset (road_accident_microlesions)
    regardless of the invoking case_type, since the same official table applies."""

    def _micro_result(self, input_data, source_refs, *, extra_assumptions=None,
                      extra_warnings=None):
        from apps.compensation.services import get_approved_dataset_for_sources

        # the micro values live under the road_accident_microlesions dataset
        sources_models = [s for s in self._approved_sources_cache]
        micro_dataset = get_approved_dataset_for_sources(
            sources_models, CaseType.ROAD_ACCIDENT_MICROLESIONS.value
        )
        if micro_dataset is None:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[_diag.diagnostic_to_internal_warning(_diag.COMPENSATION_DATASET_NOT_APPROVED)],
                missing_documents=[_diag.COMPENSATION_DATASET_NOT_APPROVED],
            )
        comp = _compute_art139_micro(micro_dataset, input_data)
        if comp is None:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[_diag.diagnostic_to_internal_warning(_diag.COMPENSATION_ROW_VALUE_MISSING)],
                missing_documents=[_diag.COMPENSATION_ROW_VALUE_MISSING],
            )
        breakdown = [
            BreakdownItem(
                label="Danno biologico permanente (art. 139)",
                amount_min=comp.permanent, amount_mid=comp.permanent, amount_max=comp.permanent,
                formula="italy_art139_micro_v1",
                source_ref_ids=tuple(s.id for s in source_refs),
                notes=(f"primo_punto={comp.primo_punto} × coeff={comp.coeff} × punti × "
                       f"demoltiplicatore_età (art. 139 co.1/co.6)."),
            ),
            BreakdownItem(
                label="Danno biologico temporaneo (ITT)",
                amount_min=comp.temporary, amount_mid=comp.temporary, amount_max=comp.temporary,
                formula="italy_art139_micro_v1",
                source_ref_ids=tuple(s.id for s in source_refs),
                notes=f"giorni ITT × {comp.itt_daily}/giorno (parziali al 50%).",
            ),
        ]
        provenance = build_calculation_provenance(
            engine="italy_art139_micro_v1",
            engine_version=ITALY_MICRO_ENGINE_VERSION,
            amount_rule="italy_art139_micro_v1",
            dataset=micro_dataset,
            formula=None,
            rows=list(micro_dataset.rows.all()),
        )
        return self._build_result(
            status=CalculationStatus.CALCULATED.value,
            estimated_min=comp.total, estimated_mid=comp.total, estimated_max=comp.total,
            breakdown=breakdown,
            sources=source_refs,
            assumptions=list(extra_assumptions or []),
            warnings=list(extra_warnings or []),
            confidence=ConfidenceLevel.MEDIUM.value,
            provenance=provenance,
        )


class ItalyRoadAccidentMicrolesionCalculator(_ItalyArt139MicroMixin, _ItalyPlaceholderCalculator):
    """Italia — incidente stradale, micropermanenti 1–9% (art. 139 CAP)."""

    case_type = CaseType.ROAD_ACCIDENT_MICROLESIONS.value

    def _compute_with_sources(self, input_data, sources):
        self._approved_sources_cache = sources
        source_refs = [SourceRef.from_legal_source(s) for s in sources]
        return self._micro_result(input_data, source_refs)


class ItalyMedicalLiabilityBiologicalCalculator(_ItalyArt139MicroMixin, _ItalyPlaceholderCalculator):
    """Italia — responsabilità sanitaria, stima TABELLARE del danno biologico.

    L. 24/2017 → il danno biologico da attività sanitaria si liquida con le
    tabelle artt. 138/139 CAP. Stima SOLO il danno biologico tabellare: 1–9% via
    art. 139 micro; ≥10% delega al TUN (art. 138). NON valuta colpa, nesso
    causale, perdita di chance, danno morale extra, danno patrimoniale o la
    responsabilità sanitaria complessiva (disclaimer pubblico forte)."""

    case_type = CaseType.MEDICAL_LIABILITY_BIOLOGICAL.value

    def _compute_with_sources(self, input_data, sources):
        self._approved_sources_cache = sources
        source_refs = [SourceRef.from_legal_source(s) for s in sources]
        pct = _to_int(input_data.get("permanent_disability_percentage"))
        if pct is None or pct < 1:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_public_warning(
                        _diag.ITALY_REQUIRED_INPUT_MISSING,
                        context={"fields": ("permanent_disability_percentage",)},
                    )
                ],
            )
        if pct <= _MICRO_MAX_PCT:
            # 1–9% → art. 139 micro (the medical disclaimer is added on the result page)
            return self._micro_result(input_data, source_refs)
        # ≥10% → reuse the approved TUN art. 138 engine, presented under L. 24/2017.
        tun = ItalyRoadAccidentBodilyInjuryCalculator(
            simulation_id=self.simulation_id, language=self.language
        )
        return tun._compute_with_sources(input_data, sources)


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


def _to_int(raw: Any) -> int | None:
    """Parse an integer from wizard input; None when absent/blank/invalid."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    try:
        return int(Decimal(s))
    except Exception:
        return None


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
# P8: official art. 139 micro engine + medical-liability tabular biological damage.
register_calculator(
    JURISDICTION_CODE_IT,
    CaseType.ROAD_ACCIDENT_MICROLESIONS.value,
    ItalyRoadAccidentMicrolesionCalculator,
)
register_calculator(
    JURISDICTION_CODE_IT,
    CaseType.MEDICAL_LIABILITY_BIOLOGICAL.value,
    ItalyMedicalLiabilityBiologicalCalculator,
)
