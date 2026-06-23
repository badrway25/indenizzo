"""report_legal_review_readiness — read-only Studio review-readiness report (D1).

For every ``LegalSource`` (optionally per country) reports: attachment / hash /
version status, the latest Studio review decision, whether it is
calculation-ready, the concrete missing steps and the recommended next action.

Strictly read-only: no DB writes, no network, no PII, no secrets. NEVER promotes
a source, approves a dataset, or activates a calculator. Fail-closed.

CLI::

    python manage.py report_legal_review_readiness
    python manage.py report_legal_review_readiness --country FR --format markdown
    python manage.py report_legal_review_readiness --format json --output docs/legal_sources/FR_READINESS.md
    # CI / ops guards (non-zero exit on violation):
    python manage.py report_legal_review_readiness --fail-if-calculation-ready-without-review
    python manage.py report_legal_review_readiness --fail-if-approved-without-source-version
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.legal_sources.review_readiness import (
    approved_datasets_without_source_version,
    build_readiness_report,
    build_readiness_rows,
    calculation_ready_without_approve_review,
)


class Command(BaseCommand):
    help = (
        "Read-only Studio review-readiness report for legal sources "
        "(missing steps, latest review, calculation-readiness). No DB writes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            default=None,
            help="Filter by ISO code (FR, BE, MA, TN, IT, EU) or ALL. Default: ALL.",
        )
        parser.add_argument(
            "--format",
            choices=("text", "json", "markdown"),
            default="text",
            help="Output format. Default: text.",
        )
        parser.add_argument(
            "--output",
            default=None,
            help="Write the report to this file instead of stdout.",
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

        report = build_readiness_report(country=country)
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
            self.stdout.write(f"[ok] wrote {fmt} readiness report to {output}")
        else:
            # stdout may be a non-UTF-8 console (e.g. Windows cp1252); write
            # defensively so markdown glyphs never crash the command.
            try:
                self.stdout.write(rendered)
            except UnicodeEncodeError:
                self.stdout.write(rendered.encode("ascii", "replace").decode("ascii"))

        # --- fail-closed guards (after reporting) -------------------------
        violations: list[str] = []
        if options.get("fail_if_calculation_ready_without_review"):
            rows = build_readiness_rows(country=country)
            unsafe = calculation_ready_without_approve_review(rows)
            if unsafe:
                violations.append(
                    "calculation-ready sources without an approve review: " + ", ".join(unsafe)
                )
        if options.get("fail_if_approved_without_source_version"):
            bad = approved_datasets_without_source_version()
            if bad:
                violations.append("APPROVED datasets without a source_version: " + ", ".join(bad))
        if violations:
            raise CommandError("Readiness guard failed: " + "; ".join(violations))


def _render_text(report: dict) -> str:
    lines: list[str] = []
    t = report["totals"]
    lines.append("LEGAL SOURCE REVIEW READINESS — Studio report (read-only)")
    lines.append(
        f"sources={t['sources']}  calculation_ready={t['calculation_ready']}  "
        f"approve_reviewed={t['approve_reviewed']}  needs_steps={t['needs_steps']}"
    )
    lines.append("")
    for country, cs in report["summaries"].items():
        lines.append(
            f"[{country}] total={cs['total']}  calc_ready={cs['calculation_ready']}  "
            f"approve_reviewed={cs['approve_reviewed']}  needs_steps={cs['needs_steps']}"
        )
    lines.append("")
    for r in report["rows"]:
        ready = "CALC-READY" if r["calculation_ready"] else "not-calc-ready"
        decision = r["latest_review_decision"] or "—"
        lines.append(
            f"  {r['country']} {r['slug']}  [{ready}]\n"
            f"      status={r['status']} latest_review={decision} "
            f"versions={r['version_count']} attach={r['attachment_count']}"
            f"(hashed={r['hashed_attachment_count']})\n"
            f"      next: {r['recommended_next_action']}"
        )
        for step in r["missing_steps"]:
            lines.append(f"        - {step}")
    return "\n".join(lines)


def _render_markdown(report: dict) -> str:
    t = report["totals"]
    lines: list[str] = []
    lines.append("# Legal Source Review Readiness — Studio report")
    lines.append("")
    lines.append(
        "> Read-only snapshot from "
        "`python manage.py report_legal_review_readiness --format markdown`. "
        "It lists what each source still needs before it could ever be "
        "calculation-ready. It does **not** promote, approve or activate "
        "anything. `calculation_ready` is true only when a source backs an "
        "APPROVED dataset with a source version."
    )
    lines.append("")
    lines.append(
        f"**Totals:** sources={t['sources']} · calculation_ready={t['calculation_ready']} "
        f"· approve_reviewed={t['approve_reviewed']} · needs_steps={t['needs_steps']}"
    )
    lines.append("")
    lines.append("| Country | Total | Calc-ready | Approve-reviewed | Needs steps |")
    lines.append("|:---:|---:|---:|---:|---:|")
    for country, cs in report["summaries"].items():
        lines.append(
            f"| {country} | {cs['total']} | {cs['calculation_ready']} | "
            f"{cs['approve_reviewed']} | {cs['needs_steps']} |"
        )
    lines.append("")
    lines.append("## Sources")
    lines.append("")
    lines.append("| Country | Slug | Status | Latest review | Calc-ready | Next action |")
    lines.append("|---|---|:---:|:---:|:---:|---|")
    for r in report["rows"]:
        ready = "✅" if r["calculation_ready"] else "—"
        decision = r["latest_review_decision"] or "—"
        lines.append(
            f"| {r['country']} | `{r['slug']}` | {r['status']} | {decision} | "
            f"{ready} | {r['recommended_next_action']} |"
        )
    return "\n".join(lines)
