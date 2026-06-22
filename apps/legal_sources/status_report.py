"""Read-only consolidation of legal-source status for Studio review.

Pure, side-effect-free functions that summarise the current state of every
``LegalSource`` and whether it is *calculation-ready* (i.e. it backs at least
one APPROVED ``CompensationDataset``). No DB writes, no network, no PII.

The cardinal distinction this module makes explicit, in line with the project
architecture ("meglio nessun calcolo che un calcolo falso"):

- ``status == approved`` means the source DOCUMENT was authenticated
  (downloaded, hashed, marker-checked, signed off). It does NOT mean a public
  calculation is active.
- ``calculation_ready`` is true only when the source backs an APPROVED
  ``CompensationDataset``. Today that is a single Italian source.

Used by the ``report_legal_source_status`` management command and its tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class SourceStatusRow:
    country: str
    slug: str
    title: str
    source_type: str
    status: str
    reliability: str
    official_url: str
    publication_date: str
    effective_date: str
    valid_until: str
    last_checked_at: str
    version_count: int
    attachment_count: int
    hashed_attachment_count: int
    calculation_ready: bool
    requires_legal_review: bool


@dataclass
class CountrySummary:
    country: str
    total: int = 0
    by_status: dict[str, int] = field(default_factory=dict)
    approved_sources: int = 0
    calculation_ready: int = 0
    requires_legal_review: int = 0


def _fmt_date(value: Any) -> str:
    return value.isoformat() if value else ""


def _calculation_ready_slugs() -> set[str]:
    """Slugs of sources that back at least one APPROVED CompensationDataset."""
    from apps.compensation.models import CompensationDataset, DatasetStatus

    return set(
        CompensationDataset.objects.filter(status=DatasetStatus.APPROVED).values_list(
            "source__slug", flat=True
        )
    )


def build_rows(country: str | None = None) -> list[SourceStatusRow]:
    """Return one row per LegalSource (optionally filtered by country code)."""
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalSource

    calc_ready = _calculation_ready_slugs()

    qs = (
        LegalSource.objects.select_related("country")
        .prefetch_related("versions", "attachments")
        .order_by("country__code", "slug")
    )
    if country:
        qs = qs.filter(country__code=country.upper())

    rows: list[SourceStatusRow] = []
    for s in qs:
        attachments = list(s.attachments.all())
        is_ready = s.slug in calc_ready
        # "requires legal review" = not yet a trustworthy approved source.
        # Approved sources are considered reviewed; everything else needs the
        # Studio's eyes before it could ever feed a calculation.
        requires_review = s.status != SourceStatus.APPROVED
        rows.append(
            SourceStatusRow(
                country=s.country.code if s.country_id else "??",
                slug=s.slug,
                title=s.title,
                source_type=s.source_type,
                status=s.status,
                reliability=s.reliability,
                official_url=s.official_url or "",
                publication_date=_fmt_date(s.publication_date),
                effective_date=_fmt_date(s.effective_date),
                valid_until=_fmt_date(s.valid_until),
                last_checked_at=_fmt_date(s.last_checked_at),
                version_count=s.versions.count(),
                attachment_count=len(attachments),
                hashed_attachment_count=sum(1 for a in attachments if a.sha256),
                calculation_ready=is_ready,
                requires_legal_review=requires_review,
            )
        )
    return rows


def summarise(rows: list[SourceStatusRow]) -> dict[str, CountrySummary]:
    """Per-country roll-up of the rows."""
    from apps.legal_sources.enums import SourceStatus

    out: dict[str, CountrySummary] = {}
    for r in rows:
        cs = out.setdefault(r.country, CountrySummary(country=r.country))
        cs.total += 1
        cs.by_status[r.status] = cs.by_status.get(r.status, 0) + 1
        if r.status == SourceStatus.APPROVED:
            cs.approved_sources += 1
        if r.calculation_ready:
            cs.calculation_ready += 1
        if r.requires_legal_review:
            cs.requires_legal_review += 1
    return out


def build_report(country: str | None = None) -> dict[str, Any]:
    """Full structured report: rows + per-country summaries + global totals."""
    rows = build_rows(country)
    summaries = summarise(rows)
    return {
        "rows": [row.__dict__ for row in rows],
        "summaries": {c: cs.__dict__ for c, cs in sorted(summaries.items())},
        "totals": {
            "sources": len(rows),
            "calculation_ready": sum(1 for r in rows if r.calculation_ready),
            "approved_sources": sum(1 for r in rows if not r.requires_legal_review),
            "requires_legal_review": sum(1 for r in rows if r.requires_legal_review),
        },
    }
