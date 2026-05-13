"""
Retention policy.

Due iter coabitano in questo modulo:

1. **Staff audit** (F-local-product-hardening-pass10-staff-audit-cleanup-task)
   — `cleanup_staff_audit_events` opera SOLO su `StaffAccessEvent` e
   `StaffSecurityAlert`. Pre-esistente, non toccato.

2. **Wide retention** (F-p0-leg-4-retention) — `run_retention` orchestra
   `Lead`, `Simulation`, `ConsentRecord`, `PrivacyAuditEvent`. Scaffold
   tecnico: i giorni di default sono valori di sviluppo, lo Studio firma
   la policy reale prima del go-live.

Disegno comune:
- **Dry-run-first**: tutte le funzioni accettano `dry_run`/`mode` con
  default sicuro. Il caller decide esplicitamente quando passare ad
  azione reale.
- **Funzioni pure**: `get_*_cutoffs` e `count_*` sono read-only.
- **Determinismo nei test**: tutte le funzioni accettano `now`
  iniettabile per pinnare l'orologio.
- **Anonymize prima di delete**: il delete fisico di Lead/Simulation
  non gira mai senza configurazione esplicita. Per scaffold P0 il delete
  e' supportato a livello di codice ma rifiutato finche' la policy non
  e' firmata e l'operatore non passa `--yes-i-understand`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

# Modalita' ammesse per la wide retention. Coerenti con
# `RetentionRunLog.Mode.choices`.
RETENTION_MODES = ("dry_run", "anonymize", "delete")
DRAFT_MARKERS = ("working-copy", "draft")


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


# ---------------------------------------------------------------------------
# Wide retention (F-p0-leg-4-retention)
#
# Coordina Lead, Simulation, ConsentRecord, PrivacyAuditEvent. Il delete
# fisico e' previsto dalla configurazione ma in P0 viene rifiutato:
# permettiamo solo dry_run e anonymize, salvo deroga esplicita.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetentionCutoffs:
    """Snapshot dei cutoff calcolati una sola volta per run."""

    now: datetime
    lead_cutoff: datetime
    simulation_cutoff: datetime
    consent_cutoff: datetime
    audit_cutoff: datetime
    lead_days: int
    simulation_days: int
    consent_days: int
    audit_days: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "now": self.now,
            "lead_cutoff": self.lead_cutoff,
            "simulation_cutoff": self.simulation_cutoff,
            "consent_cutoff": self.consent_cutoff,
            "audit_cutoff": self.audit_cutoff,
            "lead_days": self.lead_days,
            "simulation_days": self.simulation_days,
            "consent_days": self.consent_days,
            "audit_days": self.audit_days,
        }


def get_retention_cutoffs(now: datetime | None = None) -> RetentionCutoffs:
    """
    Calcola i cutoff per la wide retention dai settings.

    Le retention sono lette da:
    - `RETENTION_LEAD_DAYS`         (default dev 365)
    - `RETENTION_SIMULATION_DAYS`   (default dev 365)
    - `RETENTION_CONSENT_RECORD_DAYS` (default dev 1825)
    - `RETENTION_AUDIT_LOG_DAYS`    (default dev 1825)
    """
    if now is None:
        now = timezone.now()
    lead_days = _settings_int("RETENTION_LEAD_DAYS", 365)
    sim_days = _settings_int("RETENTION_SIMULATION_DAYS", 365)
    consent_days = _settings_int("RETENTION_CONSENT_RECORD_DAYS", 1825)
    audit_days = _settings_int("RETENTION_AUDIT_LOG_DAYS", 1825)
    return RetentionCutoffs(
        now=now,
        lead_cutoff=now - timedelta(days=lead_days),
        simulation_cutoff=now - timedelta(days=sim_days),
        consent_cutoff=now - timedelta(days=consent_days),
        audit_cutoff=now - timedelta(days=audit_days),
        lead_days=lead_days,
        simulation_days=sim_days,
        consent_days=consent_days,
        audit_days=audit_days,
    )


def collect_retention_candidates(now: datetime | None = None) -> dict[str, Any]:
    """
    Conta i record candidati alla retention SENZA modificarli.

    `lead_candidates`: Lead non gia' anonymized con `created_at < lead_cutoff`.
    `simulation_candidates`: Simulation non gia' anonymized con
        `created_at < simulation_cutoff`.
    `consent_candidates`: ConsentRecord con `accepted_at < consent_cutoff`.
        Conta soltanto: in P0 NON cancelliamo i ConsentRecord, perche'
        sono prova del consenso e potrebbero richiedere conservazione
        prolungata.
    `audit_candidates`: PrivacyAuditEvent con `created_at < audit_cutoff`.
    """
    from apps.cases.models import Simulation
    from apps.crm.models import Lead

    from .models import ConsentRecord, PrivacyAuditEvent

    cutoffs = get_retention_cutoffs(now=now)
    lead_qs = Lead.objects.filter(
        anonymized=False, created_at__lt=cutoffs.lead_cutoff
    )
    sim_qs = Simulation.objects.filter(
        anonymized=False, created_at__lt=cutoffs.simulation_cutoff
    )
    consent_qs = ConsentRecord.objects.filter(accepted_at__lt=cutoffs.consent_cutoff)
    audit_qs = PrivacyAuditEvent.objects.filter(created_at__lt=cutoffs.audit_cutoff)
    return {
        "cutoffs": cutoffs.to_dict(),
        "lead_candidates": lead_qs.count(),
        "simulation_candidates": sim_qs.count(),
        "consent_candidates": consent_qs.count(),
        "audit_candidates": audit_qs.count(),
    }


def _anonymize_lead_inplace(lead) -> None:
    """
    Sostituisce i campi PII di un Lead con valori sentinel.

    Mantiene:
    - `public_id`, `created_at`, `country_id`, `case_type`,
      `preferred_language`, `status`, `priority`, `utm_*`,
    - i campi `*_consent_*` (versione, timestamp, given) come prova
      del consenso fornito,
    - `consent_record` FK (il ledger ConsentRecord vive piu' a lungo).

    Anonymizza:
    - first_name, last_name, email, phone_number, message,
      ip_address, user_agent, source_path, session_key, internal_notes,
      assigned_to.

    Idempotente: se gia' anonymized non rifa' nulla.
    """
    if lead.anonymized:
        return
    lead.first_name = ""
    lead.last_name = ""
    lead.email = "anonymized@example.invalid"
    lead.phone_number = ""
    lead.message = ""
    lead.ip_address = None
    lead.user_agent = ""
    lead.source_path = ""
    lead.session_key = ""
    lead.internal_notes = ""
    lead.assigned_to = None
    lead.user = None
    lead.anonymized = True
    lead.anonymized_at = timezone.now()
    lead.save(
        update_fields=[
            "first_name",
            "last_name",
            "email",
            "phone_number",
            "message",
            "ip_address",
            "user_agent",
            "source_path",
            "session_key",
            "internal_notes",
            "assigned_to",
            "user",
            "anonymized",
            "anonymized_at",
        ]
    )


def _anonymize_simulation_inplace(simulation) -> None:
    """
    Anonymizza una Simulation. Riusa il pattern di
    `apps.cases.services.anonymize_simulation` ma evita la dipendenza
    circolare scrivendo direttamente sui campi.
    """
    if simulation.anonymized:
        return
    simulation.input_data = {"_anonymized": True}
    simulation.session_key = ""
    simulation.ip_address = None
    simulation.user_agent = ""
    simulation.source_path = ""
    simulation.user = None
    simulation.anonymized = True
    simulation.anonymized_at = timezone.now()
    simulation.save(
        update_fields=[
            "input_data",
            "session_key",
            "ip_address",
            "user_agent",
            "source_path",
            "user",
            "anonymized",
            "anonymized_at",
        ]
    )


def run_retention(
    *,
    mode: str = "dry_run",
    now: datetime | None = None,
    executed_by: str = "system",
    notes: str = "",
    allow_delete: bool = False,
) -> dict[str, Any]:
    """
    Orchestra una run di wide retention.

    Crea un `RetentionRunLog` (status=started) PRIMA di toccare la
    base dati. Lo aggiorna a success/failed al termine.

    `mode`:
    - `"dry_run"`: conta candidati, non modifica nulla.
    - `"anonymize"`: anonymizza Lead + Simulation candidati.
      ConsentRecord e PrivacyAuditEvent sono soltanto contati: la
      cancellazione di un consenso e' una decisione legale che richiede
      la firma dello Studio.
    - `"delete"`: rifiutato in P0 a meno che `allow_delete=True` venga
      passato esplicitamente dal caller (in test o se lo Studio firma
      la policy reale e l'operatore lo richiede). In quel caso elimina
      Lead + Simulation candidati. ConsentRecord/audit log non vengono
      mai cancellati automaticamente in P0.

    `executed_by`: stringa libera (`system`, `manual`, `cron`, `test`)
    per audit. Salvata su `RetentionRunLog.executed_by`.

    Ritorna un dict con la sintesi della run e l'`id` del log.
    """
    from .models import RetentionRunLog

    if mode not in RETENTION_MODES:
        raise ValueError(
            f"Invalid retention mode {mode!r}. Allowed: {', '.join(RETENTION_MODES)}."
        )

    snapshot = collect_retention_candidates(now=now)
    cutoffs = snapshot["cutoffs"]
    log = RetentionRunLog.objects.create(
        policy_version=str(getattr(settings, "RETENTION_POLICY_VERSION", "")),
        mode=mode,
        dry_run=(mode == "dry_run"),
        lead_candidates_count=snapshot["lead_candidates"],
        simulation_candidates_count=snapshot["simulation_candidates"],
        consent_candidates_count=snapshot["consent_candidates"],
        audit_candidates_count=snapshot["audit_candidates"],
        status=RetentionRunLog.Status.STARTED,
        executed_by=executed_by[:32] if executed_by else "system",
        notes=notes,
    )

    anonymized_count = 0
    deleted_count = 0
    try:
        if mode == "anonymize":
            from apps.cases.models import Simulation
            from apps.crm.models import Lead

            with transaction.atomic():
                for lead in Lead.objects.filter(
                    anonymized=False, created_at__lt=cutoffs["lead_cutoff"]
                ):
                    _anonymize_lead_inplace(lead)
                    anonymized_count += 1
                for sim in Simulation.objects.filter(
                    anonymized=False, created_at__lt=cutoffs["simulation_cutoff"]
                ):
                    _anonymize_simulation_inplace(sim)
                    anonymized_count += 1
        elif mode == "delete":
            if not allow_delete:
                raise RuntimeError(
                    "Retention mode=delete is refused in P0: the legal policy "
                    "must be signed by the Studio first. Pass allow_delete=True "
                    "explicitly only if you are absolutely sure (and only Lead/"
                    "Simulation are affected — ConsentRecord and audit log "
                    "are never deleted automatically)."
                )
            from apps.cases.models import Simulation
            from apps.crm.models import Lead

            with transaction.atomic():
                lead_qs = Lead.objects.filter(
                    created_at__lt=cutoffs["lead_cutoff"]
                )
                sim_qs = Simulation.objects.filter(
                    created_at__lt=cutoffs["simulation_cutoff"]
                )
                lead_deleted, _ = lead_qs.delete()
                sim_deleted, _ = sim_qs.delete()
                deleted_count = int(lead_deleted) + int(sim_deleted)
        # dry_run: nothing to do.
    except Exception as exc:
        log.status = RetentionRunLog.Status.FAILED
        log.error_message = repr(exc)[:1024]
        log.finished_at = timezone.now()
        log.save(update_fields=["status", "error_message", "finished_at"])
        raise
    else:
        log.anonymized_count = anonymized_count
        log.deleted_count = deleted_count
        log.status = RetentionRunLog.Status.SUCCESS
        log.finished_at = timezone.now()
        log.save(
            update_fields=[
                "anonymized_count",
                "deleted_count",
                "status",
                "finished_at",
            ]
        )

    return {
        "log_id": log.pk,
        "policy_version": log.policy_version,
        "mode": mode,
        "cutoffs": cutoffs,
        "lead_candidates": snapshot["lead_candidates"],
        "simulation_candidates": snapshot["simulation_candidates"],
        "consent_candidates": snapshot["consent_candidates"],
        "audit_candidates": snapshot["audit_candidates"],
        "anonymized_count": anonymized_count,
        "deleted_count": deleted_count,
        "status": log.status,
    }
