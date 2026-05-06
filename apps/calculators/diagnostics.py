"""Centralised diagnostic codes for the calculator stack.

Iter: ``F-calculator-warning-strings-translatable-pass1``.

The MA / TN / FR / BE / IT engines used to write English warning
sentences inline. They were never surfaced on the public template
(the result page renders the curated
:class:`apps.cases.public_result_messages.PublicResultMessage`
instead) but they were embedded in ``Simulation.output_data`` and
visible to Studio reviewers / audit logs.

This module centralises every diagnostic so:

- Engines emit warnings via :func:`diagnostic_to_internal_warning`
  rather than hard-coded English strings.
- The text is wrapped in :func:`gettext_lazy`, so audit interfaces
  that activate a locale can render the message in IT / FR / AR.
- The set of diagnostic codes is a stable, narrow vocabulary.
- Public-safety is explicit: :func:`diagnostic_public_safe` returns
  ``True`` only for messages that were vetted as safe to surface to
  end users (today: none — every diagnostic is internal-only).

The ``code`` strings match the existing ``missing_documents`` slugs
emitted by the engines so downstream tests / Studio dashboards keep
working unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils.translation import gettext_lazy as _

# ---------------------------------------------------------------------------
# Code constants — keep in sync with the slugs already used in
# Simulation.output_data["missing_documents"] across the engines.
# ---------------------------------------------------------------------------

LEGAL_SOURCES_NOT_APPROVED = "legal_sources_not_approved"
COMPENSATION_DATASET_NOT_APPROVED = "compensation_dataset_approved"
RANGE_DATASET_NOT_APPROVED = "range_dataset_approved"
CALCULATION_FORMULA_NOT_APPROVED = "calculation_formula_approved"
CALCULATOR_ENGINE_PENDING = "calculator_engine_pending_for_jurisdiction"
FORMULA_ENGINE_UNKNOWN = "formula_engine_unknown"
FORMULA_AMOUNT_RULE_UNKNOWN = "formula_amount_rule_unknown"
FORMULA_AMOUNT_RULE_NOT_SINGLE_ROW_RANGE = "formula_amount_rule_not_single_row_range"
FORMULA_AMOUNT_RULE_NOT_INHERITANCE_SHARE = "formula_amount_rule_not_inheritance_share"
FORMULA_ROW_TYPE_MISSING = "formula_row_type_missing"
FORMULA_RANGE_PARAMETERS_INCOMPLETE = "formula_range_parameters_incomplete"
COMPENSATION_ROW_MATCH_MISSING = "compensation_row_match"
COMPENSATION_ROW_DISAMBIGUATION = "compensation_row_disambiguation"
COMPENSATION_RANGE_INCONSISTENT = "compensation_range_inconsistent"
INHERITANCE_SHARE_SPEC_INVALID = "shares_spec_invalid"
APPLICABLE_LAW_REVIEW_REQUIRED = "applicable_law_review_required"
APPLICABLE_LAW_CONTEXT_MISSING = "applicable_law_context_missing"
INPUT_FIELDS_MISSING = "input_fields_missing"
INPUT_ESTATE_VALUE_INVALID = "input_estate_value_invalid"
INPUT_NEGATIVE_ESTATE = "input_negative_estate"
INPUT_NO_HEIR_ALLOCATION = "input_no_heir_allocation"

# ---------------------------------------------------------------------------
# Public-safe codes — warnings rendered on the public result page / PDF.
# Italy calculated path uses these to surface its calculated-side
# warnings in IT/FR/AR rather than the historical inline English
# strings.
# ---------------------------------------------------------------------------

ITALY_RANGE_COLLAPSED = "italy_range_collapsed"
ITALY_FIELD_NOT_AGGREGATED = "italy_field_not_aggregated"
ITALY_FAULT_REDUCTION_APPLIED = "italy_fault_reduction_applied"
ITALY_FAULT_REDUCTION_APPLIED_UNIFORM = "italy_fault_reduction_applied_uniform"

# ---------------------------------------------------------------------------
# Italy input-validation codes — emitted by the engine when the wizard
# input is missing or out of range. Public-safe today because the
# wizard already prevents the impossible cases (HTML min/max +
# required attributes), but the engine still validates as a safety
# net and the message is shown on the result page if it fires.
# ---------------------------------------------------------------------------

ITALY_REQUIRED_INPUT_MISSING = "italy_required_input_missing"
ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE = "italy_fault_percentage_out_of_range"
ITALY_INVALID_PERCENTAGE_INPUT = "italy_invalid_percentage_input"
ITALY_INPUT_PAYLOAD_INVALID = "italy_input_payload_invalid"
ITALY_FORMULA_INPUT_MISMATCH = "italy_formula_input_mismatch"


@dataclass(frozen=True)
class _DiagnosticSpec:
    code: str
    message: Any  # gettext_lazy proxy
    public_safe: bool = False


# ---------------------------------------------------------------------------
# Registry — single source of truth.
# ---------------------------------------------------------------------------


_REGISTRY: dict[str, _DiagnosticSpec] = {
    LEGAL_SOURCES_NOT_APPROVED: _DiagnosticSpec(
        code=LEGAL_SOURCES_NOT_APPROVED,
        message=_(
            "No approved legal sources are available for this jurisdiction "
            "and case type. The simulation cannot produce an estimate "
            "without legally validated sources."
        ),
    ),
    COMPENSATION_DATASET_NOT_APPROVED: _DiagnosticSpec(
        code=COMPENSATION_DATASET_NOT_APPROVED,
        message=_(
            "Approved legal sources are present, but no approved "
            "compensation dataset is linked to them. A Studio reviewer "
            "must promote the candidate dataset before any estimate can "
            "be produced."
        ),
    ),
    RANGE_DATASET_NOT_APPROVED: _DiagnosticSpec(
        code=RANGE_DATASET_NOT_APPROVED,
        message=_(
            "The base dataset is approved, but the secondary range "
            "dataset referenced by the formula has not been promoted "
            "yet. A Studio reviewer must approve it before any range "
            "estimate can be produced."
        ),
    ),
    CALCULATION_FORMULA_NOT_APPROVED: _DiagnosticSpec(
        code=CALCULATION_FORMULA_NOT_APPROVED,
        message=_(
            "Approved compensation dataset is present, but no approved "
            "calculation formula is linked to it. The formula must be "
            "validated by a legal reviewer before any estimate can be "
            "produced."
        ),
    ),
    CALCULATOR_ENGINE_PENDING: _DiagnosticSpec(
        code=CALCULATOR_ENGINE_PENDING,
        message=_(
            "Calculator engine not yet implemented for this jurisdiction "
            "and case type. Studio review is required before any "
            "computation can be exposed publicly."
        ),
    ),
    FORMULA_ENGINE_UNKNOWN: _DiagnosticSpec(
        code=FORMULA_ENGINE_UNKNOWN,
        message=_(
            "An approved formula exists but its engine is not registered "
            "in the calculator's supported list."
        ),
    ),
    FORMULA_AMOUNT_RULE_UNKNOWN: _DiagnosticSpec(
        code=FORMULA_AMOUNT_RULE_UNKNOWN,
        message=_(
            "An approved formula exists with a recognised engine, but its "
            "amount rule is not registered in the calculator's supported "
            "list."
        ),
    ),
    FORMULA_AMOUNT_RULE_NOT_SINGLE_ROW_RANGE: _DiagnosticSpec(
        code=FORMULA_AMOUNT_RULE_NOT_SINGLE_ROW_RANGE,
        message=_(
            "Approved formula declares an amount rule that this engine "
            "does not support today. Only single-row range rules are "
            "wired for road-accident bodily injury on this jurisdiction."
        ),
    ),
    FORMULA_AMOUNT_RULE_NOT_INHERITANCE_SHARE: _DiagnosticSpec(
        code=FORMULA_AMOUNT_RULE_NOT_INHERITANCE_SHARE,
        message=_(
            "Approved formula declares an amount rule that this engine "
            "does not support today. Only inheritance-share rules apply "
            "to inheritance allocation."
        ),
    ),
    FORMULA_ROW_TYPE_MISSING: _DiagnosticSpec(
        code=FORMULA_ROW_TYPE_MISSING,
        message=_(
            "Approved formula does not declare a row_type. The engine "
            "requires this parameter to dispatch the rule to the right "
            "compensation rows."
        ),
    ),
    FORMULA_RANGE_PARAMETERS_INCOMPLETE: _DiagnosticSpec(
        code=FORMULA_RANGE_PARAMETERS_INCOMPLETE,
        message=_(
            "The range rule is wired but one of its parameter fields is "
            "missing or inconsistent. A Studio reviewer must complete "
            "the formula before the range can be produced."
        ),
    ),
    COMPENSATION_ROW_MATCH_MISSING: _DiagnosticSpec(
        code=COMPENSATION_ROW_MATCH_MISSING,
        message=_(
            "No compensation row matches the input combination on the "
            "approved dataset. Either the dataset is incomplete for this "
            "case or the inputs fall outside the table."
        ),
    ),
    COMPENSATION_ROW_DISAMBIGUATION: _DiagnosticSpec(
        code=COMPENSATION_ROW_DISAMBIGUATION,
        message=_(
            "More than one compensation row matches the input "
            "combination. A Studio reviewer must disambiguate the "
            "dataset before any estimate can be produced."
        ),
    ),
    COMPENSATION_RANGE_INCONSISTENT: _DiagnosticSpec(
        code=COMPENSATION_RANGE_INCONSISTENT,
        message=_(
            "The min / mid / max rows of the range are inconsistent — "
            "min must be ≤ mid ≤ max. A Studio reviewer must correct "
            "the dataset before the range can be produced."
        ),
    ),
    INHERITANCE_SHARE_SPEC_INVALID: _DiagnosticSpec(
        code=INHERITANCE_SHARE_SPEC_INVALID,
        message=_(
            "The approved formula declares an invalid share specification. "
            "The engine refuses to produce an estimate; a Studio reviewer "
            "must correct the formula before any allocation can be shown."
        ),
    ),
    APPLICABLE_LAW_REVIEW_REQUIRED: _DiagnosticSpec(
        code=APPLICABLE_LAW_REVIEW_REQUIRED,
        message=_(
            "Applicable-law context requires Studio review before any "
            "inheritance shares can be produced. The engine refuses to "
            "compute on the fixture-only path until a legal reviewer "
            "reads the family and cross-border elements of the case."
        ),
    ),
    APPLICABLE_LAW_CONTEXT_MISSING: _DiagnosticSpec(
        code=APPLICABLE_LAW_CONTEXT_MISSING,
        message=_(
            "Applicable-law context is missing from the wizard input. "
            "The engine cannot decide which jurisdiction's law applies "
            "without the country of last residence."
        ),
    ),
    INPUT_FIELDS_MISSING: _DiagnosticSpec(
        code=INPUT_FIELDS_MISSING,
        message=_("Required input fields are missing for this calculation."),
    ),
    INPUT_ESTATE_VALUE_INVALID: _DiagnosticSpec(
        code=INPUT_ESTATE_VALUE_INVALID,
        message=_("Estate value is not a valid number."),
    ),
    INPUT_NEGATIVE_ESTATE: _DiagnosticSpec(
        code=INPUT_NEGATIVE_ESTATE,
        message=_("Estate value must be non-negative."),
    ),
    INPUT_NO_HEIR_ALLOCATION: _DiagnosticSpec(
        code=INPUT_NO_HEIR_ALLOCATION,
        message=_(
            "No heir class with a positive head count matches the approved "
            "share specification. Provide at least one heir covered by "
            "the formula (spouse, father, mother, sons, daughters)."
        ),
    ),
    ITALY_RANGE_COLLAPSED: _DiagnosticSpec(
        code=ITALY_RANGE_COLLAPSED,
        message=_(
            "The estimated min, central and max values coincide because the "
            "approved formula does not yet configure a personalisation "
            "range for this case. The figure is the canonical TUN amount "
            "for the matched age and disability."
        ),
        public_safe=True,
    ),
    ITALY_FIELD_NOT_AGGREGATED: _DiagnosticSpec(
        code=ITALY_FIELD_NOT_AGGREGATED,
        # The field name is interpolated by the engine via ``context``.
        message=_(
            "The reported {field} is not included in the automatic "
            "estimate: the approved formula does not aggregate this "
            "voice. The Studio reviews it case-by-case."
        ),
        public_safe=True,
    ),
    ITALY_FAULT_REDUCTION_APPLIED: _DiagnosticSpec(
        code=ITALY_FAULT_REDUCTION_APPLIED,
        message=_("A fault reduction was applied as declared by the approved " "formula."),
        public_safe=True,
    ),
    ITALY_FAULT_REDUCTION_APPLIED_UNIFORM: _DiagnosticSpec(
        code=ITALY_FAULT_REDUCTION_APPLIED_UNIFORM,
        message=_("A fault reduction was applied uniformly to the min, central " "and max values."),
        public_safe=True,
    ),
    ITALY_REQUIRED_INPUT_MISSING: _DiagnosticSpec(
        code=ITALY_REQUIRED_INPUT_MISSING,
        message=_(
            "Some fields needed for the estimate are missing: {fields}. "
            "Provide them and run the simulation again."
        ),
        public_safe=True,
    ),
    ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE: _DiagnosticSpec(
        code=ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE,
        message=_(
            "The percentage of fault must be between 0 and 100. The "
            "estimate cannot run with the value provided."
        ),
        public_safe=True,
    ),
    ITALY_INVALID_PERCENTAGE_INPUT: _DiagnosticSpec(
        code=ITALY_INVALID_PERCENTAGE_INPUT,
        message=_(
            "The percentage of fault is not a valid number. Use a digit " "between 0 and 100."
        ),
        public_safe=True,
    ),
    ITALY_INPUT_PAYLOAD_INVALID: _DiagnosticSpec(
        code=ITALY_INPUT_PAYLOAD_INVALID,
        message=_(
            "The wizard payload could not be parsed by the calculator. "
            "Studio review is required to identify the inconsistency."
        ),
    ),
    ITALY_FORMULA_INPUT_MISMATCH: _DiagnosticSpec(
        code=ITALY_FORMULA_INPUT_MISMATCH,
        message=_(
            "The approved formula declares input requirements that the "
            "wizard does not collect. A Studio reviewer must align the "
            "formula and the wizard before any estimate can be produced."
        ),
    ),
}


# Human-friendly labels for the dynamic context fields. Translated
# lazily so audit logs / FR / AR locales render the right name.
# Used by:
#   - ITALY_FIELD_NOT_AGGREGATED (single field)
#   - ITALY_REQUIRED_INPUT_MISSING (comma-joined list of fields)
_ITALY_FIELD_LABELS = {
    "medical_expenses": _("documented medical expenses"),
    "lost_income": _("lost income"),
    "victim_age": _("age of the injured person"),
    "permanent_disability_percentage": _("permanent disability percentage"),
    "total_temporary_disability_days": _("total temporary disability days"),
    "partial_temporary_disability_days": _("partial temporary disability days"),
    "fault_percentage": _("percentage of fault"),
    "accident_country": _("country of the accident"),
    "accident_date": _("date of the accident"),
    "heirs": _("family situation"),
    "estate_value": _("estimated estate value"),
    "deceased_country_of_last_residence": _("country of the deceased's last residence"),
    "nationality": _("nationality"),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def diagnostic_message(
    code: str,
    *,
    language: str | None = None,
    context: dict[str, Any] | None = None,
) -> str:
    """Return the localised message for ``code``.

    ``language`` activates the Django translation if given; ``None``
    keeps the current request's locale (or the project default if no
    request is active). ``context`` is interpolated into ``{name}``
    placeholders inside the message — used today by
    :data:`ITALY_FIELD_NOT_AGGREGATED`. Unknown keys silently render
    their literal placeholder (no KeyError) so diagnostics never raise.
    """
    spec = _REGISTRY.get(code)
    if spec is None:
        # Defensive: never raise from the diagnostic layer. Returning
        # the code itself keeps audit logs readable while flagging the
        # missing entry.
        return code

    rendered = _render(spec.message, language=language)
    if context:
        rendered = _safe_format(rendered, _localised_context(context, language=language))
    return rendered


def _render(message: Any, *, language: str | None) -> str:
    if language is None:
        return str(message)
    from django.utils import translation

    with translation.override(language):
        return str(message)


def _localised_context(context: dict[str, Any], *, language: str | None) -> dict[str, Any]:
    """Translate known field labels in ``context`` to the active locale.

    Only interpolation values that are project-known field slugs are
    swapped for their localised label; unknown values pass through
    untouched. Two slot shapes are handled:

    - ``"field"`` — single slug, swapped in place.
    - ``"fields"`` — list/tuple/iterable of slugs, joined with ", " and
      every slug looked up against the label dict (unknown slugs render
      their raw form).
    """
    out = dict(context)
    if "field" in out:
        label = _ITALY_FIELD_LABELS.get(out["field"])
        if label is not None:
            out["field"] = _render(label, language=language)
    if "fields" in out:
        raw = out["fields"]
        if isinstance(raw, (list, tuple, set, frozenset)):
            translated = []
            for slug in raw:
                label = _ITALY_FIELD_LABELS.get(slug)
                translated.append(_render(label, language=language) if label else str(slug))
            out["fields"] = ", ".join(translated)
    return out


def _safe_format(template: str, mapping: dict[str, Any]) -> str:
    class _SafeDict(dict):
        def __missing__(self, key):  # pragma: no cover - defensive
            return "{" + key + "}"

    try:
        return template.format_map(_SafeDict(mapping))
    except (IndexError, ValueError):  # pragma: no cover - defensive
        return template


def diagnostic_public_safe(code: str) -> bool:
    """Return ``True`` only for diagnostics vetted for public surfaces.

    Today every diagnostic is internal-only. The public result page
    renders the curated :class:`PublicResultMessage` instead. This
    helper exists so future iters can selectively expose specific
    codes (e.g. ``input_fields_missing`` could become public-safe
    once the wizard guarantees they are field-level errors).
    """
    spec = _REGISTRY.get(code)
    if spec is None:
        return False
    return spec.public_safe


def diagnostic_to_internal_warning(
    code: str,
    *,
    context: dict[str, Any] | None = None,
) -> str:
    """Return the engine-facing warning string for ``code``.

    Engines call this to populate ``CalculationResult.warnings`` and
    keep ``missing_documents=[code]`` for stable audit trails. The
    returned string is the localised message in the current request
    locale (lazy translation through :class:`gettext_lazy`).
    """
    return diagnostic_message(code, context=context)


def diagnostic_to_public_warning(
    code: str,
    *,
    language: str | None = None,
    context: dict[str, Any] | None = None,
) -> str:
    """Return a localised, public-safe warning string for ``code``.

    Raises :class:`ValueError` if the code is not flagged
    ``public_safe=True`` — engines that want to surface a public
    warning must use a code that has been vetted for end-user
    rendering.
    """
    if not diagnostic_public_safe(code):
        raise ValueError(
            f"diagnostic code {code!r} is not flagged public_safe — refusing "
            "to surface it on a public surface."
        )
    return diagnostic_message(code, language=language, context=context)


def known_diagnostic_codes() -> tuple[str, ...]:
    """Return the registered codes — handy for tests / audit reports."""
    return tuple(sorted(_REGISTRY))


__all__ = [
    "ITALY_RANGE_COLLAPSED",
    "ITALY_FIELD_NOT_AGGREGATED",
    "ITALY_FAULT_REDUCTION_APPLIED",
    "ITALY_FAULT_REDUCTION_APPLIED_UNIFORM",
    "ITALY_REQUIRED_INPUT_MISSING",
    "ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE",
    "ITALY_INVALID_PERCENTAGE_INPUT",
    "ITALY_INPUT_PAYLOAD_INVALID",
    "ITALY_FORMULA_INPUT_MISMATCH",
    "diagnostic_to_public_warning",
    "LEGAL_SOURCES_NOT_APPROVED",
    "COMPENSATION_DATASET_NOT_APPROVED",
    "RANGE_DATASET_NOT_APPROVED",
    "CALCULATION_FORMULA_NOT_APPROVED",
    "CALCULATOR_ENGINE_PENDING",
    "FORMULA_ENGINE_UNKNOWN",
    "FORMULA_AMOUNT_RULE_UNKNOWN",
    "FORMULA_AMOUNT_RULE_NOT_SINGLE_ROW_RANGE",
    "FORMULA_AMOUNT_RULE_NOT_INHERITANCE_SHARE",
    "FORMULA_ROW_TYPE_MISSING",
    "FORMULA_RANGE_PARAMETERS_INCOMPLETE",
    "COMPENSATION_ROW_MATCH_MISSING",
    "COMPENSATION_ROW_DISAMBIGUATION",
    "COMPENSATION_RANGE_INCONSISTENT",
    "INHERITANCE_SHARE_SPEC_INVALID",
    "APPLICABLE_LAW_REVIEW_REQUIRED",
    "APPLICABLE_LAW_CONTEXT_MISSING",
    "INPUT_FIELDS_MISSING",
    "INPUT_ESTATE_VALUE_INVALID",
    "INPUT_NEGATIVE_ESTATE",
    "INPUT_NO_HEIR_ALLOCATION",
    "diagnostic_message",
    "diagnostic_public_safe",
    "diagnostic_to_internal_warning",
    "known_diagnostic_codes",
]
