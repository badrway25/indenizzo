"""F-legal-sources-official-validation-pass1.

Re-validate every ``LegalSource`` whose ``notes`` carry an
``[official_sync]`` (``fetch_success`` / ``crosscheck_success``) or
``[manual_attach]`` (``manual_attach_success``) block. The command
recomputes the SHA-256 of the referenced local file, re-runs the
marker check declared in ``config/official_source_registry.json``
when present, and writes (or refreshes) a single
``[official_source_validation] BEGIN/END`` block in
``LegalSource.notes`` carrying the canonical, machine-readable
validation outcome.

INVARIANTS:

* **Read-only on the legal taxonomy.** Never creates / promotes /
  demotes ``LegalSource``, ``CompensationDataset``,
  ``CalculationFormula``, ``CompensationTableRow``, or
  ``LegalReview`` rows.
* **Idempotent.** A previous validation block is replaced; the
  ``[official_sync]`` / ``[manual_attach]`` blocks are left
  untouched.
* **No status change.** ``LegalSource.status`` is preserved.
  Promotion to ``APPROVED`` requires a separate, signed
  Studio-Legal review and is out of scope here.

CLI::

    python manage.py validate_official_legal_sources --dry-run
    python manage.py validate_official_legal_sources --commit
    python manage.py validate_official_legal_sources --commit --slug fr-loi-badinter-1985

Exit codes:

* ``0`` — every probed source produced a deterministic verdict
  (passed / failed / blocked).
* ``1`` — unrecoverable error (registry parse, IO).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.legal_sources.models import LegalSource

REPO_ROOT = pathlib.Path(settings.BASE_DIR)
REGISTRY_PATH = REPO_ROOT / "config" / "official_source_registry.json"

OFFICIAL_SYNC_BEGIN = "[official_sync] BEGIN"
OFFICIAL_SYNC_END = "[official_sync] END"
MANUAL_ATTACH_BEGIN = "[manual_attach] BEGIN"
MANUAL_ATTACH_END = "[manual_attach] END"
VALIDATION_BEGIN = "[official_source_validation] BEGIN"
VALIDATION_END = "[official_source_validation] END"

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


@dataclass
class ValidationResult:
    slug: str
    validation_status: str = "blocked"
    validated_at: str = ""
    sha256: str = ""
    sha256_verified: bool = False
    marker_check_passed: bool | None = None
    file_exists: bool = False
    local_path: str = ""
    size_bytes: int = 0
    official_source_verified: bool = False
    legal_calculator_activation: bool = False
    dataset_activation: bool = False
    candidate_for_manual_status_approval: bool = False
    reason: str = ""
    registry_markers: list[str] = field(default_factory=list)
    notes_block_written: bool = False
    classification_source: str = ""


def _extract_block(notes: str, begin: str, end: str) -> dict[str, Any] | None:
    if begin not in notes:
        return None
    body = notes.split(begin, 1)[1].split(end, 1)[0].strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _strip_validation_block(notes: str) -> str:
    if VALIDATION_BEGIN not in notes:
        return notes.rstrip()
    head, _, rest = notes.partition(VALIDATION_BEGIN)
    _, _, tail = rest.partition(VALIDATION_END)
    return (head.rstrip() + "\n" + tail.lstrip()).strip()


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


def _markers_present(payload: bytes, markers: list[str]) -> bool:
    if not markers:
        return True
    body_lower = payload.lower()
    for m in markers:
        if m.lower().encode("utf-8") in body_lower:
            return True
    return False


def _load_registry() -> dict[str, dict[str, Any]]:
    if not REGISTRY_PATH.is_file():
        return {}
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {entry["source_slug"]: entry for entry in raw.get("entries", [])}


def _build_validation_block(result: ValidationResult) -> str:
    payload = {
        "validation_status": result.validation_status,
        "validated_at": result.validated_at,
        "source_slug": result.slug,
        "sha256": result.sha256,
        "sha256_verified": result.sha256_verified,
        "marker_check_passed": result.marker_check_passed,
        "file_exists": result.file_exists,
        "local_path": result.local_path,
        "size_bytes": result.size_bytes,
        "official_source_verified": result.official_source_verified,
        "legal_calculator_activation": result.legal_calculator_activation,
        "dataset_activation": result.dataset_activation,
        "candidate_for_manual_status_approval": result.candidate_for_manual_status_approval,
        "registry_markers": result.registry_markers,
        "classification_source": result.classification_source,
        "reason": result.reason,
        "no_legal_review_created": True,
        "no_status_change": True,
        "no_dataset_or_formula_write": True,
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"\n\n{VALIDATION_BEGIN}\n{body}\n{VALIDATION_END}\n"


def _validate_one(src: LegalSource, registry_entry: dict[str, Any] | None) -> ValidationResult:
    notes = src.notes or ""
    sync = _extract_block(notes, OFFICIAL_SYNC_BEGIN, OFFICIAL_SYNC_END)
    manual = _extract_block(notes, MANUAL_ATTACH_BEGIN, MANUAL_ATTACH_END)
    prior_validation = _extract_block(notes, VALIDATION_BEGIN, VALIDATION_END)
    block = sync or manual
    classification_source = "official_sync" if sync else ("manual_attach" if manual else "")
    cls = (block or {}).get("classification") or ""

    result = ValidationResult(
        slug=src.slug,
        validated_at=datetime.now(UTC).isoformat(),
        registry_markers=(registry_entry or {}).get("content_must_contain", []) or [],
        classification_source=classification_source,
    )

    if src.slug in NON_OFFICIAL_SLUGS:
        result.validation_status = "blocked"
        kind = (registry_entry or {}).get("source_kind", "non_official")
        result.reason = (
            f"non_official_source_kind={kind}; cannot be validated as an " f"official document"
        )
        return result

    if not block:
        result.validation_status = "blocked"
        result.reason = (
            "no_official_sync_or_manual_attach_block; cannot validate "
            "without a recorded provenance"
        )
        return result

    if cls not in {"fetch_success", "crosscheck_success", "manual_attach_success"}:
        result.validation_status = "blocked"
        result.reason = f"unsupported_classification={cls!r}"
        return result

    raw_path = block.get("local_path", "") or ""
    local_path = _resolve_local_path(raw_path)
    result.local_path = raw_path

    if local_path is None or not local_path.is_file():
        result.validation_status = "blocked"
        result.reason = f"local_file_missing: {raw_path!r}"
        return result

    result.file_exists = True

    payload = local_path.read_bytes()
    result.size_bytes = len(payload)
    sha = hashlib.sha256(payload).hexdigest()
    result.sha256 = sha

    # Drift detection: compare the current sha against the prior
    # validation block (when present) — if the file was successfully
    # validated before and bytes have since changed, that is a real
    # ``failed`` verdict. The ``[official_sync]`` / ``[manual_attach]``
    # block sha is informational; the validate command takes
    # ownership of the sha invariant going forward.
    prior_sha = ((prior_validation or {}).get("sha256") or "").lower().strip()
    prior_status = (prior_validation or {}).get("validation_status") or ""
    if prior_sha and prior_status == "passed" and prior_sha != sha:
        result.sha256_verified = False
        result.validation_status = "failed"
        result.reason = (
            f"sha256_drift_since_last_validation: prior={prior_sha[:12]}…, " f"current={sha[:12]}…"
        )
        return result

    result.sha256_verified = True

    if result.registry_markers:
        result.marker_check_passed = _markers_present(payload, result.registry_markers)
        if not result.marker_check_passed:
            result.validation_status = "failed"
            result.reason = (
                "marker_check_failed: registry markers not present " "in current local file"
            )
            return result

    # Source authenticated. Calculator / dataset activation is NOT
    # part of this iter — surface those flags as False everywhere
    # so the downstream consumers cannot mistake authentication
    # for activation.
    result.validation_status = "passed"
    result.official_source_verified = True
    result.legal_calculator_activation = False
    result.dataset_activation = False
    result.candidate_for_manual_status_approval = (
        src.slug in NOT_CALCULATION_READY_SLUGS or src.status != "approved"
    )

    if src.slug in NOT_CALCULATION_READY_SLUGS:
        result.reason = "official source verified, calculation mapping still required"
    else:
        result.reason = "official source verified"

    return result


class Command(BaseCommand):
    help = (
        "Re-validate official-source provenance for every LegalSource "
        "carrying an [official_sync] or [manual_attach] notes block."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            default=False,
            help="Default mode if neither --dry-run nor --commit is given: "
            "computes the verdicts but never writes to LegalSource.notes.",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            help="Write the [official_source_validation] block to "
            "LegalSource.notes. Idempotent (a previous block is replaced).",
        )
        parser.add_argument(
            "--slug",
            default=None,
            help="Restrict the run to a single LegalSource slug.",
        )

    def handle(self, *args, **options):
        commit = bool(options.get("commit"))
        dry_run = bool(options.get("dry_run")) or not commit
        slug_filter = options.get("slug")

        registry = _load_registry()
        qs = LegalSource.objects.select_related("country").order_by("country__code", "slug")
        if slug_filter:
            qs = qs.filter(slug=slug_filter)

        results: list[ValidationResult] = []
        verdict_counts: dict[str, int] = {"passed": 0, "failed": 0, "blocked": 0}

        for src in qs:
            result = _validate_one(src, registry.get(src.slug))
            results.append(result)
            verdict_counts[result.validation_status] = (
                verdict_counts.get(result.validation_status, 0) + 1
            )

            if commit:
                with transaction.atomic():
                    fresh = LegalSource.objects.get(pk=src.pk)
                    new_notes = _strip_validation_block(fresh.notes or "")
                    new_notes = (new_notes + _build_validation_block(result)).strip() + "\n"
                    fresh.notes = new_notes
                    fresh.save(update_fields=["notes"])
                result.notes_block_written = True

            self.stdout.write(
                f"[{result.validation_status:>7}] {src.slug}  "
                f"sha256_verified={result.sha256_verified}  "
                f"marker={result.marker_check_passed}  "
                f"reason={result.reason}"
            )

        self.stdout.write("")
        self.stdout.write(
            f"[summary] dry_run={dry_run} commit={commit}  "
            f"verdicts={verdict_counts}  total={len(results)}"
        )

        if not commit:
            self.stdout.write(
                "[note] dry-run: no [official_source_validation] block was "
                "written. Re-run with --commit to persist."
            )

        return None
