"""
Servizi compliance.

Tutte le funzioni qui sono pensate per essere chiamate da view, signal,
management command. Nessuna di esse logga payload utente: i log sono
limitati a fatti tecnici (event_type, model name, object id).

Convenzioni:
- `request` può essere None (es. management command, signal): in tal caso
  IP/UA/path restano stringhe vuote;
- gli ID utente sono passati per FK, mai per username/email nei log;
- `record_consent` e `log_privacy_event` sono idempotenti rispetto a
  errori di IO: se il DB fallisce, l'eccezione propaga (non silenziata).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.utils import timezone

from .models import (
    ConsentPurpose,
    ConsentRecord,
    ConsentTextVersion,
    PrivacyAuditEvent,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RequestMeta:
    """Snapshot dei dati tecnici di una request, mai PII utente."""

    ip_address: str | None
    user_agent: str
    path: str
    locale: str
    session_key: str


def _first_forwarded_ip(value: str) -> str:
    """Estrai il primo IP da X-Forwarded-For. Mai loggare il valore intero."""
    if not value:
        return ""
    return value.split(",")[0].strip()


def get_request_meta(request: Any | None) -> RequestMeta:
    """
    Estrai i metadata tecnici da una HttpRequest senza toccarne il body.

    Tollerante a request=None (utile per service chiamati da CLI/signal).
    """
    if request is None:
        return RequestMeta(
            ip_address=None,
            user_agent="",
            path="",
            locale="",
            session_key="",
        )

    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    ip = _first_forwarded_ip(forwarded) or request.META.get("REMOTE_ADDR") or None

    user_agent = (request.META.get("HTTP_USER_AGENT") or "")[:512]
    path = (getattr(request, "path", "") or "")[:512]
    locale = getattr(request, "LANGUAGE_CODE", "") or ""

    session = getattr(request, "session", None)
    session_key = getattr(session, "session_key", "") or ""

    return RequestMeta(
        ip_address=ip or None,
        user_agent=user_agent,
        path=path,
        locale=locale,
        session_key=session_key,
    )


def record_consent(
    *,
    purpose: ConsentPurpose,
    accepted: bool,
    request: Any | None = None,
    user: Any | None = None,
    text_version: ConsentTextVersion | None = None,
    metadata: dict | None = None,
) -> ConsentRecord:
    """
    Registra un atto di consenso.

    `user` e `request` sono entrambi opzionali: il consenso può essere
    raccolto da utente anonimo (solo session_key) o da CLI (nessuno dei due).
    `metadata` è per dati tecnici, NON per testo libero utente.
    """
    meta = get_request_meta(request)
    resolved_user = user
    if resolved_user is None and request is not None:
        candidate = getattr(request, "user", None)
        if candidate is not None and getattr(candidate, "is_authenticated", False):
            resolved_user = candidate

    record = ConsentRecord.objects.create(
        user=resolved_user,
        session_key=meta.session_key,
        purpose=purpose,
        text_version=text_version,
        accepted=accepted,
        accepted_at=timezone.now(),
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
        locale=meta.locale,
        source_path=meta.path,
        metadata=dict(metadata or {}),
    )
    logger.info(
        "consent.recorded purpose=%s accepted=%s user_id=%s",
        purpose.code,
        accepted,
        getattr(resolved_user, "pk", None),
    )
    return record


def has_consent(
    *,
    purpose_code: str,
    user: Any | None = None,
    session_key: str = "",
) -> bool:
    """
    True se esiste un ConsentRecord positivo (accepted=True) recente per
    `user` o `session_key` sulla finalità indicata.

    "Recente" qui significa: l'ultimo record cronologico per quel soggetto
    su quella finalità è positivo. Un consenso ritirato (record successivo
    con accepted=False) annulla il precedente.
    """
    if user is None and not session_key:
        return False

    qs = ConsentRecord.objects.filter(purpose__code=purpose_code)
    if user is not None and getattr(user, "is_authenticated", False):
        qs = qs.filter(user=user)
    elif session_key:
        qs = qs.filter(session_key=session_key)
    else:
        return False

    latest = qs.order_by("-accepted_at").first()
    return bool(latest and latest.accepted)


def log_privacy_event(
    *,
    event_type: str,
    request: Any | None = None,
    actor: Any | None = None,
    target_model: str = "",
    target_object_id: str | int = "",
    metadata: dict | None = None,
) -> PrivacyAuditEvent:
    """
    Registra un evento di audit privacy.

    Mai chiamare con `metadata` contenente dati personali utente:
    è solo per contesto tecnico (es. {"reason": "user_request"}).
    """
    meta = get_request_meta(request)
    resolved_actor = actor
    if resolved_actor is None and request is not None:
        candidate = getattr(request, "user", None)
        if candidate is not None and getattr(candidate, "is_authenticated", False):
            resolved_actor = candidate

    event = PrivacyAuditEvent.objects.create(
        actor=resolved_actor,
        event_type=event_type,
        target_model=target_model or "",
        target_object_id=str(target_object_id or ""),
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
        path=meta.path,
        metadata=dict(metadata or {}),
    )
    logger.info(
        "privacy.event type=%s target=%s:%s actor_id=%s",
        event_type,
        target_model,
        target_object_id,
        getattr(resolved_actor, "pk", None),
    )
    return event
