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
    assert "fetch_failed: ConnectionError" in block["error"], block["error"]
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
    assert "fetch_failed: ConnectionError" in block["error"]
    assert block["http_status"] is None
    assert block["sha256"] == ""
    assert block["local_path"] == ""


# ---------------------------------------------------------------------------
# 8 — TN Code DIP Loi 98-97 (post F-official-source-tn-code-dip-fetch-and-trace)
# ---------------------------------------------------------------------------


TN_DIP_SLUG = "tn-code-dip-loi-98-97"


def _fake_fetch_dip_html(url, timeout=30):
    body = (
        b'<!DOCTYPE html><html lang="fr"><head><title>'
        b"Code de Droit International Prive</title></head>"
        b"<body><h1>TITRE II - La competence des juridictions tunisiennes</h1>"
        b"<p>Loi 98-97 du 27 novembre 1998</p></body></html>"
    )
    return (
        "https://www.jurisitetunisie.com/tunisie/codes/cdip/cdip1010.htm",
        200,
        "text/html",
        body,
    )


def test_tn_dip_registry_entry_is_present_and_valid():
    """Il registry committato deve contenere un entry per Code DIP TN
    classificato come official_law / fetch / can_auto_ingest=true."""
    registry_path = REPO_ROOT / "config" / "official_source_registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = next(
        (e for e in payload["entries"] if e["source_slug"] == TN_DIP_SLUG),
        None,
    )
    assert entry is not None, f"registry missing entry {TN_DIP_SLUG!r}"
    assert entry["country"] == "TN"
    assert entry["jurisdiction"] == "TN-NATIONAL"
    assert entry["case_type"] == "international_inheritance"
    assert entry["source_kind"] == "official_law"
    assert entry["machine_readable"] is True
    assert entry["expected_format"] == "html"
    assert entry["can_auto_ingest"] is True
    assert entry["human_exception_review_required"] is False
    assert entry["ingest_mode"] == "fetch"


@pytest.mark.django_db
def test_tn_dip_html_fetch_success_writes_sha256_and_notes(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_dip_html,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_DIP_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=TN_DIP_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_success"
    assert block["http_status"] == 200
    assert block["ingest_mode"] == "fetch"
    assert block["source_kind"] == "official_law"
    assert block["local_path"].endswith(".html")
    assert block["no_calculator_activation"] is True
    assert block["error"] == ""

    repo_local = Path(settings.BASE_DIR) / block["local_path"]
    assert repo_local.exists()
    body = repo_local.read_bytes()
    assert b"International Prive" in body or b"droit international" in body.lower()


@pytest.mark.django_db
def test_tn_dip_html_extension_is_html(tmp_path, settings):
    """Content-Type=text/html → extension `.html` (not `.bin`)."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_dip_html,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_DIP_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=TN_DIP_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["local_path"].endswith(".html")


@pytest.mark.django_db
def test_tn_dip_idempotent_replaces_block(tmp_path, settings):
    """Re-run con payload diverso → un solo blocco, sha256 diverso."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out1 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_dip_html,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_DIP_SLUG, stdout=out1)
    src = LegalSource.objects.get(slug=TN_DIP_SLUG)
    first = _extract_official_sync_block(src.notes)

    def _fake_fetch_dip_html_v2(url, timeout=30):
        body = b"<html><body><h1>Code DIP v2</h1><p>updated</p></body></html>"
        return (
            "https://www.jurisitetunisie.com/tunisie/codes/cdip/cdip1010.htm",
            200,
            "text/html",
            body,
        )

    out2 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_dip_html_v2,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_DIP_SLUG, stdout=out2)
    src.refresh_from_db()
    assert src.notes.count(NOTES_MARKER_BEGIN) == 1
    assert src.notes.count(NOTES_MARKER_END) == 1
    second = _extract_official_sync_block(src.notes)
    assert first["sha256"] != second["sha256"]


@pytest.mark.django_db
def test_tn_dip_calculator_remains_unavailable_after_fetch(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_dip_html,
    ):
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_DIP_SLUG, stdout=out)

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
def test_tn_dip_fetch_failure_does_not_create_legal_layer(tmp_path, settings):
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
        call_command("sync_official_sources", "--country", "TN", "--slug", TN_DIP_SLUG, stdout=out)

    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before

    src = LegalSource.objects.get(slug=TN_DIP_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert block["http_status"] is None
    assert block["sha256"] == ""


@pytest.mark.django_db
def test_tn_csp_and_dip_can_coexist(tmp_path, settings):
    """Eseguendo sync TN senza --slug, entrambe le entry vengono
    fetchate e il manifest ne contiene i due result; nessuno
    sovrascrive l'altro."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    def _fake_either(url, timeout=30):
        if "csp" in url.lower() or "csp1100" in url.lower():
            return _fake_fetch_html(url, timeout)
        return _fake_fetch_dip_html(url, timeout)

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_either,
    ):
        call_command("sync_official_sources", "--country", "TN", stdout=out)

    csp = LegalSource.objects.get(slug=TN_SLUG)
    dip = LegalSource.objects.get(slug=TN_DIP_SLUG)
    csp_block = _extract_official_sync_block(csp.notes)
    dip_block = _extract_official_sync_block(dip.notes)
    assert csp_block["classification"] == "fetch_success"
    assert dip_block["classification"] == "fetch_success"
    assert csp_block["sha256"] != dip_block["sha256"]
    assert csp_block["registry_slug"] == TN_SLUG
    assert dip_block["registry_slug"] == TN_DIP_SLUG
    # Each LegalSource has exactly one block (no duplication).
    assert csp.notes.count(NOTES_MARKER_BEGIN) == 1
    assert dip.notes.count(NOTES_MARKER_BEGIN) == 1


# ---------------------------------------------------------------------------
# 9 — EU Reg 650/2012 (post F-official-source-eu-reg-650-fetch-and-trace)
# ---------------------------------------------------------------------------


EU_SLUG = "eu-regulation-650-2012-successions"


def _fake_fetch_eu_html(url, timeout=30):
    body = (
        b'<!DOCTYPE html><html lang="fr"><head>'
        b"<title>Reglement (UE) 650/2012 - successions transfrontalieres - EUR-Lex</title></head>"
        b"<body><h1>REGLEMENT (UE) No 650/2012 DU PARLEMENT EUROPEEN ET DU CONSEIL</h1>"
        b"<p>du 4 juillet 2012 relatif a la competence, la loi applicable, "
        b"la reconnaissance et l'execution des decisions, et l'acceptation et "
        b"l'execution des actes authentiques en matiere de successions et a la "
        b"creation d'un certificat successoral europeen.</p>"
        b"</body></html>"
    )
    return (
        "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650",
        200,
        "text/html",
        body,
    )


def _fake_fetch_eu_xml(url, timeout=30):
    body = (
        b'<?xml version="1.0" encoding="UTF-8"?>'
        b"<NOTICE><WORK><URI>"
        b"http://publications.europa.eu/resource/cellar/650/2012</URI>"
        b"</WORK></NOTICE>"
    )
    return (
        "https://eur-lex.europa.eu/legal-content/FR/TXT/XML/?uri=CELEX:32012R0650",
        200,
        "text/xml",
        body,
    )


def _fake_fetch_eu_pdf(url, timeout=30):
    body = b"%PDF-1.4 fake EU 650/2012 payload " + b"x" * 200
    return (
        "https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32012R0650",
        200,
        "application/pdf",
        body,
    )


def _fake_fetch_eu_202_empty(url, timeout=30):
    """EUR-Lex CloudFront interstitial: 202 + tiny holding page senza marker."""
    body = b"<!DOCTYPE html><html><head><title></title></head><body></body></html>"
    return (url, 202, "text/html", body)


def _fake_fetch_zero_bytes(url, timeout=30):
    return (url, 200, "text/html", b"")


def _fake_fetch_html_no_marker(url, timeout=30):
    """200 OK con HTML che non contiene il marker 650/2012 (es. cookie banner)."""
    body = (
        b"<!DOCTYPE html><html><head><title>Cookie consent</title></head>"
        b"<body><p>This site uses cookies. Click accept.</p></body></html>"
    )
    return (url, 200, "text/html", body)


def test_eu_registry_entry_is_present_and_valid():
    registry_path = REPO_ROOT / "config" / "official_source_registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = next(
        (e for e in payload["entries"] if e["source_slug"] == EU_SLUG),
        None,
    )
    assert entry is not None, f"registry missing entry {EU_SLUG!r}"
    assert entry["country"] == "EU"
    assert entry["jurisdiction"] == "EU-INTL"
    assert entry["case_type"] == "international_inheritance"
    assert entry["source_kind"] == "eu_regulation"
    assert entry["authority"] == "eurlex"
    assert entry["machine_readable"] is True
    assert entry["expected_format"] == "html"
    assert entry["can_auto_ingest"] is True
    assert entry["human_exception_review_required"] is False
    assert entry["ingest_mode"] == "fetch"
    # Fallback URLs must include XML and PDF endpoints.
    alts = entry.get("fetch_url_alternatives") or []
    assert any("XML" in u for u in alts), alts
    assert any("PDF" in u for u in alts), alts
    # Content validation marker.
    assert "650/2012" in (entry.get("content_must_contain") or [])


@pytest.mark.django_db
def test_eu_html_fetch_success_writes_sha256_and_notes(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_eu_html,
    ):
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=EU_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_success"
    assert block["http_status"] == 200
    assert block["ingest_mode"] == "fetch"
    assert block["source_kind"] == "eu_regulation"
    assert block["authority"] == "eurlex"
    assert block["local_path"].endswith(".html")
    assert block["no_calculator_activation"] is True
    assert block["error"] == ""
    assert len(block["sha256"]) == 64

    repo_local = Path(settings.BASE_DIR) / block["local_path"]
    assert repo_local.exists()
    body = repo_local.read_bytes()
    assert b"650/2012" in body


@pytest.mark.django_db
def test_eu_fetch_falls_back_to_xml_when_html_returns_202(tmp_path, settings):
    """Primary URL gives 202 (rejected) → fallback to XML succeeds."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    def _fake_eu_dispatcher(url, timeout=30):
        if "/XML/" in url:
            return _fake_fetch_eu_xml(url, timeout)
        if "/PDF/" in url:
            return _fake_fetch_eu_pdf(url, timeout)
        # Primary HTML returns 202 + empty stub.
        return _fake_fetch_eu_202_empty(url, timeout)

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_eu_dispatcher,
    ):
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=EU_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_success"
    assert block["local_path"].endswith(".xml")
    assert "/XML/" in block["final_url"]
    # The HTML primary URL is recorded as a fallback attempt.
    assert any("HTTP 202" in att for att in block["fallback_attempts"]), block["fallback_attempts"]


@pytest.mark.django_db
def test_eu_fetch_rejects_http_202_with_empty_body(tmp_path, settings):
    """When ALL URLs return 202, classification stays fetch_failed."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_eu_202_empty,
    ):
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=EU_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert block["http_status"] is None
    assert block["sha256"] == ""
    assert block["local_path"] == ""
    assert "HTTP 202" in block["error"]


@pytest.mark.django_db
def test_eu_fetch_rejects_zero_byte_response(tmp_path, settings):
    """200 OK with size_bytes=0 must be classified fetch_failed."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_zero_bytes,
    ):
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=EU_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert "empty body" in block["error"]


@pytest.mark.django_db
def test_eu_fetch_rejects_missing_content_marker(tmp_path, settings):
    """200 OK with body that lacks the registry's content_must_contain
    markers (e.g. a cookie-only banner page) is rejected."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_html_no_marker,
    ):
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=EU_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert "missing required content markers" in block["error"]


def test_validate_fetch_response_rejects_known_empty_sha256():
    """Defensive unit test on the validator helper itself: the well-known
    sha256 of an empty byte string must always be rejected, even if the
    body somehow has length > 0 (paranoid guard against future regressions)."""
    from apps.legal_sources.management.commands.sync_official_sources import (
        EMPTY_SHA256,
        validate_fetch_response,
    )

    err = validate_fetch_response(b"non-empty", 200, EMPTY_SHA256)
    assert err.startswith("fetch_failed: null sha256"), err


@pytest.mark.django_db
def test_eu_fetch_idempotent_replaces_block(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out1 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_eu_html,
    ):
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out1)
    src = LegalSource.objects.get(slug=EU_SLUG)
    first = _extract_official_sync_block(src.notes)

    def _fake_eu_html_v2(url, timeout=30):
        body = (
            b"<!DOCTYPE html><html><body>"
            b"<h1>EU 650/2012 v2</h1><p>updated body</p></body></html>"
        )
        return (
            "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650",
            200,
            "text/html",
            body,
        )

    out2 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_eu_html_v2,
    ):
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out2)
    src.refresh_from_db()
    assert src.notes.count(NOTES_MARKER_BEGIN) == 1
    assert src.notes.count(NOTES_MARKER_END) == 1
    second = _extract_official_sync_block(src.notes)
    assert first["sha256"] != second["sha256"]


@pytest.mark.django_db
def test_eu_fetch_does_not_activate_ma_or_tn_calculator(tmp_path, settings):
    """Successfully fetching the EU regulation must not promote MA or TN
    inheritance calculators out of unavailable_requires_legal_validation."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_eu_html,
    ):
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out)

    for jcode in ("MA-NATIONAL", "TN-NATIONAL"):
        sim = run_simulation(
            jurisdiction_code=jcode,
            case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
            input_data={},
        )
        assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


@pytest.mark.django_db
def test_eu_fetch_failure_does_not_create_legal_layer(tmp_path, settings):
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
        call_command("sync_official_sources", "--country", "EU", "--slug", EU_SLUG, stdout=out)

    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before

    src = LegalSource.objects.get(slug=EU_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert block["http_status"] is None
    assert block["sha256"] == ""


# ---------------------------------------------------------------------------
# 10 — IT D.P.R. 12/2025 cross-check (post
# F-official-source-it-dpr-12-2025-gazzetta-crosscheck)
# ---------------------------------------------------------------------------


IT_DPR_SLUG = "it-dpr-12-2025-tun-danno-biologico"


def _fake_fetch_it_gazzetta_pdf(url, timeout=30):
    """Synthetic Gazzetta PDF body that contains all five registry markers
    in the raw bytes. Real Gazzetta PDFs encode glyphs through font CMap so
    only pdfplumber can recover the text — but for the test we keep things
    mock-friendly by embedding the marker words directly in the byte stream.
    """
    body = (
        b"%PDF-1.4\n"
        b"% Synthetic Gazzetta payload for tests\n"
        b"D.P.R. 13 gennaio 2025, n. 12\n"
        b"Tabella Unica Nazionale - art. 138 CAP\n"
        b"danno biologico\n" + b"x" * 400
    )
    return (
        "https://www.gazzettaufficiale.it/eli/gu/2025/02/11/34/sg/pdf",
        200,
        "application/pdf",
        body,
    )


def _fake_fetch_it_html_no_marker(url, timeout=30):
    """ELI HTML page returns 200 + JS-only shell (no markers in raw bytes).
    This mimics the real Gazzetta ELI behaviour: the page is rendered
    client-side, so a server-side fetch sees only navigation chrome.
    """
    body = (
        b"<!DOCTYPE html><html><head>"
        b"<title>Gazzetta Ufficiale</title></head>"
        b"<body><div id='app'></div>"
        b"<script>/* SPA bootstrap */</script></body></html>"
    )
    return (url, 200, "text/html;charset=UTF-8", body)


def test_it_dpr_registry_entry_is_present_and_valid():
    """Registry must declare IT D.P.R. as verify_existing crosscheck with
    Gazzetta PDF as fallback and the five Italian-language markers."""
    registry_path = REPO_ROOT / "config" / "official_source_registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = next(
        (e for e in payload["entries"] if e["source_slug"] == IT_DPR_SLUG),
        None,
    )
    assert entry is not None, f"registry missing entry {IT_DPR_SLUG!r}"
    assert entry["country"] == "IT"
    assert entry["jurisdiction"] == "IT-NATIONAL"
    assert entry["case_type"] == "road_accident_bodily_injury"
    assert entry["source_kind"] == "official_decree"
    assert entry["authority"] == "official_gazette"
    assert entry["can_auto_ingest"] is True
    assert entry["human_exception_review_required"] is False
    assert entry["ingest_mode"] == "verify_existing"
    assert entry.get("no_reimport") is True
    assert entry.get("no_calculator_activation_change") is True
    alts = entry.get("fetch_url_alternatives") or []
    assert any("gazzettaufficiale.it" in u and u.endswith("pdf") for u in alts), alts
    markers = entry.get("content_must_contain") or []
    for required in ("D.P.R.", "13 gennaio 2025", "n. 12", "danno biologico", "Tabella"):
        assert required in markers, f"missing marker {required!r} in {markers!r}"


@pytest.mark.django_db
def test_it_crosscheck_success_writes_sha256_and_notes(tmp_path, settings):
    """Cross-check on IT entry: Gazzetta PDF accepted, classification is
    crosscheck_success (not fetch_success), notes block carries the
    crosscheck_only/no_reimport/no_calculator_activation_change/marker_check_passed
    flags."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    def _dispatcher(url, timeout=30):
        if url.endswith(".pdf") or "/gu/" in url:
            return _fake_fetch_it_gazzetta_pdf(url, timeout)
        return _fake_fetch_it_html_no_marker(url, timeout)

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_dispatcher,
    ):
        call_command("sync_official_sources", "--country", "IT", "--slug", IT_DPR_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=IT_DPR_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "crosscheck_success"
    assert block["http_status"] == 200
    assert block["ingest_mode"] == "verify_existing"
    assert block["source_kind"] == "official_decree"
    assert block["authority"] == "official_gazette"
    assert block["local_path"].endswith(".pdf")
    assert block["error"] == ""
    assert block["crosscheck_only"] is True
    assert block["no_reimport"] is True
    assert block["no_calculator_activation_change"] is True
    assert block["marker_check_passed"] is True
    # The HTML primary URL is recorded as a fallback attempt — its raw
    # body lacks every marker because the page is JS-rendered.
    assert any(
        "missing required content markers" in att for att in block["fallback_attempts"]
    ), block["fallback_attempts"]


@pytest.mark.django_db
def test_it_crosscheck_marker_missing_classified_failed(tmp_path, settings):
    """All candidate URLs return bodies without any required marker →
    classification crosscheck_failed and marker_check_passed=False."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_it_html_no_marker,
    ):
        call_command("sync_official_sources", "--country", "IT", "--slug", IT_DPR_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=IT_DPR_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "crosscheck_failed"
    assert block["sha256"] == ""
    assert block["local_path"] == ""
    assert block["marker_check_passed"] is False
    assert "missing required content markers" in block["error"]


@pytest.mark.django_db
def test_it_crosscheck_does_not_modify_dataset_formula_rows(tmp_path, settings):
    """A successful cross-check must not create or alter any
    CompensationDataset / CalculationFormula / CompensationTableRow row,
    even when the LegalSource is already wired to APPROVED dataset+formula
    fixtures (no_reimport guarantee)."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from datetime import date
    from decimal import Decimal as D

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalReview, LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug=IT_DPR_SLUG,
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
        point_value=D("1"),
    )
    CalculationFormula.objects.create(
        dataset=base_ds,
        code="italy_art_138_tun_2025_crosscheck_smoke",
        name="crosscheck-smoke",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={"engine": "italy_tun_point_value_v1", "amount_rule": "row_amount_range_direct"},
        status=DatasetStatus.APPROVED,
    )
    review_before = LegalReview.objects.count()
    dataset_before = CompensationDataset.objects.count()
    formula_before = CalculationFormula.objects.count()
    rows_before = CompensationTableRow.objects.count()

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_it_gazzetta_pdf,
    ):
        call_command("sync_official_sources", "--country", "IT", "--slug", IT_DPR_SLUG, stdout=out)

    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before


@pytest.mark.django_db
def test_it_crosscheck_does_not_demote_approved_source(tmp_path, settings):
    """Pre-existing APPROVED LegalSource must remain APPROVED after a
    successful cross-check (the verify_existing path never alters status)."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from datetime import date

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    LegalSource.objects.create(
        slug=IT_DPR_SLUG,
        title="D.P.R. 12/2025 approved fixture",
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
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_it_gazzetta_pdf,
    ):
        call_command("sync_official_sources", "--country", "IT", "--slug", IT_DPR_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=IT_DPR_SLUG)
    assert src.status == SourceStatus.APPROVED, f"got {src.status!r}"
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "crosscheck_success"


@pytest.mark.django_db
def test_it_crosscheck_idempotent_replaces_block(tmp_path, settings):
    """Re-run cross-check with a different mock payload: notes still
    contain a single [official_sync] block, sha256 reflects the latest
    body, and crosscheck_only flag stays True."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out1 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_it_gazzetta_pdf,
    ):
        call_command("sync_official_sources", "--country", "IT", "--slug", IT_DPR_SLUG, stdout=out1)
    src = LegalSource.objects.get(slug=IT_DPR_SLUG)
    first = _extract_official_sync_block(src.notes)

    def _fake_pdf_v2(url, timeout=30):
        body = (
            b"%PDF-1.7\n"
            b"% Updated synthetic Gazzetta payload\n"
            b"D.P.R. 13 gennaio 2025, n. 12 - revision\n"
            b"Tabella Unica Nazionale\n"
            b"danno biologico\n" + b"y" * 600
        )
        return (
            "https://www.gazzettaufficiale.it/eli/gu/2025/02/11/34/sg/pdf",
            200,
            "application/pdf",
            body,
        )

    out2 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_pdf_v2,
    ):
        call_command("sync_official_sources", "--country", "IT", "--slug", IT_DPR_SLUG, stdout=out2)
    src.refresh_from_db()
    assert src.notes.count(NOTES_MARKER_BEGIN) == 1, "block duplicated on re-run"
    assert src.notes.count(NOTES_MARKER_END) == 1
    second = _extract_official_sync_block(src.notes)
    assert first["sha256"] != second["sha256"]
    assert second["crosscheck_only"] is True


@pytest.fixture
def italy_smoke_it_crosscheck(db):
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
        slug="it-dpr-12-2025-tun-it-crosscheck-smoke",
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
        code="italy_art_138_tun_2025_it_crosscheck",
        name="it-crosscheck-smoke",
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
def test_italy_smoke_unchanged_after_it_crosscheck(italy_smoke_it_crosscheck, tmp_path, settings):
    """Italia 35/10/0 → 26268/27353/28439 EUR resta invariata anche dopo
    una run di crosscheck del D.P.R. 12/2025 sulla Gazzetta Ufficiale."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_it_gazzetta_pdf,
    ):
        call_command("sync_official_sources", "--country", "IT", "--slug", IT_DPR_SLUG, stdout=out)

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
# 11 — BE Loi 1989 RC Auto fetch (post
# F-official-source-be-loi-1989-rc-auto-fetch-and-trace)
# ---------------------------------------------------------------------------


BE_LOI_SLUG = "be-loi-1989-11-21-rc-auto"


def _fake_fetch_be_loi_html(url, timeout=30):
    """Synthetic SPF Économie HTML response. Embeds all four FR registry
    markers verbatim so the raw-bytes marker check passes."""
    body = (
        b'<!DOCTYPE html><html lang="fr"><head>'
        b"<title>Loi du 21 novembre 1989 - SPF Economie</title></head>"
        b"<body><h1>Loi du 21 novembre 1989 relative \xc3\xa0 l'assurance "
        b"obligatoire de la responsabilit\xc3\xa9 en mati\xc3\xa8re de "
        b"v\xc3\xa9hicules automoteurs</h1>"
        b"<p>21 NOVEMBRE 1989. - Loi relative \xc3\xa0 l'assurance "
        b"obligatoire de la responsabilit\xc3\xa9 en mati\xc3\xa8re de "
        b"v\xc3\xa9hicules automoteurs.</p></body></html>"
    )
    return (
        "https://economie.fgov.be/fr/legislation/loi-du-21-novembre-1989",
        200,
        "text/html; charset=UTF-8",
        body,
    )


def _fake_fetch_be_html_no_marker(url, timeout=30):
    """200 OK + body without any of the four FR markers (e.g. cookie banner)."""
    body = (
        b"<!DOCTYPE html><html><head><title>Cookies</title></head>"
        b"<body><p>This site uses cookies.</p></body></html>"
    )
    return (url, 200, "text/html; charset=UTF-8", body)


def test_be_loi_registry_entry_is_present_and_valid():
    """Registry must declare BE Loi 1989 as fetch with FR primary URL,
    NL fallback and the four French markers."""
    registry_path = REPO_ROOT / "config" / "official_source_registry.json"
    payload = json.loads(registry_path.read_text(encoding="utf-8"))
    entry = next(
        (e for e in payload["entries"] if e["source_slug"] == BE_LOI_SLUG),
        None,
    )
    assert entry is not None, f"registry missing entry {BE_LOI_SLUG!r}"
    assert entry["country"] == "BE"
    assert entry["jurisdiction"] == "BE-NATIONAL"
    assert entry["case_type"] == "road_accident_bodily_injury"
    assert entry["source_kind"] == "official_law"
    assert entry["authority"] == "spf_economie"
    assert entry["machine_readable"] is True
    assert entry["expected_format"] == "html"
    assert entry["can_auto_ingest"] is True
    assert entry["human_exception_review_required"] is False
    assert entry["ingest_mode"] == "fetch"
    assert "/fr/" in entry["official_url"], entry["official_url"]
    alts = entry.get("fetch_url_alternatives") or []
    assert any("/nl/" in u for u in alts), alts
    markers = entry.get("content_must_contain") or []
    for required in (
        "21 novembre 1989",
        "responsabilité",
        "véhicules automoteurs",
        "assurance obligatoire",
    ):
        assert required in markers, f"missing marker {required!r} in {markers!r}"


@pytest.mark.django_db
def test_be_loi_html_fetch_success_writes_sha256_and_notes(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_be_loi_html,
    ):
        call_command("sync_official_sources", "--country", "BE", "--slug", BE_LOI_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=BE_LOI_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_success"
    assert block["http_status"] == 200
    assert block["ingest_mode"] == "fetch"
    assert block["source_kind"] == "official_law"
    assert block["authority"] == "spf_economie"
    assert block["local_path"].endswith(".html")
    assert block["no_calculator_activation"] is True
    assert block["error"] == ""
    assert len(block["sha256"]) == 64

    repo_local = Path(settings.BASE_DIR) / block["local_path"]
    assert repo_local.exists()
    body = repo_local.read_bytes()
    assert b"21 novembre 1989" in body or b"21 NOVEMBRE 1989" in body
    assert b"automoteurs" in body


@pytest.mark.django_db
def test_be_loi_content_type_html_produces_html_extension(tmp_path, settings):
    """Content-Type=text/html → local file saved with `.html` extension."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_be_loi_html,
    ):
        call_command("sync_official_sources", "--country", "BE", "--slug", BE_LOI_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=BE_LOI_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["local_path"].endswith(".html"), block["local_path"]


@pytest.mark.django_db
def test_be_loi_marker_missing_produces_fetch_failed(tmp_path, settings):
    """All candidate URLs return bodies without any required marker →
    classification fetch_failed (BE entry uses fetch mode, not
    verify_existing, so no crosscheck_failed label)."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_be_html_no_marker,
    ):
        call_command("sync_official_sources", "--country", "BE", "--slug", BE_LOI_SLUG, stdout=out)

    src = LegalSource.objects.get(slug=BE_LOI_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert block["sha256"] == ""
    assert block["local_path"] == ""
    assert "missing required content markers" in block["error"]


@pytest.mark.django_db
def test_be_loi_idempotent_replaces_block(tmp_path, settings):
    """Re-run BE fetch with a different mock payload → still a single
    [official_sync] block, sha256 reflects the latest body."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    out1 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_be_loi_html,
    ):
        call_command("sync_official_sources", "--country", "BE", "--slug", BE_LOI_SLUG, stdout=out1)
    src = LegalSource.objects.get(slug=BE_LOI_SLUG)
    first = _extract_official_sync_block(src.notes)

    def _fake_be_html_v2(url, timeout=30):
        body = (
            b"<!DOCTYPE html><html><body>"
            b"<h1>Loi du 21 novembre 1989 - revision</h1>"
            b"<p>responsabilit\xc3\xa9, v\xc3\xa9hicules automoteurs, "
            b"assurance obligatoire, body updated</p>"
            b"</body></html>"
        )
        return (
            "https://economie.fgov.be/fr/legislation/loi-du-21-novembre-1989",
            200,
            "text/html",
            body,
        )

    out2 = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_be_html_v2,
    ):
        call_command("sync_official_sources", "--country", "BE", "--slug", BE_LOI_SLUG, stdout=out2)
    src.refresh_from_db()
    assert src.notes.count(NOTES_MARKER_BEGIN) == 1
    assert src.notes.count(NOTES_MARKER_END) == 1
    second = _extract_official_sync_block(src.notes)
    assert first["sha256"] != second["sha256"]


@pytest.mark.django_db
def test_be_calculator_remains_unavailable_after_fetch(tmp_path, settings):
    """Fetching the BE Loi 1989 must NOT promote the BE road_accident
    calculator out of unavailable_requires_legal_validation: there is no
    approved tabular dataset, only court_indicative_table fonti."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_be_loi_html,
    ):
        call_command("sync_official_sources", "--country", "BE", "--slug", BE_LOI_SLUG, stdout=out)

    sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


@pytest.mark.django_db
def test_be_fetch_failure_does_not_create_legal_layer(tmp_path, settings):
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
        call_command("sync_official_sources", "--country", "BE", "--slug", BE_LOI_SLUG, stdout=out)

    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before

    src = LegalSource.objects.get(slug=BE_LOI_SLUG)
    block = _extract_official_sync_block(src.notes)
    assert block["classification"] == "fetch_failed"
    assert "fetch_failed: ConnectionError" in block["error"]
    assert block["http_status"] is None
    assert block["sha256"] == ""


@pytest.fixture
def italy_smoke_be_fetch(db):
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
        slug="it-dpr-12-2025-tun-be-fetch",
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
        code="italy_art_138_tun_2025_be_fetch_smoke",
        name="be-fetch-smoke",
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
def test_italy_smoke_unchanged_after_be_fetch(italy_smoke_be_fetch, tmp_path, settings):
    """Italia 35/10/0 → 26268/27353/28439 EUR resta invariata anche dopo
    una run di fetch della Loi BE 1989."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    out = StringIO()
    with patch(
        "apps.legal_sources.management.commands.sync_official_sources._fetch",
        side_effect=_fake_fetch_be_loi_html,
    ):
        call_command("sync_official_sources", "--country", "BE", "--slug", BE_LOI_SLUG, stdout=out)

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
