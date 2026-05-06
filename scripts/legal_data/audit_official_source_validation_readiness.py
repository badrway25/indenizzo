"""Audit official-source validation readiness.

Iter: F-legal-sources-official-validation-pass1.

For each ``LegalSource`` row, classify it into one of four buckets:

1. ``VALIDATED_OFFICIAL_SOURCE`` — the source carries a known
   ``[official_sync]`` ``fetch_success`` / ``crosscheck_success``
   block, or a ``[manual_attach]`` ``manual_attach_success`` block,
   the local file referenced exists, and its SHA-256 still matches
   the recorded value. (When the registry declares
   ``content_must_contain``, the marker check is also expected to
   pass.)
2. ``NEEDS_REVIEW_NON_OFFICIAL`` — the source is either a
   ``private_bareme`` / ``court_indicative_table`` / OCR-incomplete
   scan / un-attached ``manual_required`` / mirror without
   validation, or otherwise not anchored on an official body.
3. ``OFFICIAL_BUT_NOT_CALCULATION_READY`` — the source is
   officially validated but the calculator cannot yet be activated
   because mapping / dataset / formula are still required (e.g. MA
   Moudawana Livre III, TN CSP + DIP + Reg. 650, EU 650/2012,
   Badinter, BE Loi 1989).
4. ``DATASET_APPROVAL_BLOCKED`` — a DRAFT FR/BE compensation
   dataset is rooted on a non-official source whose validation has
   not yet completed, so the dataset cannot be promoted.

The script is **read-only**: it touches no DB row and no file other
than re-computing SHA-256 on the local copy referenced by each
notes block.

Outputs:

- ``docs/architecture/OFFICIAL_SOURCE_VALIDATION_READINESS_PASS1.md``
- ``docs/reports/legal_sources/official_source_validation_readiness.json``

Exit codes:

- 0 = audit ran to completion (regardless of bucket counts).
- 1 = unexpected error (DB integrity, registry parse, etc.).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.compensation.models import (  # noqa: E402
    CompensationDataset,
    DatasetStatus,
)
from apps.legal_sources.models import LegalSource  # noqa: E402

REPORT_MD = REPO_ROOT / "docs" / "architecture" / "OFFICIAL_SOURCE_VALIDATION_READINESS_PASS1.md"
REPORT_JSON = (
    REPO_ROOT / "docs" / "reports" / "legal_sources" / "official_source_validation_readiness.json"
)
REGISTRY_PATH = REPO_ROOT / "config" / "official_source_registry.json"

OFFICIAL_SYNC_BEGIN = "[official_sync] BEGIN"
OFFICIAL_SYNC_END = "[official_sync] END"
MANUAL_ATTACH_BEGIN = "[manual_attach] BEGIN"
MANUAL_ATTACH_END = "[manual_attach] END"
VALIDATION_BEGIN = "[official_source_validation] BEGIN"
VALIDATION_END = "[official_source_validation] END"

# Sources that match these slugs / kinds are intrinsically non-official
# and MUST NOT bubble up as validated even if a later iter wires them
# into a sync block by mistake.
NON_OFFICIAL_SLUGS = {
    "fr-referentiel-mornet-2024",
    "fr-bareme-capitalisation-gazette-palais-2022",
    "fr-bareme-capitalisation-gazette-palais-2025-page",
    "fr-nomenclature-dintilhac-2005",
    "be-tableau-indicatif-2020",
    "be-tableau-indicatif-2024",
    "be-tables-schryvers-2026-page",
    "be-tables-schryvers-tableurs",
}

# Sources where the official document is verifiable but the
# calculator activation requires mapping work the iter must NOT do.
# These slugs always land in OFFICIAL_BUT_NOT_CALCULATION_READY when
# the file/marker checks pass.
NOT_CALCULATION_READY_SLUGS = {
    "ma-code-famille-moudawana-fr-pdf",
    "tn-code-statut-personnel-livre-ix-succession",
    "tn-code-dip-loi-98-97",
    "eu-regulation-650-2012-successions",
    "eu-regulation-650-2012-successions-fr-ma",
    "eu-regulation-650-2012-successions-fr-tn",
    "fr-loi-badinter-1985",
    "be-loi-1989-11-21-rc-auto",
}

DRAFT_DATASET_LABELS = (
    "FR-MORNET-2024-DRAFT",
    "FR-GAZETTE-PALAIS-2022-DRAFT",
    "FR-DINTILHAC-2005-DRAFT",
    "BE-TABLEAU-INDICATIF-2020-DRAFT",
    "BE-TABLEAU-INDICATIF-2024-DRAFT",
    "BE-SCHRYVERS-DRAFT",
)


@dataclass
class SourceFinding:
    slug: str
    country: str
    title: str
    status: str
    bucket: str
    sync_classification: str = ""
    manual_classification: str = ""
    file_path: str = ""
    file_exists: bool = False
    sha256_recorded: str = ""
    sha256_recomputed: str = ""
    sha256_match: bool = False
    size_bytes_recorded: int | None = None
    marker_check_passed: bool | None = None
    registry_markers: list[str] = field(default_factory=list)
    candidate_for_manual_status_approval: bool = False
    blocking_reasons: list[str] = field(default_factory=list)
    notes_excerpt: str = ""


def _extract_block(notes: str, begin: str, end: str) -> dict[str, Any] | None:
    if begin not in notes:
        return None
    body = notes.split(begin, 1)[1].split(end, 1)[0].strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _load_registry() -> dict[str, dict[str, Any]]:
    if not REGISTRY_PATH.is_file():
        return {}
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {entry["source_slug"]: entry for entry in raw.get("entries", [])}


def _resolve_local_path(raw: str | None) -> pathlib.Path | None:
    if not raw:
        return None
    p = pathlib.Path(raw)
    if not p.is_absolute():
        p = REPO_ROOT / p
    return p


def _sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _classify(src: LegalSource, registry_entry: dict[str, Any] | None) -> SourceFinding:
    notes = src.notes or ""
    sync = _extract_block(notes, OFFICIAL_SYNC_BEGIN, OFFICIAL_SYNC_END)
    manual = _extract_block(notes, MANUAL_ATTACH_BEGIN, MANUAL_ATTACH_END)
    validation = _extract_block(notes, VALIDATION_BEGIN, VALIDATION_END)

    finding = SourceFinding(
        slug=src.slug,
        country=src.country.code if src.country_id else "",
        title=src.title,
        status=src.status,
        bucket="NEEDS_REVIEW_NON_OFFICIAL",
        sync_classification=(sync or {}).get("classification", ""),
        manual_classification=(manual or {}).get("classification", ""),
        registry_markers=(registry_entry or {}).get("content_must_contain", []) or [],
    )

    # Hard rule: non-official slugs never move past
    # NEEDS_REVIEW_NON_OFFICIAL even if a sync block is present.
    if src.slug in NON_OFFICIAL_SLUGS:
        finding.bucket = "NEEDS_REVIEW_NON_OFFICIAL"
        kind = (registry_entry or {}).get("source_kind", "")
        if kind:
            finding.blocking_reasons.append(f"source_kind={kind}")
        finding.blocking_reasons.append("intrinsically_non_official")
        return finding

    block = sync or manual
    if not block:
        finding.bucket = "NEEDS_REVIEW_NON_OFFICIAL"
        finding.blocking_reasons.append("no_official_sync_or_manual_attach_block")
        return finding

    cls = block.get("classification") or ""
    valid_classifications = {
        "fetch_success",
        "crosscheck_success",
        "manual_attach_success",
    }
    if cls not in valid_classifications:
        finding.bucket = "NEEDS_REVIEW_NON_OFFICIAL"
        finding.blocking_reasons.append(f"classification={cls!r}_not_validated")
        return finding

    finding.sha256_recorded = block.get("sha256", "") or ""
    finding.size_bytes_recorded = block.get("size_bytes")
    finding.marker_check_passed = block.get("marker_check_passed")
    finding.file_path = block.get("local_path", "") or ""

    local_path = _resolve_local_path(finding.file_path)
    if local_path is None or not local_path.is_file():
        finding.bucket = "NEEDS_REVIEW_NON_OFFICIAL"
        finding.blocking_reasons.append("local_file_missing")
        return finding
    finding.file_exists = True

    if finding.sha256_recorded:
        finding.sha256_recomputed = _sha256_of(local_path)
        finding.sha256_match = finding.sha256_recomputed == finding.sha256_recorded
    else:
        finding.sha256_match = False
        finding.blocking_reasons.append("no_recorded_sha256")
        finding.bucket = "NEEDS_REVIEW_NON_OFFICIAL"
        return finding

    # If a more recent ``[official_source_validation]`` block has
    # passed against the same file, treat that as the authoritative
    # ground truth. The validate command always recomputes the
    # sha256 against the live file at validation time, so this
    # supersedes a stale sha256 left in the older sync/manual block.
    validation_passed = (
        validation is not None
        and validation.get("validation_status") == "passed"
        and validation.get("file_exists") is True
        and validation.get("sha256_verified") is True
        and validation.get("sha256") == finding.sha256_recomputed
    )
    if validation_passed:
        finding.sha256_match = True

    if not finding.sha256_match:
        finding.bucket = "NEEDS_REVIEW_NON_OFFICIAL"
        finding.blocking_reasons.append("sha256_mismatch")
        return finding

    # If registry declares markers, marker_check_passed must be
    # True. The validate command's ``[official_source_validation]``
    # block is the freshest authority for this; fall back to the
    # sync/manual block when the validation block is absent.
    effective_marker_check = finding.marker_check_passed
    if validation is not None and "marker_check_passed" in validation:
        effective_marker_check = validation.get("marker_check_passed")
    if finding.registry_markers and effective_marker_check is False:
        finding.bucket = "NEEDS_REVIEW_NON_OFFICIAL"
        finding.blocking_reasons.append("marker_check_failed")
        return finding

    # All file invariants pass. Place into the calculation-ready
    # bucket only for sources where mapping work has not yet
    # completed.
    if src.slug in NOT_CALCULATION_READY_SLUGS:
        finding.bucket = "OFFICIAL_BUT_NOT_CALCULATION_READY"
        finding.candidate_for_manual_status_approval = True
        return finding

    # Already-approved IT decree: the only source where the
    # calculator IS active. Surface it as VALIDATED_OFFICIAL_SOURCE.
    finding.bucket = "VALIDATED_OFFICIAL_SOURCE"
    finding.candidate_for_manual_status_approval = src.status != "approved"
    return finding


def _draft_dataset_blockers() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for label in DRAFT_DATASET_LABELS:
        for ds in CompensationDataset.objects.filter(version_label=label):
            out.append(
                {
                    "version_label": ds.version_label,
                    "country": ds.country.code if ds.country_id else "",
                    "case_type": ds.case_type,
                    "status": ds.status,
                    "name": ds.name,
                    "source_slug": ds.source.slug if ds.source_id else "",
                    "blocking_reason": (
                        "non_official_source_validation_pending"
                        if ds.status == DatasetStatus.DRAFT
                        else f"unexpected_status={ds.status}"
                    ),
                }
            )
    return out


def _render_md(report: dict[str, Any]) -> str:
    lines = [
        "# Official-source validation readiness — pass 1",
        "",
        "Iter: F-legal-sources-official-validation-pass1.",
        "",
        f"- generated: `{report['generated_at']}`",
        f"- LegalSource rows audited: {report['total']}",
        "- bucket counts:",
    ]
    for bucket, n in report["bucket_counts"].items():
        lines.append(f"  - `{bucket}`: {n}")
    lines.extend(
        [
            "",
            "## Per-source classification",
            "",
            "| Country | Slug | Status | Bucket | sha256 match | marker | reasons |",
            "| --- | --- | :-: | --- | :-: | :-: | --- |",
        ]
    )
    for f in report["findings"]:
        marker_cell = "—"
        if f["marker_check_passed"] is True:
            marker_cell = "✓"
        elif f["marker_check_passed"] is False:
            marker_cell = "✗"
        sha_cell = "—"
        if f["sha256_recorded"]:
            sha_cell = "✓" if f["sha256_match"] else "✗"
        reasons = ", ".join(f["blocking_reasons"]) or "—"
        lines.append(
            f"| `{f['country']}` | `{f['slug']}` "
            f"| `{f['status']}` | `{f['bucket']}` "
            f"| {sha_cell} | {marker_cell} | {reasons} |"
        )
    lines.extend(
        [
            "",
            "## Draft datasets blocked",
            "",
            "| version_label | country | case_type | status | source_slug | reason |",
            "| --- | :-: | --- | :-: | --- | --- |",
        ]
    )
    for ds in report["draft_datasets_blocked"]:
        lines.append(
            f"| `{ds['version_label']}` | `{ds['country']}` "
            f"| `{ds['case_type']}` | `{ds['status']}` "
            f"| `{ds['source_slug']}` | {ds['blocking_reason']} |"
        )

    lines.extend(
        [
            "",
            "## What can be approved after this pass",
            "",
            "| Slug | Validated by file invariants | Manual status approval candidate |",
            "| --- | :-: | :-: |",
        ]
    )
    for f in report["findings"]:
        if f["bucket"] in (
            "VALIDATED_OFFICIAL_SOURCE",
            "OFFICIAL_BUT_NOT_CALCULATION_READY",
        ):
            lines.append(
                f"| `{f['slug']}` | ✓ "
                f"| {'✓' if f['candidate_for_manual_status_approval'] else '—'} |"
            )

    lines.extend(
        [
            "",
            "## Invariants enforced by this pass",
            "",
            "- No `LegalSource.status` change (file-only validation).",
            "- No `CompensationDataset` / `CalculationFormula` / " "`CompensationTableRow` write.",
            "- No `LegalReview` row created (no fake reviewer).",
            "- No FR / BE / MA / TN calculator activation.",
            "- IT 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", default=str(REPORT_MD))
    parser.add_argument("--report-json", default=str(REPORT_JSON))
    args = parser.parse_args()

    registry = _load_registry()
    findings: list[SourceFinding] = []
    bucket_counts: dict[str, int] = defaultdict(int)

    for src in LegalSource.objects.select_related("country").order_by("country__code", "slug"):
        finding = _classify(src, registry.get(src.slug))
        findings.append(finding)
        bucket_counts[finding.bucket] += 1

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "total": len(findings),
        "bucket_counts": dict(bucket_counts),
        "findings": [asdict(f) for f in findings],
        "draft_datasets_blocked": _draft_dataset_blockers(),
        "invariants": {
            "no_status_change": True,
            "no_dataset_write": True,
            "no_formula_write": True,
            "no_legal_review_created": True,
            "no_calculator_activation": True,
        },
    }

    md_path = pathlib.Path(args.report)
    if not md_path.is_absolute():
        md_path = (REPO_ROOT / md_path).resolve()
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_render_md(report), encoding="utf-8")

    json_path = pathlib.Path(args.report_json)
    if not json_path.is_absolute():
        json_path = (REPO_ROOT / json_path).resolve()
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[report-md]   {md_path}")
    print(f"[report-json] {json_path}")
    print(f"[summary] buckets={dict(bucket_counts)}  total={len(findings)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
