"""Centralised premium copy for public country status badges & banners.

Iter origin: F-product-public-site-release-polish-pass5-premium-content-cleanup.

Avoids the "scaffold / placeholder / in preparation / legal validation
wizard / module pending / engine pending" wording that used to leak
into public pages. Each status now ships:

- ``label`` — the short badge text shown next to a country / case card.
- ``description`` — the longer explanation in card bodies.
- ``cta`` — the call-to-action label on the relevant button.
- ``no_amounts`` — the disclaimer explaining why no automatic amount
  is shown for this status.

All strings go through ``gettext_lazy`` so the values participate in
the ``makemessages`` extraction. Templates can either use these
constants directly via a context processor, or — for now — inline the
same wording as ``{% translate %}`` strings; both pull from the same
catalogue entries.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

# Canonical statuses for public country / case-type rendering.
STATUS_AVAILABLE = "available"
STATUS_LEGAL_ASSESSMENT = "legal_assessment"
STATUS_ON_REQUEST = "on_request"

PUBLIC_STATUS_COPY: dict[str, dict[str, str]] = {
    # Italy today: TUN 2025 dataset is approved → an indicative
    # calculation is available.
    STATUS_AVAILABLE: {
        "label": _("Indicative calculation available"),
        "description": _(
            "Indicative simulation based on the verified national dataset. "
            "The Studio remains available to review the case and discuss "
            "the next step."
        ),
        "cta": _("Run an indicative simulation"),
        "no_amounts": "",
    },
    # FR / BE road-accident: the Studio reviews each case manually
    # using verified quantification sources, no automatic amount is
    # published until the underlying tables are wired in.
    STATUS_LEGAL_ASSESSMENT: {
        "label": _("Preliminary legal assessment"),
        "description": _(
            "The Studio reviews the case manually, on the basis of the "
            "verified quantification sources for the relevant jurisdiction. "
            "No automatic amount is published before the case has been "
            "examined by a lawyer."
        ),
        "cta": _("Submit the case to the Studio"),
        "no_amounts": _(
            "No automatic amount is shown before the quantification "
            "sources have been verified for the case."
        ),
    },
    # MA / TN inheritance: the Studio reviews the case manually under
    # the applicable family-law regime; no shares are computed
    # automatically without an applicable-law mapping.
    STATUS_ON_REQUEST: {
        "label": _("International inheritance review"),
        "description": _(
            "The Studio reviews the case manually under the applicable "
            "family-law regime and EU Regulation 650/2012. Inheritance "
            "shares are not computed automatically without an applicable-"
            "law mapping for the case."
        ),
        "cta": _("Submit the case to the Studio"),
        "no_amounts": _(
            "Inheritance shares are not computed automatically without "
            "an applicable-law mapping for the case."
        ),
    },
}


def public_status_for_country(country_code: str, *, scaffold_only: bool, available: bool) -> str:
    """Return the canonical public-status key for a country card.

    The mapping is intentionally minimal:

    - ``available`` (Italy today) → ``available``.
    - ``scaffold_only`` (FR/BE road accident; MA/TN inheritance) →
      either ``legal_assessment`` (compensation cases) or
      ``on_request`` (inheritance cases). We disambiguate by country
      code so MA/TN read as inheritance reviews while FR/BE read as
      compensation reviews.
    - everything else (no public flow yet) → ``on_request``: we still
      offer a manual review rather than calling it "in preparation".
    """

    cc = country_code.upper()
    if available:
        return STATUS_AVAILABLE
    if scaffold_only:
        if cc in {"MA", "TN"}:
            return STATUS_ON_REQUEST
        return STATUS_LEGAL_ASSESSMENT
    # No public flow wired yet — still surface a "review on request"
    # badge rather than the banned "in preparation" wording.
    return STATUS_ON_REQUEST
