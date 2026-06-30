"""Centralised premium copy for public country / case-type status.

Iter origin: F-product-public-site-release-polish-pass5-premium-content-cleanup.
Iter extension: F-product-public-status-centralization-pass6.

This module is the single source of truth for the user-facing wording
of country / case-type status across the public site. Templates pull
labels, descriptions and CTAs from here rather than inlining them, so
when a country flips from "Preliminary legal assessment" to
"Indicative calculation available" we only change one place.

Public API:

- ``get_country_public_status(country_code, case_type=None)`` — return
  the full ``PublicStatus`` object for a country / case-type pair.
- ``get_country_status_label(...)`` — short badge text.
- ``get_country_status_description(...)`` — long body description.
- ``get_country_primary_cta(...)`` — label of the primary CTA.
- ``get_country_no_amounts_message(...)`` — disclaimer line shown
  when no automatic amount is published.

All copy strings go through ``gettext_lazy`` so they participate in
``makemessages`` extraction.

Banned wording (never reintroduce in this file):
``scaffold | placeholder | under validation | in preparation |
coming soon | work in progress | in corso | legal validation wizard
| module pending | engine pending | missing_documents |
unavailable_requires_legal_validation``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils.translation import gettext_lazy as _

# Canonical status keys.  Kept stable so external code can rely on
# them; the user-visible wording lives in ``PublicStatus``.
STATUS_AVAILABLE = "available"
STATUS_LEGAL_ASSESSMENT = "legal_assessment"
STATUS_INHERITANCE_REVIEW = "inheritance_review"
STATUS_MANUAL_REVIEW = "manual_review"

# Backwards-compat alias used by pass-5 callers.
STATUS_ON_REQUEST = STATUS_INHERITANCE_REVIEW


@dataclass(frozen=True)
class PublicStatus:
    """User-facing status surface for a country / case-type pair.

    All ``str`` fields are lazy translations; they're ready to be
    rendered through Django's template engine without further
    wrapping.
    """

    status_key: str
    badge_label: Any  # gettext_lazy
    badge_variant: str  # "ok" | "gold" | "sand"
    short_description: Any
    long_description: Any
    primary_cta_label: Any
    secondary_cta_label: Any
    no_amounts_message: Any
    is_calculation_available: bool


# ---------------------------------------------------------------------------
# Concrete statuses
# ---------------------------------------------------------------------------


_AVAILABLE = PublicStatus(
    status_key=STATUS_AVAILABLE,
    badge_label=_("Indicative calculation available"),
    badge_variant="ok",
    short_description=_(
        "An indicative calculation is available, based on the verified "
        "national dataset for the chosen jurisdiction."
    ),
    long_description=_(
        "Indicative simulation based on the verified national dataset. "
        "The Studio remains available to review the case and discuss "
        "the next step."
    ),
    primary_cta_label=_("Run an indicative simulation"),
    secondary_cta_label=_("Request a Studio review of this case"),
    no_amounts_message="",
    is_calculation_available=True,
)


_LEGAL_ASSESSMENT = PublicStatus(
    status_key=STATUS_LEGAL_ASSESSMENT,
    badge_label=_("Assisted legal pathway"),
    badge_variant="gold",
    short_description=_(
        "The Studio offers an assisted legal pathway for this "
        "country: each case is reviewed manually and no automatic "
        "amount is published before the underlying quantification "
        "sources have been verified."
    ),
    long_description=_(
        "The Studio reviews the case manually, on the basis of the "
        "verified quantification sources for the relevant jurisdiction. "
        "No automatic amount is published before the case has been "
        "examined by a lawyer."
    ),
    primary_cta_label=_("Submit the case to the Studio"),
    secondary_cta_label=_("Request a dedicated legal review"),
    no_amounts_message=_(
        "No automatic amount is shown before the quantification "
        "sources have been verified for the case."
    ),
    is_calculation_available=False,
)


_INHERITANCE_REVIEW = PublicStatus(
    status_key=STATUS_INHERITANCE_REVIEW,
    badge_label=_("International inheritance review"),
    badge_variant="gold",
    short_description=_(
        "The Studio reviews each inheritance case manually; "
        "inheritance shares are not computed automatically without "
        "an applicable-law mapping for the case."
    ),
    long_description=_(
        "The Studio reviews the case manually under the applicable "
        "family-law regime and EU Regulation 650/2012. Inheritance "
        "shares are not computed automatically without an applicable-"
        "law mapping for the case."
    ),
    primary_cta_label=_("Submit the case to the Studio"),
    secondary_cta_label=_("Request a dedicated legal review"),
    no_amounts_message=_(
        "Inheritance shares are not computed automatically without "
        "an applicable-law mapping for the case."
    ),
    is_calculation_available=False,
)


_MANUAL_REVIEW = PublicStatus(
    status_key=STATUS_MANUAL_REVIEW,
    badge_label=_("Dedicated legal review"),
    badge_variant="sand",
    short_description=_(
        "The Studio offers a manual legal review for this country on "
        "request, while the national quantification dataset is being "
        "verified by our team."
    ),
    long_description=_(
        "A lawyer of the Studio reviews the case directly, on the "
        "basis of the legal sources of the relevant jurisdiction. "
        "No automatic amount is published until the underlying "
        "quantification dataset has been verified."
    ),
    primary_cta_label=_("Request a dedicated legal review"),
    secondary_cta_label=_("Contact the Studio"),
    no_amounts_message=_(
        "No automatic amount is published until the underlying "
        "quantification dataset has been verified for this country."
    ),
    is_calculation_available=False,
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

# (country_code, case_type_prefix) → PublicStatus.  case_type_prefix
# is matched against the start of the case-type slug so that, e.g.,
# both ``road_accident_bodily_injury`` and a future
# ``road_accident_property`` map to the same France status.
_RULES: tuple[tuple[str, str, PublicStatus], ...] = (
    ("IT", "road_accident", _AVAILABLE),
    ("FR", "road_accident", _LEGAL_ASSESSMENT),
    ("BE", "road_accident", _LEGAL_ASSESSMENT),
    ("MA", "international_inheritance", _INHERITANCE_REVIEW),
    ("MA", "inheritance", _INHERITANCE_REVIEW),
    ("TN", "international_inheritance", _INHERITANCE_REVIEW),
    ("TN", "inheritance", _INHERITANCE_REVIEW),
)


def get_country_public_status(
    country_code: str | None,
    case_type: str | None = None,
) -> PublicStatus:
    """Return the user-facing status for a country / case-type pair.

    The mapping is intentionally minimal:

    - Italy + any road-accident case type → ``_AVAILABLE`` (the
      calculator is the verified TUN 2025 dataset).
    - France / Belgium + any road-accident case type → preliminary
      legal assessment.
    - Morocco / Tunisia + any inheritance case type → international
      inheritance review.
    - Anything else → manual legal review on request. We never
      reintroduce "in preparation" / "coming soon" wording.

    ``case_type`` is matched as a prefix so adding a sibling case type
    in the same family does not break the mapping.
    """

    cc = (country_code or "").upper()
    ct = (case_type or "").lower()
    for rule_cc, rule_prefix, status in _RULES:
        if cc == rule_cc and (not ct or ct.startswith(rule_prefix)):
            return status
    return _MANUAL_REVIEW


def get_country_status_label(
    country_code: str | None,
    case_type: str | None = None,
) -> Any:
    """Short badge label for the country / case-type."""

    return get_country_public_status(country_code, case_type).badge_label


def get_country_status_description(
    country_code: str | None,
    case_type: str | None = None,
) -> Any:
    """Long-form body description shown on country / case-type cards."""

    return get_country_public_status(country_code, case_type).short_description


def get_country_primary_cta(
    country_code: str | None,
    case_type: str | None = None,
) -> Any:
    """Label of the primary CTA button (gold or ink-fill)."""

    return get_country_public_status(country_code, case_type).primary_cta_label


def get_country_no_amounts_message(
    country_code: str | None,
    case_type: str | None = None,
) -> Any:
    """Disclaimer about no automatic amount being shown.

    Returns the empty string when an automatic amount IS published
    (so callers can render it unconditionally without showing a
    contradictory warning on countries with a live calculator).
    """

    return get_country_public_status(country_code, case_type).no_amounts_message


# ---------------------------------------------------------------------------
# Backwards-compat (pass-5 callers)
# ---------------------------------------------------------------------------


PUBLIC_STATUS_COPY: dict[str, dict[str, Any]] = {
    STATUS_AVAILABLE: {
        "label": _AVAILABLE.badge_label,
        "description": _AVAILABLE.long_description,
        "cta": _AVAILABLE.primary_cta_label,
        "no_amounts": _AVAILABLE.no_amounts_message,
    },
    STATUS_LEGAL_ASSESSMENT: {
        "label": _LEGAL_ASSESSMENT.badge_label,
        "description": _LEGAL_ASSESSMENT.long_description,
        "cta": _LEGAL_ASSESSMENT.primary_cta_label,
        "no_amounts": _LEGAL_ASSESSMENT.no_amounts_message,
    },
    STATUS_INHERITANCE_REVIEW: {
        "label": _INHERITANCE_REVIEW.badge_label,
        "description": _INHERITANCE_REVIEW.long_description,
        "cta": _INHERITANCE_REVIEW.primary_cta_label,
        "no_amounts": _INHERITANCE_REVIEW.no_amounts_message,
    },
}


def public_status_for_country(country_code: str, *, scaffold_only: bool, available: bool) -> str:
    """Pass-5 helper kept for back-compat — returns just the status key.

    Prefer ``get_country_public_status`` for new code.
    """

    if available:
        return STATUS_AVAILABLE
    if scaffold_only:
        if (country_code or "").upper() in {"MA", "TN"}:
            return STATUS_INHERITANCE_REVIEW
        return STATUS_LEGAL_ASSESSMENT
    return STATUS_MANUAL_REVIEW
