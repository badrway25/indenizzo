"""P16 — pre-check decision engine: turns interactive answers into a guided result.

Given a `PreCheckFlow` and the submitted answers, this produces a personalised,
non-numeric result: a completeness level, the missing documents/data, the
applicable official sources, contextual guidance messages, the recommended next
step and a CTA. It NEVER computes or shows an amount — these flows have no
approved engine, so the output is organisational, not monetary.

Stateless: the answers are evaluated in memory and never persisted (GDPR-light).
"""

from __future__ import annotations

from dataclasses import dataclass, field

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

    @property
    def completeness_label(self):
        return COMPLETENESS_LABEL[self.completeness]

    @property
    def completeness_tone(self):
        return COMPLETENESS_TONE[self.completeness]


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


# --- Per-flow evaluators ----------------------------------------------------
def _eval_inail(flow, answers):
    missing = []
    if not _yes(answers, "medical_cert"):
        missing.append(pc._DOC_MEDICAL)
    if not _yes(answers, "employer_docs"):
        missing.append(pc._DOC_INAIL)

    messages = []
    pct = _int(answers, "impairment_pct")
    if pct is not None:
        if 6 <= pct <= 15:
            messages.append(_M_INAIL_CAPITAL)
        elif pct > 15:
            messages.append(_M_INAIL_ANNUITY)
    if _yes(answers, "third_party_liability"):
        messages.append(_M_INAIL_DIFFERENTIAL)

    completeness = _completeness([_yes(answers, "medical_cert"), _yes(answers, "employer_docs")])
    return PreCheckResult(
        completeness=completeness,
        answered_summary=_summary(flow, answers),
        missing_documents=tuple(missing),
        applicable_sources=flow.official_sources,
        messages=tuple(messages),
        next_step=_NS_DOCUMENTAL,
        cta_label=flow.cta_label,
    )


def _eval_loss(flow, answers):
    missing = []
    if not _yes(answers, "civil_docs"):
        missing.append(pc._DOC_CIVIL)

    messages = []
    country = answers.get("country")
    if country == "IT" and answers.get("death_cause") == "road_accident" and _yes(answers, "offer_received"):
        messages.append(_M_LOSS_OFFER)
    if country and country != "IT":
        messages.append(_M_LOSS_FOREIGN)

    completeness = _completeness([_yes(answers, "civil_docs")])
    # Foreign case → suggest the applicable-law framing flow as the CTA.
    if country and country not in ("IT", ""):
        cta_url, cta_kwargs, cta_label = ("core:precheck",
                                          {"slug": "international-road-accident"},
                                          pc._CTA_LAW)
    else:
        cta_url, cta_kwargs, cta_label = ("crm:contact", {}, flow.cta_label)
    return PreCheckResult(
        completeness=completeness,
        answered_summary=_summary(flow, answers),
        missing_documents=tuple(missing),
        applicable_sources=flow.official_sources,
        messages=tuple(messages),
        next_step=_NS_DOCUMENTAL,
        cta_label=cta_label,
        cta_url_name=cta_url,
        cta_kwargs=cta_kwargs,
    )


def _eval_road(flow, answers, ready_message):
    """Shared logic for Morocco / Tunisia road-accident flows."""
    missing = []
    if not _yes(answers, "police_report"):
        missing.append(pc._DOC_ACCIDENT)
    if not _yes(answers, "medical_cert"):
        missing.append(pc._DOC_MEDICAL)
    if not _yes(answers, "ipp_known"):
        missing.append(_MISS_IPP)
    if not _yes(answers, "income_documentable"):
        missing.append(pc._DOC_INCOME)

    messages = []
    liability_ok = answers.get("liability_estimate") in ("full", "partial")
    # Tunisia has no liability_estimate field → treat as satisfied there.
    if "liability_estimate" not in {f.id for f in flow.fields}:
        liability_ok = True
    if _yes(answers, "ipp_known") and _yes(answers, "income_documentable") and liability_ok:
        messages.append(ready_message)

    completeness = _completeness([_yes(answers, "police_report"), _yes(answers, "medical_cert")])
    return PreCheckResult(
        completeness=completeness,
        answered_summary=_summary(flow, answers),
        missing_documents=tuple(missing),
        applicable_sources=flow.official_sources,
        messages=tuple(messages),
        next_step=_NS_DOCUMENTAL,
        cta_label=flow.cta_label,
    )


def _eval_international(flow, answers):
    messages = [_M_INT_LAW, _M_INT_CROSS]
    missing = []
    if _yes(answers, "foreign_docs") or _yes(answers, "translation_needed"):
        messages.insert(1, _M_INT_TRANSLATE)
        missing.append(_FOREIGN_DOCS)

    # Completeness here reflects whether the key location facts are provided.
    present = [bool((answers.get("event_country") or "").strip()),
               bool((answers.get("residence_country") or "").strip())]
    completeness = _completeness(present)
    return PreCheckResult(
        completeness=completeness,
        answered_summary=_summary(flow, answers),
        missing_documents=tuple(missing),
        applicable_sources=flow.official_sources,
        messages=tuple(messages),
        next_step=_NS_LAW,
        cta_label=flow.cta_label,
    )


def evaluate(flow, answers) -> PreCheckResult:
    """Dispatch to the per-flow evaluator. `answers` is a {field_id: str} dict."""
    if flow.slug == "inail":
        return _eval_inail(flow, answers)
    if flow.slug == "loss-of-relative":
        return _eval_loss(flow, answers)
    if flow.slug == "morocco-road-accident":
        return _eval_road(flow, answers, _M_MA_READY)
    if flow.slug == "tunisia-road-accident":
        return _eval_road(flow, answers, _M_TN_READY)
    if flow.slug == "international-road-accident":
        return _eval_international(flow, answers)
    # Defensive fallback — should be unreachable (every flow is handled).
    return PreCheckResult(
        completeness=INITIAL,
        answered_summary=_summary(flow, answers),
        missing_documents=(),
        applicable_sources=flow.official_sources,
        messages=(),
        next_step=_NS_DOCUMENTAL,
        cta_label=flow.cta_label,
    )
