"""Data module — content for case-type landing pages (PRODUCT-4).

Each entry describes one public landing page under
`/case-types/<slug>/`. The data is rendered by a single template
(`templates/public/case_type_landing.html`) so adding / editing a
landing is a one-place change.

Deontological guardrails (enforced by tests + content hygiene
audit):

- No promise of result.
- No EUR amounts in copy.
- No "scopri quanto ti spetta" / "ottieni il risarcimento" / "pay
  only if you win" / "no win no fee" — see
  `apps/cases/test_product_3_wizard_mobile_ux.py::BANNED_PROMISE_PHRASES`
  and `scripts/audit_legal_content_hygiene.py`.
- Every landing carries a primary CTA (wizard if a direct wizard
  exists for the case-type, else contact form with
  `?case_type=<code>` prefill) AND a secondary CTA. Both CTAs lead
  to pages already in tree.
- Each landing's copy stays at the level of "what kind of cases
  the Studio handles and what to bring for a preliminary review"
  — informational, not advisory. No claim is case-specific.

URL slug convention: English snake-case ("road-accident",
"medical-malpractice", etc.) — matches the repo's existing
conventions (`/case-types/`, `/wizard/it/road-accident/`, etc.).
This is documented in
`docs/product/CASE_TYPE_LANDING_AUDIT_2026-05-12.md`.

How to add a new landing: append a new entry to LANDINGS below. The
view (`core.views.case_type_landing`) and template will pick it up
automatically. Add the URL + slug to the
`_GLOBAL_HREFLANG_VIEW_NAMES` allowlist in
`apps.core.context_processors` for hreflang coverage.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from django.urls import reverse
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class CaseTypeLanding:
    """One per-case-type SEO/product landing page.

    All translatable strings are `gettext_lazy` so they resolve to
    the request locale at render time.
    """

    slug: str
    """Slug used in the URL `/case-types/<slug>/`. English snake-case."""

    case_type_code: str = ""
    """
    The `CaseType` enum value this landing maps to, if any. Empty
    string for landings that describe a profile (e.g. "foreigners
    in Italy") rather than a single case-type code.
    """

    h1: str = ""
    """The page H1. Translatable."""

    meta_title: str = ""
    """`<title>` content. Translatable. If empty, falls back to H1 + site name."""

    meta_description: str = ""
    """`<meta name="description">`. Translatable."""

    intro: str = ""
    """One-paragraph intro under the H1. Translatable."""

    when_it_applies: Sequence[str] = field(default_factory=tuple)
    """Bulleted "when this applies" items. Translatable strings."""

    what_studio_does: Sequence[str] = field(default_factory=tuple)
    """Bulleted list of concrete steps the Studio performs. Translatable."""

    primary_cta_label: str = ""
    primary_cta_url_name: str = ""
    """Reverse-able URL name for the primary CTA (wizard or contact)."""
    primary_cta_url_kwargs: dict = field(default_factory=dict)

    secondary_cta_label: str = ""
    secondary_cta_url_name: str = ""
    secondary_cta_url_kwargs: dict = field(default_factory=dict)

    def primary_cta_href(self) -> str:
        url = reverse(self.primary_cta_url_name, kwargs=self.primary_cta_url_kwargs)
        # Append `?case_type=<code>` querystring if the primary CTA
        # is the contact form AND we have a case_type code to carry.
        if self.case_type_code and self.primary_cta_url_name == "crm:contact":
            url = f"{url}?case_type={self.case_type_code}"
        return url

    def secondary_cta_href(self) -> str:
        url = reverse(self.secondary_cta_url_name, kwargs=self.secondary_cta_url_kwargs)
        if self.case_type_code and self.secondary_cta_url_name == "crm:contact":
            url = f"{url}?case_type={self.case_type_code}"
        return url


# Note on CaseType codes used below. We avoid a hard import of
# `CaseType` from `apps.calculators.enums` at module-load time
# (it would create a circular import: enums imports translation
# modules → context loaders → views → this module). The codes here
# match the enum values at `apps/calculators/enums.py:18-38`.
# A static test asserts they stay in sync.
_CODE_ROAD = "road_accident_bodily_injury"
_CODE_MEDICAL = "medical_malpractice"
_CODE_WORK = "work_injury"
_CODE_DEATH = "death_compensation"
_CODE_INT_INHERITANCE = "international_inheritance"
_CODE_GENERIC = "generic_legal_assessment"


LANDINGS: tuple[CaseTypeLanding, ...] = (
    CaseTypeLanding(
        slug="road-accident",
        case_type_code=_CODE_ROAD,
        h1=_("Road accident — bodily injury"),
        meta_title=_("Road accident bodily injury — preliminary legal assessment"),
        meta_description=_(
            "Preliminary legal assessment of road-accident bodily injury claims, "
            "based on the Tabella Unica Nazionale 2025 in Italy and recognised "
            "indicative references in France and Belgium. Indicative, not a "
            "guarantee of outcome."
        ),
        intro=_(
            "If you were injured in a road accident as a driver, passenger, "
            "cyclist or pedestrian, the Studio reviews each case manually and "
            "produces a preliminary indicative assessment based on validated "
            "legal sources. No automatic figure is published before the "
            "underlying sources have been verified for your case."
        ),
        when_it_applies=(
            _("You suffered bodily injury after a collision involving a vehicle, on a public or private road."),
            _("A medical report has assessed your temporary or permanent disability, or your medical course is ongoing."),
            _("The insurer of the third party has made an offer you want to verify, or no offer has yet been made."),
            _("You hold or are entitled to a certificate identifying the responsible party (police report, constat amiable, CAI)."),
        ),
        what_studio_does=(
            _("Reads the available pieces (medical reports, insurance correspondence) and identifies the applicable jurisdiction."),
            _("Runs the indicative simulation against the validated legal sources and prepares the breakdown by head of damage."),
            _("Highlights the documents missing for a binding evaluation and the next legal steps available to you."),
            _("Proposes whether and how the Studio can take the case forward — without any automatic engagement."),
        ),
        primary_cta_label=_("Start indicative simulation"),
        primary_cta_url_name="cases:wizard_italy_road_accident",
        secondary_cta_label=_("Request a legal review instead"),
        secondary_cta_url_name="crm:contact",
    ),
    CaseTypeLanding(
        slug="bodily-injury",
        case_type_code=_CODE_ROAD,
        h1=_("Bodily injury claims"),
        meta_title=_("Bodily injury — preliminary legal assessment"),
        meta_description=_(
            "Preliminary legal assessment of bodily injury claims (permanent "
            "disability, temporary disability, biological damage), based on "
            "the validated legal sources approved for the chosen jurisdiction. "
            "Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "Bodily injury — sometimes referred to as biological damage — "
            "covers temporary disability, permanent disability and the broader "
            "impact on your life from a documented injury. The Studio reviews "
            "each case manually using validated legal sources and produces a "
            "preliminary indicative assessment, not a binding evaluation."
        ),
        when_it_applies=(
            _("A medical-legal report has assessed your permanent disability percentage, or the assessment is in progress."),
            _("You also suffered temporary disability (ITT) or partial temporary disability (ITP), with documented duration."),
            _("The injury has impact on your daily life, your work capacity or your relational life that you want recognised."),
        ),
        what_studio_does=(
            _("Reads the medical-legal report and identifies the applicable indicative source (e.g. Tabella Unica Nazionale 2025 in Italy)."),
            _("Computes an indicative range using validated coefficients, highlighting the assumptions made and the missing documents."),
            _("Helps you understand whether the figure offered by an insurer is in line with the indicative range or significantly below."),
        ),
        primary_cta_label=_("Start indicative simulation"),
        primary_cta_url_name="cases:wizard_italy_road_accident",
        secondary_cta_label=_("Request a legal review instead"),
        secondary_cta_url_name="crm:contact",
    ),
    CaseTypeLanding(
        slug="insurance-offer-review",
        case_type_code=_CODE_GENERIC,
        h1=_("Insurance offer review"),
        meta_title=_("Insurance offer review — preliminary legal assessment"),
        meta_description=_(
            "Preliminary review of insurance settlement offers in road-accident "
            "and bodily-injury cases. The Studio compares the offer against "
            "validated indicative sources and highlights what is missing. "
            "Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "You received an offer from an insurance company but you are not "
            "sure whether it reflects what your case is worth. The Studio "
            "reviews each offer manually, compares it against validated "
            "indicative sources and gives you a preliminary indicative "
            "assessment of whether to accept, negotiate or refuse. No "
            "professional engagement is created by this review."
        ),
        when_it_applies=(
            _("An insurer has sent a written settlement offer and you have time to evaluate it."),
            _("You want to understand whether the offer reflects the indicative range supported by validated sources."),
            _("You are negotiating an offer and want a second opinion before signing anything."),
            _("Important: do not sign a settlement without a legal review — once signed, most counter-claims are precluded."),
        ),
        what_studio_does=(
            _("Reviews the offer letter and the documents you have, identifies the legal basis the insurer is relying on."),
            _("Compares the offer against the validated indicative range for the case (e.g. Tabella Unica Nazionale 2025 in Italy)."),
            _("Indicates whether the offer is in line, below, or significantly below the indicative range — and what is missing."),
            _("Recommends the next step — accept, negotiate, refuse — without any automatic engagement."),
        ),
        primary_cta_label=_("Request a legal review of your offer"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Run the indicative simulation first"),
        secondary_cta_url_name="cases:wizard_start",
    ),
    CaseTypeLanding(
        slug="work-injury",
        case_type_code=_CODE_WORK,
        h1=_("Work injury"),
        meta_title=_("Work injury — preliminary legal assessment"),
        meta_description=_(
            "Preliminary legal assessment of work-injury claims and the "
            "interaction between mandatory insurance (e.g. INAIL in Italy) and "
            "additional civil liability. Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "Work injuries combine mandatory work-insurance coverage (e.g. INAIL "
            "in Italy) with potential civil liability of the employer or third "
            "parties. The Studio reviews each case manually to identify what is "
            "covered by mandatory insurance, what may be claimed as additional "
            "damages, and how to document the case correctly. A preliminary "
            "indicative assessment is provided after that review."
        ),
        when_it_applies=(
            _("You were injured during work activities, including commuting where covered by law."),
            _("Mandatory work insurance has already been notified, or you need help notifying it."),
            _("You believe the injury was caused or aggravated by inadequate safety conditions, equipment or training."),
            _("A medical report has assessed the permanent or temporary impact, or the assessment is in progress."),
        ),
        what_studio_does=(
            _("Identifies what is covered by mandatory work insurance and what remains for civil-liability review."),
            _("Reviews the safety documentation (DVR, equipment records, training certificates) for a possible additional claim."),
            _("Provides a preliminary indicative assessment of the additional damages potentially recoverable."),
            _("Indicates next steps and missing documents — without any automatic engagement."),
        ),
        primary_cta_label=_("Request a legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
    ),
    CaseTypeLanding(
        slug="medical-malpractice",
        case_type_code=_CODE_MEDICAL,
        h1=_("Medical malpractice"),
        meta_title=_("Medical malpractice — preliminary legal assessment"),
        meta_description=_(
            "Preliminary legal assessment of medical-malpractice claims. The "
            "Studio reviews the clinical documentation and identifies whether "
            "a medico-legal expert assessment is the right next step. "
            "Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "Medical-malpractice cases require a clinical assessment of the "
            "treatment received and a legal assessment of whether a deviation "
            "from the standard of care has caused harm. The Studio reviews the "
            "available clinical documentation, identifies whether an "
            "independent medico-legal expert is the right next step, and "
            "produces a preliminary indicative assessment. This page is "
            "informational; it does not constitute a clinical or legal opinion."
        ),
        when_it_applies=(
            _("You believe a medical or surgical treatment caused an avoidable harm, or the harm was not adequately explained to you."),
            _("You have at least partial clinical documentation (discharge letters, exam results, surgical reports)."),
            _("You want to understand whether commissioning an independent medico-legal expert assessment is justified."),
        ),
        what_studio_does=(
            _("Reviews the clinical documentation you have and identifies the relevant medical-legal framework."),
            _("Helps you understand whether commissioning an independent medico-legal expert is justified, and at what cost."),
            _("Produces a preliminary indicative assessment of the recoverable categories of damage."),
            _("Recommends next steps and the documents you should gather for a complete review."),
        ),
        primary_cta_label=_("Request a legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
    ),
    CaseTypeLanding(
        slug="death-of-relative",
        case_type_code=_CODE_DEATH,
        h1=_("Death of a relative"),
        meta_title=_("Death of a relative — preliminary legal assessment"),
        meta_description=_(
            "Preliminary legal assessment of damage claims following the death "
            "of a relative — loss of the parental / family relationship, "
            "patrimonial damage, mandatory insurance coverage. Indicative, not "
            "a guarantee of outcome."
        ),
        intro=_(
            "The death of a close relative may give rise to compensation for "
            "the loss of the parental or family relationship and for "
            "patrimonial damage suffered by the surviving family. The Studio "
            "reviews each case manually with the sensitivity it requires and "
            "produces a preliminary indicative assessment. The Studio does not "
            "publish any automatic figure before reading the documents."
        ),
        when_it_applies=(
            _("A close relative has died as a consequence of an accident, of a medical event, or of work circumstances."),
            _("You want to understand whether and how the loss can be assessed under the relevant legal framework."),
            _("You are dealing with the insurer of a third party and want a second opinion before any agreement."),
            _("You hold at least basic documentation about the cause of death and the family link."),
        ),
        what_studio_does=(
            _("Reads the documentation, identifies the applicable jurisdiction and the recoverable categories of damage."),
            _("Produces a preliminary indicative assessment based on validated indicative sources for the relevant family relationships."),
            _("Indicates next steps, missing documents and the alternatives available to the family."),
            _("Handles the matter with the discretion the case requires."),
        ),
        primary_cta_label=_("Request a legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
    ),
    CaseTypeLanding(
        slug="foreigners-in-italy",
        case_type_code=_CODE_GENERIC,
        h1=_("Foreign citizens injured in Italy"),
        meta_title=_("Foreign citizens injured in Italy — preliminary legal assessment"),
        meta_description=_(
            "Preliminary legal assessment for foreign citizens who suffered a "
            "road-accident, work-injury or medical injury during a stay or "
            "residence in Italy. Multilingual handling (IT / FR / EN / AR). "
            "Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "Foreign citizens injured during a stay or residence in Italy face "
            "a specific procedural picture: notification to the Italian "
            "insurer, language barriers, evidence collection across countries. "
            "The Studio handles the case multilingually (Italian, French, "
            "English, Arabic) and produces a preliminary indicative assessment "
            "after reading the documents."
        ),
        when_it_applies=(
            _("You are not an Italian resident but you suffered an accident or harm during a stay in Italy."),
            _("You need to communicate with an Italian insurer or with Italian medical structures."),
            _("Your medical records or police reports are in Italian and you want them reviewed in your own language."),
            _("You are unsure whether to pursue the case in Italy or in your country of residence."),
        ),
        what_studio_does=(
            _("Communicates in your own language and translates the procedural correspondence where needed."),
            _("Identifies the applicable jurisdiction, applicable law and competent court."),
            _("Produces a preliminary indicative assessment of recoverable damages under Italian indicative sources."),
            _("Coordinates with local counsel in your country of residence if cross-border execution is needed."),
        ),
        primary_cta_label=_("Request a multilingual legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
    ),
    CaseTypeLanding(
        slug="cross-border-cases",
        case_type_code=_CODE_INT_INHERITANCE,
        h1=_("Cross-border cases"),
        meta_title=_("Cross-border legal cases — preliminary legal assessment"),
        meta_description=_(
            "Preliminary legal assessment of cases with cross-border elements: "
            "international inheritance (Morocco, Tunisia), road accidents "
            "abroad, and disputes involving parties in different countries. "
            "Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "When a case involves parties or assets across multiple countries "
            "— a road accident abroad, an inheritance opened in another "
            "jurisdiction, a contract dispute under foreign law — the first "
            "step is identifying the applicable law and the competent court. "
            "The Studio reviews each case manually and produces a preliminary "
            "indicative assessment after that triage."
        ),
        when_it_applies=(
            _("An accident occurred abroad and you are pursuing damages from your country of residence."),
            _("An inheritance has been opened in another jurisdiction (e.g. Morocco, Tunisia) with assets or heirs in Europe."),
            _("Parties to your case are residents of different countries and you do not know which law applies."),
            _("Documents you need to use are in foreign languages and need to be reviewed by counsel familiar with both jurisdictions."),
        ),
        what_studio_does=(
            _("Identifies the applicable conflict-of-laws rules, the competent jurisdiction and any treaty framework."),
            _("Translates / interprets foreign documents and correspondence and coordinates with local counsel."),
            _("Produces a preliminary indicative assessment of the most likely jurisdictional outcome."),
            _("Recommends a structured next step — without any automatic engagement."),
        ),
        primary_cta_label=_("Request a cross-border legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
    ),
)


LANDINGS_BY_SLUG = {landing.slug: landing for landing in LANDINGS}


def get_landing(slug: str) -> CaseTypeLanding | None:
    """Resolve a slug to its `CaseTypeLanding`, or None if unknown."""
    return LANDINGS_BY_SLUG.get(slug)


def all_slugs() -> tuple[str, ...]:
    """Tuple of all published landing slugs (stable order)."""
    return tuple(landing.slug for landing in LANDINGS)
