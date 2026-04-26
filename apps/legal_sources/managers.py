"""
Manager e queryset per LegalSource.

Regola d'oro del progetto: solo le fonti `APPROVED` possono essere
consumate dai calcolatori pubblici. Il filtro `.approved()` è il punto
d'ingresso unico per quel percorso ed è responsabilità di tutti i
calcolatori usarlo invece di `.objects`.
"""

from django.db import models

from .enums import SourceStatus


class LegalSourceQuerySet(models.QuerySet):
    def approved(self) -> "LegalSourceQuerySet":
        """Solo fonti approvate, attive e non scadute alla data corrente."""
        from django.utils import timezone

        today = timezone.now().date()
        return self.filter(status=SourceStatus.APPROVED).filter(
            models.Q(valid_until__isnull=True) | models.Q(valid_until__gte=today)
        )

    def by_country(self, country_code: str) -> "LegalSourceQuerySet":
        return self.filter(country__code=country_code.upper())

    def by_jurisdiction(self, jurisdiction_code: str) -> "LegalSourceQuerySet":
        return self.filter(jurisdiction__code=jurisdiction_code.upper())


class LegalSourceManager(models.Manager.from_queryset(LegalSourceQuerySet)):
    """Manager pubblico di LegalSource."""

    def approved(self) -> LegalSourceQuerySet:
        return self.get_queryset().approved()
