"""Tests for generate_legal_review_package + review_package builder.

Verify the package merges DB state with the registry policy, scaffolds the
Studio decisions WITHOUT auto-approving anything, filters by country, emits
valid JSON/markdown, errors on an unknown country, and never writes the DB.
"""

from __future__ import annotations

import io
import json
from datetime import date

import pytest
from django.core.management import CommandError, call_command

from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource
from apps.legal_sources.review_package import build_review_package


@pytest.fixture
def fr_sources(db):
    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    lang = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    # In the official registry (slug present in config/official_source_registry.json).
    LegalSource.objects.create(
        slug="fr-loi-badinter-1985",
        title="Loi Badinter",
        country=france,
        jurisdiction=juris,
        language=lang,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(1985, 7, 5),
    )
    # NOT in the registry.
    LegalSource.objects.create(
        slug="fr-not-in-registry-xyz",
        title="Some FR table",
        country=france,
        jurisdiction=juris,
        language=lang,
        source_type=SourceType.COURT_TABLE,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2024, 1, 1),
    )
    return france


@pytest.mark.django_db
def test_package_structure_and_counts(fr_sources):
    pkg = build_review_package("FR")
    assert pkg["country"] == "FR"
    assert pkg["total_sources"] == 2
    assert pkg["needs_review_count"] == 2
    assert pkg["calculation_ready"] == 0


@pytest.mark.django_db
def test_registry_overlay_applied(fr_sources):
    pkg = build_review_package("FR")
    by_slug = {i["slug"]: i for i in pkg["items"]}
    # Badinter is in the registry and is manual-attach.
    assert by_slug["fr-loi-badinter-1985"]["registry"]["in_registry"] is True
    assert by_slug["fr-loi-badinter-1985"]["registry"]["manual_attach_allowed"] is True
    # The unknown slug is not in the registry.
    assert by_slug["fr-not-in-registry-xyz"]["registry"]["in_registry"] is False


@pytest.mark.django_db
def test_decisions_default_to_pending_never_autoapprove(fr_sources):
    pkg = build_review_package("FR")
    for i in pkg["items"]:
        assert i["decisions"]["verdict"] == "pending"
        assert i["decisions"]["document_authentic"] is None


@pytest.mark.django_db
def test_command_markdown_has_checklist_and_cardinal_rule(fr_sources):
    buf = io.StringIO()
    call_command("generate_legal_review_package", "--country", "FR", stdout=buf)
    out = buf.getvalue()
    assert "Studio decisions to record" in out
    assert "Meglio nessun calcolo che un calcolo falso" in out
    assert "MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md" in out  # cross-reference


@pytest.mark.django_db
def test_command_json_is_valid(fr_sources):
    buf = io.StringIO()
    call_command("generate_legal_review_package", "--country", "FR", "--format", "json", stdout=buf)
    data = json.loads(buf.getvalue())
    assert data["country"] == "FR"
    assert len(data["items"]) == 2


@pytest.mark.django_db
def test_command_writes_output_file(fr_sources, tmp_path):
    target = tmp_path / "fr_pkg.md"
    call_command(
        "generate_legal_review_package",
        "--country",
        "FR",
        "--output",
        str(target),
        stdout=io.StringIO(),
    )
    assert target.is_file()
    assert "Legal review package" in target.read_text(encoding="utf-8")


@pytest.mark.django_db
def test_command_errors_on_unknown_country(db):
    with pytest.raises(CommandError):
        call_command("generate_legal_review_package", "--country", "ZZ", stdout=io.StringIO())


@pytest.mark.django_db
def test_command_is_read_only(fr_sources):
    before = LegalSource.objects.count()
    call_command("generate_legal_review_package", "--country", "FR", stdout=io.StringIO())
    assert LegalSource.objects.count() == before
