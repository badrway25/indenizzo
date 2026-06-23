"""Read-only Studio review BATCH builder (D3).

Composes D1 readiness (:mod:`apps.legal_sources.review_readiness`) and D2 evidence
(:mod:`apps.legal_sources.review_evidence`) into ordered, reviewer-oriented
*batches*: per source the safe evidence, readiness, latest decision, missing
steps, recommended action, a safe link to the generated review package, and a
**manual decision template** (a checklist placeholder the Studio fills by hand —
never parsed as a decision).

Strictly read-only and PII-safe. It NEVER approves a source, creates a
``LegalReview``, promotes a dataset or activates a calculator. Only safe fields
are emitted: no full hashes (only present/absent), no absolute paths (only the
repo-relative package path), no reviewer names/emails, no review notes, no raw
PDF/OCR/legal text.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

# The manual decision template. Rendered as text for the reviewer to fill in by
# hand in the back-office; it is NOT a machine decision and is never parsed.
DECISION_TEMPLATE = (
    "[ ] Reject",
    "[ ] Request changes",
    "[ ] Approve metadata only",
    "[ ] Approve for dataset seed review",
    "[ ] Escalate for second legal review",
)


@dataclass(frozen=True)
class ReviewBatchItem:
    country: str
    slug: str
    title: str
    status: str
    in_registry: bool
    calculation_ready: bool
    has_source_version: bool
    has_attachment: bool
    attachment_hash_present: bool
    has_review_package: bool
    review_package_path: str
    review_package_fresh: bool
    latest_review_decision: str
    readiness_status: str
    evidence_summary: str
    missing_steps: list[str]
    recommended_action: str
    fail_closed_reason: str
    decision_template: list[str]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _evidence_summary(ev) -> str:
    parts = ["attach=" + ("yes" if ev.has_attachment else "no")]
    if ev.has_attachment:
        parts.append("hash=" + ("yes" if ev.attachment_hash_present else "no"))
    parts.append("version=" + ("yes" if ev.has_source_version else "no"))
    parts.append("package=" + ("yes" if ev.has_review_package else "no"))
    return " · ".join(parts)


def _readiness_status(ev) -> str:
    if ev.calculation_ready:
        return "calc-ready"
    n = sum(
        (
            ev.needs_attachment,
            ev.needs_hash_check,
            not ev.has_source_version,
            ev.needs_legal_review,
        )
    )
    return f"needs {n} step(s)"


def build_review_batch(
    country: str | None = None,
    *,
    include_ready: bool = False,
    include_blocked: bool = True,
    limit: int | None = None,
    today: str = "",
) -> dict[str, Any]:
    """Build a read-only review batch (safe fields only).

    - ``include_blocked`` (default True): include sources that are NOT yet
      calculation-ready — the review work.
    - ``include_ready`` (default False): include calculation-ready sources too.
    - ``limit``: cap the number of items (logged in totals as ``truncated``).
    """
    from apps.legal_sources.review_evidence import build_evidence_checklist
    from apps.legal_sources.review_readiness import build_readiness_rows

    evidence = build_evidence_checklist(country, today=today)
    readiness = {r.slug: r for r in build_readiness_rows(country)}

    items: list[ReviewBatchItem] = []
    for ev in evidence:
        if ev.calculation_ready and not include_ready:
            continue
        if (not ev.calculation_ready) and not include_blocked:
            continue
        rd = readiness.get(ev.slug)
        items.append(
            ReviewBatchItem(
                country=ev.country,
                slug=ev.slug,
                title=ev.title,
                status=ev.status,
                in_registry=ev.in_registry,
                calculation_ready=ev.calculation_ready,
                has_source_version=ev.has_source_version,
                has_attachment=ev.has_attachment,
                attachment_hash_present=ev.attachment_hash_present,
                has_review_package=ev.has_review_package,
                review_package_path=ev.review_package_path,
                review_package_fresh=ev.review_package_fresh,
                latest_review_decision=ev.latest_review_decision,
                readiness_status=_readiness_status(ev),
                evidence_summary=_evidence_summary(ev),
                missing_steps=list(rd.missing_steps) if rd else [],
                recommended_action=(rd.recommended_next_action if rd else ""),
                fail_closed_reason=ev.never_calculation_ready_reason,
                decision_template=list(DECISION_TEMPLATE),
            )
        )

    total_before_limit = len(items)
    truncated = False
    if limit is not None and limit >= 0 and len(items) > limit:
        items = items[:limit]
        truncated = True

    summaries: dict[str, dict[str, int]] = {}
    for it in items:
        cs = summaries.setdefault(
            it.country, {"total": 0, "candidates": 0, "calculation_ready": 0, "with_package": 0}
        )
        cs["total"] += 1
        cs["candidates"] += int(it.in_registry)
        cs["calculation_ready"] += int(it.calculation_ready)
        cs["with_package"] += int(it.has_review_package)

    return {
        "generated_for": (country or "ALL"),
        "items": [it.as_dict() for it in items],
        "summaries": dict(sorted(summaries.items())),
        "totals": {
            "items": len(items),
            "matched_before_limit": total_before_limit,
            "truncated": truncated,
            "candidates": sum(1 for it in items if it.in_registry),
            "calculation_ready": sum(1 for it in items if it.calculation_ready),
        },
    }


def render_review_batch_json(batch: dict[str, Any]) -> str:
    import json

    return json.dumps(batch, indent=2, ensure_ascii=False)


def render_review_batch_markdown(batch: dict[str, Any], *, today: str = "") -> str:
    t = batch["totals"]
    lines = [f"# Studio Review Batch — {batch['generated_for']}"]
    if today:
        lines.append(f"_Date: {today}_")
    lines.append("")
    lines.append(
        "> Read-only batch from `python manage.py prepare_studio_review_batch`. "
        "It lists the sources a reviewer should work through, with evidence, "
        "readiness and a **manual** decision template. It **approves, promotes "
        "and activates nothing** — record real decisions in the back-office."
    )
    lines.append("")
    lines.append(
        f"**Totals:** items={t['items']} · candidates={t['candidates']} · "
        f"calculation_ready={t['calculation_ready']}"
        + (f" · (truncated from {t['matched_before_limit']})" if t["truncated"] else "")
    )
    lines.append("")
    if batch["summaries"]:
        lines.append("| Country | Items | Candidates | Calc-ready | With package |")
        lines.append("|:---:|---:|---:|---:|---:|")
        for cc, cs in batch["summaries"].items():
            lines.append(
                f"| {cc} | {cs['total']} | {cs['candidates']} | "
                f"{cs['calculation_ready']} | {cs['with_package']} |"
            )
        lines.append("")
    for it in batch["items"]:
        lines.append(f"## {it['country']} — `{it['slug']}`")
        lines.append(f"*{it['title']}*")
        lines.append("")
        lines.append(f"- status: **{it['status']}** · readiness: **{it['readiness_status']}**")
        lines.append(f"- evidence: {it['evidence_summary']}")
        lines.append(
            f"- candidate: {'yes' if it['in_registry'] else 'no'} · "
            f"latest review: {it['latest_review_decision'] or '—'} · "
            f"calculation-ready: {'yes' if it['calculation_ready'] else 'no'}"
        )
        pkg = it["review_package_path"] or "—"
        fresh = " (fresh)" if it["review_package_fresh"] else ""
        lines.append(f"- review package: {pkg}{fresh}")
        if it["fail_closed_reason"]:
            lines.append(f"- fail-closed: {it['fail_closed_reason']}")
        if it["missing_steps"]:
            lines.append("- missing steps:")
            lines.extend(f"  - {s}" for s in it["missing_steps"])
        lines.append(f"- recommended next action: {it['recommended_action'] or '—'}")
        lines.append("")
        lines.append("**Decision (fill in manually — not parsed):**")
        lines.extend(it["decision_template"])
        lines.append("")
    lines.append("---")
    lines.append(
        "**Do not use this batch for automatic calculation activation.** A source "
        "feeds a public calculation only after a real Studio approval, an APPROVED "
        "dataset with a source version, a validated engine mapping and an explicit "
        "activation decision. *Meglio nessun calcolo che un calcolo falso.*"
    )
    return "\n".join(lines)
