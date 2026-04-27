"""
Manager e queryset per LegalSource.

Regola d'oro del progetto: solo le fonti `APPROVED` possono essere
consumate dai calcolatori pubblici. Il filtro `.approved()` è il punto
d'ingresso unico per quel percorso ed è responsabilità di tutti i
calcolatori usarlo invece di `.objects`.

Il filtro temporale è doppio:
- `valid_until` nel passato → la fonte è scaduta, esclusa;
- `effective_date` nel futuro → la fonte non è ancora vigente,
  esclusa anche se `APPROVED`.

Il parametro `reference_date` permette di calcolare al "momento del
fatto" e non al momento della query: indispensabile per simulazioni
basate su una data di evento (es. incidente avvenuto nel 2024 calcolato
oggi sotto la normativa allora in vigore).
"""

from __future__ import annotations

from datetime import date as _date

from django.db import models

from .enums import SourceStatus


class LegalSourceQuerySet(models.QuerySet):
    def approved(self, reference_date: _date | None = None) -> LegalSourceQuerySet:
        """
        Solo fonti approvate, vigenti e non scadute alla data di riferimento.

        - se `reference_date` è omessa, usa la data corrente (UTC):
          comportamento precedente compatibile;
        - esclude fonti con `effective_date` futura rispetto a
          `reference_date` (norma non ancora in vigore);
        - esclude fonti con `valid_until` < `reference_date` (norma
          scaduta).
        """
        from django.utils import timezone

        ref = reference_date or timezone.now().date()
        return (
            self.filter(status=SourceStatus.APPROVED)
            .filter(models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=ref))
            .filter(models.Q(effective_date__isnull=True) | models.Q(effective_date__lte=ref))
        )

    def by_country(self, country_code: str) -> LegalSourceQuerySet:
        return self.filter(country__code=country_code.upper())

    def by_jurisdiction(self, jurisdiction_code: str) -> LegalSourceQuerySet:
        return self.filter(jurisdiction__code=jurisdiction_code.upper())


class LegalSourceManager(models.Manager.from_queryset(LegalSourceQuerySet)):
    """Manager pubblico di LegalSource."""

    def approved(self, reference_date: _date | None = None) -> LegalSourceQuerySet:
        return self.get_queryset().approved(reference_date=reference_date)
