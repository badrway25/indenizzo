"""report_legal_review_pack_index — read-only evidence & review-pack index (D2).

Per legal source: candidate status, latest version, attachment/hash status, the
generated review-package path for its country, latest review, the recommended
reviewer action, the fail-closed reason and calculation-readiness.

Strictly read-only: no DB writes, no network, no PII, no raw PDF/OCR text. NEVER
promotes, approves or activates anything.

CLI::

    python manage.py report_legal_review_pack_index --country ALL --format markdown
    python manage.py report_legal_review_pack_index --country FR --format json
    # CI / ops guards (non-zero exit on violation):
    python manage.py report_legal_review_pack_index --fail-if-missing-review-pack-for-candidate
    python manage.py report_legal_review_pack_index --fail-if-calculation-ready-without-review
    python manage.py report_legal_review_pack_index --fail-if-approved-without-source-version
"""

from __future__ import annotations

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.legal_sources.review_evidence import (
    build_evidence_checklist,
    build_pack_index_report,
    candidates_missing_review_pack,
)
from apps.legal_sources.review_readiness import (
    approved_datasets_without_source_version,
    build_readiness_rows,
    calculation_ready_without_approve_review,
)


class Command(BaseCommand):
    help = (
        "Read-only evidence & review-pack index for legal sources "
        "(attachment/hash/version/package/review). No DB writes."
    )

    def add_arguments(self, parser):
        parser.add_argument("--country", default=None, help="ISO code or ALL. Default: ALL.")
        parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
        parser.add_argument("--output", default=None, help="Write to file instead of stdout.")
        parser.add_argument("--today", default="", help="ISO date for package freshness (testing).")
        parser.add_argument(
            "--fail-if-missing-review-pack-for-candidate",
            action="store_true",
            help="Exit non-zero if a registry candidate needing review lacks a country package.",
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

        report = build_pack_index_report(country=country, today=today)
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
            self.stdout.write(f"[ok] wrote {fmt} pack index to {output}")
        else:
            # stdout may be a non-UTF-8 console (e.g. Windows cp1252); write
            # defensively so markdown glyphs never crash the command.
            try:
                self.stdout.write(rendered)
            except UnicodeEncodeError:
                self.stdout.write(rendered.encode("ascii", "replace").decode("ascii"))

        violations: list[str] = []
        if options.get("fail_if_missing_review_pack_for_candidate"):
            rows = build_evidence_checklist(country, today=today)
            missing = candidates_missing_review_pack(rows)
            if missing:
                violations.append(
                    "candidates needing review without a package: " + ", ".join(missing)
                )
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
            raise CommandError("Pack-index guard failed: " + "; ".join(violations))


def _action(r: dict) -> str:
    if r["needs_attachment"]:
        return "attach the official source file"
    if r["needs_hash_check"]:
        return "compute/verify the attachment SHA-256"
    if r["needs_ocr"]:
        return "OCR / marker-extract the PDF, then verify the hash"
    if not r["has_source_version"]:
        return "create a LegalSourceVersion"
    if r["needs_legal_review"]:
        return "record a Studio legal review (approve/reject/request_changes)"
    if r["ready_for_dataset_seed_review"]:
        return "Studio may consider a dataset-seed review (separate, gated)"
    return "no action"


def _render_text(report: dict) -> str:
    t = report["totals"]
    lines = ["LEGAL SOURCE EVIDENCE & REVIEW-PACK INDEX — Studio report (read-only)"]
    lines.append(
        f"sources={t['sources']}  candidates={t['candidates']}  "
        f"ready_for_studio_review={t['ready_for_studio_review']}  "
        f"calculation_ready={t['calculation_ready']}"
    )
    lines.append("")
    for cc, cs in report["summaries"].items():
        lines.append(
            f"[{cc}] total={cs['total']} candidates={cs['candidates']} "
            f"attach={cs['with_attachment']} hash={cs['with_hash']} "
            f"package={cs['with_package']} ready={cs['ready_for_studio_review']} "
            f"calc_ready={cs['calculation_ready']}"
        )
    lines.append("")
    for r in report["rows"]:
        ready = "CALC-READY" if r["calculation_ready"] else "not-calc-ready"
        lines.append(
            f"  {r['country']} {r['slug']}  [{ready}]\n"
            f"      status={r['status']} candidate={r['in_registry']} "
            f"version={r['has_source_version']} attach={r['has_attachment']} "
            f"hash={r['attachment_hash_present']} ocr_needed={r['needs_ocr']}\n"
            f"      latest_review={r['latest_review_decision'] or '—'} "
            f"package={r['review_package_path'] or '—'} "
            f"({'fresh' if r['review_package_fresh'] else 'check-date'})\n"
            f"      next: {_action(r)}"
        )
        if r["never_calculation_ready_reason"]:
            lines.append(f"      fail-closed: {r['never_calculation_ready_reason']}")
    return "\n".join(lines)


def _render_markdown(report: dict) -> str:
    t = report["totals"]
    lines = ["# Legal Source Evidence & Review-Pack Index — Studio report"]
    lines.append("")
    lines.append(
        "> Read-only from `python manage.py report_legal_review_pack_index "
        "--format markdown`. Shows the evidence a reviewer needs (attachment, "
        "hash, version, package, latest review) and the recommended next action. "
        "It **approves, promotes and activates nothing**. `calculation_ready` is "
        "true only when a source backs an APPROVED dataset with a source version."
    )
    lines.append("")
    lines.append(
        f"**Totals:** sources={t['sources']} · candidates={t['candidates']} · "
        f"ready_for_studio_review={t['ready_for_studio_review']} · "
        f"calculation_ready={t['calculation_ready']}"
    )
    lines.append("")
    lines.append(
        "| Country | Slug | Status | Cand. | Attach | Hash | Version | Package | Latest review | Calc-ready | Next action |"
    )
    lines.append("|---|---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|---|")
    for r in report["rows"]:
        yn = lambda b: "✅" if b else "—"  # noqa: E731
        pkg = "✅" if r["has_review_package"] else "—"
        ready = "✅" if r["calculation_ready"] else "—"
        lines.append(
            f"| {r['country']} | `{r['slug']}` | {r['status']} | {yn(r['in_registry'])} | "
            f"{yn(r['has_attachment'])} | {yn(r['attachment_hash_present'])} | "
            f"{yn(r['has_source_version'])} | {pkg} | {r['latest_review_decision'] or '—'} | "
            f"{ready} | {_action(r)} |"
        )
    return "\n".join(lines)
