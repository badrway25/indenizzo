"""
Tests F1 — apps.legal_sources.

Verifichiamo:
- creazione minima (default status = draft);
- manager `.approved()` filtra correttamente status e validità temporale;
- helper `compute_sha256` e `compute_bytes_sha256` calcolano hash stabili;
- `LegalSource.is_usable_for_calculations` rispetta la regola d'oro
  ("solo `approved` finisce nei calcoli").
"""

import io
from datetime import date, timedelta

import pytest

from apps.jurisdictions.models import Country, Jurisdiction
from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
from apps.legal_sources.models import LegalSource
from apps.legal_sources.utils import compute_bytes_sha256, compute_sha256


@pytest.fixture
def italy(db) -> Country:
    return Country.objects.create(code="IT", name="Italia")


@pytest.fixture
def italy_jurisdiction(db, italy: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=italy,
        code="IT",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


@pytest.mark.django_db
def test_legal_source_default_status_is_draft(italy: Country):
    source = LegalSource.objects.create(
        title="D.Lgs. 209/2005 (Codice delle Assicurazioni Private)",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
    )
    assert source.status == SourceStatus.DRAFT
    assert source.reliability == Reliability.UNKNOWN
    assert source.is_usable_for_calculations is False


@pytest.mark.django_db
def test_approved_manager_filters_non_approved(italy: Country):
    approved = LegalSource.objects.create(
        title="Fonte approvata",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    LegalSource.objects.create(
        title="Fonte in bozza",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.DRAFT,
    )
    LegalSource.objects.create(
        title="Fonte da revisionare",
        country=italy,
        source_type=SourceType.COURT_TABLE,
        status=SourceStatus.NEEDS_REVIEW,
    )
    LegalSource.objects.create(
        title="Fonte deprecata",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.DEPRECATED,
    )

    approved_qs = LegalSource.objects.approved()
    assert list(approved_qs) == [approved]


@pytest.mark.django_db
def test_approved_manager_excludes_expired_sources(italy: Country):
    yesterday = date.today() - timedelta(days=1)
    LegalSource.objects.create(
        title="Fonte approvata ma scaduta",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        valid_until=yesterday,
    )
    still_valid = LegalSource.objects.create(
        title="Fonte approvata ancora valida",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        valid_until=date.today() + timedelta(days=10),
    )
    no_expiry = LegalSource.objects.create(
        title="Fonte approvata senza scadenza",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )

    approved_titles = set(LegalSource.objects.approved().values_list("title", flat=True))
    assert still_valid.title in approved_titles
    assert no_expiry.title in approved_titles
    assert "Fonte approvata ma scaduta" not in approved_titles


@pytest.mark.django_db
def test_is_usable_for_calculations(italy: Country):
    valid_source = LegalSource.objects.create(
        title="Fonte usabile",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        reliability=Reliability.OFFICIAL,
    )
    expired_source = LegalSource.objects.create(
        title="Fonte scaduta",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
        valid_until=date.today() - timedelta(days=1),
    )
    assert valid_source.is_usable_for_calculations is True
    assert expired_source.is_usable_for_calculations is False


@pytest.mark.django_db
def test_by_country_and_jurisdiction_filters(italy: Country, italy_jurisdiction: Jurisdiction):
    LegalSource.objects.create(
        title="Fonte IT",
        country=italy,
        jurisdiction=italy_jurisdiction,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    france = Country.objects.create(code="FR", name="France")
    LegalSource.objects.create(
        title="Fonte FR",
        country=france,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    assert LegalSource.objects.by_country("it").count() == 1
    assert LegalSource.objects.by_jurisdiction("it").count() == 1
    assert LegalSource.objects.by_country("fr").count() == 1


def test_compute_bytes_sha256_is_deterministic():
    payload = b"hello legal world"
    digest_a = compute_bytes_sha256(payload)
    digest_b = compute_bytes_sha256(payload)
    assert digest_a == digest_b
    assert len(digest_a) == 64


def test_compute_sha256_resets_cursor():
    payload = b"some pdf bytes"
    buffer = io.BytesIO(payload)
    digest = compute_sha256(buffer)
    assert digest == compute_bytes_sha256(payload)
    # Il cursore deve essere riposizionato a 0 per non disturbare il salvataggio file.
    assert buffer.tell() == 0
