"""P17 — the single public-facing humaniser for internal codes and slugs.

No technical identifier (CaseType enum value, pre-check slug, jurisdiction key,
snake_case code) may ever reach the rendered page. Anything shown to the public
goes through ``humanize()``, which maps a known code to a premium, translatable
label and, defensively, never echoes a raw snake_case token for an unknown code
(it title-cases it instead). This is the canonical mapping the public-copy guard
test checks against.
"""

from __future__ import annotations

from django.utils.translation import gettext_lazy as _

# Premium public labels — keyed by the internal code (CaseType value or slug).
# Wording is deliberately legal, human and concise; translated in IT/FR/AR.
PUBLIC_LABELS: dict[str, str] = {
    # Road accident family.
    "road_accident": _("Road accident with injuries"),
    "road_accident_bodily_injury": _("Road accident with injuries"),
    "road_accident_microlesions": _("Road accident — minor injuries"),
    # Medical.
    "medical_malpractice": _("Healthcare liability"),
    "medical_liability": _("Healthcare liability"),
    "medical_liability_biological": _("Healthcare liability — biological damage"),
    # Work.
    "work_injury": _("Workplace injury"),
    # Death / family.
    "loss_of_relative": _("Loss of a relative"),
    "death_of_relative": _("Loss of a relative"),
    "death_compensation": _("Compensation for a death"),
    "parental_loss": _("Loss of the parental bond"),
    # Patrimonial / product / offer.
    "patrimonial_damage": _("Economic loss"),
    "product_liability": _("Defective product"),
    "insurance_offer": _("Insurance-offer check"),
    # Succession.
    "inheritance_basic": _("Succession"),
    "international_inheritance": _("International succession"),
    # Cross-border road.
    "morocco_road_accident": _("Road accident in Morocco"),
    "tunisia_road_accident": _("Road accident in Tunisia"),
    "international_road_accident": _("Cross-border accident"),
    # Generic.
    "generic_legal_assessment": _("Legal assessment"),
}


def humanize(code: str | None) -> str:
    """Return the public label for an internal code.

    Known codes map to their premium label. Unknown codes are title-cased with
    spaces so a raw snake_case identifier can never surface in public copy.
    """
    if not code:
        return ""
    if code in PUBLIC_LABELS:
        return PUBLIC_LABELS[code]
    return str(code).replace("_", " ").replace("-", " ").strip().capitalize()
