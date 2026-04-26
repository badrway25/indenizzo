"""
Modelli `apps.cases` — persistenza delle simulazioni.

F5 — `Simulation` è il "ponte" architetturale: lega input utente,
giurisdizione, consenso GDPR, output del motore F4 e snapshot delle
fonti usate. È la fonte di verità per:

- il futuro report PDF (REQ-5);
- l'audit privacy (F3 `PrivacyAuditEvent` referenzia `cases.Simulation`);
- la dashboard staff;
- l'esportazione GDPR / cancellazione su richiesta.

Principi:
- `public_id` UUID è l'identificativo esposto verso l'esterno; il PK
  numerico resta interno (mai in URL pubblici);
- nulla di sensibile in `__str__` (può finire in log);
- `input_data`/`output_data` sono JSON; i contenuti effettivi sono
  governati dal contratto F4 (`CalculationResult.to_dict()`);
- `anonymized=True` indica che i dati personali sono stati rimossi:
  il record resta come traccia tecnica.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.calculators.enums import CalculationStatus, CaseType, ConfidenceLevel


class SimulationLocale(models.TextChoices):
    IT = "it", _("Italiano")
    FR = "fr", _("Français")
    EN = "en", _("English")
    AR = "ar", _("العربية")


class Simulation(models.Model):
    """Una singola esecuzione del motore di calcolo, persistita."""

    public_id = models.UUIDField(
        _("public id"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="simulations",
        verbose_name=_("user"),
        null=True,
        blank=True,
    )
    session_key = models.CharField(_("session key"), max_length=64, blank=True)

    jurisdiction = models.ForeignKey(
        "jurisdictions.Jurisdiction",
        on_delete=models.PROTECT,
        related_name="simulations",
        verbose_name=_("jurisdiction"),
        null=True,
        blank=True,
    )
    country = models.ForeignKey(
        "jurisdictions.Country",
        on_delete=models.PROTECT,
        related_name="simulations",
        verbose_name=_("country"),
        null=True,
        blank=True,
    )

    case_type = models.CharField(
        _("case type"),
        max_length=64,
        choices=CaseType.choices,
        db_index=True,
    )
    locale = models.CharField(
        _("locale"),
        max_length=4,
        choices=SimulationLocale.choices,
        default=SimulationLocale.IT,
    )

    input_data = models.JSONField(_("input data"), default=dict, blank=True)
    output_data = models.JSONField(_("output data"), default=dict, blank=True)
    sources_snapshot = models.JSONField(_("sources snapshot"), default=list, blank=True)

    status = models.CharField(
        _("status"),
        max_length=64,
        choices=CalculationStatus.choices,
        default=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION,
        db_index=True,
    )
    confidence = models.CharField(
        _("confidence"),
        max_length=16,
        choices=ConfidenceLevel.choices,
        default=ConfidenceLevel.LOW,
    )

    currency = models.CharField(_("currency"), max_length=3, blank=True)
    estimated_min = models.DecimalField(
        _("estimated min"),
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    estimated_mid = models.DecimalField(
        _("estimated mid"),
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )
    estimated_max = models.DecimalField(
        _("estimated max"),
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
    )

    consent_record = models.ForeignKey(
        "compliance.ConsentRecord",
        on_delete=models.SET_NULL,
        related_name="simulations",
        verbose_name=_("consent record"),
        null=True,
        blank=True,
    )

    ip_address = models.GenericIPAddressField(_("ip address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    source_path = models.CharField(_("source path"), max_length=512, blank=True)

    anonymized = models.BooleanField(_("anonymized"), default=False, db_index=True)
    anonymized_at = models.DateTimeField(_("anonymized at"), null=True, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("simulation")
        verbose_name_plural = _("simulations")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["jurisdiction", "case_type"]),
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self) -> str:
        # Niente PII: solo public_id e case_type.
        return f"sim:{self.public_id} [{self.case_type}]"


class SimulationEvent(models.Model):
    """
    Evento di lifecycle/audit di una `Simulation`. Append-only.

    Distinto da `PrivacyAuditEvent` (apps.compliance):
    - `SimulationEvent` è semantico al dominio (created, computed,
      anonymized, error) ed è leggibile dallo staff Studio;
    - `PrivacyAuditEvent` è privacy-ledger globale e cross-modello.

    Entrambi vengono scritti dal service layer in fase di `run_simulation`.
    """

    class EventType(models.TextChoices):
        CREATED = "created", _("Created")
        COMPUTED = "computed", _("Computed")
        ANONYMIZED = "anonymized", _("Anonymized")
        ERROR = "error", _("Error")
        OTHER = "other", _("Other")

    simulation = models.ForeignKey(
        Simulation,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("simulation"),
    )
    event_type = models.CharField(
        _("event type"),
        max_length=24,
        choices=EventType.choices,
    )
    message = models.CharField(_("message"), max_length=512, blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("simulation event")
        verbose_name_plural = _("simulation events")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["simulation", "event_type"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}@{self.simulation_id}"
