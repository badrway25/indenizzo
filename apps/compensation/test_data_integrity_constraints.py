"""H1-5: DB-level integrity constraints on legal / compensation data.

These constraints backstop the ``clean()``-only invariants at the database
layer, so non-ORM paths (bulk_create/update, raw SQL, fixtures, shell saves
without ``full_clean()``) cannot insert inverted date ranges, inverted
age/disability bands, or cross-source provenance.

Pre-audit confirmed the existing 41k+ rows are all compatible; these tests
prove the constraints REJECT invalid data and ACCEPT valid data — including
open-ended validity (NULL end), which is legitimate ("still valid").
"""

from __future__ import annotations

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.calculators.enums import CaseType
from apps.compensation.models import (
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
)
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource, LegalSourceVersion

ROAD = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value


@pytest.fixture
def source(db) -> LegalSource:
    country = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    lang = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=country,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return LegalSource.objects.create(
        slug="it-h15-test",
        title="Test source",
        country=country,
        jurisdiction=juris,
        language=lang,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
    )


@pytest.fixture
def dataset(source) -> CompensationDataset:
    return CompensationDataset.objects.create(
        source=source,
        jurisdiction=source.jurisdiction,
        country=source.country,
        case_type=ROAD,
        name="DS",
        status=DatasetStatus.DRAFT,
    )


def _ds(source, **kw):
    base = dict(
        source=source,
        jurisdiction=source.jurisdiction,
        country=source.country,
        case_type=ROAD,
        name="DS",
    )
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# CompensationDataset — validity dates
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dataset_db_rejects_inverted_validity(source):
    # .create() bypasses clean(); the DB CheckConstraint must still fire.
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CompensationDataset.objects.create(
                **_ds(source, name="bad", valid_from=date(2025, 12, 31), valid_to=date(2025, 1, 1))
            )


@pytest.mark.django_db
def test_dataset_accepts_open_equal_and_ordered_validity(source):
    CompensationDataset.objects.create(
        **_ds(source, name="open", valid_from=date(2025, 1, 1), valid_to=None)
    )
    CompensationDataset.objects.create(
        **_ds(source, name="none", valid_from=None, valid_to=date(2025, 1, 1))
    )
    CompensationDataset.objects.create(
        **_ds(source, name="eq", valid_from=date(2025, 1, 1), valid_to=date(2025, 1, 1))
    )
    CompensationDataset.objects.create(
        **_ds(source, name="ord", valid_from=date(2025, 1, 1), valid_to=date(2026, 1, 1))
    )
    assert CompensationDataset.objects.count() == 4


# ---------------------------------------------------------------------------
# CompensationTableRow — age / disability band ordering
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_row_db_rejects_inverted_age(dataset):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CompensationTableRow.objects.create(dataset=dataset, age_min=50, age_max=10)


@pytest.mark.django_db
def test_row_db_rejects_inverted_disability(dataset):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            CompensationTableRow.objects.create(
                dataset=dataset, disability_min=80, disability_max=10
            )


@pytest.mark.django_db
def test_row_accepts_valid_and_open_bands(dataset):
    CompensationTableRow.objects.create(
        dataset=dataset, age_min=18, age_max=65, disability_min=10, disability_max=10
    )
    CompensationTableRow.objects.create(
        dataset=dataset, age_min=None, age_max=65
    )  # open lower band
    CompensationTableRow.objects.create(
        dataset=dataset, age_min=30, age_max=None
    )  # open upper band
    CompensationTableRow.objects.create(dataset=dataset, age_min=40, age_max=40)  # degenerate ok
    assert dataset.rows.count() == 4


# ---------------------------------------------------------------------------
# LegalSourceVersion — validity dates
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_legalsourceversion_db_rejects_inverted_validity(source):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            LegalSourceVersion.objects.create(
                source=source,
                version_label="bad",
                valid_from=date(2025, 12, 31),
                valid_to=date(2025, 1, 1),
            )


@pytest.mark.django_db
def test_legalsourceversion_accepts_valid_and_open(source):
    LegalSourceVersion.objects.create(
        source=source, version_label="v1", valid_from=date(2025, 1, 1), valid_to=date(2026, 1, 1)
    )
    LegalSourceVersion.objects.create(
        source=source, version_label="v2", valid_from=date(2025, 1, 1), valid_to=None
    )
    assert source.versions.count() == 2


# ---------------------------------------------------------------------------
# CompensationDataset.source_version — provenance consistency (clean)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dataset_source_version_must_belong_to_same_source(source):
    other_country = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    other_lang = Language.objects.create(code="fr", name="Français")
    other_juris = Jurisdiction.objects.create(
        country=other_country,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    other_src = LegalSource.objects.create(
        slug="fr-h15-test",
        title="FR source",
        country=other_country,
        jurisdiction=other_juris,
        language=other_lang,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2025, 1, 1),
    )
    cross_version = LegalSourceVersion.objects.create(source=other_src, version_label="vX")
    ds = CompensationDataset(**_ds(source, source_version=cross_version))
    with pytest.raises(ValidationError):
        ds.full_clean()


@pytest.mark.django_db
def test_dataset_accepts_matching_source_version(source):
    version = LegalSourceVersion.objects.create(source=source, version_label="v1")
    ds = CompensationDataset(**_ds(source, source_version=version))
    ds.full_clean()  # must not raise
    ds.save()
    assert ds.source_version_id == version.id
