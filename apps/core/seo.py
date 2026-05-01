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

from pathlib import Path
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


# ---------------------------------------------------------------------------
# Open Graph + Twitter Card metadata (pass 4)
# ---------------------------------------------------------------------------

# Mappa lingua app → tag `og:locale` standard.
# I tag OG vogliono il formato POSIX `lang_TERRITORY` (es. `it_IT`).
# Quando il territory non è ovvio (en, ar) scegliamo la variante più
# comunemente usata sul web (`en_US`, `ar_AR`).
_OG_LOCALE_BY_LANG: dict[str, str] = {
    "it": "it_IT",
    "fr": "fr_FR",
    "en": "en_US",
    "ar": "ar_AR",
}


def _og_locale(lang: str) -> str:
    """Codice OG-locale per una lingua app, fallback `<lang>_<LANG>`."""
    return _OG_LOCALE_BY_LANG.get(lang, f"{lang.lower()}_{lang.upper()}")


# ---------------------------------------------------------------------------
# OG image picker (pass og-images-pass1)
# ---------------------------------------------------------------------------

# Map: country_code (lowercase) → static slug per il PNG OG.
# `country_code` proviene dal context view (`"italy"`, `"france"`, …).
_COUNTRY_TO_OG_SLUG = {
    "italy": "italy",
    "france": "france",
    "belgium": "belgium",
    "morocco": "morocco",
    "tunisia": "tunisia",
}


def _resolve_og_image_static_path(country_code: str | None) -> str:
    """
    Sceglie il path STATIC dell'immagine OG. Strategia:

    1. Se `country_code` mappato e `static/img/og/og-{slug}.png` esiste
       → usalo (immagine country-specific generata da
       `scripts/generate_og_images.py`).
    2. Altrimenti, se `static/img/og/og-country-default.png` esiste →
       fallback raster default.
    3. Altrimenti fallback finale all'SVG `static/img/og-country-default.svg`
       (pass 4) — sempre presente.
    """
    base_dir = Path(getattr(settings, "BASE_DIR", "."))
    static_dir = base_dir / "static"
    if country_code:
        slug = _COUNTRY_TO_OG_SLUG.get(country_code.lower())
        if slug:
            country_png = static_dir / "img" / "og" / f"og-{slug}.png"
            if country_png.exists():
                return f"img/og/og-{slug}.png"
    default_png = static_dir / "img" / "og" / "og-country-default.png"
    if default_png.exists():
        return "img/og/og-country-default.png"
    return "img/og-country-default.svg"


def _is_png(static_path: str) -> bool:
    return static_path.lower().endswith(".png")


def build_open_graph_metadata(
    request: Any,
    *,
    title: str,
    description: str,
    canonical_url: str,
    image_static_path: str | None = None,
    country_code: str | None = None,
) -> dict[str, Any]:
    """
    Costruisce i metadati Open Graph + Twitter Card per la pagina.

    Parametri:
    - `title`, `description`: stringhe già localizzate dal chiamante
      (la view passa il title/description usati in <title> e <meta
      name="description"> per coerenza con quello che gli scraper
      OG vedrebbero comunque).
    - `canonical_url`: URL canonico assoluto (pass 2). Va anche in
      `og:url` per evitare scraping della versione localizzata
      sbagliata.
    - `image_static_path`: path relativo dentro `STATICFILES_DIRS`.
      Se None (default), `_resolve_og_image_static_path(country_code)`
      sceglie automaticamente la PNG country-specific (pass og-images-1)
      o il fallback default. Caller può forzare un path esplicito (es.
      override Pexels in `_render_country_landing`).
    - `country_code`: usato per il picker OG image. È in lowercase
      come nel context (`"italy"`, `"france"`, …).

    Output dict:
    ```
    {
      "og": [{"property": "og:title", "content": "..."}, ...],
      "twitter": [{"name": "twitter:card", "content": "..."}, ...],
    }
    ```
    Il template itera direttamente le due liste e renderizza i tag.
    Quando l'immagine è PNG, vengono emessi anche `og:image:width=1200`
    e `og:image:height=630` (Facebook/X best practice).
    """
    from django.templatetags.static import static

    current = (translation.get_language() or _default_language()).lower()
    other_langs = [code for code in _supported_languages() if code != current]

    if image_static_path is None:
        image_static_path = _resolve_og_image_static_path(country_code)
    image_url = request.build_absolute_uri(static(image_static_path))

    site_name = getattr(settings, "SITE_NAME", "Studio Legale Internazionale Badrane")

    og_tags: list[dict[str, str]] = [
        {"property": "og:type", "content": "website"},
        {"property": "og:site_name", "content": site_name},
        {"property": "og:title", "content": title},
        {"property": "og:description", "content": description},
        {"property": "og:url", "content": canonical_url},
        {"property": "og:image", "content": image_url},
        {"property": "og:image:alt", "content": title},
        {"property": "og:locale", "content": _og_locale(current)},
    ]
    if _is_png(image_static_path):
        # Pass og-images-pass1: tutte le PNG sono 1200×630.
        og_tags.append({"property": "og:image:width", "content": "1200"})
        og_tags.append({"property": "og:image:height", "content": "630"})
    for other in other_langs:
        og_tags.append(
            {"property": "og:locale:alternate", "content": _og_locale(other)},
        )

    twitter_tags: list[dict[str, str]] = [
        {"name": "twitter:card", "content": "summary_large_image"},
        {"name": "twitter:title", "content": title},
        {"name": "twitter:description", "content": description},
        {"name": "twitter:image", "content": image_url},
        {"name": "twitter:image:alt", "content": title},
    ]

    return {"og": og_tags, "twitter": twitter_tags}
