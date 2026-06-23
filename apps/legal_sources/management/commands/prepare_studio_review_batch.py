"""prepare_studio_review_batch — read-only Studio review batch (D3).

Builds an ordered, reviewer-oriented batch of legal sources (evidence, readiness,
missing steps, recommended action, safe package link, manual decision template).

Strictly read-only: no DB writes, no network, no PII, no raw PDF/OCR text, no
full hashes, no absolute paths. NEVER approves a source, creates a LegalReview,
promotes a dataset or activates a calculator.

CLI::

    python manage.py prepare_studio_review_batch --country FR --format markdown
    python manage.py prepare_studio_review_batch --country ALL --format json --output docs/legal_sources/generated/FR_STUDIO_REVIEW_BATCH_2026-06-23.md
    # CI / ops guards (non-zero exit on violation):
    python manage.py prepare_studio_review_batch --fail-if-empty
    python manage.py prepare_studio_review_batch --fail-if-calculation-ready-without-review
    python manage.py prepare_studio_review_batch --fail-if-approved-without-source-version
"""

from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.legal_sources.review_batch import (
    build_review_batch,
    render_review_batch_json,
    render_review_batch_markdown,
)
from apps.legal_sources.review_readiness import (
    approved_datasets_without_source_version,
    build_readiness_rows,
    calculation_ready_without_approve_review,
)


class Command(BaseCommand):
    help = (
        "Read-only Studio review batch for legal sources (evidence, readiness, "
        "missing steps, manual decision template). No DB writes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--country", default=None, help="ISO code or ALL. Default: ALL.")
        parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
        parser.add_argument("--output", default=None, help="Write to file instead of stdout.")
        parser.add_argument("--limit", type=int, default=None, help="Cap the number of items.")
        parser.add_argument("--today", default="", help="ISO date for freshness/header (testing).")
        parser.add_argument(
            "--include-ready",
            action="store_true",
            help="Also include calculation-ready sources (default: blocked only).",
        )
        parser.add_argument(
            "--no-include-blocked",
            dest="include_blocked",
            action="store_false",
            help="Exclude not-yet-calculation-ready sources.",
        )
        parser.set_defaults(include_blocked=True)
        parser.add_argument(
            "--fail-if-empty",
            action="store_true",
            help="Exit non-zero if the batch has no items.",
        )
        parser.add_argument(
            "--fail-if-calculation-ready-without-review",
            action="store_true",
            help="Exit non-zero if any calculation-ready source lacks an approve review.",
        )
        parser.add_argument(
            "--fail-if-approved-without-source-version",
            action="store_true",
            help="Exit non-zero if any APPROVED dataset lacks a source_version.",
        )

    def handle(self, *args, **options):
        country = options.get("country")
        if country and country.upper() == "ALL":
            country = None
        today = options.get("today") or ""

        batch = build_review_batch(
            country=country,
            include_ready=options["include_ready"],
            include_blocked=options["include_blocked"],
            limit=options.get("limit"),
            today=today,
        )
        if options["format"] == "json":
            rendered = render_review_batch_json(batch)
        else:
            rendered = render_review_batch_markdown(batch, today=today)

        output = options.get("output")
        if output:
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered + "\n", encoding="utf-8")
            self.stdout.write(f"[ok] wrote {options['format']} review batch to {output}")
        else:
            # stdout may be a non-UTF-8 console; write defensively.
            try:
                self.stdout.write(rendered)
            except UnicodeEncodeError:
                self.stdout.write(rendered.encode("ascii", "replace").decode("ascii"))

        violations: list[str] = []
        if options.get("fail_if_empty") and batch["totals"]["items"] == 0:
            violations.append("review batch is empty")
        if options.get("fail_if_calculation_ready_without_review"):
            unsafe = calculation_ready_without_approve_review(build_readiness_rows(country))
            if unsafe:
                violations.append(
                    "calculation-ready sources without an approve review: " + ", ".join(unsafe)
                )
        if options.get("fail_if_approved_without_source_version"):
            bad = approved_datasets_without_source_version()
            if bad:
                violations.append("APPROVED datasets without a source_version: " + ", ".join(bad))
        if violations:
            raise CommandError("Review-batch guard failed: " + "; ".join(violations))
