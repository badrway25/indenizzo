"""
Public views per `apps.core` (F7).

Queste view sono volutamente *informative*: nessuna crea `Simulation`,
nessuna esegue calcoli, nessuna raccoglie input utente. Servono solo
ad esporre l'identità della piattaforma e linkare al sito madre.

Il wizard pubblico (F-wizard) e il lead form (F6) avranno view dedicate.
"""

from __future__ import annotations

from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.calculators.enums import CaseType
from apps.calculators.registry import list_available_calculators
from apps.core.public_status import get_country_public_status

# Default case type used when surfacing a country's public status on
# pages that are not case-type-specific (e.g. /countries/).  IT/FR/BE
# map to road accident, MA/TN map to international inheritance.
_COUNTRY_DEFAULT_CASE_TYPE = {
    "IT": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    "FR": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    "BE": CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    "MA": CaseType.INTERNATIONAL_INHERITANCE.value,
    "TN": CaseType.INTERNATIONAL_INHERITANCE.value,
}

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
def healthz(request):
    """
    Healthcheck leggero per Docker/Caddy/monitoring.

    Volutamente non tocca DB né sessioni: deve restare verde anche se
    il database è temporaneamente sotto stress, così che il loadbalancer
    non spenga il container per un picco di IO. Per un check più
    profondo (DB ping, cache ping) si farà un endpoint separato in fase
    di hardening produzione.
    """
    return JsonResponse({"status": "ok"})


def _pexels_hero(request, purpose: str, country_code: str | None = None) -> dict | None:
    """
    Lookup read-only del manifest Pexels per la slot indicata.
    Ritorna `{"src", "alt"}` per il template (URL assoluto), oppure
    None per fallback. Niente chiamata API live.
    """
    from .pexels import get_image_for_slot, media_url_for_entry

    entry = get_image_for_slot(purpose, country_code=country_code)
    if not entry:
        return None
    return {
        "src": request.build_absolute_uri(media_url_for_entry(entry)),
        "alt": entry.get("alt") or "",
    }


@require_GET
def home(request):
    return render(
        request,
        "public/home.html",
        {
            "mvp_countries": MVP_COUNTRIES,
            "case_types_count": len(PUBLIC_CASE_TYPES),
            "pexels_image": _pexels_hero(request, "home_hero"),
        },
    )


@require_GET
def methodology(request):
    return render(
        request,
        "public/methodology.html",
        {"pexels_image": _pexels_hero(request, "methodology_hero")},
    )


@require_GET
def disclaimer(request):
    return render(request, "public/disclaimer.html")


@require_GET
def privacy(request):
    return render(request, "public/privacy.html")


def _country_landing_context(country_code: str) -> dict:
    """
    Context per le landing page paese (pass F-product-country-landing).

    NIENTE valori monetari né claim numerici: la landing è informativa.
    Il calcolatore reale (se esiste) è dietro il CTA wizard.

    Convenzioni:
    - `status_label`: badge mostrato nell'hero (Available / Under review).
    - `is_calculator_available`: gates il messaggio "real range" vs "no estimate".
    - `wizard_url_name`: URL name del wizard CTA (può essere None se non c'è).
    - `legal_sources`: lista di tuple (slug, status) per la sezione Legal basis.
    """
    italian = country_code == "italy"
    france = country_code == "france"
    belgium = country_code == "belgium"
    morocco = country_code == "morocco"
    tunisia = country_code == "tunisia"

    if italian:
        return {
            "country_code": "italy",
            "country_iso": "IT",
            "country_name_key": "Italy",
            "case_type_key": "road_accident_bodily_injury",
            "is_calculator_available": True,
            "status_label_key": "Calculator available",
            "status_tone": "ok",
            "wizard_url_name": "cases:wizard_italy_road_accident",
            "legal_sources": [
                (
                    "D.P.R. 13 gennaio 2025, n. 12 — Tabella Unica Nazionale art. 138 CAP",
                    "approved",
                ),
                ("D.Lgs. 209/2005 — Codice delle Assicurazioni Private (CAP)", "needs_review"),
                ("MIMIT — aggiornamento art. 139 (lieve entità)", "needs_review"),
                ("MIMIT — aggiornamento macrolesioni", "needs_review"),
                ("Tabelle Tribunale di Milano 2024", "needs_review"),
            ],
        }
    if france:
        return {
            "country_code": "france",
            "country_iso": "FR",
            "country_name_key": "France",
            "case_type_key": "road_accident_bodily_injury",
            "is_calculator_available": False,
            "status_label_key": "Legal sources under review",
            "status_tone": "warn",
            "wizard_url_name": "cases:wizard_france_road_accident",
            "legal_sources": [
                (
                    "Référentiel Mornet 2024 — indemnisation des préjudices corporels",
                    "needs_review",
                ),
                ("Barème de capitalisation Gazette du Palais 2022", "needs_review"),
                ("Loi n°85-677 du 5 juillet 1985 (Loi Badinter)", "needs_review"),
                ("Rapport Dintilhac — nomenclature des préjudices corporels", "needs_review"),
            ],
        }
    if belgium:
        return {
            "country_code": "belgium",
            "country_iso": "BE",
            "country_name_key": "Belgium",
            "case_type_key": "road_accident_bodily_injury",
            "is_calculator_available": False,
            "status_label_key": "Legal sources under review",
            "status_tone": "warn",
            "wizard_url_name": "cases:wizard_belgium_road_accident",
            "legal_sources": [
                ("Tableau Indicatif 2020 (édition Magistrats / Avocats)", "needs_review"),
                ("Tableau Indicatif 2024 (image-scanned, OCR pendente)", "needs_review"),
                ("Tables Schryvers (capitalisation belge)", "needs_review"),
                ("Loi du 21 novembre 1989 — assurance RC auto", "needs_review"),
            ],
        }
    if morocco:
        return {
            "country_code": "morocco",
            "country_iso": "MA",
            "country_name_key": "Morocco",
            "case_type_key": "international_inheritance",
            "is_calculator_available": False,
            "status_label_key": "Legal sources under review",
            "status_tone": "warn",
            "wizard_url_name": "cases:wizard_morocco_inheritance",
            "legal_sources": [
                ("Code de la famille — Moudawana, Loi n°70-03 (2004)", "needs_review"),
                ("Code des droits réels — Loi n°39-08", "needs_review"),
                ("Règlement UE n°650/2012 — successions internationales", "needs_review"),
            ],
        }
    if tunisia:
        return {
            "country_code": "tunisia",
            "country_iso": "TN",
            "country_name_key": "Tunisia",
            "case_type_key": "international_inheritance",
            "is_calculator_available": False,
            "status_label_key": "Legal sources under review",
            "status_tone": "warn",
            "wizard_url_name": "cases:wizard_tunisia_inheritance",
            "legal_sources": [
                ("Code du statut personnel (CSP) — Livre IX «De la succession»", "needs_review"),
                ("Loi n°98-97 — Code de droit international privé", "needs_review"),
                ("JORT 1956 — Code du statut personnel (édition originale)", "needs_review"),
                ("Règlement UE n°650/2012 — successions internationales", "needs_review"),
            ],
        }
    raise ValueError(f"Unknown country_code: {country_code!r}")


def _render_country_landing(request, country_code: str, view_name: str):
    """
    Render shared per le 5 landing paese. Aggiunge:
    - canonical self-reference + hreflang alternates (pass 2);
    - JSON-LD `LegalService` schema.org (pass 3);
    - Open Graph + Twitter Card metadata (pass 4).

    Il dict JSON-LD è serializzato qui come stringa JSON valida e
    passato al template marcato safe (il dict NON contiene input
    utente: solo costanti country e canonical URL costruito da
    `request.path`, già sanitizzato da Django).
    """
    import json

    from django.utils.translation import get_language
    from django.utils.translation import gettext as _

    from .seo import (
        build_canonical_url,
        build_hreflang_alternates,
        build_legal_service_json_ld,
        build_open_graph_metadata,
    )

    ctx = _country_landing_context(country_code)
    # Inject the centralised public status — templates render the badge,
    # description and CTA from here so we never duplicate the wording.
    ctx["public_status"] = get_country_public_status(
        ctx.get("country_iso"),
        ctx.get("case_type_key"),
    )
    canonical = build_canonical_url(request)
    ctx["canonical_url"] = canonical
    ctx["hreflang_alternates"] = build_hreflang_alternates(request, view_name)
    json_ld = build_legal_service_json_ld(
        country_code=country_code,
        canonical_url=canonical,
        language_code=(get_language() or "it").lower(),
    )
    # Il dict resta in ctx come dict (utile per i test) e in più
    # serializziamo la versione JSON che il template inietta nel
    # <script type="application/ld+json">.
    ctx["json_ld_legal_service"] = json_ld
    ctx["json_ld_legal_service_json"] = json.dumps(json_ld, ensure_ascii=False)

    # OG/Twitter title e description: ricalchiamo le stesse stringhe
    # gettext-translatable usate nei {% blocktranslate %} di
    # `country_landing.html`, così il social scraper vede esattamente
    # quello che vedrebbe leggendo il <title> e la
    # <meta name="description">. Senza il SITE_NAME appended (per OG
    # il `og:site_name` è già un tag separato).
    country_label = _(ctx["country_name_key"])
    ctx["country_name"] = country_label
    og_title = _("%(country)s — coverage and legal sources") % {"country": country_label}
    if ctx["is_calculator_available"]:
        og_description = _(
            "Indicative compensation simulation for %(country)s, based on approved "
            "legal sources. The estimate is informative and never a guarantee of "
            "outcome."
        ) % {"country": country_label}
    else:
        og_description = _(
            "%(country)s legal sources are under Studio review. No automatic estimate "
            "is currently issued; the wizard collects your request for a legal "
            "review."
        ) % {"country": country_label}
    # Pexels hero image: lookup READ-ONLY del manifest. Niente chiamata
    # API live al render: solo file locali. Se assente → fallback
    # gradient/SVG nel template.
    from .pexels import attribution_for_entry, get_image_for_country_landing, media_url_for_entry

    pexels_entry = get_image_for_country_landing(country_code)
    if pexels_entry:
        ctx["pexels_image"] = {
            "src": request.build_absolute_uri(media_url_for_entry(pexels_entry)),
            "alt": pexels_entry.get("alt") or og_title,
            "attribution": attribution_for_entry(pexels_entry),
            "photographer_url": pexels_entry.get("photographer_url") or "",
            "pexels_url": pexels_entry.get("pexels_url") or "",
        }
    else:
        ctx["pexels_image"] = None

    # OG image strategy (pass og-images-pass1):
    # - Se Pexels manifest ha un'entry country-specific, og:image punta
    #   a quel file (foto "vera" cached, migliore signal social).
    # - Altrimenti, l'helper `build_open_graph_metadata` auto-sceglie
    #   il PNG country-specific generato da
    #   `scripts/generate_og_images.py` (es. `static/img/og/og-italy.png`).
    # - Fallback finale: PNG default → SVG default.
    ctx["og_meta"] = build_open_graph_metadata(
        request,
        title=og_title,
        description=og_description,
        canonical_url=canonical,
        country_code=country_code,
    )
    if pexels_entry and pexels_entry.get("local_path"):
        pexels_image_url = request.build_absolute_uri(media_url_for_entry(pexels_entry))
        for tag in ctx["og_meta"]["og"]:
            if tag["property"] in ("og:image", "og:image:alt"):
                tag["content"] = pexels_image_url if tag["property"] == "og:image" else (og_title)
        for tag in ctx["og_meta"]["twitter"]:
            if tag["name"] in ("twitter:image", "twitter:image:alt"):
                tag["content"] = pexels_image_url if tag["name"] == "twitter:image" else (og_title)
        # I tag og:image:width/height vengono emessi dall'helper SOLO se
        # l'image_static_path è PNG. La foto Pexels è JPG con dimensioni
        # arbitrarie; rimuoviamo i tag width/height per evitare di
        # comunicare dimensioni sbagliate agli scraper.
        ctx["og_meta"]["og"] = [
            tag
            for tag in ctx["og_meta"]["og"]
            if tag["property"] not in ("og:image:width", "og:image:height")
        ]

    return render(request, "public/country_landing.html", ctx)


@require_GET
def country_italy(request):
    return _render_country_landing(request, "italy", "core:country_italy")


@require_GET
def country_france(request):
    return _render_country_landing(request, "france", "core:country_france")


@require_GET
def country_belgium(request):
    return _render_country_landing(request, "belgium", "core:country_belgium")


@require_GET
def country_morocco(request):
    return _render_country_landing(request, "morocco", "core:country_morocco")


@require_GET
def country_tunisia(request):
    return _render_country_landing(request, "tunisia", "core:country_tunisia")


@require_GET
def countries(request):
    registered_pairs = list_available_calculators()
    available_countries = {jurisdiction.split("-", 1)[0] for jurisdiction, _ in registered_pairs}
    # Lista dei paesi in cui il calculator pubblico produce stime reali
    # (CALCULATED). Un calculator può essere registrato come "scaffold"
    # ma restituire SOLO `unavailable_requires_legal_validation` finché
    # le fonti non sono `approved`. Lo distinguiamo da "really available".
    # Hardcoded per ora — quando FR avrà engine + sources approved si
    # toglierà da SCAFFOLD_ONLY_COUNTRIES.
    SCAFFOLD_ONLY_COUNTRIES = {"FR", "BE", "MA", "TN"}
    # Per ogni paese cerchiamo l'immagine country-specific dal manifest
    # (purpose="country_landing", country_code=ISO). Niente chiamata API.
    from .pexels import get_image_for_slot, media_url_for_entry

    countries_view = []
    for country in MVP_COUNTRIES:
        registered = country["code"] in available_countries
        is_scaffold = country["code"] in SCAFFOLD_ONLY_COUNTRIES
        country_image_entry = get_image_for_slot("country_landing", country_code=country["code"])
        country_image = None
        if country_image_entry:
            country_image = {
                "src": request.build_absolute_uri(media_url_for_entry(country_image_entry)),
                "alt": country_image_entry.get("alt") or country["name_key"],
            }
        countries_view.append(
            {
                **country,
                "has_calculator": registered and not is_scaffold,
                "scaffold_only": registered and is_scaffold,
                "image": country_image,
                "public_status": get_country_public_status(
                    country["code"],
                    _COUNTRY_DEFAULT_CASE_TYPE.get(country["code"]),
                ),
            }
        )
    return render(
        request,
        "public/countries.html",
        {
            "countries": countries_view,
            "pexels_image": _pexels_hero(request, "countries_index"),
        },
    )


@require_GET
def case_types(request):
    registered_pairs = list_available_calculators()
    pairs_by_case_type: dict[str, list[str]] = {}
    for j, c in registered_pairs:
        pairs_by_case_type.setdefault(c, []).append(j)
    # Per-case-type 3-state: available / scaffold_only / in_preparation.
    # Lo stesso set hardcoded usato in `countries` per coerenza.
    SCAFFOLD_ONLY_PAIRS_FOR_CT = {
        ("FR-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value),
        ("BE-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value),
        ("MA-NATIONAL", CaseType.INTERNATIONAL_INHERITANCE.value),
        ("TN-NATIONAL", CaseType.INTERNATIONAL_INHERITANCE.value),
    }
    case_types_view = []
    for case_type in PUBLIC_CASE_TYPES:
        jurisdictions = pairs_by_case_type.get(case_type.value, [])
        registered = bool(jurisdictions)
        # Operative se ALMENO una pair (j, c) NON è in SCAFFOLD_ONLY_PAIRS.
        all_scaffold = registered and all(
            (j, case_type.value) in SCAFFOLD_ONLY_PAIRS_FOR_CT for j in jurisdictions
        )
        # Pick a representative country whose status best reflects
        # the case-type readiness: prefer the most-available
        # jurisdiction so a case type that is live in IT but scaffold
        # in FR/BE still reads as "Indicative calculation available".
        non_scaffold = [
            j for j in jurisdictions if (j, case_type.value) not in SCAFFOLD_ONLY_PAIRS_FOR_CT
        ]
        rep_jurisdiction = (non_scaffold or jurisdictions or [""])[0]
        rep_country = rep_jurisdiction.split("-", 1)[0] if rep_jurisdiction else ""
        case_types_view.append(
            {
                "code": case_type.value,
                "label": case_type.label,
                "available": registered and not all_scaffold,
                "scaffold_only": all_scaffold,
                "public_status": get_country_public_status(rep_country, case_type.value),
            }
        )
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
    # Per ogni coppia (jurisdiction, case_type) registrata, marchiamo se è
    # operativa (calcola davvero) o solo scaffold (calculator placeholder
    # che restituisce `unavailable`). Hardcoded — quando FR avrà il vero
    # engine si toglierà da SCAFFOLD_ONLY_PAIRS.
    SCAFFOLD_ONLY_PAIRS = {
        ("FR-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value),
        ("BE-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value),
        ("MA-NATIONAL", CaseType.INTERNATIONAL_INHERITANCE.value),
        ("TN-NATIONAL", CaseType.INTERNATIONAL_INHERITANCE.value),
    }
    modules_active = [
        {
            "jurisdiction": j,
            "case_type": c,
            "scaffold_only": (j, c) in SCAFFOLD_ONLY_PAIRS,
        }
        for j, c in sorted(registered_pairs)
    ]
    upcoming = []

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
