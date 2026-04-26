from django.apps import AppConfig


class CasesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cases"
    label = "cases"

    def ready(self) -> None:
        # auditlog su `Simulation`: ogni edit dallo staff (incluse le
        # anonimizzazioni) viene tracciato con diff completo.
        # `SimulationEvent` non è registrato perché è già append-only.
        from auditlog.registry import auditlog

        from .models import Simulation

        auditlog.register(Simulation)
