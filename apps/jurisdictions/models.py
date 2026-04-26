"""
Jurisdictions — modelli minimi (F1) richiesti come FK da apps.legal_sources.

Scope F1: solo strutture base (Country, Jurisdiction, Currency, Language) per
permettere a LegalSource di avere FK solide. Estensioni (sistemi giuridici di
dettaglio, regioni, lingue ufficiali multiple, tabelle valutarie, ecc.) sono
rinviate a F2.

Nessun seed di dati legali reali. Le sole stringhe presenti sono le label
ISO (codici alpha-2/alpha-3 e similari), che NON costituiscono dato legale.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class Country(models.Model):
    """Paese sovrano. ISO 3166-1."""

    code = models.CharField(
        _("ISO alpha-2 code"),
        max_length=2,
        unique=True,
        help_text=_("Codice ISO 3166-1 alpha-2, es. IT, FR, BE, MA, TN."),
    )
    code_alpha3 = models.CharField(
        _("ISO alpha-3 code"),
        max_length=3,
        blank=True,
        help_text=_("Codice ISO 3166-1 alpha-3, opzionale."),
    )
    name = models.CharField(_("name"), max_length=128)
    is_active = models.BooleanField(
        _("active"),
        default=True,
        help_text=_("Se False, il paese non viene proposto nei wizard pubblici."),
    )
    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("country")
        verbose_name_plural = _("countries")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        if self.code_alpha3:
            self.code_alpha3 = self.code_alpha3.upper()
        super().save(*args, **kwargs)


class Currency(models.Model):
    """Valuta. ISO 4217. Nessun tasso di cambio in F1."""

    code = models.CharField(
        _("ISO 4217 code"),
        max_length=3,
        unique=True,
        help_text=_("Codice ISO 4217, es. EUR, MAD, TND, USD."),
    )
    name = models.CharField(_("name"), max_length=64)
    symbol = models.CharField(_("symbol"), max_length=8, blank=True)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("currency")
        verbose_name_plural = _("currencies")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)


class Language(models.Model):
    """Lingua. ISO 639-1 (codici a due lettere)."""

    code = models.CharField(
        _("ISO 639-1 code"),
        max_length=8,
        unique=True,
        help_text=_("Codice ISO 639-1, es. it, fr, en, ar."),
    )
    name = models.CharField(_("name"), max_length=64)
    is_active = models.BooleanField(_("active"), default=True)

    class Meta:
        verbose_name = _("language")
        verbose_name_plural = _("languages")
        ordering = ["code"]

    def __str__(self) -> str:
        return self.code

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.lower()
        super().save(*args, **kwargs)


class Jurisdiction(models.Model):
    """
    Giurisdizione di riferimento per un calcolo.

    In F1 una Jurisdiction coincide tipicamente con un Country (livello
    nazionale). In F2 si potranno aggiungere giurisdizioni sub-nazionali
    (regione, cantone, comune) e sistemi giuridici dettagliati.
    """

    class LegalSystem(models.TextChoices):
        CIVIL_LAW = "civil_law", _("Civil law")
        COMMON_LAW = "common_law", _("Common law")
        MIXED = "mixed", _("Mixed system")
        RELIGIOUS = "religious", _("Religious-based")
        UNKNOWN = "unknown", _("Unknown / not classified")

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="jurisdictions",
        verbose_name=_("country"),
    )
    code = models.CharField(
        _("internal code"),
        max_length=32,
        unique=True,
        help_text=_("Identificatore interno stabile, es. IT, IT-LOM, FR, BE, MA, TN."),
    )
    name = models.CharField(_("name"), max_length=128)
    legal_system = models.CharField(
        _("legal system"),
        max_length=32,
        choices=LegalSystem.choices,
        default=LegalSystem.UNKNOWN,
    )
    default_currency = models.ForeignKey(
        Currency,
        on_delete=models.PROTECT,
        related_name="jurisdictions",
        verbose_name=_("default currency"),
        null=True,
        blank=True,
    )
    default_language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name="jurisdictions",
        verbose_name=_("default language"),
        null=True,
        blank=True,
    )
    is_active = models.BooleanField(_("active"), default=True)
    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("jurisdiction")
        verbose_name_plural = _("jurisdictions")
        ordering = ["code"]

    def __str__(self) -> str:
        return f"{self.code} — {self.name}"

    def save(self, *args, **kwargs):
        if self.code:
            self.code = self.code.upper()
        super().save(*args, **kwargs)
