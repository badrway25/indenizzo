"""P15 — country × category guided router.

A single, navigable entry point: the visitor picks a country, then a category,
and the platform routes to the RIGHT destination for that pair — never a generic
page and never an invented amount. The routing decision is data-driven and
mirrors the live engines / pre-check flows:

- ``estimate``        → an approved numeric engine exists (IT road accident).
- ``tabular``         → an approved official table drives the figure (IT medical).
- ``comparison``      → an approved engine reused to compare an offer (IT offer).
- ``pre_check``       → official source but no table yet → documental pre-check.
- ``guided``          → assisted path on official sources (no state table).
- ``applicable_law``  → cross-border framing before any quantification.

The status labels are the SAME gettext strings used by the estimate badges
(P13) and the pre-check flows (P15), so the public wording never diverges.

Cardinal rule: this router only *routes*. No amount, coefficient or table is
computed here.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils.translation import gettext_lazy as _

# Routing statuses — reused verbatim from the estimate badges / pre-check labels.
ESTIMATE = "estimate"
TABULAR = "tabular"
COMPARISON = "comparison"
PRE_CHECK = "pre_check"
GUIDED = "guided"
APPLICABLE_LAW = "applicable_law"

STATUS_LABEL = {
    ESTIMATE: _("Estimate based on official sources"),
    TABULAR: _("Official table-based biological damage estimate"),
    COMPARISON: _("Comparison based on official sources"),
    PRE_CHECK: _("Documental pre-check with official sources"),
    GUIDED: _("Assisted path based on official sources"),
    APPLICABLE_LAW: _("Applicable-law framing"),
}

# Whether the destination produces a real numeric range. Drives the
# "what calculates / what does not" copy and guards against money leaks.
COMPUTES_AMOUNT = {ESTIMATE, TABULAR, COMPARISON}


@dataclass(frozen=True)
class Route:
    country_code: str  # ISO-2 or "INT"
    country_key: str  # gettext country name
    category_id: str  # locale-stable category key (matched by resolve())
    category_key: str  # gettext category label (rendered)
    status: str
    url_name: str
    url_kwargs: dict = field(default_factory=dict)
    min_inputs: str = ""  # P16: the minimal data the visitor will need
    main_source: str = ""  # P25: the primary normative reference (preview)

    @property
    def status_label(self):
        return STATUS_LABEL[self.status]

    @property
    def computes_amount(self) -> bool:
        return self.status in COMPUTES_AMOUNT

    @property
    def est_time(self):
        """P25: an honest, non-monetary indication of how long the path takes."""
        if self.computes_amount:
            return _("about 4–6 minutes")
        return _("about 3–5 minutes")

    @property
    def cta_label(self):
        """A direct CTA that reflects the actual destination (P16)."""
        if self.computes_amount:
            return _("Open the calculator")
        if self.status == APPLICABLE_LAW:
            return _("Frame the applicable law")
        if self.url_name.startswith("cases:wizard"):
            # France / Belgium → guided legal pathway (wizard with checklist).
            return _("Check documents and liability")
        return _("Start the pre-check")


# Order matters: Italy first (most live), then the official-source countries,
# then the cross-border framing. Each row is grounded in a live engine or a
# real pre-check flow — nothing aspirational.
# Shared minimal-input hints (bound the translation surface).
_IN_ROAD_ENGINE = _("Injury percentage and accident details")
_IN_ROAD_PRECHECK = _("Injury or death, incapacity and documents")
_IN_ROAD_GUIDED = _("Accident details and supporting documents")

ROUTES: tuple[Route, ...] = (
    Route("IT", _("Italy"), "road_accident", _("Road accident"), ESTIMATE,
          "cases:wizard_italy_road_accident", min_inputs=_IN_ROAD_ENGINE,
          main_source="art. 139 CAP · Tabella Unica Nazionale 2025"),
    Route("IT", _("Italy"), "medical_liability", _("Medical liability"), TABULAR,
          "cases:wizard_italy_medical", min_inputs=_("Medical-legal impairment percentage"),
          main_source="L. 24/2017 · artt. 138–139 CAP"),
    Route("IT", _("Italy"), "insurance_offer", _("Insurance offer"), COMPARISON,
          "cases:wizard_insurance_offer", min_inputs=_("The offer amount and the injury details"),
          main_source="art. 139 CAP · Tabella Unica Nazionale 2025"),
    Route("IT", _("Italy"), "work_injury", _("Work injury (INAIL)"), PRE_CHECK,
          "core:precheck", {"slug": "inail"}, min_inputs=_("Event date, impairment and documents"),
          main_source="D.P.R. 1124/1965 (T.U. INAIL)"),
    Route("IT", _("Italy"), "loss_of_relative", _("Loss of a relative"), GUIDED,
          "core:precheck", {"slug": "loss-of-relative"},
          min_inputs=_("Relationship, cause of death and documents"),
          main_source="artt. 2043, 2059 Cod. Civile"),
    Route("MA", _("Morocco"), "road_accident", _("Road accident"), PRE_CHECK,
          "core:precheck", {"slug": "morocco-road-accident"}, min_inputs=_IN_ROAD_PRECHECK,
          main_source="Dahir 1-84-177 · ACAPS"),
    Route("TN", _("Tunisia"), "road_accident", _("Road accident"), PRE_CHECK,
          "core:precheck", {"slug": "tunisia-road-accident"}, min_inputs=_IN_ROAD_PRECHECK,
          main_source="Loi 2005-86 (Code des assurances)"),
    Route("FR", _("France"), "road_accident", _("Road accident"), GUIDED,
          "cases:wizard_france_road_accident", min_inputs=_IN_ROAD_GUIDED,
          main_source="Loi Badinter (loi 85-677)"),
    Route("BE", _("Belgium"), "road_accident", _("Road accident"), GUIDED,
          "cases:wizard_belgium_road_accident", min_inputs=_IN_ROAD_GUIDED,
          main_source="Indicatieve tabel / Tableau indicatif"),
    Route("INT", _("International"), "cross_border", _("Cross-border road accident"),
          APPLICABLE_LAW, "core:precheck", {"slug": "international-road-accident"},
          min_inputs=_("The countries involved and the documents"),
          main_source="Reg. (CE) 864/2007 (Roma II)"),
)


def grouped_routes() -> list[dict]:
    """Routes grouped by country, preserving declaration order — for the page."""
    order: list[str] = []
    by_country: dict[str, dict] = {}
    for route in ROUTES:
        if route.country_code not in by_country:
            order.append(route.country_code)
            by_country[route.country_code] = {
                "country_code": route.country_code,
                "country_key": route.country_key,
                "routes": [],
            }
        by_country[route.country_code]["routes"].append(route)
    return [by_country[code] for code in order]


def resolve(country_code: str, category_id: str) -> Route | None:
    """Resolve a (country, category) pair to its routing decision (or None).

    ``category_id`` is the locale-stable category key (e.g. ``"road_accident"``),
    so callers/tests resolve identically regardless of the active locale.
    """
    for route in ROUTES:
        if route.country_code == country_code and route.category_id == category_id:
            return route
    return None
