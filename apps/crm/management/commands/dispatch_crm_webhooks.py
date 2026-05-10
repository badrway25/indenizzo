"""
Management command: drain the LeadWebhookDelivery outbox.

Iter: F-p1-crm-1-webhook-dispatcher.

Usage:

    # Dry-run (default sicuro): count candidate rows, do not POST.
    python manage.py dispatch_crm_webhooks --dry-run

    # Send up to 50 pending rows whose next_attempt_at <= now.
    python manage.py dispatch_crm_webhooks --limit 50

    # Force one specific row regardless of next_attempt_at.
    python manage.py dispatch_crm_webhooks --delivery-id 42 --force

    # Pin clock for deterministic test/cron runs (ISO UTC).
    python manage.py dispatch_crm_webhooks --now 2026-12-31T23:59:59+00:00

Sicurezza:
- senza ``CRM_WEBHOOK_ENABLED=True`` o senza URL/secret, il dispatcher
  rifiuta di lavorare (a meno di --dry-run);
- ogni riga e' single-shot: una sola POST per invocazione, con il
  contatore `attempts` che incrementa su ogni call.
"""

from __future__ import annotations

from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone


class Command(BaseCommand):
    help = "Dispatch pending LeadWebhookDelivery rows to the configured CRM endpoint."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit", type=int, default=50,
            help="Max rows to dispatch in this run (default 50).",
        )
        parser.add_argument(
            "--dry-run", action="store_true", default=False,
            help="Count candidate rows without sending or mutating DB.",
        )
        parser.add_argument(
            "--delivery-id", type=int, default=None,
            help="Dispatch a single specific row by primary key.",
        )
        parser.add_argument(
            "--force", action="store_true", default=False,
            help="Ignore next_attempt_at when used with --delivery-id.",
        )
        parser.add_argument(
            "--now", default=None,
            help="ISO datetime (es. 2026-01-01T00:00:00+00:00) for clock pin.",
        )

    def handle(self, *args, **options):
        from apps.crm.models import LeadWebhookDelivery
        from apps.crm.webhooks import dispatch_one, dispatch_pending_webhooks

        dry_run = bool(options["dry_run"])
        limit = int(options["limit"])
        delivery_id = options["delivery_id"]
        force = bool(options["force"])

        now: datetime | None = None
        now_iso = options["now"]
        if now_iso:
            try:
                now = datetime.fromisoformat(now_iso)
            except ValueError as exc:
                raise CommandError(f"--now invalid: {exc}") from exc

        enabled = bool(getattr(settings, "CRM_WEBHOOK_ENABLED", False))
        if not enabled and not dry_run:
            raise CommandError(
                "CRM_WEBHOOK_ENABLED=False — refusing to dispatch. "
                "Use --dry-run to inspect candidate rows or set the flag in env."
            )

        # Pinned now for the rest of the call so the printed cutoff
        # and the dispatcher's clock match.
        clock_now = now or timezone.now()

        # Single-row mode (--delivery-id).
        if delivery_id is not None:
            try:
                delivery = LeadWebhookDelivery.objects.get(pk=delivery_id)
            except LeadWebhookDelivery.DoesNotExist:
                raise CommandError(f"LeadWebhookDelivery id={delivery_id} not found.")

            if dry_run:
                self.stdout.write(
                    f"DRY-RUN delivery_id={delivery_id} "
                    f"status={delivery.status} "
                    f"attempts={delivery.attempts}/{delivery.max_attempts} "
                    f"next_attempt_at={delivery.next_attempt_at}"
                )
                return

            if not force:
                if delivery.next_attempt_at and delivery.next_attempt_at > clock_now:
                    raise CommandError(
                        f"delivery_id={delivery_id} not yet due "
                        f"(next_attempt_at={delivery.next_attempt_at}). "
                        "Pass --force to override."
                    )

            new_status = dispatch_one(delivery, now=clock_now)
            self.stdout.write(
                f"delivery_id={delivery.pk} new_status={new_status} "
                f"attempts={delivery.attempts}/{delivery.max_attempts} "
                f"http={delivery.last_status_code}"
            )
            return

        # Bulk mode: dispatch up to --limit pending rows.
        result = dispatch_pending_webhooks(
            limit=limit, now=clock_now, dry_run=dry_run
        )

        self.stdout.write("=" * 64)
        self.stdout.write(
            f"CRM webhook dispatcher [{'DRY-RUN' if result['dry_run'] else 'LIVE'}] "
            f"limit={limit}"
        )
        self.stdout.write("=" * 64)
        self.stdout.write(f"now:        {result['now'].isoformat()}")
        self.stdout.write(f"candidates: {result['candidates']}")
        if not result["dry_run"]:
            self.stdout.write(f"delivered:  {result['delivered']}")
            self.stdout.write(f"failed:     {result['failed']}")
            self.stdout.write(f"dead:       {result['dead']}")
            self.stdout.write(f"retried:    {result['retried']}")
        else:
            self.stdout.write(self.style.NOTICE(
                "Dry-run: no row dispatched. Drop --dry-run to actually send."
            ))
