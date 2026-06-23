"""D2: tests for the read-only evidence checklist + review-pack index.

Asserts the evidence booleans, the review-package index + freshness, PII-safety,
read-only/no-promotion behaviour, and that FR/BE/MA/TN stay not calculation-ready.
"""

from __future__ import annotations

from datetime import date
from io import StringIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import (
    LegalReview,
    LegalSource,
    LegalSourceAttachment,
)
from apps.legal_sources.review_evidence import (
    build_evidence_checklist,
    review_package_index,
)


def _source(slug, country_code="FR", *, status=SourceStatus.NEEDS_REVIEW):
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


def _attach(src):
    # save() auto-computes sha256 from the file (integrity proof).
    return LegalSourceAttachment.objects.create(
        source=src,
        file=SimpleUploadedFile(f"{src.slug}.pdf", b"%PDF-1.4 test"),
        original_filename=f"{src.slug}.pdf",
        mime_type="application/pdf",
        size_bytes=12,
    )


def _row(slug, country="FR"):
    return next(r for r in build_evidence_checklist(country) if r.slug == slug)


# --------------------------------------------------------------------------- #
# evidence booleans
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_source_without_attachment_needs_attachment():
    _source("fr-noatt", "FR")
    r = _row("fr-noatt")
    assert r.needs_attachment is True
    assert r.has_attachment is False
    assert r.attachment_hash_present is False
    assert r.ready_for_studio_review is False


@pytest.mark.django_db
def test_attachment_without_hash_needs_hash_check():
    # The model auto-hashes on save(); force the (rare) unhashed state via
    # .update() to exercise the evidence logic deterministically.
    src = _source("fr-nohash", "FR")
    att = _attach(src)
    LegalSourceAttachment.objects.filter(pk=att.pk).update(sha256="")
    r = _row("fr-nohash")
    assert r.has_attachment is True
    assert r.attachment_hash_present is False
    assert r.needs_hash_check is True


@pytest.mark.django_db
def test_attachment_with_hash_is_ready_for_studio_review():
    src = _source("fr-hash", "FR")
    _attach(src)
    r = _row("fr-hash")
    assert r.attachment_hash_present is True
    assert r.needs_hash_check is False
    # hash present + no approve review yet -> evidence ready for a legal review
    assert r.ready_for_studio_review is True
    assert r.never_calculation_ready_reason  # not empty: still not calc-ready


# --------------------------------------------------------------------------- #
# review-package index + freshness
# --------------------------------------------------------------------------- #


def test_review_package_index_parses_generated_files():
    # The committed FR/BE/MA/TN packages should be discovered.
    idx = review_package_index(today="2026-06-23")
    assert "FR" in idx and idx["FR"]["path"].endswith(".md")
    # a package dated 2026-06-22 is fresh relative to 2026-06-23
    assert idx["FR"]["fresh"] is True
    # and stale relative to a much later date
    idx_old = review_package_index(today="2030-01-01")
    assert idx_old["FR"]["fresh"] is False


@pytest.mark.django_db
def test_country_with_generated_package_has_review_package():
    _source("fr-pkg", "FR")
    assert _row("fr-pkg").has_review_package is True


# --------------------------------------------------------------------------- #
# fail-closed: FR/BE/MA/TN never calculation-ready
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
@pytest.mark.parametrize("cc", ["FR", "BE", "MA", "TN"])
def test_non_italian_never_calculation_ready(cc):
    _source(f"{cc.lower()}-ev", cc, status=SourceStatus.APPROVED)
    rows = build_evidence_checklist(cc)
    assert all(r.calculation_ready is False for r in rows)
    assert all(r.never_calculation_ready_reason for r in rows)


# --------------------------------------------------------------------------- #
# command: read-only, PII-safe, coherent formats, no promotion
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_command_is_read_only_and_pii_safe():
    src = _source("fr-cmd", "FR")
    _attach(src)
    before = (
        LegalSource.objects.count(),
        LegalReview.objects.count(),
        LegalSourceAttachment.objects.count(),
    )
    out = StringIO()
    call_command("report_legal_review_pack_index", "--format", "json", stdout=out)
    after = (
        LegalSource.objects.count(),
        LegalReview.objects.count(),
        LegalSourceAttachment.objects.count(),
    )
    assert before == after  # no DB writes
    assert "@" not in out.getvalue()  # PII-safe


@pytest.mark.django_db
def test_command_json_and_markdown_are_coherent():
    import json

    _source("fr-fmt", "FR")
    j = StringIO()
    call_command("report_legal_review_pack_index", "--country", "FR", "--format", "json", stdout=j)
    data = json.loads(j.getvalue())
    assert "rows" in data and "totals" in data
    m = StringIO()
    call_command(
        "report_legal_review_pack_index", "--country", "FR", "--format", "markdown", stdout=m
    )
    assert "| Country |" in m.getvalue()  # markdown table header


@pytest.mark.django_db
def test_command_does_not_promote_or_activate():
    from apps.calculators.enums import CalculationStatus
    from apps.calculators.registry import get_calculator

    src = _source("fr-noact", "FR", status=SourceStatus.NEEDS_REVIEW)
    call_command("report_legal_review_pack_index", "--country", "FR", stdout=StringIO())
    src.refresh_from_db()
    assert src.status == SourceStatus.NEEDS_REVIEW  # status unchanged
    calc_cls = get_calculator("FR-NATIONAL", "road_accident_bodily_injury")
    if calc_cls is not None:
        result = calc_cls().compute(
            {"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0}
        )
        status = getattr(result.status, "value", result.status)
        assert status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
