"""validate_legal_review_decisions — read-only audit of recorded review decisions (D4).

Re-evaluates existing ``LegalReview`` decisions against the current evidence and
the fail-closed invariants, and reports: ``approve`` decisions whose evidence is
now incomplete, calculation-ready sources without an approve review, APPROVED
datasets without a source version, and any non-Italian source that is
calculation-ready (should never happen).

Strictly read-only: no DB writes, no network, no PII (no reviewer emails), no raw
text. It approves/promotes/activates nothing.

CLI::

    python manage.py validate_legal_review_decisions --country ALL --format markdown
    python manage.py validate_legal_review_decisions --include-history --fail-on-blocking
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.legal_sources.review_decision_guard import evaluate_legal_review_decision
from apps.legal_sources.review_readiness import (
    approved_datasets_without_source_version,
    build_readiness_rows,
    calculation_ready_without_approve_review,
)


class Command(BaseCommand):
    help = (
        "Read-only audit of recorded LegalReview decisions vs current evidence "
        "and the fail-closed invariants. No DB writes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--country", default=None, help="ISO code or ALL. Default: ALL.")
        parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
        parser.add_argument("--output", default=None, help="Write to file instead of stdout.")
        parser.add_argument(
            "--include-history",
            action="store_true",
            help="Evaluate every review, not only the latest per source.",
        )
        parser.add_argument(
            "--fail-on-blocking",
            action="store_true",
            help="Exit non-zero if any decision has a blocking inconsistency.",
        )
        parser.add_argument(
            "--fail-on-warning",
            action="store_true",
            help="Exit non-zero if any decision has a warning.",
        )

    def handle(self, *args, **options):
        from apps.legal_sources.models import LegalSource

        country = options.get("country")
        if country and country.upper() == "ALL":
            country = None

        qs = LegalSource.objects.all().select_related("country")
        if country:
            qs = qs.filter(country__code=country.upper())

        findings: list[dict] = []
        for source in qs.order_by("country__code", "slug"):
            reviews = list(source.reviews.order_by("-created_at", "-pk"))
            if not options["include_history"]:
                reviews = reviews[:1]
            for rev in reviews:
                res = evaluate_legal_review_decision(source, rev.decision)
                if res.severity == "ok":
                    continue
                findings.append(
                    {
                        "country": source.country.code if source.country_id else "??",
                        "slug": source.slug,
                        "decision": rev.decision,
                        "severity": res.severity,
                        "warnings": res.warnings,
                        "blocking_reasons": res.blocking_reasons,
                        "evidence_summary": res.evidence_summary,
                    }
                )

        # Fail-closed invariants (independent of recorded decisions).
        rows = build_readiness_rows(country)
        calc_ready_no_review = calculation_ready_without_approve_review(rows)
        approved_no_version = approved_datasets_without_source_version()
        non_it_calc_ready = [r.slug for r in rows if r.calculation_ready and r.country != "IT"]

        report = {
            "country": country or "ALL",
            "findings": findings,
            "invariants": {
                "calculation_ready_without_approve_review": calc_ready_no_review,
                "approved_datasets_without_source_version": approved_no_version,
                "non_italian_calculation_ready": non_it_calc_ready,
            },
            "totals": {
                "findings": len(findings),
                "blocking": sum(1 for f in findings if f["severity"] == "blocking"),
                "warning": sum(1 for f in findings if f["severity"] == "warning"),
            },
        }
        # D5: non-invasive hint pointing to the attachment-alignment audit when a
        # blocking finding exists (legacy approve without an attachment row). Does
        # not change default behaviour or exit codes.
        if report["totals"]["blocking"]:
            report["hint"] = (
                "Run `python manage.py audit_legacy_attachment_alignment "
                "--format markdown` for the attachment-gap details and safe actions."
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
            self.stdout.write(f"[ok] wrote {fmt} decision audit to {output}")
        else:
            try:
                self.stdout.write(rendered)
            except UnicodeEncodeError:
                self.stdout.write(rendered.encode("ascii", "replace").decode("ascii"))

        # Invariant violations are always blocking.
        inv = report["invariants"]
        invariant_violations = (
            inv["calculation_ready_without_approve_review"]
            or inv["approved_datasets_without_source_version"]
            or inv["non_italian_calculation_ready"]
        )
        violations: list[str] = []
        if invariant_violations:
            violations.append("fail-closed invariant violated: " + json.dumps(inv))
        if options["fail_on_blocking"] and report["totals"]["blocking"]:
            violations.append(f"{report['totals']['blocking']} blocking decision finding(s)")
        if options["fail_on_warning"] and report["totals"]["warning"]:
            violations.append(f"{report['totals']['warning']} warning decision finding(s)")
        if violations:
            raise CommandError("Decision audit failed: " + "; ".join(violations))


def _render_text(report: dict) -> str:
    t = report["totals"]
    lines = ["LEGAL REVIEW DECISION AUDIT — read-only"]
    lines.append(f"findings={t['findings']}  blocking={t['blocking']}  warning={t['warning']}")
    inv = report["invariants"]
    lines.append(
        "invariants: "
        f"calc_ready_without_review={len(inv['calculation_ready_without_approve_review'])} "
        f"approved_without_version={len(inv['approved_datasets_without_source_version'])} "
        f"non_it_calc_ready={len(inv['non_italian_calculation_ready'])}"
    )
    if report.get("hint"):
        lines.append(f"hint: {report['hint']}")
    lines.append("")
    for f in report["findings"]:
        lines.append(f"  [{f['severity']}] {f['country']} {f['slug']} (decision={f['decision']})")
        for b in f["blocking_reasons"]:
            lines.append(f"      blocking: {b}")
        for w in f["warnings"]:
            lines.append(f"      warning: {w}")
    return "\n".join(lines)


def _render_markdown(report: dict) -> str:
    t = report["totals"]
    inv = report["invariants"]
    lines = ["# Legal Review Decision Audit — read-only"]
    lines.append("")
    lines.append(
        f"**Totals:** findings={t['findings']} · blocking={t['blocking']} · warning={t['warning']}"
    )
    if report.get("hint"):
        lines.append("")
        lines.append(f"> {report['hint']}")
    lines.append("")
    lines.append("## Fail-closed invariants")
    lines.append(
        f"- calculation-ready without approve review: "
        f"{inv['calculation_ready_without_approve_review'] or 'none'}"
    )
    lines.append(
        f"- APPROVED datasets without source version: "
        f"{inv['approved_datasets_without_source_version'] or 'none'}"
    )
    lines.append(
        f"- non-Italian calculation-ready: {inv['non_italian_calculation_ready'] or 'none'}"
    )
    lines.append("")
    if report["findings"]:
        lines.append("## Decision findings")
        lines.append("| Severity | Country | Slug | Decision | Issue |")
        lines.append("|:---:|:---:|---|:---:|---|")
        for f in report["findings"]:
            issue = "; ".join(f["blocking_reasons"] + f["warnings"])
            lines.append(
                f"| {f['severity']} | {f['country']} | `{f['slug']}` | {f['decision']} | {issue} |"
            )
    return "\n".join(lines)
