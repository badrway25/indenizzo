"""H1-5 follow-up: APPROVED compensation datasets require a source version.

Enforcement is application-level (CompensationDataset.clean()), so it fires on
admin/form saves (full_clean()) — the real path by which a dataset is promoted
to APPROVED — but NOT on bare .create() (which is why ~65 synthetic-data test
fixtures keep working). The DB-level CheckConstraint for this rule is a planned
follow-up (see migration 0005 docstring), gated on updating those fixtures.

The data migration 0005 backfills the real IT approved datasets so they already
satisfy this rule.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.core.exceptions import ValidationError

from apps.calculators.enums import CaseType
from apps.compensation.models import CompensationDataset, DatasetStatus
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource, LegalSourceVersion

ROAD = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value


@pytest.fixture
def approved_source(db) -> LegalSource:
    country = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    lang = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=country,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return LegalSource.objects.create(
        slug="it-asv-test",
        title="Test approved source",
        country=country,
        jurisdiction=juris,
        language=lang,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
        effective_date=date(2025, 1, 1),
    )


def _ds(src, **kw) -> CompensationDataset:
    base = dict(
        source=src,
        jurisdiction=src.jurisdiction,
        country=src.country,
        case_type=ROAD,
        name="DS",
    )
    base.update(kw)
    return CompensationDataset(**base)


@pytest.mark.django_db
def test_approved_without_source_version_rejected_by_clean(approved_source):
    ds = _ds(approved_source, status=DatasetStatus.APPROVED, source_version=None)
    with pytest.raises(ValidationError) as exc:
        ds.full_clean()
    assert "source_version" in exc.value.message_dict


@pytest.mark.django_db
def test_draft_without_source_version_accepted(approved_source):
    # draft / needs_review / deprecated may stay without a version.
    _ds(approved_source, status=DatasetStatus.DRAFT, source_version=None).full_clean()
    _ds(approved_source, status=DatasetStatus.NEEDS_REVIEW, source_version=None).full_clean()


@pytest.mark.django_db
def test_approved_with_matching_source_version_accepted(approved_source):
    version = LegalSourceVersion.objects.create(source=approved_source, version_label="v1")
    ds = _ds(approved_source, status=DatasetStatus.APPROVED, source_version=version)
    ds.full_clean()  # must not raise
    ds.save()
    assert ds.source_version_id == version.id


@pytest.mark.django_db
def test_approved_with_cross_source_version_rejected(approved_source):
    other_country = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    other_juris = Jurisdiction.objects.create(
        country=other_country,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    other_src = LegalSource.objects.create(
        slug="fr-asv-test",
        title="FR source",
        country=other_country,
        jurisdiction=other_juris,
        language=approved_source.language,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
    )
    cross_version = LegalSourceVersion.objects.create(source=other_src, version_label="vX")
    ds = _ds(approved_source, status=DatasetStatus.APPROVED, source_version=cross_version)
    with pytest.raises(ValidationError) as exc:
        ds.full_clean()
    assert "source_version" in exc.value.message_dict


@pytest.mark.django_db
def test_source_version_fk_is_protected(approved_source):
    """Deleting a LegalSourceVersion still referenced by a dataset is blocked."""
    from django.db.models import ProtectedError

    version = LegalSourceVersion.objects.create(source=approved_source, version_label="v1")
    ds = _ds(approved_source, status=DatasetStatus.DRAFT, source_version=version)
    ds.save()
    with pytest.raises(ProtectedError):
        version.delete()
