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
        DatasetStatus,
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
    # Nota: il `Meta.ordering` di CompensationTableRow include `age_min` /
    # `disability_min`, che Django propaga al SELECT e rompe `distinct()`.
    # `.order_by("row_type")` ripristina il distinct corretto.
    base_row_types = (
        list(
            CompensationTableRow.objects.filter(dataset=dataset)
            .order_by("row_type")
            .values_list("row_type", flat=True)
            .distinct()
        )
        if dataset
        else []
    )

    # Range moral dataset (secondario, referenziato da formula.parameters
    # quando amount_rule == row_amount_range_direct).
    moral = (
        CompensationDataset.objects.filter(version_label="DPR-12-2025-MORAL")
        .select_related("source", "jurisdiction", "country")
        .first()
    )
    moral_row_type_counts: list[dict] = []
    moral_rows_total = 0
    if moral:
        # Conta per row_type. Se la formula dichiara dei row_type espliciti
        # nei parameters range, li mostriamo nell'ordine min/mid/max anche
        # se nel DB risultano in altro ordine alfabetico.
        params = formula.parameters or {} if formula else {}
        ordered = [
            ("min", params.get("min_row_type") or "tun_biological_moral_min_total_amount"),
            ("mid", params.get("mid_row_type") or "tun_biological_moral_mid_total_amount"),
            ("max", params.get("max_row_type") or "tun_biological_moral_max_total_amount"),
        ]
        for kind, rt in ordered:
            cnt = CompensationTableRow.objects.filter(dataset=moral, row_type=rt).count()
            moral_rows_total += cnt
            moral_row_type_counts.append({"kind": kind, "row_type": rt, "count": cnt})

    # Active calculation rule: vista "umana" dei parametri della formula
    # approvata, focalizzata sui campi rilevanti per il range engine.
    active_rule = None
    if formula and formula.status == DatasetStatus.APPROVED:
        params = formula.parameters or {}
        active_rule = {
            "amount_rule": params.get("amount_rule"),
            "fault_reduction": params.get("fault_reduction"),
            "is_range": params.get("amount_rule") == "row_amount_range_direct",
            "range_dataset_version_label": params.get("range_dataset_version_label"),
            "min_row_type": params.get("min_row_type"),
            "mid_row_type": params.get("mid_row_type"),
            "max_row_type": params.get("max_row_type"),
            "engine": params.get("engine"),
        }

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
    # Latest LegalReview che cita esplicitamente le Tabelle 2.A/2.B/2.C —
    # è quella che ha autorizzato l'attivazione del range moral. Se non
    # esiste (range non ancora attivato) restiamo a None senza errore.
    last_moral_review = (
        LegalReview.objects.filter(source=src, comment__icontains="2.A")
        .filter(comment__icontains="2.B")
        .filter(comment__icontains="2.C")
        .order_by("-created_at", "-pk")
        .first()
        if src
        else None
    )

    # Reference smoke values (display-only). NON eseguiamo il calculator
    # qui: i numeri sono il contratto storico documentato dei test/QA,
    # mostrati per dare un riferimento veloce all'oncall di Studio.
    reference_smoke = {
        "input": {"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0},
        "expected_min": "26268",
        "expected_mid": "27353",
        "expected_max": "28439",
        "applicable": active_rule is not None and active_rule.get("is_range"),
    }

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
        "base_row_types": base_row_types,
        "moral_dataset": moral,
        "moral_row_type_counts": moral_row_type_counts,
        "moral_rows_total": moral_rows_total,
        "active_rule": active_rule,
        "reference_smoke": reference_smoke,
        "formula": formula,
        "rows_count": rows_count,
        "last_extraction_log": last_extraction,
        "last_review": last_review,
        "last_moral_review": last_moral_review,
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
