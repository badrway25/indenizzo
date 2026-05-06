"""Calculator Belgium — engine inattivo, scaffold pronto per fixture-only.

Iter:

- F-belgium-road-accident-bootstrap: registrazione del calculator + ritorno
  ``unavailable_requires_legal_validation`` permanente.
- F-belgium-import-candidate-datasets-draft-seed: seed del Tableau
  Indicatif 2020 in DRAFT (4 perimetri, 166 righe non pubblicabili).
- F-belgium-engine-inactive-fixture-only: aggiunta del *path eseguibile*
  per i 3 perimetri pass-1 (souffrances endurées, indemnité forfaitaire,
  prejudice de décès / affection). Sul DB pubblico nulla cambia: nessuna
  ``LegalSource`` BE è ``APPROVED`` → il gating impedisce l'esecuzione e
  il calculator pubblico continua a restituire ``unavailable``.

Engine identity (registrato in ``apps.compensation.services.SUPPORTED_ENGINES``):

    "belgium_road_accident_v1"

Le tre amount_rule pass-1 vivono in
``apps.compensation.services.SUPPORTED_AMOUNT_RULES``:

- ``belgium_souffrances_age_severity_direct``
- ``belgium_forfait_age_annual_direct``
- ``belgium_deces_affection_relation_direct``

Tutte e tre sono ``SINGLE_ROW_RANGE_AMOUNT_RULES``: una sola riga matchata
emette una tripla ``(min, mid, max)``. Il quarto perimetro del Tableau
Indicatif 2020 (véhicule de remplacement) è volutamente fuori pass-1: la
sua tassonomia camions/autobus richiede una formula dedicata che lo
Studio dovrà esaminare in un iter successivo.

Schema atteso di ``CalculationFormula.parameters`` per attivare l'engine
quando lo Studio promuoverà sorgente + dataset (UNA formula per
perimetro, ognuna con il proprio ``row_type`` whitelisted):

    Souffrances endurées:
    {
        "engine": "belgium_road_accident_v1",
        "amount_rule": "belgium_souffrances_age_severity_direct",
        "row_type": "be_souffrances_endurees_per_age_severity_amount",
        "row_match": ["victim_age", "severity_scale"],
        "requires": ["victim_age", "severity_scale"],
        "fault_reduction": true | false
    }

    Indemnité forfaitaire:
    {
        "engine": "belgium_road_accident_v1",
        "amount_rule": "belgium_forfait_age_annual_direct",
        "row_type": "be_indemnite_forfaitaire_per_age_annual_amount",
        "row_match": ["victim_age"],
        "requires": ["victim_age"],
        "fault_reduction": true | false
    }

    Prejudice de décès / affection:
    {
        "engine": "belgium_road_accident_v1",
        "amount_rule": "belgium_deces_affection_relation_direct",
        "row_type": "be_prejudice_deces_affection_per_relation_amount",
        "row_match": ["relation_code"],
        "requires": ["relation_code"],
        "fault_reduction": true | false
    }

Ordine di valutazione (specchia France con un singolo path single-row range):

  1. nessuna fonte approvata             → UNAVAILABLE
  2. nessun dataset approvato            → UNAVAILABLE (compensation_dataset_approved)
  3. nessuna formula approvata           → UNAVAILABLE (calculation_formula_approved)
  4. engine ignoto                       → UNAVAILABLE (formula_engine_unknown)
  5. amount_rule ignota                  → UNAVAILABLE (formula_amount_rule_unknown)
  6. amount_rule non single-row range    → UNAVAILABLE (formula_amount_rule_not_single_row_range)
  7. input minimi mancanti               → INSUFFICIENT_INPUT
  8. fault_percentage fuori range        → INSUFFICIENT_INPUT
  9. row_type non dichiarato             → UNAVAILABLE (formula_row_type_missing)
  10. nessuna riga match                 → UNAVAILABLE (compensation_row_match)
  11. più righe match                    → UNAVAILABLE (compensation_row_disambiguation)
  12. range non monotono                 → UNAVAILABLE (compensation_range_inconsistent)
  13. tutto ok                           → CALCULATED
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

JURISDICTION_CODE_BE = "BE-NATIONAL"

# Per-rule short label used in the breakdown item. Kept in code, not in
# DB, because it's a visualisation concern not a legal one.
_RULE_BREAKDOWN_LABELS = {
    "belgium_souffrances_age_severity_direct": "Souffrances endurées",
    "belgium_forfait_age_annual_direct": "Indemnité forfaitaire",
    "belgium_deces_affection_relation_direct": "Préjudice de décès / affection",
}


class _BelgiumPlaceholderCalculator(BaseCalculator):
    """Base placeholder per i calculator Belgio non ancora cablati.

    Identico al placeholder Francia di
    F-france-road-accident-bootstrap: con o senza fonti ``approved``,
    il calculator NON produce importi finché tutte le porte di gating
    non sono passate.
    """

    jurisdiction_code = JURISDICTION_CODE_BE

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


class BelgiumRoadAccidentBodilyInjuryCalculator(_BelgiumPlaceholderCalculator):
    """Belgium — accident de la circulation, dommages corporels (Tableau Indicatif).

    Esegue il calcolo SOLO se tutte le condizioni di gating sono
    soddisfatte: fonte ``approved``, dataset ``approved``, formula
    ``approved`` con engine ``belgium_road_accident_v1``, riga unica che
    matcha gli input. Sul DB pubblico oggi le fonti BE sono
    ``needs_review`` quindi il gating fallisce al primo livello e il
    calcolatore restituisce ``unavailable``. Solo i test fixture-only
    seedano sorgenti+dataset+formula APPROVED in test DB per esercitare
    il path eseguibile.
    """

    case_type = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value

    def _compute_with_sources(
        self,
        input_data: dict[str, Any],
        sources: list[LegalSource],
    ) -> CalculationResult:
        # Lazy import: stessa motivazione di Italia/Francia, evita un
        # dipendency edge statico fra apps.calculators e apps.compensation.
        from apps.compensation.services import (
            RowMatchKind,
            apply_amount_single_row_range_rule,
            find_matching_row_by_type,
            get_approved_dataset_for_sources,
            get_executable_formula,
            is_single_row_range_rule,
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

        # --- gate 6: only single-row range rules supported by BE engine
        rule = params.get("amount_rule")
        if not is_single_row_range_rule(rule):
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(
                        _diag.FORMULA_AMOUNT_RULE_NOT_SINGLE_ROW_RANGE
                    )
                ],
                missing_documents=[_diag.FORMULA_AMOUNT_RULE_NOT_SINGLE_ROW_RANGE],
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

        # --- gate 8: fault_percentage in range (0..100) se fornito
        fault_code = _validate_fault_percentage(input_data)
        if fault_code is not None:
            return self._build_result(
                status=CalculationStatus.INSUFFICIENT_INPUT.value,
                sources=source_refs,
                warnings=[_diag.diagnostic_to_public_warning(fault_code)],
            )

        # --- gate 9/10/11: row match unico via row_type whitelisted
        row_type = params.get("row_type")
        row_match_fields = params.get("row_match") or []
        if not row_type:
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[_diag.diagnostic_to_internal_warning(_diag.FORMULA_ROW_TYPE_MISSING)],
                missing_documents=[_diag.FORMULA_ROW_TYPE_MISSING],
            )

        match = find_matching_row_by_type(
            dataset,
            row_type=row_type,
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

        # --- step 13: calcolo vero (single-row range rule)
        fault_reduction_enabled = bool(params.get("fault_reduction"))
        amounts = apply_amount_single_row_range_rule(
            rule,
            row=match.row,
            input_data=input_data,
            fault_reduction_enabled=fault_reduction_enabled,
        )

        # --- gate 12: monotonicità — il public path non pubblica un
        # range invertito anche se il fault si applica uniformemente.
        if not amounts.is_monotone():
            return self._build_result(
                status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
                sources=source_refs,
                warnings=[
                    _diag.diagnostic_to_internal_warning(_diag.COMPENSATION_RANGE_INCONSISTENT)
                ],
                missing_documents=[_diag.COMPENSATION_RANGE_INCONSISTENT],
            )

        breakdown_label = _RULE_BREAKDOWN_LABELS.get(rule, "Belgium amount")
        breakdown = [
            BreakdownItem(
                label=breakdown_label,
                amount_min=amounts.min_amount,
                amount_mid=amounts.mid_amount,
                amount_max=amounts.max_amount,
                formula=formula.code,
                source_ref_ids=tuple(s.id for s in source_refs),
                notes=(
                    f"Computed from CompensationTableRow id={match.row.pk} "
                    f"(row_type={row_type!r}) using formula '{formula.code}' "
                    f"(rule='{rule}')."
                ),
            )
        ]

        assumptions = [
            f"Formula applied: {formula.code} ({rule}).",
            f"Source dataset: '{dataset.name}' (version '{dataset.version_label or 'n/a'}').",
        ]
        if fault_reduction_enabled and _has_value(input_data, "fault_percentage"):
            assumptions.append("Fault reduction applied uniformly to min/mid/max.")

        warnings_out: list[str] = []
        if amounts.min_amount == amounts.mid_amount == amounts.max_amount:
            warnings_out.append(
                "Estimated min/mid/max coincide because the matched row "
                "carries no per-cell fourchette range; the value is the "
                "single Tableau Indicatif amount for the matched bucket."
            )
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
            estimated_min=amounts.min_amount,
            estimated_mid=amounts.mid_amount,
            estimated_max=amounts.max_amount,
            breakdown=breakdown,
            sources=source_refs,
            assumptions=assumptions,
            warnings=warnings_out,
            confidence=ConfidenceLevel.MEDIUM.value,
        )

    # ------------------------------------------------------------------
    # helpers privati (specchio di quelli Italia/Francia, riadattati a BE)
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
# helpers di modulo (cloni privati di quelli Italia/Francia — un duplicato
# intenzionale per evitare di introdurre dipendenze cross-engine: ogni
# engine paese deve restare leggibile come unità).
# ---------------------------------------------------------------------------


def _has_value(input_data: dict[str, Any], field: str) -> bool:
    if field not in input_data:
        return False
    value = input_data[field]
    if value is None:
        return False
    if isinstance(value, str) and not value.strip():
        return False
    return True


def _validate_fault_percentage(input_data: dict[str, Any]) -> str | None:
    """Returns a diagnostic code when invalid, ``None`` when ok."""
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
    JURISDICTION_CODE_BE,
    CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    BelgiumRoadAccidentBodilyInjuryCalculator,
)
