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

F-sources-italy estende il resolver con due garanzie:
- `calculation_date` opzionale per simulazioni datate (es. incidente
  avvenuto nel 2024 calcolato oggi sotto la normativa vigente nel 2024);
- fallback country che, se non passato esplicitamente, è derivato da
  `Jurisdiction.country` su DB invece che da uno split del codice.
  Questo evita ipotesi sbagliate quando i codici interni non rispettano
  il pattern `XX-...` (es. giurisdizioni regionali con codici composti).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from apps.legal_sources.models import LegalSource


def find_approved_sources(
    *,
    jurisdiction_code: str | None = None,
    country_code: str | None = None,
    source_types: Sequence[str] | None = None,
    calculation_date: date | None = None,
    fallback_to_country: bool = True,
) -> list[LegalSource]:
    """
    Restituisci le fonti approved per una jurisdiction (o country in fallback).

    - se `jurisdiction_code` è fornito, filtra per quella jurisdiction;
    - se non trova nulla e `fallback_to_country` è True, ritenta a livello
      di paese: usa `country_code` esplicito o, in mancanza, lo deriva da
      `Jurisdiction.country` su DB. Le fonti taggate solo a `country`
      (senza giurisdizione specifica) restano usabili come riferimento
      nazionale;
    - se `source_types` è fornito, filtra per quei tipi;
    - se `calculation_date` è fornita, le fonti sono valutate a quella
      data (esclude `effective_date` futura e `valid_until` precedente).
      Default: oggi.
    """

    base = LegalSource.objects.approved(reference_date=calculation_date)
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

    if not fallback_to_country:
        return []

    resolved_country_code = country_code or _country_code_from_jurisdiction(jurisdiction_code)
    if resolved_country_code:
        return list(
            base.by_country(resolved_country_code)
            .select_related("country", "jurisdiction", "language")
            .order_by("-publication_date")
        )

    return []


def _country_code_from_jurisdiction(jurisdiction_code: str | None) -> str | None:
    """
    Deriva il codice paese dalla `Jurisdiction` registrata in DB.

    Preferiamo questo lookup allo split `IT-NATIONAL → IT`: in scenari con
    giurisdizioni sub-nazionali (`IT-LOM`, `BE-FLA`) lo split manuale
    funziona, ma è una convenzione interna fragile. Il DB resta la
    fonte autoritativa: se la `Jurisdiction` non esiste, restituiamo None
    e il calling site deve trattare il caso come "no fallback".
    """
    if not jurisdiction_code:
        return None
    try:
        from apps.jurisdictions.models import Jurisdiction

        jurisdiction = (
            Jurisdiction.objects.select_related("country").filter(code=jurisdiction_code).first()
        )
        if jurisdiction and jurisdiction.country_id:
            return jurisdiction.country.code
    except Exception:  # pragma: no cover — solo se app non pronta
        return None
    return None
