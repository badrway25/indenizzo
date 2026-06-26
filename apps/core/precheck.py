"""P15/P16 — guided documental pre-check flows for non-numeric sections.

Where no approved engine exists but an official source does, the public gets a
CONCRETE interactive pre-check (P16): a premium mini-form whose answers produce a
personalised guided result — completeness, missing documents, the applicable
official source, the next step and a contextual CTA — and NEVER an amount.

Single source of truth (gettext_lazy), rendered by `templates/public/precheck.html`
via `core.views.precheck(request, slug)`. The decision logic lives in
`apps/core/precheck_engine.py` (kept separate so the form schema and the result
reasoning evolve independently).

Cardinal rule: no amount/coefficient is computed or shown here. A numeric estimate
activates only once the relevant official table is imported and canary-green.
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

# --- Interactive form schema (P16) ------------------------------------------
# Shared choice sets to bound the translation surface.
_YES = _("Yes")
_NO = _("No")
_UNKNOWN = _("I don't know")
_YESNO = (("yes", _YES), ("no", _NO))
_YESNO_UNK = (("yes", _YES), ("no", _NO), ("unknown", _UNKNOWN))


@dataclass(frozen=True)
class PreCheckField:
    """One question in an interactive pre-check form.

    `type` ∈ {select, date, number, text, radio, checkbox}. `choices` is a tuple
    of (value, gettext_label) for select/radio. `privacy` documents the
    sensitivity (low/medium/high) — nothing is persisted, but the level drives
    the on-page note and keeps us honest about what we ask. `show_if` reveals the
    field only when another field equals a value (progressive disclosure).
    """

    id: str
    label: str
    type: str
    required: bool = False
    choices: tuple = ()
    help_text: str = ""
    privacy: str = "low"
    min_value: int | None = None
    max_value: int | None = None
    show_if: tuple | None = None  # (field_id, value)

    @property
    def is_choice(self) -> bool:
        return self.type in ("select", "radio")


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
    fields: tuple = field(default_factory=tuple)  # P16 interactive form

    @property
    def status_label(self):
        return STATUS_LABEL.get(self.status, STATUS_LABEL[STATUS_GUIDED])


# --- Per-flow field schemas -------------------------------------------------
_INAIL_FIELDS = (
    PreCheckField("event_date", _("Date of the event"), "date", required=True, privacy="low"),
    PreCheckField("age", _("Age at the time of the event"), "number", required=True,
                  min_value=0, max_value=120, privacy="low"),
    PreCheckField("impairment_pct", _("Estimated impairment percentage"), "number",
                  min_value=0, max_value=100, privacy="medium",
                  help_text=_("Enter the percentage only if a doctor has assessed it.")),
    PreCheckField("inail_recognised", _("Has INAIL already recognised the case?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("benefit_received", _("Have you already received an annuity or capital from INAIL?"),
                  "radio", choices=_YESNO, privacy="medium"),
    PreCheckField("medical_cert", _("Is a medical-legal certificate available?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("employer_docs", _("Are the INAIL notification / employer documents available?"),
                  "radio", choices=_YESNO, privacy="low"),
    PreCheckField("third_party_liability",
                  _("Is there possible third-party or employer liability?"), "radio",
                  choices=_YESNO, privacy="low"),
)

_LOSS_FIELDS = (
    PreCheckField("country", _("Country"), "select", required=True, privacy="low",
                  choices=(("IT", _("Italy")), ("FR", _("France")), ("BE", _("Belgium")),
                           ("MA", _("Morocco")), ("TN", _("Tunisia")), ("other", _("Other country")))),
    PreCheckField("death_cause", _("Cause of death"), "select", privacy="medium",
                  choices=(("road_accident", _("Road accident")), ("medical", _("Medical event")),
                           ("work", _("Workplace event")), ("other", _("Other cause")))),
    PreCheckField("relationship", _("Relationship with the victim"), "select", privacy="medium",
                  choices=(("spouse", _("Spouse or partner")), ("child", _("Child")),
                           ("parent", _("Parent")), ("sibling", _("Sibling")), ("other", _("Other relative")))),
    PreCheckField("cohabitation", _("Did you live with the victim?"), "radio",
                  choices=_YESNO, privacy="medium"),
    PreCheckField("victim_age", _("Age of the victim"), "number", min_value=0, max_value=120, privacy="low"),
    PreCheckField("family_age", _("Age of the family member"), "number", min_value=0, max_value=120, privacy="low"),
    PreCheckField("liability_established", _("Has liability been established?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("offer_received", _("Has an insurance offer been received?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("civil_docs", _("Are the civil-status documents available?"), "radio",
                  choices=_YESNO, privacy="low"),
)

_MOROCCO_FIELDS = (
    PreCheckField("injury_or_death", _("Injury or death"), "radio", required=True, privacy="medium",
                  choices=(("injury", _("Injury")), ("death", _("Death")))),
    PreCheckField("event_date", _("Date of the event"), "date", privacy="low"),
    PreCheckField("place", _("Place / city"), "text", privacy="low"),
    PreCheckField("vehicle_insured", _("Is the vehicle insured?"), "select",
                  choices=_YESNO_UNK, privacy="low"),
    PreCheckField("liability_estimate", _("Estimated liability"), "select", privacy="low",
                  choices=(("full", _("Fully the other party")), ("partial", _("Shared")),
                           ("none", _("Not the other party")), ("unknown", _("I don't know")))),
    PreCheckField("ipp_known", _("Is the permanent-incapacity rate (IPP) known?"), "radio",
                  choices=_YESNO, privacy="medium"),
    PreCheckField("income_documentable", _("Is income documentable?"), "radio",
                  choices=_YESNO, privacy="medium"),
    PreCheckField("heirs", _("Are there eligible family members?"), "radio", choices=_YESNO,
                  privacy="medium", show_if=("injury_or_death", "death")),
    PreCheckField("police_report", _("Is the police report / constat available?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("medical_cert", _("Is a medical certificate available?"), "radio",
                  choices=_YESNO, privacy="low"),
)

_TUNISIA_FIELDS = (
    PreCheckField("injury_or_death", _("Injury or death"), "radio", required=True, privacy="medium",
                  choices=(("injury", _("Injury")), ("death", _("Death")))),
    PreCheckField("event_date", _("Date of the event"), "date", privacy="low"),
    PreCheckField("insurer_identified", _("Is the insurer identified?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("ipp_known", _("Is the permanent-incapacity rate (IPP) known?"), "radio",
                  choices=_YESNO, privacy="medium"),
    PreCheckField("income_documentable", _("Is income documentable?"), "radio",
                  choices=_YESNO, privacy="medium"),
    PreCheckField("heirs", _("Are there eligible family members?"), "radio", choices=_YESNO,
                  privacy="medium", show_if=("injury_or_death", "death")),
    PreCheckField("police_report", _("Is the police report (PV / constat) available?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("medical_cert", _("Is a medical certificate available?"), "radio",
                  choices=_YESNO, privacy="low"),
)

_INTERNATIONAL_FIELDS = (
    PreCheckField("event_country", _("Country where the event happened"), "text", required=True, privacy="low"),
    PreCheckField("residence_country", _("Country of residence of the injured party"), "text", privacy="low"),
    PreCheckField("insurer_country", _("Country of the insurer"), "text", privacy="low"),
    PreCheckField("damage_type", _("Type of damage"), "select", privacy="medium",
                  choices=(("injury", _("Personal injury")), ("death", _("Death")),
                           ("property", _("Property damage")))),
    PreCheckField("contract_present", _("Is there a contract or insurance policy?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("foreign_docs", _("Are there documents in a foreign language?"), "radio",
                  choices=_YESNO, privacy="low"),
    PreCheckField("translation_needed", _("Is a translation needed?"), "radio",
                  choices=_YESNO, privacy="low"),
)


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
        fields=_INAIL_FIELDS,
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
        fields=_LOSS_FIELDS,
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
        fields=_MOROCCO_FIELDS,
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
        fields=_TUNISIA_FIELDS,
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
        fields=_INTERNATIONAL_FIELDS,
    ),
)

PRECHECK_BY_SLUG = {f.slug: f for f in PRECHECK_FLOWS}


def get_precheck(slug: str) -> PreCheckFlow | None:
    return PRECHECK_BY_SLUG.get(slug)
