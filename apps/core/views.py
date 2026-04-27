"""
Public views per `apps.core` (F7).

Queste view sono volutamente *informative*: nessuna crea `Simulation`,
nessuna esegue calcoli, nessuna raccoglie input utente. Servono solo
ad esporre l'identità della piattaforma e linkare al sito madre.

Il wizard pubblico (F-wizard) e il lead form (F6) avranno view dedicate.
"""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.calculators.enums import CaseType
from apps.calculators.registry import list_available_calculators

# Paesi MVP esposti pubblicamente. Lista statica, NON è dato legale —
# è la mappa "questi paesi sono all'orizzonte del prodotto".
MVP_COUNTRIES = [
    {"code": "IT", "name_key": "Italy"},
    {"code": "FR", "name_key": "France"},
    {"code": "BE", "name_key": "Belgium"},
    {"code": "MA", "name_key": "Morocco"},
    {"code": "TN", "name_key": "Tunisia"},
]

# Case type publici (sottoinsieme della tassonomia REQ-4).
# Il flag `available` è derivato dal registry F4: se nessun calculator è
# registrato per quel case_type, è "in preparazione".
PUBLIC_CASE_TYPES = [
    CaseType.ROAD_ACCIDENT_BODILY_INJURY,
    CaseType.MEDICAL_MALPRACTICE,
    CaseType.WORK_INJURY,
    CaseType.DEATH_COMPENSATION,
    CaseType.PARENTAL_LOSS,
    CaseType.PATRIMONIAL_DAMAGE,
    CaseType.INHERITANCE_BASIC,
    CaseType.INTERNATIONAL_INHERITANCE,
]


def _registered_case_types() -> set[str]:
    """Insieme dei case_type per cui esiste almeno un calculator registrato."""
    return {case_type for _, case_type in list_available_calculators()}


@require_GET
def home(request):
    return render(
        request,
        "public/home.html",
        {
            "mvp_countries": MVP_COUNTRIES,
            "case_types_count": len(PUBLIC_CASE_TYPES),
        },
    )


@require_GET
def methodology(request):
    return render(request, "public/methodology.html")


@require_GET
def disclaimer(request):
    return render(request, "public/disclaimer.html")


@require_GET
def privacy(request):
    return render(request, "public/privacy.html")


@require_GET
def countries(request):
    registered_pairs = list_available_calculators()
    available_countries = {jurisdiction.split("-", 1)[0] for jurisdiction, _ in registered_pairs}
    countries_view = []
    for country in MVP_COUNTRIES:
        countries_view.append(
            {
                **country,
                "has_calculator": country["code"] in available_countries,
            }
        )
    return render(
        request,
        "public/countries.html",
        {"countries": countries_view},
    )


@require_GET
def case_types(request):
    registered = _registered_case_types()
    case_types_view = [
        {
            "code": case_type.value,
            "label": case_type.label,
            "available": case_type.value in registered,
        }
        for case_type in PUBLIC_CASE_TYPES
    ]
    return render(
        request,
        "public/case_types.html",
        {"case_types": case_types_view},
    )


# ---------------------------------------------------------------------------
# Staff project status dashboard
# ---------------------------------------------------------------------------

NO_GO_PRODUCTION = [
    "DB ancora SQLite (CLAUDE.md richiede Postgres in prod).",
    "SECRET_KEY di default — sostituire via env in prod.",
    "DJANGO_DEBUG=true in dev — verificare false in prod.",
    "Translation .mo non compilate per fr/en/ar.",
    "Tailwind via CDN (warning console) — passare a build PostCSS.",
    "Cookie consent banner EU non implementato.",
    "Email transactional Lead non configurate.",
    "Backup / monitoring / Sentry assenti.",
    "Nessun rate-limit sui POST pubblici.",
]


@staff_member_required
@require_GET
def project_status(request):
    """
    Pagina di stato per staff Studio: snapshot live della pipeline TUN
    + contatori. Solo lettura. Richiede `is_staff=True`.
    """
    # Lazy imports per non rompere circular deps.
    from apps.cases.models import Simulation
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        ExtractionLog,
    )
    from apps.crm.models import Lead
    from apps.legal_sources.models import LegalReview, LegalSource
    from apps.reports.models import SimulationReport

    src = LegalSource.objects.filter(slug="it-dpr-12-2025-tun-danno-biologico").first()
    attach = src.attachments.first() if src else None
    dataset = (
        CompensationDataset.objects.filter(version_label="DPR-12-2025")
        .select_related("source", "jurisdiction", "country")
        .first()
    )
    formula = (
        CalculationFormula.objects.filter(code="italy_art_138_tun_2025_base")
        .select_related("dataset")
        .first()
    )
    rows_count = CompensationTableRow.objects.filter(dataset=dataset).count() if dataset else 0
    last_extraction = (
        ExtractionLog.objects.filter(method=ExtractionLog.Method.CSV_IMPORT)
        .order_by("-created_at", "-pk")
        .first()
    )
    last_review = (
        LegalReview.objects.filter(source=src).order_by("-created_at", "-pk").first()
        if src
        else None
    )

    registered_pairs = list_available_calculators()
    modules_active = [{"jurisdiction": j, "case_type": c} for j, c in sorted(registered_pairs)]
    upcoming = [
        {"jurisdiction": "FR-NATIONAL", "case_type": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value},
        {"jurisdiction": "BE-NATIONAL", "case_type": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value},
        {"jurisdiction": "MA-NATIONAL", "case_type": CaseType.INTERNATIONAL_INHERITANCE.value},
        {"jurisdiction": "TN-NATIONAL", "case_type": CaseType.INTERNATIONAL_INHERITANCE.value},
    ]

    context = {
        "source": src,
        "attachment": attach,
        "dataset": dataset,
        "formula": formula,
        "rows_count": rows_count,
        "last_extraction_log": last_extraction,
        "last_review": last_review,
        "simulation_total": Simulation.objects.count(),
        "simulation_calculated": Simulation.objects.filter(status="calculated").count(),
        "simulation_unavailable": Simulation.objects.filter(
            status="unavailable_requires_legal_validation"
        ).count(),
        "lead_total": Lead.objects.count(),
        "report_total": SimulationReport.objects.count(),
        "modules_active": modules_active,
        "modules_upcoming": upcoming,
        "no_go_production": NO_GO_PRODUCTION,
    }
    return render(request, "staff/project_status.html", context)
