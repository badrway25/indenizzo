"""Structured, translatable content for the Workstream-3 public pages.

Single source of truth (gettext_lazy, same pattern as `case_type_landings.py`)
so the rendered page and the FAQPage JSON-LD never drift. NO monetary values,
NO invented legal facts, NO outcome promises — every entry is prudent and
deontological. The only "calculable" service is Italy road-accident bodily
injury (TUN 2025), mirroring the real calculator registry; everything else is
flagged "preliminary assessment".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class Step:
    index: str
    title: str
    body: str


@dataclass(frozen=True)
class Service:
    key: str
    title: str
    body: str
    icon: str            # name resolved by partials/_icon.html (inline SVG, never emoji)
    calculable: bool     # True only where an approved official source/formula exists
    cta_label: str
    cta_url_name: str
    cta_kwargs: dict = field(default_factory=dict)
    # P5: premium, fail-closed badge text (never a weak "preliminary assessment"
    # label) + the governing official instrument shown as "Legal basis". The
    # base_normativa value is a language-neutral legal citation (same in every
    # locale) so it is intentionally NOT wrapped in gettext.
    badge: str = ""
    base_normativa: str = ""


@dataclass(frozen=True)
class Faq:
    question: str
    answer: str


# --- How it works -----------------------------------------------------------
HOW_IT_WORKS_STEPS = (
    Step("01", _("Indicative estimate in a few clicks"),
         _("Answer a short, optional set of questions. Where an official validated source exists, you immediately see an indicative min / mid / max range with the sources behind it.")),
    Step("02", _("Share your documents"),
         _("If you decide to go further, you send the relevant documents. None are required for the first orientation; the Studio asks for what it needs after reading the case.")),
    Step("03", _("Free preliminary assessment"),
         _("A lawyer reviews your request manually and replies on whether and how the Studio can help. The preliminary assessment is free and without obligation.")),
    Step("04", _("Source and formula verification"),
         _("When a calculation is available, it is checked against the official source and the approved formula. When it is not, we say so explicitly rather than invent a number.")),
    Step("05", _("Professional evaluation"),
         _("Where appropriate, the Studio carries out a full legal evaluation — medical-legal aspects, liability, applicable law and competent jurisdiction.")),
    Step("06", _("Written engagement, only if you choose"),
         _("A professional engagement begins solely with a separate written agreement. Fees follow the applicable rules and the forensic code of conduct.")),
)


# --- Services ---------------------------------------------------------------
# P13-FIX: four distinct PUBLIC estimate states, each tied to an approved
# engine where one exists — the estimate badge is NOT limited to road-accident.
_BADGE_OFFICIAL = _("Estimate based on official sources")          # numeric_estimate_approved
_BADGE_TABULAR = _("Official table-based biological damage estimate")  # tabular_biological_damage_approved
_BADGE_OFFER = _("Comparison based on official sources")           # offer_comparison_approved
_BADGE_GUIDED = _("Assisted path based on official sources")       # official_guided_path_approved
# P15: two further public states, differentiating the non-numeric services and
# reusing the pre-check / router msgids so the wording never diverges.
_BADGE_PRECHECK = _("Documental pre-check with official sources")  # documental pre-check
_BADGE_LAW = _("Applicable-law framing")                           # cross-border framing
# P18: distinct badges so the guided services don't all read identically.
_BADGE_MULTILINGUAL = _("Multilingual assistance on official sources")
_BADGE_DOC_VERIFY = _("Documental verification")
_CTA_GUIDED = _("Request a guided analysis")
_CTA_PRECHECK = _("Start the pre-check")

SERVICES = (
    Service("road_accident", _("Road accident"),
            _("Bodily injury from a road accident. Micro-permanent 1–9% on art. 139 CAP and macro 10–100% on the Tabella Unica Nazionale 2025 produce an indicative estimate when the data is compatible."),
            "car", True, _("Calculate the estimate"), "cases:wizard_italy_road_accident",
            badge=_BADGE_OFFICIAL, base_normativa="art. 139 CAP · D.P.R. 12/2025 (TUN) · D.Lgs. 209/2005"),
    Service("medical", _("Medical liability"),
            _("When the injury is quantified medico-legally, the platform produces a tabular biological-damage estimate (1–9% art. 139, 10–100% TUN). It does not assess fault, causation or overall healthcare liability."),
            "stethoscope", True, _("Calculate the tabular estimate"), "cases:wizard_italy_medical",
            badge=_BADGE_TABULAR, base_normativa="L. 24/2017 (Gelli) · artt. 138–139 CAP"),
    Service("work_injury", _("Workplace injury"),
            _("Accidents at work and occupational disease, including the differential beyond INAIL. The Studio frames it on the official sources; an automatic figure follows once the INAIL table is imported."),
            "hard-hat", False, _("Start the INAIL pre-check"), "core:precheck", {"slug": "inail"},
            badge=_BADGE_PRECHECK, base_normativa="D.P.R. 1124/1965 (T.U. INAIL)"),
    Service("death", _("Loss of a relative"),
            _("Death and loss-of-relationship damages for family members. A sensitive, fact-specific area handled directly by the Studio."),
            "heart", False, _("Assisted pathway for relatives"), "core:precheck", {"slug": "loss-of-relative"},
            badge=_BADGE_GUIDED, base_normativa="artt. 2043, 2059 c.c."),
    Service("insurance_offer", _("Insurance offer to check"),
            _("If the offer concerns an injury compatible with art. 139 micro-permanent or the TUN, the platform compares the proposed amount against the official tabular estimate and shows the deviation."),
            "shield-check", True, _("Compare your offer"), "cases:wizard_insurance_offer",
            badge=_BADGE_OFFER, base_normativa="art. 139 CAP · TUN · CAP artt. 145, 148"),
    Service("international", _("Cross-border matters"),
            _("Cases with foreign elements — parties, assets or events abroad — including questions of applicable law and competent jurisdiction."),
            "globe", False, _("Frame the applicable law"), "core:precheck",
            {"slug": "international-road-accident"},
            badge=_BADGE_LAW, base_normativa="Reg. CE 864/2007 (Roma II)"),
    Service("foreigners", _("Foreign nationals in Italy"),
            _("Assistance for foreign or non-resident clients who suffered harm in Italy, with multilingual support and remote handling."),
            "users", False, _CTA_GUIDED, "crm:contact",
            badge=_BADGE_MULTILINGUAL, base_normativa="Roma II · CAP/TUN (Italia)"),
    Service("documents", _("Foreign / consular documents"),
            _("Help with documentation produced abroad — translation, legalisation and consular formalities needed to support a claim."),
            "document", False, _CTA_GUIDED, "crm:contact",
            badge=_BADGE_DOC_VERIFY),
)


# --- FAQ (platform-level, prudent) ------------------------------------------
FAQ_ITEMS = (
    Faq(_("Is the estimate binding?"),
        _("No. It is an indicative orientation based on validated official sources — not a quote, a verdict or a promise. The amount actually awarded depends on documents, expert reports, liability, the applicable law and the deciding court.")),
    Faq(_("Can I calculate any case?"),
        _("An automatic estimate appears where an official validated source and formula exist: today, road-accident bodily injury (art. 139 micro-permanent and the TUN), the tabular biological-damage estimate for healthcare liability, and the insurance-offer comparison. For everything else the platform follows an assisted pathway on official sources instead of inventing a number.")),
    Faq(_("Why are some countries not calculable?"),
        _("Because a figure is published only when the underlying legal source has been validated. For France, Belgium, Morocco and Tunisia the sources are catalogued but not yet validated, so no automatic amount is shown and the Studio reviews those cases manually.")),
    Faq(_("What documents are needed?"),
        _("For a first orientation, none. For a real assessment the Studio typically asks for medical records, accident or incident reports, insurance correspondence and proof of economic impact. A checklist is shown after each simulation.")),
    Faq(_("I already received an offer — can I have it checked?"),
        _("Yes. The Studio can review an insurance or INAIL offer before you accept it. Do not sign a settlement before a professional review: reopening it afterwards can be difficult.")),
    Faq(_("Can I be assisted if I live abroad?"),
        _("Yes. The Studio handles cross-border matters and assists clients living outside Italy, in several languages. A preliminary assessment can be requested remotely.")),
    Faq(_("Is a medical-legal report needed?"),
        _("For permanent injury, a medical-legal assessment is usually decisive for the final valuation. The platform can produce an indicative range without it, but it does not replace the report.")),
    Faq(_("Is the preliminary assessment free?"),
        _("The preliminary assessment of your request is free and without obligation. A professional engagement begins only with a separate written agreement.")),
    Faq(_("Does this site replace legal advice?"),
        _("No. It is an informational tool. It does not constitute legal or medical-legal advice and does not guarantee any outcome. For a binding opinion, request a professional evaluation.")),
    Faq(_("How is my personal data handled?"),
        _("Your data is processed only with your explicit consent, for the stated purpose, under the GDPR. Special-category data (health, income, family) is processed under art. 9 only after a dedicated consent. See the privacy notice for details.")),
)
