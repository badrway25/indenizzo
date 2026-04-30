"""
Celery tasks per il CRM.

Iter: F-local-product-hardening-pass7-celery-async.

Disegno:
- Task fire-and-forget: `send_lead_notification_task(lead_id)`
  carica il `Lead` dal DB e delega a
  `apps.crm.email_notifications.send_lead_notification`.
- Idempotency: il task è safe da retry: la funzione sottostante
  è già failure-soft. Multipli retry possono al peggio inviare
  la stessa email N volte allo Studio (preferibile alla perdita
  silenziosa).
- No PII nei log: si emette solo `lead_id` (PK numerico interno) +
  `error.__class__.__name__`.
- Retry policy: 3 tentativi, backoff lineare 60s. Fine-tuning
  rinviato a quando avremo metriche reali (vedi
  `LOCAL_PRODUCT_HARDENING_PASS7_CELERY.md` §10).
"""

from __future__ import annotations

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,
    name="apps.crm.tasks.send_lead_notification_task",
)
def send_lead_notification_task(self, lead_id: int) -> bool:
    """
    Invia la notifica email allo Studio per il `Lead` con `pk=lead_id`.

    Ritorna True se l'email è stata inoltrata al backend, False se la
    notifica è disattivata, il Lead non esiste, o il send è fallito
    in modo non-retriable.

    Sollevamenti gestiti:
    - `Lead.DoesNotExist` → log warning + return False (no retry: il
      Lead potrebbe essere stato cancellato post-creazione).
    - Eccezioni non previste → `self.retry(exc=...)` con backoff.
      Dopo `max_retries`, il task viene marcato come failed e l'errore
      è emesso nei log Celery.
    """
    # Lazy import per non rompere l'autodiscover se Django non è
    # bootstrappato al momento dell'import del modulo.
    from .email_notifications import send_lead_notification
    from .models import Lead

    try:
        lead = Lead.objects.get(pk=lead_id)
    except Lead.DoesNotExist:
        logger.warning("crm.lead.notification.task.lead_not_found pk=%s", lead_id)
        return False

    try:
        return send_lead_notification(lead)
    except Exception as exc:  # pragma: no cover — il send è già
        # failure-soft, ma copriamo eventuali eccezioni inattese
        # nel layer di trasporto Celery (es. timeout broker durante
        # il return).
        logger.warning(
            "crm.lead.notification.task.unexpected_error pk=%s error=%s",
            lead_id,
            exc.__class__.__name__,
        )
        try:
            raise self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            return False
