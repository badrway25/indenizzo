"""P15 — guided documental pre-check flows for non-numeric sections.

Where no approved engine exists but an official source does, the public must get
a CONCRETE guided pre-check (not a roadmap, not a weak label): the official
sources, exactly which data and documents to prepare, the next step and a CTA —
and NEVER an amount. Single source of truth (gettext_lazy), rendered by
`templates/public/precheck.html` via `core.views.precheck(request, slug)`.

Cardinal rule: no amount/coefficient is computed or shown here. The estimate
activates only once the relevant official table is imported and canary-green
(tracked in the approval queue).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from django.utils.translation import gettext_lazy as _

# Public status labels (reused; never a weak/technical state).
STATUS_PRECHECK = "precheck"
STATUS_GUIDED = "guided"
STATUS_APPLICABLE_LAW = "applicable_law"

STATUS_LABEL = {
    STATUS_PRECHECK: _("Documental pre-check with official sources"),
    STATUS_GUIDED: _("Assisted path based on official sources"),
    STATUS_APPLICABLE_LAW: _("Applicable-law framing"),
}

# Reusable data-point labels (kept shared to bound the i18n surface).
_D_EVENT_DATE = _("Date of the event")
_D_AGE = _("Age of the person involved")
_D_IMPAIRMENT = _("Estimated impairment degree, if assessed")
_D_LIABILITY = _("Established liability and any insurance offer received")
_D_INCOME = _("Income or economic impact, where relevant")
_D_HEIRS = _("Eligible family members, in case of death")
_D_RELATIONSHIP = _("Relationship with the victim and cohabitation")
_D_INSURED = _("Whether the vehicle is insured and the insurer")
_D_PLACE = _("Country and place of the event")

# Reusable document-checklist labels.
_DOC_MEDICAL = _("Medical-legal report or impairment certificate")
_DOC_ACCIDENT = _("Accident or police report (constat amiable, PV, CAI)")
_DOC_INSURANCE = _("Insurance correspondence and any settlement offer")
_DOC_CIVIL = _("Civil-status and family documents")
_DOC_INCOME = _("Proof of income or economic loss")
_DOC_INAIL = _("INAIL notification and recognition documents")

_CTA_PRECHECK = _("Request the documental check")
_CTA_LAW = _("Frame the applicable law")
_DISCLAIMER = _("No amount is calculated without a verified official table or formula.")


@dataclass(frozen=True)
class PreCheckFlow:
    slug: str
    title: str
    country_code: str
    status: str
    intro: str
    official_sources: tuple = field(default_factory=tuple)  # language-neutral citations
    data_points: tuple = field(default_factory=tuple)
    documents: tuple = field(default_factory=tuple)
    cta_label: str = ""
    cta_url_name: str = "crm:contact"

    @property
    def status_label(self):
        return STATUS_LABEL.get(self.status, STATUS_LABEL[STATUS_GUIDED])


PRECHECK_FLOWS: tuple[PreCheckFlow, ...] = (
    PreCheckFlow(
        slug="inail",
        title=_("INAIL work injury — documental pre-check"),
        country_code="IT",
        status=STATUS_PRECHECK,
        intro=_(
            "Work-injury indemnity combines the mandatory INAIL biological-damage "
            "table with any civil-liability differential. Prepare the data below; "
            "the automatic INAIL figure activates once the official table is "
            "imported and verified."
        ),
        official_sources=("D.P.R. 1124/1965 (T.U. INAIL)", "D.Lgs. 38/2000 (art. 13)",
                          "D.M. 45/2019 — tabella indennizzo capitale"),
        data_points=(_D_EVENT_DATE, _D_AGE, _D_IMPAIRMENT,
                     _("Whether INAIL has already recognised the case"),
                     _("Any annuity or capital already paid by INAIL")),
        documents=(_DOC_INAIL, _DOC_MEDICAL, _DOC_INSURANCE),
        cta_label=_CTA_PRECHECK,
    ),
    PreCheckFlow(
        slug="loss-of-relative",
        title=_("Loss of a relative — documental pre-check"),
        country_code="IT",
        status=STATUS_GUIDED,
        intro=_(
            "The loss of a close relative may give rise to compensation for the "
            "parental/family relationship and patrimonial damage. There is no "
            "state table, so the Studio frames it on the official sources and the "
            "documents below — no automatic figure is published."
        ),
        official_sources=("artt. 2043, 2059 Cod. Civile", "artt. 1223, 1226 Cod. Civile"),
        data_points=(_D_RELATIONSHIP, _D_AGE,
                     _("Cause of death and any established liability"),
                     _D_LIABILITY),
        documents=(_DOC_CIVIL, _DOC_MEDICAL, _DOC_INSURANCE),
        cta_label=_CTA_PRECHECK,
    ),
    PreCheckFlow(
        slug="morocco-road-accident",
        title=_("Road accident in Morocco — documental pre-check"),
        country_code="MA",
        status=STATUS_PRECHECK,
        intro=_(
            "Road-accident compensation in Morocco follows the Dahir 1984 method "
            "(capital de référence × taux d'incapacité × taux de responsabilité). "
            "Prepare the data below; no MAD amount is shown until the official "
            "capital-de-référence table is validated."
        ),
        official_sources=("Dahir 1-84-177 (1984)", "ACAPS — guide d'indemnisation",
                          "Code des assurances", "Code des obligations et des contrats"),
        data_points=(_("Injury or death"), _D_PLACE, _D_EVENT_DATE, _D_INSURED,
                     _D_IMPAIRMENT, _D_INCOME, _D_HEIRS),
        documents=(_DOC_INSURANCE, _DOC_ACCIDENT, _DOC_MEDICAL, _DOC_CIVIL),
        cta_label=_CTA_PRECHECK,
    ),
    PreCheckFlow(
        slug="tunisia-road-accident",
        title=_("Road accident in Tunisia — documental pre-check"),
        country_code="TN",
        status=STATUS_PRECHECK,
        intro=_(
            "Road-accident compensation in Tunisia follows the binding loi 2005-86 "
            "barème (Code des assurances, Titre V). Prepare the data below; no TND "
            "amount is shown until that barème is validated."
        ),
        official_sources=("Loi 2005-86 — Code des assurances (Titre V)",
                          "Comité Général des Assurances (CGA)",
                          "Code des obligations et des contrats tunisien"),
        data_points=(_("Injury or death"), _D_EVENT_DATE, _D_INSURED,
                     _D_IMPAIRMENT, _D_INCOME, _D_HEIRS),
        documents=(_DOC_INSURANCE, _DOC_ACCIDENT, _DOC_MEDICAL, _DOC_CIVIL),
        cta_label=_CTA_PRECHECK,
    ),
    PreCheckFlow(
        slug="international-road-accident",
        title=_("Cross-border road accident — applicable-law framing"),
        country_code="INT",
        status=STATUS_APPLICABLE_LAW,
        intro=_(
            "When the accident has foreign elements, the first step is identifying "
            "the applicable law and the competent court under Rome II, before any "
            "quantification. No amount is produced at this stage."
        ),
        official_sources=("Reg. (CE) 864/2007 (Roma II)", "Reg. (UE) 650/2012",
                          "Conv. de La Haye — accidents de la circulation"),
        data_points=(_D_PLACE,
                     _("Country of residence of the parties"),
                     _("Insurer and country of the vehicle"),
                     _("Whether proceedings are open abroad")),
        documents=(_DOC_ACCIDENT, _DOC_INSURANCE,
                   _("Foreign documents to be translated / legalised")),
        cta_label=_CTA_LAW,
    ),
)

PRECHECK_BY_SLUG = {f.slug: f for f in PRECHECK_FLOWS}


def get_precheck(slug: str) -> PreCheckFlow | None:
    return PRECHECK_BY_SLUG.get(slug)
