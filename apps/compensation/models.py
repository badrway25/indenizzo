"""
Modelli `compensation` — dataset tabellari e formule di calcolo.

F-sources-italy: separazione netta fra **fonti** (`apps.legal_sources`) e
**dati estratti** (qui). La regola del progetto è "meglio nessun calcolo
che un calcolo falso": questi modelli sono il contenitore in cui i dati
tabellari potranno entrare *solo dopo* che la fonte corrispondente è
stata caricata, validata, approvata da un revisore legale, e i numeri
trascritti riga per riga.

Garanzie strutturali:

- ogni `CompensationDataset` è ancorato a una `LegalSource`. Senza fonte,
  niente dataset. Niente importi senza traccia documentale.
- un dataset può essere `APPROVED` *solo* se la fonte collegata è già
  `APPROVED`. Vincolo applicato in `clean()`.
- le righe (`CompensationTableRow`) e le formule (`CalculationFormula`)
  ereditano lo stato dal dataset di appartenenza: il calculator non le
  legge se il dataset non è `APPROVED`.
- nessun valore numerico è popolato in DB da seed o migrazioni: il
  caricamento è un'attività umana di estrazione legale, non un side
  effect del codice.

I modelli NON contengono dati. F-sources-italy ne crea solo lo schema.
La fase successiva (estrazione tabellare) inserirà righe in `DRAFT` e
le promuoverà a `APPROVED` solo dopo legal review.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.calculators.enums import CaseType
from apps.legal_sources.enums import SourceStatus


class DatasetStatus(models.TextChoices):
    """
    Stato di lavorazione di un dataset / formula di calcolo.

    Solo `APPROVED` può essere consumato da un calculator pubblico.
    `DEPRECATED` indica un dataset storicamente valido ma non più da usare.
    """

    DRAFT = "draft", _("Draft")
    NEEDS_REVIEW = "needs_review", _("Needs review")
    APPROVED = "approved", _("Approved")
    DEPRECATED = "deprecated", _("Deprecated")


class CompensationDataset(models.Model):
    """
    Insieme di dati tabellari estratti da una `LegalSource` validata.

    Esempio (futuro): righe della Tabella Unica Nazionale per il danno
    biologico in RCA, ancorate al D.P.R. 13 gennaio 2025 n. 12.

    Un dataset NON contiene importi finché un revisore non li ha
    trascritti dalla fonte e marcati `APPROVED`. La sola creazione del
    dataset (status `DRAFT`) non sblocca alcun calcolo.
    """

    source = models.ForeignKey(
        "legal_sources.LegalSource",
        on_delete=models.PROTECT,
        related_name="compensation_datasets",
        verbose_name=_("legal source"),
        help_text=_("Fonte legale da cui i dati sono estratti."),
    )
    jurisdiction = models.ForeignKey(
        "jurisdictions.Jurisdiction",
        on_delete=models.PROTECT,
        related_name="compensation_datasets",
        verbose_name=_("jurisdiction"),
    )
    country = models.ForeignKey(
        "jurisdictions.Country",
        on_delete=models.PROTECT,
        related_name="compensation_datasets",
        verbose_name=_("country"),
    )

    case_type = models.CharField(
        _("case type"),
        max_length=64,
        choices=CaseType.choices,
        db_index=True,
        help_text=_(
            "Tipo di caso a cui il dataset si applica. Determina quale "
            "calculator può eventualmente leggerlo."
        ),
    )

    name = models.CharField(
        _("name"),
        max_length=200,
        help_text=_("Etichetta umana, es. 'Tabella Unica Nazionale 2025'."),
    )
    version_label = models.CharField(
        _("version label"),
        max_length=64,
        blank=True,
        help_text=_("Versione interna, es. '2025.1'."),
    )

    status = models.CharField(
        _("status"),
        max_length=24,
        choices=DatasetStatus.choices,
        default=DatasetStatus.DRAFT,
        db_index=True,
    )

    valid_from = models.DateField(_("valid from"), null=True, blank=True)
    valid_to = models.DateField(_("valid to"), null=True, blank=True)

    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("compensation dataset")
        verbose_name_plural = _("compensation datasets")
        ordering = ["-valid_from", "name"]
        indexes = [
            models.Index(fields=["jurisdiction", "case_type", "status"]),
            models.Index(fields=["country", "case_type", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} [{self.status}]"

    def clean(self) -> None:
        super().clean()
        # Vincolo applicativo: un dataset APPROVED richiede una fonte
        # APPROVED. Senza questo, sarebbe possibile sbloccare un calcolo
        # leggendo dati ancorati a una fonte ancora in revisione.
        if self.status == DatasetStatus.APPROVED:
            if not self.source_id:
                raise ValidationError(
                    {"source": _("An approved dataset must reference a legal source.")}
                )
            if self.source.status != SourceStatus.APPROVED:
                raise ValidationError(
                    {
                        "status": _(
                            "Cannot mark dataset APPROVED while its legal source "
                            "is not APPROVED."
                        )
                    }
                )
        # Vincolo temporale: valid_to deve essere >= valid_from.
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValidationError(
                {"valid_to": _("`valid_to` must be greater than or equal to `valid_from`.")}
            )

    @property
    def is_usable_for_calculations(self) -> bool:
        """True solo se il dataset può essere consumato da un calcolo."""
        if self.status != DatasetStatus.APPROVED:
            return False
        if self.source_id and self.source.status != SourceStatus.APPROVED:
            return False
        return True


class CompensationTableRow(models.Model):
    """
    Riga tabellare di un `CompensationDataset`.

    Esempio (futuro, NON popolato qui): per la TUN danno biologico,
    una riga rappresenta il valore-punto in funzione di età ed
    invalidità. La struttura è volutamente generica: ciascun calculator
    sa quali colonne leggere per il proprio case_type.

    Tutti i campi numerici sono `null=True`: non tutte le tabelle usano
    tutti i campi. Solo i valori effettivamente trascritti dalla fonte
    devono essere riempiti.
    """

    dataset = models.ForeignKey(
        CompensationDataset,
        on_delete=models.CASCADE,
        related_name="rows",
        verbose_name=_("dataset"),
    )

    row_type = models.CharField(
        _("row type"),
        max_length=64,
        blank=True,
        help_text=_(
            "Categoria libera della riga, es. 'point_value', "
            "'daily_temporary_disability', 'multiplier'."
        ),
    )

    age_min = models.PositiveIntegerField(_("age min"), null=True, blank=True)
    age_max = models.PositiveIntegerField(_("age max"), null=True, blank=True)

    disability_min = models.PositiveIntegerField(_("disability % min"), null=True, blank=True)
    disability_max = models.PositiveIntegerField(_("disability % max"), null=True, blank=True)

    point_value = models.DecimalField(
        _("point value"),
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    daily_amount = models.DecimalField(
        _("daily amount"),
        max_digits=14,
        decimal_places=4,
        null=True,
        blank=True,
    )
    coefficient = models.DecimalField(
        _("coefficient"),
        max_digits=14,
        decimal_places=6,
        null=True,
        blank=True,
    )

    extra = models.JSONField(
        _("extra"),
        default=dict,
        blank=True,
        help_text=_("Campi opzionali specifici della tabella, JSON libero."),
    )
    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("compensation table row")
        verbose_name_plural = _("compensation table rows")
        ordering = ["dataset", "age_min", "disability_min"]
        indexes = [
            models.Index(fields=["dataset", "row_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.dataset.name} — {self.row_type or 'row'}#{self.pk or 'new'}"

    def clean(self) -> None:
        super().clean()
        if self.age_min is not None and self.age_max is not None and self.age_max < self.age_min:
            raise ValidationError({"age_max": _("`age_max` must be >= `age_min`.")})
        if (
            self.disability_min is not None
            and self.disability_max is not None
            and self.disability_max < self.disability_min
        ):
            raise ValidationError(
                {"disability_max": _("`disability_max` must be >= `disability_min`.")}
            )


class CalculationFormula(models.Model):
    """
    Formula di calcolo collegata a un `CompensationDataset`.

    L'`expression_text` è documentale: il motore non la valuta dinamicamente
    in F-sources-italy. La sua presenza serve a tracciare che la formula
    usata è la stessa dichiarata nella fonte (es. "punto × inabilità ×
    demoltiplicatore età"). I parametri numerici vivono nei campi tabellari
    o in `parameters` JSON.

    `code` è un identificatore stabile interno (es. `tun_biologico_punto`)
    che il calculator referenzia.
    """

    dataset = models.ForeignKey(
        CompensationDataset,
        on_delete=models.CASCADE,
        related_name="formulas",
        verbose_name=_("dataset"),
    )

    code = models.CharField(
        _("internal code"),
        max_length=64,
        help_text=_("Identificatore stabile, es. 'tun_biologico_punto'."),
    )
    name = models.CharField(_("name"), max_length=200)
    expression_text = models.TextField(
        _("expression text"),
        blank=True,
        help_text=_(
            "Descrizione testuale della formula, riprodotta dalla fonte. "
            "Non viene valutata automaticamente: serve come traccia."
        ),
    )
    parameters = models.JSONField(
        _("parameters"),
        default=dict,
        blank=True,
        help_text=_("Mappa parametri opzionale, JSON libero."),
    )
    source_reference = models.CharField(
        _("source reference"),
        max_length=255,
        blank=True,
        help_text=_(
            "Riferimento testuale alla porzione di fonte da cui la "
            "formula è stata estratta, es. 'art. 138 comma 2'."
        ),
    )

    status = models.CharField(
        _("status"),
        max_length=24,
        choices=DatasetStatus.choices,
        default=DatasetStatus.DRAFT,
        db_index=True,
    )

    notes = models.TextField(_("notes"), blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta:
        verbose_name = _("calculation formula")
        verbose_name_plural = _("calculation formulas")
        ordering = ["dataset", "code"]
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "code"],
                name="uniq_formula_code_per_dataset",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.dataset.name})"

    def clean(self) -> None:
        super().clean()
        # Una formula APPROVED richiede un dataset APPROVED. Stessa logica
        # di propagazione di stato che applichiamo a livello dataset/source.
        if self.status == DatasetStatus.APPROVED:
            if not self.dataset_id:
                raise ValidationError(
                    {"dataset": _("An approved formula must belong to a dataset.")}
                )
            if self.dataset.status != DatasetStatus.APPROVED:
                raise ValidationError(
                    {
                        "status": _(
                            "Cannot mark formula APPROVED while its dataset is " "not APPROVED."
                        )
                    }
                )


class ExtractionLog(models.Model):
    """
    Audit append-only delle esecuzioni di import di dati tabellari.

    Ogni esecuzione di un command `import_*` lascia una riga qui:
    - quale fonte / dataset è stato toccato;
    - quale file è stato letto, con SHA-256;
    - quante righe sono entrate;
    - esito (success / partial / failed) ed eventuale errore.

    Append-only: non c'è `update`, non c'è cancellazione automatica. Lo
    Studio può consultare lo storico per dimostrare la provenienza di
    qualsiasi dato finito in calcolo.
    """

    class Method(models.TextChoices):
        PDF_ATTACH = "pdf_attach", _("PDF attached")
        CSV_IMPORT = "csv_import", _("CSV import")
        MANUAL = "manual", _("Manual entry")

    class Result(models.TextChoices):
        SUCCESS = "success", _("Success")
        PARTIAL = "partial", _("Partial")
        FAILED = "failed", _("Failed")

    source = models.ForeignKey(
        "legal_sources.LegalSource",
        on_delete=models.PROTECT,
        related_name="extraction_logs",
        verbose_name=_("legal source"),
    )
    dataset = models.ForeignKey(
        CompensationDataset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="extraction_logs",
        verbose_name=_("dataset"),
        help_text=_(
            "Può essere null se l'estrazione non è arrivata a creare il "
            "dataset (es. errore durante l'attach del PDF)."
        ),
    )

    method = models.CharField(_("method"), max_length=24, choices=Method.choices)
    file_path = models.CharField(_("file path"), max_length=1024, blank=True)
    file_sha256 = models.CharField(_("file sha256"), max_length=64, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(_("file size (bytes)"), default=0)

    rows_imported = models.PositiveIntegerField(_("rows imported"), default=0)
    rows_skipped = models.PositiveIntegerField(_("rows skipped"), default=0)

    result = models.CharField(_("result"), max_length=16, choices=Result.choices)
    error_message = models.TextField(_("error message"), blank=True)
    metadata = models.JSONField(_("metadata"), default=dict, blank=True)

    created_at = models.DateTimeField(_("created at"), auto_now_add=True)

    class Meta:
        verbose_name = _("extraction log")
        verbose_name_plural = _("extraction logs")
        # `-pk` come tiebreak deterministico: `auto_now_add` ha
        # risoluzione ~15.6 ms su Windows, e due ExtractionLog creati
        # nello stesso burst (es. due re-run del command nello stesso
        # test) possono condividere `created_at`. Stesso pattern usato
        # in cases.SimulationEvent e crm.ConsentRecord.
        ordering = ["-created_at", "-pk"]
        indexes = [
            models.Index(fields=["source", "-created_at"]),
            models.Index(fields=["dataset", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.method} {self.result} {self.source} ({self.created_at:%Y-%m-%d})"
