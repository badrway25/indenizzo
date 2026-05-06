"""Public-facing messaging for the wizard result page.

Iter: ``F-inheritance-wizard-result-page-localization-pass1``.

The result template historically rendered the calculator's raw
``warnings`` / ``missing_documents`` / ``assumptions`` arrays directly
into the public page. Those values are useful for audit logs and
internal debugging but they leak technical noise (English-only
strings, slugs like ``compensation_dataset_approved`` or
``unavailable_requires_legal_validation``, etc.) to end users.

This helper produces a clean :class:`PublicResultMessage` for every
result that does **not** carry an estimate. The calculated path is
not affected — Italy's TUN result keeps its existing premium
breakdown, sources card and disclaimer layout.

The module never inspects the backend diagnostics. It maps
``(country_code, case_type)`` to a tone-appropriate copy block. If a
new country/case combination lands here, ``DEFAULT_MESSAGE`` carries
a safe fallback that is still localised, premium and free of
technical noise.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class PublicResultMessage:
    """Localised, premium copy block shown when a result has no estimate.

    Every field carries a translatable string (lazy ``gettext_lazy``)
    so the same instance can be reused across locales.
    """

    public_title: str
    public_summary: str
    public_explanation: str
    public_next_steps: tuple[str, ...]
    primary_cta_label: str
    secondary_cta_label: str
    # Optional one-liner that clarifies the Studio's applicable-law
    # review for cross-border inheritance cases. Surfaced as a quiet
    # callout above the next-steps list when set; ignored otherwise.
    applicable_law_hint: str | None = None


# ---------------------------------------------------------------------------
# Per-jurisdiction copy blocks
# ---------------------------------------------------------------------------


_ROAD_ACCIDENT_PRELIMINARY_REVIEW = PublicResultMessage(
    public_title=_("Preliminary legal assessment"),
    public_summary=_(
        "Your case has been received for a preliminary legal " "assessment by the Studio."
    ),
    public_explanation=_(
        "A Studio lawyer reviews the facts and the applicable source "
        "material before any indicative amount is shown. The platform "
        "publishes amounts only when validated quantification sources "
        "are wired for the jurisdiction; for cross-border road "
        "accident cases the Studio prefers a manual reading of the "
        "case before any estimate is produced."
    ),
    public_next_steps=(
        _("A lawyer reads the case manually and replies on whether " "and how the firm can help."),
        _(
            "Keep the simulation reference below — the Studio uses it "
            "to retrieve the exact inputs of this run."
        ),
        _(
            "You can download a PDF of the submission for your records "
            "or to share with another professional."
        ),
    ),
    primary_cta_label=_("Request the Studio review"),
    secondary_cta_label=_("Back to the wizard"),
)


_INHERITANCE_REVIEW = PublicResultMessage(
    public_title=_("International inheritance review"),
    public_summary=_(
        "Your inheritance case has been received for manual legal " "review by the Studio."
    ),
    public_explanation=_(
        "A Studio lawyer examines the family structure, the "
        "applicable law and the cross-border elements before any "
        "inheritance shares are produced. The Moroccan and Tunisian "
        "frameworks (Moudawana / Code du statut personnel) interact "
        "with EU Regulation 650/2012 on a case-by-case basis: the "
        "platform does not publish automatic shares without that "
        "manual reading."
    ),
    public_next_steps=(
        _(
            "A lawyer reads the family situation and the patrimony "
            "context you entered, and identifies the law applicable "
            "to the succession."
        ),
        _(
            "Keep the simulation reference below — the Studio uses it "
            "to retrieve the exact inputs of this run."
        ),
        _(
            "You can download a PDF of the submission for your records "
            "or to share with another professional."
        ),
    ),
    primary_cta_label=_("Request the Studio review"),
    secondary_cta_label=_("Back to the wizard"),
    applicable_law_hint=_(
        "The Studio will review the applicable law and cross-border "
        "elements before any shares are calculated."
    ),
)


_DEFAULT_PRELIMINARY = PublicResultMessage(
    public_title=_("Preliminary legal assessment"),
    public_summary=_(
        "Your case has been received for a preliminary legal " "assessment by the Studio."
    ),
    public_explanation=_(
        "A Studio lawyer reviews the case before any indicative "
        "amount is published. The platform produces estimates only "
        "when validated quantification sources are wired for the "
        "jurisdiction and the case type."
    ),
    public_next_steps=(
        _("A lawyer reads the case manually and replies on whether " "and how the firm can help."),
        _(
            "Keep the simulation reference below — the Studio uses it "
            "to retrieve the exact inputs of this run."
        ),
    ),
    primary_cta_label=_("Request the Studio review"),
    secondary_cta_label=_("Back to the wizard"),
)


_INSUFFICIENT_INPUT = PublicResultMessage(
    public_title=_("More information needed"),
    public_summary=_("The Studio needs a little more context before it can review " "your case."),
    public_explanation=_(
        "Some of the inputs were not enough to identify the "
        "applicable law or the family structure. You can submit the "
        "case to the Studio with the context you have today — a "
        "lawyer will reply with the additional questions needed for "
        "a complete review."
    ),
    public_next_steps=(
        _("Submit the case to the Studio with what you know today."),
        _("A lawyer replies with the additional context the case " "needs."),
    ),
    primary_cta_label=_("Submit the case to the Studio"),
    secondary_cta_label=_("Back to the wizard"),
)


# ---------------------------------------------------------------------------
# Resolver
# ---------------------------------------------------------------------------


_INHERITANCE_CASES = {
    "international_inheritance",
    "inheritance",
}

_ROAD_ACCIDENT_CASES = {
    "road_accident_bodily_injury",
    "road_accident",
}


def build_public_result_message(
    *,
    status: str,
    country_code: str,
    case_type: str,
) -> PublicResultMessage:
    """Resolve the right :class:`PublicResultMessage` for a simulation.

    Pure function — no DB lookup, no raw diagnostic inspection. Pass
    the simulation's ``status``, the ISO country code and the
    case_type slug; the helper picks one of a small set of curated,
    pre-translated copy blocks.

    The mapping is intentionally narrow:

    - ``insufficient_input`` → "More information needed" copy regardless
      of country, because the case is salvageable but the user has to
      add context.
    - inheritance case types (MA, TN) → "International inheritance
      review" copy; the Moroccan / Tunisian framework + EU Reg. 650/2012
      story is shared.
    - road-accident case types where no estimate is produced (FR, BE,
      future jurisdictions while their sources are catalogued) →
      "Preliminary legal assessment" copy.
    - everything else → ``_DEFAULT_PRELIMINARY``.
    """
    case = (case_type or "").strip().lower()
    if status == "insufficient_input":
        return _INSUFFICIENT_INPUT
    if case in _INHERITANCE_CASES:
        return _INHERITANCE_REVIEW
    if case in _ROAD_ACCIDENT_CASES:
        return _ROAD_ACCIDENT_PRELIMINARY_REVIEW
    # Country-specific fallback could go here. Today the default is
    # plenty for every supported country/case while no estimate is
    # produced, and the centralised public_status panel renders the
    # case-specific badge above this copy.
    _ = country_code  # reserved for future country-specific tuning
    return _DEFAULT_PRELIMINARY


__all__ = [
    "PublicResultMessage",
    "build_public_result_message",
]
