from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm"
    label = "crm"

    def ready(self) -> None:
        # auditlog su `Lead`: ogni edit dello staff è tracciato (cambi
        # status/priority/assigned_to/internal_notes). `LeadEvent` è già
        # append-only e non serve auditlog.
        from auditlog.registry import auditlog

        from .models import Lead

        auditlog.register(Lead)
