from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.reports"
    label = "reports"

    def ready(self) -> None:
        # I `SimulationReport` sono artefatti derivati di una Simulation
        # e tracciati da auditlog: ogni creazione/cancellazione lascia
        # diff completo (chi, quando, perché).
        from auditlog.registry import auditlog

        from .models import SimulationReport

        auditlog.register(SimulationReport)
