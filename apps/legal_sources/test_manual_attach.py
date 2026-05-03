"""Tests F-official-source-manual-attach-pipeline.

Cover the new ``attach_official_source_file`` management command for
sources that cannot be auto-fetched (Légifrance HTTP 403, anti-bot WAFs,
JS-only SPAs). The command must:

1. Refuse if the registry slug doesn't set ``manual_attach_allowed=true``.
2. Compute sha256 + size_bytes of the supplied file.
3. Run the same ``content_must_contain`` marker check the auto-fetch
   pipeline uses (raw bytes + pdfplumber PDF fallback).
4. Copy the file into ``legal_data/sources/<country>/manual_attached/``.
5. Write a ``[manual_attach] BEGIN…END`` block in ``LegalSource.notes``
   that **coexists** with any prior ``[official_sync]`` block.
6. Append to a cumulative ``manual_attach_manifest.json`` per country.
7. Never create LegalReview / CompensationDataset / CalculationFormula /
   CompensationTableRow.
8. Never promote ``LegalSource.status`` to ``APPROVED``.
9. Leave Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR untouched.
"""

from __future__ import annotations

import json
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.legal_sources.management.commands.attach_official_source_file import (
    NOTES_MARKER_BEGIN as MA_BEGIN,
)
from apps.legal_sources.management.commands.attach_official_source_file import (
    NOTES_MARKER_END as MA_END,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "config" / "official_source_registry.json"
BADINTER_SLUG = "fr-loi-badinter-1985"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_manual_attach_block(notes: str) -> dict:
    payload = notes.split(MA_BEGIN, 1)[1].split(MA_END)[0]
    return json.loads(payload.strip())


def _write_html_with_markers(tmp_path: Path) -> Path:
    """Synthetic Badinter HTML body that hits all four FR markers."""
    body = (
        b'<!DOCTYPE html><html lang="fr"><head>'
        b"<title>Loi du 5 juillet 1985 - Loi Badinter</title></head>"
        b"<body><h1>Loi n\xc2\xb085-677 du 5 juillet 1985</h1>"
        b"<p>Tendant \xc3\xa0 l'am\xc3\xa9lioration de la situation des "
        b"victimes d'accidents de la circulation et \xc3\xa0 "
        b"l'acc\xc3\xa9l\xc3\xa9ration des proc\xc3\xa9dures "
        b"d'indemnisation.</p></body></html>"
    )
    f = tmp_path / "badinter-consolidee.html"
    f.write_bytes(body)
    return f


def _write_pdf_with_markers(tmp_path: Path) -> Path:
    """Synthetic PDF body that hits markers in raw bytes (no pdfplumber
    fallback needed for marker check). The PDF magic bytes also exercise
    the PDF detection branch in ``_markers_present``."""
    body = (
        b"%PDF-1.4\n"
        b"% Synthetic Badinter test payload\n"
        b"Loi n.85-677 du 5 juillet 1985\n"
        b"victimes d'accidents de la circulation\n"
        b"indemnisation\n" + b"x" * 400
    )
    f = tmp_path / "badinter-consolidee.pdf"
    f.write_bytes(body)
    return f


def _write_html_without_markers(tmp_path: Path) -> Path:
    """200 OK + body without any of the four FR markers."""
    body = (
        b"<!DOCTYPE html><html><head><title>Cookies</title></head>"
        b"<body><p>This site uses cookies.</p></body></html>"
    )
    f = tmp_path / "wrong-document.html"
    f.write_bytes(body)
    return f


def _override_registry(tmp_path: Path, mutate) -> Path:
    """Write a registry copy with ``mutate`` applied to the entries list."""
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    mutate(payload["entries"])
    out = tmp_path / "registry_override.json"
    out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# 1 — registry entry validity
# ---------------------------------------------------------------------------


def test_badinter_registry_entry_allows_manual_attach():
    """The committed registry must declare Badinter with
    ``manual_attach_allowed=true`` and the four FR markers."""
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    entry = next(
        (e for e in payload["entries"] if e["source_slug"] == BADINTER_SLUG),
        None,
    )
    assert entry is not None
    assert entry["country"] == "FR"
    assert entry["jurisdiction"] == "FR-NATIONAL"
    assert entry["case_type"] == "road_accident_bodily_injury"
    assert entry["source_kind"] == "official_law"
    assert entry["authority"] == "legifrance"
    assert entry["can_auto_ingest"] is False
    assert entry["human_exception_review_required"] is True
    assert entry["ingest_mode"] == "manual_attach"
    assert entry.get("manual_attach_allowed") is True
    assert entry.get("no_calculator_activation") is True
    markers = entry.get("content_must_contain") or []
    for required in (
        "5 juillet 1985",
        "accidents de la circulation",
        "indemnisation",
        "victimes",
    ):
        assert required in markers, markers


# ---------------------------------------------------------------------------
# 2 — attach HTML success writes manifest + notes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_manual_attach_html_success_writes_manifest_and_notes(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    src_file = _write_html_with_markers(tmp_path)
    out = StringIO()
    call_command(
        "attach_official_source_file",
        "--slug",
        BADINTER_SLUG,
        "--file",
        str(src_file),
        stdout=out,
    )

    src = LegalSource.objects.get(slug=BADINTER_SLUG)
    block = _extract_manual_attach_block(src.notes)
    assert block["classification"] == "manual_attach_success"
    assert block["registry_slug"] == BADINTER_SLUG
    assert block["source_kind"] == "official_law"
    assert block["authority"] == "legifrance"
    assert block["marker_check_passed"] is True
    assert block["no_calculator_activation"] is True
    assert block["no_dataset_creation"] is True
    assert block["error"] == ""
    assert len(block["sha256"]) == 64
    assert block["size_bytes"] == src_file.stat().st_size
    assert block["local_path"].endswith(".html")

    repo_local = Path(settings.BASE_DIR) / block["local_path"]
    assert repo_local.exists()
    assert b"5 juillet 1985" in repo_local.read_bytes()

    # Per-country cumulative manifest contains exactly one entry for this slug.
    manifest_path = repo_local.parent / "manual_attach_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    badinter_results = [r for r in manifest["results"] if r["slug"] == BADINTER_SLUG]
    assert len(badinter_results) == 1
    assert badinter_results[0]["sha256"] == block["sha256"]


# ---------------------------------------------------------------------------
# 3 — attach PDF success
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_manual_attach_pdf_success(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    src_file = _write_pdf_with_markers(tmp_path)
    out = StringIO()
    call_command(
        "attach_official_source_file",
        "--slug",
        BADINTER_SLUG,
        "--file",
        str(src_file),
        stdout=out,
    )

    src = LegalSource.objects.get(slug=BADINTER_SLUG)
    block = _extract_manual_attach_block(src.notes)
    assert block["classification"] == "manual_attach_success"
    assert block["local_path"].endswith(".pdf")
    assert block["marker_check_passed"] is True

    repo_local = Path(settings.BASE_DIR) / block["local_path"]
    assert repo_local.exists()
    assert repo_local.read_bytes()[:5] == b"%PDF-"


# ---------------------------------------------------------------------------
# 4 — marker missing → CommandError, no file copy, no notes write
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_manual_attach_marker_missing_raises_and_skips_persistence(tmp_path, settings):
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

    # Snapshot any pre-existing on-disk artefact left by other tests in
    # the same session — the command writes inside the real BASE_DIR so
    # this is the only way to prove the failed call did not mutate it.
    dest_path = (
        Path(settings.BASE_DIR)
        / "legal_data"
        / "sources"
        / "france"
        / "manual_attached"
        / f"{BADINTER_SLUG}.html"
    )
    pre_bytes = dest_path.read_bytes() if dest_path.exists() else None

    src_file = _write_html_without_markers(tmp_path)
    with pytest.raises(CommandError, match="manual_attach_marker_failed"):
        call_command(
            "attach_official_source_file",
            "--slug",
            BADINTER_SLUG,
            "--file",
            str(src_file),
        )

    # No legal-layer write.
    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before

    # The destination either still doesn't exist (clean session) or
    # still has the same bytes as before (no overwrite from this run).
    if pre_bytes is None:
        assert not dest_path.exists(), "marker_failed run must not create the destination file"
    else:
        assert dest_path.exists()
        assert (
            dest_path.read_bytes() == pre_bytes
        ), "marker_failed run must not overwrite the destination file"

    # No LegalSource notes block was written by this call (the row may
    # or may not exist depending on prior tests, but if it does its notes
    # must not contain a manual_attach block from this run).
    src = LegalSource.objects.filter(slug=BADINTER_SLUG).first()
    if src is not None:
        assert MA_BEGIN not in (src.notes or ""), src.notes


# ---------------------------------------------------------------------------
# 5 — manual_attach_allowed=false rejects the call
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_manual_attach_rejected_when_not_allowed(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")

    def _flip(entries):
        for e in entries:
            if e["source_slug"] == BADINTER_SLUG:
                e["manual_attach_allowed"] = False

    override = _override_registry(tmp_path, _flip)
    src_file = _write_html_with_markers(tmp_path)

    with pytest.raises(CommandError, match="does not allow manual_attach"):
        call_command(
            "attach_official_source_file",
            "--slug",
            BADINTER_SLUG,
            "--file",
            str(src_file),
            "--registry",
            str(override),
        )


# ---------------------------------------------------------------------------
# 6 — idempotency: re-run replaces single block, doesn't duplicate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_manual_attach_idempotent_replaces_block(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.legal_sources.models import LegalSource

    f1 = _write_html_with_markers(tmp_path)
    out1 = StringIO()
    call_command(
        "attach_official_source_file",
        "--slug",
        BADINTER_SLUG,
        "--file",
        str(f1),
        stdout=out1,
    )
    src = LegalSource.objects.get(slug=BADINTER_SLUG)
    first = _extract_manual_attach_block(src.notes)

    # Different body → different sha256.
    f2 = tmp_path / "badinter-v2.html"
    f2.write_bytes(
        b"<html><body>"
        b"Loi du 5 juillet 1985 - victimes d'accidents de la circulation - "
        b"indemnisation - revision 2"
        b"</body></html>"
    )
    out2 = StringIO()
    call_command(
        "attach_official_source_file",
        "--slug",
        BADINTER_SLUG,
        "--file",
        str(f2),
        stdout=out2,
    )
    src.refresh_from_db()
    assert src.notes.count(MA_BEGIN) == 1, "manual_attach block duplicated"
    assert src.notes.count(MA_END) == 1
    second = _extract_manual_attach_block(src.notes)
    assert first["sha256"] != second["sha256"]


# ---------------------------------------------------------------------------
# 7 — no LegalReview / Dataset / Formula / Rows created
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_manual_attach_does_not_create_legal_layer(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
    )
    from apps.legal_sources.models import LegalReview

    review_before = LegalReview.objects.count()
    dataset_before = CompensationDataset.objects.count()
    formula_before = CalculationFormula.objects.count()
    rows_before = CompensationTableRow.objects.count()

    src_file = _write_html_with_markers(tmp_path)
    out = StringIO()
    call_command(
        "attach_official_source_file",
        "--slug",
        BADINTER_SLUG,
        "--file",
        str(src_file),
        stdout=out,
    )

    assert LegalReview.objects.count() == review_before
    assert CompensationDataset.objects.count() == dataset_before
    assert CalculationFormula.objects.count() == formula_before
    assert CompensationTableRow.objects.count() == rows_before


# ---------------------------------------------------------------------------
# 8 — FR calculator stays unavailable after manual attach
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_calculator_remains_unavailable_after_manual_attach(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    src_file = _write_html_with_markers(tmp_path)
    out = StringIO()
    call_command(
        "attach_official_source_file",
        "--slug",
        BADINTER_SLUG,
        "--file",
        str(src_file),
        stdout=out,
    )

    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={},
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 9 — Italia 35/10/0 invariata sotto la run di manual_attach
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_manual_attach(db):
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
        slug="it-dpr-12-2025-tun-manual-attach",
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
        code="italy_art_138_tun_2025_manual_attach_smoke",
        name="manual-attach-smoke",
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
def test_italy_smoke_unchanged_after_manual_attach(italy_smoke_manual_attach, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    src_file = _write_html_with_markers(tmp_path)
    out = StringIO()
    call_command(
        "attach_official_source_file",
        "--slug",
        BADINTER_SLUG,
        "--file",
        str(src_file),
        stdout=out,
    )

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
# 10 — coexistence with [official_sync] block (regression check)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_manual_attach_block_preserves_official_sync_block(tmp_path, settings):
    """Pre-seed a LegalSource with an [official_sync] block, then run
    manual attach: the new [manual_attach] block must coexist, and the
    [official_sync] block must remain untouched."""
    settings.MEDIA_ROOT = str(tmp_path / "media")
    from datetime import date

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    pre_existing = LegalSource.objects.create(
        slug=BADINTER_SLUG,
        title="Loi Badinter pre-existing",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(1985, 7, 5),
        effective_date=date(1986, 1, 1),
        notes=(
            "Existing free notes.\n\n"
            "[official_sync] BEGIN\n"
            '{"classification": "metadata_only", "registry_slug": "fr-loi-badinter-1985"}\n'
            "[official_sync] END\n"
        ),
    )

    src_file = _write_html_with_markers(tmp_path)
    out = StringIO()
    call_command(
        "attach_official_source_file",
        "--slug",
        BADINTER_SLUG,
        "--file",
        str(src_file),
        stdout=out,
    )

    pre_existing.refresh_from_db()
    # Both blocks present, exactly once each.
    assert pre_existing.notes.count("[official_sync] BEGIN") == 1
    assert pre_existing.notes.count("[official_sync] END") == 1
    assert pre_existing.notes.count(MA_BEGIN) == 1
    assert pre_existing.notes.count(MA_END) == 1
    # Status preserved (no APPROVED promotion).
    assert pre_existing.status == SourceStatus.NEEDS_REVIEW
