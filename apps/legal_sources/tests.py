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
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.jurisdictions.models import Country, Jurisdiction, Language
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


# ---------------------------------------------------------------------------
# F2 — clean() language enforcement (REQ-1)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_approved_legal_source_requires_language(italy: Country):
    source = LegalSource(
        title="Fonte senza lingua",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    with pytest.raises(ValidationError) as exc:
        source.full_clean()
    assert "language" in exc.value.error_dict


@pytest.mark.django_db
def test_draft_legal_source_can_omit_language(italy: Country):
    source = LegalSource(
        title="Bozza senza lingua",
        country=italy,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.DRAFT,
    )
    # Draft può non avere lingua: l'arricchimento può avvenire dopo.
    source.full_clean()


@pytest.mark.django_db
def test_approved_legal_source_passes_clean_when_language_set(italy: Country):
    italian = Language.objects.create(code="it", name="Italiano")
    source = LegalSource(
        title="Fonte con lingua",
        country=italy,
        language=italian,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.APPROVED,
    )
    source.full_clean()


# ---------------------------------------------------------------------------
# F-sources-italy — effective_date filter + reference_date in approved()
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_approved_manager_excludes_sources_with_future_effective_date(italy: Country):
    """Una fonte APPROVED ma non ancora vigente NON deve essere usata."""
    not_yet_in_force = LegalSource.objects.create(
        title="Decreto futuro",
        country=italy,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        effective_date=date.today() + timedelta(days=30),
    )
    in_force = LegalSource.objects.create(
        title="Decreto vigente",
        country=italy,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        effective_date=date.today() - timedelta(days=30),
    )
    titles = set(LegalSource.objects.approved().values_list("title", flat=True))
    assert in_force.title in titles
    assert not_yet_in_force.title not in titles


@pytest.mark.django_db
def test_approved_manager_accepts_reference_date_for_dated_simulations(italy: Country):
    """
    Una simulazione su un evento del 2024 deve usare le fonti vigenti
    al 2024, non quelle promulgate dopo.
    """
    promulgated_in_2025 = LegalSource.objects.create(
        title="Decreto 2025",
        country=italy,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        effective_date=date(2025, 2, 26),
    )
    pre_2024 = LegalSource.objects.create(
        title="Decreto pre-2024",
        country=italy,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        effective_date=date(2023, 1, 1),
    )

    # Riferimento al 2024-06-15: la 2025 NON è ancora in vigore.
    titles_2024 = set(
        LegalSource.objects.approved(reference_date=date(2024, 6, 15)).values_list(
            "title", flat=True
        )
    )
    assert pre_2024.title in titles_2024
    assert promulgated_in_2025.title not in titles_2024

    # Riferimento al 2025-12-31: la 2025 è in vigore.
    titles_2025 = set(
        LegalSource.objects.approved(reference_date=date(2025, 12, 31)).values_list(
            "title", flat=True
        )
    )
    assert promulgated_in_2025.title in titles_2025


@pytest.mark.django_db
def test_is_usable_at_respects_effective_date(italy: Country):
    not_yet = LegalSource.objects.create(
        title="Decreto futuro",
        country=italy,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        effective_date=date.today() + timedelta(days=10),
    )
    # Oggi non è usabile.
    assert not_yet.is_usable_at() is False
    # Lo è in una data successiva all'effective_date.
    assert not_yet.is_usable_at(date.today() + timedelta(days=20)) is True


# ---------------------------------------------------------------------------
# F-sources-italy — seed_italy_legal_sources management command
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_italy_legal_sources_creates_metadata_only():
    """
    Il command crea solo metadati, mai status APPROVED automatico, mai
    importi tabellari. Le 5 fonti del seed devono comparire come
    `needs_review`, in italiano, con paese IT.
    """
    from django.core.management import call_command

    from apps.legal_sources.management.commands.seed_italy_legal_sources import (
        SEED_SOURCES,
    )

    call_command("seed_italy_legal_sources", "--quiet")

    sources = LegalSource.objects.filter(country__code="IT")
    assert sources.count() == len(SEED_SOURCES)
    for src in sources:
        assert src.status == SourceStatus.NEEDS_REVIEW
        assert src.language is not None
        assert src.language.code == "it"
        assert src.country.code == "IT"


@pytest.mark.django_db
def test_seed_italy_legal_sources_is_idempotent():
    """Eseguibile più volte senza creare duplicati."""
    from django.core.management import call_command

    from apps.legal_sources.management.commands.seed_italy_legal_sources import (
        SEED_SOURCES,
    )

    call_command("seed_italy_legal_sources", "--quiet")
    first_count = LegalSource.objects.count()
    call_command("seed_italy_legal_sources", "--quiet")
    second_count = LegalSource.objects.count()
    assert first_count == second_count == len(SEED_SOURCES)


@pytest.mark.django_db
def test_seed_does_not_demote_manually_approved_sources():
    """
    Se un legal reviewer ha promosso una fonte ad APPROVED, un re-run
    del seed non deve riportarla a NEEDS_REVIEW.
    """
    from django.core.management import call_command

    call_command("seed_italy_legal_sources", "--quiet")
    src = LegalSource.objects.get(slug="it-dpr-12-2025-tun-danno-biologico")
    src.status = SourceStatus.APPROVED
    src.save(update_fields=["status"])

    call_command("seed_italy_legal_sources", "--quiet")
    src.refresh_from_db()
    assert src.status == SourceStatus.APPROVED


@pytest.mark.django_db
def test_seed_marks_tabelle_milano_as_court_table_not_decree():
    """
    Le Tabelle Milano sono uno standard giurisprudenziale, NON una
    fonte ministeriale: garanzia anti-confusione documentata in
    REQ-3 e nelle note del seed.
    """
    from django.core.management import call_command

    call_command("seed_italy_legal_sources", "--quiet")
    src = LegalSource.objects.get(slug="it-tabelle-milano-2024")
    assert src.source_type == SourceType.COURT_TABLE
    assert src.source_type != SourceType.MINISTRY_DECREE
    assert src.reliability != Reliability.OFFICIAL


# ---------------------------------------------------------------------------
# F-production-bootstrap-preflight — export_italy_tun_dataset
# ---------------------------------------------------------------------------


def _build_italy_tun_stack(italy: Country):
    """Helper: minimal approved Italy TUN stack for export tests."""
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.jurisdictions.models import Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italian = Language.objects.create(code="it", name="Italiano")
    jurisdiction = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title="D.P.R. 12/2025 (test fixture)",
        country=italy,
        jurisdiction=jurisdiction,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
    )
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=jurisdiction,
        country=italy,
        case_type="road_accident_bodily_injury",
        name="Test TUN dataset",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
    )
    CalculationFormula.objects.create(
        dataset=dataset,
        code="italy_art_138_tun_2025_base",
        name="Test formula",
        status=DatasetStatus.APPROVED,
        parameters={
            "engine": "italy_tun_point_value_v1",
            "amount_rule": "row_amount_direct",
            "fault_reduction": True,
        },
    )
    # 3 fixture rows (NOT real TUN values).
    for i in range(3):
        CompensationTableRow.objects.create(
            dataset=dataset,
            row_type="tun_biological_total_amount",
            age_min=i,
            age_max=i,
            disability_min=10,
            disability_max=10,
            point_value=Decimal("1.00"),
            notes="fixture only",
        )
    return src, dataset


@pytest.mark.django_db
def test_export_italy_tun_dataset_writes_json(italy: Country, tmp_path):
    from django.core.management import call_command

    _build_italy_tun_stack(italy)
    out = tmp_path / "snap.json"
    call_command("export_italy_tun_dataset", "--output", str(out), "--quiet")

    import json as _json

    payload = _json.loads(out.read_text(encoding="utf-8"))

    assert payload["schema_version"] == "1.0"
    assert payload["module"]["country"] == "IT"
    assert payload["source"]["slug"] == "it-dpr-12-2025-tun-danno-biologico"
    assert payload["source"]["status"] == "approved"
    assert payload["dataset"]["status"] == "approved"
    assert payload["formula"]["status"] == "approved"
    assert payload["formula"]["parameters"]["amount_rule"] == "row_amount_direct"
    assert payload["rows_count"] == 3
    assert len(payload["rows"]) == 3
    # Every row carries the structural fields:
    for r in payload["rows"]:
        assert {"age_min", "age_max", "disability_min", "disability_max", "point_value"}.issubset(r)


@pytest.mark.django_db
def test_export_italy_tun_dataset_excludes_pii_models(italy: Country, tmp_path):
    """Export MUST NOT include Simulation/Lead/Consent/PrivacyAudit/User."""
    from django.core.management import call_command

    _build_italy_tun_stack(italy)
    out = tmp_path / "snap.json"
    call_command("export_italy_tun_dataset", "--output", str(out), "--quiet")

    raw = out.read_text(encoding="utf-8").lower()
    # The JSON keys are namespaced — these tokens must not appear:
    assert "simulation_id" not in raw
    assert "consent_record" not in raw
    assert "privacyauditevent" not in raw
    assert "lead_id" not in raw
    # Top-level structure should NOT have those collections:
    import json as _json

    payload = _json.loads(out.read_text(encoding="utf-8"))
    forbidden_keys = {"simulations", "leads", "consents", "privacy_events", "users"}
    assert forbidden_keys.isdisjoint(payload.keys())


@pytest.mark.django_db
def test_export_italy_tun_dataset_fails_when_source_missing(tmp_path):
    """No seed → command refuses to write a partial export."""
    from django.core.management import call_command
    from django.core.management.base import CommandError

    out = tmp_path / "snap.json"
    with pytest.raises(CommandError):
        call_command("export_italy_tun_dataset", "--output", str(out), "--quiet")
    assert not out.exists()


# ---------------------------------------------------------------------------
# F-production-bootstrap-preflight — settings security guards
# ---------------------------------------------------------------------------


def test_settings_csrf_trusted_origins_is_list():
    from django.conf import settings

    assert isinstance(settings.CSRF_TRUSTED_ORIGINS, list)


def test_settings_database_uses_env_db_url_or_sqlite_default():
    from django.conf import settings

    db = settings.DATABASES["default"]
    # Either Postgres (when DATABASE_URL is set) or SQLite default
    assert db["ENGINE"] in (
        "django.db.backends.sqlite3",
        "django.db.backends.postgresql",
        "django.db.backends.postgresql_psycopg2",
    )


@pytest.mark.django_db
def test_seeded_sources_do_not_unlock_public_calculations():
    """
    Conferma fine-a-fine: anche dopo aver seedato 5 fonti italiane, il
    calculator pubblico Italia/road_accident resta `unavailable`. Le
    fonti sono `needs_review`, quindi il manager `.approved()` le esclude.
    """
    from django.core.management import call_command

    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    call_command("seed_italy_legal_sources", "--quiet")

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})
    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.sources == []
    assert result.estimated_min is None
