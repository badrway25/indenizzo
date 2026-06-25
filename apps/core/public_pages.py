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
_BADGE_OFFICIAL = _("Official-source estimate")
_BADGE_ASSISTED = _("Assisted legal pathway")
_CTA_GUIDED = _("Request a guided analysis")

SERVICES = (
    Service("road_accident", _("Road accident"),
            _("Bodily injury from a road accident. Where the case fits the official Tabella Unica Nazionale 2025, the platform produces an indicative range; otherwise the Studio reviews it."),
            "car", True, _("Calculate the estimate"), "cases:wizard_italy_road_accident",
            badge=_BADGE_OFFICIAL, base_normativa="D.P.R. 12/2025 (TUN) · CAP D.Lgs. 209/2005"),
    Service("medical", _("Medical liability"),
            _("Suspected medical or healthcare malpractice. These cases hinge on expert evidence and are assessed by the Studio — no automatic figure is published."),
            "stethoscope", False, _CTA_GUIDED, "crm:contact",
            badge=_BADGE_ASSISTED, base_normativa="L. 24/2017 (Gelli) · artt. 1218, 2043 c.c."),
    Service("work_injury", _("Workplace injury"),
            _("Accidents at work and occupational disease, including the differential beyond INAIL. Reviewed by the Studio; not automatically calculated today."),
            "hard-hat", False, _CTA_GUIDED, "crm:contact",
            badge=_BADGE_ASSISTED, base_normativa="D.P.R. 1124/1965 (T.U. INAIL)"),
    Service("death", _("Loss of a relative"),
            _("Death and loss-of-relationship damages for family members. A sensitive, fact-specific area handled directly by the Studio."),
            "heart", False, _("Assisted pathway for relatives"), "crm:contact",
            badge=_BADGE_ASSISTED, base_normativa="artt. 2043, 2059 c.c."),
    Service("insurance_offer", _("Insurance / INAIL offer to check"),
            _("You received a settlement or INAIL offer. The Studio can review whether it is adequate before you sign — do not accept a settlement without a professional review."),
            "shield-check", False, _("Have your offer reviewed"), "crm:contact",
            badge=_("Insurance procedure"), base_normativa="CAP D.Lgs. 209/2005, artt. 145, 148"),
    Service("international", _("Cross-border matters"),
            _("Cases with foreign elements — parties, assets or events abroad — including questions of applicable law and competent jurisdiction."),
            "globe", False, _("Frame the applicable law"), "crm:contact",
            badge=_("Applicable law"), base_normativa="Reg. CE 864/2007 (Roma II)"),
    Service("foreigners", _("Foreign nationals in Italy"),
            _("Assistance for foreign or non-resident clients who suffered harm in Italy, with multilingual support and remote handling."),
            "users", False, _CTA_GUIDED, "crm:contact",
            badge=_BADGE_ASSISTED, base_normativa="Roma II · CAP/TUN (Italia)"),
    Service("documents", _("Foreign / consular documents"),
            _("Help with documentation produced abroad — translation, legalisation and consular formalities needed to support a claim."),
            "document", False, _CTA_GUIDED, "crm:contact",
            badge=_("Document analysis")),
)


# --- FAQ (platform-level, prudent) ------------------------------------------
FAQ_ITEMS = (
    Faq(_("Is the estimate binding?"),
        _("No. It is an indicative orientation based on validated official sources — not a quote, a verdict or a promise. The amount actually awarded depends on documents, expert reports, liability, the applicable law and the deciding court.")),
    Faq(_("Can I calculate any case?"),
        _("No. An automatic estimate appears only where an official, validated source and formula exist — today, road-accident bodily injury in Italy on the Tabella Unica Nazionale 2025. For everything else the platform asks for a preliminary assessment instead of inventing a number.")),
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
