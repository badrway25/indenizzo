from django.apps import AppConfig


class JurisdictionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.jurisdictions"
    label = "jurisdictions"

    def ready(self) -> None:
        # System check `jurisdictions.E001` (F-p0-mvp-1-non-it-readiness):
        # in production, every APPROVED LegalSource must have a matching
        # APPROVE LegalReview audit row + a non-null legal_reviewer FK.
        # The import here registers the check via the
        # `@register("jurisdictions")` decorator.
        from . import checks  # noqa: F401
