"""
Django auth signals → `StaffAccessEvent`.

Iter: F-local-product-hardening-pass8-audit-log-staff-access.

Disegno:
- Tre handler agganciati a `user_logged_in`, `user_login_failed`,
  `user_logged_out`. Tutti read-only sull'auth flow: NON bloccano
  il login né lo modificano. Il loro unico effetto è scrivere
  una riga in `StaffAccessEvent`.
- **Filtro per ridurre rumore**: registriamo solo se il request
  arriva da `/admin/...` oppure se l'utente è staff/superuser. Il
  funnel pubblico (`/contact/`, `/wizard/...`) NON viene loggato
  qui (i Lead/ConsentRecord coprono già quei percorsi).
- Failure-soft: nessuna eccezione del handler propaga al flow
  Django. In caso di errore (es. DB write fallito), si logga un
  warning e si ignora.
"""

from __future__ import annotations

import logging
from typing import Any

from django.contrib.auth.signals import (
    user_logged_in,
    user_logged_out,
    user_login_failed,
)
from django.dispatch import receiver

from .privacy_helpers import build_staff_access_event_kwargs

logger = logging.getLogger(__name__)


def _is_admin_path(request: Any | None) -> bool:
    if request is None:
        return False
    path = getattr(request, "path", "") or ""
    return path.startswith("/admin/")


def _is_staff_user(user: Any | None) -> bool:
    if user is None:
        return False
    return bool(getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))


def _create_event(*, event_type: str, request, user, username):
    # Lazy import per evitare circular import durante app loading.
    from .models import StaffAccessEvent

    kwargs = build_staff_access_event_kwargs(
        event_type=event_type,
        request=request,
        user=user,
        username=username,
    )
    try:
        event = StaffAccessEvent.objects.create(**kwargs)
    except Exception as exc:  # pragma: no cover — difensivo
        logger.warning(
            "compliance.staff_access_event.write_failed event=%s error=%s",
            event_type,
            exc.__class__.__name__,
        )
        return None
    # Pass 9: dopo aver registrato un login_failed admin, attiva il
    # detector brute-force. Failure-soft: la funzione non solleva mai.
    if event_type == "login_failed":
        from .staff_security import create_staff_security_alert_if_needed

        create_staff_security_alert_if_needed(event)
    return event


@receiver(user_logged_in)
def _on_user_logged_in(sender, request, user, **kwargs):
    """Logga login_success solo per staff o path admin."""
    if not (_is_admin_path(request) or _is_staff_user(user)):
        return
    _create_event(
        event_type="login_success",
        request=request,
        user=user,
        username=None,  # derivato da user.get_username()
    )


@receiver(user_logged_out)
def _on_user_logged_out(sender, request, user, **kwargs):
    """Logga logout solo per staff o path admin."""
    if not (_is_admin_path(request) or _is_staff_user(user)):
        return
    _create_event(
        event_type="logout",
        request=request,
        user=user,
        username=None,
    )


@receiver(user_login_failed)
def _on_user_login_failed(sender, credentials, request=None, **kwargs):
    """
    Logga login_failed solo se il request arriva da `/admin/...`.

    `user` è None per definizione (login fallito). `credentials` è
    un dict tipico `{"username": "...", "password": "..."}`. Estraiamo
    SOLO l'username (sarà hashato), MAI la password.
    """
    if not _is_admin_path(request):
        return
    username = ""
    if isinstance(credentials, dict):
        username = credentials.get("username") or credentials.get("email") or ""
    _create_event(
        event_type="login_failed",
        request=request,
        user=None,
        username=username,
    )
