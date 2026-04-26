"""
Context processor `site_context`.

Espone ai template:
- `SITE_NAME` (settings)
- `SITE_DOMAIN` (settings)
- `PARENT_SITE_URL` (settings, sito madre istituzionale)
- `AVAILABLE_LANGUAGES` lista di tuple (code, label)
- `CURRENT_LANGUAGE` codice attivo
- `IS_RTL` boolean (True solo per `ar`)
- `RTL_LANGUAGES` set di codici con direzione RTL

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
