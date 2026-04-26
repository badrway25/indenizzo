"""
Public views per `apps.core` (F7).

Queste view sono volutamente *informative*: nessuna crea `Simulation`,
nessuna esegue calcoli, nessuna raccoglie input utente. Servono solo
ad esporre l'identità della piattaforma e linkare al sito madre.

Il wizard pubblico (F-wizard) e il lead form (F6) avranno view dedicate.
"""

from __future__ import annotations

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
