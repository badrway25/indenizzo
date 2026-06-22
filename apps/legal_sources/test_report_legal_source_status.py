"""Tests for the read-only report_legal_source_status command + status_report.

Verify the report distinguishes an authenticated (approved) source from a
calculation-ready one (backs an APPROVED dataset), filters by country, emits
valid JSON, writes a file, and never mutates the DB.
"""

from __future__ import annotations

import io
import json
from datetime import date

import pytest
from django.core.management import call_command

from apps.calculators.enums import CaseType
from apps.compensation.models import CompensationDataset, DatasetStatus
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource, LegalSourceVersion
from apps.legal_sources.status_report import build_report


@pytest.fixture
def stack(db):
    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    lang = Language.objects.create(code="it", name="Italiano")
    it_juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    fr_juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    # Approved IT source that backs an APPROVED dataset -> calculation-ready.
    it_src = LegalSource.objects.create(
        slug="it-report-test",
        title="IT decree",
        country=italy,
        jurisdiction=it_juris,
        language=lang,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
        effective_date=date(2025, 1, 1),
    )
    version = LegalSourceVersion.objects.create(source=it_src, version_label="v1")
    CompensationDataset.objects.create(
        source=it_src,
        source_version=version,
        jurisdiction=it_juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="DS",
        status=DatasetStatus.APPROVED,
    )
    # Approved FR source but NO approved dataset -> authenticated, NOT calc-ready.
    LegalSource.objects.create(
        slug="fr-report-approved-no-dataset",
        title="FR law",
        country=france,
        jurisdiction=fr_juris,
        language=lang,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        publication_date=date(2020, 1, 1),
    )
    # FR needs_review source.
    LegalSource.objects.create(
        slug="fr-report-needs-review",
        title="FR table",
        country=france,
        jurisdiction=fr_juris,
        language=lang,
        source_type=SourceType.COURT_TABLE,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2024, 1, 1),
    )
    return {"italy": italy, "france": france}


@pytest.mark.django_db
def test_report_totals_and_calculation_ready(stack):
    report = build_report()
    assert report["totals"]["sources"] == 3
    assert report["totals"]["approved_sources"] == 2  # IT + FR approved
    assert report["totals"]["calculation_ready"] == 1  # only IT (backs a dataset)
    assert report["totals"]["requires_legal_review"] == 1  # the FR needs_review

    by_slug = {r["slug"]: r for r in report["rows"]}
    assert by_slug["it-report-test"]["calculation_ready"] is True
    # Approved but no dataset: authenticated, NOT calculation-ready.
    assert by_slug["fr-report-approved-no-dataset"]["calculation_ready"] is False
    assert by_slug["fr-report-approved-no-dataset"]["requires_legal_review"] is False
    assert by_slug["fr-report-needs-review"]["requires_legal_review"] is True


@pytest.mark.django_db
def test_country_filter(stack):
    report = build_report(country="IT")
    assert {r["country"] for r in report["rows"]} == {"IT"}
    assert report["totals"]["sources"] == 1


@pytest.mark.django_db
def test_command_json_is_valid(stack):
    buf = io.StringIO()
    call_command("report_legal_source_status", "--format", "json", stdout=buf)
    data = json.loads(buf.getvalue())
    assert set(data.keys()) == {"rows", "summaries", "totals"}
    assert data["totals"]["calculation_ready"] == 1


@pytest.mark.django_db
def test_command_text_marks_calc_ready(stack):
    buf = io.StringIO()
    call_command("report_legal_source_status", stdout=buf)
    out = buf.getvalue()
    assert "it-report-test" in out
    assert "CALC-READY" in out


@pytest.mark.django_db
def test_command_writes_output_file(stack, tmp_path):
    target = tmp_path / "report.md"
    buf = io.StringIO()
    call_command(
        "report_legal_source_status",
        "--format",
        "markdown",
        "--output",
        str(target),
        stdout=buf,
    )
    assert target.is_file()
    content = target.read_text(encoding="utf-8")
    assert "# Legal Source Status" in content
    assert "| Country | Total |" in content


@pytest.mark.django_db
def test_command_is_read_only(stack):
    before = (LegalSource.objects.count(), CompensationDataset.objects.count())
    call_command("report_legal_source_status", stdout=io.StringIO())
    after = (LegalSource.objects.count(), CompensationDataset.objects.count())
    assert before == after
