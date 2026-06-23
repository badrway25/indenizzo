"""Read-only legacy attachment-alignment audit (D5).

Explains the strict-validator blocking findings: legal sources whose latest review
is ``approve`` but which lack a ``LegalSourceAttachment`` DB row (they were
promoted on a disk-file validation without an attachment row), plus softer gaps
(no hash, no source version). It classifies each gap and recommends the safe
resolution — WITHOUT inventing attachments or hashes and WITHOUT activating any
calculation.

Strictly read-only and PII-safe (present/absent flags only; no full hashes, no
absolute paths, no reviewer names, no review notes, no raw legal text). It never
attaches a file, approves a source, promotes a dataset or activates an engine —
the only safe way to attach an official file is the existing
``attach_official_source_file`` workflow, run by the Studio/ops with the real
file (D5 does not do it).

Classifications:
- ``ok`` — not an open ``approve``, or approve with attachment + hash.
- ``missing_attachment_row`` — approve, no attachment, but a registry candidate
  exists → attach the official file via the registry workflow (BLOCKING).
- ``manual_review_required`` — approve, no attachment, and NOT a registry
  candidate → the Studio must source the official file first (BLOCKING).
- ``hash_unavailable`` — approve, attachment present but not hash-verified
  (BLOCKING).
- ``missing_source_version`` — approve, attachment + hash, but no
  ``LegalSourceVersion`` (WARNING).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

CLASS_OK = "ok"
CLASS_MISSING_ATTACHMENT = "missing_attachment_row"
CLASS_MANUAL_REVIEW = "manual_review_required"
CLASS_HASH_UNAVAILABLE = "hash_unavailable"
CLASS_MISSING_VERSION = "missing_source_version"

IMPACT_BLOCKING = "blocking"
IMPACT_WARNING = "warning"
IMPACT_NONE = "none"


@dataclass(frozen=True)
class AttachmentAlignmentItem:
    country: str
    slug: str
    title: str
    latest_review_decision: str
    has_source_version: bool
    has_attachment: bool
    attachment_hash_present: bool
    in_registry: bool
    classification: str
    strict_validator_impact: str
    recommended_action: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _classify_row(ev) -> AttachmentAlignmentItem:
    decision = ev.latest_review_decision or ""
    if decision != "approve":
        cls, impact, action = CLASS_OK, IMPACT_NONE, "no open approval — nothing to align"
    elif not ev.has_attachment:
        if ev.in_registry:
            cls = CLASS_MISSING_ATTACHMENT
            impact = IMPACT_BLOCKING
            action = (
                "attach the official source file via `attach_official_source_file` "
                "(registry candidate), then re-validate — do NOT invent an attachment"
            )
        else:
            cls = CLASS_MANUAL_REVIEW
            impact = IMPACT_BLOCKING
            action = "Studio must source the official file before this approval can stand"
    elif not ev.attachment_hash_present:
        cls = CLASS_HASH_UNAVAILABLE
        impact = IMPACT_BLOCKING
        action = "verify the attachment SHA-256 (`validate_official_legal_sources`)"
    elif not ev.has_source_version:
        cls = CLASS_MISSING_VERSION
        impact = IMPACT_WARNING
        action = "create a LegalSourceVersion before relying on this approval"
    else:
        cls, impact, action = CLASS_OK, IMPACT_NONE, "aligned — attachment + hash + version present"

    return AttachmentAlignmentItem(
        country=ev.country,
        slug=ev.slug,
        title=ev.title,
        latest_review_decision=decision,
        has_source_version=ev.has_source_version,
        has_attachment=ev.has_attachment,
        attachment_hash_present=ev.attachment_hash_present,
        in_registry=ev.in_registry,
        classification=cls,
        strict_validator_impact=impact,
        recommended_action=action,
    )


def classify_attachment_gap(source) -> AttachmentAlignmentItem | None:
    """Classify a single source's attachment gap (or None if not found)."""
    from apps.legal_sources.review_evidence import build_evidence_checklist

    country = source.country.code if source.country_id else None
    for ev in build_evidence_checklist(country):
        if ev.slug == source.slug:
            return _classify_row(ev)
    return None


def build_legacy_attachment_alignment_report(
    country: str | None = None, *, include_ok: bool = False
) -> dict[str, Any]:
    """Read-only alignment report (blocking/warning gaps + per-country roll-up)."""
    from apps.legal_sources.review_evidence import build_evidence_checklist

    items = [_classify_row(ev) for ev in build_evidence_checklist(country)]
    if not include_ok:
        items = [it for it in items if it.classification != CLASS_OK]

    summaries: dict[str, dict[str, int]] = {}
    for it in items:
        cs = summaries.setdefault(it.country, {"items": 0, "blocking": 0, "warning": 0})
        cs["items"] += 1
        if it.strict_validator_impact == IMPACT_BLOCKING:
            cs["blocking"] += 1
        elif it.strict_validator_impact == IMPACT_WARNING:
            cs["warning"] += 1

    return {
        "country": country or "ALL",
        "items": [it.as_dict() for it in items],
        "summaries": dict(sorted(summaries.items())),
        "totals": {
            "items": len(items),
            "blocking": sum(1 for it in items if it.strict_validator_impact == IMPACT_BLOCKING),
            "warning": sum(1 for it in items if it.strict_validator_impact == IMPACT_WARNING),
            "manual_review_required": sum(
                1 for it in items if it.classification == CLASS_MANUAL_REVIEW
            ),
        },
    }


def has_blocking_attachment_gap(country: str | None = None) -> bool:
    """True if any source has a blocking attachment-alignment gap (for hints)."""
    return build_legacy_attachment_alignment_report(country)["totals"]["blocking"] > 0
