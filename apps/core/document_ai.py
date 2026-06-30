"""P30 — document intelligence service (local-first, OpenAI optional).

Recognises the kind of document a visitor uploads, links it to a country,
category and official sources, and proposes the right path (estimate /
pre-check / applicable law / dossier). It works WITHOUT any AI provider via a
local fallback (filename + MIME signals + a manual category override); an
OpenAI provider can be enabled by env to enrich the recognition, but it is OFF
by default and inert without a key.

Hard rules honoured here:
  * never invents an amount, a table or a source;
  * never logs document content, personal data or the API key;
  * does not persist the uploaded file — analysis is in-memory and stateless;
  * the public sees a human confidence band, never a raw model score.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)

# --- confidence bands (human, never a raw float) ----------------------------
CONF_STRONG = "strong"
CONF_TO_CONFIRM = "to_confirm"
CONF_NEEDS_VERIFICATION = "needs_verification"

CONFIDENCE_LABEL = {
    CONF_STRONG: _("Strong recognition"),
    CONF_TO_CONFIRM: _("To confirm"),
    CONF_NEEDS_VERIFICATION: _("Data needs verification"),
}

# --- readiness keys (non-monetary when no engine) ---------------------------
READY_ESTIMATE = "estimate_ready"
READY_TABULAR = "tabular_ready"
READY_OFFER = "offer_comparison_ready"
READY_PRECHECK = "precheck_ready"
READY_LAW = "applicable_law_ready"
READY_INCOMPLETE = "dossier_incomplete"

READINESS_LABEL = {
    READY_ESTIMATE: _("An estimate may be possible"),
    READY_TABULAR: _("A tabular estimate may be possible"),
    READY_OFFER: _("An offer comparison may be possible"),
    READY_PRECHECK: _("A documental pre-check applies"),
    READY_LAW: _("Applicable-law framing applies"),
    READY_INCOMPLETE: _("The dossier needs more documents"),
}


@dataclass(frozen=True)
class DocType:
    key: str
    label: Any
    country: str                 # "" = any
    categories: tuple
    keywords: tuple              # filename signals for local matching
    unlocks: Any                 # what data this document provides
    source_ids: tuple = ()       # official_sources ids
    recommended: tuple = ("", {})  # (url_name, kwargs) for the proposed flow
    readiness: tuple = (READY_PRECHECK,)


@dataclass(frozen=True)
class DocumentAnalysis:
    document_type: Any           # human label of the recognised type
    type_key: str
    confidence: str              # band key
    country: str
    category: str
    language: str = ""
    extracted_fields: tuple = ()
    missing_fields: tuple = ()
    official_source_ids: tuple = ()
    recommended: tuple = ("", {})
    recommended_label: Any = ""
    readiness: tuple = ()
    can_estimate_now: bool = False
    requires_precheck: bool = True
    warnings: tuple = ()
    provider: str = "local"      # "openai" | "local"
    detected_pairs: tuple = ()   # P31: ((label, value), …) structured, redacted

    @property
    def confidence_label(self):
        return CONFIDENCE_LABEL.get(self.confidence, "")

    @property
    def readiness_labels(self):
        return tuple(READINESS_LABEL[r] for r in self.readiness if r in READINESS_LABEL)

    @property
    def official_sources(self):
        from apps.core import official_sources as src
        return tuple(s for s in (src.get_source(i) for i in self.official_source_ids) if s)


# Reusable "data this document provides" phrases.
_F_INJURY = _("Injury / permanent-impairment evidence")
_F_OFFER = _("The insurer's settlement offer")
_F_INCOME = _("Proof of income")
_F_LIABILITY = _("Accident facts and liability")
_F_INAIL = _("INAIL recognition of the injury")
_F_FAMILY = _("Family relationship / eligible relatives")
_F_FOREIGN = _("A foreign-authority or translated document")

# Structured-extraction labels (P31). Only non-sensitive, confirmable fields are
# ever surfaced — never names, plates, addresses or detailed health data.
_E_EVENT_DATE = _("Event date")
_E_AGE = _("Age at the event")
_E_IPP = _("Permanent impairment")
_E_OFFER_PRESENT = _("A settlement offer is present")
_E_INCOME_PRESENT = _("Proof of income is present")
_E_INSURER_PRESENT = _("An insurer is identified")
_E_FAMILY_PRESENT = _("A family relationship is documented")
_E_TRANSLATION = _("A certified translation is needed")
_E_YES = _("yes")

# Recommended-flow labels (human).
_R_OFFER = _("Compare the insurance offer")
_R_ROAD = _("Open the road-accident estimate")
_R_MEDICAL = _("Open the medical estimate")
_R_INAIL = _("Open the INAIL pre-check")
_R_MA = _("Open the Morocco pre-check")
_R_TN = _("Open the Tunisia pre-check")
_R_INTL = _("Frame the applicable law")
_R_LOSS = _("Open the loss-of-relative pre-check")
_R_GUIDED = _("Find the right path")

# --- document type catalog ---------------------------------------------------
DOC_TYPES: tuple[DocType, ...] = (
    # Italy
    DocType("it_medical_report", _("Medical report"), "IT", ("road_accident", "medical"),
            ("referto", "medico", "cartella", "clinica", "report"), _F_INJURY,
            ("it-cap-139", "it-tun-2025", "it-gelli-24-2017"),
            ("cases:wizard_italy_road_accident", {}), (READY_ESTIMATE, READY_PRECHECK)),
    DocType("it_medlegal_cert", _("Medical-legal certificate"), "IT", ("road_accident", "medical"),
            ("medico-legale", "medicolegale", "ctu", "perizia"), _F_INJURY,
            ("it-cap-139", "it-gelli-24-2017"),
            ("cases:wizard_italy_medical", {}), (READY_TABULAR, READY_PRECHECK)),
    DocType("it_accident_report", _("Accident report"), "IT", ("road_accident",),
            ("verbale", "constatazione", "cai", "sinistro"), _F_LIABILITY,
            ("it-cap-139",), ("cases:wizard_italy_road_accident", {}),
            (READY_ESTIMATE, READY_PRECHECK)),
    DocType("it_insurance_offer", _("Insurance offer"), "IT", ("insurance_offer",),
            ("offerta", "transazione", "liquidazione", "proposta"), _F_OFFER,
            ("it-cap-139", "it-tun-2025"), ("cases:wizard_insurance_offer", {}),
            (READY_OFFER,)),
    DocType("it_inail_decision", _("INAIL decision"), "IT", ("work_injury",),
            ("inail", "infortunio", "rendita", "indennizzo"), _F_INAIL,
            ("it-tu-inail-1124", "it-dlgs-38-2000", "it-dm-45-2019"),
            ("core:precheck", {"slug": "inail"}), (READY_PRECHECK,)),
    DocType("it_income_proof", _("Income document"), "IT", ("road_accident", "patrimonial"),
            ("busta", "paga", "cud", "730", "reddito", "stipendio"), _F_INCOME,
            (), ("core:guided_router", {}), (READY_INCOMPLETE,)),
    DocType("it_civil_status", _("Civil-status document"), "IT", ("loss", "death", "inheritance"),
            ("stato civile", "famiglia", "matrimonio", "nascita", "morte", "decesso"), _F_FAMILY,
            ("it-cc-2043-2059",), ("core:precheck", {"slug": "loss-of-relative"}),
            (READY_PRECHECK,)),
    # Morocco (country-specific keywords so a Tunisian/French constat is not mis-mapped)
    DocType("ma_accident_report", _("Accident report (constat / PV)"), "MA", ("road_accident",),
            ("maroc", "marocco", "morocco", "dahir"), _F_LIABILITY,
            ("ma-dahir-1-84-177", "ma-acaps-guide"),
            ("core:precheck", {"slug": "morocco-road-accident"}), (READY_PRECHECK,)),
    DocType("ma_insurance_doc", _("Insurance document (Morocco)"), "MA", ("road_accident",),
            ("acaps", "assurance maroc"), _F_OFFER,
            ("ma-code-assurances", "ma-acaps-guide"),
            ("core:precheck", {"slug": "morocco-road-accident"}), (READY_PRECHECK,)),
    # Tunisia
    DocType("tn_accident_report", _("Accident report (PV / constat)"), "TN", ("road_accident",),
            ("tunisie", "tunisia", "cga"), _F_LIABILITY,
            ("tn-code-assurances", "tn-loi-2005-86"),
            ("core:precheck", {"slug": "tunisia-road-accident"}), (READY_PRECHECK,)),
    # France / Belgium
    DocType("fr_constat", _("Constat amiable"), "FR", ("road_accident",),
            ("constat amiable", "france", "rapport médical"), _F_LIABILITY,
            ("fr-loi-badinter", "fr-code-assurances"),
            ("cases:wizard_france_road_accident", {}), (READY_PRECHECK,)),
    DocType("be_constat", _("Constat / accident report (Belgium)"), "BE", ("road_accident",),
            ("belgique", "belgium", "belgie"), _F_LIABILITY,
            ("be-loi-1989",), ("cases:wizard_belgium_road_accident", {}),
            (READY_PRECHECK,)),
    # International
    DocType("intl_foreign_doc", _("Foreign / translated document"), "", ("cross_border",),
            ("traduzione", "translation", "apostille", "legalisation", "étranger", "foreign"),
            _F_FOREIGN, ("eu-roma-ii-864-2007", "eu-reg-650-2012"),
            ("core:precheck", {"slug": "international-road-accident"}), (READY_LAW,)),
)

_BY_KEY = {d.key: d for d in DOC_TYPES}
_FLOW_LABEL = {
    "cases:wizard_insurance_offer": _R_OFFER,
    "cases:wizard_italy_road_accident": _R_ROAD,
    "cases:wizard_italy_medical": _R_MEDICAL,
    "cases:wizard_france_road_accident": _R_ROAD,
    "cases:wizard_belgium_road_accident": _R_ROAD,
}


def document_types(country: str = "", category: str = "") -> list[DocType]:
    return [d for d in DOC_TYPES
            if (not country or d.country in (country, ""))
            and (not category or category in d.categories)]


def _flow_label(doc: DocType):
    url, kwargs = doc.recommended
    if url in _FLOW_LABEL:
        return _FLOW_LABEL[url]
    slug = kwargs.get("slug", "")
    return {"inail": _R_INAIL, "morocco-road-accident": _R_MA,
            "tunisia-road-accident": _R_TN, "loss-of-relative": _R_LOSS,
            "international-road-accident": _R_INTL}.get(slug, _R_GUIDED)


def _build(doc: DocType, confidence: str, *, provider: str,
           country: str = "", category: str = "", language: str = "",
           warnings: tuple = ()) -> DocumentAnalysis:
    can_estimate = READY_ESTIMATE in doc.readiness or READY_TABULAR in doc.readiness or READY_OFFER in doc.readiness
    return DocumentAnalysis(
        document_type=doc.label,
        type_key=doc.key,
        confidence=confidence,
        country=country or doc.country,
        category=category or (doc.categories[0] if doc.categories else ""),
        language=language,
        extracted_fields=(doc.unlocks,) if doc.unlocks else (),
        missing_fields=(),
        official_source_ids=doc.source_ids,
        recommended=doc.recommended,
        recommended_label=_flow_label(doc),
        readiness=doc.readiness,
        can_estimate_now=False,  # a single document never produces a figure alone
        requires_precheck=not can_estimate,
        warnings=warnings,
        provider=provider,
    )


def _generic(category: str) -> DocType:
    """A neutral fallback type when the filename gives no signal."""
    for d in DOC_TYPES:
        if category and category in d.categories:
            return d
    return DocType("unrecognised", _("Document to classify"), "", (category,) if category else (),
                   (), _("Document content to review"), (), ("core:guided_router", {}),
                   (READY_INCOMPLETE,))


def classify_local(filename: str, mime: str, *, country: str = "",
                   category: str = "") -> DocumentAnalysis:
    """Local, no-AI recognition from filename + MIME (+ manual category)."""
    name = (filename or "").lower()
    for doc in DOC_TYPES:
        if country and doc.country and doc.country != country:
            continue
        if any(kw in name for kw in doc.keywords):
            return _build(doc, CONF_TO_CONFIRM, provider="local",
                          country=country, category=category)
    # No filename signal → ask the visitor to confirm the category.
    return _build(_generic(category), CONF_NEEDS_VERIFICATION, provider="local",
                  country=country, category=category)


def _pairs_from_extraction(data: dict) -> tuple:
    """Turn the OpenAI structured payload into redacted (label, value) pairs.

    Only non-sensitive, confirmable fields are kept; amounts are presence flags,
    never values, so no figure is ever surfaced without an engine run.
    """
    pairs: list[tuple] = []
    for key, label in (("event_date", _E_EVENT_DATE), ("age", _E_AGE),
                       ("impairment_percent", _E_IPP)):
        value = str(data.get(key) or "").strip()
        if value:
            pairs.append((label, value))
    for key, label in (("offer_present", _E_OFFER_PRESENT),
                       ("income_present", _E_INCOME_PRESENT),
                       ("insurer_present", _E_INSURER_PRESENT),
                       ("family_relationship_present", _E_FAMILY_PRESENT),
                       ("translation_needed", _E_TRANSLATION)):
        if data.get(key) is True:
            pairs.append((label, _E_YES))
    return tuple(pairs)


def _analyze_openai(filename, mime, *, country, category):  # pragma: no cover
    """Optional OpenAI enrichment. Returns a DocumentAnalysis or None.

    Feature-flagged and inert without a key. Defensive: ANY problem (missing
    library, error, timeout, incoherent output) returns None → local fallback.
    The document bytes are NOT logged; only the file name length / mime is.
    """
    if not (settings.OPENAI_DOCUMENT_AI_ENABLED and settings.OPENAI_API_KEY):
        return None
    try:
        from openai import OpenAI  # optional dependency

        from apps.core import official_sources as src

        client = OpenAI(api_key=settings.OPENAI_API_KEY,
                        timeout=settings.OPENAI_DOCUMENT_AI_TIMEOUT)
        valid_types = [d.key for d in DOC_TYPES]
        schema = {
            "type": "object",
            "properties": {
                "type_key": {"type": "string", "enum": valid_types},
                "country": {"type": "string"},
                "category": {"type": "string"},
                "language": {"type": "string"},
                "confidence": {"type": "string",
                               "enum": [CONF_STRONG, CONF_TO_CONFIRM, CONF_NEEDS_VERIFICATION]},
                # Structured extraction — non-sensitive, confirmable fields only.
                "event_date": {"type": "string"},
                "age": {"type": "string"},
                "impairment_percent": {"type": "string"},
                "offer_present": {"type": "boolean"},
                "income_present": {"type": "boolean"},
                "insurer_present": {"type": "boolean"},
                "family_relationship_present": {"type": "boolean"},
                "translation_needed": {"type": "boolean"},
            },
            "required": ["type_key", "confidence"],
            "additionalProperties": False,
        }
        instructions = (
            "Classify the legal document and extract only non-sensitive, "
            "confirmable fields. NEVER return personal names, license plates, "
            "addresses, identifiers or detailed health data — redact any personal "
            "party. For amounts, report only presence as a boolean, not the value."
        )
        resp = client.responses.create(
            model=settings.OPENAI_DOCUMENT_AI_MODEL,
            instructions=instructions,
            input=[{"role": "user",
                    "content": f"Classify this legal document by file name: {filename[:120]}"}],
            text={"format": {"type": "json_schema", "name": "doc", "schema": schema}},
        )
        import json
        data = json.loads(resp.output_text)
        doc = _BY_KEY.get(data.get("type_key"))
        if doc is None:
            return None  # incoherent → safe fallback
        _ = src  # sources resolved by the property
        analysis = _build(doc, data.get("confidence", CONF_TO_CONFIRM), provider="openai",
                          country=data.get("country") or country,
                          category=data.get("category") or category,
                          language=data.get("language", ""))
        pairs = _pairs_from_extraction(data)
        if pairs:
            from dataclasses import replace
            analysis = replace(analysis, detected_pairs=pairs)
        return analysis
    except Exception:
        # No document content in the log — only a coarse failure marker.
        logger.info("document_ai.openai_unavailable mime=%s", mime)
        return None


def analyze_document(*, filename: str, mime: str, size: int,
                     country: str = "", category: str = "") -> DocumentAnalysis:
    """Public entry point: OpenAI if configured, else the local fallback."""
    result = _analyze_openai(filename, mime, country=country, category=category)
    if result is not None:
        return result
    return classify_local(filename, mime, country=country, category=category)


def dev_status() -> dict:
    """Non-public diagnostic for the internal report only.

    NEVER shown to public visitors and NEVER includes the key — not even a
    masked fragment — nor the model name. It only answers yes/no questions so a
    developer can confirm how the recognition is wired.
    """
    enabled = bool(settings.OPENAI_DOCUMENT_AI_ENABLED)
    key_present = bool(settings.OPENAI_API_KEY)
    notes: list[str] = []
    if enabled and not key_present:
        notes.append("AI enabled but no key present — recognition uses the local fallback.")
    if not enabled:
        notes.append("AI disabled — recognition uses the local fallback.")
    return {
        "ai_enabled": enabled,
        "dev_mode": bool(settings.OPENAI_DOCUMENT_AI_DEV_MODE),
        "model_configured": bool(settings.OPENAI_DOCUMENT_AI_MODEL),
        "key_present": key_present,
        "fallback_available": True,  # the local classifier is always available
        "active_provider": "openai" if (enabled and key_present) else "local",
        "notes": tuple(notes),
    }


# --- multi-document dossier aggregation (P31) --------------------------------
# The highest-priority recognised document drives the proposed global path;
# complementary documents that would unlock more are surfaced as "still useful",
# never as a blocker and never as a figure.
_LEAD_PRIORITY = (
    "it_insurance_offer", "it_medical_report", "it_medlegal_cert",
    "it_accident_report", "it_inail_decision", "it_civil_status",
    "ma_accident_report", "ma_insurance_doc", "tn_accident_report",
    "fr_constat", "be_constat", "intl_foreign_doc", "it_income_proof",
)
_READY_ORDER = (READY_OFFER, READY_ESTIMATE, READY_TABULAR,
                READY_PRECHECK, READY_LAW, READY_INCOMPLETE)

# Complementary documents that would strengthen the dossier (human phrases).
_M_INJURY = _("A medical report or impairment certificate")
_M_OFFER = _("The insurer's settlement offer, to compare it")
_M_INCOME = _("Proof of income, for the economic component")
_M_ACCIDENT = _("The accident report or constat")


@dataclass(frozen=True)
class DossierAggregate:
    document_count: int
    country: str
    category: str
    readiness: tuple
    official_source_ids: tuple
    recommended: tuple = ("", {})
    recommended_label: Any = ""
    missing_documents: tuple = ()
    present_evidence: tuple = ()
    can_estimate_now: bool = False     # still False — no figure without an engine
    can_compare_offer: bool = False
    requires_precheck: bool = True
    analyses: tuple = ()

    @property
    def readiness_labels(self):
        return tuple(READINESS_LABEL[r] for r in self.readiness if r in READINESS_LABEL)

    @property
    def official_sources(self):
        from apps.core import official_sources as src
        return tuple(s for s in (src.get_source(i) for i in self.official_source_ids) if s)


def aggregate_dossier(analyses) -> DossierAggregate:
    """Combine per-document analyses into one dossier with a global path."""
    analyses = tuple(a for a in (analyses or ()) if a is not None)
    if not analyses:
        return DossierAggregate(0, "", "", (READY_INCOMPLETE,), (),
                                ("core:guided_router", {}), _R_GUIDED,
                                missing_documents=(), present_evidence=())

    keys = {a.type_key for a in analyses}
    has_offer = bool(keys & {"it_insurance_offer", "ma_insurance_doc"})
    has_injury = bool(keys & {"it_medical_report", "it_medlegal_cert"})
    has_accident = bool(keys & {"it_accident_report", "ma_accident_report",
                                "tn_accident_report", "fr_constat", "be_constat"})
    has_income = "it_income_proof" in keys

    # Lead document drives the recommended path.
    lead = None
    for key in _LEAD_PRIORITY:
        lead = next((a for a in analyses if a.type_key == key), None)
        if lead is not None:
            break
    lead = lead or analyses[0]

    # Country = most frequent non-empty; category from the lead document.
    counts: dict[str, int] = {}
    for a in analyses:
        if a.country:
            counts[a.country] = counts.get(a.country, 0) + 1
    country = max(counts, key=lambda c: counts[c]) if counts else lead.country

    # Union of readiness and sources, in a stable order.
    ready_seen = {r for a in analyses for r in a.readiness}
    readiness = tuple(r for r in _READY_ORDER if r in ready_seen) or (READY_INCOMPLETE,)
    source_ids: list[str] = []
    for a in analyses:
        for sid in a.official_source_ids:
            if sid not in source_ids:
                source_ids.append(sid)

    # Recognised evidence across the dossier (de-duplicated human phrases).
    present: list[Any] = []
    for a in analyses:
        for f in a.extracted_fields:
            if f not in present:
                present.append(f)

    # Complementary documents that would strengthen the dossier.
    missing: list[Any] = []
    if has_offer and not has_injury:
        missing.append(_M_INJURY)
    if (has_injury or has_accident) and not has_offer:
        missing.append(_M_OFFER)
    if (has_injury or has_accident) and not has_income:
        missing.append(_M_INCOME)
    if has_offer and not (has_injury or has_accident):
        missing.append(_M_ACCIDENT)

    can_compare_offer = has_offer and (has_injury or has_accident)
    requires_precheck = not bool(
        ready_seen & {READY_ESTIMATE, READY_TABULAR, READY_OFFER})

    return DossierAggregate(
        document_count=len(analyses),
        country=country,
        category=lead.category,
        readiness=readiness,
        official_source_ids=tuple(source_ids),
        recommended=lead.recommended,
        recommended_label=lead.recommended_label,
        missing_documents=tuple(missing),
        present_evidence=tuple(present),
        can_estimate_now=False,
        can_compare_offer=can_compare_offer,
        requires_precheck=requires_precheck,
        analyses=analyses,
    )
