"""P29 — a lightweight, dependency-free public search index.

Builds an in-memory index over the platform's destinations — estimates,
pre-checks, countries, case types, official sources and key pages — and ranks
results by simple token overlap against a multilingual ``keywords`` blob, so a
query like "incidente in Marocco" or "Roma II" lands on the right place. No
external engine, no heavy dependency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.utils.translation import gettext_lazy as _

from apps.core import official_sources as src

# result kinds (stable key → label).
KIND_ESTIMATE = "estimate"
KIND_PRECHECK = "pre_check"
KIND_SOURCE = "source"
KIND_COUNTRY = "country"
KIND_CATEGORY = "category"
KIND_PAGE = "page"

KIND_LABEL = {
    KIND_ESTIMATE: _("Estimate"),
    KIND_PRECHECK: _("Pre-check"),
    KIND_SOURCE: _("Official source"),
    KIND_COUNTRY: _("Country"),
    KIND_CATEGORY: _("Case type"),
    KIND_PAGE: _("Page"),
}

# CTA per kind.
KIND_CTA = {
    KIND_ESTIMATE: _("Start the estimate"),
    KIND_PRECHECK: _("Open the pre-check"),
    KIND_SOURCE: _("Read the source"),
    KIND_COUNTRY: _("Open the country"),
    KIND_CATEGORY: _("Frame the case"),
    KIND_PAGE: _("Open"),
}


@dataclass(frozen=True)
class SearchEntry:
    title: Any
    description: Any
    kind: str
    url_name: str
    url_kwargs: dict = field(default_factory=dict)
    keywords: str = ""

    @property
    def kind_label(self):
        return KIND_LABEL.get(self.kind, "")

    @property
    def cta_label(self):
        return KIND_CTA.get(self.kind, _("Open"))


def _entries() -> list[SearchEntry]:
    e: list[SearchEntry] = []

    # --- Estimates (live engines) ---
    e.append(SearchEntry(_("Road accident with injuries"),
                         _("Indicative estimate on the official Italian tables."),
                         KIND_ESTIMATE, "cases:wizard_italy_road_accident",
                         keywords="incidente stradale road accident car injury lesioni italia italy art 139 tun estimate stima"))
    e.append(SearchEntry(_("Healthcare liability"),
                         _("Tabular biological-damage estimate (Gelli law)."),
                         KIND_ESTIMATE, "cases:wizard_italy_medical",
                         keywords="responsabilita sanitaria medical malpractice healthcare gelli danno biologico medico estimate stima tabellare"))
    e.append(SearchEntry(_("Insurance-offer check"),
                         _("Compare a settlement offer against the official estimate."),
                         KIND_ESTIMATE, "cases:wizard_insurance_offer",
                         keywords="offerta assicurativa insurance offer comparison confronto settlement risarcimento"))

    # --- Pre-checks ---
    for slug, title, kw in (
        ("inail", _("INAIL workplace injury"),
         "inail infortunio lavoro work injury workplace occupational malattia professionale italia"),
        ("loss-of-relative", _("Loss of a relative"),
         "perdita familiare loss relative death decesso parentale lutto famiglia bereavement"),
        ("morocco-road-accident", _("Road accident in Morocco"),
         "marocco morocco maroc incidente accident stradale road dahir acaps"),
        ("tunisia-road-accident", _("Road accident in Tunisia"),
         "tunisia tunisie incidente accident stradale road code assurances barème loi 2005-86"),
        ("international-road-accident", _("Cross-border accident — applicable law"),
         "internazionale international cross-border roma ii rome estero legge applicabile applicable law"),
    ):
        e.append(SearchEntry(title, _("Documental pre-check on the official sources."),
                             KIND_PRECHECK, "core:precheck", {"slug": slug}, keywords=kw))

    # --- Countries ---
    for _code, name, urlname, kw in (
        ("IT", _("Italy"), "core:country_italy", "italia italy italie"),
        ("FR", _("France"), "core:country_france", "francia france"),
        ("BE", _("Belgium"), "core:country_belgium", "belgio belgium belgique"),
        ("MA", _("Morocco"), "core:country_morocco", "marocco morocco maroc"),
        ("TN", _("Tunisia"), "core:country_tunisia", "tunisia tunisie"),
    ):
        e.append(SearchEntry(name, _("Coverage, categories and official sources."),
                             KIND_COUNTRY, urlname, keywords=kw + " paese country pays"))

    # --- Case types (hub) ---
    e.append(SearchEntry(_("Inheritance"), _("Statutory shares and international successions."),
                         KIND_CATEGORY, "core:case_types",
                         keywords="successione inheritance eredità quote international successioni"))
    e.append(SearchEntry(_("Defective product"), _("Producer liability — documental verification."),
                         KIND_CATEGORY, "core:case_types",
                         keywords="prodotto difettoso defective product liability consumo"))

    # --- Official sources ---
    for s in src.all_sources():
        e.append(SearchEntry(
            s.title, s.summary, KIND_SOURCE, "core:source_detail", {"slug": s.source_id},
            keywords=f"{s.legal_instrument} {s.institution} {s.country} "
                     f"{' '.join(s.categories)} fonte source ufficiale official".lower()))

    # --- Key pages ---
    for urlname, title, kw in (
        ("core:sources", _("Official source library"), "fonti sources biblioteca library official"),
        ("core:guided_router", _("Find your guided path"), "guidato guided percorso path navigator"),
        ("core:services", _("Areas the Studio handles"), "servizi services aree areas"),
        ("core:how_it_works", _("How it works"), "come funziona how it works metodo"),
        # P30: the document-intake flow — found via document-type keywords.
        ("core:documents", _("Prepare your dossier"),
         "documenti documents carica upload dossier referto medico report offerta "
         "assicurativa insurance offer constat verbale pv accident inail provvedimento "
         "certificato busta paga reddito traduzione foreign document riconoscimento"),
    ):
        e.append(SearchEntry(title, _("Platform page."), KIND_PAGE, urlname, keywords=kw))

    return e


def search(query: str, limit: int = 30) -> list[SearchEntry]:
    """Rank entries by token overlap against title/description/keywords."""
    q = (query or "").strip().lower()
    if not q:
        return []
    tokens = [t for t in q.replace(",", " ").split() if len(t) >= 2]
    if not tokens:
        return []
    scored = []
    for entry in _entries():
        blob = f"{entry.title} {entry.description} {entry.keywords}".lower()
        score = sum(1 for t in tokens if t in blob)
        # small boost when a token matches the (shorter) title directly.
        title_l = str(entry.title).lower()
        score += sum(1 for t in tokens if t in title_l)
        if score:
            scored.append((score, entry))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [e for _, e in scored[:limit]]
