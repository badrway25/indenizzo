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
    # F-p0-codice-3-footer: identificativi professionali Studio. Default
    # stringa vuota -> il template mostra `[da configurare prima del go-live]`.
    studio_identity = {
        "STUDIO_LEAD_LAWYER_NAME": getattr(settings, "STUDIO_LEAD_LAWYER_NAME", ""),
        "STUDIO_BAR_ASSOCIATION": getattr(settings, "STUDIO_BAR_ASSOCIATION", ""),
        "STUDIO_BAR_REGISTRATION_NUMBER": getattr(
            settings, "STUDIO_BAR_REGISTRATION_NUMBER", ""
        ),
        "STUDIO_VAT_NUMBER": getattr(settings, "STUDIO_VAT_NUMBER", ""),
        "STUDIO_TAX_CODE": getattr(settings, "STUDIO_TAX_CODE", ""),
        "STUDIO_PEC_EMAIL": getattr(settings, "STUDIO_PEC_EMAIL", ""),
        "STUDIO_PHYSICAL_ADDRESS": getattr(settings, "STUDIO_PHYSICAL_ADDRESS", ""),
        "STUDIO_PROFESSIONAL_INSURANCE_INSURER": getattr(
            settings, "STUDIO_PROFESSIONAL_INSURANCE_INSURER", ""
        ),
        "STUDIO_PROFESSIONAL_INSURANCE_POLICY": getattr(
            settings, "STUDIO_PROFESSIONAL_INSURANCE_POLICY", ""
        ),
        "STUDIO_PROFESSIONAL_INSURANCE_CEILING": getattr(
            settings, "STUDIO_PROFESSIONAL_INSURANCE_CEILING", ""
        ),
    }
    # F-p0-leg-3-consent: versioni del testo dei consensi (esposte al
    # template per il banner "working-copy" + per i campi denormalizzati
    # salvati in DB).
    consent_versions = {
        "PRIVACY_NOTICE_VERSION": getattr(
            settings, "PRIVACY_NOTICE_VERSION", "working-copy"
        ),
        "SPECIAL_CATEGORIES_NOTICE_VERSION": getattr(
            settings, "SPECIAL_CATEGORIES_NOTICE_VERSION", "working-copy"
        ),
    }
    # F-p0-leg-1-6-legal-pages: versioni e status delle pagine legali
    # pubbliche (privacy policy, disclaimer). Esposte al template per
    # rendere il badge di stato + il banner working-copy.
    legal_pages = {
        "PRIVACY_POLICY_VERSION": getattr(
            settings, "PRIVACY_POLICY_VERSION", "working-copy"
        ),
        "PRIVACY_POLICY_STATUS": getattr(
            settings, "PRIVACY_POLICY_STATUS", "working_copy"
        ),
        "PRIVACY_POLICY_SIGNED_AT": getattr(settings, "PRIVACY_POLICY_SIGNED_AT", ""),
        "DISCLAIMER_VERSION": getattr(
            settings, "DISCLAIMER_VERSION", "working-copy"
        ),
        "DISCLAIMER_STATUS": getattr(
            settings, "DISCLAIMER_STATUS", "working_copy"
        ),
        "DISCLAIMER_SIGNED_AT": getattr(settings, "DISCLAIMER_SIGNED_AT", ""),
        # F-p0-leg-2-mandate: stato del template mandato (versione +
        # status). Non e' PII: il template lo mostra come banner.
        "MANDATE_TEMPLATE_VERSION": getattr(
            settings, "MANDATE_TEMPLATE_VERSION", "working-copy"
        ),
        "MANDATE_TEMPLATE_STATUS": getattr(
            settings, "MANDATE_TEMPLATE_STATUS", "working_copy"
        ),
        "MANDATE_TEMPLATE_SIGNED_AT": getattr(
            settings, "MANDATE_TEMPLATE_SIGNED_AT", ""
        ),
    }
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
        **studio_identity,
        **consent_versions,
        **legal_pages,
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
        # Workstream-3 content pages (indexable, multilingual).
        "core:how_it_works",
        "core:services",
        "core:faq",
        "core:about",
        "core:community",
        # P40: public documentation hub (plain-language guides).
        "core:documentation",
        # F-product-4-case-type-landings: per-case-type SEO landings
        # under `/case-types/<slug>/`. Indexable, SEO-targeted,
        # multilingue. Stessa view, kwargs `slug` diverso per
        # landing — il builder accetta i kwargs e produce alternate
        # URLs coerenti.
        "core:case_type_landing",
        # P15: country × category guided router (static) + the guided
        # documental pre-check flows (slug-parametric, like case_type_landing).
        # Indicizzabili, multilingua — il builder accetta i kwargs `slug`.
        "core:guided_router",
        "core:precheck",
        # P29: official source library, per-source detail and smart search —
        # indexable, multilingual (source_detail/search take a slug/query).
        "core:sources",
        "core:source_detail",
        "core:search",
        # P30: document intake landing (the upload POST page stays out of the
        # hreflang allowlist — it is a stateless form, not indexable content).
        "core:documents",
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
