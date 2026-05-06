"""F-legal-sources-approved-status-promotion-pass1.

Promote a fixed allow-list of official ``LegalSource`` rows to
``status=APPROVED``. Each promotion is gated on three independent
checks:

1. The reviewer named via ``--reviewer-username`` must already
   exist in the user table and be ``is_staff=True``. Fake or
   missing reviewers fail loudly — the command never creates a
   user.
2. The source slug must be in ``PROMOTABLE_SLUGS``. Sources outside
   this allow-list (Mornet, Gazette du Palais, Tableau Indicatif,
   Schryvers, Dintilhac, etc.) are refused even if a future block
   were spoofed in their notes.
3. The source must carry a passing
   ``[official_source_validation]`` block (i.e. the iter that
   validated the file integrity must already have run with
   ``--commit``).

When all three pass, the command:

* creates a real ``LegalReview`` row with
  ``decision=approve`` and ``new_status=approved``;
* sets ``LegalSource.status = APPROVED`` and
  ``LegalSource.legal_reviewer = <user>``.

It NEVER creates ``CompensationDataset``, ``CalculationFormula``,
``CompensationTableRow`` rows, NEVER promotes a draft dataset,
NEVER activates the FR / BE / MA / TN public calculators.

Idempotent: a second run with the same reviewer simply records
that the source is already approved and skips creating a duplicate
review row.

CLI::

    # Default: dry-run (prints the plan, does not write).
    python manage.py promote_official_legal_sources --reviewer-username badr

    # Persist:
    python manage.py promote_official_legal_sources --reviewer-username badr --commit

    # Restrict to a single slug:
    python manage.py promote_official_legal_sources \
        --reviewer-username badr --commit \
        --slug fr-loi-badinter-1985
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.legal_sources.enums import SourceStatus
from apps.legal_sources.models import LegalReview, LegalSource

VALIDATION_BEGIN = "[official_source_validation] BEGIN"
VALIDATION_END = "[official_source_validation] END"

# Allow-list of slugs eligible for promotion. The IT decree is
# already approved and is included here so a future re-run is a
# safe no-op for it as well.
PROMOTABLE_SLUGS: tuple[str, ...] = (
    "it-dpr-12-2025-tun-danno-biologico",
    "eu-regulation-650-2012-successions",
    "ma-code-famille-moudawana-fr-pdf",
    "tn-code-statut-personnel-livre-ix-succession",
    "tn-code-dip-loi-98-97",
    "be-loi-1989-11-21-rc-auto",
    "fr-loi-badinter-1985",
)

# Slugs that MUST NEVER be promoted by this command — they are
# private barèmes / court-indicative tables / mirror copies.
DENY_LIST_SLUGS: tuple[str, ...] = (
    "fr-referentiel-mornet-2024",
    "fr-bareme-capitalisation-gazette-palais-2022",
    "fr-bareme-capitalisation-gazette-palais-2025-page",
    "fr-nomenclature-dintilhac-2005",
    "be-tableau-indicatif-2020",
    "be-tableau-indicatif-2024",
    "be-tables-schryvers-2026-page",
    "be-tables-schryvers-tableurs",
)


@dataclass
class PromotionResult:
    slug: str
    decision: str = "skip"
    previous_status: str = ""
    new_status: str = ""
    review_created: bool = False
    legal_reviewer_set: bool = False
    reason: str = ""
    blocking_reasons: list[str] = field(default_factory=list)


def _extract_validation_block(notes: str) -> dict | None:
    if VALIDATION_BEGIN not in notes:
        return None
    body = notes.split(VALIDATION_BEGIN, 1)[1].split(VALIDATION_END, 1)[0].strip()
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _evaluate(src: LegalSource) -> PromotionResult:
    """Return a planned action without writing anything."""
    result = PromotionResult(slug=src.slug, previous_status=src.status)

    if src.slug in DENY_LIST_SLUGS:
        result.blocking_reasons.append("slug_in_deny_list")
        result.reason = (
            "deny-listed slug — private barème / court-indicative table / "
            "mirror copy; never eligible for promotion"
        )
        return result

    if src.slug not in PROMOTABLE_SLUGS:
        result.blocking_reasons.append("slug_not_in_allow_list")
        result.reason = "slug not in PROMOTABLE_SLUGS"
        return result

    if src.status == SourceStatus.APPROVED:
        result.decision = "already_approved"
        result.new_status = src.status
        result.reason = "source already approved; nothing to do"
        return result

    validation = _extract_validation_block(src.notes or "")
    if not validation:
        result.blocking_reasons.append("no_official_source_validation_block")
        result.reason = (
            "no [official_source_validation] block; run "
            "`validate_official_legal_sources --commit` first"
        )
        return result

    if validation.get("validation_status") != "passed":
        result.blocking_reasons.append(f"validation_status={validation.get('validation_status')!r}")
        result.reason = "validation block does not record validation_status=passed"
        return result

    if not validation.get("official_source_verified"):
        result.blocking_reasons.append("official_source_verified_false")
        result.reason = "validation block does not assert official_source_verified=true"
        return result

    if not validation.get("sha256_verified"):
        result.blocking_reasons.append("sha256_verified_false")
        result.reason = "validation block does not assert sha256_verified=true"
        return result

    result.decision = "promote"
    result.new_status = str(SourceStatus.APPROVED)
    result.reason = "eligible: official source verified + sha256 verified"
    return result


def _resolve_reviewer(username: str):
    User = get_user_model()
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist as exc:  # noqa: PERF203
        raise CommandError(
            f"--reviewer-username {username!r} does not exist; this command "
            f"never creates users. Pass an existing staff username."
        ) from exc
    if not user.is_staff:
        raise CommandError(
            f"--reviewer-username {username!r} is not a staff user; promotion "
            f"requires is_staff=True so the LegalReview row is auditable."
        )
    if not user.is_active:
        raise CommandError(f"--reviewer-username {username!r} is not active.")
    return user


class Command(BaseCommand):
    help = (
        "Promote validated official LegalSource rows to status=APPROVED "
        "by creating a real LegalReview decision row attached to an "
        "existing staff reviewer."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--reviewer-username",
            required=True,
            help="Username of the existing staff user that signs the "
            "LegalReview rows. The command fails if the user does not "
            "exist or is not is_staff.",
        )
        parser.add_argument(
            "--commit",
            action="store_true",
            default=False,
            help="Persist the promotion (LegalReview + LegalSource.status). "
            "Without this flag the command only prints the plan.",
        )
        parser.add_argument(
            "--slug",
            default=None,
            help="Restrict the run to a single LegalSource slug.",
        )
        parser.add_argument(
            "--comment",
            default=(
                "F-legal-sources-approved-status-promotion-pass1: official "
                "source provenance verified, file sha256 + registry markers "
                "checked. No calculator activation."
            ),
            help="Comment to store on the LegalReview row.",
        )

    def handle(self, *args, **options):
        reviewer = _resolve_reviewer(options["reviewer_username"])
        commit = bool(options.get("commit"))
        slug_filter = options.get("slug")
        comment = options.get("comment") or ""

        qs = LegalSource.objects.select_related("country").order_by("country__code", "slug")
        if slug_filter:
            qs = qs.filter(slug=slug_filter)

        results: list[PromotionResult] = []
        promote_count = 0
        already_count = 0
        skip_count = 0

        for src in qs:
            plan = _evaluate(src)
            results.append(plan)

            if plan.decision == "promote":
                promote_count += 1
                if commit:
                    with transaction.atomic():
                        # Re-fetch under the lock to avoid races.
                        fresh = LegalSource.objects.select_for_update().get(pk=src.pk)
                        previous = fresh.status
                        LegalReview.objects.create(
                            source=fresh,
                            reviewer=reviewer,
                            decision=LegalReview.Decision.APPROVE,
                            previous_status=previous,
                            new_status=SourceStatus.APPROVED,
                            comment=comment,
                        )
                        fresh.status = SourceStatus.APPROVED
                        fresh.legal_reviewer = reviewer
                        fresh.save(update_fields=["status", "legal_reviewer", "updated_at"])
                    plan.review_created = True
                    plan.legal_reviewer_set = True
                    plan.previous_status = previous
                    plan.new_status = str(SourceStatus.APPROVED)
            elif plan.decision == "already_approved":
                already_count += 1
            else:
                skip_count += 1

            tag = f"{plan.decision:>17}"
            self.stdout.write(
                f"[{tag}] {src.slug}  prev={plan.previous_status!r}  "
                f"new={plan.new_status!r}  reason={plan.reason}"
            )

        self.stdout.write("")
        self.stdout.write(
            f"[summary] reviewer={reviewer.username}  commit={commit}  "
            f"promote={promote_count}  already_approved={already_count}  "
            f"skipped={skip_count}  total={len(results)}"
        )
        if not commit:
            self.stdout.write(
                "[note] dry-run: no LegalReview row was created and no "
                "LegalSource.status was changed. Re-run with --commit "
                "to persist."
            )
