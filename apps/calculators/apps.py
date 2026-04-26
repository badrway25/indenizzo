from django.apps import AppConfig


class CalculatorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.calculators"
    label = "calculators"

    def ready(self) -> None:
        # Forziamo l'import del package `engines` perché ogni submodule
        # paese si auto-registra nel calculator registry. Senza questo,
        # il registry resta vuoto finché nessuno importa esplicitamente
        # `apps.calculators.engines.italy` o simili.
        from . import engines  # noqa: F401
