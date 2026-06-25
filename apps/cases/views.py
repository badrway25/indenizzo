"""
Public views — wizard pubblico (F-wizard).

Tre endpoint:

  GET  /wizard/                        landing — scelta percorso wizard
  GET  /wizard/it/road-accident/       form Italia incidente stradale
  POST /wizard/it/road-accident/       crea Simulation via service
  GET  /wizard/result/<uuid>/          pagina risultato per la Simulation

Regole architetturali:
- la view *non* esegue calcoli: delega a `cases.services.run_simulation`
  (e dunque al motore F4). Questa view è solo glue + UX.
- consenso `simulation_processing` raccolto QUI prima di creare la
  Simulation. Il record viene passato a `run_simulation` via il
  parametro `consent_record`.
- honeypot `website`: se compilato il form passa la validazione, ma la
  view non crea Simulation né ConsentRecord. Redirect alla landing
  wizard (innocuo, nessuna thank-you per non rivelare la trappola).
- nessuna view crea `Lead` direttamente: il funnel resta wizard →
  result → CTA `/contact/?sim=<public_id>`.
"""

from __future__ import annotations

import logging
import uuid

from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.views.decorators.http import require_GET, require_http_methods

from apps.calculators.enums import CaseType
from apps.calculators.registry import list_available_calculators
from apps.compliance.models import ConsentPurpose
from apps.compliance.services import record_double_consent
from apps.core.public_status import get_country_public_status
from apps.core.rate_limit import public_post_rate_limit

from .forms import (
    BelgiumRoadAccidentWizardForm,
    FranceRoadAccidentWizardForm,
    InternationalInheritanceWizardForm,
    ItalyRoadAccidentWizardForm,
)
from .models import Simulation
from .services import run_simulation

logger = logging.getLogger(__name__)

ITALY_ROAD_ACCIDENT_JURISDICTION = "IT-NATIONAL"
ITALY_ROAD_ACCIDENT_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
FRANCE_ROAD_ACCIDENT_JURISDICTION = "FR-NATIONAL"
FRANCE_ROAD_ACCIDENT_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
BELGIUM_ROAD_ACCIDENT_JURISDICTION = "BE-NATIONAL"
BELGIUM_ROAD_ACCIDENT_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
MOROCCO_INHERITANCE_JURISDICTION = "MA-NATIONAL"
TUNISIA_INHERITANCE_JURISDICTION = "TN-NATIONAL"
INTERNATIONAL_INHERITANCE_CASE_TYPE = CaseType.INTERNATIONAL_INHERITANCE.value
SIMULATION_CONSENT_PURPOSE_CODE = "simulation_processing"


# ---------------------------------------------------------------------------
# /wizard/  — landing
# ---------------------------------------------------------------------------


@require_GET
def wizard_start(request):
    """Landing del wizard: elenco moduli pronti / in preparazione."""
    registered = set(list_available_calculators())
    is_italy_road_ready = (
        ITALY_ROAD_ACCIDENT_JURISDICTION,
        ITALY_ROAD_ACCIDENT_CASE_TYPE,
    ) in registered
    is_france_road_scaffolded = (
        FRANCE_ROAD_ACCIDENT_JURISDICTION,
        FRANCE_ROAD_ACCIDENT_CASE_TYPE,
    ) in registered
    is_belgium_road_scaffolded = (
        BELGIUM_ROAD_ACCIDENT_JURISDICTION,
        BELGIUM_ROAD_ACCIDENT_CASE_TYPE,
    ) in registered
    is_morocco_inheritance_scaffolded = (
        MOROCCO_INHERITANCE_JURISDICTION,
        INTERNATIONAL_INHERITANCE_CASE_TYPE,
    ) in registered
    is_tunisia_inheritance_scaffolded = (
        TUNISIA_INHERITANCE_JURISDICTION,
        INTERNATIONAL_INHERITANCE_CASE_TYPE,
    ) in registered

    options = [
        {
            "country_code": "IT",
            "country_name": "Italia",
            "case_label": CaseType.ROAD_ACCIDENT_BODILY_INJURY.label,
            "url": reverse("cases:wizard_italy_road_accident"),
            "available": is_italy_road_ready,
            "description_key": "italy_road_accident",
        },
        {
            "country_code": "FR",
            "country_name": "France",
            "case_label": CaseType.ROAD_ACCIDENT_BODILY_INJURY.label,
            "url": reverse("cases:wizard_france_road_accident"),
            # `available` resta False perché il calculator restituisce
            # `unavailable_requires_legal_validation`. La pagina è
            # raggiungibile (scaffold) ma non produce stime.
            "available": False,
            "scaffold_only": is_france_road_scaffolded,
            "description_key": "france_road_accident",
        },
        {
            "country_code": "BE",
            "country_name": "Belgique",
            "case_label": CaseType.ROAD_ACCIDENT_BODILY_INJURY.label,
            "url": reverse("cases:wizard_belgium_road_accident"),
            "available": False,
            "scaffold_only": is_belgium_road_scaffolded,
            "description_key": "belgium_road_accident",
        },
        {
            "country_code": "MA",
            "country_name": "Maroc",
            "case_label": CaseType.INTERNATIONAL_INHERITANCE.label,
            "url": reverse("cases:wizard_morocco_inheritance"),
            "available": False,
            "scaffold_only": is_morocco_inheritance_scaffolded,
            "description_key": "morocco_international_inheritance",
        },
        {
            "country_code": "TN",
            "country_name": "Tunisie",
            "case_label": CaseType.INTERNATIONAL_INHERITANCE.label,
            "url": reverse("cases:wizard_tunisia_inheritance"),
            "available": False,
            "scaffold_only": is_tunisia_inheritance_scaffolded,
            "description_key": "tunisia_international_inheritance",
        },
    ]
    upcoming = [
        {"country_code": "IT", "case_label": CaseType.INHERITANCE_BASIC.label},
    ]
    # Inject the centralised public status into every option. Templates
    # render the badge / description / CTA from here so the wording is
    # never duplicated.
    _option_case_type = {
        "IT": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        "FR": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        "BE": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        "MA": CaseType.INTERNATIONAL_INHERITANCE.value,
        "TN": CaseType.INTERNATIONAL_INHERITANCE.value,
    }
    for option in options:
        option["public_status"] = get_country_public_status(
            option["country_code"],
            _option_case_type.get(option["country_code"]),
        )

    from apps.core.views import _pexels_hero

    return render(
        request,
        "public/wizard_start.html",
        {
            "options": options,
            "upcoming": upcoming,
            "pexels_image": _pexels_hero(request, "wizard_start_hero"),
        },
    )


# ---------------------------------------------------------------------------
# /wizard/it/road-accident/  — Italia, incidente stradale
# ---------------------------------------------------------------------------


@public_post_rate_limit
@require_http_methods(["GET", "POST"])
def wizard_italy_road_accident(request):
    """Step unico MVP: input → consenso → run_simulation → redirect result."""
    if request.method == "POST":
        form = ItalyRoadAccidentWizardForm(request.POST)
        if form.is_valid():
            if form.is_likely_bot:
                logger.info("cases.wizard.dropped reason=honeypot path=%s", request.path)
                return redirect(reverse("cases:wizard_start"))

            simulation = _run_italy_road_accident(request, form)
            return redirect(
                reverse(
                    "cases:wizard_result",
                    kwargs={"public_id": str(simulation.public_id)},
                )
            )
    else:
        form = ItalyRoadAccidentWizardForm()

    from apps.core.views import _pexels_hero

    return render(
        request,
        "public/wizard_italy_road_accident.html",
        {
            "form": form,
            "jurisdiction_code": ITALY_ROAD_ACCIDENT_JURISDICTION,
            "case_type": ITALY_ROAD_ACCIDENT_CASE_TYPE,
            "pexels_image": _pexels_hero(
                request, "wizard_italy_road_accident_hero", country_code="IT"
            ),
        },
    )


# ---------------------------------------------------------------------------
# /wizard/result/<uuid>/  — pagina risultato
# ---------------------------------------------------------------------------


@require_GET
def wizard_result(request, public_id: uuid.UUID):
    simulation = get_object_or_404(
        Simulation.objects.select_related("jurisdiction", "country"),
        public_id=public_id,
    )

    sources = simulation.sources_snapshot or []
    output = simulation.output_data or {}
    # Keep the raw arrays accessible for audit / debug only — never
    # surface them on the public result template. The localised
    # ``PublicResultMessage`` carries the user-facing copy.
    warnings = output.get("warnings") or []
    missing_documents = output.get("missing_documents") or []
    assumptions = output.get("assumptions") or []
    legal_disclaimer = output.get("legal_disclaimer") or ""

    # The engine emits public-safe warnings (e.g. "min/max coincide",
    # "<field> not aggregated", "fields needed are missing") sourced
    # from the diagnostics layer. We render them when:
    # - the estimate is produced (calculated path), or
    # - the engine reached the input-validation gate (insufficient
    #   input path) — those warnings are public-safe by design.
    # On the unavailable path we suppress them: the curated
    # PublicResultMessage carries every user-facing copy and the
    # engine-emitted warning may still be the un-migrated English
    # string from ``base.py``.
    _PUBLIC_WARNING_STATUSES = {"calculated", "insufficient_input"}
    if simulation.status in _PUBLIC_WARNING_STATUSES and warnings:
        public_warnings = list(warnings)
    else:
        public_warnings = []

    # Costruzione URL CTA verso il lead form già in F6.
    contact_url = reverse("crm:contact") + f"?sim={simulation.public_id}"

    # Difesa in profondità: gli importi si mostrano SOLO quando lo status è
    # `calculated`, oltre a essere non-null. Oggi gli importi si persistono
    # solo nel ramo CALCULATED, quindi il guard non cambia il comportamento
    # corrente; protegge però contro una futura regressione in cui una
    # Simulation non-`calculated` portasse comunque un `estimated_*`
    # valorizzato (vedi audit invariante "no calcolo falso").
    has_estimate = simulation.status == "calculated" and any(
        simulation.output_data.get(k) is not None
        for k in ("estimated_min", "estimated_mid", "estimated_max")
    )

    # Label pubblica dello status: il template mostra questa, mentre il
    # `simulation.status` raw resta visibile come "internal status code"
    # per audit/trasparenza.
    from apps.calculators.status_labels import get_public_status_label

    locale = (translation.get_language() or simulation.locale or "it").split("-", 1)[0]
    status_public_label = get_public_status_label(simulation.status, language=locale)

    # H2-2 transparency: localise the engine's missing-document diagnostic
    # codes for the public result page. `diagnostic_message` returns a
    # localised, human-readable sentence per code (it/fr/ar); unknown codes
    # fall back to the code itself. Empty on the calculated happy path — the
    # template then renders an explicit "no missing elements" note (mirrors
    # the PDF report's "no missing documents" section).
    from apps.calculators.diagnostics import diagnostic_message

    public_missing_documents = [
        diagnostic_message(code, language=locale) for code in missing_documents
    ]

    # Wire the centralised public status: the unavailable card on the
    # result page renders its CTA / disclaimer from this object so the
    # wording stays in sync with the rest of the site.
    case_type_value = getattr(simulation, "case_type", None) or ""
    country_code = ""
    if simulation.country_id:
        country_code = simulation.country.code
    elif simulation.jurisdiction_id:
        country_code = simulation.jurisdiction.code.split("-", 1)[0]
    public_status = get_country_public_status(country_code, case_type_value)

    # Build the public-facing copy block for the no-estimate path. The
    # helper never inspects the engine's diagnostics; it picks a
    # curated, pre-translated message from the country/case-type
    # mapping.
    from apps.cases.public_result_messages import build_public_result_message

    public_message = build_public_result_message(
        status=simulation.status,
        country_code=country_code,
        case_type=case_type_value,
    )

    # F-product-5-result-page-next-pages: resolve a small set of
    # case-type landings to surface on the result page as soft
    # "Useful pages for your case" links. Data-driven from
    # `apps.core.case_type_landings._RECOMMENDATIONS_BY_CASE_TYPE`;
    # empty tuple when the simulation's case_type is unmapped, which
    # tells the template to silently omit the section.
    from apps.core.case_type_landings import get_recommended_landings

    recommended_landings = get_recommended_landings(case_type_value)

    # H1-8: compact, public-safe provenance summary. Only display-safe fields
    # (source version label, abbreviated content hash, engine version, calc
    # date) — never the raw JSON. Present only on the calculated path and only
    # when a provenance snapshot exists (historical simulations omit it).
    provenance = simulation.calculation_provenance or {}
    provenance_summary = None
    if has_estimate and provenance:
        prov_dataset = provenance.get("dataset") or {}
        content_hash = prov_dataset.get("source_content_hash") or ""
        provenance_summary = {
            "source_version_label": prov_dataset.get("source_version_label") or "",
            "source_hash_short": content_hash[:12] if content_hash else "",
            "engine_version": provenance.get("engine_version") or "",
            "calculated_date": (provenance.get("calculated_at") or "")[:10],
        }

    return render(
        request,
        "public/wizard_result.html",
        {
            "simulation": simulation,
            "sources": sources,
            "assumptions": assumptions,
            "legal_disclaimer": legal_disclaimer,
            "contact_url": contact_url,
            "has_estimate": has_estimate,
            "public_warnings": public_warnings,
            "public_missing_documents": public_missing_documents,
            "status_public_label": status_public_label,
            "public_status": public_status,
            "public_message": public_message,
            "recommended_landings": recommended_landings,
            "provenance_summary": provenance_summary,
        },
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _run_italy_road_accident(request, form: ItalyRoadAccidentWizardForm) -> Simulation:
    """
    Registra il doppio consenso GDPR art. 6 + art. 9 e chiama il service.

    F-p0-leg-3-consent: il submit del wizard richiede entrambi i
    consensi (validati dal form). Qui creiamo due ConsentRecord
    (`simulation_processing` + `special_categories_processing`) e
    salviamo i campi denormalizzati sulla `Simulation`.
    """
    # P8: route by permanent-disability percentage. Micropermanenti (1–9%) use the
    # official art. 139 engine; 10%+ stay on the TUN art. 138 engine — so the TUN
    # canary (35/10/0) is untouched. Only Italy routes; FR/BE stay fail-closed.
    pct = form.cleaned_data.get("permanent_disability_percentage")
    case_type = ITALY_ROAD_ACCIDENT_CASE_TYPE
    try:
        if pct is not None and 1 <= int(pct) <= 9:
            case_type = CaseType.ROAD_ACCIDENT_MICROLESIONS.value
    except (TypeError, ValueError):
        pass
    return _run_road_accident_simulation(
        request=request,
        form=form,
        jurisdiction_code=ITALY_ROAD_ACCIDENT_JURISDICTION,
        case_type=case_type,
        trigger="wizard_italy_road_accident",
        privacy_purpose_code=SIMULATION_CONSENT_PURPOSE_CODE,
        privacy_purpose_label="Italy road-accident simulation",
        default_locale="it",
    )


def _run_road_accident_simulation(
    *,
    request,
    form,
    jurisdiction_code: str,
    case_type: str,
    trigger: str,
    privacy_purpose_code: str,
    privacy_purpose_label: str,
    default_locale: str,
) -> Simulation:
    """Helper comune ai 3 wizard road-accident (IT, FR, BE)."""
    user = request.user if request.user.is_authenticated else None
    privacy_record, _special_record = record_double_consent(
        request=request,
        user=user,
        privacy_purpose_code=privacy_purpose_code,
        privacy_purpose_label=privacy_purpose_label,
        privacy_version=settings.PRIVACY_NOTICE_VERSION,
        special_categories_version=settings.SPECIAL_CATEGORIES_NOTICE_VERSION,
        metadata={"trigger": trigger},
    )
    locale = (translation.get_language() or default_locale).split("-", 1)[0].lower()
    return run_simulation(
        jurisdiction_code=jurisdiction_code,
        case_type=case_type,
        input_data=form.to_input_data(),
        request=request,
        user=user,
        consent_record=privacy_record,
        locale=locale,
        privacy_consent_given=True,
        privacy_consent_version=settings.PRIVACY_NOTICE_VERSION,
        special_categories_consent_given=True,
        special_categories_consent_version=settings.SPECIAL_CATEGORIES_NOTICE_VERSION,
    )


# ---------------------------------------------------------------------------
# /wizard/fr/road-accident/  — France, accident de la circulation (scaffold)
# ---------------------------------------------------------------------------


@public_post_rate_limit
@require_http_methods(["GET", "POST"])
def wizard_france_road_accident(request):
    """
    Step unico scaffold MVP Francia: input → consenso → run_simulation
    → redirect result. Il calculator FR è un placeholder: anche con un
    submit valido, la `Simulation` risultante avrà
    ``status=unavailable_requires_legal_validation`` finché lo Studio
    non avrà promosso a ``approved`` fonte/dataset/formula. La pagina
    risultato gestisce già lo status `unavailable` come per l'Italia
    pre-attivazione.
    """
    if request.method == "POST":
        form = FranceRoadAccidentWizardForm(request.POST)
        if form.is_valid():
            if form.is_likely_bot:
                logger.info("cases.wizard.dropped reason=honeypot path=%s", request.path)
                return redirect(reverse("cases:wizard_start"))

            simulation = _run_france_road_accident(request, form)
            return redirect(
                reverse(
                    "cases:wizard_result",
                    kwargs={"public_id": str(simulation.public_id)},
                )
            )
    else:
        form = FranceRoadAccidentWizardForm()

    from apps.core.views import _pexels_hero

    return render(
        request,
        "public/wizard_france_road_accident.html",
        {
            "form": form,
            "jurisdiction_code": FRANCE_ROAD_ACCIDENT_JURISDICTION,
            "case_type": FRANCE_ROAD_ACCIDENT_CASE_TYPE,
            "public_status": get_country_public_status("FR", FRANCE_ROAD_ACCIDENT_CASE_TYPE),
            "pexels_image": _pexels_hero(
                request, "wizard_france_road_accident_hero", country_code="FR"
            ),
        },
    )


def _run_france_road_accident(request, form: FranceRoadAccidentWizardForm) -> Simulation:
    """Stesso pattern di `_run_italy_road_accident` ma su giurisdizione FR."""
    return _run_road_accident_simulation(
        request=request,
        form=form,
        jurisdiction_code=FRANCE_ROAD_ACCIDENT_JURISDICTION,
        case_type=FRANCE_ROAD_ACCIDENT_CASE_TYPE,
        trigger="wizard_france_road_accident",
        privacy_purpose_code=SIMULATION_CONSENT_PURPOSE_CODE,
        privacy_purpose_label="France road-accident simulation",
        default_locale="fr",
    )


# ---------------------------------------------------------------------------
# /wizard/be/road-accident/  — Belgium, accident de la circulation (scaffold)
# ---------------------------------------------------------------------------


@public_post_rate_limit
@require_http_methods(["GET", "POST"])
def wizard_belgium_road_accident(request):
    """Step unico scaffold MVP Belgio. Stesso pattern di Francia.

    Anche con submit valido, la `Simulation` risultante avrà
    ``status=unavailable_requires_legal_validation`` finché lo Studio
    non promuove a ``approved`` fonte/dataset/formula.
    """
    if request.method == "POST":
        form = BelgiumRoadAccidentWizardForm(request.POST)
        if form.is_valid():
            if form.is_likely_bot:
                logger.info("cases.wizard.dropped reason=honeypot path=%s", request.path)
                return redirect(reverse("cases:wizard_start"))

            simulation = _run_belgium_road_accident(request, form)
            return redirect(
                reverse(
                    "cases:wizard_result",
                    kwargs={"public_id": str(simulation.public_id)},
                )
            )
    else:
        form = BelgiumRoadAccidentWizardForm()

    from apps.core.views import _pexels_hero

    return render(
        request,
        "public/wizard_belgium_road_accident.html",
        {
            "form": form,
            "jurisdiction_code": BELGIUM_ROAD_ACCIDENT_JURISDICTION,
            "case_type": BELGIUM_ROAD_ACCIDENT_CASE_TYPE,
            "public_status": get_country_public_status("BE", BELGIUM_ROAD_ACCIDENT_CASE_TYPE),
            "pexels_image": _pexels_hero(
                request, "wizard_belgium_road_accident_hero", country_code="BE"
            ),
        },
    )


def _run_belgium_road_accident(request, form: BelgiumRoadAccidentWizardForm) -> Simulation:
    """Stesso pattern di `_run_france_road_accident` ma su giurisdizione BE."""
    return _run_road_accident_simulation(
        request=request,
        form=form,
        jurisdiction_code=BELGIUM_ROAD_ACCIDENT_JURISDICTION,
        case_type=BELGIUM_ROAD_ACCIDENT_CASE_TYPE,
        trigger="wizard_belgium_road_accident",
        privacy_purpose_code=SIMULATION_CONSENT_PURPOSE_CODE,
        privacy_purpose_label="Belgium road-accident simulation",
        default_locale="fr",
    )


# ---------------------------------------------------------------------------
# /wizard/{ma,tn}/inheritance/  — successioni internazionali (scaffold)
# ---------------------------------------------------------------------------


def _wizard_inheritance_view(
    request,
    *,
    jurisdiction_code: str,
    template_name: str,
    trigger: str,
    default_locale: str,
    pexels_purpose: str | None = None,
    pexels_country: str | None = None,
):
    """Vista comune ai wizard inheritance MA/TN.

    Anche con submit valido la `Simulation` resta
    ``unavailable_requires_legal_validation``: il calculator placeholder
    non produce quote ereditarie. Lo scaffold serve solo per il funnel.
    """
    if request.method == "POST":
        form = InternationalInheritanceWizardForm(request.POST)
        if form.is_valid():
            if form.is_likely_bot:
                logger.info("cases.wizard.dropped reason=honeypot path=%s", request.path)
                return redirect(reverse("cases:wizard_start"))

            user = request.user if request.user.is_authenticated else None
            privacy_record, _special_record = record_double_consent(
                request=request,
                user=user,
                privacy_purpose_code=SIMULATION_CONSENT_PURPOSE_CODE,
                privacy_purpose_label="International inheritance simulation",
                privacy_version=settings.PRIVACY_NOTICE_VERSION,
                special_categories_version=settings.SPECIAL_CATEGORIES_NOTICE_VERSION,
                metadata={"trigger": trigger},
            )
            locale = (translation.get_language() or default_locale).split("-", 1)[0].lower()
            simulation = run_simulation(
                jurisdiction_code=jurisdiction_code,
                case_type=INTERNATIONAL_INHERITANCE_CASE_TYPE,
                input_data=form.to_input_data(),
                request=request,
                user=user,
                consent_record=privacy_record,
                locale=locale,
                privacy_consent_given=True,
                privacy_consent_version=settings.PRIVACY_NOTICE_VERSION,
                special_categories_consent_given=True,
                special_categories_consent_version=settings.SPECIAL_CATEGORIES_NOTICE_VERSION,
            )
            return redirect(
                reverse(
                    "cases:wizard_result",
                    kwargs={"public_id": str(simulation.public_id)},
                )
            )
    else:
        form = InternationalInheritanceWizardForm()

    from apps.core.views import _pexels_hero

    # ``MA-NATIONAL`` / ``TN-NATIONAL`` → ``MA`` / ``TN`` for the helper.
    country_code = jurisdiction_code.split("-", 1)[0]
    return render(
        request,
        template_name,
        {
            "form": form,
            "jurisdiction_code": jurisdiction_code,
            "case_type": INTERNATIONAL_INHERITANCE_CASE_TYPE,
            "public_status": get_country_public_status(
                country_code, INTERNATIONAL_INHERITANCE_CASE_TYPE
            ),
            "pexels_image": (
                _pexels_hero(request, pexels_purpose, country_code=pexels_country)
                if pexels_purpose
                else None
            ),
        },
    )


@public_post_rate_limit
@require_http_methods(["GET", "POST"])
def wizard_morocco_inheritance(request):
    return _wizard_inheritance_view(
        request,
        jurisdiction_code=MOROCCO_INHERITANCE_JURISDICTION,
        template_name="public/wizard_morocco_inheritance.html",
        trigger="wizard_morocco_inheritance",
        default_locale="fr",
        pexels_purpose="wizard_morocco_inheritance_hero",
        pexels_country="MA",
    )


@public_post_rate_limit
@require_http_methods(["GET", "POST"])
def wizard_tunisia_inheritance(request):
    return _wizard_inheritance_view(
        request,
        jurisdiction_code=TUNISIA_INHERITANCE_JURISDICTION,
        template_name="public/wizard_tunisia_inheritance.html",
        trigger="wizard_tunisia_inheritance",
        default_locale="fr",
        pexels_purpose="wizard_tunisia_inheritance_hero",
        pexels_country="TN",
    )


def _get_or_create_simulation_purpose() -> ConsentPurpose:
    """
    Recupera (o crea con default sicuri) il `ConsentPurpose` per il wizard.

    In produzione il purpose è seedato da `seed_compliance_basics`. Il
    fallback qui evita che una piattaforma non seedata crashi sul primo
    submit del wizard: stessa filosofia di `crm.services`.
    """
    purpose, _ = ConsentPurpose.objects.get_or_create(
        code=SIMULATION_CONSENT_PURPOSE_CODE,
        defaults={
            "name": "Simulation data processing",
            "description": (
                "Consent to process the inputs provided in the public "
                "simulator for the sole purpose of producing an indicative "
                "simulation."
            ),
            "required_for_simulation": True,
        },
    )
    return purpose
