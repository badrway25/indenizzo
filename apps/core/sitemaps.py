"""
Sitemap dichiarativi per `/sitemap.xml`.

Iter: F-product-country-landing-pass3-sitemap-schema-ux-live.

Espone una sitemap singola con le 12 URL pubbliche statiche del
prodotto (home, countries index, 5 country landing, methodology,
privacy, disclaimer, case-types, wizard hub). Volutamente esclude:
- `/admin/`, `/staff/...` (back-office, no-index implicito);
- detail page lead/simulation (gestiti dietro login o con URL token);
- pagine wizard country-specific (sono gated dal wizard hub).

Nessuna logica DB: la lista è statica e il `Sitemap` framework di
Django costruisce gli URL via `reverse()`, così che il prefisso i18n
venga gestito coerentemente (la lingua default `it` non ha prefisso).

Le 5 country landing hanno priority 0.9 (più alta dello "0.8" del hub
`/countries/`) per segnalare ai motori di ricerca che sono le pagine
pivot del prodotto. Le pagine di policy (privacy, disclaimer) hanno
priority 0.3 — necessarie ma non SEO-critical.
"""

from __future__ import annotations

from django.contrib.sitemaps import Sitemap
from django.urls import reverse


class CountryLandingSitemap(Sitemap):
    """Sitemap delle 5 landing paese — priorità più alta del prodotto."""

    changefreq = "weekly"
    priority = 0.9
    protocol = "https"

    def items(self) -> list[str]:
        return [
            "core:country_italy",
            "core:country_france",
            "core:country_belgium",
            "core:country_morocco",
            "core:country_tunisia",
        ]

    def location(self, item: str) -> str:
        return reverse(item)


class StaticSitemap(Sitemap):
    """
    Sitemap delle pagine statiche pubbliche non-paese.

    `priority` è derivata dall'item: home/countries hub hanno 0.8,
    methodology/case-types/wizard hub 0.6, privacy/disclaimer 0.3.
    """

    changefreq = "monthly"
    protocol = "https"

    _PRIORITY = {
        "core:home": 0.8,
        "core:countries": 0.8,
        "core:methodology": 0.6,
        "core:case_types": 0.6,
        # P15: country × category guided router — navigational pivot.
        "core:guided_router": 0.7,
        # P29: official source library + smart search.
        "core:sources": 0.7,
        "core:search": 0.5,
        # P30: document intake landing.
        "core:documents": 0.7,
        "cases:wizard_start": 0.6,
        # Workstream-3 content pages.
        "core:how_it_works": 0.7,
        # P40: public documentation hub.
        "core:documentation": 0.6,
        "core:services": 0.7,
        "core:faq": 0.6,
        "core:about": 0.5,
        "core:community": 0.6,
        "core:privacy": 0.3,
        "core:disclaimer": 0.3,
    }

    def items(self) -> list[str]:
        return list(self._PRIORITY.keys())

    def location(self, item: str) -> str:
        return reverse(item)

    def priority(self, item: str) -> float:
        return self._PRIORITY.get(item, 0.5)


SITEMAPS = {
    "country_landings": CountryLandingSitemap,
    "static": StaticSitemap,
}
