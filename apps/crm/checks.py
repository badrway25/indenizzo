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
