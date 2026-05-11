"""
Django system checks for ``apps.jurisdictions``.

Iter:
- F-p0-mvp-1-non-it-readiness (``jurisdictions.E001``):
  approved LegalSource rows must have a matching APPROVE
  LegalReview audit row.

The system as a whole already gates non-IT calculator output via a
12-step chain (LegalSource APPROVED + CompensationDataset APPROVED +
CalculationFormula APPROVED + calculator code guard). This check
tightens the **audit trail integrity** around the first link in that
chain — the LegalSource status — so a sloppy admin promotion path
("opened the LegalSource form, switched status to APPROVED, didn't
fill the LegalReview workflow, hit save") fails ``manage.py check``
in production.

Logic:
- active only in *production-like* scenarios (``DEBUG=False``);
- in dev (``DEBUG=True``) the check is silent (default-safe);
- queries the DB (read-only).

The check is opt-out-able via ``settings.JURISDICTIONS_REQUIRE_LEGAL_REVIEW_AUDIT_TRAIL``
defaulting to ``True``. The opt-out exists for the same reason as
``RETENTION_REQUIRE_SIGNED_VERSION``: staging environments may
legitimately run without a complete audit trail (e.g. a smoke
environment that re-seeds LegalSources from a fixture).
"""

from __future__ import annotations

from django.conf import settings
from django.core.checks import Error, register
from django.db.utils import OperationalError, ProgrammingError


@register("jurisdictions")
def check_approved_legal_sources_have_review_audit_trail(app_configs, **kwargs):
    """
    ``jurisdictions.E001`` — fail in production-like settings if any
    LegalSource is APPROVED without a matching APPROVE LegalReview
    audit row.

    The check is read-only and Django-style: zero writes, idempotent,
    no network. Safe to run on every ``manage.py check`` invocation.
    """
    if getattr(settings, "DEBUG", False):
        return []

    if not getattr(settings, "JURISDICTIONS_REQUIRE_LEGAL_REVIEW_AUDIT_TRAIL", True):
        return []

    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview, LegalSource

    try:
        approved = LegalSource.objects.filter(status=SourceStatus.APPROVED).only(
            "id", "slug", "legal_reviewer_id"
        )
        approved_count = approved.count()
    except (OperationalError, ProgrammingError):
        return []

    if approved_count == 0:
        return []

    issues: list[Error] = []
    approve_decision = LegalReview.Decision.APPROVE
    approved_ids = list(approved.values_list("id", flat=True))
    sources_with_audit = set(
        LegalReview.objects.filter(
            source_id__in=approved_ids, decision=approve_decision
        )
        .exclude(reviewer__isnull=True)
        .values_list("source_id", flat=True)
    )

    for src in approved.iterator():
        if src.id not in sources_with_audit:
            issues.append(
                Error(
                    f"LegalSource(slug={src.slug!r}, id={src.id}) is APPROVED "
                    "but has no matching LegalReview row with decision=APPROVE "
                    "and a non-null reviewer. The audit trail is incomplete: "
                    "in production, every approved legal source must be "
                    "traceable to a Studio reviewer + decision date.",
                    hint=(
                        "Either (a) record the LegalReview row (decision=approve, "
                        "reviewer=<user>, new_status=approved) via the admin, or "
                        "(b) demote the source back to NEEDS_REVIEW until the "
                        "Studio signs off. Do not deploy with this gap — the "
                        "calculator output would lack an audit trail."
                    ),
                    id="jurisdictions.E001",
                )
            )
        elif src.legal_reviewer_id is None:
            issues.append(
                Error(
                    f"LegalSource(slug={src.slug!r}, id={src.id}) is APPROVED "
                    "with a LegalReview audit row, but its legal_reviewer FK "
                    "is null. The source-level reviewer must be set so the "
                    "report / PDF can cite the responsible Studio reviewer.",
                    hint=(
                        "Set LegalSource.legal_reviewer to the user who signed "
                        "the APPROVE LegalReview row."
                    ),
                    id="jurisdictions.E001",
                )
            )

    return issues
