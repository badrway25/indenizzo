"""
Notifica email transazionale al Studio quando arriva un nuovo Lead.

Iter: F-local-product-hardening-pass2-email-lead.

Disegno:
- Plaintext only. Niente HTML, niente tracking pixel, niente
  unsubscribe link (è un'email transazionale interna, non
  marketing).
- Privacy minimization: il body riporta solo i campi necessari
  allo Studio per richiamare il cliente. Sono volutamente esclusi
  `ip_address`, `user_agent`, `session_key`, `internal_notes` —
  questi restano consultabili in admin se servono e non vanno
  duplicati in inbox.
- Failure-soft: una send fallita NON deve rompere la creazione
  del Lead. Si logga un warning (senza PII) e si ritorna False.
- Disabilitazione: se `LEAD_NOTIFICATION_ENABLED=False` o se la
  lista destinatari è vuota, la funzione esce senza chiamate
  SMTP e ritorna False.
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import send_mail
from django.urls import NoReverseMatch, reverse

from .models import Lead

logger = logging.getLogger(__name__)


def _build_admin_link(lead: Lead, request: Any | None) -> str:
    """
    URL al record admin del Lead. Relativo se non c'è request,
    assoluto altrimenti. Se l'URL admin non è risolvibile, ritorna
    stringa vuota (la mail si manda comunque).
    """
    try:
        path = reverse("admin:crm_lead_change", args=[lead.pk])
    except NoReverseMatch:
        return ""
    if request is not None:
        try:
            return request.build_absolute_uri(path)
        except Exception:
            return path
    return path


def _build_body(lead: Lead, request: Any | None) -> str:
    """Compose plaintext body. Privacy-minimized."""
    country_code = lead.country.code if lead.country_id else "—"
    case_type = lead.case_type or "—"
    phone = lead.phone_number or "—"
    sim = lead.simulation
    sim_public_id = str(sim.public_id) if sim is not None else ""
    admin_link = _build_admin_link(lead, request)

    lines = [
        "A new legal review request has been received via the public",
        "/contact/ form.",
        "",
        f"Lead public_id:       {lead.public_id}",
        f"Received at (UTC):    {lead.created_at.isoformat()}",
        f"Status:               {lead.status}",
        "",
        f"Name:                 {lead.full_name}",
        f"Email:                {lead.email}",
        f"Phone:                {phone}",
        f"Preferred language:   {lead.preferred_language}",
        f"Country:              {country_code}",
        f"Case type:            {case_type}",
    ]
    if sim_public_id:
        lines.append(f"Linked simulation:    {sim_public_id}")
    if admin_link:
        lines.extend(["", f"Admin link: {admin_link}"])
    lines.extend(
        [
            "",
            "This is an automated transactional notification. Do not reply.",
            "Contact details are visible in the Studio admin only.",
        ]
    )
    return "\n".join(lines)


def send_lead_notification(lead: Lead, *, request: Any | None = None) -> bool:
    """
    Invia la notifica email al Studio per il `lead` appena creato.

    Ritorna True se l'email è stata inoltrata al backend (anche se il
    backend è `console` o `locmem`), False se la notifica è disattivata
    o se la send è fallita.

    Non solleva mai: gli errori vengono loggati e assorbiti.
    """
    if not getattr(settings, "LEAD_NOTIFICATION_ENABLED", False):
        return False

    recipients = list(getattr(settings, "LEAD_NOTIFICATION_TO_EMAILS", []) or [])
    if not recipients:
        # Disattivazione implicita: nessun destinatario configurato.
        return False

    subject_prefix = getattr(settings, "EMAIL_SUBJECT_PREFIX", "")
    subject = f"{subject_prefix}New legal review request"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@localhost")

    try:
        body = _build_body(lead, request)
        send_mail(
            subject=subject,
            message=body,
            from_email=from_email,
            recipient_list=recipients,
            fail_silently=False,
        )
    except Exception as exc:
        # Log senza PII: solo public_id + classe errore. Niente body
        # (potrebbe contenere PII) e niente recipients (potrebbero
        # essere considerati staff PII in alcuni contesti).
        logger.warning(
            "crm.lead.notification.failed public_id=%s error=%s",
            lead.public_id,
            exc.__class__.__name__,
        )
        return False

    logger.info(
        "crm.lead.notification.sent public_id=%s recipients=%d",
        lead.public_id,
        len(recipients),
    )
    return True
