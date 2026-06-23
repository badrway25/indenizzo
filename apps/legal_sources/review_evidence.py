"""Read-only legal-source EVIDENCE checklist + review-pack index (D2).

Builds on :mod:`apps.legal_sources.review_readiness` (D1) and adds, per source,
the *evidence* a Studio reviewer needs: official attachment present? hash
present? source version? a generated review package for the country? latest
review + its age? plus crisp "ready for Studio review" / "ready for dataset-seed
review" flags and a fail-closed "why not calculation-ready" reason.

Strictly read-only and PII-safe: no DB writes, no network, no raw PDF/OCR text.
It NEVER promotes a source, approves a dataset, or activates a calculator. Only
registry METADATA and on-disk package filenames are read — never document
contents.

Cardinal rule ("meglio nessun calcolo che un calcolo falso"): authenticating a
document is necessary but not sufficient. ``calculation_ready`` is true only when
a source backs an APPROVED dataset linked to a source version — today only Italy.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REGISTRY_PATH = REPO_ROOT / "config" / "official_source_registry.json"
GENERATED_DIR = REPO_ROOT / "docs" / "legal_sources" / "generated"
_PACKAGE_RE = re.compile(r"^([A-Z]{2})_REVIEW_PACKAGE_GENERATED_(\d{4}-\d{2}-\d{2})\.md$")
_FRESH_DAYS = 30


@dataclass(frozen=True)
class EvidenceRow:
    country: str
    slug: str
    title: str
    status: str
    in_registry: bool
    has_source_version: bool
    has_attachment: bool
    attachment_hash_present: bool
    has_review_package: bool
    review_package_path: str
    review_package_date: str
    review_package_fresh: bool
    latest_review_decision: str
    latest_review_age_days: int | None
    needs_ocr: bool
    needs_attachment: bool
    needs_hash_check: bool
    needs_legal_review: bool
    ready_for_studio_review: bool
    ready_for_dataset_seed_review: bool
    calculation_ready: bool
    never_calculation_ready_reason: str


def _load_registry() -> dict[str, dict[str, Any]]:
    """slug -> registry entry (metadata only). Empty dict if absent."""
    if not REGISTRY_PATH.is_file():
        return {}
    data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    return {e["source_slug"]: e for e in data.get("entries", []) if e.get("source_slug")}


def review_package_index(today: str = "") -> dict[str, dict[str, str]]:
    """country code -> {path, date, fresh} for the latest generated package.

    ``today`` (ISO ``YYYY-MM-DD``) is optional; when given, freshness is computed
    against it (callers pass a stamp to keep the function pure/deterministic).
    """
    out: dict[str, dict[str, Any]] = {}
    if not GENERATED_DIR.is_dir():
        return out
    for p in GENERATED_DIR.iterdir():
        m = _PACKAGE_RE.match(p.name)
        if not m:
            continue
        cc, date = m.group(1), m.group(2)
        prev = out.get(cc)
        if prev is None or date > prev["date"]:
            out[cc] = {
                "path": f"docs/legal_sources/generated/{p.name}",
                "date": date,
            }
    if today:
        for info in out.values():
            info["fresh"] = _days_between(info["date"], today) <= _FRESH_DAYS
    return out


def _days_between(d1: str, d2: str) -> int:
    from datetime import date

    a = date.fromisoformat(d1)
    b = date.fromisoformat(d2)
    return abs((b - a).days)


def _never_ready_reason(status: str, calculation_ready: bool) -> str:
    from apps.legal_sources.enums import SourceStatus

    if calculation_ready:
        return ""
    if status != SourceStatus.APPROVED:
        return "source document not APPROVED yet"
    return "no APPROVED dataset backs this source (calculation mapping not validated)"


def build_evidence_checklist(country: str | None = None, *, today: str = "") -> list[EvidenceRow]:
    """One :class:`EvidenceRow` per LegalSource (optionally filtered)."""
    from datetime import datetime

    from apps.legal_sources.review_readiness import build_readiness_rows

    registry = _load_registry()
    packages = review_package_index(today=today)
    base_rows = build_readiness_rows(country)

    # latest_review_age needs the raw datetime; recompute the map once.
    from apps.legal_sources.models import LegalReview

    age_by_slug: dict[str, int] = {}
    now = datetime.now(UTC) if not today else None
    ref = now or datetime.fromisoformat(today + "T00:00:00+00:00")
    for rev in (
        LegalReview.objects.filter(source__slug__in=[r.slug for r in base_rows])
        .order_by("-created_at", "-pk")
        .only("source__slug", "created_at", "source")
        .select_related("source")
    ):
        age_by_slug.setdefault(rev.source.slug, max(0, (ref - rev.created_at).days))

    out: list[EvidenceRow] = []
    for r in base_rows:
        entry = registry.get(r.slug)
        in_registry = entry is not None
        has_attachment = r.attachment_count > 0
        hash_present = r.hashed_attachment_count > 0
        has_version = r.version_count > 0
        pkg = packages.get(r.country, {})
        has_pkg = bool(pkg)
        approved_review = r.latest_review_decision == "approve"
        from apps.legal_sources.enums import SourceStatus

        is_approved = r.status == SourceStatus.APPROVED
        expected_pdf = bool(entry and entry.get("expected_format") == "pdf")

        out.append(
            EvidenceRow(
                country=r.country,
                slug=r.slug,
                title=r.title,
                status=r.status,
                in_registry=in_registry,
                has_source_version=has_version,
                has_attachment=has_attachment,
                attachment_hash_present=hash_present,
                has_review_package=has_pkg,
                review_package_path=pkg.get("path", ""),
                review_package_date=pkg.get("date", ""),
                review_package_fresh=bool(pkg.get("fresh", False)),
                latest_review_decision=r.latest_review_decision,
                latest_review_age_days=age_by_slug.get(r.slug),
                # conservative heuristic: a PDF candidate whose attachment is not
                # yet hash-validated may still need OCR/marker extraction.
                needs_ocr=expected_pdf and has_attachment and not hash_present,
                needs_attachment=not has_attachment,
                needs_hash_check=has_attachment and not hash_present,
                needs_legal_review=not approved_review,
                ready_for_studio_review=has_attachment and hash_present and not approved_review,
                ready_for_dataset_seed_review=is_approved and approved_review,
                calculation_ready=r.calculation_ready,
                never_calculation_ready_reason=_never_ready_reason(r.status, r.calculation_ready),
            )
        )
    return out


def candidates_missing_review_pack(rows: list[EvidenceRow]) -> list[str]:
    """Registry candidates still needing review whose country has no package."""
    return [
        r.slug for r in rows if r.in_registry and r.needs_legal_review and not r.has_review_package
    ]


def build_pack_index_report(country: str | None = None, *, today: str = "") -> dict[str, Any]:
    rows = build_evidence_checklist(country, today=today)
    summaries: dict[str, dict[str, int]] = {}
    for r in rows:
        cs = summaries.setdefault(
            r.country,
            {
                "total": 0,
                "candidates": 0,
                "with_attachment": 0,
                "with_hash": 0,
                "with_package": 0,
                "ready_for_studio_review": 0,
                "calculation_ready": 0,
            },
        )
        cs["total"] += 1
        cs["candidates"] += int(r.in_registry)
        cs["with_attachment"] += int(r.has_attachment)
        cs["with_hash"] += int(r.attachment_hash_present)
        cs["with_package"] += int(r.has_review_package)
        cs["ready_for_studio_review"] += int(r.ready_for_studio_review)
        cs["calculation_ready"] += int(r.calculation_ready)
    return {
        "rows": [r.__dict__ for r in rows],
        "summaries": dict(sorted(summaries.items())),
        "totals": {
            "sources": len(rows),
            "candidates": sum(1 for r in rows if r.in_registry),
            "calculation_ready": sum(1 for r in rows if r.calculation_ready),
            "ready_for_studio_review": sum(1 for r in rows if r.ready_for_studio_review),
        },
    }
