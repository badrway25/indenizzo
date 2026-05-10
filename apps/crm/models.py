"""
Modelli CRM — pipeline lead Studio Legale Badrane.

F6 — `Lead` chiude il funnel "visitatore → simulazione → richiesta".
È il primo modello dove i dati personali utente entrano davvero in DB
(nome, email, telefono): GDPR-aware by design.

Principi:
- nessun PII nel `__str__` (può finire in log);
- `consent_record` FK puntuale alla `ConsentRecord` registrata al submit;
- niente `message` nei log (solo `public_id`);
- `LeadEvent` è append-only (lifecycle: created, contacted, qualified, ...).

Le retention reali (cancellazione automatica) saranno F11. Qui registriamo
solo lo stato e la pipeline.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.calculators.enums import CaseType


class LeadLanguage(models.TextChoices):
    IT = "it", _("Italiano")
    FR = "fr", _("Français")
    EN = "en", _("English")
    AR = "ar", _("العربية")


class LeadStatus(models.TextChoices):
    RECEIVED = "received", _("Received")
    CONTACTED = "contacted", _("Contacted")
    QUALIFIED = "qualified", _("Qualified")
    CONVERTED = "converted", _("Converted")
    REJECTED = "rejected", _("Rejected")
    ARCHIVED = "archived", _("Archived")


class LeadPriority(models.TextChoices):
    LOW = "low", _("Low")
    NORMAL = "normal", _("Normal")
    HIGH = "high", _("High")
    URGENT = "urgent", _("Urgent")


class Lead(models.Model):
    """Richiesta di valutazione legale entrata dal form pubblico."""

    public_id = models.UUIDField(
        _("public id"),
        default=uuid.uuid4,
        editable=False,
        unique=True,
    )

    simulation = models.ForeignKey(
        "cases.Simulation",
        on_delete=models.SET_NULL,
        related_name="leads",
        verbose_name=_("simulation"),
        null=True,
        blank=True,
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="leads",
        verbose_name=_("user"),
        null=True,
        blank=True,
    )
    session_key = models.CharField(_("session key"), max_length=64, blank=True)

    first_name = models.CharField(_("first name"), max_length=80)
    last_name = models.CharField(_("last name"), max_length=80)
    email = models.EmailField(_("email"))
    phone_number = models.CharField(_("phone number"), max_length=32, blank=True)

    preferred_language = models.CharField(
        _("preferred language"),
        max_length=4,
        choices=LeadLanguage.choices,
        default=LeadLanguage.IT,
    )
    country = models.ForeignKey(
        "jurisdictions.Country",
        on_delete=models.SET_NULL,
        related_name="leads",
        verbose_name=_("country"),
        null=True,
        blank=True,
    )
    case_type = models.CharField(
        _("case type"),
        max_length=64,
        choices=CaseType.choices,
        blank=True,
    )

    message = models.TextField(_("message"))

    status = models.CharField(
        _("status"),
        max_length=16,
        choices=LeadStatus.choices,
        default=LeadStatus.RECEIVED,
        db_index=True,
    )
    priority = models.CharField(
        _("priority"),
        max_length=8,
        choices=LeadPriority.choices,
        default=LeadPriority.NORMAL,
    )

    consent_record = models.ForeignKey(
        "compliance.ConsentRecord",
        on_delete=models.SET_NULL,
        related_name="leads",
        verbose_name=_("consent record"),
        null=True,
        blank=True,
        help_text=_(
            "Backward-compatible FK al primo ConsentRecord (lead_contact). "
            "Iter F-p0-leg-3-consent: il doppio consenso GDPR art. 6 + art. 9 "
            "e' tracciato anche tramite i campi denormalizzati privacy_*/special_categories_* "
            "sotto + un secondo ConsentRecord con purpose `special_categories_processing`."
        ),
    )

    # F-p0-leg-3-consent: campi denormalizzati per audit del doppio consenso.
    # Source-of-truth resta `compliance.ConsentRecord` (uno per purpose);
    # questi campi servono per query rapide, esportazioni GDPR, e per
    # rendere visibile a colpo d'occhio nello staff admin che il submit
    # ha raccolto entrambi i consensi richiesti.
    privacy_consent_given = models.BooleanField(
        _("privacy consent (GDPR art. 6) given"),
        default=False,
    )
    privacy_consent_at = models.DateTimeField(
        _("privacy consent timestamp"),
        null=True,
        blank=True,
    )
    privacy_consent_version = models.CharField(
        _("privacy consent text version"),
        max_length=64,
        blank=True,
    )
    special_categories_consent_given = models.BooleanField(
        _("special categories consent (GDPR art. 9) given"),
        default=False,
    )
    special_categories_consent_at = models.DateTimeField(
        _("special categories consent timestamp"),
        null=True,
        blank=True,
    )
    special_categories_consent_version = models.CharField(
        _("special categories consent text version"),
        max_length=64,
        blank=True,
    )

    ip_address = models.GenericIPAddressField(_("ip address"), null=True, blank=True)
    user_agent = models.CharField(_("user agent"), max_length=512, blank=True)
    source_path = models.CharField(_("source path"), max_length=512, blank=True)

    utm_source = models.CharField(_("utm source"), max_length=128, blank=True)
    utm_medium = models.CharField(_("utm medium"), max_length=128, blank=True)
    utm_campaign = models.CharField(_("utm campaign"), max_length=128, blank=True)

    internal_notes = models.TextField(_("internal notes"), blank=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="assigned_leads",
        verbose_name=_("assigned to"),
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)
    contacted_at = models.DateTimeField(_("contacted at"), null=True, blank=True)
    converted_at = models.DateTimeField(_("converted at"), null=True, blank=True)

    anonymized = models.BooleanField(_("anonymized"), default=False, db_index=True)
    anonymized_at = models.DateTimeField(_("anonymized at"), null=True, blank=True)

    class Meta:
        verbose_name = _("lead")
        verbose_name_plural = _("leads")
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
            models.Index(fields=["priority", "status"]),
            models.Index(fields=["assigned_to", "status"]),
            models.Index(fields=["country", "case_type"]),
        ]

    def __str__(self) -> str:
        return f"lead:{self.public_id} [{self.status}]"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class LeadEvent(models.Model):
    """Lifecycle event di un Lead. Append-only."""

    class EventType(models.TextChoices):
        CREATED = "created", _("Created")
        CONTACTED = "contacted", _("Contacted")
        QUALIFIED = "qualified", _("Qualified")
        CONVERTED = "converted", _("Converted")
        REJECTED = "rejected", _("Rejected")
        ARCHIVED = "archived", _("Archived")
        NOTE = "note", _("Note")
        OTHER = "other", _("Other")

    lead = models.ForeignKey(
        Lead,
        on_delete=models.CASCADE,
        related_name="events",
        verbose_name=_("lead"),
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
        verbose_name = _("lead event")
        verbose_name_plural = _("lead events")
        # `-pk` come tiebreak deterministico (stesso pattern di SimulationEvent
        # e ConsentRecord: timer Windows ~15.6ms causa timestamp uguali su
        # eventi consecutivi).
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["lead", "event_type"]),
            models.Index(fields=["event_type", "created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.event_type}@{self.lead_id}"
