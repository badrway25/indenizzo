"""
Django system checks per `apps.crm`.

Iter: F-p0-codice-1-crm-system-check (audit/indennizzati-platform).

Scopo: bloccare `manage.py check` (e quindi il deploy in produzione)
quando la notifica email Lead allo Studio risulta abilitata ma senza
destinatari configurati. Un Lead arriverebbe in DB ma nessuna email
verrebbe inviata, perdendo silenziosamente la richiesta.

Logica:
- Si attiva solo in scenario *production-like* (`DEBUG=False`).
- Non disturba dev locale (`DEBUG=True`) né test ordinari (pytest
  setta `DEBUG=False` ma resta una test-suite, non un deploy).
  Per i test-only, il check resta valido perche' simula la
  situazione reale di produzione e va testato esplicitamente
  (vedi `apps/crm/test_checks.py`).
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, register


@register("crm")
def check_lead_notification_recipients(app_configs, **kwargs):
    """
    `crm.E001` — fail in produzione se la notifica email Lead e'
    abilitata ma senza destinatari.

    Condizione di failure (tutte e tre):
    - `DEBUG=False` (deploy produzione);
    - `LEAD_NOTIFICATION_ENABLED=True`;
    - `LEAD_NOTIFICATION_TO_EMAILS` vuoto / non configurato.

    Hint: settare `DJANGO_LEAD_NOTIFICATION_TO_EMAILS=lead@…` o
    disabilitare `LEAD_NOTIFICATION_ENABLED` prima del deploy.
    """
    errors: list[Error] = []

    # Scenario production-like: il check scatta solo se DEBUG=False.
    # Cosi' lo sviluppatore locale (DEBUG=True) non viene disturbato
    # mentre lavora senza un'inbox di test configurata.
    if getattr(settings, "DEBUG", False):
        return errors

    enabled = bool(getattr(settings, "LEAD_NOTIFICATION_ENABLED", False))
    recipients = list(getattr(settings, "LEAD_NOTIFICATION_TO_EMAILS", []) or [])

    if enabled and not recipients:
        errors.append(
            Error(
                (
                    "LEAD_NOTIFICATION_ENABLED=True but "
                    "LEAD_NOTIFICATION_TO_EMAILS is empty. Lead form "
                    "submissions would be persisted to the DB but no "
                    "transactional email would reach the Studio."
                ),
                hint=(
                    "Set LEAD_NOTIFICATION_TO_EMAILS or disable "
                    "LEAD_NOTIFICATION_ENABLED before production deploy."
                ),
                id="crm.E001",
            )
        )

    return errors


_MIN_SECRET_LEN = 32


@register("crm")
def check_crm_webhook_configuration_in_production(app_configs, **kwargs):
    """
    `crm.E002` / `crm.E003` — fail in produzione quando
    `CRM_WEBHOOK_ENABLED=True` e l'endpoint/secret CRM non sono
    configurati correttamente.

    Validazioni:
    - URL valorizzato e su `https://` (E002);
    - secret valorizzato, almeno 32 caratteri (E002);
    - timeout > 0 (E003);
    - max_attempts >= 1 (E003).

    In dev (`DEBUG=True`) il check e' silenzioso.
    """
    if getattr(settings, "DEBUG", False):
        return []
    if not getattr(settings, "CRM_WEBHOOK_ENABLED", False):
        # Default OFF -> nessun controllo necessario.
        return []

    errors: list[Error] = []

    url = (getattr(settings, "CRM_WEBHOOK_URL", "") or "").strip()
    if not url:
        errors.append(
            Error(
                "CRM_WEBHOOK_ENABLED=True but CRM_WEBHOOK_URL is empty. "
                "The dispatcher would refuse to send any delivery.",
                hint="Set CRM_WEBHOOK_URL to the production endpoint (https://...).",
                id="crm.E002",
            )
        )
    elif not url.lower().startswith("https://"):
        errors.append(
            Error(
                f"CRM_WEBHOOK_URL={url!r} must be served over HTTPS in "
                "production. The dispatcher refuses to ship credentials over "
                "a plaintext channel.",
                hint="Use an https:// URL or terminate TLS in front of the n8n endpoint.",
                id="crm.E002",
            )
        )

    secret = getattr(settings, "CRM_WEBHOOK_SECRET", "") or ""
    if not secret:
        errors.append(
            Error(
                "CRM_WEBHOOK_ENABLED=True but CRM_WEBHOOK_SECRET is empty. "
                "Every delivery would carry an unsigned payload.",
                hint="Set CRM_WEBHOOK_SECRET to a high-entropy random string.",
                id="crm.E002",
            )
        )
    elif len(secret) < _MIN_SECRET_LEN:
        errors.append(
            Error(
                f"CRM_WEBHOOK_SECRET is only {len(secret)} chars; minimum is "
                f"{_MIN_SECRET_LEN} for HMAC-SHA256 signing strength.",
                hint=(
                    "Generate a longer secret, e.g. "
                    "`python -c \"import secrets;print(secrets.token_urlsafe(48))\"`."
                ),
                id="crm.E002",
            )
        )

    timeout = int(getattr(settings, "CRM_WEBHOOK_TIMEOUT_SECONDS", 0) or 0)
    if timeout <= 0:
        errors.append(
            Error(
                f"CRM_WEBHOOK_TIMEOUT_SECONDS={timeout} must be a positive integer.",
                hint="A small positive value (e.g. 10) is sane; 0 or negative blocks the dispatcher.",
                id="crm.E003",
            )
        )

    attempts = int(getattr(settings, "CRM_WEBHOOK_MAX_ATTEMPTS", 0) or 0)
    if attempts < 1:
        errors.append(
            Error(
                f"CRM_WEBHOOK_MAX_ATTEMPTS={attempts} must be >= 1.",
                hint="Default 5 is reasonable; 0 would mark every delivery dead immediately.",
                id="crm.E003",
            )
        )

    return errors
