"""Read-only "verified disk evidence" bridge (D6).

OPS-1 found that some legacy APPROVED official sources record their validated file
via an on-disk ``official_downloaded/`` file + an ``[official_source_validation]``
notes block (with the file's sha256) rather than via a ``LegalSourceAttachment``
DB row. The D5 audit / D4 validator only checked the attachment row, so those
sources were flagged as false "missing attachment" blockers.

This module recognises a *second, conservative* form of evidence —
``verified_official_downloaded_file`` — WITHOUT creating any attachment row, hash
or DB write, and without any network access. It is accepted ONLY when ALL hold:

1. the source slug is a registry candidate;
2. an ``official_downloaded/<slug>.<ext>`` file exists on disk (any extension);
3. the source notes carry an ``[official_source_validation]`` block whose
   ``validation_status`` is ``passed`` (a PRESENT-BUT-FAILED block is rejected —
   OPS-1 wrongly assumed presence meant success; BE/TN actually have
   ``validation_status=failed`` and stay blocking, which is the honest result);
4. the file on disk hashes to EXACTLY the ``sha256`` recorded in that marker
   (so the file IS the validated official file — no tampering, no other file).

Strictly read-only and PII-safe: it reads the file only to compute its hash for
the equality check; it NEVER prints the raw content, the full hash, an absolute
path, the reviewer or the notes. In CI (where ``legal_data/`` may be absent) the
file is simply not present, so evidence is False — deterministic and testable via
a temp ``legal_data_root``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Country ISO code -> legal_data/sources/<folder>/ (mirrors sync_official_sources).
COUNTRY_FOLDER_BY_CODE: dict[str, str] = {
    "IT": "italy",
    "EU": "eu",
    "FR": "france",
    "BE": "belgium",
    "MA": "morocco",
    "TN": "tunisia",
}
_VALIDATION_BEGIN = "[official_source_validation] BEGIN"
_VALIDATION_END = "[official_source_validation] END"

KIND_ATTACHMENT_ROW = "legal_source_attachment"
KIND_VERIFIED_DISK = "verified_official_downloaded_file"
KIND_NONE = "none"


@dataclass(frozen=True)
class DiskEvidenceResult:
    has_verified_disk_evidence: bool
    evidence_kind: str
    file_present: bool
    validation_marker_present: bool
    hash_present: bool  # bool only — the full hash is never exposed
    hash_matches_marker: bool
    safe_relative_path: str  # repo-relative, or "" when no evidence
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    recommended_action: str = ""

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_validation_block(notes: str | None) -> dict[str, Any] | None:
    notes = notes or ""
    if _VALIDATION_BEGIN not in notes:
        return None
    body = notes.split(_VALIDATION_BEGIN, 1)[1].split(_VALIDATION_END, 1)[0].strip()
    try:
        import json

        return json.loads(body)
    except (ValueError, IndexError):
        return None


def _has_attachment_row(source) -> bool:
    return source.attachments.exclude(sha256="").exists()


def evaluate_verified_disk_evidence(source, *, legal_data_root=None) -> DiskEvidenceResult:
    """Evaluate a source's evidence (attachment row OR verified disk file). Read-only."""
    # A real LegalSourceAttachment row (hashed) is the primary evidence.
    if _has_attachment_row(source):
        return DiskEvidenceResult(
            has_verified_disk_evidence=True,
            evidence_kind=KIND_ATTACHMENT_ROW,
            file_present=True,
            validation_marker_present=True,
            hash_present=True,
            hash_matches_marker=True,
            safe_relative_path="",
            recommended_action="attachment row present",
        )

    from django.conf import settings

    from apps.legal_sources.review_evidence import _load_registry

    registry = _load_registry()
    entry = registry.get(source.slug)
    cc = (source.country.code if source.country_id else "").upper()
    folder = COUNTRY_FOLDER_BY_CODE.get(cc, cc.lower())
    root = Path(legal_data_root or settings.LEGAL_DATA_ROOT)
    # Find official_downloaded/<slug>.<ext> by GLOB (any extension) so a registry
    # expected_format mismatch (e.g. EU recorded html, file is xml) is tolerated.
    official_dir = root / "sources" / folder / "official_downloaded"
    path = None
    if entry is not None and official_dir.is_dir():
        for cand in sorted(official_dir.glob(f"{source.slug}.*")):
            if cand.suffix.lower() != ".json":  # skip manifests
                path = cand
                break
    file_present = path is not None
    rel = f"sources/{folder}/official_downloaded/{path.name}" if file_present else ""

    block = _parse_validation_block(source.notes)
    # PRESENT-BUT-FAILED blocks are rejected: require validation_status == passed.
    marker = bool(block and block.get("validation_status") == "passed")
    stored_sha = (block or {}).get("sha256", "") if block else ""

    hash_present = False
    hash_match = False
    if file_present:
        try:
            from apps.legal_sources.utils import compute_sha256

            with open(path, "rb") as fh:
                computed = compute_sha256(fh)
            hash_present = bool(computed)
            hash_match = bool(stored_sha) and computed == stored_sha
        except OSError:
            pass

    blocking: list[str] = []
    if entry is None:
        blocking.append("not a registry candidate")
    elif not file_present:
        blocking.append("no official_downloaded file on disk")
    elif not marker:
        blocking.append(
            "validation block is not 'passed' (or absent) — legacy validation did not succeed"
        )
    elif not hash_match:
        blocking.append("on-disk file hash does not match the validation marker")

    has = entry is not None and file_present and marker and hash_match
    return DiskEvidenceResult(
        has_verified_disk_evidence=has,
        evidence_kind=KIND_VERIFIED_DISK if has else KIND_NONE,
        file_present=file_present,
        validation_marker_present=marker,
        hash_present=hash_present,
        hash_matches_marker=hash_match,
        safe_relative_path=(rel if has else ""),
        blocking_reasons=blocking,
        recommended_action=(
            "verified legacy disk evidence (official_downloaded file matches the validation marker)"
            if has
            else "attach/verify the official file (no verified disk evidence)"
        ),
    )


def has_evidence(source, *, legal_data_root=None) -> bool:
    """True if the source has an attachment row OR verified disk evidence."""
    return evaluate_verified_disk_evidence(
        source, legal_data_root=legal_data_root
    ).has_verified_disk_evidence
