"""
Modelli per la gestione documentale delle fonti legali.

F1 — fondamento del sistema dati legali. Nessun importo, nessun coefficiente,
nessuna formula: questi modelli memorizzano SOLO documenti, metadati e stato
di validazione. La logica di calcolo userà queste fonti in fasi successive
(F4+ calculators) e solo se status == approved.

Le storiche dei record (chi ha cambiato cosa, quando) sono garantite da:
- created_at / updated_at (snapshot temporali);
- LegalSourceVersion (versioni documentali con hash integrità);
- LegalReview (decisioni di validazione legale);
- auditlog (registrato in `apps.py`) per il diff completo.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from .enums import Reliability, SourceStatus, SourceType
from .managers import LegalSourceManager
from .utils import compute_sha256


def attachment_upload_path(instance: LegalSourceAttachment, filename: str) -> str:
    country = (instance.source.country.code if instance.source.country else "XX").lower()
    return f"legal_sources/{country}/{instance.source.pk or 'new'}/{filename}"


class LegalSource(models.Model):
    """
    Fonte legale: norma, decreto, tabella, linea guida, riferimento assicurativo.

    Una `LegalSource` è il "documento canonico" identificato da titolo + paese
    + tipo. Le sue copie/edizioni nel tempo vivono in `LegalSourceVersion`.
    Gli allegati (PDF, screenshot, estratti) vivono in `LegalSourceAttachment`.
    """

    title = models.CharField(_("title"), max_length=512)
    slug = models.SlugField(_("slug"), max_length=200, blank=True)

    country = models.ForeignKey(
        "jurisdictions.Country",
        on_delete=models.PROTECT,
        related_name="legal_sources",
        verbose_name=_("country"),
    )
    jurisdiction = models.ForeignKey(
        "jurisdictions.Jurisdiction",
        on_delete=models.PROTECT,
        related_name="legal_sources",
        verbose_name=_("jurisdiction"),
        null=True,
        blank=True,
        help_text=_("Giurisdizione specifica, se più precisa del paese."),
    )
    language = models.ForeignKey(
        "jurisdictions.Language",
        on_delete=models.PROTECT,
        related_name="legal_sources",
        verbose_name=_("language"),
        null=True,
        blank=True,
    )

    source_type = models.CharField(
        _("source type"),
        max_length=32,
        choices=SourceType.choices,
        default=SourceType.OFFICIAL_LAW,
    )
    official_url = models.URLField(_("official URL"), max_length=1000, blank=True)
    citation = models.CharField(
        _("citation / reference"),
        max_length=512,
        blank=True,
        help_text=_("Riferimento testuale stabile, es. 'D.Lgs. 209/2005, art. 139'."),
    )

    publication_date = models.DateField(_("publication date"), null=True, blank=True)
    effective_date = models.DateField(_("effective date"), null=True, blank=True)
    valid_until = models.DateField(_("valid until"), null=True, blank=True)
    last_checked_at = models.DateField(_("last checked at"), null=True, blank=True)

    status = models.CharField(
        _("status"),
        max_length=24,
        choices=SourceStatus.choices,
        default=SourceStatus.DRAFT,
        db_index=True,
    )
    reliability = models.CharField(
        _("reliability"),
        max_length=16,
        choices=Reliability.choices,
        default=Reliability.UNKNOWN,
    )
    legal_reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviewed_legal_sources",
        verbose_name=_("legal reviewer"),
        null=True,
        blank=True,
    )

    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="superseded_by",
        verbose_name=_("supersedes"),
        null=True,
        blank=True,
    )
    replaced_by = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="replaces",
        verbose_name=_("replaced by"),
        null=True,
        blank=True,
    )

    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    objects = LegalSourceManager()

    class Meta:
        verbose_name = _("legal source")
        verbose_name_plural = _("legal sources")
        ordering = ["-publication_date", "title"]
        indexes = [
            models.Index(fields=["country", "status"]),
            models.Index(fields=["jurisdiction", "status"]),
            models.Index(fields=["source_type", "status"]),
        ]

    def __str__(self) -> str:
        country = self.country.code if self.country_id else "??"
        return f"[{country}] {self.title}"

    def clean(self) -> None:
        # REQ-1 (multilingua): le fonti pubblicamente usabili devono dichiarare
        # la lingua originale. Vincolo applicativo, non DB: lasciamo le bozze
        # senza language per consentire bulk import in cui la lingua viene
        # arricchita dopo. Una fonte può essere promossa ad APPROVED solo se
        # la lingua è nota.
        super().clean()
        if self.status == SourceStatus.APPROVED and not self.language_id:
            raise ValidationError(
                {"language": _("An approved legal source must declare its original language.")}
            )

    @property
    def is_usable_for_calculations(self) -> bool:
        """True solo se la fonte può essere consumata da un calcolo pubblico."""
        return self.is_usable_at()

    def is_usable_at(self, reference_date=None) -> bool:
        """
        Vigenza alla `reference_date` indicata (default: oggi).

        Coerente con `LegalSourceManager.approved(reference_date=...)`:
        esclude fonti scadute (`valid_until < ref`) ed esclude fonti non
        ancora in vigore (`effective_date > ref`). Necessario per
        simulazioni datate, dove la fonte applicabile è quella vigente
        al momento del fatto, non al momento della query.
        """
        if self.status != SourceStatus.APPROVED:
            return False
        from django.utils import timezone

        ref = reference_date or timezone.now().date()
        if self.valid_until and self.valid_until < ref:
            return False
        if self.effective_date and self.effective_date > ref:
            return False
        return True


class LegalSourceVersion(models.Model):
    """
    Versione concreta del contenuto normativo nel tempo.

    Una norma resta "la stessa" (stesso `LegalSource`) ma cambia testo /
    coefficienti nel tempo. Ogni cambio = nuovo `LegalSourceVersion` con il
    suo intervallo di validità. Il campo `supersedes` permette di tracciare
    quale versione precedente sostituisce.
    """

    source = models.ForeignKey(
        LegalSource,
        on_delete=models.CASCADE,
        related_name="versions",
        verbose_name=_("legal source"),
    )
    version_label = models.CharField(
        _("version label"),
        max_length=64,
        help_text=_("Etichetta umana, es. '2024.1' o 'Tabelle Milano 2024'."),
    )
    content_hash = models.CharField(
        _("content hash (sha256)"),
        max_length=64,
        blank=True,
        help_text=_("SHA-256 del contenuto canonico, per integrità."),
    )

    valid_from = models.DateField(_("valid from"), null=True, blank=True)
    valid_to = models.DateField(_("valid to"), null=True, blank=True)

    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        related_name="superseded_by",
        verbose_name=_("supersedes"),
        null=True,
        blank=True,
    )

    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("legal source version")
        verbose_name_plural = _("legal source versions")
        ordering = ["-valid_from", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["source", "version_label"],
                name="uniq_source_version_label",
            ),
            # H1-5: una versione non può avere validità che si chiude prima di
            # aprirsi. NULL su un estremo = validità aperta (legittima).
            models.CheckConstraint(
                name="lsv_valid_to_gte_valid_from",
                condition=(
                    models.Q(valid_from__isnull=True)
                    | models.Q(valid_to__isnull=True)
                    | models.Q(valid_to__gte=models.F("valid_from"))
                ),
            ),
        ]

    def __str__(self) -> str:
        return f"{self.source} — {self.version_label}"


class LegalSourceAttachment(models.Model):
    """
    File allegato a una `LegalSource`: PDF ufficiale, screenshot, estratto.

    Per ogni file teniamo hash SHA-256, mime e dimensione: serve per
    rilevare modifiche silenziose dello stesso file e per audit forense.
    """

    source = models.ForeignKey(
        LegalSource,
        on_delete=models.CASCADE,
        related_name="attachments",
        verbose_name=_("legal source"),
    )
    file = models.FileField(_("file"), upload_to=attachment_upload_path)
    original_filename = models.CharField(_("original filename"), max_length=255, blank=True)
    mime_type = models.CharField(_("mime type"), max_length=128, blank=True)
    size_bytes = models.PositiveBigIntegerField(_("size (bytes)"), default=0)
    sha256 = models.CharField(_("sha256"), max_length=64, blank=True)

    description = models.CharField(_("description"), max_length=512, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("legal source attachment")
        verbose_name_plural = _("legal source attachments")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.original_filename or self.file.name

    def save(self, *args, **kwargs):
        if self.file and hasattr(self.file, "file"):
            try:
                self.size_bytes = self.file.size or 0
            except (OSError, ValueError):
                self.size_bytes = 0
            try:
                self.sha256 = compute_sha256(self.file.file)
            except (AttributeError, OSError, ValueError):
                # Allegati salvati senza file binario leggibile restano senza
                # hash. La presenza di `sha256` resta la prova di integrità.
                pass
            if not self.original_filename:
                self.original_filename = getattr(self.file, "name", "") or ""
        super().save(*args, **kwargs)


class LegalReview(models.Model):
    """
    Decisione di validazione legale su una `LegalSource`.

    Storicizza chi ha approvato/respinto cosa e quando. Indipendente
    dall'auditlog: questo modello è semantico (decisione legale), l'auditlog
    è tecnico (diff su tutti i campi).
    """

    class Decision(models.TextChoices):
        REQUEST_CHANGES = "request_changes", _("Request changes")
        APPROVE = "approve", _("Approve")
        REJECT = "reject", _("Reject")
        REOPEN = "reopen", _("Reopen")

    source = models.ForeignKey(
        LegalSource,
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name=_("legal source"),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="legal_reviews",
        verbose_name=_("reviewer"),
    )
    decision = models.CharField(
        _("decision"),
        max_length=24,
        choices=Decision.choices,
    )
    previous_status = models.CharField(
        _("previous status"),
        max_length=24,
        choices=SourceStatus.choices,
        blank=True,
    )
    new_status = models.CharField(
        _("new status"),
        max_length=24,
        choices=SourceStatus.choices,
        blank=True,
    )
    comment = models.TextField(_("comment"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("legal review")
        verbose_name_plural = _("legal reviews")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.source} — {self.decision} by {self.reviewer}"
