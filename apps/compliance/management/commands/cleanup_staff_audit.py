"""
Management command: cleanup retention staff audit.

Iter: F-local-product-hardening-pass10-staff-audit-cleanup-task.

Uso:

    # Dry-run (default, sicuro): mostra cosa verrebbe cancellato
    python manage.py cleanup_staff_audit

    # Cancellazione reale (richiede flag esplicito)
    python manage.py cleanup_staff_audit --commit

    # Pin orologio per test/determinismo (formato ISO UTC)
    python manage.py cleanup_staff_audit --now 2026-01-01T00:00:00+00:00

Output: counts leggibili. Exit code 0 al successo (qualunque sia
il numero di record cancellati). Exit 1 solo per errori
strutturali (parsing `--now`, ecc.).

Sicurezza:
- Dry-run di default: nessuna cancellazione senza `--commit`.
- Tocca SOLO `StaffAccessEvent` e `StaffSecurityAlert`.
- Non emette PII nel log.
"""

from __future__ import annotations

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from apps.compliance.retention import cleanup_staff_audit_events


class Command(BaseCommand):
    help = "Cleanup retention StaffAccessEvent + StaffSecurityAlert (dry-run by default)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            help="Esegue la cancellazione reale. Senza questo flag, dry-run only.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Forza esplicitamente il dry-run (default già sicuro). Per chiarezza.",
        )
        parser.add_argument(
            "--now",
            default=None,
            help="ISO datetime (es. 2026-01-01T00:00:00+00:00) per pin orologio. Utile in test.",
        )

    def handle(self, *args, **options):
        commit = bool(options.get("commit"))
        dry_run_flag = bool(options.get("dry_run"))
        if commit and dry_run_flag:
            raise CommandError("--commit e --dry-run sono mutuamente esclusivi.")
        # Sicurezza: senza --commit, sempre dry-run.
        dry_run = not commit

        now_iso = options.get("now")
        now: datetime | None = None
        if now_iso:
            try:
                now = datetime.fromisoformat(now_iso)
            except ValueError as exc:
                raise CommandError(f"--now invalido: {exc}") from exc

        result = cleanup_staff_audit_events(dry_run=dry_run, now=now)

        self.stdout.write("=" * 64)
        self.stdout.write(
            "Staff audit retention cleanup "
            f"({'DRY-RUN (no delete)' if result['dry_run'] else 'COMMIT'})"
        )
        self.stdout.write("=" * 64)
        self.stdout.write(f"now:                          {result['now'].isoformat()}")
        self.stdout.write(
            f"StaffAccessEvent retention:   {result['staff_access_retention_days']} days  "
            f"(cutoff: {result['staff_access_cutoff'].isoformat()})"
        )
        self.stdout.write(
            f"StaffSecurityAlert retention: {result['staff_alert_retention_days']} days  "
            f"(cutoff: {result['staff_alert_cutoff'].isoformat()})"
        )
        self.stdout.write("")
        self.stdout.write(f"StaffAccessEvent expired:     {result['access_expired']}")
        self.stdout.write(f"StaffSecurityAlert expired:   {result['alerts_expired']}")
        if not result["dry_run"]:
            self.stdout.write("")
            self.stdout.write(
                self.style.WARNING(f"StaffAccessEvent deleted:     {result['access_deleted']}")
            )
            self.stdout.write(
                self.style.WARNING(f"StaffSecurityAlert deleted:   {result['alerts_deleted']}")
            )
        else:
            self.stdout.write("")
            self.stdout.write(
                self.style.NOTICE(
                    "Nessuna cancellazione eseguita. Aggiungi --commit per applicare."
                )
            )
