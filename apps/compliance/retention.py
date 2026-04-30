"""
Retention policy per gli audit log staff.

Iter: F-local-product-hardening-pass10-staff-audit-cleanup-task.

Disegno:
- **Solo audit staff**: il modulo opera SOLO su `StaffAccessEvent`
  (pass 8) e `StaffSecurityAlert` (pass 9). NON tocca
  `PrivacyAuditEvent`, `LegalReview`, `SimulationReport`,
  `ConsentRecord`, `Lead`, `Simulation`. Quei modelli hanno
  policy diverse (legal hold, retention regolatoria, ecc.).
- **Dry-run-first**: tutte le funzioni accettano `dry_run` con
  default sicuro `True`. Il caller (management command, Celery
  task) decide esplicitamente quando passare a `False`.
- **Funzioni pure**: `get_staff_audit_retention_cutoffs` e
  `count_expired_staff_audit_events` sono read-only.
- **Determinismo nei test**: tutte le funzioni accettano `now`
  iniettabile per pinnare l'orologio.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone


def _settings_int(name: str, default: int) -> int:
    return int(getattr(settings, name, default))


def get_staff_audit_retention_cutoffs(now: datetime | None = None) -> dict:
    """
    Calcola i cutoff datetime per la retention staff audit.

    Ritorna:
    - `staff_access_cutoff`: gli StaffAccessEvent con
      `created_at < this` sono considerati expired.
    - `staff_alert_cutoff`: gli StaffSecurityAlert con
      `triggered_at < this` sono considerati expired.

    Le retention sono lette da settings:
    `STAFF_ACCESS_EVENT_RETENTION_DAYS` (default 90),
    `STAFF_SECURITY_ALERT_RETENTION_DAYS` (default 180).
    """
    if now is None:
        now = timezone.now()
    access_days = _settings_int("STAFF_ACCESS_EVENT_RETENTION_DAYS", 90)
    alert_days = _settings_int("STAFF_SECURITY_ALERT_RETENTION_DAYS", 180)
    return {
        "now": now,
        "staff_access_cutoff": now - timedelta(days=access_days),
        "staff_alert_cutoff": now - timedelta(days=alert_days),
        "staff_access_retention_days": access_days,
        "staff_alert_retention_days": alert_days,
    }


def count_expired_staff_audit_events(now: datetime | None = None) -> dict:
    """Conta i record expired SENZA cancellare nulla."""
    from .models import StaffAccessEvent, StaffSecurityAlert

    cutoffs = get_staff_audit_retention_cutoffs(now=now)
    access_expired = StaffAccessEvent.objects.filter(
        created_at__lt=cutoffs["staff_access_cutoff"]
    ).count()
    alerts_expired = StaffSecurityAlert.objects.filter(
        triggered_at__lt=cutoffs["staff_alert_cutoff"]
    ).count()
    return {
        **cutoffs,
        "access_expired": access_expired,
        "alerts_expired": alerts_expired,
    }


def cleanup_staff_audit_events(
    *,
    dry_run: bool = True,
    now: datetime | None = None,
) -> dict:
    """
    Esegue la cancellazione (o il dry-run) degli audit staff
    expired secondo la retention policy.

    - `dry_run=True` (default): conta gli expired e ritorna senza
      cancellare. `access_deleted` e `alerts_deleted` sono 0.
    - `dry_run=False`: cancella i record expired e ritorna i conteggi
      effettivi cancellati.

    Ritorna un dict con:
    - `now`, `staff_access_cutoff`, `staff_alert_cutoff`
    - `staff_access_retention_days`, `staff_alert_retention_days`
    - `access_expired`, `alerts_expired` (count pre-delete)
    - `access_deleted`, `alerts_deleted` (count effettivi)
    - `dry_run` (bool, eco)

    NON tocca altri modelli (PrivacyAuditEvent, LegalReview,
    SimulationReport, ConsentRecord, Lead, Simulation, ecc.).
    """
    from .models import StaffAccessEvent, StaffSecurityAlert

    snapshot = count_expired_staff_audit_events(now=now)

    access_deleted = 0
    alerts_deleted = 0
    if not dry_run:
        # Solo i record sotto cutoff: la query è strettamente
        # filtrata per evitare cancellazioni accidentali di record
        # recenti.
        access_qs = StaffAccessEvent.objects.filter(created_at__lt=snapshot["staff_access_cutoff"])
        alert_qs = StaffSecurityAlert.objects.filter(
            triggered_at__lt=snapshot["staff_alert_cutoff"]
        )
        # `delete()` ritorna `(total, {model_label: count})`.
        access_deleted, _ = access_qs.delete()
        alerts_deleted, _ = alert_qs.delete()

    return {
        **snapshot,
        "access_deleted": int(access_deleted),
        "alerts_deleted": int(alerts_deleted),
        "dry_run": bool(dry_run),
    }
