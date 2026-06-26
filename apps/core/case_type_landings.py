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
  the Studio handles and what to bring for an indicative review"
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

from collections.abc import Sequence
from dataclasses import dataclass, field

from django.urls import reverse
from django.utils.translation import gettext_lazy as _


@dataclass(frozen=True)
class FAQItem:
    """One FAQ entry rendered on a case-type landing.

    Both strings are `gettext_lazy` so they resolve to the request
    locale at render time. See
    `docs/product/CASE_TYPE_FAQ_AUDIT_2026-05-12.md` for the
    deontological guardrails.
    """

    question: str
    answer: str


# Max FAQ entries per landing — keeps the section compact on mobile
# and forces the copy to stay focused. Enforced by the module-level
# invariant at the bottom of this file.
MAX_FAQ_ITEMS = 4


# Universal FAQ items reused across every landing. Keeping them as
# module-level constants guarantees the first FAQ ("is this a legal
# opinion?") and the mandate FAQ ("does sending the form create an
# engagement?") are literally identical across landings — tested.
_FAQ_LEGAL_OPINION = FAQItem(
    question=_("Questa simulazione è un parere legale?"),
    answer=_(
        "No. La simulazione è una valutazione indicativa basata su fonti "
        "legali validate per la giurisdizione applicabile. Non sostituisce "
        "un parere legale né una perizia medico-legale; la valutazione "
        "effettiva dipende dai documenti, dalla perizia e dalla legge "
        "applicabile al caso specifico."
    ),
)

_FAQ_MANDATE = FAQItem(
    question=_("Inviare il modulo crea un incarico professionale?"),
    answer=_(
        "No. L'invio del modulo richiede una verifica preliminare allo "
        "Studio e non costituisce un incarico professionale. L'eventuale "
        "conferimento dell'incarico avviene solo dopo un accordo scritto "
        "separato tra cliente e Studio."
    ),
)


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

    faq_items: Sequence[FAQItem] = field(default_factory=tuple)
    """
    F-product-6-case-type-faqs: prudent FAQ entries rendered as a
    `<details>/<summary>` accordion at the bottom of the landing.
    Capped at `MAX_FAQ_ITEMS` (4). See
    `docs/product/CASE_TYPE_FAQ_AUDIT_2026-05-12.md`.
    """

    official_basis: Sequence[str] = field(default_factory=tuple)
    """
    P10: official normative basis shown as public source chips, so every
    section reads as an "official guided path" with a visible legal source.
    These are language-neutral legal citations (law / decree identifiers),
    NOT translatable copy and NOT computed amounts — they name the official
    source, never invent a figure. Required on every landing (tested).
    """

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
        official_basis=(
            "D.P.R. 12/2025 — Tabella Unica Nazionale",
            "artt. 138–139 Cod. Assicurazioni (D.Lgs. 209/2005)",
        ),
        h1=_("Road accident — bodily injury"),
        meta_title=_("Road accident bodily injury — assisted legal pathway"),
        meta_description=_(
            "Assisted legal pathway for road-accident bodily injury claims, "
            "based on the Tabella Unica Nazionale 2025 in Italy and recognised "
            "indicative references in France and Belgium. Indicative, not a "
            "guarantee of outcome."
        ),
        intro=_(
            "If you were injured in a road accident as a driver, passenger, "
            "cyclist or pedestrian, the Studio reviews each case manually and "
            "produces an assisted legal pathway based on validated "
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
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("Devo già avere tutti i documenti per chiedere una valutazione?"),
                answer=_(
                    "No. Si può iniziare con i documenti disponibili — verbale "
                    "delle autorità o constat amiable, referti medici, "
                    "eventuali corrispondenze con l'assicurazione. Lo Studio "
                    "indica quali documenti mancano dopo la prima revisione."
                ),
            ),
            FAQItem(
                question=_("Ho già ricevuto un'offerta dall'assicurazione: posso chiedere una verifica?"),
                answer=_(
                    "Sì. Lo Studio può valutare l'offerta in via preliminare "
                    "confrontandola con le fonti indicative validate per la "
                    "giurisdizione applicabile. Si consiglia di non firmare "
                    "alcuna transazione prima della verifica."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
    CaseTypeLanding(
        slug="bodily-injury",
        case_type_code=_CODE_ROAD,
        official_basis=(
            "D.P.R. 12/2025 — Tabella Unica Nazionale",
            "artt. 138–139 Cod. Assicurazioni (D.Lgs. 209/2005)",
        ),
        h1=_("Bodily injury claims"),
        meta_title=_("Bodily injury — assisted legal pathway"),
        meta_description=_(
            "Assisted legal pathway for bodily injury claims (permanent "
            "disability, temporary disability, biological damage), based on "
            "the validated legal sources approved for the chosen jurisdiction. "
            "Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "Bodily injury — sometimes referred to as biological damage — "
            "covers temporary disability, permanent disability and the broader "
            "impact on your life from a documented injury. The Studio reviews "
            "each case manually using validated legal sources and produces an assisted legal pathway, not a binding evaluation."
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
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("Quali documenti aiutano la valutazione del danno biologico?"),
                answer=_(
                    "Il referto medico-legale che attesta la percentuale di "
                    "invalidità permanente, i certificati di durata della "
                    "inabilità temporanea (totale o parziale) e la "
                    "documentazione clinica del percorso terapeutico. La "
                    "valutazione effettiva dipende da queste fonti."
                ),
            ),
            FAQItem(
                question=_("Se il percorso medico-legale è ancora in corso, posso comunque chiedere una valutazione?"),
                answer=_(
                    "Sì, ma la valutazione resta preliminare e potrà cambiare "
                    "al consolidarsi del quadro medico-legale. Lo Studio "
                    "indica le ipotesi e i documenti ancora mancanti."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
    CaseTypeLanding(
        slug="insurance-offer-review",
        case_type_code=_CODE_GENERIC,
        official_basis=(
            "D.P.R. 12/2025 — Tabella Unica Nazionale",
            "artt. 138–139 Cod. Assicurazioni (D.Lgs. 209/2005)",
            "IVASS — vigilanza assicurativa",
        ),
        h1=_("Insurance offer review"),
        meta_title=_("Insurance offer review — assisted legal pathway"),
        meta_description=_(
            "Assisted legal review of insurance settlement offers in road-accident "
            "and bodily-injury cases. The Studio compares the offer against "
            "validated indicative sources and highlights what is missing. "
            "Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "You received an offer from an insurance company but you are not "
            "sure whether it reflects what your case is worth. The Studio "
            "reviews each offer manually, compares it against validated "
            "indicative sources and gives you an assisted legal pathway towards whether to accept, negotiate or refuse. No "
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
        primary_cta_label=_("Compare your offer now"),
        primary_cta_url_name="cases:wizard_insurance_offer",
        secondary_cta_label=_("Request a legal review of your offer"),
        secondary_cta_url_name="crm:contact",
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("Posso firmare l'offerta prima della verifica legale?"),
                answer=_(
                    "Si consiglia di non sottoscrivere alcuna transazione "
                    "prima di una verifica legale. Una volta firmata, la "
                    "maggior parte delle pretese ulteriori risulta preclusa: "
                    "la revisione preliminare aiuta a evitare rinunce non "
                    "informate."
                ),
            ),
            FAQItem(
                question=_("La revisione dell'offerta equivale ad accettarla?"),
                answer=_(
                    "No. La revisione è solo orientativa: lo Studio indica se "
                    "l'offerta è in linea con il range indicativo delle fonti "
                    "validate e suggerisce se accettare, negoziare o rifiutare. "
                    "La decisione finale resta sempre del cliente."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
    CaseTypeLanding(
        slug="work-injury",
        case_type_code=_CODE_WORK,
        official_basis=(
            "D.P.R. 1124/1965 — Testo Unico INAIL",
            "D.Lgs. 38/2000 (art. 13) — danno biologico INAIL",
            "D.M. 12/07/2000 — tabelle indennizzo INAIL",
        ),
        h1=_("Work injury"),
        meta_title=_("Work injury — assisted legal pathway"),
        meta_description=_(
            "Assisted legal pathway for work-injury claims and the "
            "interaction between mandatory insurance (e.g. INAIL in Italy) and "
            "additional civil liability. Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "Work injuries combine mandatory work-insurance coverage (e.g. INAIL "
            "in Italy) with potential civil liability of the employer or third "
            "parties. The Studio reviews each case manually to identify what is "
            "covered by mandatory insurance, what may be claimed as additional "
            "damages, and how to document the case correctly. An assisted legal pathway is provided after that review."
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
            _("Provides an assisted legal pathway of the additional damages potentially recoverable."),
            _("Indicates next steps and missing documents — without any automatic engagement."),
        ),
        primary_cta_label=_("Request a legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("Se l'assicurazione obbligatoria (es. INAIL) copre già l'infortunio, ha senso una valutazione?"),
                answer=_(
                    "Sì. La copertura obbligatoria e l'eventuale "
                    "responsabilità civile del datore di lavoro o di terzi "
                    "sono profili distinti: la valutazione indicativa aiuta "
                    "a individuare quanto potrebbe restare esigibile in via "
                    "civilistica, oltre alla copertura obbligatoria."
                ),
            ),
            FAQItem(
                question=_("Quali documenti aiutano la valutazione di un infortunio sul lavoro?"),
                answer=_(
                    "La denuncia di infortunio, gli eventuali verbali "
                    "ispettivi, la documentazione clinica e, quando "
                    "disponibile, la documentazione di sicurezza relativa "
                    "alla mansione (es. DVR, registri di formazione)."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
    CaseTypeLanding(
        slug="medical-malpractice",
        case_type_code=_CODE_MEDICAL,
        official_basis=(
            "L. 24/2017 (Gelli-Bianco)",
            "artt. 138–139 Cod. Assicurazioni (D.Lgs. 209/2005)",
        ),
        h1=_("Medical malpractice"),
        meta_title=_("Medical malpractice — assisted legal pathway"),
        meta_description=_(
            "Assisted legal pathway for medical-malpractice claims. The "
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
            "produces an assisted legal pathway. This page is "
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
            _("Produces an assisted legal pathway of the recoverable categories of damage."),
            _("Recommends next steps and the documents you should gather for a complete review."),
        ),
        primary_cta_label=_("Start indicative simulation"),
        primary_cta_url_name="cases:wizard_italy_medical",
        secondary_cta_label=_("Request a legal review instead"),
        secondary_cta_url_name="crm:contact",
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("Serve già una perizia medico-legale indipendente per chiedere la valutazione?"),
                answer=_(
                    "Non necessariamente in questa fase. Lo Studio aiuta a "
                    "capire se commissionare una perizia indipendente è "
                    "giustificato, e con quale ordine di costo, prima di "
                    "qualsiasi avvio formale."
                ),
            ),
            FAQItem(
                question=_("Una perizia indipendente è sempre obbligatoria?"),
                answer=_(
                    "Non sempre. Dipende dalla documentazione clinica "
                    "disponibile e dalla complessità del caso. Lo Studio "
                    "valuta caso per caso prima di consigliare un esborso "
                    "ulteriore."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
    CaseTypeLanding(
        slug="death-of-relative",
        case_type_code=_CODE_DEATH,
        official_basis=(
            "artt. 2043, 2059 Cod. Civile",
            "art. 1223 Cod. Civile — danno patrimoniale",
        ),
        h1=_("Death of a relative"),
        meta_title=_("Death of a relative — assisted legal pathway"),
        meta_description=_(
            "Assisted legal pathway for damage claims following the death "
            "of a relative — loss of the parental / family relationship, "
            "patrimonial damage, mandatory insurance coverage. Indicative, not "
            "a guarantee of outcome."
        ),
        intro=_(
            "The death of a close relative may give rise to compensation for "
            "the loss of the parental or family relationship and for "
            "patrimonial damage suffered by the surviving family. The Studio "
            "reviews each case manually with the sensitivity it requires and "
            "produces an assisted legal pathway. The Studio does not "
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
            _("Produces an indicative assessment based on validated indicative sources for the relevant family relationships."),
            _("Indicates next steps, missing documents and the alternatives available to the family."),
            _("Handles the matter with the discretion the case requires."),
        ),
        primary_cta_label=_("Request a legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("Quali familiari possono chiedere la valutazione?"),
                answer=_(
                    "La valutazione orientativa è disponibile per i "
                    "familiari direttamente coinvolti dalla perdita. Lo "
                    "Studio identifica caso per caso quali categorie di "
                    "danno risultano applicabili in base al rapporto "
                    "familiare documentato."
                ),
            ),
            FAQItem(
                question=_("Posso chiedere una verifica se è già in corso una trattativa con l'assicurazione?"),
                answer=_(
                    "Sì, è anzi consigliato. Una seconda opinione "
                    "orientativa prima di accordi o sottoscrizioni aiuta a "
                    "evitare rinunce non informate che potrebbero "
                    "precludere ulteriori pretese."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
    CaseTypeLanding(
        slug="foreigners-in-italy",
        case_type_code=_CODE_GENERIC,
        official_basis=(
            "D.P.R. 12/2025 — Tabella Unica Nazionale",
            "Reg. (CE) 864/2007 — Roma II (legge applicabile)",
        ),
        h1=_("Foreign citizens injured in Italy"),
        meta_title=_("Foreign citizens injured in Italy — assisted legal pathway"),
        meta_description=_(
            "Assisted legal pathway for foreign citizens who suffered a "
            "road-accident, work-injury or medical injury during a stay or "
            "residence in Italy. Multilingual handling (IT / FR / EN / AR). "
            "Indicative, not a guarantee of outcome."
        ),
        intro=_(
            "Foreign citizens injured during a stay or residence in Italy face "
            "a specific procedural picture: notification to the Italian "
            "insurer, language barriers, evidence collection across countries. "
            "The Studio handles the case multilingually (Italian, French, "
            "English, Arabic) and produces an indicative assessment "
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
            _("Produces an indicative assessment of recoverable damages under Italian indicative sources."),
            _("Coordinates with local counsel in your country of residence if cross-border execution is needed."),
        ),
        primary_cta_label=_("Request a multilingual legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("In quale lingua posso comunicare con lo Studio?"),
                answer=_(
                    "Lo Studio gestisce italiano, francese, inglese e arabo. "
                    "La documentazione clinica e procedurale italiana viene "
                    "letta e tradotta nelle parti rilevanti per il caso."
                ),
            ),
            FAQItem(
                question=_("Devo necessariamente avviare la causa in Italia?"),
                answer=_(
                    "Non sempre. La giurisdizione competente dipende dai "
                    "fatti, dalla legge applicabile e dai trattati: la "
                    "valutazione indicativa include questo passo di triage "
                    "prima di qualsiasi avvio formale."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
    CaseTypeLanding(
        slug="cross-border-cases",
        case_type_code=_CODE_INT_INHERITANCE,
        official_basis=(
            "Reg. (CE) 864/2007 — Roma II (obbligazioni extracontrattuali)",
            "Reg. (UE) 650/2012 — successioni internazionali",
        ),
        h1=_("Cross-border cases"),
        meta_title=_("Cross-border legal cases — assisted legal pathway"),
        meta_description=_(
            "Assisted legal pathway for cases with cross-border elements: "
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
            _("Produces an indicative assessment of the most likely jurisdictional outcome."),
            _("Recommends a structured next step — without any automatic engagement."),
        ),
        primary_cta_label=_("Request a cross-border legal review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Open the simulation wizard"),
        secondary_cta_url_name="cases:wizard_start",
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("Come si stabilisce quale legge si applica al caso?"),
                answer=_(
                    "Attraverso le regole di conflitto e i trattati "
                    "internazionali rilevanti per il caso. Lo Studio "
                    "individua il quadro applicabile prima di formulare una "
                    "stima orientativa dell'esito."
                ),
            ),
            FAQItem(
                question=_("Lo Studio collabora con avvocati locali nei paesi coinvolti?"),
                answer=_(
                    "Sì. Quando l'esecuzione transfrontaliera richiede "
                    "l'intervento di un legale locale, lo Studio si "
                    "coordina con corrispondenti nei paesi rilevanti per "
                    "il caso."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
    CaseTypeLanding(
        slug="product-liability",
        case_type_code=_CODE_GENERIC,
        official_basis=(
            "artt. 114–127 Cod. del Consumo (D.Lgs. 206/2005)",
            "Direttiva 85/374/CEE — prodotti difettosi",
        ),
        h1=_("Defective product liability"),
        meta_title=_("Defective product — official guided pathway"),
        meta_description=_(
            "Official guided pathway for harm caused by a defective product, "
            "under the Italian Consumer Code (artt. 114–127, D.Lgs. 206/2005) "
            "and Directive 85/374/EEC. Document-led analysis, not an automatic "
            "figure."
        ),
        intro=_(
            "When a defective product causes injury or damage, liability is "
            "governed by the Italian Consumer Code (artt. 114–127) and "
            "Directive 85/374/EEC. The Studio reviews the documentation, frames "
            "the case against these official sources and indicates the next "
            "steps. No automatic figure is published before the file is read."
        ),
        when_it_applies=(
            _("A product caused injury or property damage that you believe is due to a defect, not to misuse."),
            _("You can identify the product, the manufacturer or importer, and roughly when the harm occurred."),
            _("You hold at least basic documentation: purchase proof, photos, medical or technical reports."),
        ),
        what_studio_does=(
            _("Frames the case under artt. 114–127 of the Consumer Code and Directive 85/374/EEC, identifying the liable party."),
            _("Reviews the documentation and indicates what is missing to establish the defect and the causal link."),
            _("Explains the recoverable categories of damage and the next steps — without any automatic engagement."),
        ),
        primary_cta_label=_("Request a guided review"),
        primary_cta_url_name="crm:contact",
        secondary_cta_label=_("Read the methodology"),
        secondary_cta_url_name="core:methodology",
        faq_items=(
            _FAQ_LEGAL_OPINION,
            FAQItem(
                question=_("Devo già provare il difetto del prodotto per chiedere una valutazione?"),
                answer=_(
                    "In questa fase no. Lo Studio aiuta a capire quali "
                    "elementi servono per dimostrare il difetto e il nesso "
                    "causale, e quali documenti raccogliere, prima di "
                    "qualsiasi avvio formale."
                ),
            ),
            _FAQ_MANDATE,
        ),
    ),
)


# ---------------------------------------------------------------------------
# F-product-6-case-type-faqs: defensive module-level invariant.
# ---------------------------------------------------------------------------
#
# Catches future drift if a landing accidentally grows beyond
# `MAX_FAQ_ITEMS` (4) entries — the section would push the disclaimer
# below the mobile fold. Raises at import, so any test run catches it
# immediately.
for _landing in LANDINGS:
    assert len(_landing.faq_items) <= MAX_FAQ_ITEMS, (
        f"Landing {_landing.slug!r} has {len(_landing.faq_items)} FAQ items; "
        f"max is {MAX_FAQ_ITEMS} (see CASE_TYPE_FAQ_AUDIT_2026-05-12.md)."
    )


LANDINGS_BY_SLUG = {landing.slug: landing for landing in LANDINGS}


def get_landing(slug: str) -> CaseTypeLanding | None:
    """Resolve a slug to its `CaseTypeLanding`, or None if unknown."""
    return LANDINGS_BY_SLUG.get(slug)


def all_slugs() -> tuple[str, ...]:
    """Tuple of all published landing slugs (stable order)."""
    return tuple(landing.slug for landing in LANDINGS)


# ---------------------------------------------------------------------------
# F-product-5-result-page-next-pages: case_type → recommended landings
# ---------------------------------------------------------------------------
#
# Mapping from `CaseType` enum value to an ordered list of landing
# slugs to surface on `/wizard/result/<uuid>/`. The result-page
# view (`cases.views.wizard_result`) reads this and renders a
# "Useful pages for your case" section. Capped to 3 recommendations
# at render time to avoid distracting from the primary CTA.
#
# Codes that don't appear in the mapping receive an empty list →
# the section is silently omitted on the result page.
#
# Profile-style landings (`foreigners-in-italy`, `cross-border-cases`,
# `insurance-offer-review`) appear across several case-types because
# they describe a user *situation*, not a case-type code.
_RECOMMENDATIONS_BY_CASE_TYPE: dict[str, tuple[str, ...]] = {
    _CODE_ROAD: ("bodily-injury", "insurance-offer-review", "cross-border-cases"),
    _CODE_MEDICAL: ("medical-malpractice", "insurance-offer-review"),
    _CODE_WORK: ("work-injury", "insurance-offer-review"),
    _CODE_DEATH: ("death-of-relative", "cross-border-cases"),
    "parental_loss": ("death-of-relative",),
    _CODE_INT_INHERITANCE: ("cross-border-cases", "foreigners-in-italy"),
    "inheritance_basic": ("cross-border-cases",),
    _CODE_GENERIC: ("insurance-offer-review", "cross-border-cases"),
    "patrimonial_damage": ("insurance-offer-review", "cross-border-cases"),
}

# Maximum landings rendered on the result page.
RESULT_PAGE_RECOMMENDATION_LIMIT = 3


def get_recommended_landings(case_type: str) -> tuple[CaseTypeLanding, ...]:
    """Return the ordered tuple of recommended landings for a case_type.

    Empty tuple when the case_type is unknown or unmapped — the
    result-page template treats an empty list as "do not render the
    recommendations section".

    Capped at `RESULT_PAGE_RECOMMENDATION_LIMIT` (3) entries. Skips
    any slug that does not resolve to a real landing — defensive
    against future drift between the mapping and the LANDINGS tuple.
    """
    if not case_type:
        return ()
    slugs = _RECOMMENDATIONS_BY_CASE_TYPE.get(case_type, ())
    out: list[CaseTypeLanding] = []
    for slug in slugs[:RESULT_PAGE_RECOMMENDATION_LIMIT]:
        landing = LANDINGS_BY_SLUG.get(slug)
        if landing is not None:
            out.append(landing)
    return tuple(out)
