from django.apps import AppConfig


class LegalSourcesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.legal_sources"
    label = "legal_sources"

    def ready(self) -> None:
        # Registrazione auditlog per LegalSource: ogni modifica viene tracciata
        # con diff completo, utente e timestamp. Indispensabile dato che
        # queste fonti governeranno calcoli legali in produzione.
        from auditlog.registry import auditlog

        from .models import LegalReview, LegalSource, LegalSourceVersion

        auditlog.register(LegalSource)
        auditlog.register(LegalSourceVersion)
        auditlog.register(LegalReview)
