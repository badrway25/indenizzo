"""
Detector brute-force login admin → `StaffSecurityAlert`.

Iter: F-local-product-hardening-pass9-staff-audit-brute-force-detector.

Disegno:
- **Detection-only**: questo modulo rileva pattern sospetti e li
  registra come `StaffSecurityAlert`. NON blocca login, NON
  blackliste IP, NON disattiva account.
- **Failure-soft**: ogni eccezione è loggata senza PII e
  assorbita; mai propaga al flow di autenticazione.
- **Privacy-first**: lavora solo su `username_hash` e
  `ip_address_masked` di `StaffAccessEvent`. Niente IP/UA raw,
  niente password.
- **Cooldown**: dopo un alert, gli alert successivi per la stessa
  combinazione `(username_hash, ip_address_masked)` vengono
  soppressi finché non scade `cooldown_until`. Evita spam in caso
  di attacco prolungato.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

logger = logging.getLogger(__name__)


def _settings_int(name: str, default: int) -> int:
    return int(getattr(settings, name, default))


def _settings_bool(name: str, default: bool) -> bool:
    return bool(getattr(settings, name, default))


def _settings_list(name: str, default: list[str]) -> list[str]:
    return list(getattr(settings, name, default) or [])


def get_recent_failed_admin_logins(
    *,
    username_hash: str = "",
    ip_address_masked: str = "",
    window_seconds: int,
) -> int:
    """
    Conta i `StaffAccessEvent(event_type=login_failed)` recenti che
    matchano `username_hash` OPPURE `ip_address_masked`.

    Se entrambi gli identificatori sono vuoti, ritorna 0 (niente
    chiave valida → niente match). Funzione pure (lettura DB,
    nessuna scrittura).
    """
    from .models import StaffAccessEvent

    if not username_hash and not ip_address_masked:
        return 0

    threshold_ts = timezone.now() - timedelta(seconds=window_seconds)

    q = Q()
    if username_hash:
        q |= Q(username_hash=username_hash)
    if ip_address_masked:
        q |= Q(ip_address_masked=ip_address_masked)

    return (
        StaffAccessEvent.objects.filter(
            event_type="login_failed",
            created_at__gte=threshold_ts,
        )
        .filter(q)
        .count()
    )


def _has_active_cooldown(
    *,
    alert_type: str,
    username_hash: str,
    ip_address_masked: str,
) -> bool:
    """
    True se esiste un alert attivo (cooldown_until > now) dello
    stesso `alert_type` per la stessa combinazione di
    `username_hash` o `ip_address_masked`.
    """
    from .models import StaffSecurityAlert

    if not username_hash and not ip_address_masked:
        return False

    now = timezone.now()
    q = Q(alert_type=alert_type, cooldown_until__gt=now)

    sub_q = Q()
    if username_hash:
        sub_q |= Q(username_hash=username_hash)
    if ip_address_masked:
        sub_q |= Q(ip_address_masked=ip_address_masked)

    return StaffSecurityAlert.objects.filter(q & sub_q).exists()


def should_create_staff_alert(
    *,
    username_hash: str = "",
    ip_address_masked: str = "",
    threshold: int,
    window_seconds: int,
    alert_type: str = "admin_login_bruteforce",
) -> bool:
    """
    True se l'aggregato di failed login supera la soglia E non c'è
    già un alert attivo (in cooldown) per la stessa combinazione.
    """
    if threshold <= 0:
        return False
    count = get_recent_failed_admin_logins(
        username_hash=username_hash,
        ip_address_masked=ip_address_masked,
        window_seconds=window_seconds,
    )
    if count < threshold:
        return False
    if _has_active_cooldown(
        alert_type=alert_type,
        username_hash=username_hash,
        ip_address_masked=ip_address_masked,
    ):
        return False
    return True


def _send_alert_email(alert: Any) -> bool:
    """
    Invia email di notifica per l'alert appena creato. Privacy-minimized.

    Body include solo:
    - alert_id (PK numerico)
    - alert_type, severity
    - event_count, window_seconds
    - username_hash, ip_address_masked
    - triggered_at ISO

    NON include: IP raw, UA raw, email utente, password.

    Failure-soft: send_mail in `try/except`, log warning senza PII,
    return False.
    """
    if not _settings_bool("STAFF_LOGIN_ALERT_EMAIL_ENABLED", False):
        return False
    recipients = _settings_list("STAFF_LOGIN_ALERT_TO_EMAILS", [])
    if not recipients:
        return False

    from django.core.mail import send_mail

    subject_prefix = getattr(settings, "EMAIL_SUBJECT_PREFIX", "")
    subject = f"{subject_prefix}Admin login alert"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@localhost")

    lines = [
        "A staff security alert has been triggered.",
        "",
        f"Alert id:           {alert.pk}",
        f"Alert type:         {alert.alert_type}",
        f"Severity:           {alert.severity}",
        f"Event count:        {alert.event_count}",
        f"Window (seconds):   {alert.window_seconds}",
        f"Username hash:      {alert.username_hash or '—'}",
        f"IP (masked):        {alert.ip_address_masked or '—'}",
        f"Triggered at (UTC): {alert.triggered_at.isoformat()}",
        f"Cooldown until:     "
        f"{alert.cooldown_until.isoformat() if alert.cooldown_until else '—'}",
        "",
        "This is a detection-only signal. No login was blocked.",
        "Investigate via Django admin → Staff security alerts.",
    ]
    body = "\n".join(lines)
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception as exc:
        logger.warning(
            "compliance.staff_alert.email_failed alert_id=%s error=%s",
            alert.pk,
            exc.__class__.__name__,
        )
        return False
    logger.info(
        "compliance.staff_alert.email_sent alert_id=%s recipients=%d",
        alert.pk,
        len(recipients),
    )
    return True


def create_staff_security_alert_if_needed(event: Any) -> Any | None:
    """
    Punto d'ingresso del detector.

    Argomenti:
    - event: `StaffAccessEvent` appena creato (event_type=login_failed,
      path /admin/...). Se non ha username_hash né ip_address_masked,
      ritorna None.

    Comportamento:
    - Se `STAFF_LOGIN_ALERTS_ENABLED=False`: ritorna None.
    - Calcola count failed login recenti per la combinazione.
    - Se count < threshold o cooldown attivo: ritorna None.
    - Altrimenti: crea `StaffSecurityAlert(severity=medium)`,
      cooldown_until = now + cooldown_seconds; opzionalmente invia
      email; ritorna l'alert.

    Mai solleva.
    """
    try:
        if not _settings_bool("STAFF_LOGIN_ALERTS_ENABLED", True):
            return None

        username_hash = getattr(event, "username_hash", "") or ""
        ip_masked = getattr(event, "ip_address_masked", "") or ""
        if not username_hash and not ip_masked:
            return None

        threshold = _settings_int("STAFF_LOGIN_ALERT_THRESHOLD", 5)
        window = _settings_int("STAFF_LOGIN_ALERT_WINDOW_SECONDS", 900)
        cooldown_s = _settings_int("STAFF_LOGIN_ALERT_COOLDOWN_SECONDS", 3600)
        alert_type = "admin_login_bruteforce"

        if not should_create_staff_alert(
            username_hash=username_hash,
            ip_address_masked=ip_masked,
            threshold=threshold,
            window_seconds=window,
            alert_type=alert_type,
        ):
            return None

        from .models import StaffSecurityAlert

        # Conta esatto al momento della creazione (potrebbe essere
        # diverso da `count` precedente per race condition: usiamo
        # il valore più recente).
        count_now = get_recent_failed_admin_logins(
            username_hash=username_hash,
            ip_address_masked=ip_masked,
            window_seconds=window,
        )
        cooldown_until = timezone.now() + timedelta(seconds=cooldown_s)
        alert = StaffSecurityAlert.objects.create(
            alert_type=alert_type,
            severity=StaffSecurityAlert.Severity.MEDIUM,
            username_hash=username_hash,
            ip_address_masked=ip_masked,
            event_count=count_now,
            window_seconds=window,
            cooldown_until=cooldown_until,
            metadata={
                "reason": "threshold_exceeded",
                "path": getattr(event, "path", "") or "",
                "trigger_event_id": getattr(event, "pk", None),
            },
        )
        logger.info(
            "compliance.staff_alert.created alert_id=%s count=%s window=%ss",
            alert.pk,
            count_now,
            window,
        )
        # Email notify (opzionale, failure-soft)
        _send_alert_email(alert)
        return alert
    except Exception as exc:  # pragma: no cover — difensivo
        logger.warning(
            "compliance.staff_alert.detector_failed error=%s",
            exc.__class__.__name__,
        )
        return None
