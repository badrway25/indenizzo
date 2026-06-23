"""D1: tests for the read-only legal-source review-readiness workflow.

Asserts the workflow NEVER promotes/activates, the latest-review logic, the
missing-steps + fail-closed invariants, PII-safety, and that FR/BE/MA/TN stay
not calculation-ready.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.calculators.enums import CaseType
from apps.compensation.models import CompensationDataset, CompensationTableRow, DatasetStatus
from apps.compensation.test_fixtures import approved_source_version
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalReview, LegalSource
from apps.legal_sources.review_readiness import (
    build_readiness_rows,
    calculation_ready_without_approve_review,
)

ROAD = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value


def _source(slug, country_code, *, status=SourceStatus.NEEDS_REVIEW):
    country, _ = Country.objects.get_or_create(
        code=country_code, defaults={"code_alpha3": country_code + "X", "name": country_code}
    )
    lang, _ = Language.objects.get_or_create(code="it", defaults={"name": "Italiano"})
    juris, _ = Jurisdiction.objects.get_or_create(
        country=country,
        code=f"{country_code}-NATIONAL",
        defaults={"name": country_code, "legal_system": Jurisdiction.LegalSystem.CIVIL_LAW},
    )
    return LegalSource.objects.create(
        slug=slug,
        title=f"Source {slug}",
        country=country,
        jurisdiction=juris,
        language=lang,
        source_type=SourceType.MINISTRY_DECREE,
        status=status,
        publication_date=date(2025, 1, 1),
        effective_date=date(2025, 1, 1),
    )


def _make_calc_ready_source(slug="it-calc-src"):
    """An APPROVED source backing an APPROVED dataset (with source_version)."""
    src = _source(slug, "IT", status=SourceStatus.APPROVED)
    version = approved_source_version(src)
    ds = CompensationDataset.objects.create(
        source=src,
        source_version=version,
        jurisdiction=src.jurisdiction,
        country=src.country,
        case_type=ROAD,
        name="DS",
        status=DatasetStatus.APPROVED,
    )
    CompensationTableRow.objects.create(
        dataset=ds, age_min=35, age_max=35, point_value=Decimal("1")
    )
    return src


def _reviewer():
    return get_user_model().objects.create_user("d1_reviewer", "r@x.it", "x", is_staff=True)


# --------------------------------------------------------------------------- #
# latest_review + missing steps
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_latest_review_returns_most_recent():
    src = _source("fr-x", "FR")
    user = _reviewer()
    LegalReview.objects.create(source=src, reviewer=user, decision="request_changes")
    approve = LegalReview.objects.create(source=src, reviewer=user, decision="approve")
    assert src.latest_review.pk == approve.pk  # ordered -created_at


@pytest.mark.django_db
def test_fresh_source_missing_steps_start_with_attachment():
    _source("fr-fresh", "FR")
    rows = {r.slug: r for r in build_readiness_rows("FR")}
    row = rows["fr-fresh"]
    assert row.calculation_ready is False
    assert row.recommended_next_action == "attach the official source file"
    assert "obtain a Studio legal review (approve)" in row.missing_steps


# --------------------------------------------------------------------------- #
# fail-closed: FR/BE/MA/TN never calculation-ready
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
@pytest.mark.parametrize("cc", ["FR", "BE", "MA", "TN"])
def test_non_italian_sources_never_calculation_ready(cc):
    _source(f"{cc.lower()}-src", cc, status=SourceStatus.APPROVED)
    rows = build_readiness_rows(cc)
    assert all(r.calculation_ready is False for r in rows)


# --------------------------------------------------------------------------- #
# guard: calculation-ready requires an approve review
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_calc_ready_without_review_is_flagged_then_cleared():
    src = _make_calc_ready_source()
    rows = build_readiness_rows()
    # calc-ready but NO review yet -> flagged
    assert src.slug in calculation_ready_without_approve_review(rows)
    # record an approve review -> no longer flagged
    LegalReview.objects.create(source=src, reviewer=_reviewer(), decision="approve")
    rows2 = build_readiness_rows()
    assert calculation_ready_without_approve_review(rows2) == []


@pytest.mark.django_db
def test_command_fail_guard_raises_on_calc_ready_without_review():
    _make_calc_ready_source()  # calc-ready, no approve review
    with pytest.raises(CommandError):
        call_command(
            "report_legal_review_readiness",
            "--fail-if-calculation-ready-without-review",
            stdout=StringIO(),
        )


@pytest.mark.django_db
def test_command_guards_pass_when_clean():
    src = _make_calc_ready_source()
    LegalReview.objects.create(source=src, reviewer=_reviewer(), decision="approve")
    out = StringIO()
    # must NOT raise: calc-ready source has an approve review; H1-9 keeps datasets sound
    call_command(
        "report_legal_review_readiness",
        "--fail-if-calculation-ready-without-review",
        "--fail-if-approved-without-source-version",
        stdout=out,
    )


# --------------------------------------------------------------------------- #
# read-only + PII-safe + does not activate calculators
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_command_is_read_only_and_pii_safe():
    _source("fr-ro", "FR")
    reviews_before = LegalReview.objects.count()
    sources_before = LegalSource.objects.count()
    datasets_before = CompensationDataset.objects.count()
    out = StringIO()
    call_command("report_legal_review_readiness", "--format", "json", stdout=out)
    assert LegalReview.objects.count() == reviews_before
    assert LegalSource.objects.count() == sources_before
    assert CompensationDataset.objects.count() == datasets_before
    body = out.getvalue()
    assert "@" not in body  # no emails / PII


@pytest.mark.django_db
def test_report_does_not_activate_non_italian_calculator():
    """Running the readiness report must not make FR produce a calculation.

    France has a registered *placeholder* engine that stays fail-closed: with no
    APPROVED dataset it returns UNAVAILABLE_REQUIRES_LEGAL_VALIDATION, never a
    number. The readiness report (read-only) must not change that.
    """
    from apps.calculators.enums import CalculationStatus
    from apps.calculators.registry import get_calculator

    _source("fr-engine", "FR", status=SourceStatus.APPROVED)
    datasets_before = CompensationDataset.objects.filter(country__code="FR").count()
    call_command("report_legal_review_readiness", "--country", "FR", stdout=StringIO())
    # the report created no FR dataset -> FR cannot be calculation-ready
    assert CompensationDataset.objects.filter(country__code="FR").count() == datasets_before
    # and the FR placeholder engine still refuses to compute a number
    calc_cls = get_calculator("FR-NATIONAL", ROAD)
    if calc_cls is not None:
        result = calc_cls().compute(
            {"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0}
        )
        status = getattr(result.status, "value", result.status)
        assert status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
