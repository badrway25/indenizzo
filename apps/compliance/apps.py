from django.apps import AppConfig


class ComplianceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.compliance"
    label = "compliance"

    def ready(self) -> None:
        # auditlog tracks staff edits a DataDeletionRequest (workflow GDPR).
        # ConsentRecord/PrivacyAuditEvent sono già append-only via admin.
        from auditlog.registry import auditlog

        from .models import DataDeletionRequest, DataRetentionPolicy

        auditlog.register(DataDeletionRequest)
        auditlog.register(DataRetentionPolicy)

        # Auth signals → StaffAccessEvent (pass 8). L'import qui registra
        # i receiver `@receiver(user_logged_in/out/failed)`. Read-only:
        # mai blocca o altera il flow di autenticazione.
        from . import signals  # noqa: F401
