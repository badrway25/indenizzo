"""
SEO helpers — canonical + hreflang alternates.

Iter: F-product-country-landing-pass2-canonical-hreflang.

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
