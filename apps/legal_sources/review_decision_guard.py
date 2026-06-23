"""Read-only safety guard for manual LegalReview decisions (D4).

Evaluates whether a manual review decision is *coherent* with the evidence
(attachment, hash, source version, review package) before the Studio records it
in the back-office. It NEVER creates a review, approves a source, promotes a
dataset or activates a calculator — it only reports. ``approve`` always carries
``calculation_activation_allowed = False``: authenticating a document is never,
by itself, a calculation activation.

Prudent rules:
- ``reject`` / ``request_changes`` / ``reopen`` — always allowed.
- ``approve`` — BLOCKED (clearly incoherent) when there is no official
  attachment, or the attachment is not hash-verified; WARNED when a source
  version or a generated review package is missing.

Used by the LegalReview admin form (blocking validation) and the read-only
``validate_legal_review_decisions`` command.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

DECISION_APPROVE = "approve"
DECISION_REJECT = "reject"
DECISION_REQUEST_CHANGES = "request_changes"
DECISION_REOPEN = "reopen"

SEVERITY_OK = "ok"
SEVERITY_WARNING = "warning"
SEVERITY_BLOCKING = "blocking"


@dataclass(frozen=True)
class DecisionGuardResult:
    decision: str
    allowed: bool
    severity: str
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommended_next_action: str = ""
    evidence_summary: str = ""
    # Authenticating a document is never a calculation activation.
    calculation_activation_allowed: bool = False

    def as_dict(self) -> dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)


def _evidence_for(source) -> Any | None:
    """The D2 EvidenceRow for a single source (or None)."""
    from apps.legal_sources.review_evidence import build_evidence_checklist

    country = source.country.code if source.country_id else None
    for row in build_evidence_checklist(country):
        if row.slug == source.slug:
            return row
    return None


def evaluate_legal_review_decision(source, decision: str) -> DecisionGuardResult:
    """Evaluate a manual decision against the source's evidence. Read-only."""
    decision = (decision or "").strip()
    ev = _evidence_for(source)

    if ev is None:
        summary = "no evidence row"
        has_attach = has_hash = has_version = has_pkg = False
    else:
        has_attach = ev.has_attachment
        has_hash = ev.attachment_hash_present
        has_version = ev.has_source_version
        has_pkg = ev.has_review_package
        summary = (
            f"attachment={'yes' if has_attach else 'no'} · "
            f"hash={'yes' if has_hash else 'no'} · "
            f"version={'yes' if has_version else 'no'} · "
            f"package={'yes' if has_pkg else 'no'}"
        )

    warnings: list[str] = []
    blocking: list[str] = []

    if decision == DECISION_APPROVE:
        if not has_attach:
            # D6: an approve with no attachment ROW is still coherent when the
            # source carries verified disk evidence (a validated official_downloaded
            # file whose hash matches the validation marker). Otherwise blocking.
            from apps.legal_sources.verified_disk_evidence import evaluate_verified_disk_evidence

            disk = evaluate_verified_disk_evidence(source)
            if disk.has_verified_disk_evidence:
                warnings.append(
                    "no attachment row, but verified legacy disk evidence present "
                    "(validated official_downloaded file) — document-level only"
                )
                summary += " · verified_disk_evidence=yes"
            else:
                blocking.append("no official attachment — cannot approve an unattached source")
        elif not has_hash:
            blocking.append("attachment is not hash-verified — verify the SHA-256 before approving")
        if not has_version:
            warnings.append("no LegalSourceVersion — create one before relying on this approval")
        if not has_pkg:
            warnings.append("no generated review package for this country")
        recommended = (
            "fix the blocking evidence gap, then re-evaluate"
            if blocking
            else "approval may proceed (document-level only) — it does NOT activate any calculation"
        )
    elif decision in (DECISION_REJECT, DECISION_REQUEST_CHANGES, DECISION_REOPEN):
        recommended = "record the decision with a clear comment"
    else:
        blocking.append(f"unknown decision: {decision!r}")
        recommended = "use one of: approve / reject / request_changes / reopen"

    severity = SEVERITY_BLOCKING if blocking else (SEVERITY_WARNING if warnings else SEVERITY_OK)
    return DecisionGuardResult(
        decision=decision,
        allowed=not blocking,
        severity=severity,
        warnings=warnings,
        blocking_reasons=blocking,
        recommended_next_action=recommended,
        evidence_summary=summary,
        calculation_activation_allowed=False,
    )
