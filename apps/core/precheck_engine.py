"""P16/P25 — pre-check decision engine: turns interactive answers into a guided result.

Given a `PreCheckFlow` and the submitted answers, this produces a personalised,
non-numeric result. P25 turns the result from a flat readiness signal into a
professional dossier analysis:

  * a top-line ``result_status`` ("Dossier ready for analysis" / "Documents to
    consolidate" / "Initial document collection") with a one-line summary;
  * the data that is already SOLID vs. the points that still need ATTENTION;
  * WHY this legal path applies, what can be ASSESSED now and what is PENDING
    before any figure;
  * a CATEGORISED document checklist (essential / useful / optional) with the
    purpose of each record;
  * a primary AND a secondary next action.

It NEVER computes or shows an amount — these flows have no approved engine, so
the output is organisational and analytical, not monetary. Stateless: the
answers are evaluated in memory and never persisted (GDPR-light).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.utils.translation import gettext_lazy as _

from apps.core import precheck as pc

# --- Completeness levels ----------------------------------------------------
ESSENTIAL = "essential_present"
PARTIAL = "partial"
INITIAL = "initial_collection"

COMPLETENESS_LABEL = {
    ESSENTIAL: _("Essential documents present"),
    PARTIAL: _("Partial documents"),
    INITIAL: _("Initial document collection needed"),
}
COMPLETENESS_TONE = {ESSENTIAL: "ok", PARTIAL: "gold", INITIAL: "gold"}

# --- P25: analytical top-line status ----------------------------------------
STATUS_READY = "ready"
STATUS_CONSOLIDATING = "consolidating"
STATUS_INITIAL = "initial"

RESULT_STATUS_LABEL = {
    STATUS_READY: _("Dossier ready for analysis"),
    STATUS_CONSOLIDATING: _("Documents to consolidate"),
    STATUS_INITIAL: _("Initial document collection"),
}
RESULT_STATUS_TONE = {STATUS_READY: "ok", STATUS_CONSOLIDATING: "gold", STATUS_INITIAL: "gold"}
_STATUS_FROM_COMPLETENESS = {ESSENTIAL: STATUS_READY, PARTIAL: STATUS_CONSOLIDATING, INITIAL: STATUS_INITIAL}

_SUMMARY_BY_STATUS = {
    STATUS_READY: _("The essential records are in place; the Studio can review the "
                    "file against the official sources."),
    STATUS_CONSOLIDATING: _("The core of the file is there; a few essential records "
                            "still need to be gathered."),
    STATUS_INITIAL: _("The case is framed; the essential records still need to be "
                      "collected before a review."),
}

# --- P25: document categories -----------------------------------------------
DOC_ESSENTIAL = "essential"
DOC_USEFUL = "useful"
DOC_OPTIONAL = "optional"

DOC_CATEGORY_LABEL = {
    DOC_ESSENTIAL: _("Essential"),
    DOC_USEFUL: _("Useful to strengthen the file"),
    DOC_OPTIONAL: _("Optional"),
}

# --- Guidance message strings (fixed, translatable) -------------------------
_M_INAIL_CAPITAL = _("Estimated impairment in the 6–15% band: the INAIL capital "
                     "indemnity table is the candidate basis — it activates once the "
                     "official table is validated.")
_M_INAIL_ANNUITY = _("Estimated impairment above 15%: this points to a possible INAIL "
                     "annuity and requires a dedicated INAIL analysis.")
_M_INAIL_DIFFERENTIAL = _("Possible third-party or employer liability: the civil-liability "
                          "differential beyond INAIL should be assessed.")
_M_LOSS_OFFER = _("Italy, road accident with an offer received: a comparison between the "
                  "insurance offer and a documental valuation is recommended.")
_M_LOSS_FOREIGN = _("Foreign country involved: framing the applicable law (cross-border) "
                    "is the recommended first step.")
_M_MA_READY = _("Key data available (incapacity, income, liability): the file is ready for "
                "the future application of the Dahir / ACAPS barème once it is validated.")
_M_TN_READY = _("Key data available (incapacity, income): the file is ready for the future "
                "application of the Code des assurances barème once it is validated.")
_M_INT_LAW = _("Under Rome II the applicable law is, as a rule, that of the country where the "
               "damage occurred — to be confirmed against the specific facts.")
_M_INT_TRANSLATE = _("Foreign-language documents will need certified translation / "
                     "legalisation before the cross-border analysis.")
_M_INT_CROSS = _("A cross-border analysis of jurisdiction and applicable law is the "
                 "recommended next step.")

# Missing data labels not already covered by a document constant.
_MISS_IPP = _("Permanent-incapacity (IPP) assessment")
_FOREIGN_DOCS = _("Foreign documents to be translated / legalised")

# Next-step strings.
_NS_DOCUMENTAL = _("Request a documental check from the Studio on the official sources above.")
_NS_LAW = _("Request a cross-border framing of the applicable law and the competent court.")

# Potential path — the official route this case would follow toward a figure.
_PATH_INAIL = _("Official INAIL calculation, once the capital / annuity table is validated")
_PATH_MA = _("Official Dahir / ACAPS barème (capital de référence), once validated")
_PATH_TN = _("Official Code des assurances barème (loi 2005-86), once validated")
_PATH_PARENTAL = _("Guided assessment of the parental / family damage")
_PATH_LAW = _("Applicable-law framing under Rome II, before any quantification")

# Data that would unlock a numeric estimate (honest — no figure is implied now).
_UNLOCK_INAIL = _("A validated INAIL capital / annuity table for the indicated impairment")
_UNLOCK_MA = _("A validated capital-de-référence table (Dahir / ACAPS)")
_UNLOCK_TN = _("A validated Code des assurances barème (loi 2005-86)")
_UNLOCK_LIABILITY = _("Established liability and the assessed permanent incapacity")
_UNLOCK_PARENTAL = _("The documented family relationship and the established liability")
_UNLOCK_LAW = _("Identification of the applicable law and the competent court")

# --- P25: "why this path" reasons -------------------------------------------
_WHY_INAIL = _("Workplace injuries are indemnified on the INAIL tariff (D.P.R. 1124/1965): "
               "the figure follows the official table, not a free estimate.")
_WHY_MA = _("Moroccan road-accident compensation is settled by the insurer on the Dahir "
            "1-84-177 barème — the amount derives from the official capital de référence.")
_WHY_TN = _("Tunisian road-accident compensation follows the Code des assurances "
            "(loi 2005-86) barème applied by the insurer.")
_WHY_PARENTAL = _("Loss-of-relationship damage has no statutory table: Italian courts "
                  "assess it case by case under artt. 2043 and 2059 of the Civil Code.")
_WHY_LAW = _("Before any figure, Rome II decides which national law and which court "
            "govern a cross-border case.")

# --- P25: what can be assessed now vs. what is pending ----------------------
_NOW_INAIL = _("We can map the file to the INAIL framework and to any differential beyond it.")
_PEND_INAIL = _("The indemnity figure needs the validated INAIL capital / annuity table "
                "for the assessed impairment.")
_NOW_MA = _("We can check the file against the structure the Dahir / ACAPS barème requires.")
_PEND_MA = _("The amount needs the validated capital-de-référence table and the assessed "
             "permanent incapacity.")
_NOW_TN = _("We can check the file against the structure the Code des assurances barème requires.")
_PEND_TN = _("The amount needs the validated barème (loi 2005-86) and the assessed "
             "permanent incapacity.")
_NOW_PARENTAL = _("We can structure the parental-damage claim and weigh the relationship "
                  "and the established liability.")
_PEND_PARENTAL = _("No statutory table fixes the amount: it depends on the deciding court "
                   "and the documented relationship.")
_NOW_LAW = _("We can frame which law applies and which court is competent.")
_PEND_LAW = _("Any figure follows only once the governing law and the forum are settled.")

# --- P25: solid (strong) vs. attention signals ------------------------------
_SIG_MEDICAL_OK = _("Medical-legal report available")
_SIG_MEDICAL_TODO = _("Medical-legal report still to obtain")
_SIG_INAIL_OK = _("INAIL recognition documented")
_SIG_INAIL_TODO = _("INAIL recognition documents to gather")
_SIG_IPP_OK = _("Permanent incapacity assessed")
_SIG_IPP_TODO = _("Permanent incapacity not yet assessed")
_SIG_INCOME_OK = _("Income is documentable")
_SIG_INCOME_TODO = _("Proof of income still to gather")
_SIG_LIABILITY_OK = _("Liability is established")
_SIG_LIABILITY_TODO = _("Liability still to establish")
_SIG_ACCIDENT_OK = _("Accident / police report available")
_SIG_ACCIDENT_TODO = _("Accident / police report to obtain")
_SIG_CIVIL_OK = _("Civil-status documents available")
_SIG_CIVIL_TODO = _("Civil-status documents to gather")
_SIG_INSURER_OK = _("Insurer identified")
_SIG_INSURER_TODO = _("Insurer to identify")
_SIG_THIRDPARTY = _("Third-party / employer liability to pursue beyond INAIL")
_SIG_OFFER = _("An insurance offer was received — worth comparing")
_SIG_RELATIONSHIP = _("Family relationship indicated")

# --- P25: document-checklist reasons ----------------------------------------
_R_MEDICAL = _("Quantifies the permanent impairment that drives any indemnity.")
_R_INAIL = _("Establishes the INAIL recognition and the benefit already paid.")
_R_ACCIDENT = _("Fixes the facts and the dynamics that found liability.")
_R_INSURANCE = _("Identifies the insurer and any offer to weigh.")
_R_INCOME = _("Supports the economic-loss component of the claim.")
_R_CIVIL = _("Proves the family relationship and the eligible relatives.")
_R_FOREIGN = _("Needed before a cross-border file can be assessed.")


@dataclass(frozen=True)
class DocItem:
    """One categorised document in the readiness checklist."""

    label: Any
    category: str = DOC_ESSENTIAL
    present: bool = False
    reason: Any = ""

    @property
    def category_label(self):
        return DOC_CATEGORY_LABEL.get(self.category, "")


@dataclass(frozen=True)
class PreCheckResult:
    completeness: str
    answered_summary: tuple  # ((label, value_label), ...)
    missing_documents: tuple
    applicable_sources: tuple
    messages: tuple
    next_step: str
    cta_label: str
    cta_url_name: str = "crm:contact"
    cta_kwargs: dict = field(default_factory=dict)
    has_numeric_estimate: bool = False  # always False for these flows
    readiness_pct: int = 0  # documental readiness, NOT a monetary figure
    potential_path: str = ""  # the official route toward a figure
    unlocking_data: tuple = ()  # what would unlock a numeric estimate
    # --- P25 analytical layer (all optional / defaulted) ---
    dossier_summary: Any = ""        # one-line readiness explanation
    strong_points: tuple = ()        # data that is already solid
    attention_points: tuple = ()     # points to verify (NOT alarms)
    path_reason: Any = ""            # why this legal path applies
    assessable_now: Any = ""         # what can be assessed now
    pending_for_estimate: Any = ""   # what blocks a numeric figure
    document_items: tuple = ()       # tuple[DocItem] — categorised checklist
    secondary_cta_label: Any = ""
    secondary_cta_url_name: str = ""
    secondary_cta_kwargs: dict = field(default_factory=dict)

    @property
    def completeness_label(self):
        return COMPLETENESS_LABEL[self.completeness]

    @property
    def completeness_tone(self):
        return COMPLETENESS_TONE[self.completeness]

    @property
    def result_status(self):
        return _STATUS_FROM_COMPLETENESS.get(self.completeness, STATUS_INITIAL)

    @property
    def result_status_label(self):
        return RESULT_STATUS_LABEL.get(self.result_status, "")

    @property
    def result_status_tone(self):
        return RESULT_STATUS_TONE.get(self.result_status, "gold")

    @property
    def documents_by_category(self):
        """Group document_items into ordered (category_label, items) sections."""
        order = (DOC_ESSENTIAL, DOC_USEFUL, DOC_OPTIONAL)
        out = []
        for cat in order:
            items = tuple(d for d in self.document_items if d.category == cat)
            if items:
                out.append((DOC_CATEGORY_LABEL[cat], items))
        return tuple(out)


# --- Helpers ----------------------------------------------------------------
def _yes(answers, key):
    return answers.get(key) == "yes"


def _int(answers, key):
    raw = (answers.get(key) or "").strip()
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _completeness(present_flags):
    present = [b for b in present_flags]
    if present and all(present):
        return ESSENTIAL
    if any(present):
        return PARTIAL
    return INITIAL


def _readiness(flow, answers):
    """Documental readiness as a percentage of the applicable fields answered.

    This is an organisational completeness signal, NOT a monetary estimate.
    Conditional fields whose `show_if` is not met are excluded from the count.
    """
    applicable = [f for f in flow.fields
                  if not (f.show_if and answers.get(f.show_if[0]) != f.show_if[1])]
    if not applicable:
        return 0
    answered = sum(1 for f in applicable if (answers.get(f.id) or "").strip())
    return round(answered / len(applicable) * 100)


def _summary(flow, answers):
    """Build a human (label, value-label) summary from answered fields."""
    choice_maps = {f.id: dict(f.choices) for f in flow.fields if f.choices}
    out = []
    for f in flow.fields:
        raw = (answers.get(f.id) or "").strip()
        if not raw:
            continue
        if f.id in choice_maps and raw in choice_maps[f.id]:
            value_label = choice_maps[f.id][raw]
        else:
            value_label = raw
        out.append((f.label, value_label))
    return tuple(out)


def _signals(specs):
    """Split (ok, strong_label, attention_label) specs into two ordered tuples."""
    strong, attention = [], []
    for ok, s_label, a_label in specs:
        if ok:
            if s_label:
                strong.append(s_label)
        elif a_label:
            attention.append(a_label)
    return tuple(strong), tuple(attention)


def _docs(specs):
    """Build categorised DocItems and the essential-but-missing labels.

    `specs` is an iterable of (label, category, present, reason). Returns
    (document_items, missing_essential_labels).
    """
    items, missing = [], []
    for label, category, present, reason in specs:
        items.append(DocItem(label=label, category=category, present=present, reason=reason))
        if category == DOC_ESSENTIAL and not present:
            missing.append(label)
    return tuple(items), tuple(missing)


# --- Per-flow evaluators ----------------------------------------------------
def _eval_inail(flow, answers):
    has_medical = _yes(answers, "medical_cert")
    has_inail = _yes(answers, "employer_docs")
    pct = _int(answers, "impairment_pct")
    third_party = _yes(answers, "third_party_liability")

    document_items, missing = _docs([
        (pc._DOC_INAIL, DOC_ESSENTIAL, has_inail, _R_INAIL),
        (pc._DOC_MEDICAL, DOC_ESSENTIAL, has_medical, _R_MEDICAL),
        (pc._DOC_INSURANCE, DOC_USEFUL, False, _R_INSURANCE),
    ])

    messages = []
    if pct is not None:
        if 6 <= pct <= 15:
            messages.append(_M_INAIL_CAPITAL)
        elif pct > 15:
            messages.append(_M_INAIL_ANNUITY)
    if third_party:
        messages.append(_M_INAIL_DIFFERENTIAL)

    strong, attention = _signals([
        (has_inail, _SIG_INAIL_OK, _SIG_INAIL_TODO),
        (has_medical, _SIG_MEDICAL_OK, _SIG_MEDICAL_TODO),
        (pct is not None, _SIG_IPP_OK, _SIG_IPP_TODO),
        (third_party, _SIG_THIRDPARTY, ""),
    ])
    completeness = _completeness([has_medical, has_inail])
    return _result(
        flow, answers, completeness, missing, messages,
        next_step=_NS_DOCUMENTAL,
        potential_path=_PATH_INAIL, unlocking=(_UNLOCK_INAIL, _UNLOCK_LIABILITY),
        strong=strong, attention=attention, document_items=document_items,
        path_reason=_WHY_INAIL, assessable_now=_NOW_INAIL, pending=_PEND_INAIL,
        secondary=("crm:contact", {}, pc._CTA_LAW) if third_party else None,
    )


def _eval_loss(flow, answers):
    has_civil = _yes(answers, "civil_docs")
    offer = _yes(answers, "offer_received")
    liability = _yes(answers, "liability_established")
    country = answers.get("country")

    document_items, missing = _docs([
        (pc._DOC_CIVIL, DOC_ESSENTIAL, has_civil, _R_CIVIL),
        (pc._DOC_MEDICAL, DOC_USEFUL, False, _R_MEDICAL),
        (pc._DOC_INSURANCE, DOC_USEFUL, offer, _R_INSURANCE),
    ])

    messages = []
    if country == "IT" and answers.get("death_cause") == "road_accident" and offer:
        messages.append(_M_LOSS_OFFER)
    if country and country != "IT":
        messages.append(_M_LOSS_FOREIGN)

    strong, attention = _signals([
        (has_civil, _SIG_CIVIL_OK, _SIG_CIVIL_TODO),
        (bool(answers.get("relationship")), _SIG_RELATIONSHIP, ""),
        (liability, _SIG_LIABILITY_OK, _SIG_LIABILITY_TODO),
        (offer, _SIG_OFFER, ""),
    ])
    completeness = _completeness([has_civil])

    # Foreign case → primary CTA becomes the applicable-law framing flow.
    if country and country not in ("IT", ""):
        primary = ("core:precheck", {"slug": "international-road-accident"}, pc._CTA_LAW)
        secondary = ("crm:contact", {}, flow.cta_label)
    else:
        primary = ("crm:contact", {}, flow.cta_label)
        secondary = None
    return _result(
        flow, answers, completeness, missing, messages,
        next_step=_NS_DOCUMENTAL, primary=primary, secondary=secondary,
        potential_path=_PATH_PARENTAL, unlocking=(_UNLOCK_PARENTAL,),
        strong=strong, attention=attention, document_items=document_items,
        path_reason=_WHY_PARENTAL, assessable_now=_NOW_PARENTAL, pending=_PEND_PARENTAL,
    )


def _eval_road(flow, answers, ready_message, potential_path, unlock, why, now, pending):
    """Shared logic for Morocco / Tunisia road-accident flows."""
    has_accident = _yes(answers, "police_report")
    has_medical = _yes(answers, "medical_cert")
    has_ipp = _yes(answers, "ipp_known")
    has_income = _yes(answers, "income_documentable")
    insurer_ok = _yes(answers, "vehicle_insured") or _yes(answers, "insurer_identified")
    liability_ok = answers.get("liability_estimate") in ("full", "partial")
    if "liability_estimate" not in {f.id for f in flow.fields}:
        liability_ok = True

    document_items, doc_missing = _docs([
        (pc._DOC_ACCIDENT, DOC_ESSENTIAL, has_accident, _R_ACCIDENT),
        (pc._DOC_MEDICAL, DOC_ESSENTIAL, has_medical, _R_MEDICAL),
        (pc._DOC_INSURANCE, DOC_USEFUL, insurer_ok, _R_INSURANCE),
        (pc._DOC_INCOME, DOC_USEFUL, has_income, _R_INCOME),
    ])
    # Keep the legacy missing set (docs + key data) for backward compatibility.
    missing = list(doc_missing)
    if not has_ipp:
        missing.append(_MISS_IPP)
    if not has_income and pc._DOC_INCOME not in missing:
        missing.append(pc._DOC_INCOME)

    messages = []
    if has_ipp and has_income and liability_ok:
        messages.append(ready_message)

    strong, attention = _signals([
        (has_accident, _SIG_ACCIDENT_OK, _SIG_ACCIDENT_TODO),
        (has_medical, _SIG_MEDICAL_OK, _SIG_MEDICAL_TODO),
        (has_ipp, _SIG_IPP_OK, _SIG_IPP_TODO),
        (has_income, _SIG_INCOME_OK, _SIG_INCOME_TODO),
        (insurer_ok, _SIG_INSURER_OK, _SIG_INSURER_TODO),
        (liability_ok, _SIG_LIABILITY_OK, _SIG_LIABILITY_TODO),
    ])
    completeness = _completeness([has_accident, has_medical])
    return _result(
        flow, answers, completeness, tuple(missing), messages,
        next_step=_NS_DOCUMENTAL,
        potential_path=potential_path, unlocking=(unlock, _UNLOCK_LIABILITY),
        strong=strong, attention=attention, document_items=document_items,
        path_reason=why, assessable_now=now, pending=pending,
    )


def _eval_international(flow, answers):
    foreign = _yes(answers, "foreign_docs") or _yes(answers, "translation_needed")
    has_event = bool((answers.get("event_country") or "").strip())
    has_residence = bool((answers.get("residence_country") or "").strip())
    contract = _yes(answers, "contract_present")

    messages = [_M_INT_LAW, _M_INT_CROSS]
    if foreign:
        messages.insert(1, _M_INT_TRANSLATE)

    document_items, _missing = _docs([
        (pc._DOC_ACCIDENT, DOC_USEFUL, False, _R_ACCIDENT),
        (pc._DOC_INSURANCE, DOC_USEFUL, contract, _R_INSURANCE),
        (_FOREIGN_DOCS, DOC_USEFUL, not foreign, _R_FOREIGN),
    ])
    missing = (_FOREIGN_DOCS,) if foreign else ()

    strong, attention = _signals([
        (has_event, _("Country of the event indicated"), _("Country of the event to confirm")),
        (has_residence, _("Country of residence indicated"), _("Country of residence to confirm")),
        (contract, _SIG_INSURER_OK, _SIG_INSURER_TODO),
    ])
    completeness = _completeness([has_event, has_residence])
    return _result(
        flow, answers, completeness, missing, messages,
        next_step=_NS_LAW,
        potential_path=_PATH_LAW, unlocking=(_UNLOCK_LAW,),
        strong=strong, attention=attention, document_items=document_items,
        path_reason=_WHY_LAW, assessable_now=_NOW_LAW, pending=_PEND_LAW,
    )


def _result(flow, answers, completeness, missing, messages, *, next_step,
            potential_path="", unlocking=(), strong=(), attention=(),
            document_items=(), path_reason="", assessable_now="", pending="",
            primary=None, secondary=None):
    """Assemble a PreCheckResult, including the P25 analytical layer."""
    if primary is None:
        primary = (flow.cta_url_name, {}, flow.cta_label)
    cta_url, cta_kwargs, cta_label = primary
    sec_url, sec_kwargs, sec_label = (secondary or ("", {}, ""))
    status = _STATUS_FROM_COMPLETENESS.get(completeness, STATUS_INITIAL)
    return PreCheckResult(
        completeness=completeness,
        answered_summary=_summary(flow, answers),
        missing_documents=tuple(missing),
        applicable_sources=flow.official_sources,
        messages=tuple(messages),
        next_step=next_step,
        cta_label=cta_label,
        cta_url_name=cta_url,
        cta_kwargs=cta_kwargs,
        readiness_pct=_readiness(flow, answers),
        potential_path=potential_path,
        unlocking_data=tuple(unlocking),
        dossier_summary=_SUMMARY_BY_STATUS.get(status, ""),
        strong_points=tuple(strong),
        attention_points=tuple(attention),
        path_reason=path_reason,
        assessable_now=assessable_now,
        pending_for_estimate=pending,
        document_items=tuple(document_items),
        secondary_cta_label=sec_label,
        secondary_cta_url_name=sec_url,
        secondary_cta_kwargs=sec_kwargs,
    )


def evaluate(flow, answers) -> PreCheckResult:
    """Dispatch to the per-flow evaluator. `answers` is a {field_id: str} dict."""
    if flow.slug == "inail":
        return _eval_inail(flow, answers)
    if flow.slug == "loss-of-relative":
        return _eval_loss(flow, answers)
    if flow.slug == "morocco-road-accident":
        return _eval_road(flow, answers, _M_MA_READY, _PATH_MA, _UNLOCK_MA,
                          _WHY_MA, _NOW_MA, _PEND_MA)
    if flow.slug == "tunisia-road-accident":
        return _eval_road(flow, answers, _M_TN_READY, _PATH_TN, _UNLOCK_TN,
                          _WHY_TN, _NOW_TN, _PEND_TN)
    if flow.slug == "international-road-accident":
        return _eval_international(flow, answers)
    # Defensive fallback — should be unreachable (every flow is handled).
    return _result(flow, answers, INITIAL, (), (), next_step=_NS_DOCUMENTAL)
