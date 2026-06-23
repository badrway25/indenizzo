"""audit_legacy_attachment_alignment — read-only legacy attachment audit (D5).

Reports legal sources whose latest review is ``approve`` but which lack a
``LegalSourceAttachment`` DB row (or a hash / source version), with a safe
recommended action per gap. It NEVER attaches a file, invents a hash, approves a
source or activates a calculation — the safe attach path is the existing
``attach_official_source_file`` workflow.

CLI::

    python manage.py audit_legacy_attachment_alignment --country ALL --format markdown
    python manage.py audit_legacy_attachment_alignment --country TN --format json
    # CI / ops guards (non-zero exit on violation):
    python manage.py audit_legacy_attachment_alignment --fail-on-blocking
    python manage.py audit_legacy_attachment_alignment --fail-on-manual-required
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.legal_sources.attachment_alignment import build_legacy_attachment_alignment_report


class Command(BaseCommand):
    help = (
        "Read-only audit of legacy approved sources missing an attachment row / "
        "hash / version. No DB writes, never attaches or approves."
    )

    def add_arguments(self, parser):
        parser.add_argument("--country", default=None, help="ISO code or ALL. Default: ALL.")
        parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
        parser.add_argument("--output", default=None, help="Write to file instead of stdout.")
        parser.add_argument("--include-ok", action="store_true", help="Also list aligned sources.")
        parser.add_argument(
            "--fail-on-blocking",
            action="store_true",
            help="Exit non-zero if any source has a blocking attachment gap.",
        )
        parser.add_argument(
            "--fail-on-manual-required",
            action="store_true",
            help="Exit non-zero if any source needs manual Studio sourcing.",
        )

    def handle(self, *args, **options):
        country = options.get("country")
        if country and country.upper() == "ALL":
            country = None

        report = build_legacy_attachment_alignment_report(
            country=country, include_ok=options["include_ok"]
        )
        fmt = options["format"]
        if fmt == "json":
            rendered = json.dumps(report, indent=2, ensure_ascii=False)
        elif fmt == "markdown":
            rendered = _render_markdown(report)
        else:
            rendered = _render_text(report)

        output = options.get("output")
        if output:
            path = Path(output)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered + "\n", encoding="utf-8")
            self.stdout.write(f"[ok] wrote {fmt} alignment audit to {output}")
        else:
            try:
                self.stdout.write(rendered)
            except UnicodeEncodeError:
                self.stdout.write(rendered.encode("ascii", "replace").decode("ascii"))

        t = report["totals"]
        violations: list[str] = []
        if options["fail_on_blocking"] and t["blocking"]:
            violations.append(f"{t['blocking']} blocking attachment gap(s)")
        if options["fail_on_manual_required"] and t["manual_review_required"]:
            violations.append(
                f"{t['manual_review_required']} source(s) need manual Studio sourcing"
            )
        if violations:
            raise CommandError("Attachment alignment audit failed: " + "; ".join(violations))


def _render_text(report: dict) -> str:
    t = report["totals"]
    lines = ["LEGACY ATTACHMENT ALIGNMENT AUDIT — read-only"]
    lines.append(
        f"items={t['items']}  blocking={t['blocking']}  warning={t['warning']}  "
        f"manual_required={t['manual_review_required']}"
    )
    lines.append("")
    for it in report["items"]:
        lines.append(
            f"  [{it['strict_validator_impact']}] {it['country']} {it['slug']} "
            f"({it['classification']})"
        )
        lines.append(
            f"      attach={it['has_attachment']} hash={it['attachment_hash_present']} "
            f"version={it['has_source_version']} candidate={it['in_registry']}"
        )
        lines.append(f"      action: {it['recommended_action']}")
    return "\n".join(lines)


def _render_markdown(report: dict) -> str:
    t = report["totals"]
    lines = ["# Legacy Attachment Alignment Audit — read-only"]
    lines.append("")
    lines.append(
        "> Read-only from `python manage.py audit_legacy_attachment_alignment`. It "
        "explains the strict review-validator's blocking findings (approved sources "
        "with no attachment row / hash / version) and the SAFE resolution. It "
        "**attaches nothing, invents no hash, approves nothing and activates no "
        "calculation.** Attach official files via `attach_official_source_file`."
    )
    lines.append("")
    lines.append(
        f"**Totals:** items={t['items']} · blocking={t['blocking']} · "
        f"warning={t['warning']} · manual_required={t['manual_review_required']}"
    )
    lines.append("")
    if report["summaries"]:
        lines.append("| Country | Items | Blocking | Warning |")
        lines.append("|:---:|---:|---:|---:|")
        for cc, cs in report["summaries"].items():
            lines.append(f"| {cc} | {cs['items']} | {cs['blocking']} | {cs['warning']} |")
        lines.append("")
    if report["items"]:
        lines.append(
            "| Impact | Country | Slug | Classification | Attach | Hash | Version | Action |"
        )
        lines.append("|:---:|:---:|---|:---:|:---:|:---:|:---:|---|")
        for it in report["items"]:
            yn = lambda b: "yes" if b else "no"  # noqa: E731
            lines.append(
                f"| {it['strict_validator_impact']} | {it['country']} | `{it['slug']}` | "
                f"{it['classification']} | {yn(it['has_attachment'])} | "
                f"{yn(it['attachment_hash_present'])} | {yn(it['has_source_version'])} | "
                f"{it['recommended_action']} |"
            )
    return "\n".join(lines)
