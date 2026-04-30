"""
Observability — Sentry integration opzionale.

Iter: F-local-product-hardening-pass3-sentry.

Disegno:
- **Lazy import**: `sentry_sdk` viene importato SOLO dentro
  `init_sentry_from_settings()` e SOLO se `SENTRY_DSN` non è
  vuoto. Questo significa che il codebase resta importabile e
  testabile anche senza il pacchetto installato (es. in un
  ambiente locale minimale, o in test che non vogliono toccare
  Sentry).
- **DSN vuoto = no-op**: se `SENTRY_DSN` è "" l'inizializzazione
  ritorna False senza tentare alcun import. Il default in dev è
  vuoto; lo Studio attiva Sentry solo configurando esplicitamente
  l'env in staging/prod.
- **Privacy-first**: `scrub_sentry_event` è una funzione pura,
  testabile senza Sentry installato. Maschera ricorsivamente i
  campi sensibili (email, telefono, nome, messaggi, sessione,
  CSRF, ecc.) in qualunque punto del payload (request body, form
  data, breadcrumbs).
- `send_default_pii=False` di default: Sentry non manda IP né
  user identifiers a meno di esplicita configurazione.

Note:
- La funzione `init_sentry_from_settings` accetta `sentry_init`
  come parametro per dependency injection nei test (così non
  serve sentry-sdk installato per verificare la guard sul DSN
  vuoto).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Privacy scrubber
# ---------------------------------------------------------------------------

# Chiavi (case-insensitive) il cui valore va sempre redatto. La lista
# include sia campi del modello `Lead` (email, phone, ...) che chiavi
# tecniche (CSRF token, session key, cookie). Sentry può raccogliere
# automaticamente request.body / form data / breadcrumbs: questi
# nomi-chiave sono i più comuni vettori di leak PII.
SENSITIVE_KEYS: frozenset[str] = frozenset(
    {
        # PII utente
        "email",
        "phone",
        "phone_number",
        "first_name",
        "last_name",
        "full_name",
        "name",
        "message",
        "internal_notes",
        # Tecnici
        "session_key",
        "sessionid",
        "csrfmiddlewaretoken",
        "csrftoken",
        "user_agent",
        "ip_address",
        "remote_addr",
        # Compliance
        "consent",
        "consent_record",
        "privacy_accepted",
        # Auth
        "password",
        "passwd",
        "secret",
        "api_key",
        "authorization",
        "token",
        # Honeypot (non sensibile, ma irrilevante in event)
        "website",
    }
)

REDACTED_VALUE = "[REDACTED]"


def _key_is_sensitive(key: str) -> bool:
    """Match case-insensitive sulla lista `SENSITIVE_KEYS`."""
    if not isinstance(key, str):
        return False
    return key.lower() in SENSITIVE_KEYS


def _scrub_value(value: Any) -> Any:
    """Walk ricorsivo di dict/list scrub-ando in-place le chiavi sensibili."""
    if isinstance(value, dict):
        for k in list(value.keys()):
            if _key_is_sensitive(k):
                value[k] = REDACTED_VALUE
            else:
                value[k] = _scrub_value(value[k])
        return value
    if isinstance(value, list):
        return [_scrub_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_scrub_value(item) for item in value)
    return value


def scrub_sentry_event(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any]:
    """
    `before_send` hook per Sentry.

    Riceve un `event` (dict serializzabile) e lo restituisce con i
    campi sensibili sostituiti da `[REDACTED]`. Modifica l'event in
    place ma lo ritorna comunque per chiarezza d'uso.

    Mai solleva: in caso di payload inatteso ritorna l'event inalterato
    (Sentry preferisce un evento parzialmente filtrato a un crash del
    client). `hint` è ignorato — accetterlo solo per conformità con la
    firma Sentry.
    """
    del hint  # non usato
    if not isinstance(event, dict):
        return event
    try:
        _scrub_value(event)
    except Exception as exc:  # pragma: no cover — difensivo
        logger.warning("sentry.scrub.failed error=%s", exc.__class__.__name__)
    return event


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------


def init_sentry_from_settings(
    *,
    sentry_init: Callable[..., None] | None = None,
    integrations_factory: Callable[[], list[Any]] | None = None,
) -> bool:
    """
    Inizializza Sentry usando i settings Django.

    Ritorna:
    - `False` se `SENTRY_DSN` è vuoto (skip totale, nessun import).
    - `True` se `sentry_init` è stato chiamato.

    `sentry_init` è opzionale per dependency injection nei test:
    se `None`, la funzione tenta `import sentry_sdk` e usa
    `sentry_sdk.init`. Se sentry-sdk non è installato, solleva
    `ImportError` (è il caso "DSN configurato ma libreria mancante",
    fail-loud è meglio di un silent skip).

    `integrations_factory` consente di produrre la lista di
    integrazioni Django/Celery/Redis solo quando serve (lazy
    import).
    """
    dsn = getattr(settings, "SENTRY_DSN", "") or ""
    if not dsn:
        return False

    environment = getattr(settings, "SENTRY_ENVIRONMENT", "local")
    traces_sample_rate = float(getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", 0.0))
    profiles_sample_rate = float(getattr(settings, "SENTRY_PROFILES_SAMPLE_RATE", 0.0))
    send_default_pii = bool(getattr(settings, "SENTRY_SEND_DEFAULT_PII", False))

    if integrations_factory is None:
        integrations = _default_integrations()
    else:
        integrations = integrations_factory()

    if sentry_init is None:
        import sentry_sdk  # noqa: F401  — late import, may raise ImportError

        sentry_init = sentry_sdk.init

    sentry_init(
        dsn=dsn,
        environment=environment,
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        send_default_pii=send_default_pii,
        before_send=scrub_sentry_event,
        integrations=integrations,
    )
    logger.info(
        "sentry.initialized environment=%s traces_rate=%s profiles_rate=%s pii=%s integrations=%d",
        environment,
        traces_sample_rate,
        profiles_sample_rate,
        send_default_pii,
        len(integrations),
    )
    return True


def _default_integrations() -> list[Any]:
    """
    Costruisce la lista di integrations Sentry. Lazy: importa solo
    quando chiamato. Le singole integrazioni vengono saltate se non
    disponibili (graceful: l'utente può installare sentry-sdk con
    extras minimi).
    """
    integrations: list[Any] = []
    try:
        from sentry_sdk.integrations.django import DjangoIntegration

        integrations.append(DjangoIntegration())
    except ImportError:  # pragma: no cover — extras non installati
        pass
    return integrations
