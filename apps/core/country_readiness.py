"""Public, leak-safe country readiness surface (E1).

A thin consolidation on top of :mod:`apps.core.public_status` that answers, per
supported country, the only questions the *public* needs: is the automatic
calculation available, and — if not — what is the transparent message and the
recommended action. It NEVER activates a calculation and NEVER exposes any
internal review detail (hashes, file paths, reviewer names, review notes, raw
legal text, D1/D2 readiness internals, or the internal status slug).

`internal_reason` exists only for logs/tests; ``as_public_dict()`` deliberately
omits it. Italy is available; FR/BE/MA/TN are ``official_guided_path``
(fail-closed) until the Studio approves their sources.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from django.utils.translation import gettext_lazy as _

from apps.core.public_status import (
    STATUS_AVAILABLE,
    get_country_public_status,
)

# Public 3-state surface (intentionally coarser than the internal status keys).
PUBLIC_AVAILABLE = "available"
PUBLIC_IN_VALIDATION = "official_guided_path"
PUBLIC_NOT_AVAILABLE = "not_available"

# Supported countries and the representative case type used to resolve status.
# Order matters: Italy first (the only available calculator today).
_SUPPORTED: tuple[tuple[str, Any, str], ...] = (
    ("IT", _("Italy"), "road_accident_bodily_injury"),
    ("FR", _("France"), "road_accident_bodily_injury"),
    ("BE", _("Belgium"), "road_accident_bodily_injury"),
    ("MA", _("Morocco"), "international_inheritance"),
    ("TN", _("Tunisia"), "international_inheritance"),
)


@dataclass(frozen=True)
class CountryReadiness:
    country_code: str
    label: Any
    public_status: str
    can_calculate: bool
    public_message: Any
    recommended_action: Any
    manual_review_available: bool
    # NOT public — logs/tests only. Excluded from as_public_dict().
    internal_reason: str

    def as_public_dict(self) -> dict[str, Any]:
        """JSON/template-safe projection. Never includes ``internal_reason``."""
        data = asdict(self)
        data.pop("internal_reason", None)
        # Render lazy strings eagerly so callers/serializers never leak proxies.
        data["label"] = str(self.label)
        data["public_message"] = str(self.public_message)
        data["recommended_action"] = str(self.recommended_action)
        return data


def _public_status_key(status_key: str) -> str:
    if status_key == STATUS_AVAILABLE:
        return PUBLIC_AVAILABLE
    # legal_assessment / inheritance_review / manual_review are all
    # "in legal validation" from the public's point of view (fail-closed).
    return PUBLIC_IN_VALIDATION


def get_country_readiness(country_code: str, case_type: str | None = None) -> CountryReadiness:
    """Public readiness for one country (+ optional case type)."""
    cc = (country_code or "").upper()
    label = next((lbl for code, lbl, _ct in _SUPPORTED if code == cc), cc)
    default_ct = next((ct for code, _lbl, ct in _SUPPORTED if code == cc), None)
    status = get_country_public_status(cc, case_type or default_ct)
    public_status = _public_status_key(status.status_key)
    can_calc = bool(status.is_calculation_available)
    return CountryReadiness(
        country_code=cc,
        label=label,
        public_status=public_status,
        can_calculate=can_calc,
        public_message=status.short_description,
        recommended_action=status.primary_cta_label,
        manual_review_available=True,  # the Studio always accepts a manual request
        internal_reason=(
            "active calculator backed by an approved national dataset"
            if can_calc
            else f"no active public calculator (internal status: {status.status_key})"
        ),
    )


def build_country_readiness() -> list[CountryReadiness]:
    """Readiness for every supported country (Italy first)."""
    return [get_country_readiness(code) for code, _lbl, _ct in _SUPPORTED]


def public_country_readiness() -> list[dict[str, Any]]:
    """Leak-safe public projection for templates / a JSON surface."""
    return [r.as_public_dict() for r in build_country_readiness()]
