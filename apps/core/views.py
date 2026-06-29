"""
Public views per `apps.core` (F7).

Queste view sono volutamente *informative*: nessuna crea `Simulation`,
nessuna esegue calcoli, nessuna raccoglie input utente. Servono solo
ad esporre l'identità della piattaforma e linkare al sito madre.

Il wizard pubblico (F-wizard) e il lead form (F6) avranno view dedicate.
"""

from __future__ import annotations

import json

from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_GET, require_http_methods

from apps.calculators.enums import CaseType
from apps.calculators.registry import list_available_calculators
from apps.core import public_pages
from apps.core.country_readiness import public_country_readiness
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

# P26: per-country coverage for the redesigned countries hub — the main
# categories (so no country reads as inheritance-only) and the primary
# normative reference. Categories reuse already-translated labels; main_source
# is a language-neutral citation, never an amount.
_COUNTRY_COVERAGE = {
    "IT": {"categories": [_("Road accident"), _("Medical liability"),
                          _("Workplace injury"), _("Loss of a relative"), _("Inheritance")],
           "main_source": "art. 139 CAP · Tabella Unica Nazionale 2025"},
    "FR": {"categories": [_("Road accident")],
           "main_source": "Loi Badinter (loi 85-677)"},
    "BE": {"categories": [_("Road accident")],
           "main_source": "Indicatieve tabel / Tableau indicatif"},
    "MA": {"categories": [_("Road accident"), _("Inheritance")],
           "main_source": "Dahir 1-84-177 · ACAPS"},
    "TN": {"categories": [_("Road accident"), _("Inheritance")],
           "main_source": "Loi 2005-86 (Code des assurances)"},
}

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


_FAVICON_SVG_BYTES: bytes | None = None


@require_GET
def favicon_ico(request):
    """
    Serve `/favicon.ico` returning the local SVG favicon.

    Iter: F-p1-seo-2-favicon. Modern browsers honour the
    ``<link rel="icon" type="image/svg+xml">`` in `base.html`, but
    naive clients (curl, some bots, the Lighthouse runner without
    DOM-discovery) hit `/favicon.ico` directly. Without this view
    those requests 404, polluting the console + the LHCI report.

    Implementation: read the SVG once at module load, cache in a
    module-level variable, return it with `Content-Type: image/svg+xml`.
    Browsers honour the Content-Type even when the URL ends in `.ico`.
    """
    global _FAVICON_SVG_BYTES
    if _FAVICON_SVG_BYTES is None:
        from django.conf import settings as _settings

        candidates = [_settings.BASE_DIR / "static" / "img" / "favicon.svg"]
        # When the project is collected (`collectstatic`) STATIC_ROOT
        # also has the file; in dev the `static/` source dir is the
        # source of truth.
        for path in candidates:
            if path.exists():
                _FAVICON_SVG_BYTES = path.read_bytes()
                break
        else:
            # Defensive: if the file went missing we still return a
            # valid response rather than letting a 500 leak.
            _FAVICON_SVG_BYTES = (
                b'<svg xmlns="http://www.w3.org/2000/svg" '
                b'viewBox="0 0 64 64"><rect width="64" height="64" fill="#0c2046"/></svg>'
            )
    response = HttpResponse(_FAVICON_SVG_BYTES, content_type="image/svg+xml")
    # Long-lived cache: browsers + CDNs can keep the favicon for a
    # year. Bumping the SVG bytes implicitly busts the cache because
    # most clients fetch on first visit per session anyway.
    response["Cache-Control"] = "public, max-age=31536000"
    return response


# Path da escludere dall'indicizzazione tramite robots.txt.
# Note:
# - /contact/ NON è in lista: è una pagina pubblica utile a SEO/lead.
# - /contact/thank-you/ è bloccata (pagina post-submit, non SEO-utile).
# - /wizard/result/ è bloccata: contiene input personali utente
#   (la regola robots.txt è la prima linea di difesa, ma il vero
#   noindex sta nel meta tag dei template — robots.txt da solo non
#   evita indicizzazione di URL già scoperti).
# - /admin/, /staff/, /reports/ sono back-office.
_ROBOTS_DISALLOW_PATHS = (
    "/admin/",
    "/staff/",
    "/reports/",
    "/wizard/result/",
    "/contact/thank-you/",
)


@require_GET
def robots_txt(request):
    """
    `/robots.txt` statico, servito plain-text.

    Iter: F-p0-codice-1-robots-txt (audit/indennizzati-platform).

    Strategia:
    - User-agent universale `*`;
    - Disallow su back-office, pagine post-submit con dati utente,
      pagine confirmation;
    - Allow esplicito di /contact/ (pagina pubblica utile a SEO);
    - Sitemap puntato all'URL assoluto (lo sitemap framework Django
      e' montato fuori da i18n_patterns).
    """
    sitemap_url = request.build_absolute_uri(reverse("django.contrib.sitemaps.views.sitemap"))
    lines = ["User-agent: *"]
    lines.extend(f"Disallow: {path}" for path in _ROBOTS_DISALLOW_PATHS)
    lines.append("Allow: /contact/")
    lines.append("")
    lines.append(f"Sitemap: {sitemap_url}")
    body = "\n".join(lines) + "\n"
    return HttpResponse(body, content_type="text/plain; charset=utf-8")


def _pexels_hero(request, purpose: str, country_code: str | None = None) -> dict | None:
    """
    Lookup read-only del manifest Pexels per la slot indicata.
    Ritorna un dict per il template (URL assoluti), oppure None per
    fallback. Niente chiamata API live.

    Keys:
      - ``src``           : original JPEG/PNG URL (always present)
      - ``alt``           : alt text (may be empty)
      - ``webp_src``      : full-resolution WebP URL, only if the
                            companion file exists on disk
                            (see `manage.py compress_pexels_images`)
      - ``webp_src_mobile``: 800-wide mobile WebP URL, same condition

    Templates that want to emit a `<picture>` element MUST check
    `webp_src` and `webp_src_mobile` before using them — if the
    companion files were never generated, the `<source>` elements
    must be omitted so the browser falls back to the original
    JPEG/PNG via the `<img>` tag.
    """
    from pathlib import Path

    from django.conf import settings

    from .pexels import get_image_for_slot, media_url_for_entry

    entry = get_image_for_slot(purpose, country_code=country_code)
    if not entry:
        return None

    result: dict[str, str] = {
        "src": request.build_absolute_uri(media_url_for_entry(entry)),
        "alt": entry.get("alt") or "",
    }

    # WebP companions (P2-IMG-1). The compress_pexels_images command
    # writes `<name>.webp` and `<name>.mobile.webp` next to each
    # source JPEG/PNG. We surface their URLs only when the files
    # actually exist on disk, so a project that has not run the
    # compression step still gets a working <img> fallback.
    local_path = (entry.get("local_path") or "").lstrip("/")
    if local_path:
        source_disk = Path(settings.MEDIA_ROOT) / local_path
        media_url = (getattr(settings, "MEDIA_URL", "/media/") or "/media/").rstrip("/")
        relative_dir = "/".join(local_path.split("/")[:-1])
        relative_dir = (relative_dir + "/") if relative_dir else ""

        stem = source_disk.stem
        webp_desktop_disk = source_disk.with_suffix(".webp")
        webp_mobile_disk = source_disk.with_name(stem + ".mobile.webp")

        if webp_desktop_disk.is_file():
            result["webp_src"] = request.build_absolute_uri(
                f"{media_url}/{relative_dir}{webp_desktop_disk.name}"
            )
        if webp_mobile_disk.is_file():
            result["webp_src_mobile"] = request.build_absolute_uri(
                f"{media_url}/{relative_dir}{webp_mobile_disk.name}"
            )

    return result


@require_GET
def home(request):
    # P22: featured documental pre-checks for the home product section. The
    # label/badge are gettext msgids (translated in-template); the source is a
    # language-neutral citation rendered as-is.
    home_prechecks = [
        {"slug": "inail", "icon": "hard-hat", "label": "Work injury (INAIL)",
         "badge": "Documental pre-check with official sources", "source": "D.P.R. 1124/1965 · D.M. 45/2019"},
        {"slug": "morocco-road-accident", "icon": "car", "label": "Road accident in Morocco",
         "badge": "Documental pre-check with official sources", "source": "Dahir 1-84-177 · ACAPS"},
        {"slug": "tunisia-road-accident", "icon": "car", "label": "Road accident in Tunisia",
         "badge": "Documental pre-check with official sources", "source": "Loi 2005-86 · CGA"},
        {"slug": "loss-of-relative", "icon": "heart", "label": "Loss of a relative",
         "badge": "Assisted path based on official sources", "source": "artt. 2043, 2059 c.c."},
        {"slug": "international-road-accident", "icon": "globe", "label": "Cross-border accident",
         "badge": "Applicable-law framing", "source": "Reg. CE 864/2007 (Roma II)"},
    ]
    return render(
        request,
        "public/home.html",
        {
            "mvp_countries": MVP_COUNTRIES,
            "case_types_count": len(PUBLIC_CASE_TYPES),
            "home_prechecks": home_prechecks,
            "pexels_image": _pexels_hero(request, "home_hero"),
            # P24: a distinct, heavily-tinted photo behind the closing CTA band.
            "pexels_texture": _pexels_hero(request, "methodology_hero"),
            # P36: "what do you want to do?" intent cards with section imagery.
            "intent_cards": [
                {"url": reverse("cases:wizard_italy_road_accident"), "icon": "scale",
                 "image": _pexels_hero(request, "intent_estimate"), "delay": 0,
                 "event": "intent_estimate",
                 "title": _("Make an estimate"),
                 "text": _("See an indicative range where an official table allows it.")},
                {"url": reverse("cases:wizard_insurance_offer"), "icon": "shield-check",
                 "image": _pexels_hero(request, "intent_offer"), "delay": 80,
                 "event": "intent_offer",
                 "title": _("Check an offer"),
                 "text": _("Find out whether the insurer's offer is in line.")},
                {"url": reverse("core:documents_upload"), "icon": "document",
                 "image": _pexels_hero(request, "intent_documents"), "delay": 160,
                 "event": "intent_documents",
                 "title": _("Upload documents"),
                 "text": _("We recognise your documents and prepare your file.")},
                {"url": reverse("core:guided_router"), "icon": "globe",
                 "image": _pexels_hero(request, "intent_law"), "delay": 240,
                 "event": "intent_law",
                 "title": _("Which law applies"),
                 "text": _("Understand which country's law may apply to your case.")},
            ],
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


@require_GET
def how_it_works(request):
    from apps.core.seo import build_canonical_url

    return render(
        request,
        "public/how_it_works.html",
        {
            "steps": public_pages.HOW_IT_WORKS_STEPS,
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "how_it_works_hero"),
        },
    )


@require_GET
def services(request):
    from apps.core.seo import build_canonical_url

    return render(
        request,
        "public/services.html",
        {
            "services": public_pages.SERVICES,
            "service_groups": public_pages.grouped_services(),
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "services_hero"),
            # P39: internal imagery for the three service sections.
            "img_estimate": _pexels_hero(request, "services_estimate"),
            "img_documents": _pexels_hero(request, "services_documents"),
            "img_international": _pexels_hero(request, "services_international"),
        },
    )


@require_http_methods(["GET", "POST"])
def precheck(request, slug):
    """P15/P16: interactive guided documental pre-check for a non-numeric section.

    GET renders the premium mini-form. POST evaluates the answers in memory
    (stateless, GDPR-light — nothing is persisted) and renders a personalised
    guided result: completeness, missing documents, applicable official sources,
    contextual messages and a CTA. Never an amount (no approved engine here).
    404 for an unknown slug.
    """
    from django.http import Http404

    from apps.core.precheck import get_precheck
    from apps.core.precheck_engine import evaluate
    from apps.core.seo import build_canonical_url

    flow = get_precheck(slug)
    if flow is None:
        raise Http404("Unknown pre-check flow")

    answers = {}
    result = None
    if request.method == "POST":
        # Collect only the known field ids — ignore anything else in POST.
        answers = {f.id: request.POST.get(f.id, "").strip() for f in flow.fields}
        result = evaluate(flow, answers)

    # Render-ready fields: pair each field with its submitted value so the
    # template can repopulate without a dict-lookup template filter.
    form_fields = [{"field": f, "value": answers.get(f.id, "")} for f in flow.fields]

    # P28: a unified dossier summary drives the "consolidate the dossier" panel,
    # the print layout and the result-aware contact CTA. Built statelessly.
    dossier = None
    if result is not None:
        from django.utils.translation import get_language

        from apps.core.dossier import from_precheck

        dossier = from_precheck(flow, result, get_language() or "")

    return render(
        request,
        "public/precheck.html",
        {
            "flow": flow,
            "form_fields": form_fields,
            "result": result,
            "dossier": dossier,
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "services_hero"),
            # P39: report-style side panel for the human pre-check result.
            "img_report": _pexels_hero(request, "result_report"),
        },
    )


@require_GET
def guided_router(request):
    """P15: country × category guided router.

    A single navigable entry point — pick a country, then a category — that
    routes to the right destination (live engine, tabular/comparison wizard or
    documental pre-check). It only routes: no amount is computed here.
    """
    from apps.core.guided_router import grouped_routes
    from apps.core.seo import build_canonical_url

    return render(
        request,
        "public/guided_router.html",
        {
            "country_groups": grouped_routes(),
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "guided_hero"),
            # P39: internal imagery beside the visual stepper.
            "img_workflow": _pexels_hero(request, "guided_workflow"),
        },
    )


@require_GET
def faq(request):
    """Public FAQ + FAQPage structured data.

    The JSON-LD is built from the SAME `public_pages.FAQ_ITEMS` rendered on the
    page (gettext_lazy resolved in the active language), so the structured data
    can never drift from the visible answers. Plain text only — no HTML, no
    invented figures.
    """
    from apps.core.seo import build_canonical_url

    faq_jsonld = json.dumps(
        {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": str(item.question),
                    "acceptedAnswer": {"@type": "Answer", "text": str(item.answer)},
                }
                for item in public_pages.FAQ_ITEMS
            ],
        },
        ensure_ascii=False,
    )
    return render(
        request,
        "public/faq.html",
        {
            "faq_items": public_pages.FAQ_ITEMS,
            "faq_jsonld": faq_jsonld,
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "faq_hero"),
        },
    )


@require_GET
def about(request):
    from apps.core.seo import build_canonical_url

    return render(
        request,
        "public/about.html",
        {
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "about_hero"),
        },
    )


@require_GET
def community(request):
    """Arabic/French-speaking community landing (Ta3ouid). RTL-safe; prudent."""
    from apps.core.seo import build_canonical_url

    return render(
        request,
        "public/community.html",
        {
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "ta3ouid_hero"),
        },
    )


def _country_landing_context(country_code: str) -> dict:
    """
    Context per le landing page paese (pass F-product-country-landing).

    NIENTE valori monetari né claim numerici: la landing è informativa.
    Il calcolatore reale (se esiste) è dietro il CTA wizard.

    Convenzioni:
    - `status_label`: badge mostrato nell'hero (Available / Official guided pathway).
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
            "status_label_key": "Official guided pathway",
            "status_tone": "gold",
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
            "status_label_key": "Official guided pathway",
            "status_tone": "gold",
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
            "status_label_key": "Official guided pathway",
            "status_tone": "gold",
            "wizard_url_name": "cases:wizard_morocco_inheritance",
            "legal_sources": [
                ("Dahir n°1-84-177 (1984) — indemnisation accidents de circulation", "approved"),
                ("ACAPS — guide d'indemnisation des victimes", "approved"),
                ("Code des obligations et des contrats", "approved"),
                ("Code des assurances", "approved"),
                ("Code de la famille — Moudawana, Loi n°70-03 (2004)", "approved"),
                ("Règlement UE n°650/2012 — successions internationales", "approved"),
            ],
            # P14: Morocco covers road injury, death, bodily damage and eligible
            # family members on the Dahir 1984 / ACAPS — not succession only.
            "categories": [
                {"name_key": "Road accidents and bodily injury",
                 "sources": ("Dahir 1-84-177 (1984)", "ACAPS", "Code des assurances"),
                 "cta_slug": "morocco-road-accident",
                 "cta_label": "Start the Dahir / ACAPS pre-check"},
                {"name_key": "Death and eligible family members",
                 "sources": ("Dahir 1-84-177 (1984)", "ACAPS"),
                 "cta_slug": "morocco-road-accident",
                 "cta_label": "Start the death pre-check"},
                {"name_key": "Civil liability and insurance",
                 "sources": ("Code des obligations et des contrats", "Code des assurances"),
                 "cta_slug": "morocco-road-accident",
                 "cta_label": "Check the documents needed"},
                {"name_key": "International succession",
                 "sources": ("Moudawana (Loi 70-03)", "Règlement UE 650/2012"),
                 "cta_slug": "international-road-accident",
                 "cta_label": "Frame the applicable law"},
            ],
        }
    if tunisia:
        return {
            "country_code": "tunisia",
            "country_iso": "TN",
            "country_name_key": "Tunisia",
            "case_type_key": "international_inheritance",
            "is_calculator_available": False,
            "status_label_key": "Official guided pathway",
            "status_tone": "gold",
            "wizard_url_name": "cases:wizard_tunisia_inheritance",
            "legal_sources": [
                ("Loi n°2005-86 — Code des assurances, Titre V (art. 110–179)", "approved"),
                ("Comité Général des Assurances (CGA)", "approved"),
                ("Code des obligations et des contrats tunisien", "approved"),
                ("Code du statut personnel (CSP) — Livre IX «De la succession»", "approved"),
                ("Règlement UE n°650/2012 — successions internationales", "approved"),
            ],
            # P14: Tunisia covers road injury and death on the binding loi 2005-86
            # barème (Code des assurances), not succession only.
            "categories": [
                {"name_key": "Road accidents and bodily injury",
                 "sources": ("Loi 2005-86", "Code des assurances (Titre V)", "CGA"),
                 "cta_slug": "tunisia-road-accident",
                 "cta_label": "Start the Code des assurances pre-check"},
                {"name_key": "Death and eligible family members",
                 "sources": ("Loi 2005-86", "Code des assurances"),
                 "cta_slug": "tunisia-road-accident",
                 "cta_label": "Start the death pre-check"},
                {"name_key": "Civil liability and insurance",
                 "sources": ("Code des assurances", "CGA"),
                 "cta_slug": "tunisia-road-accident",
                 "cta_label": "Check the documents needed"},
                {"name_key": "International succession",
                 "sources": ("Code du statut personnel", "Règlement UE 650/2012"),
                 "cta_slug": "international-road-accident",
                 "cta_label": "Frame the applicable law"},
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
            "%(country)s offers an assisted legal pathway grounded in official "
            "sources. The wizard collects your request and the Studio replies "
            "directly."
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
        coverage = _COUNTRY_COVERAGE.get(country["code"], {})
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
                # P26: real coverage categories (no country is inheritance-only)
                # + the primary normative reference, for the richer hub card.
                "categories": coverage.get("categories", []),
                "main_source": coverage.get("main_source", ""),
            }
        )
    return render(
        request,
        "public/countries.html",
        {
            "countries": countries_view,
            # E1: leak-safe public readiness (Italy available; FR/BE/MA/TN in
            # legal validation). Same data as the readiness.json endpoint.
            "country_readiness": public_country_readiness(),
            "pexels_image": _pexels_hero(request, "countries_index"),
        },
    )


@require_GET
def country_readiness_json(request):
    """Public, leak-safe per-country readiness state (E1).

    Italy is ``available``; FR/BE/MA/TN are ``official_guided_path``.
    Contains no internal review detail (no hashes, paths, reviewer names, review
    notes, raw legal text or status slugs) — only the public projection.
    """
    return JsonResponse(
        {"countries": public_country_readiness()},
        json_dumps_params={"ensure_ascii": False},
    )


# P24: a direct, premium card identity per case-type family. Returns
# (badge, tone, description). Calculable families read as an estimate
# (never a generic "assisted path"); the rest get a precise pre-check /
# guided / applicable-law label. Each family carries its OWN one-line
# description so the hub no longer repeats a single generic blurb on
# every card. Badge msgids reuse the shared labels in public_pages.
# tone: "ok" (green) for a real calculation, "gold" for a documental /
# guided / cross-border path.
def _case_card_status(case_value: str):
    from django.utils.translation import gettext_lazy as _

    cv = (case_value or "").lower()
    if cv.startswith("road_accident"):
        return (
            _("Estimate based on official sources"),
            "ok",
            _("Indicative estimate of bodily injury on the official national tables, with its sources and assumptions."),
        )
    if cv.startswith("medical"):
        return (
            _("Official table-based biological damage estimate"),
            "ok",
            _("A tabular biological-damage estimate when the injury is quantified medico-legally — it does not rule on fault."),
        )
    if cv == "insurance_offer":
        return (
            _("Comparison based on official sources"),
            "ok",
            _("Measures a settlement offer against the official tabular estimate and shows the deviation."),
        )
    if cv == "work_injury":
        return (
            # Short badge (matches the page legend); the detail is in the line below.
            _("Documental pre-check"),
            "gold",
            _("We identify the official INAIL source and list the records your file needs before any assessment."),
        )
    if cv == "parental_loss":
        return (
            _("Guided assessment"),
            "gold",
            _("A guided reading of the loss-of-relationship damage, parameter by parameter, on the facts of the case."),
        )
    if cv == "death_compensation":
        return (
            _("Documental verification"),
            "gold",
            _("Documental verification of the file and the heirs before the Studio frames a loss-of-life claim."),
        )
    if cv in ("patrimonial_damage", "product_liability"):
        return (
            _("Documental verification"),
            "gold",
            _("Documental verification of income and economic losses before a patrimonial claim is framed."),
        )
    if cv == "inheritance_basic":
        return (
            _("Estimate based on official sources"),
            "ok",
            _("Indicative calculation of the statutory shares on the applicable succession rules."),
        )
    if "inheritance" in cv:
        return (
            _("Applicable-law framing"),
            "gold",
            _("Applicable-law framing: which jurisdiction and which law govern a cross-border estate."),
        )
    return (
        _("Assisted path based on official sources"),
        "gold",
        _("An assisted pathway on official sources: the Studio reviews the file and proposes the next step."),
    )


# P26: the short "what data you'll provide" hint per case-type family — reuses
# the guided-router input strings where they overlap so nothing is re-translated.
def _case_data_required(case_value: str):
    from django.utils.translation import gettext_lazy as _

    cv = (case_value or "").lower()
    if cv.startswith("road_accident"):
        return _("Injury percentage and accident details")
    if cv.startswith("medical"):
        return _("Medical-legal impairment percentage")
    if cv == "work_injury":
        return _("Event date, impairment and documents")
    if cv == "death_compensation":
        return _("Relationship, cause of death and documents")
    if cv == "parental_loss":
        return _("Relationship, cohabitation and liability")
    if cv == "patrimonial_damage":
        return _("Documentable income and economic loss")
    if cv == "inheritance_basic":
        return _("Heirs and statutory shares")
    if "inheritance" in cv:
        return _("Countries involved and the assets")
    return _("The facts of the case and the documents")


# P26: thematic grouping so the case-types hub reads as a navigator, not a flat
# grid. (group_label, group_intro, ordered case-type values).
def _case_groups():
    from django.utils.translation import gettext_lazy as _

    return (
        (_("Personal injury"),
         _("Road injuries and healthcare liability, estimated on the official tables."),
         ["road_accident_bodily_injury", "medical_malpractice"]),
        (_("Workplace"),
         _("Workplace injury and occupational disease on the INAIL sources."),
         ["work_injury"]),
        (_("Family and bereavement"),
         _("Loss of a relative and loss-of-relationship damage, handled with care."),
         ["death_compensation", "parental_loss"]),
        (_("Economic damage"),
         _("Income and economic losses, verified against the documents."),
         ["patrimonial_damage"]),
        (_("Inheritance"),
         _("Statutory shares, reserved portion and international successions."),
         ["inheritance_basic", "international_inheritance"]),
    )


@require_GET
def case_types(request):
    from apps.core.public_labels import humanize as humanize_case

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
        card_badge, card_tone, card_description = _case_card_status(case_type.value)
        case_types_view.append(
            {
                "code": case_type.value,
                "label": case_type.label,
                # P17: the public never sees the raw enum code — humanise it.
                "display_label": humanize_case(case_type.value),
                "available": registered and not all_scaffold,
                "scaffold_only": all_scaffold,
                "public_status": get_country_public_status(rep_country, case_type.value),
                # P24: a direct, non-repetitive card identity — calculable
                # families read as an estimate (never a generic "assisted
                # path"), and each card carries its own one-line description
                # instead of a single shared status blurb.
                "card_badge": card_badge,
                "card_tone": card_tone,
                "card_description": card_description,
                # P26: a short "what you'll provide" hint for the navigator card.
                "data_required": _case_data_required(case_type.value),
            }
        )
    # F-product-4-case-type-landings: surface the slug for each
    # CaseType code if a per-case-type landing exists, so the hub
    # cards can link to the deep page. Data-driven from
    # `apps.core.case_type_landings.LANDINGS`.
    from apps.core.case_type_landings import LANDINGS as _LANDINGS

    landings_by_code: dict[str, str] = {}
    for landing in _LANDINGS:
        # First landing wins per code — for codes with multiple
        # landings (e.g. road_accident has both `road-accident` and
        # `bodily-injury`), the hub links to the more general one
        # which is declared first.
        landings_by_code.setdefault(landing.case_type_code, landing.slug)
    for entry in case_types_view:
        entry["landing_slug"] = landings_by_code.get(entry["code"], "")

    # P26: assemble the thematic navigator groups from the built cards.
    by_code = {e["code"]: e for e in case_types_view}
    case_groups = []
    for label, intro, codes in _case_groups():
        cards = [by_code[c] for c in codes if c in by_code]
        if cards:
            case_groups.append({"label": label, "intro": intro, "cases": cards})

    return render(
        request,
        "public/case_types.html",
        {
            "case_types": case_types_view,
            "case_groups": case_groups,
            # P32: dedicated topical hero for the case-types hub.
            "pexels_image": _pexels_hero(request, "case_types_hero"),
            # F-product-4: surface the full landings list so the hub
            # can also show the "profile-style" landings (foreigners
            # in Italy, cross-border cases, insurance offer review)
            # that don't map 1:1 to a CaseType code.
            "extra_landings": [
                landing
                for landing in _LANDINGS
                if landing.case_type_code in {"", "generic_legal_assessment"}
                or landing.slug not in landings_by_code.values()
            ],
        },
    )


@require_GET
def case_type_landing(request, slug):
    """F-product-4-case-type-landings: per-case-type landing page.

    Looks up the slug in `apps.core.case_type_landings.LANDINGS`. If
    unknown, returns 404. Renders a single shared template with the
    landing's content. The page is public, indexable, and carries
    hreflang via the global context processor allowlist.
    """
    from django.http import Http404

    from apps.core.case_type_landings import get_landing

    landing = get_landing(slug)
    if landing is None:
        raise Http404("Unknown case-type landing.")
    return render(
        request,
        "public/case_type_landing.html",
        {
            "landing": landing,
            # P32: per-slug slot if present, else the shared case-types hero
            # (no per-case-type landing should ship heroless).
            "pexels_image": _pexels_hero(request, f"case_type_{slug}")
            or _pexels_hero(request, "case_types_hero"),
        },
    )


# ---------------------------------------------------------------------------
# P29 — Official source library + smart search
# ---------------------------------------------------------------------------
# Public, human filter labels (no slug). Category labels reuse humanize().
_SOURCE_CATEGORY_LABELS = {
    "road_accident": _("Road accident"),
    "insurance_offer": _("Insurance offer"),
    "medical": _("Medical liability"),
    "work_injury": _("Workplace injury"),
    "loss": _("Loss of a relative"),
    "death": _("Loss of a relative"),
    "patrimonial": _("Economic damage"),
    "product": _("Defective product"),
    "inheritance": _("Inheritance"),
    "cross_border": _("Cross-border"),
}
_SOURCE_COUNTRY_LABELS = {
    "IT": _("Italy"), "FR": _("France"), "BE": _("Belgium"),
    "MA": _("Morocco"), "TN": _("Tunisia"), "EU": _("European Union"),
}


@require_GET
def sources(request):
    """Public official-source library with country / category / type / use filters."""
    from apps.core import official_sources as official
    from apps.core.seo import build_canonical_url

    country = request.GET.get("country", "").strip()
    category = request.GET.get("category", "").strip()
    source_type = request.GET.get("type", "").strip()
    unlock = request.GET.get("use", "").strip()

    results = official.filter_sources(
        country=country, category=category, source_type=source_type, unlock=unlock
    )
    facets = official.facets()
    return render(
        request,
        "public/sources.html",
        {
            "sources": results,
            "total": len(official.all_sources()),
            "facets": facets,
            "active": {"country": country, "category": category,
                       "type": source_type, "use": unlock},
            "country_labels": _SOURCE_COUNTRY_LABELS,
            "category_labels": _SOURCE_CATEGORY_LABELS,
            "type_labels": official.SOURCE_TYPE_LABEL,
            "use_labels": official.UNLOCK_LABEL,
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "sources_hero"),
            # P39: body image for the "official documents, explained simply" block.
            "img_library": _pexels_hero(request, "sources_body"),
        },
    )


@require_GET
def source_detail(request, slug):
    """Detail page for a single official source, with related platform links."""
    from django.http import Http404

    from apps.core import official_sources as official
    from apps.core.seo import build_canonical_url

    source = official.get_source(slug)
    if source is None:
        raise Http404("Unknown source.")

    # Related platform links derived from the source's categories/country.
    related = []
    if "road_accident" in source.categories and source.country == "IT":
        related.append((_("Open the road-accident estimate"),
                        "cases:wizard_italy_road_accident", {}))
    if "medical" in source.categories:
        related.append((_("Open the medical estimate"), "cases:wizard_italy_medical", {}))
    _precheck_for = {"MA": "morocco-road-accident", "TN": "tunisia-road-accident"}
    if source.country in _precheck_for and "road_accident" in source.categories:
        related.append((_("Open the documental pre-check"), "core:precheck",
                        {"slug": _precheck_for[source.country]}))
    if "work_injury" in source.categories:
        related.append((_("Open the INAIL pre-check"), "core:precheck", {"slug": "inail"}))
    return render(
        request,
        "public/source_detail.html",
        {
            "source": source,
            "related": related,
            "country_labels": _SOURCE_COUNTRY_LABELS,
            "category_labels": _SOURCE_CATEGORY_LABELS,
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "methodology_hero"),
            # P39: visual document panel for the source sheet.
            "img_document": _pexels_hero(request, "source_document"),
        },
    )


@require_GET
def search(request):
    """Smart public search over estimates, pre-checks, countries, sources and pages."""
    from apps.core import search_index
    from apps.core.seo import build_canonical_url

    query = request.GET.get("q", "").strip()
    results = search_index.search(query) if query else []
    return render(
        request,
        "public/search.html",
        {
            "query": query,
            "results": results,
            "canonical_url": build_canonical_url(request),
        },
    )


# ---------------------------------------------------------------------------
# P30 — intelligent document intake (stateless, local-first, OpenAI-optional)
# ---------------------------------------------------------------------------
@require_GET
def documents(request):
    """Landing for the document-intelligence flow."""
    from django.conf import settings

    from apps.core.seo import build_canonical_url

    return render(
        request,
        "public/documents.html",
        {
            "canonical_url": build_canonical_url(request),
            "ai_enabled": settings.OPENAI_DOCUMENT_AI_ENABLED,
            "pexels_image": _pexels_hero(request, "documents_hero"),
        },
    )


def _file_kind(mime: str, name: str) -> str:
    """Coarse preview kind: 'image' or 'pdf' (no file is stored)."""
    name = (name or "").lower()
    if (mime or "").startswith("image/") or name.endswith((".jpg", ".jpeg", ".png", ".webp")):
        return "image"
    return "pdf"


@require_http_methods(["GET", "POST"])
def documents_upload(request):
    """Secure, stateless multi-document intake. Files are never persisted."""
    from django.conf import settings

    from apps.core.document_ai import aggregate_dossier, analyze_document
    from apps.core.document_forms import DocumentUploadForm
    from apps.core.rate_limit import public_post_rate_limit
    from apps.core.seo import build_canonical_url

    files_meta: list[dict] = []
    dossier = None
    if request.method == "POST":
        # Rate-limit the public POST (same guard as the contact form).
        limited = public_post_rate_limit(lambda r: None)(request)
        if limited is not None:
            return limited
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            if form.is_likely_bot:
                form = DocumentUploadForm()  # drop silently
            else:
                country = form.cleaned_data.get("country", "")
                category = form.cleaned_data.get("category", "")
                language = form.cleaned_data.get("language", "")
                for f in form.cleaned_data["document"]:
                    filename = DocumentUploadForm.safe_filename(f.name)
                    mime = getattr(f, "content_type", "") or ""
                    analysis = analyze_document(
                        filename=filename, mime=mime, size=f.size,
                        country=country, category=category,
                    )
                    if language and not analysis.language:
                        from dataclasses import replace
                        analysis = replace(analysis, language=language)
                    files_meta.append({
                        "filename": filename,
                        "size": f.size,
                        "kind": _file_kind(mime, filename),
                        "analysis": analysis,
                    })
                    # The uploaded file is intentionally NOT stored anywhere.
                dossier = aggregate_dossier([m["analysis"] for m in files_meta])
    else:
        form = DocumentUploadForm()

    return render(
        request,
        "public/documents_upload.html",
        {
            "form": form,
            "files_meta": files_meta,
            "dossier": dossier,
            "ai_enabled": settings.OPENAI_DOCUMENT_AI_ENABLED,
            "max_mb": settings.DOCUMENT_INTAKE_MAX_UPLOAD_MB,
            "max_files": settings.DOCUMENT_INTAKE_MAX_FILES,
            "canonical_url": build_canonical_url(request),
            "pexels_image": _pexels_hero(request, "documents_hero"),
            # P39: report-style side panel for the human dossier result.
            "img_report": _pexels_hero(request, "result_report"),
        },
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
