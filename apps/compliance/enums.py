"""
Enum di apps.compliance.

Mantengo separati per leggibilità: ConsentLanguage replica le 4 lingue
ufficiali del progetto (it/fr/en/ar) per coerenza con LANGUAGES, mentre
DeletionStatus e PrivacyEventType formalizzano i workflow GDPR.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class ConsentLanguage(models.TextChoices):
    IT = "it", _("Italiano")
    FR = "fr", _("Français")
    EN = "en", _("English")
    AR = "ar", _("العربية")


class RetentionScope(models.TextChoices):
    """A quale tipo di dato si applica una retention policy."""

    SIMULATION_INPUT = "simulation_input", _("Simulation inputs")
    SIMULATION_RESULT = "simulation_result", _("Simulation results")
    LEAD_CONTACT = "lead_contact", _("Lead / contact requests")
    UPLOADED_DOCUMENT = "uploaded_document", _("Uploaded documents")
    CONSENT_LOG = "consent_log", _("Consent records")
    AUDIT_LOG = "audit_log", _("Audit / privacy events")
    OTHER = "other", _("Other")


class DeletionStatus(models.TextChoices):
    RECEIVED = "received", _("Received")
    VERIFYING_IDENTITY = "verifying_identity", _("Verifying identity")
    APPROVED = "approved", _("Approved")
    REJECTED = "rejected", _("Rejected")
    COMPLETED = "completed", _("Completed")


class PrivacyEventType(models.TextChoices):
    """
    Tipi di evento privacy. Questa lista è volutamente compatta:
    ogni evento riporta `target_model` + `target_object_id`, quindi
    non serve un enum esploso per oggetto.
    """

    CONSENT_GIVEN = "consent_given", _("Consent given")
    CONSENT_WITHDRAWN = "consent_withdrawn", _("Consent withdrawn")
    DATA_ACCESSED = "data_accessed", _("Data accessed")
    DATA_EXPORTED = "data_exported", _("Data exported")
    DATA_DELETION_REQUESTED = "data_deletion_requested", _("Data deletion requested")
    DATA_DELETION_COMPLETED = "data_deletion_completed", _("Data deletion completed")
    LEGAL_SOURCE_REVIEWED = "legal_source_reviewed", _("Legal source reviewed")
    OTHER = "other", _("Other")
