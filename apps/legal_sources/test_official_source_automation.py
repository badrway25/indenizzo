"""
Tests F-product-official-source-automation-and-full-site-functional-upgrade.

Coprono:

1. ``config/official_source_registry.json`` rispetta lo schema atteso.
2. ``manage.py sync_official_sources --dry-run`` non scrive nulla né
   su filesystem né su DB.
3. ``manage.py sync_official_sources --metadata-only`` annota
   ``LegalSource.notes`` con un trailer ``[official_sync] BEGIN…END`` e
   non crea ``LegalReview`` / ``CompensationDataset`` /
   ``CalculationFormula``.
4. Una entry con ``can_auto_ingest=false`` viene saltata nella run
   default e non viene mai promossa a calculator-ready.
5. Una fonte già in stato ``approved`` non viene retrocessa dal sync.
6. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR resta invariata sotto
   tutte le run del sync.
"""

from __future__ import annotations

import json
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command

from apps.legal_sources.management.commands.sync_official_sources import (
    NOTES_MARKER_BEGIN,
    NOTES_MARKER_END,
    validate_registry,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "config" / "official_source_registry.json"


# ---------------------------------------------------------------------------
# 1 — registry schema
# ---------------------------------------------------------------------------


def test_registry_file_exists():
    assert REGISTRY_PATH.exists(), REGISTRY_PATH


def test_registry_schema_is_valid():
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    errors = validate_registry(payload)
    assert errors == [], errors


def test_registry_classifications_balance():
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entries = payload["entries"]
    auto = [e for e in entries if e["can_auto_ingest"]]
    review = [e for e in entries if e["human_exception_review_required"]]
    assert len(auto) >= 3, "expected at least 3 auto-ingest entries"
    assert len(review) >= 2, "expected at least 2 human-exception entries"
    # Mutual exclusion already validated by validate_registry, double-check here.
    for e in entries:
        assert not (e["can_auto_ingest"] and e["human_exception_review_required"])


def test_registry_disallows_invalid_kind(tmp_path):
    bad = {
        "schema_version": "1.0",
        "entries": [
            {
                "country": "IT",
                "jurisdiction": "IT-NATIONAL",
                "case_type": "road_accident_bodily_injury",
                "source_slug": "bad",
                "title": "Bad",
                "official_url": "https://example.test/",
                "source_kind": "wikipedia",
                "authority": "ministry",
                "machine_readable": True,
                "expected_format": "html",
                "can_auto_ingest": True,
                "human_exception_review_required": False,
            }
        ],
    }
    errors = validate_registry(bad)
    assert any("source_kind" in e for e in errors), errors


def test_registry_rejects_mutual_exclusion_violation():
    bad = {
        "schema_version": "1.0",
        "entries": [
            {
                "country": "IT",
                "jurisdiction": "IT-NATIONAL",
                "case_type": "road_accident_bodily_injury",
                "source_slug": "bad",
                "title": "Bad",
                "official_url": "https://example.test/",
                "source_kind": "official_law",
                "authority": "ministry",
                "machine_readable": True,
                "expected_format": "html",
                "can_auto_ingest": True,
                "human_exception_review_required": True,
            }
        ],
    }
    errors = validate_registry(bad)
    assert any("mutually exclusive" in e for e in errors), errors


# ---------------------------------------------------------------------------
# 2 — dry-run does not write
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dry_run_does_not_persist():
    from apps.legal_sources.models import LegalSource

    before_count = LegalSource.objects.count()
    out = StringIO()
    call_command("sync_official_sources", "--dry-run", stdout=out)
    after_count = LegalSource.objects.count()
    assert (
        after_count == before_count
    ), f"dry-run created LegalSource rows: {before_count} -> {after_count}"


# ---------------------------------------------------------------------------
# 3 — metadata-only annotates notes; no LegalReview / dataset / formula
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_metadata_only_annotates_notes_and_no_legal_layer_writes(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
    )
    from apps.legal_sources.models import LegalReview, LegalSource

    review_before = LegalReview.objects.count()
    dataset_before = CompensationDataset.objects.count()
    formula_before = CalculationFormula.objects.count()
    rows_before = CompensationTableRow.objects.count()

    out = StringIO()
    call_command("sync_official_sources", "--metadata-only", stdout=out)

    assert LegalReview.objects.count() == review_before, "LegalReview created!"
    assert CompensationDataset.objects.count() == dataset_before, "CompensationDataset created!"
    assert CalculationFormula.objects.count() == formula_before, "CalculationFormula created!"
    assert CompensationTableRow.objects.count() == rows_before, "CompensationTableRow created!"

    # Each auto-ingestable source must now carry the trailer in notes.
    eu = LegalSource.objects.filter(slug="eu-regulation-650-2012-successions").first()
    assert eu is not None, "EU 650/2012 LegalSource not created by sync"
    assert NOTES_MARKER_BEGIN in (eu.notes or "")
    assert NOTES_MARKER_END in (eu.notes or "")
    payload = (eu.notes or "").split(NOTES_MARKER_BEGIN, 1)[1].split(NOTES_MARKER_END)[0]
    block = json.loads(payload.strip())
    assert block["registry_slug"] == "eu-regulation-650-2012-successions"
    # Post-iter F-official-source-eu-reg-650-fetch-and-trace the registry
    # declares ingest_mode=fetch. The --metadata-only CLI flag overrides
    # the run, which we observe via classification, not via ingest_mode.
    assert block["ingest_mode"] == "fetch"
    assert block["classification"] == "metadata_only"
    assert block["source_kind"] == "eu_regulation"


# ---------------------------------------------------------------------------
# 4 — review-required entries are skipped by default
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_review_required_entries_skipped_by_default(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    call_command("sync_official_sources", "--metadata-only", stdout=out)
    # `fr-loi-badinter-1985` is human_exception_review_required=true → must NOT be created.
    badinter = LegalSource.objects.filter(slug="fr-loi-badinter-1985").first()
    mornet = LegalSource.objects.filter(slug="fr-referentiel-mornet-2024").first()
    tab_indicatif = LegalSource.objects.filter(slug="be-tableau-indicatif-2024").first()
    assert badinter is None, "Loi Badinter must not be auto-synced"
    assert mornet is None, "Référentiel Mornet must not be auto-synced"
    assert tab_indicatif is None, "Tableau Indicatif must not be auto-synced"


@pytest.mark.django_db
def test_review_required_entries_visible_with_include_flag(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    call_command(
        "sync_official_sources",
        "--metadata-only",
        "--include-review-required",
        "--slug",
        "fr-loi-badinter-1985",
        stdout=out,
    )
    badinter = LegalSource.objects.filter(slug="fr-loi-badinter-1985").first()
    assert badinter is not None
    # Even with include-review, the source is created in NEEDS_REVIEW (never APPROVED).
    assert badinter.status != "approved"


# ---------------------------------------------------------------------------
# 5 — already-APPROVED source is not downgraded
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sync_does_not_downgrade_approved_sources(settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from datetime import date

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy, _ = Country.objects.get_or_create(
        code="IT", defaults={"code_alpha3": "ITA", "name": "Italia"}
    )
    italian, _ = Language.objects.get_or_create(code="it", defaults={"name": "Italiano"})
    juris, _ = Jurisdiction.objects.get_or_create(
        code="IT-NATIONAL",
        defaults={
            "country": italy,
            "name": "Italia",
            "legal_system": Jurisdiction.LegalSystem.CIVIL_LAW,
        },
    )
    pre_existing = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title="D.P.R. 12/2025 (pre-existing approved fixture)",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )

    out = StringIO()
    call_command("sync_official_sources", "--metadata-only", stdout=out)

    pre_existing.refresh_from_db()
    assert (
        pre_existing.status == SourceStatus.APPROVED
    ), f"approved source downgraded to {pre_existing.status!r}"
    # Notes get the [official_sync] trailer appended.
    assert NOTES_MARKER_BEGIN in (pre_existing.notes or "")


# ---------------------------------------------------------------------------
# 6 — Italy 35/10/0 contract preserved (engine smoke under sync run)
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_official_automation(db):
    from datetime import date

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-official-automation",
        title="D.P.R. 12/2025",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )
    base_ds = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=base_ds,
        row_type="tun_biological_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    moral_ds = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    for kind, amount in (("min", "26268"), ("mid", "27353"), ("max", "28439")):
        CompensationTableRow.objects.create(
            dataset=moral_ds,
            row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=35,
            age_max=35,
            disability_min=10,
            disability_max=10,
            point_value=Decimal(amount),
        )
    CalculationFormula.objects.create(
        dataset=base_ds,
        code="italy_art_138_tun_2025_official_automation",
        name="official-automation-smoke",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct",
            "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            "min_row_type": "tun_biological_moral_min_total_amount",
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        },
        status=DatasetStatus.APPROVED,
    )
    return {"country": italy}


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_sync(italy_smoke_official_automation, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    call_command("sync_official_sources", "--metadata-only", stdout=out)

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("26268")
    assert sim.estimated_mid == Decimal("27353")
    assert sim.estimated_max == Decimal("28439")
