"""P29 — the official-source library (single source of truth, static).

A curated catalogue of the official legal sources behind every estimate and
pre-check, so the public can see WHERE a figure or a guided path comes from and
the platform can link country × category × source × engine × pre-check.

Static data, no DB model, no migration — consistent with the rest of the public
content layer. Citations/instruments/URLs are language-neutral plain strings;
only the descriptive summary and the type/usage/access labels are translatable.

Rules honoured: nothing is invented. ``official_url`` points to the institution's
real official portal (Normattiva, EUR-Lex, ACAPS, Legifrance, …); a downloadable
PDF is offered ONLY where a stable official PDF endpoint is known (the EU
regulations on EUR-Lex). No heavy file is ever stored in the repo — only the
metadata, the official link and (when a copy was verified) a hash.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.utils.translation import gettext_lazy as _

# --- source_type (stable key → public label) --------------------------------
TYPE_LAW = "law"
TYPE_DECREE = "decree"
TYPE_TABLE = "official_table"
TYPE_INSURANCE_CODE = "insurance_code"
TYPE_EU_REGULATION = "eu_regulation"
TYPE_ADMINISTRATIVE = "administrative"
TYPE_PRACTICE = "judicial_practice"

SOURCE_TYPE_LABEL = {
    TYPE_LAW: _("Law"),
    TYPE_DECREE: _("Decree"),
    TYPE_TABLE: _("Official table"),
    TYPE_INSURANCE_CODE: _("Insurance code"),
    TYPE_EU_REGULATION: _("EU regulation"),
    TYPE_ADMINISTRATIVE: _("Administrative source"),
    TYPE_PRACTICE: _("Judicial practice (non-binding)"),
}

# --- what a source unlocks (stable key → public label) ----------------------
UNLOCK_ESTIMATE = "estimate"
UNLOCK_TABULAR = "tabular_estimate"
UNLOCK_OFFER = "offer_comparison"
UNLOCK_PRECHECK = "pre_check"
UNLOCK_LAW = "applicable_law"

UNLOCK_LABEL = {
    UNLOCK_ESTIMATE: _("Indicative estimate"),
    UNLOCK_TABULAR: _("Tabular estimate"),
    UNLOCK_OFFER: _("Offer comparison"),
    UNLOCK_PRECHECK: _("Documental pre-check"),
    UNLOCK_LAW: _("Applicable-law framing"),
}

# --- internal status (NOT shown verbatim publicly) --------------------------
STATUS_ENGINE = "usable_for_engine"
STATUS_PRECHECK = "usable_for_precheck"
STATUS_APPROVAL = "approval_needed"
STATUS_PRACTICE = "non_binding_practice"

# --- storage mode -----------------------------------------------------------
STORAGE_EXTERNAL = "external_official_url"
STORAGE_LOCAL = "local_verified_copy"
STORAGE_METADATA = "metadata_only"


@dataclass(frozen=True)
class OfficialSource:
    source_id: str
    country: str                      # ISO-2, or "EU"
    title: str                        # instrument name (language-neutral)
    summary: Any                      # short translatable description
    institution: str                  # publishing body (language-neutral)
    legal_instrument: str             # e.g. "D.P.R. 1124/1965"
    article_or_section: str = ""      # e.g. "art. 139", "Titre V"
    source_type: str = TYPE_LAW
    categories: tuple = ()            # case categories it applies to
    unlocks: tuple = ()               # what it enables
    status: str = STATUS_PRECHECK     # internal; never rendered verbatim
    # --- access / PDF ---
    official_url: str = ""            # institution's real official portal/page
    pdf_available: bool = False
    pdf_url: str = ""
    file_format: str = "PDF"
    file_size_label: str = ""
    sha256_hash: str = ""             # only if a copy was downloaded + verified
    source_language: str = ""         # ISO-2 of the document
    last_checked: str = ""
    storage_mode: str = STORAGE_EXTERNAL
    public_download_allowed: bool = True
    internal_notes: str = ""

    # --- public, weak-state-free labels ---
    @property
    def source_type_label(self):
        return SOURCE_TYPE_LABEL.get(self.source_type, "")

    @property
    def unlock_labels(self):
        return tuple(UNLOCK_LABEL[u] for u in self.unlocks if u in UNLOCK_LABEL)

    @property
    def produces_estimate(self) -> bool:
        return bool({UNLOCK_ESTIMATE, UNLOCK_TABULAR, UNLOCK_OFFER} & set(self.unlocks))

    @property
    def access_label(self):
        """Refined access state — never a weak/error state."""
        if self.pdf_available and self.pdf_url:
            return _("Official PDF available")
        if self.official_url:
            return _("Source available online")
        return _("Source details available")

    @property
    def is_verified(self) -> bool:
        return bool(self.sha256_hash)


# Real official portals (stable, verifiable). Used where an exact deep link is
# not asserted — the source card links to the institution's official site.
_NORMATTIVA = "https://www.normattiva.it"
_GAZZETTA = "https://www.gazzettaufficiale.it"
_INAIL = "https://www.inail.it"
_SGG_MA = "http://www.sgg.gov.ma"
_ACAPS = "https://www.acaps.ma"
_CGA_TN = "http://www.cga.gov.tn"
_IORT_TN = "http://www.iort.gov.tn"
_LEGIFRANCE = "https://www.legifrance.gouv.fr"
_EJUSTICE_BE = "https://www.ejustice.just.fgov.be"
# EUR-Lex exposes a documented, stable HTML + PDF endpoint per CELEX id.
_EURLEX_ROMA2 = "https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX:32007R0864"
_EURLEX_ROMA2_PDF = "https://eur-lex.europa.eu/legal-content/IT/TXT/PDF/?uri=CELEX:32007R0864"
_EURLEX_650 = "https://eur-lex.europa.eu/legal-content/IT/TXT/?uri=CELEX:32012R0650"
_EURLEX_650_PDF = "https://eur-lex.europa.eu/legal-content/IT/TXT/PDF/?uri=CELEX:32012R0650"


SOURCES: tuple[OfficialSource, ...] = (
    # ---------------- Italy ----------------
    OfficialSource(
        "it-cap-139", "IT", "Codice delle Assicurazioni — art. 139",
        _("Statutory micro-permanent road-injury scale (1–9%) for the indicative estimate."),
        "Gazzetta Ufficiale / MIMIT", "D.Lgs. 209/2005", "art. 139",
        TYPE_LAW, ("road_accident", "insurance_offer"),
        (UNLOCK_ESTIMATE, UNLOCK_OFFER), STATUS_ENGINE,
        official_url=_NORMATTIVA, source_language="it"),
    OfficialSource(
        "it-tun-2025", "IT", "Tabella Unica Nazionale — D.P.R. 12/2025",
        _("National macro-injury table (10–100%) behind the road-accident estimate."),
        "Gazzetta Ufficiale", "D.P.R. 12/2025", "",
        TYPE_TABLE, ("road_accident", "medical", "insurance_offer"),
        (UNLOCK_ESTIMATE, UNLOCK_TABULAR, UNLOCK_OFFER), STATUS_ENGINE,
        official_url=_GAZZETTA, source_language="it"),
    OfficialSource(
        "it-gelli-24-2017", "IT", "Legge Gelli-Bianco — L. 24/2017",
        _("Healthcare-liability framework; the biological damage follows the official tables."),
        "Gazzetta Ufficiale", "L. 24/2017", "artt. 7–8",
        TYPE_LAW, ("medical",), (UNLOCK_TABULAR,), STATUS_ENGINE,
        official_url=_NORMATTIVA, source_language="it"),
    OfficialSource(
        "it-tu-inail-1124", "IT", "Testo Unico INAIL — D.P.R. 1124/1965",
        _("The INAIL framework for workplace injury and occupational disease."),
        "INAIL", "D.P.R. 1124/1965", "",
        TYPE_LAW, ("work_injury",), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_INAIL, source_language="it"),
    OfficialSource(
        "it-dlgs-38-2000", "IT", "D.Lgs. 38/2000 — danno biologico INAIL",
        _("Introduces the INAIL biological-damage indemnity (capital / annuity)."),
        "INAIL", "D.Lgs. 38/2000", "art. 13",
        TYPE_DECREE, ("work_injury",), (UNLOCK_PRECHECK,), STATUS_APPROVAL,
        official_url=_INAIL, source_language="it"),
    OfficialSource(
        "it-dm-45-2019", "IT", "D.M. 45/2019 — tabella indennizzo capitale INAIL",
        _("The INAIL capital-indemnity table the work-injury figure will use once imported."),
        "INAIL", "D.M. 45/2019", "",
        TYPE_TABLE, ("work_injury",), (UNLOCK_PRECHECK,), STATUS_APPROVAL,
        official_url=_INAIL, source_language="it"),
    OfficialSource(
        "it-cc-2043-2059", "IT", "Codice Civile — artt. 2043, 2059",
        _("Civil liability and non-pecuniary damage, incl. loss of a relationship."),
        "Gazzetta Ufficiale", "Codice Civile", "artt. 2043, 2059",
        TYPE_LAW, ("loss", "death"), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_NORMATTIVA, source_language="it"),
    OfficialSource(
        "it-cc-1223-1226", "IT", "Codice Civile — artt. 1223, 1226",
        _("Measure of damages and equitable assessment for economic loss."),
        "Gazzetta Ufficiale", "Codice Civile", "artt. 1223, 1226",
        TYPE_LAW, ("loss", "patrimonial"), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_NORMATTIVA, source_language="it"),
    OfficialSource(
        "it-consumo-114-127", "IT", "Codice del Consumo — artt. 114–127",
        _("Producer liability for defective products (no statutory monetary table)."),
        "Gazzetta Ufficiale", "D.Lgs. 206/2005", "artt. 114–127",
        TYPE_LAW, ("product",), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_NORMATTIVA, source_language="it"),
    # ---------------- Morocco ----------------
    OfficialSource(
        "ma-dahir-1-84-177", "MA", "Dahir n° 1-84-177 (1984)",
        _("Moroccan road-accident compensation: the official capital-de-référence barème."),
        "Secrétariat Général du Gouvernement", "Dahir 1-84-177", "",
        TYPE_LAW, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_APPROVAL,
        official_url=_SGG_MA, source_language="fr"),
    OfficialSource(
        "ma-acaps-guide", "MA", "ACAPS — guide d'indemnisation",
        _("The insurance authority's indemnification guidance applied by insurers."),
        "ACAPS", "Guide ACAPS", "",
        TYPE_ADMINISTRATIVE, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_APPROVAL,
        official_url=_ACAPS, source_language="fr"),
    OfficialSource(
        "ma-doc", "MA", "Code des obligations et des contrats",
        _("General civil-liability basis for Moroccan compensation claims."),
        "Secrétariat Général du Gouvernement", "D.O.C.", "",
        TYPE_LAW, ("road_accident", "inheritance"), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_SGG_MA, source_language="fr"),
    OfficialSource(
        "ma-code-assurances", "MA", "Code des assurances (Maroc)",
        _("The insurance code that governs how road-accident claims are settled."),
        "ACAPS", "Code des assurances", "",
        TYPE_INSURANCE_CODE, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_ACAPS, source_language="fr"),
    OfficialSource(
        "ma-moudawana", "MA", "Moudawana — Code de la famille",
        _("Family-law code, relevant to heirs and international successions."),
        "Secrétariat Général du Gouvernement", "Loi 70-03", "",
        TYPE_LAW, ("inheritance",), (UNLOCK_LAW, UNLOCK_PRECHECK), STATUS_PRECHECK,
        official_url=_SGG_MA, source_language="fr"),
    # ---------------- Tunisia ----------------
    OfficialSource(
        "tn-code-assurances", "TN", "Code des assurances — Titre V",
        _("The binding road-accident barème (incapacity, income, heirs)."),
        "Comité Général des Assurances", "Code des assurances", "Titre V (art. 110–179)",
        TYPE_INSURANCE_CODE, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_APPROVAL,
        official_url=_CGA_TN, source_language="fr"),
    OfficialSource(
        "tn-loi-2005-86", "TN", "Loi n° 2005-86",
        _("The law that introduced the Title V road-accident compensation barème."),
        "JORT / IORT", "Loi 2005-86", "",
        TYPE_LAW, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_APPROVAL,
        official_url=_IORT_TN, source_language="fr"),
    OfficialSource(
        "tn-doc", "TN", "Code des obligations et des contrats (Tunisie)",
        _("General civil-liability basis for Tunisian compensation claims."),
        "JORT / IORT", "C.O.C.", "",
        TYPE_LAW, ("road_accident", "inheritance"), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_IORT_TN, source_language="fr"),
    # ---------------- France ----------------
    OfficialSource(
        "fr-loi-badinter", "FR", "Loi Badinter — loi n° 85-677",
        _("The French road-accident compensation regime (no single state barème)."),
        "Légifrance", "Loi 85-677", "",
        TYPE_LAW, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_LEGIFRANCE, source_language="fr"),
    OfficialSource(
        "fr-code-assurances", "FR", "Code des assurances (France)",
        _("The insurance code governing how road-accident claims are handled."),
        "Légifrance", "Code des assurances", "",
        TYPE_INSURANCE_CODE, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_LEGIFRANCE, source_language="fr"),
    # ---------------- Belgium ----------------
    OfficialSource(
        "be-loi-1989", "BE", "Loi du 21/11/1989 — assurance RC auto",
        _("Compulsory motor-liability insurance and the compensation framework."),
        "SPF Justice", "Loi 21/11/1989", "",
        TYPE_LAW, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_PRECHECK,
        official_url=_EJUSTICE_BE, source_language="fr"),
    OfficialSource(
        "be-tableau-indicatif", "BE", "Tableau indicatif / Indicatieve tabel",
        _("Reference figures used by practitioners — non-binding professional practice."),
        "Union professionnelle des magistrats", "Tableau indicatif", "",
        TYPE_PRACTICE, ("road_accident",), (UNLOCK_PRECHECK,), STATUS_PRACTICE,
        official_url="", storage_mode=STORAGE_METADATA, source_language="fr"),
    # ---------------- EU ----------------
    OfficialSource(
        "eu-roma-ii-864-2007", "EU", "Regolamento Roma II — (CE) 864/2007",
        _("Determines the law applicable to a cross-border non-contractual claim."),
        "EUR-Lex", "Reg. (CE) 864/2007", "",
        TYPE_EU_REGULATION, ("cross_border", "road_accident"),
        (UNLOCK_LAW,), STATUS_PRECHECK,
        official_url=_EURLEX_ROMA2, pdf_available=True, pdf_url=_EURLEX_ROMA2_PDF,
        source_language="it"),
    OfficialSource(
        "eu-reg-650-2012", "EU", "Regolamento Successioni — (UE) 650/2012",
        _("Governs jurisdiction and applicable law for international successions."),
        "EUR-Lex", "Reg. (UE) 650/2012", "",
        TYPE_EU_REGULATION, ("cross_border", "inheritance"),
        (UNLOCK_LAW,), STATUS_PRECHECK,
        official_url=_EURLEX_650, pdf_available=True, pdf_url=_EURLEX_650_PDF,
        source_language="it"),
)

_BY_ID = {s.source_id: s for s in SOURCES}


def all_sources() -> tuple[OfficialSource, ...]:
    return SOURCES


def get_source(source_id: str) -> OfficialSource | None:
    return _BY_ID.get(source_id)


def filter_sources(*, country: str = "", category: str = "",
                   source_type: str = "", unlock: str = "") -> list[OfficialSource]:
    """Filter the catalogue by the public facets (all optional)."""
    out = []
    for s in SOURCES:
        if country and s.country != country:
            continue
        if category and category not in s.categories:
            continue
        if source_type and s.source_type != source_type:
            continue
        if unlock and unlock not in s.unlocks:
            continue
        out.append(s)
    return out


def facets() -> dict:
    """Distinct, ordered facet values for the filter UI."""
    countries, types, cats = [], [], []
    for s in SOURCES:
        if s.country not in countries:
            countries.append(s.country)
        if s.source_type not in types:
            types.append(s.source_type)
        for c in s.categories:
            if c not in cats:
                cats.append(c)
    return {"countries": countries, "types": types, "categories": cats}
