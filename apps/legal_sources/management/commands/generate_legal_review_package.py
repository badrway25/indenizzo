"""generate_legal_review_package — regenerable per-country legal review package.

Read-only. Merges the live ``LegalSource`` state with the registry ingest
policy into a Studio-reviewable package that lists what must be decided per
source. **Approves nothing.** No DB writes, no network, no PII.

CLI::

    python manage.py generate_legal_review_package --country FR
    python manage.py generate_legal_review_package --country BE --format json
    python manage.py generate_legal_review_package --country MA \
        --format markdown --output docs/legal_sources/MA_REVIEW_PACKAGE_GENERATED.md

Complements (does not replace) the hand-written
``<COUNTRY>_LEGAL_REVIEW_PACKAGE.md`` docs and the
``MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md``.
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.legal_sources.review_package import build_review_package, render_markdown


class Command(BaseCommand):
    help = (
        "Generate a regenerable, DB+registry-grounded legal review package for "
        "one country. Read-only; approves nothing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            required=True,
            help="ISO country code (e.g. FR, BE, MA, TN, IT).",
        )
        parser.add_argument(
            "--format",
            choices=("markdown", "json"),
            default="markdown",
            help="Output format. Default: markdown.",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Write to this file instead of stdout.",
        )

    def handle(self, *args, **options):
        country = options["country"].upper()
        pkg = build_review_package(country)
        if pkg["total_sources"] == 0:
            raise CommandError(
                f"No LegalSource found for country {country!r}. " "Nothing to review."
            )

        if options["format"] == "json":
            rendered = json.dumps(pkg, indent=2, ensure_ascii=False)
        else:
            rendered = render_markdown(pkg)

        output = options.get("output")
        if output:
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered + "\n", encoding="utf-8")
            self.stdout.write(
                f"[ok] wrote {options['format']} review package for {country} "
                f"({pkg['needs_review_count']} sources need review) to {output}"
            )
        else:
            self.stdout.write(rendered)
