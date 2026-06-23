"""Read-only legal-source REVIEW READINESS consolidation (D1).

Builds on :mod:`apps.legal_sources.status_report` and adds, per source: the
latest Studio review decision, the concrete *missing steps* before the source
could ever back a calculation, a recommended next action, and two fail-closed
invariants Studio/CI can assert.

Strictly read-only: no DB writes, no network, no PII, no secrets. This module
NEVER promotes a source, approves a dataset, or activates a calculator — it only
*reports* what a human reviewer still has to do. Fail-closed by construction:
when in doubt a source is reported as NOT calculation-ready.

Cardinal rule (project architecture, "meglio nessun calcolo che un calcolo
falso"): ``status == approved`` authenticates the document; ``calculation_ready``
is true only when the source backs an APPROVED ``CompensationDataset`` linked to
a source version. FR/BE/MA/TN have sources under review but none are
calculation-ready.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ReadinessRow:
    country: str
    slug: str
    title: str
    source_type: str
    status: str
    reliability: str
    version_count: int
    attachment_count: int
    hashed_attachment_count: int
    latest_review_decision: str
    latest_review_at: str
    latest_review_reviewer: str
    calculation_ready: bool
    missing_steps: list[str]
    recommended_next_action: str


def _latest_review_map(slugs: list[str]) -> dict[str, Any]:
    """slug -> latest LegalReview (or None). Append-only, ordered -created_at."""
    from apps.legal_sources.models import LegalReview

    out: dict[str, Any] = {}
    # one row per source: the most recent review wins (queryset already ordered)
    for rev in LegalReview.objects.filter(source__slug__in=slugs).select_related(
        "source", "reviewer"
    ):
        out.setdefault(rev.source.slug, rev)  # first seen = latest (ordering)
    return out


def _missing_steps(row, latest_decision: str, calculation_ready: bool) -> list[str]:
    """Concrete, fail-closed checklist of what is still missing. Ordered."""
    from apps.legal_sources.enums import SourceStatus

    steps: list[str] = []
    if row.attachment_count == 0:
        steps.append("attach the official source file")
    elif row.hashed_attachment_count < row.attachment_count:
        steps.append("compute/verify the SHA-256 of every attachment")
    if row.version_count == 0:
        steps.append("create a LegalSourceVersion")
    if latest_decision != "approve":
        steps.append("obtain a Studio legal review (approve)")
    if row.status != SourceStatus.APPROVED:
        steps.append("promote the source to APPROVED (after review)")
    if not calculation_ready:
        # The calculation-activation step is intentionally LAST and is a
        # separate, human-gated decision — never performed by this report.
        steps.append("seed + approve a CompensationDataset with a source version")
    return steps


def build_readiness_rows(country: str | None = None) -> list[ReadinessRow]:
    """One :class:`ReadinessRow` per LegalSource (optionally filtered)."""
    from apps.legal_sources.status_report import build_rows

    base_rows = build_rows(country)
    latest = _latest_review_map([r.slug for r in base_rows])

    out: list[ReadinessRow] = []
    for r in base_rows:
        rev = latest.get(r.slug)
        decision = rev.decision if rev else ""
        steps = _missing_steps(r, decision, r.calculation_ready)
        out.append(
            ReadinessRow(
                country=r.country,
                slug=r.slug,
                title=r.title,
                source_type=r.source_type,
                status=r.status,
                reliability=r.reliability,
                version_count=r.version_count,
                attachment_count=r.attachment_count,
                hashed_attachment_count=r.hashed_attachment_count,
                latest_review_decision=decision,
                latest_review_at=rev.created_at.isoformat() if rev else "",
                latest_review_reviewer=(
                    rev.reviewer.get_username() if rev and rev.reviewer_id else ""
                ),
                calculation_ready=r.calculation_ready,
                missing_steps=steps,
                recommended_next_action=(steps[0] if steps else "ready — no action"),
            )
        )
    return out


def approved_datasets_without_source_version() -> list[str]:
    """Names of APPROVED CompensationDatasets missing a source_version.

    Should always be empty (H1-9 DB constraint). Surfaced as a fail-closed
    ops assertion.
    """
    from apps.compensation.models import CompensationDataset, DatasetStatus

    return list(
        CompensationDataset.objects.filter(
            status=DatasetStatus.APPROVED, source_version__isnull=True
        ).values_list("name", flat=True)
    )


def calculation_ready_without_approve_review(rows: list[ReadinessRow]) -> list[str]:
    """Slugs that are calculation-ready but lack an ``approve`` review.

    A calculation-ready source must carry a recorded Studio approval. Anything
    else is an unsafe activation and is flagged fail-closed.
    """
    return [r.slug for r in rows if r.calculation_ready and r.latest_review_decision != "approve"]


def build_readiness_report(country: str | None = None) -> dict[str, Any]:
    """Structured report: rows + per-country roll-up + global totals."""
    rows = build_readiness_rows(country)
    summaries: dict[str, dict[str, int]] = {}
    for r in rows:
        cs = summaries.setdefault(
            r.country,
            {"total": 0, "calculation_ready": 0, "approve_reviewed": 0, "needs_steps": 0},
        )
        cs["total"] += 1
        if r.calculation_ready:
            cs["calculation_ready"] += 1
        if r.latest_review_decision == "approve":
            cs["approve_reviewed"] += 1
        if r.missing_steps:
            cs["needs_steps"] += 1
    return {
        "rows": [r.__dict__ for r in rows],
        "summaries": dict(sorted(summaries.items())),
        "totals": {
            "sources": len(rows),
            "calculation_ready": sum(1 for r in rows if r.calculation_ready),
            "approve_reviewed": sum(1 for r in rows if r.latest_review_decision == "approve"),
            "needs_steps": sum(1 for r in rows if r.missing_steps),
        },
    }
