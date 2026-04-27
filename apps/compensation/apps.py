from django.apps import AppConfig


class CompensationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.compensation"
    label = "compensation"

    def ready(self) -> None:
        # I dataset/righe/formule governeranno calcoli legali. Ogni modifica
        # in admin (o via shell) viene tracciata da auditlog: chi, quando,
        # cosa è cambiato.
        from auditlog.registry import auditlog

        from .models import (
            CalculationFormula,
            CompensationDataset,
            CompensationTableRow,
            ExtractionLog,
        )

        auditlog.register(CompensationDataset)
        auditlog.register(CompensationTableRow)
        auditlog.register(CalculationFormula)
        auditlog.register(ExtractionLog)
