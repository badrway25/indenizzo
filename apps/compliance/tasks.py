"""
Celery tasks per la app compliance.

Iter: F-local-product-hardening-pass10-staff-audit-cleanup-task.

Tasks:
- `cleanup_staff_audit_task()` — wrapper Celery del management
  command `cleanup_staff_audit`. Legge `STAFF_AUDIT_RETENTION_*`
  dal settings e chiama `cleanup_staff_audit_events`.

Note:
- Questo iter NON aggiunge Celery Beat: il task è solo invocabile
  manualmente (`celery -A config call apps.compliance.tasks.cleanup_staff_audit_task`)
  o via shell. Lo scheduling notturno verrà aggiunto in un pass
  futuro quando Beat sarà cablato.
- Failure-soft: eccezioni loggate senza PII, mai propagate al
  worker (evitiamo che un errore del task tiri giù il worker).
"""

from __future__ import annotations

import logging

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


@shared_task(name="apps.compliance.tasks.cleanup_staff_audit_task")
def cleanup_staff_audit_task() -> dict:
    """
    Esegue il cleanup retention staff audit.

    Comportamento:
    - Se `STAFF_AUDIT_RETENTION_ENABLED=False`: ritorna un dict
      `{"skipped": "disabled"}` senza toccare DB.
    - Altrimenti chiama `cleanup_staff_audit_events(dry_run=...)`
      con `dry_run` letto da `STAFF_AUDIT_RETENTION_DRY_RUN`
      (default True per sicurezza).

    Ritorna il dict prodotto dal cleanup (counts + flag dry-run).
    Logga sempre i counts (no PII).
    """
    if not bool(getattr(settings, "STAFF_AUDIT_RETENTION_ENABLED", True)):
        logger.info("compliance.staff_audit_cleanup.skipped reason=disabled")
        return {"skipped": "disabled"}

    dry_run = bool(getattr(settings, "STAFF_AUDIT_RETENTION_DRY_RUN", True))

    # Lazy import per non forzare il caricamento di tutta la app
    # compliance al momento dell'autodiscover Celery.
    from .retention import cleanup_staff_audit_events

    try:
        result = cleanup_staff_audit_events(dry_run=dry_run)
    except Exception as exc:
        logger.warning(
            "compliance.staff_audit_cleanup.failed error=%s",
            exc.__class__.__name__,
        )
        return {"error": exc.__class__.__name__}

    logger.info(
        "compliance.staff_audit_cleanup.completed "
        "dry_run=%s access_expired=%s alerts_expired=%s "
        "access_deleted=%s alerts_deleted=%s",
        result.get("dry_run"),
        result.get("access_expired"),
        result.get("alerts_expired"),
        result.get("access_deleted"),
        result.get("alerts_deleted"),
    )
    return result
