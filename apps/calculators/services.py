"""
Source resolver per il motore di calcolo.

Unico punto di accesso a `LegalSource.objects.approved()` lato calculator.
Centralizzare qui la query ha tre vantaggi:

1. la regola "solo fonti approved alimentano calcoli pubblici" è
   applicata in un solo posto (REQ-3);
2. il filtro per jurisdiction → fallback country è coerente fra tutti
   i calculator;
3. è banale stub-bare nei test.

NESSUN calculator deve interrogare `LegalSource.objects` direttamente:
deve passare di qui.
"""

from __future__ import annotations

from collections.abc import Sequence

from apps.legal_sources.models import LegalSource


def find_approved_sources(
    *,
    jurisdiction_code: str | None = None,
    country_code: str | None = None,
    source_types: Sequence[str] | None = None,
) -> list[LegalSource]:
    """
    Restituisci le fonti approved per una jurisdiction (o country in fallback).

    - se `jurisdiction_code` è fornito, filtra per quella jurisdiction;
    - se non trova nulla e `country_code` è fornito, ritenta a livello
      di paese (`legal_sources` taggate solo a `country` senza giurisdizione
      specifica restano usabili come riferimento nazionale);
    - se `source_types` è fornito, filtra per quei tipi.

    Le fonti scadute (`valid_until` nel passato) sono già escluse dal
    manager `.approved()`.
    """

    base = LegalSource.objects.approved()
    if source_types:
        base = base.filter(source_type__in=list(source_types))

    if jurisdiction_code:
        narrow = base.by_jurisdiction(jurisdiction_code)
        if narrow.exists():
            return list(
                narrow.select_related("country", "jurisdiction", "language").order_by(
                    "-publication_date"
                )
            )

    if country_code:
        return list(
            base.by_country(country_code)
            .select_related("country", "jurisdiction", "language")
            .order_by("-publication_date")
        )

    return []
