"""Applicable-law decision skeleton for international inheritance cases.

Iter: ``F-eu-650-2012-applicable-law-decision-engine-skeleton``.

The wizard (``apps/cases/forms.py::InternationalInheritanceWizardForm``)
collects four signals that ultimately drive the applicable-law
decision under EU Regulation 650/2012, the Moroccan Moudawana / Code
des droits réels and the Tunisian Code du statut personnel + Loi
n° 98-97:

- ``deceased_country_of_last_residence`` — habitual residence at
  death (Art. 21 Reg. 650/2012 default rule).
- ``nationality`` — relevant for ``professio juris`` choices
  (Art. 22 Reg. 650/2012) and for renvoi mechanics with non-EU
  laws like the Moroccan / Tunisian frameworks.
- ``has_will`` — flags whether a written disposition (and a possible
  professio juris clause) exists; if true, the case is inherently a
  manual-review case.
- ``assets_countries`` — list of ISO codes where assets are located;
  more than one country triggers cross-border review.

This module turns those signals into a structured
:class:`ApplicableLawDecision`. The decision is **preliminary** and
**fixture-only**: the heuristics are deliberately narrow, do not
perform renvoi, do not honour public-policy exceptions, and never
phrase any conclusion as a legal certainty. The Studio reviews every
real case manually.

The output never reaches the public surface verbatim. It is stashed
under ``Simulation.output_data["internal"]["applicable_law_decision"]``
for audit / Studio review and never rendered on the public template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Decision keys — narrow vocabulary for stable serialisation
# ---------------------------------------------------------------------------

DECISION_INSUFFICIENT_CONTEXT = "insufficient_context"
DECISION_HABITUAL_RESIDENCE = "habitual_residence_default"
DECISION_PROFESSIO_JURIS_CANDIDATE = "professio_juris_candidate"
DECISION_CROSS_BORDER_FRAGMENTATION = "cross_border_fragmentation"


CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"


_ISO_RE = re.compile(r"^[A-Za-z]{2}$")


@dataclass(frozen=True)
class ApplicableLawInput:
    """Wizard-derived input for the decision skeleton.

    Every field is optional because the wizard does not require any of
    them. Validators normalise empty / None values; the evaluator
    reasons over what's actually provided.
    """

    deceased_country_of_last_residence: str | None = None
    nationality: str | None = None
    has_will: bool | None = None
    assets_countries: tuple[str, ...] = field(default_factory=tuple)
    forum_country: str | None = None


@dataclass(frozen=True)
class ApplicableLawDecision:
    """Structured, stable, audit-friendly decision payload.

    ``preliminary_law_country`` is **never** treated as a final
    conclusion: callers must surface ``requires_manual_review`` and
    leave the actual choice of law to the Studio. ``applied_rules``
    enumerates the heuristic gates that fired so a reviewer can see
    why a case was flagged.
    """

    decision_key: str
    preliminary_law_country: str | None
    confidence: str
    requires_manual_review: bool
    reasons: tuple[str, ...]
    warnings: tuple[str, ...]
    applied_rules: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "decision_key": self.decision_key,
            "preliminary_law_country": self.preliminary_law_country,
            "confidence": self.confidence,
            "requires_manual_review": self.requires_manual_review,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "applied_rules": list(self.applied_rules),
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalise_iso(value: Any) -> str | None:
    if value is None:
        return None
    s = str(value).strip().upper()
    if not s:
        return None
    if not _ISO_RE.match(s):
        return None
    return s


def normalise_assets_countries(value: Any) -> tuple[str, ...]:
    """Accept comma-separated string or sequence; return ISO tuple.

    Skips entries that are not 2-letter ISO codes after stripping
    whitespace. Order is preserved; duplicates are removed.
    """
    if value is None:
        return ()
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",")]
    else:
        try:
            parts = [str(p).strip() for p in value]
        except TypeError:
            return ()
    seen: list[str] = []
    for raw in parts:
        iso = _normalise_iso(raw)
        if iso is None:
            continue
        if iso not in seen:
            seen.append(iso)
    return tuple(seen)


def build_applicable_law_input_from_payload(payload: dict[str, Any]) -> ApplicableLawInput:
    """Build :class:`ApplicableLawInput` from a wizard ``input_data``.

    Tolerant to the legacy and new key names so this helper can be
    called from both the form layer and downstream services / tests.
    """
    ctx = payload.get("applicable_law_context")
    if isinstance(ctx, dict):
        return ApplicableLawInput(
            deceased_country_of_last_residence=_normalise_iso(
                ctx.get("deceased_country_of_last_residence")
            ),
            nationality=_normalise_iso(ctx.get("nationality")),
            has_will=ctx.get("has_will"),
            assets_countries=normalise_assets_countries(ctx.get("assets_countries")),
            forum_country=_normalise_iso(ctx.get("forum_country")),
        )
    return ApplicableLawInput(
        deceased_country_of_last_residence=_normalise_iso(
            payload.get("deceased_country_of_last_residence")
        ),
        nationality=_normalise_iso(payload.get("nationality")),
        has_will=payload.get("has_will"),
        assets_countries=normalise_assets_countries(payload.get("assets_countries")),
        forum_country=_normalise_iso(payload.get("forum_country")),
    )


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def evaluate_inheritance_applicable_law(
    payload: ApplicableLawInput | dict[str, Any],
) -> ApplicableLawDecision:
    """Produce a preliminary, manual-review-aware decision.

    The function is intentionally narrow — it never claims a final
    conclusion and never overrides Studio judgment. Heuristics:

    1. ``last_residence`` missing → ``insufficient_context``,
       ``requires_manual_review = True``.
    2. ``last_residence`` present → ``preliminary_law_country`` is set
       to that ISO code with ``decision_key = habitual_residence_default``.
       Confidence starts at ``medium`` and is downgraded by the gates
       below.
    3. ``has_will == True`` → ``decision_key`` becomes
       ``professio_juris_candidate``, confidence drops to ``low``,
       manual review is required.
    4. ``assets_countries`` includes more than one country → confidence
       drops to ``low``, manual review is required, decision_key may
       become ``cross_border_fragmentation`` if more than two
       countries appear.
    5. ``nationality`` differs from ``last_residence`` → manual review
       is required, confidence stays ``low``.

    The result preserves the *order* of fired rules in
    ``applied_rules`` so audit logs read like a checklist.
    """
    if isinstance(payload, dict):
        inp = build_applicable_law_input_from_payload(payload)
    else:
        inp = payload

    reasons: list[str] = []
    warnings: list[str] = []
    applied_rules: list[str] = []

    if inp.deceased_country_of_last_residence is None:
        applied_rules.append("rule_last_residence_missing")
        reasons.append(
            "Country of last residence not provided; the applicable-law "
            "decision cannot proceed at the heuristic level."
        )
        warnings.append(
            "Insufficient context to suggest a preliminary applicable "
            "law; Studio review is required to identify the relevant "
            "framework."
        )
        return ApplicableLawDecision(
            decision_key=DECISION_INSUFFICIENT_CONTEXT,
            preliminary_law_country=None,
            confidence=CONFIDENCE_LOW,
            requires_manual_review=True,
            reasons=tuple(reasons),
            warnings=tuple(warnings),
            applied_rules=tuple(applied_rules),
        )

    last_residence = inp.deceased_country_of_last_residence
    decision_key = DECISION_HABITUAL_RESIDENCE
    confidence = CONFIDENCE_MEDIUM
    requires_manual_review = False
    applied_rules.append("rule_habitual_residence_default")
    reasons.append(
        "Country of last residence provided; that jurisdiction is the "
        "preliminary working hypothesis for the applicable law."
    )

    if inp.has_will is True:
        applied_rules.append("rule_has_will_present")
        decision_key = DECISION_PROFESSIO_JURIS_CANDIDATE
        confidence = CONFIDENCE_LOW
        requires_manual_review = True
        warnings.append(
            "A will is reported; a professio juris clause may apply "
            "and must be read by a Studio lawyer before any conclusion."
        )

    asset_count = len(inp.assets_countries)
    if asset_count >= 2:
        applied_rules.append("rule_assets_multi_country")
        confidence = CONFIDENCE_LOW
        requires_manual_review = True
        warnings.append(
            f"Assets span {asset_count} countries; cross-border "
            "fragmentation may require coordination with the relevant "
            "fora before any allocation can be produced."
        )
        if asset_count >= 3:
            decision_key = DECISION_CROSS_BORDER_FRAGMENTATION

    if inp.nationality is not None and inp.nationality != last_residence:
        applied_rules.append("rule_nationality_differs_from_residence")
        confidence = CONFIDENCE_LOW
        requires_manual_review = True
        warnings.append(
            "Nationality differs from country of last residence; "
            "renvoi and the choice between national and residence law "
            "must be considered by a Studio lawyer."
        )

    return ApplicableLawDecision(
        decision_key=decision_key,
        preliminary_law_country=last_residence,
        confidence=confidence,
        requires_manual_review=requires_manual_review,
        reasons=tuple(reasons),
        warnings=tuple(warnings),
        applied_rules=tuple(applied_rules),
    )


# ---------------------------------------------------------------------------
# Engine integration gate (fixture-only)
# ---------------------------------------------------------------------------


# Internal diagnostic slugs the engine uses when the gate blocks. They
# stay under ``output_data["internal"]`` and never reach the public
# template (the result page only renders the curated public message).
BLOCK_REASON_NO_DECISION = "applicable_law_decision_missing"
BLOCK_REASON_INSUFFICIENT_CONTEXT = "applicable_law_insufficient_context"
BLOCK_REASON_MANUAL_REVIEW_REQUIRED = "applicable_law_manual_review_required"
BLOCK_REASON_LOW_CONFIDENCE = "applicable_law_low_confidence"
BLOCK_REASON_MISSING_LAW_COUNTRY = "applicable_law_missing_law_country"


def can_run_inheritance_share_engine(decision: ApplicableLawDecision | None) -> bool:
    """Gate that decides whether an inheritance-share engine may run.

    Strictly fixture-only: the engine is allowed to compute shares
    only when the applicable-law decision is the simplest possible
    "habitual residence default" with medium-or-better confidence and
    no manual-review flag. Any other shape (insufficient context,
    professio juris candidate, cross-border fragmentation, nationality
    mismatch, low confidence) blocks the engine.

    Returns ``False`` for ``None`` so callers that don't yet attach a
    decision get the safest default. The wider system never exposes a
    public quote when this returns ``False``; the engine surfaces an
    internal diagnostic via :func:`inheritance_engine_block_reason`
    that lives only in ``Simulation.output_data["internal"]``.
    """
    if decision is None:
        return False
    if decision.decision_key != DECISION_HABITUAL_RESIDENCE:
        return False
    if decision.requires_manual_review:
        return False
    if not decision.preliminary_law_country:
        return False
    if decision.confidence not in (CONFIDENCE_MEDIUM, CONFIDENCE_HIGH):
        return False
    return True


def inheritance_engine_block_reason(decision: ApplicableLawDecision | None) -> str:
    """Pick a stable internal slug describing why the gate blocks.

    The slug is intended for ``Simulation.output_data["internal"]`` and
    Studio audit logs only. The public result page renders the curated
    :class:`apps.cases.public_result_messages.PublicResultMessage`,
    never these slugs.
    """
    if decision is None:
        return BLOCK_REASON_NO_DECISION
    if decision.decision_key == DECISION_INSUFFICIENT_CONTEXT:
        return BLOCK_REASON_INSUFFICIENT_CONTEXT
    if decision.requires_manual_review:
        return BLOCK_REASON_MANUAL_REVIEW_REQUIRED
    if not decision.preliminary_law_country:
        return BLOCK_REASON_MISSING_LAW_COUNTRY
    if decision.confidence not in (CONFIDENCE_MEDIUM, CONFIDENCE_HIGH):
        return BLOCK_REASON_LOW_CONFIDENCE
    return ""


__all__ = [
    "ApplicableLawInput",
    "ApplicableLawDecision",
    "DECISION_INSUFFICIENT_CONTEXT",
    "DECISION_HABITUAL_RESIDENCE",
    "DECISION_PROFESSIO_JURIS_CANDIDATE",
    "DECISION_CROSS_BORDER_FRAGMENTATION",
    "CONFIDENCE_LOW",
    "CONFIDENCE_MEDIUM",
    "CONFIDENCE_HIGH",
    "BLOCK_REASON_NO_DECISION",
    "BLOCK_REASON_INSUFFICIENT_CONTEXT",
    "BLOCK_REASON_MANUAL_REVIEW_REQUIRED",
    "BLOCK_REASON_LOW_CONFIDENCE",
    "BLOCK_REASON_MISSING_LAW_COUNTRY",
    "build_applicable_law_input_from_payload",
    "can_run_inheritance_share_engine",
    "evaluate_inheritance_applicable_law",
    "inheritance_engine_block_reason",
    "normalise_assets_countries",
]
