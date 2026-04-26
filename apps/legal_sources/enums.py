"""
Enum per il dominio legal_sources.

Sono `TextChoices` perché vengono usate in DB e nelle UI admin/wizard.
Le label sono i18n-ready ma volutamente neutre: NON descrivono effetti
giuridici, descrivono solo lo stato del record nella nostra pipeline
documentale.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class SourceStatus(models.TextChoices):
    """
    Stato di lavorazione di una fonte legale all'interno della nostra pipeline.

    Solo `APPROVED` può essere consumato dai calcoli pubblici.
    `DEPRECATED` e `REPLACED` indicano fonti storicamente valide ma non più
    da usare per i calcoli correnti.
    """

    DRAFT = "draft", _("Draft")
    EXTRACTED = "extracted", _("Extracted")
    NEEDS_REVIEW = "needs_review", _("Needs review")
    REVIEWED = "reviewed", _("Reviewed")
    APPROVED = "approved", _("Approved")
    DEPRECATED = "deprecated", _("Deprecated")
    REPLACED = "replaced", _("Replaced")


class SourceType(models.TextChoices):
    """Categoria documentale della fonte. Influenza fiducia e uso."""

    OFFICIAL_LAW = "official_law", _("Official law / statute")
    MINISTRY_DECREE = "ministry_decree", _("Ministry decree")
    COURT_TABLE = "court_table", _("Court compensation table")
    ADMINISTRATIVE_GUIDELINE = "administrative_guideline", _("Administrative guideline")
    INSURANCE_REFERENCE = "insurance_reference", _("Insurance reference")
    DOCTRINE = "doctrine", _("Doctrine / academic")
    INTERNAL_LEGAL_NOTE = "internal_legal_note", _("Internal legal note")
    DEMO_PLACEHOLDER = "demo_placeholder", _("Demo / placeholder (non legal)")


class Reliability(models.TextChoices):
    """Indicatore qualitativo dell'affidabilità della fonte."""

    OFFICIAL = "official", _("Official")
    HIGH = "high", _("High")
    MEDIUM = "medium", _("Medium")
    LOW = "low", _("Low")
    UNKNOWN = "unknown", _("Unknown")
