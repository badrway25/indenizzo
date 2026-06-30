"""P28 — unified dossier summary for public results.

A single logical view over EVERY public outcome — the three live estimates
(road, medical, offer comparison) and the five documental pre-checks
(INAIL, loss-of-relative, Morocco, Tunisia, international) — so the result
templates, the print layout and the contact payload all read from the same
shape instead of each result type rolling its own.

Stateless: built on demand from the data the view already has (a
``PreCheckResult`` + flow, or a ``Simulation`` + its display context). No DB
model, no migration. It NEVER invents an amount: ``amount_summary`` is filled
only when a real approved engine produced a figure.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from django.utils.translation import gettext_lazy as _

# A raw internal/diagnostic code looks like snake_case with no spaces; never
# surface those publicly (e.g. an engine warning key).
_RAW_CODE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")


def _human_only(items) -> tuple:
    """Keep only human-readable, non-empty strings (drop raw snake_case codes)."""
    out = []
    for it in items or ():
        text = str(it).strip()
        if text and not _RAW_CODE.match(text):
            out.append(text)
    return tuple(out)

# result_kind values (stable, locale-independent).
KIND_ESTIMATE = "estimate"
KIND_COMPARISON = "comparison"
KIND_PRE_CHECK = "pre_check"
KIND_APPLICABLE_LAW = "applicable_law"

# Pre-check slug → (flow_type, category, result_kind). flow_type/category are
# stable analytics keys; result_kind drives the top-line wording.
_PRECHECK_MAP = {
    "inail": ("inail", "work_injury", KIND_PRE_CHECK),
    "loss-of-relative": ("loss_of_relative", "loss_of_relative", KIND_PRE_CHECK),
    "morocco-road-accident": ("morocco_road", "road_accident", KIND_PRE_CHECK),
    "tunisia-road-accident": ("tunisia_road", "road_accident", KIND_PRE_CHECK),
    "international-road-accident": ("international", "cross_border", KIND_APPLICABLE_LAW),
}

# Top-line status wording per result_kind (no weak states, no money).
RESULT_KIND_LABEL = {
    KIND_ESTIMATE: _("Estimate calculated"),
    KIND_COMPARISON: _("Comparison completed"),
    KIND_PRE_CHECK: _("Dossier ready for analysis"),
    KIND_APPLICABLE_LAW: _("Applicable-law framing"),
}

_DISCLAIMER = _("This summary is indicative and does not constitute legal advice or a "
                "guarantee of outcome. The actual assessment depends on the documents, "
                "the applicable law and the competent court.")


@dataclass(frozen=True)
class DossierCta:
    label: Any
    url_name: str
    kwargs: dict = field(default_factory=dict)
    query: dict = field(default_factory=dict)


@dataclass(frozen=True)
class DossierSummary:
    flow_type: str
    country: str
    category: str
    language: str
    result_kind: str
    can_calculate_amount: bool = False
    amount_summary: str = ""              # ONLY set for an approved-engine figure
    readiness_level: str = ""
    readiness_score: int = 0
    data_used: tuple = ()                 # the solid points already provided
    missing_data: tuple = ()              # points still to verify
    documents_present: tuple = ()
    documents_missing: tuple = ()
    official_sources: tuple = ()
    next_steps: tuple = ()
    primary_cta: Any = None               # DossierCta | None
    secondary_cta: Any = None             # DossierCta | None
    disclaimer: Any = _DISCLAIMER

    @property
    def result_kind_label(self):
        return RESULT_KIND_LABEL.get(self.result_kind, "")

    @property
    def contact_query(self) -> dict:
        """The structured, privacy-safe origin passed to the contact form."""
        q = {
            "flow": self.flow_type,
            "result_kind": self.result_kind,
            "readiness": self.readiness_level,
        }
        if self.country:
            q["country"] = self.country
        if self.category:
            q["category"] = self.category
        return {k: v for k, v in q.items() if v}


def from_precheck(flow, result, language: str) -> DossierSummary:
    """Build a DossierSummary from a pre-check flow + its evaluated result."""
    flow_type, category, result_kind = _PRECHECK_MAP.get(
        flow.slug, (flow.slug, "", KIND_PRE_CHECK))
    docs_present = tuple(d.label for d in result.document_items if d.present)
    docs_missing = tuple(d.label for d in result.document_items
                         if d.category == "essential" and not d.present) or result.missing_documents
    next_steps = tuple(result.messages) + ((result.next_step,) if result.next_step else ())
    query = {"flow": flow_type, "result_kind": result_kind, "readiness": result.result_status}
    if flow.country_code and flow.country_code != "INT":
        query["country"] = flow.country_code
    if category:
        query["category"] = category
    primary = DossierCta(
        label=_("Send the summary to the Studio"),
        url_name="crm:contact",
        query=query,
    )
    secondary = DossierCta(label=_("Back to the guided path"), url_name="core:guided_router")
    return DossierSummary(
        flow_type=flow_type,
        country=flow.country_code if flow.country_code != "INT" else "",
        category=category,
        language=language,
        result_kind=result_kind,
        can_calculate_amount=False,
        readiness_level=result.result_status,
        readiness_score=result.readiness_pct,
        data_used=tuple(result.strong_points),
        missing_data=tuple(result.attention_points),
        documents_present=docs_present,
        documents_missing=tuple(docs_missing),
        official_sources=tuple(result.applicable_sources),
        next_steps=next_steps,
        primary_cta=primary,
        secondary_cta=secondary,
    )


def from_estimate(simulation, *, has_estimate, sources, missing_documents,
                  offer_comparison, assumptions, language: str) -> DossierSummary:
    """Build a DossierSummary from a persisted Simulation + its display context."""
    case_type = (simulation.case_type or "").lower()
    if offer_comparison:
        flow_type, result_kind = "offer_comparison", KIND_COMPARISON
    elif case_type.startswith("medical"):
        flow_type, result_kind = "medical_estimate", KIND_ESTIMATE
    else:
        flow_type, result_kind = "road_estimate", KIND_ESTIMATE

    amount_summary = ""
    if has_estimate and simulation.estimated_min is not None:
        cur = simulation.currency or "EUR"
        amount_summary = (f"{simulation.estimated_min:,.0f} – {simulation.estimated_mid:,.0f} "
                          f"– {simulation.estimated_max:,.0f} {cur}")

    country_code = ""
    if getattr(simulation, "country_id", None) and simulation.country:
        country_code = simulation.country.code

    source_titles = tuple(
        s.get("title") or s.get("source_title") or "" for s in (sources or [])
    )
    source_titles = tuple(t for t in source_titles if t)

    query = {"sim": str(simulation.public_id), "flow": flow_type,
             "result_kind": result_kind, "readiness": "calculated"}
    if country_code:
        query["country"] = country_code
    if simulation.case_type:
        query["category"] = simulation.case_type
    primary = DossierCta(
        label=_("Send the summary to the Studio"),
        url_name="crm:contact",
        query=query,
    )
    secondary = DossierCta(label=_("Back to the guided path"), url_name="core:guided_router")
    return DossierSummary(
        flow_type=flow_type,
        country=country_code,
        category=simulation.case_type or "",
        language=language,
        result_kind=result_kind,
        can_calculate_amount=bool(has_estimate),
        amount_summary=amount_summary,
        readiness_level="calculated" if has_estimate else "",
        readiness_score=100 if has_estimate else 0,
        # Only a real calculation surfaces its assumptions; every list is
        # filtered so no raw engine/diagnostic code can ever reach the panel.
        data_used=_human_only(assumptions) if has_estimate else (),
        missing_data=(),
        documents_present=(),
        documents_missing=_human_only(missing_documents),
        official_sources=_human_only(source_titles),
        next_steps=(),
        primary_cta=primary,
        secondary_cta=secondary,
    )
