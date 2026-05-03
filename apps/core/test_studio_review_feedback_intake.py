"""
Tests F-product-studio-review-feedback-intake.

Coprono il validatore + report generator per la checklist Studio
review (vedi `scripts/parse_public_site_review_feedback.py`):

1. Il template originale (96 righe pending) supera lo schema.
2. Un CSV con `status` non ammesso fallisce.
3. `change_requested` senza `notes` fallisce.
4. `approved` con reviewer + reviewed_at popolati supera la
   validazione e produce il counter atteso.
5. Il report markdown viene generato con le sezioni canoniche.
6. I NO-GO ancora aperti vengono elencati nella sezione 7 del
   report.
7. La pipeline non fa scrittura sul DB (no `Simulation`,
   `LegalSource`, `Lead` creati durante il parse).
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR (smoke engine,
   contratto storico).
"""

from __future__ import annotations

import csv
import sys
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"
TEMPLATE_PATH = REPO_ROOT / "legal_data" / "review" / "public_site_review_checklist_template.csv"
EXAMPLE_PATH = REPO_ROOT / "docs" / "review" / "public_site_review_checklist_example_filled.csv"

if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import parse_public_site_review_feedback as feedback  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


HEADER = feedback.REQUIRED_HEADER


def _write_csv(tmp_path: Path, rows: list[dict]) -> Path:
    csv_path = tmp_path / "checklist.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=HEADER)
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in HEADER})
    return csv_path


def _row(**overrides: str) -> dict:
    base = {
        "area": "home",
        "page_url": "/",
        "language": "it",
        "review_item": "Hero copy",
        "current_status": "delivered_pass1",
        "reviewer": "",
        "status": "pending",
        "notes": "",
        "reviewed_at": "",
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# 1 — original template (96 rows, all pending) passes the schema
# ---------------------------------------------------------------------------


def test_template_passes_schema():
    assert TEMPLATE_PATH.exists(), TEMPLATE_PATH
    report = feedback.parse_csv(TEMPLATE_PATH)
    assert report.violations == []
    assert len(report.rows) >= 50
    assert report.counts_by_status.get("pending", 0) == len(report.rows)


# ---------------------------------------------------------------------------
# 2 — invalid `status` token fails
# ---------------------------------------------------------------------------


def test_invalid_status_fails(tmp_path):
    csv_path = _write_csv(tmp_path, [_row(status="banana")])
    report = feedback.parse_csv(csv_path)
    assert any("status='banana'" in v for v in report.violations), report.violations


# ---------------------------------------------------------------------------
# 3 — change_requested without notes fails
# ---------------------------------------------------------------------------


def test_change_requested_without_notes_fails(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                status="change_requested",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="",
            )
        ],
    )
    report = feedback.parse_csv(csv_path)
    assert any("notes empty" in v for v in report.violations), report.violations


def test_rejected_without_notes_fails(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                status="rejected",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="",
            )
        ],
    )
    report = feedback.parse_csv(csv_path)
    assert any("notes empty" in v for v in report.violations), report.violations


# ---------------------------------------------------------------------------
# 4 — approved with reviewer/reviewed_at passes; counters work
# ---------------------------------------------------------------------------


def test_approved_row_passes_and_counts(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                status="approved",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="copy ok",
            )
        ],
    )
    report = feedback.parse_csv(csv_path)
    assert report.violations == [], report.violations
    assert report.counts_by_status["approved"] == 1
    assert report.counts_by_status.get("pending", 0) == 0


def test_approved_without_reviewer_fails(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [_row(status="approved", reviewer="", reviewed_at="2026-05-03")],
    )
    report = feedback.parse_csv(csv_path)
    assert any("reviewer empty" in v for v in report.violations), report.violations


def test_approved_without_reviewed_at_fails(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [_row(status="approved", reviewer="Avv. QA", reviewed_at="")],
    )
    report = feedback.parse_csv(csv_path)
    assert any("reviewed_at empty" in v for v in report.violations), report.violations


def test_invalid_language_fails(tmp_path):
    csv_path = _write_csv(tmp_path, [_row(language="zh")])
    report = feedback.parse_csv(csv_path)
    assert any("language='zh'" in v for v in report.violations), report.violations


def test_missing_page_url_fails(tmp_path):
    csv_path = _write_csv(tmp_path, [_row(page_url="")])
    report = feedback.parse_csv(csv_path)
    assert any("empty `page_url`" in v for v in report.violations), report.violations


# ---------------------------------------------------------------------------
# 5 — markdown summary is generated with canonical sections
# ---------------------------------------------------------------------------


def test_summary_markdown_contains_canonical_sections(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                status="approved",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="ok",
            ),
            _row(
                status="change_requested",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="riscrivere claim",
                area="country_landing",
                page_url="/countries/france/",
                language="fr",
                review_item="Disclaimer FR",
            ),
        ],
    )
    report = feedback.parse_csv(csv_path)
    md = feedback.render_summary_markdown(csv_path, report)
    for header in (
        "# Public site Studio review — feedback summary",
        "## 1. Executive summary",
        "## 2. Counts per status",
        "## 3. Approved items",
        "## 4. Change requested items",
        "## 5. Rejected items",
        "## 6. Pending items",
        "## 7. NO-GO ancora aperti",
        "## 8. Task tecnici proposti (NON applicati)",
        "## 9. Cosa resta bloccato",
    ):
        assert header in md, f"missing markdown section header: {header!r}"


def test_summary_markdown_lists_change_requested_notes(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                status="change_requested",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="aggiungere riga 'non parere medico-legale'",
                area="wizard_italy",
                page_url="/wizard/it/road-accident/",
                language="it",
                review_item="Banner importante",
            )
        ],
    )
    report = feedback.parse_csv(csv_path)
    md = feedback.render_summary_markdown(csv_path, report)
    assert "non parere medico-legale" in md
    assert "wizard_italy" in md


# ---------------------------------------------------------------------------
# 6 — NO-GO open items are listed
# ---------------------------------------------------------------------------


def test_no_go_marked_open_when_no_related_rows(tmp_path):
    csv_path = _write_csv(tmp_path, [_row(status="pending")])
    report = feedback.parse_csv(csv_path)
    no_go_ids = {entry["id"] for entry in report.no_go_open}
    # All 5 NO-GO definitions must be flagged as open when no related row covers them.
    for nogo_id in (
        "ar_translations_native_review",
        "under_review_countries_appearance",
        "pexels_country_images_approval",
        "disclaimer_privacy_signoff",
        "cookie_banner_confirmation",
    ):
        assert nogo_id in no_go_ids, f"NO-GO {nogo_id} missing from open list"


def test_no_go_resolves_when_all_related_approved(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                area="cookie",
                page_url="/",
                language="it",
                review_item="Cookie banner",
                status="approved",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="ok",
            )
        ],
    )
    report = feedback.parse_csv(csv_path)
    resolved_ids = {entry["id"] for entry in report.no_go_resolved}
    assert "cookie_banner_confirmation" in resolved_ids
    open_ids = {entry["id"] for entry in report.no_go_open}
    assert "cookie_banner_confirmation" not in open_ids


def test_proposed_tech_tasks_for_change_requested(tmp_path):
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                area="country_landing",
                page_url="/countries/france/",
                language="fr",
                review_item="Disclaimer FR",
                status="change_requested",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="rendere piu esplicito",
            )
        ],
    )
    report = feedback.parse_csv(csv_path)
    assert len(report.proposed_tech_tasks) == 1
    proposal = report.proposed_tech_tasks[0]
    assert "templates/public/country_landing.html" in proposal["suggested_files"]
    assert "Conferma" in proposal["confirm_with_studio"]


def test_example_filled_csv_passes_schema():
    """The committed example CSV must always be schema-valid even
    though it is marked as non-binding."""
    assert EXAMPLE_PATH.exists(), EXAMPLE_PATH
    report = feedback.parse_csv(EXAMPLE_PATH)
    assert report.violations == [], report.violations
    # And it must contain at least one approved + one change_requested
    # so the documentation reads naturally.
    assert report.counts_by_status.get("approved", 0) >= 1
    assert report.counts_by_status.get("change_requested", 0) >= 1


# ---------------------------------------------------------------------------
# 7 — pipeline does not write to DB
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_parse_does_not_create_db_records(tmp_path):
    from apps.cases.models import Simulation
    from apps.crm.models import Lead
    from apps.legal_sources.models import LegalReview, LegalSource

    before = (
        Simulation.objects.count(),
        Lead.objects.count(),
        LegalSource.objects.count(),
        LegalReview.objects.count(),
    )
    csv_path = _write_csv(
        tmp_path,
        [
            _row(
                status="approved",
                reviewer="Avv. QA",
                reviewed_at="2026-05-03",
                notes="ok",
            )
        ],
    )
    feedback.parse_csv(csv_path)
    after = (
        Simulation.objects.count(),
        Lead.objects.count(),
        LegalSource.objects.count(),
        LegalReview.objects.count(),
    )
    assert before == after, f"DB record drift: {before} -> {after}"


# ---------------------------------------------------------------------------
# 8 — Italy 35/10/0 contract preserved (engine smoke)
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_feedback_intake(db):
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
        slug="it-dpr-12-2025-tun-feedback-intake",
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
        code="italy_art_138_tun_2025_feedback_intake",
        name="feedback-intake-smoke",
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
def test_italy_smoke_unchanged_under_feedback_intake(italy_smoke_feedback_intake):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

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
