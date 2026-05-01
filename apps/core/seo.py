"""
SEO helpers — canonical, hreflang alternates, JSON-LD LegalService.

Iter:
- F-product-country-landing-pass2-canonical-hreflang (canonical, hreflang).
- F-product-country-landing-pass3-sitemap-schema-ux-live (JSON-LD).

Coerente col setup `i18n_patterns(prefix_default_language=False)`
di `config/urls.py`: la lingua default (`LANGUAGE_CODE=it`) NON ha
prefisso URL; le altre lingue (`fr`, `en`, `ar`) hanno prefisso
`/<lang>/`.

Funzioni pure, nessuna dipendenza DB:
- `build_canonical_url(request) -> str`
  URL assoluto del request corrente. Self-reference (Google rule:
  ogni versione localizzata canonicalizza se stessa, non la
  default).
- `build_hreflang_alternates(request, view_name, kwargs=None) -> list[dict]`
  Una entry per lingua + `x-default`. Ogni entry: `{"lang", "href"}`.
- `build_legal_service_json_ld(country_code, canonical_url, language_code) -> dict`
  Schema.org `LegalService` per le 5 country landing. NON include
  prezzi, rating, recensioni, garanzie: il prodotto è un servizio
  legale informativo, e qualsiasi pricing/rating sarebbe non
  validato e potenzialmente fuorviante.

Niente dominio hardcoded: usa `request.build_absolute_uri()`.
"""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.urls import reverse
from django.utils import translation


def _supported_languages() -> list[str]:
    """Codici lingua supportati (da settings.LANGUAGES)."""
    return [code for code, _ in getattr(settings, "LANGUAGES", [("it", "Italiano")])]


def _default_language() -> str:
    """Codice lingua default (da settings.LANGUAGE_CODE)."""
    return getattr(settings, "LANGUAGE_CODE", "it")


def build_canonical_url(request: Any) -> str:
    """
    URL canonico assoluto del request corrente.

    Self-reference: la versione `/fr/countries/france/` canonicalizza
    se stessa, non `/countries/france/`. Questo è il pattern
    raccomandato da Google quando si usa hreflang.
    """
    return request.build_absolute_uri(request.path)


def build_hreflang_alternates(
    request: Any,
    view_name: str,
    kwargs: dict[str, Any] | None = None,
) -> list[dict[str, str]]:
    """
    Lista di alternates `[{"lang", "href"}, ...]` per il view dato.

    Si usa `translation.override(lang)` + `reverse(view_name)` per
    ottenere il path corretto in ciascuna lingua, rispettando
    `prefix_default_language=False` (la lingua default non ha
    prefisso, le altre sì).

    Aggiunge `x-default` puntando alla versione nella lingua default
    (per signal a Google: "se non sai quale variante mostrare, usa
    questa").

    Argomenti:
    - `view_name`: nome dell'URL (es. `core:country_italy`).
    - `kwargs`: kwargs del path (None se vuoto).

    Mai solleva: se un reverse fallisce per una lingua specifica,
    quella entry viene saltata. La pagina resta servibile.
    """
    kwargs = kwargs or {}
    langs = _supported_languages()
    default_lang = _default_language()

    alternates: list[dict[str, str]] = []
    seen: set[str] = set()
    default_href: str | None = None

    for lang in langs:
        try:
            with translation.override(lang):
                path = reverse(view_name, kwargs=kwargs)
        except Exception:
            continue
        href = request.build_absolute_uri(path)
        if href in seen:
            continue
        seen.add(href)
        alternates.append({"lang": lang, "href": href})
        if lang == default_lang and default_href is None:
            default_href = href

    if default_href is not None:
        alternates.append({"lang": "x-default", "href": default_href})
    return alternates


# ---------------------------------------------------------------------------
# JSON-LD LegalService (pass 3)
# ---------------------------------------------------------------------------

# Mappa country_code → (areaServed, serviceType).
#
# `serviceType` riflette ESATTAMENTE quello che il prodotto fa oggi, non
# claim aspirational:
# - Italia: "Road accident bodily injury compensation simulation" — il
#   calcolatore è attivo con TUN 2025 approvato.
# - Francia/Belgio: "Road accident bodily injury legal review" — il
#   calcolatore è scaffold; lo Studio fa una review manuale.
# - Marocco/Tunisia: "International inheritance legal review" — niente
#   calcolo automatico, lo Studio analizza il caso.
#
# `areaServed` resta il country ISO-3166 (Italy, France, Belgium,
# Morocco, Tunisia) per essere coerente con `Schema.org LegalService`
# e con l'identità multipaese del Studio.
_COUNTRY_LEGAL_SERVICE: dict[str, dict[str, str]] = {
    "italy": {
        "area_served": "Italy",
        "service_type": "Road accident bodily injury compensation simulation",
    },
    "france": {
        "area_served": "France",
        "service_type": "Road accident bodily injury legal review",
    },
    "belgium": {
        "area_served": "Belgium",
        "service_type": "Road accident bodily injury legal review",
    },
    "morocco": {
        "area_served": "Morocco",
        "service_type": "International inheritance legal review",
    },
    "tunisia": {
        "area_served": "Tunisia",
        "service_type": "International inheritance legal review",
    },
}


def build_legal_service_json_ld(
    country_code: str,
    canonical_url: str,
    language_code: str,
) -> dict[str, Any]:
    """
    JSON-LD Schema.org `LegalService` per la landing paese.

    Volutamente NON include:
    - `aggregateRating` / `review` (nessuna review pubblica validata);
    - `priceRange` / `offers` (servizio legale, non e-commerce);
    - `sameAs` (rinviamo al sito madre solo via link nel template,
      non come signal automatico).

    Il documento è un dict serializzabile JSON (no oggetti Django).
    Il template fa `{{ json_ld_legal_service|json_script }}` per
    iniettarlo come `<script type="application/json">`.
    """
    spec = _COUNTRY_LEGAL_SERVICE.get(country_code)
    if spec is None:
        raise ValueError(f"Unknown country_code for JSON-LD: {country_code!r}")
    return {
        "@context": "https://schema.org",
        "@type": "LegalService",
        "name": "Studio Legale Internazionale Badrane",
        "areaServed": spec["area_served"],
        "serviceType": spec["service_type"],
        "url": canonical_url,
        "inLanguage": language_code,
    }
