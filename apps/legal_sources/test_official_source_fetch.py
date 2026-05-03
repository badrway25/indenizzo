"""
Tests F-official-source-ma-moudawana-fetch-and-trace.

Coprono il path "fetch reale" del command ``sync_official_sources``:

1. fetch PDF success → manifest + sha256 + LegalSource notes con
   ``classification=fetch_success``.
2. fetch HTML success → stessa pipeline ma estensione `.html`.
3. fetch failure → manifest con error + notes con
   ``classification=fetch_failed``; **nessuna** scrittura legal-layer
   (LegalReview / CompensationDataset / CalculationFormula /
   CompensationTableRow).
4. Re-run sostituisce il blocco ``[official_sync]`` precedente in
   ``LegalSource.notes`` invece di duplicarlo.
5. Calculator MA resta ``unavailable_requires_legal_validation`` dopo
   il fetch.
6. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR resta invariata.

I test fanno mock di ``apps.legal_sources.management.commands.sync_official_sources._fetch``
per evitare HTTP reale.
"""

from __future__ import annotations

import json
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import patch

import pytest
import requests
from django.core.management import call_command

from apps.legal_sources.management.commands.sync_official_sources import (
    NOTES_MARKER_BEGIN,
    NOTES_MARKER_END,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MA_SLUG = "ma-code-famille-moudawana-fr-pdf"
TN_SLUG = "tn-code-statut-personnel-livre-ix-succession"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_official_sync_block(notes: str) -> dict:
    payload = notes.split(NOTES_MARKER_BEGIN, 1)[1].split(NOTES_MARKER_END)[0]
    return json.loads(payload.strip())


def _fake_fetch_pdf(url, timeout=30):
    body = b"%PDF-1.4 fake test payload " + b"x" * 200
    return ("https://www.legal-tools.org/doc/0e057b/pdf/", 200, "application/pdf", body)


def _fake_fetch_html(url, timeout=30):
    body = b"<html><body><h1>CSP livre IX</h1></body></html>"
    return ("https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1100.htm", 200, "text/html", body)


def _fake_fetch_failure(url, timeout=30):
    raise requests.ConnectionError("simulated network error for tests")


# ---------------------------------------------------------------------------
# 1 — fetch PDF success
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fetch_pdf_success_writes_sha256_and_notes(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_pdf,
    ):
        call_command("sync_official_sources", "--country", "MA", "--slug", MA_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=MA_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_success"
    assert block["http_status"] == 200
    assert block["size_bytes"] > 0
    assert len(block["sha256"]) == 64  # hex digest
    assert block["no_calculator_activation"] is True
    assert block["error"] == ""
    assert block["local_path"].endswith(".pdf")

    # Local file actually exists.
    repo_local = Path(settings.BASE_DIR) / block["local_path"]
    assert repo_local.exists()
    assert repo_local.read_bytes()[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# 2 — fetch HTML success
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fetch_html_success_writes_sha256_and_notes(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    # Switch the TN entry to fetch mode for this test by overriding the registry.
    registry_path = REPO_ROOT / "config" / "official_source_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    for entry in registry["entries"]:
        if entry["source_slug"] == TN_SLUG:
            entry["ingest_mode"] = "fetch"
    override_path = tmp_path / "registry_override.json"
    override_path.write_text(json.dumps(registry, ensure_ascii=False), encoding="utf-8")

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_html,
    ):
        call_command(
            "sync_official_sources",
            "--registry",
            str(override_path),
            "--country",
            "TN",
            "--slug",
            TN_SLUG,
            stdout=out,
        )

    src = LegalSource.objects.get(slug=TN_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_success"
    assert block["local_path"].endswith(".html")
    repo_local = Path(settings.BASE_DIR) / block["local_path"]
    assert repo_local.exists()
    assert b"livre IX" in repo_local.read_bytes()


# ---------------------------------------------------------------------------
# 3 — fetch failure: no legal-layer writes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fetch_failure_does_not_create_legal_layer(tmp_path, settings):
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
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_failure,
    ):
        call_command("sync_official_sources", "--country", "MA", "--slug", MA_SLUG, stdout=out)

    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before

    src = LegalSource.objects.get(slug=MA_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert block["error"].startswith("fetch_failed: ConnectionError"), block["error"]
    assert block["http_status"] is None
    assert block["sha256"] == ""
    assert block["local_path"] == ""
    # Manifest mirrors the failure: classification + error are recorded,
    # no PDF/HTML local_path is set, no sha256 is computed.


# ---------------------------------------------------------------------------
# 4 — re-run replaces previous [official_sync] block (idempotent)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_rerun_replaces_official_sync_block(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_pdf,
    ):
        call_command("sync_official_sources", "--country", "MA", "--slug", MA_SLUG, stdout=out)
    src = LegalSource.objects.get(slug=MA_SLUG)
    first_notes = src.notes
    assert first_notes.count(NOTES_MARKER_BEGIN) == 1
    assert first_notes.count(NOTES_MARKER_END) == 1

    # Re-run with a different fake payload to bump sha256.
    def _fake_fetch_pdf_v2(url, timeout=30):
        body = b"%PDF-1.7 second run payload " + b"y" * 300
        return ("https://www.legal-tools.org/doc/0e057b/pdf/", 200, "application/pdf", body)

    out2 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_pdf_v2,
    ):
        call_command("sync_official_sources", "--country", "MA", "--slug", MA_SLUG, stdout=out2)
    src.refresh_from_db()
    second_notes = src.notes
    assert second_notes.count(NOTES_MARKER_BEGIN) == 1, "block duplicated on re-run"
    assert second_notes.count(NOTES_MARKER_END) == 1
    block = _extract_official_sync_block(second_notes)
    # New sha256 → different from the first run.
    first_block = _extract_official_sync_block(first_notes)
    assert block["sha256"] != first_block["sha256"]


# ---------------------------------------------------------------------------
# 5 — MA calculator stays unavailable after fetch
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_calculator_remains_unavailable_after_fetch(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_pdf,
    ):
        call_command("sync_official_sources", "--country", "MA", "--slug", MA_SLUG, stdout=out)

    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min in (None,)
    assert sim.estimated_mid in (None,)
    assert sim.estimated_max in (None,)


# ---------------------------------------------------------------------------
# 6 — Italy smoke contract preserved through fetch
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_ma_fetch(db):
    from datetime import date

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
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
        slug="it-dpr-12-2025-tun-ma-fetch",
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
        code="italy_art_138_tun_2025_ma_fetch",
        name="ma-fetch-smoke",
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
def test_italy_smoke_unchanged_after_ma_fetch(italy_smoke_ma_fetch, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_pdf,
    ):
        call_command("sync_official_sources", "--country", "MA", "--slug", MA_SLUG, stdout=out)

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


# ---------------------------------------------------------------------------
# 7 — TN CSP Livre IX fetch (post F-official-source-tn-csp-livre-ix-fetch-and-trace)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_csp_fetch_uses_real_registry_in_fetch_mode(tmp_path, settings):
    """Dopo l'iter TN, il registry committato ha già ingest_mode='fetch'
    per `tn-code-statut-personnel-livre-ix-succession`. Il command non
    richiede più override."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_html,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=TN_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_success"
    assert block["http_status"] == 200
    assert block["ingest_mode"] == "fetch"
    assert block["local_path"].endswith(".html")
    assert block["no_calculator_activation"] is True


@pytest.mark.django_db
def test_tn_calculator_remains_unavailable_after_fetch(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_html,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_SLUG, stdout=out)

    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


@pytest.mark.django_db
def test_tn_html_extension_classified_as_html(tmp_path, settings):
    """Il classificatore di estensione, davanti a Content-Type=text/html,
    salva con `.html` (non `.bin` né `.pdf`) anche se il registry dichiara
    expected_format=html (registry hint coerente con header)."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_html,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=TN_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["local_path"].endswith(".html")
    repo_local = Path(settings.BASE_DIR) / block["local_path"]
    assert repo_local.exists()
    assert b"livre IX" in repo_local.read_bytes()


@pytest.mark.django_db
def test_tn_fetch_idempotent_replaces_block(tmp_path, settings):
    """Re-run con payload diverso → un solo blocco, sha256 diverso."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out1 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_html,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_SLUG, stdout=out1)
    src = LegalSource.objects.get(slug=TN_SLUG)
    first = _extract_official_sync_block(src.notes)

    def _fake_fetch_html_v2(url, timeout=30):
        body = b"<html><body><h1>CSP livre IX v2</h1><p>updated</p></body></html>"
        return (
            "https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1100.htm",
            200,
            "text/html",
            body,
        )

    out2 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_html_v2,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_SLUG, stdout=out2)
    src.refresh_from_db()
    assert src.notes.count(NOTES_MARKER_BEGIN) == 1
    assert src.notes.count(NOTES_MARKER_END) == 1
    second = _extract_official_sync_block(src.notes)
    assert first["sha256"] != second["sha256"]


@pytest.mark.django_db
def test_tn_fetch_failure_does_not_create_legal_layer(tmp_path, settings):
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
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_failure,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_SLUG, stdout=out)

    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before

    src = LegalSource.objects.get(slug=TN_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert block["error"].startswith("fetch_failed: ConnectionError")
    assert block["http_status"] is None
    assert block["sha256"] == ""
    assert block["local_path"] == ""
