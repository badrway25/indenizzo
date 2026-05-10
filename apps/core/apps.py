import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    label = "core"

    def ready(self) -> None:
        # F-p0-codice-3-footer: registra system check core.E001/W001 sui
        # campi obbligatori del footer professionale.
        from . import checks  # noqa: F401

        # Sentry init opzionale: se SENTRY_DSN è vuoto la funzione
        # ritorna False senza tentare l'import di sentry_sdk. In caso
        # di import error con DSN configurato, logghiamo ma non
        # blocchiamo l'avvio (fail-soft per non rompere management
        # commands locali).
        try:
            from .observability import init_sentry_from_settings

            init_sentry_from_settings()
        except ImportError:
            logger.warning(
                "sentry.init.skipped reason=missing_dependency. "
                "Install sentry-sdk to enable error monitoring."
            )
        except Exception as exc:
            logger.warning(
                "sentry.init.skipped reason=unexpected_error class=%s",
                exc.__class__.__name__,
            )
