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

from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import translation
from django.views.decorators.http import require_GET, require_http_methods

from apps.calculators.enums import CaseType
from apps.calculators.registry import list_available_calculators
from apps.compliance.models import ConsentPurpose
from apps.compliance.services import record_consent

from .forms import FranceRoadAccidentWizardForm, ItalyRoadAccidentWizardForm
from .models import Simulation
from .services import run_simulation

logger = logging.getLogger(__name__)

ITALY_ROAD_ACCIDENT_JURISDICTION = "IT-NATIONAL"
ITALY_ROAD_ACCIDENT_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
FRANCE_ROAD_ACCIDENT_JURISDICTION = "FR-NATIONAL"
FRANCE_ROAD_ACCIDENT_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
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
    ]
    upcoming = [
        {"country_code": "IT", "case_label": CaseType.INHERITANCE_BASIC.label},
        {"country_code": "BE", "case_label": CaseType.ROAD_ACCIDENT_BODILY_INJURY.label},
        {"country_code": "MA", "case_label": CaseType.INTERNATIONAL_INHERITANCE.label},
        {"country_code": "TN", "case_label": CaseType.INTERNATIONAL_INHERITANCE.label},
    ]
    return render(
        request,
        "public/wizard_start.html",
        {"options": options, "upcoming": upcoming},
    )


# ---------------------------------------------------------------------------
# /wizard/it/road-accident/  — Italia, incidente stradale
# ---------------------------------------------------------------------------


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

    return render(
        request,
        "public/wizard_italy_road_accident.html",
        {
            "form": form,
            "jurisdiction_code": ITALY_ROAD_ACCIDENT_JURISDICTION,
            "case_type": ITALY_ROAD_ACCIDENT_CASE_TYPE,
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
    warnings = output.get("warnings") or []
    missing_documents = output.get("missing_documents") or []
    assumptions = output.get("assumptions") or []
    legal_disclaimer = output.get("legal_disclaimer") or ""

    # Costruzione URL CTA verso il lead form già in F6.
    contact_url = reverse("crm:contact") + f"?sim={simulation.public_id}"

    has_estimate = any(
        simulation.output_data.get(k) is not None
        for k in ("estimated_min", "estimated_mid", "estimated_max")
    )

    # Label pubblica dello status: il template mostra questa, mentre il
    # `simulation.status` raw resta visibile come "internal status code"
    # per audit/trasparenza.
    from apps.calculators.status_labels import get_public_status_label

    locale = (translation.get_language() or simulation.locale or "it").split("-", 1)[0]
    status_public_label = get_public_status_label(simulation.status, language=locale)

    return render(
        request,
        "public/wizard_result.html",
        {
            "simulation": simulation,
            "sources": sources,
            "warnings": warnings,
            "missing_documents": missing_documents,
            "assumptions": assumptions,
            "legal_disclaimer": legal_disclaimer,
            "contact_url": contact_url,
            "has_estimate": has_estimate,
            "status_public_label": status_public_label,
        },
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _run_italy_road_accident(request, form: ItalyRoadAccidentWizardForm) -> Simulation:
    """
    Registra ConsentRecord (`simulation_processing`) e chiama il service.

    `record_consent` è già idempotente lato service e tollerante a
    `request=None`. Qui passiamo la request reale per catturare IP/UA/path.
    """
    purpose = _get_or_create_simulation_purpose()
    consent = record_consent(
        purpose=purpose,
        accepted=True,
        request=request,
        user=request.user if request.user.is_authenticated else None,
        metadata={"trigger": "wizard_italy_road_accident"},
    )
    locale = (translation.get_language() or "it").split("-", 1)[0].lower()

    return run_simulation(
        jurisdiction_code=ITALY_ROAD_ACCIDENT_JURISDICTION,
        case_type=ITALY_ROAD_ACCIDENT_CASE_TYPE,
        input_data=form.to_input_data(),
        request=request,
        user=request.user if request.user.is_authenticated else None,
        consent_record=consent,
        locale=locale,
    )


# ---------------------------------------------------------------------------
# /wizard/fr/road-accident/  — France, accident de la circulation (scaffold)
# ---------------------------------------------------------------------------


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

    return render(
        request,
        "public/wizard_france_road_accident.html",
        {
            "form": form,
            "jurisdiction_code": FRANCE_ROAD_ACCIDENT_JURISDICTION,
            "case_type": FRANCE_ROAD_ACCIDENT_CASE_TYPE,
        },
    )


def _run_france_road_accident(request, form: FranceRoadAccidentWizardForm) -> Simulation:
    """Stesso pattern di `_run_italy_road_accident` ma su giurisdizione FR."""
    purpose = _get_or_create_simulation_purpose()
    consent = record_consent(
        purpose=purpose,
        accepted=True,
        request=request,
        user=request.user if request.user.is_authenticated else None,
        metadata={"trigger": "wizard_france_road_accident"},
    )
    locale = (translation.get_language() or "fr").split("-", 1)[0].lower()

    return run_simulation(
        jurisdiction_code=FRANCE_ROAD_ACCIDENT_JURISDICTION,
        case_type=FRANCE_ROAD_ACCIDENT_CASE_TYPE,
        input_data=form.to_input_data(),
        request=request,
        user=request.user if request.user.is_authenticated else None,
        consent_record=consent,
        locale=locale,
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
