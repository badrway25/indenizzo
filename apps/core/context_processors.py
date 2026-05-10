"""
Context processors per `apps.core`.

`site_context` — espone settings basilari + flag i18n al template.
`seo_global_hreflang` — inietta `hreflang_alternates` per le pagine
pubbliche multilingua (allowlist esplicita), saltando pagine
noindex/private/parametriche con UUID. Iter:
F-p0-codice-2-hreflang-globale.

Niente lettura `.env`: usa i settings già caricati. Niente PII utente.
"""

from __future__ import annotations

from django.conf import settings
from django.utils.translation import get_language

# Lingue con scrittura right-to-left supportate dal progetto.
RTL_LANGUAGES = frozenset({"ar"})


def site_context(request) -> dict:
    current = (get_language() or settings.LANGUAGE_CODE or "it").lower()
    return {
        "SITE_NAME": getattr(settings, "SITE_NAME", "Studio Legale Badrane"),
        "SITE_DOMAIN": getattr(settings, "SITE_DOMAIN", ""),
        "PARENT_SITE_URL": getattr(
            settings,
            "PARENT_SITE_URL",
            "https://international.studiolegalebadrane.it/",
        ),
        "AVAILABLE_LANGUAGES": list(getattr(settings, "LANGUAGES", [])),
        "CURRENT_LANGUAGE": current,
        "IS_RTL": current in RTL_LANGUAGES,
        "RTL_LANGUAGES": list(RTL_LANGUAGES),
    }


# ---------------------------------------------------------------------------
# Global hreflang allowlist (F-p0-codice-2-hreflang-globale)
# ---------------------------------------------------------------------------
#
# Allowlist esplicita: solo le view nominate qui ricevono
# `hreflang_alternates` automatico dal context processor. Tutto il
# resto (admin, staff, reports, wizard result con UUID, contact
# thank-you) NON ne riceve. Filosofia: a default-deny, esattamente
# come un firewall — meglio una pagina senza hreflang che hreflang
# fuorvianti.
#
# Le 5 country landing sono incluse, ma le loro view passano gia'
# `hreflang_alternates` esplicitamente (`apps.core.views._render_country_landing`):
# in quel caso vince il context della view (Django: view-context >
# context-processor), quindi il context processor e' un no-op che
# non disturba ne' duplica.
#
# `crm:contact` e' indicizzabile dopo il pre-check 2 di
# P0-CODICE-2 (rimosso `noindex` da contact.html).
_GLOBAL_HREFLANG_VIEW_NAMES = frozenset(
    {
        # core/static
        "core:home",
        "core:methodology",
        "core:disclaimer",
        "core:privacy",
        "core:countries",
        "core:case_types",
        # country landings (gia' coperte dalla view, ma le includiamo
        # nella allowlist per documentare l'intento e per fallback)
        "core:country_italy",
        "core:country_france",
        "core:country_belgium",
        "core:country_morocco",
        "core:country_tunisia",
        # wizard hub: indicizzabile (pagina di scelta paese/case_type)
        "cases:wizard_start",
        # contact form (indicizzabile post-pre-check-2 P0-CODICE-2)
        "crm:contact",
        # NOTA: i 5 wizard pubblici (cases:wizard_italy_road_accident, ecc.)
        # sono `noindex, nofollow` per scelta esistente nei rispettivi
        # template — sono pagine di raccolta dati, non SEO-utili. La SEO
        # va sulla country landing equivalente. Volutamente esclusi.
        # Idem per `cases:wizard_result` (parametrico UUID) e
        # `crm:contact_thank_you` (post-submit).
    }
)


def seo_global_hreflang(request) -> dict:
    """
    Inietta `hreflang_alternates` nel template per le view pubbliche
    multilingua presenti nella allowlist `_GLOBAL_HREFLANG_VIEW_NAMES`.

    Pagine NON in allowlist (admin, staff, reports, wizard/result/<uuid>,
    contact/thank-you, qualsiasi non-pubblica) NON ricevono `hreflang`:
    il template eredita il `{% block hreflang %}` vuoto da base.html.

    Le view che passano gia' `hreflang_alternates` esplicitamente (es.
    `_render_country_landing` per le 5 country landings) NON vengono
    disturbate: il valore della view sovrascrive quello del context
    processor (Django context resolution).

    Mai solleva: in caso di errore (resolver_match assente, view non
    risolvibile in altre lingue), ritorna dict vuoto. La pagina resta
    sempre servibile.
    """
    match = getattr(request, "resolver_match", None)
    if match is None:
        return {}

    view_name = match.view_name
    if view_name not in _GLOBAL_HREFLANG_VIEW_NAMES:
        return {}

    # Lazy import per evitare import-time costs su pagine che non usano hreflang.
    from apps.core.seo import build_hreflang_alternates

    try:
        alternates = build_hreflang_alternates(
            request,
            view_name,
            kwargs=dict(match.kwargs) if match.kwargs else None,
        )
    except Exception:
        # `build_hreflang_alternates` e' gia' difensivo, ma assorbiamo
        # qualunque imprevisto per evitare di rompere il rendering di
        # una pagina pubblica per un signal SEO non critico.
        return {}

    return {"hreflang_alternates": alternates}
