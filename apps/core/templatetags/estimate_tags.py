"""P38 — "What you can estimate today" availability matrix.

Public, human states only (never technical words). The matrix reflects the real
validated-engine coverage; where no validated official table exists, the public
state is a simple document/check path — never an amount.
"""

from __future__ import annotations

from django import template
from django.utils.translation import gettext_lazy as _

register = template.Library()

# --- simple public states (no technical vocabulary) -------------------------
ST_ESTIMATE = "estimate"
ST_OFFER = "offer"
ST_DOCS = "documents"
ST_LAW = "law"
ST_TABLE = "needs_table"

_STATE = {
    ST_ESTIMATE: {"label": _("Estimate available"), "icon": "scale", "tone": "ok"},
    ST_OFFER: {"label": _("Offer check"), "icon": "shield-check", "tone": "teal"},
    ST_DOCS: {"label": _("Check your documents"), "icon": "document", "tone": "gold"},
    ST_LAW: {"label": _("Understand which law may apply"), "icon": "globe", "tone": "slate"},
    ST_TABLE: {"label": _("Needs the official table first"), "icon": "list-checks", "tone": "muted"},
}

# Category labels (reused across the site).
_C_ROAD = _("Road accident")
_C_BIO = _("Biological damage")
_C_MED = _("Medical liability")
_C_OFFER = _("Insurance offer")
_C_INAIL = _("INAIL / work injury")
_C_LOSS = _("Loss of a relative")
_C_PRODUCT = _("Defective product")
_C_SUCC = _("Inheritance")
_C_LAW = _("Applicable law")

# country -> [(category_label, state_key)] — truthful, based on what the live
# engines actually return on the public DB. P40: corrected after the official
# estimate-expansion audit + a run_simulation check proved only IT road / IT
# danno-biologico / IT medical produce a real figure today. Every other pair
# returns `unavailable_requires_legal_validation` (FR/BE road have no validated
# state table; IT/MA/TN inheritance engines are registered but gate to legal
# review), so they must NOT be labelled "Estimate available". See
# docs/audits/P40_OFFICIAL_ESTIMATE_EXPANSION_MASTERPLAN_2026-06-29.md.
_MATRIX = [
    (_("Italy"), [
        (_C_ROAD, ST_ESTIMATE), (_C_BIO, ST_ESTIMATE), (_C_MED, ST_ESTIMATE),
        (_C_OFFER, ST_OFFER), (_C_SUCC, ST_DOCS),
        (_C_INAIL, ST_DOCS), (_C_LOSS, ST_DOCS), (_C_PRODUCT, ST_DOCS),
    ]),
    (_("Morocco"), [
        (_C_SUCC, ST_DOCS), (_C_ROAD, ST_TABLE), (_C_LOSS, ST_DOCS),
    ]),
    (_("Tunisia"), [
        (_C_SUCC, ST_DOCS), (_C_ROAD, ST_TABLE), (_C_LOSS, ST_DOCS),
    ]),
    (_("France"), [
        (_C_ROAD, ST_TABLE), (_C_OFFER, ST_DOCS),
    ]),
    (_("Belgium"), [
        (_C_ROAD, ST_TABLE), (_C_OFFER, ST_DOCS),
    ]),
    (_("Cross-border"), [
        (_C_LAW, ST_LAW), (_C_SUCC, ST_LAW),
    ]),
]


def _build():
    cards = []
    for country, rows in _MATRIX:
        cards.append({
            "country": country,
            "rows": [{"category": cat, "label": _STATE[s]["label"],
                      "icon": _STATE[s]["icon"], "tone": _STATE[s]["tone"]}
                     for cat, s in rows],
        })
    legend = [{"label": v["label"], "tone": v["tone"], "icon": v["icon"]}
              for v in _STATE.values()]
    return cards, legend


@register.inclusion_tag("partials/_estimate_matrix.html")
def estimate_matrix(compact=False):
    cards, legend = _build()
    return {"matrix_cards": cards, "matrix_legend": legend, "matrix_compact": compact}
