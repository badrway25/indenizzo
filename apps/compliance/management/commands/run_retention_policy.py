"""
Management command: wide retention policy.

Iter: F-p0-leg-4-retention.

Uso:

    # Dry-run (default sicuro, conta candidati senza modifiche)
    python manage.py run_retention_policy

    # Anonymize Lead + Simulation candidati (richiede conferma esplicita)
    python manage.py run_retention_policy --mode=anonymize --yes-i-understand

    # Delete fisico (rifiutato in P0 senza --allow-delete)
    python manage.py run_retention_policy --mode=delete --yes-i-understand --allow-delete

    # Pin orologio (UTC ISO) per test/cron deterministico
    python manage.py run_retention_policy --now 2026-12-31T23:59:59+00:00

Sicurezza:
- `--mode` di default `dry_run`. Senza `--yes-i-understand`,
  qualsiasi `--mode` non dry-run e' rifiutato.
- `--mode=delete` richiede ANCHE `--allow-delete`. Il delete fisico
  non parte mai per inerzia: lo Studio deve firmare prima la policy.
- Tocca SOLO Lead, Simulation, ConsentRecord (count), PrivacyAuditEvent
  (count). NON tocca StaffAccessEvent / StaffSecurityAlert (cleanup
  dedicato: `python manage.py cleanup_staff_audit`).
- Nessun PII nel log stdout.

Output:
- policy_version, mode, cutoff dates,
- candidate counts per scope,
- action performed (anonymized_count, deleted_count),
- RetentionRunLog id (per audit).
"""

from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.compliance.retention import RETENTION_MODES, run_retention


class Command(BaseCommand):
    help = "Run wide retention policy (Lead/Simulation/ConsentRecord/audit) — dry-run by default."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Forza esplicitamente il dry-run (default). Solo per chiarezza CLI.",
        )
        parser.add_argument(
            "--mode",
            default="dry_run",
            choices=RETENTION_MODES,
            help="Modalita' retention: dry_run (default), anonymize, delete.",
        )
        parser.add_argument(
            "--yes-i-understand",
            action="store_true",
            default=False,
            help="Conferma esplicita richiesta per qualsiasi mode != dry_run.",
        )
        parser.add_argument(
            "--allow-delete",
            action="store_true",
            default=False,
            help="Sblocca --mode=delete. Richiesto in aggiunta a --yes-i-understand.",
        )
        parser.add_argument(
            "--now",
            default=None,
            help="ISO datetime (es. 2026-01-01T00:00:00+00:00) per pin orologio.",
        )
        parser.add_argument(
            "--executed-by",
            default="manual",
            help="Etichetta per RetentionRunLog.executed_by (default 'manual').",
        )

    def handle(self, *args, **options):
        dry_run_flag = bool(options["dry_run"])
        mode = options["mode"]
        confirmed = bool(options["yes_i_understand"])
        allow_delete = bool(options["allow_delete"])
        executed_by = options["executed_by"] or "manual"

        if dry_run_flag and mode != "dry_run":
            raise CommandError("--dry-run e --mode=anonymize|delete sono mutuamente esclusivi.")

        if mode != "dry_run" and not confirmed:
            raise CommandError(
                f"--mode={mode} richiede --yes-i-understand. "
                "Senza conferma esplicita la retention rifiuta di partire."
            )
        if mode == "delete" and not allow_delete:
            raise CommandError(
                "--mode=delete richiede --allow-delete in aggiunta a --yes-i-understand. "
                "Il delete fisico non parte per inerzia: la policy retention "
                "deve essere firmata dallo Studio prima di abilitarlo."
            )

        now_iso = options["now"]
        now: datetime | None = None
        if now_iso:
            try:
                now = datetime.fromisoformat(now_iso)
            except ValueError as exc:
                raise CommandError(f"--now invalido: {exc}") from exc

        result = run_retention(
            mode=mode,
            now=now,
            executed_by=executed_by,
            allow_delete=allow_delete,
        )

        cutoffs = result["cutoffs"]
        self.stdout.write("=" * 64)
        self.stdout.write(
            f"Retention policy run [mode={mode}] log_id={result['log_id']}"
        )
        self.stdout.write("=" * 64)
        self.stdout.write(f"policy_version: {result['policy_version']}")
        self.stdout.write(f"now:            {cutoffs['now'].isoformat()}")
        self.stdout.write("")
        self.stdout.write("Cutoffs:")
        self.stdout.write(
            f"  Lead         < {cutoffs['lead_cutoff'].isoformat()}  ({cutoffs['lead_days']}d)"
        )
        self.stdout.write(
            f"  Simulation   < {cutoffs['simulation_cutoff'].isoformat()}  ({cutoffs['simulation_days']}d)"
        )
        self.stdout.write(
            f"  ConsentRec.  < {cutoffs['consent_cutoff'].isoformat()}  ({cutoffs['consent_days']}d)"
        )
        self.stdout.write(
            f"  AuditEvent   < {cutoffs['audit_cutoff'].isoformat()}  ({cutoffs['audit_days']}d)"
        )
        self.stdout.write("")
        self.stdout.write("Candidates:")
        self.stdout.write(f"  Lead:         {result['lead_candidates']}")
        self.stdout.write(f"  Simulation:   {result['simulation_candidates']}")
        self.stdout.write(f"  ConsentRec.:  {result['consent_candidates']} (count only — never auto-deleted)")
        self.stdout.write(f"  AuditEvent:   {result['audit_candidates']} (count only — never auto-deleted)")
        self.stdout.write("")

        if mode == "dry_run":
            self.stdout.write(self.style.NOTICE(
                "Dry-run: no record modified. Pass --mode=anonymize --yes-i-understand to act."
            ))
        elif mode == "anonymize":
            self.stdout.write(self.style.WARNING(
                f"anonymized_count: {result['anonymized_count']}"
            ))
        elif mode == "delete":
            self.stdout.write(self.style.WARNING(
                f"deleted_count:    {result['deleted_count']}"
            ))
        self.stdout.write("")
        self.stdout.write(f"status: {result['status']}")
