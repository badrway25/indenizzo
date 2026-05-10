"""Tests F-france-activation-readiness-audit.

Cover the read-only audit script
``scripts/legal_data/audit_france_activation_readiness.py``:

1. Script importable + ``main()`` runs without raising.
2. Markdown report written at the expected path.
3. Report says Badinter "verified" / PASS when the manual_attach +
   official_source_validation blocks exist on the LegalSource.
4. Report says Mornet / Gazette BLOCKED while their LegalSources are
   ``needs_review``.
5. Report says FR ``CalculationFormula`` count is 0.
6. Report says FR calculator stays ``unavailable`` (no GO verdict).
7. The audit makes no DB writes — the row counts of every relevant
   table are unchanged before/after.
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "legal_data" / "audit_france_activation_readiness.py"


@pytest.fixture(autouse=True)
def _redirect_audit_report_path(tmp_path, monkeypatch):
    """Redirect the audit script's REPORT_PATH to tmp_path.

    Without this, every test that calls ``module.main()`` writes the
    real ``docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md`` and
    leaves the working tree dirty (timestamp drift on each run). The
    script reads ``REPORT_PATH`` as a module global, so monkeypatching
    the attribute redirects all writes — both the ``mkdir`` at the start
    of ``write_report`` and the ``write_text`` at the end.
    """
    module = _load_audit_module()
    redirected = tmp_path / "FRANCE_ACTIVATION_READINESS_AUDIT.md"
    monkeypatch.setattr(module, "REPORT_PATH", redirected)
    yield redirected


def _load_audit_module():
    """Import the audit script as a module under a stable name. The script
    calls ``django.setup()`` at import time, which is fine because pytest-
    django has already set up Django by the time these tests run.

    The module must be registered in ``sys.modules`` *before* ``exec_module``
    runs: the ``@dataclass`` decorator inside the script resolves stringified
    type annotations against ``sys.modules.get(cls.__module__)`` (because
    ``from __future__ import annotations`` is in effect), and a None lookup
    there raises ``AttributeError``.
    """
    import sys

    module_name = "audit_france_activation_readiness"
    if module_name in sys.modules:
        return sys.modules[module_name]
    spec = importlib.util.spec_from_file_location(module_name, SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        # Roll back the registration so a partial import doesn't poison
        # subsequent tests.
        sys.modules.pop(module_name, None)
        raise
    return module


# ---------------------------------------------------------------------------
# Shared fixture: seed an FR pipeline state matching the post-import iter:
# Badinter with manual_attach + validation blocks, Mornet/Gazette
# needs_review with DRAFT datasets at the expected row counts.
# ---------------------------------------------------------------------------


@pytest.fixture
def fr_audit_baseline(db, settings, tmp_path):
    """Seed the minimum DB shape the audit expects."""
    settings.MEDIA_ROOT = str(tmp_path / "media")

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
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

    badinter = LegalSource.objects.create(
        slug="fr-loi-badinter-1985",
        title="Loi Badinter — fixture",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(1985, 7, 5),
        notes=(
            "free leading notes\n\n"
            "[manual_attach] BEGIN\n"
            '{"classification": "manual_attach_success", '
            '"sha256": "0000000000000000000000000000000000000000000000000000000000000000", '
            '"marker_check_passed": true}\n'
            "[manual_attach] END\n\n"
            "[official_source_validation] BEGIN\n"
            '{"official_source_validation": "passed", '
            '"structural_markers_passed": 11, '
            '"structural_markers_total": 11, '
            '"legal_calculator_activation": false}\n'
            "[official_source_validation] END\n"
        ),
    )
    mornet = LegalSource.objects.create(
        slug="fr-referentiel-mornet-2024",
        title="Mornet — fixture",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.DOCTRINE,
        reliability=Reliability.HIGH,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2024, 1, 1),
    )
    gazette = LegalSource.objects.create(
        slug="fr-bareme-capitalisation-gazette-palais-2022",
        title="Gazette — fixture",
        country=france,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.DOCTRINE,
        reliability=Reliability.HIGH,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2022, 1, 1),
    )

    mornet_ds = CompensationDataset.objects.create(
        source=mornet,
        jurisdiction=juris,
        country=france,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="FR Mornet 2024 (candidate, DRAFT)",
        version_label="FR-MORNET-2024-DRAFT",
        status=DatasetStatus.DRAFT,
    )
    gazette_ds = CompensationDataset.objects.create(
        source=gazette,
        jurisdiction=juris,
        country=france,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="FR Gazette du Palais 2022 (candidate, DRAFT)",
        version_label="FR-GAZETTE-PALAIS-2022-DRAFT",
        status=DatasetStatus.DRAFT,
    )

    # Seed the EXPECTED counts the audit asserts. We use synthetic rows
    # (no real Mornet/Gazette numbers) so this fixture cannot accidentally
    # leak production values.
    def _rows(dataset, row_type, count, *, base_age=0):
        for i in range(count):
            CompensationTableRow.objects.create(
                dataset=dataset,
                row_type=row_type,
                age_min=base_age + i,
                age_max=base_age + i,
                disability_min=1,
                disability_max=1,
                point_value=Decimal("1"),
                extra={"nat_key": f"synth_{row_type}_{i}"},
            )

    _rows(mornet_ds, "fr_dfp_per_age_disability_amount_per_point", 180)
    _rows(mornet_ds, "fr_prejudice_affection_per_relation_amount", 11)
    _rows(
        gazette_ds,
        "fr_capitalisation_viagere_per_age_sex_rate_coefficient",
        416,
    )
    _rows(
        gazette_ds,
        "fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient",
        3752,
    )
    _rows(
        gazette_ds,
        "fr_anticipated_payment_years_per_age_sex_rate_years",
        20,
    )
    return {
        "badinter": badinter,
        "mornet": mornet,
        "gazette": gazette,
        "mornet_ds": mornet_ds,
        "gazette_ds": gazette_ds,
    }


# ---------------------------------------------------------------------------
# 1 — script importable, main() runs without raising
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_script_runs_and_returns_zero(fr_audit_baseline, tmp_path, settings):
    module = _load_audit_module()
    rc = module.main()
    assert rc == 0


# ---------------------------------------------------------------------------
# 2 — markdown report written
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_writes_markdown_report(fr_audit_baseline, _redirect_audit_report_path):
    module = _load_audit_module()
    module.main()
    redirected = _redirect_audit_report_path
    assert redirected.exists()
    body = redirected.read_text(encoding="utf-8")
    # Section markers (12 sections per the iter spec).
    for section in (
        "Executive summary",
        "Current status",
        "Sources",
        "Candidate datasets",
        "Engine",
        "Formula status",
        "Wizard",
        "Activation blockers",
        "Safe activation paths",
        "What must NOT happen",
        "Rollback plan",
        "Next tasks",
    ):
        assert section in body, section


# ---------------------------------------------------------------------------
# 3 — report flags Badinter as PASS when both blocks are present
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_reports_badinter_verified(fr_audit_baseline):
    module = _load_audit_module()
    report = module.AuditReport(generated_at="test", sources=module.audit_sources())
    badinter_row = next(r for r in report.sources if r.label.startswith("Badinter"))
    assert badinter_row.status == "PASS"
    assert "manual_attach_block=present" in badinter_row.details
    assert "official_source_validation_block=present" in badinter_row.details
    assert "structural_markers=11/11" in badinter_row.details


# ---------------------------------------------------------------------------
# 4 — report flags Mornet / Gazette as BLOCKED while needs_review
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_reports_mornet_and_gazette_blocked(fr_audit_baseline):
    module = _load_audit_module()
    rows = module.audit_sources()
    mornet_row = next(r for r in rows if "mornet" in r.label.lower())
    gazette_row = next(r for r in rows if "gazette" in r.label.lower())
    assert mornet_row.status == "BLOCKED"
    assert gazette_row.status == "BLOCKED"
    assert "status=needs_review" in mornet_row.details
    assert "status=needs_review" in gazette_row.details


# ---------------------------------------------------------------------------
# 5 — report says FR CalculationFormula count is 0
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_reports_zero_fr_formulas(fr_audit_baseline):
    module = _load_audit_module()
    rows = module.audit_formulas()
    assert len(rows) == 1
    formula_row = rows[0]
    assert formula_row.status == "PASS"
    assert "count=0" in formula_row.details


# ---------------------------------------------------------------------------
# 6 — verdict is NOT a GO; FR calculator stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_verdict_is_not_go_when_quantification_blocked(fr_audit_baseline):
    module = _load_audit_module()
    report = module.AuditReport(generated_at="test")
    report.sources = module.audit_sources()
    report.datasets = module.audit_datasets()
    report.formula = module.audit_formulas()
    report.engine = module.audit_engine()
    report.wizard = []  # skip wizard for this assertion
    report.overall_status, report.overall_summary = module._compute_verdict(report)
    # Mornet/Gazette BLOCKED + Badinter PASS → OFFICIAL-ONLY (or NO-GO if
    # Badinter weren't present). Both verdicts must NOT be a green light.
    assert report.overall_status in {"OFFICIAL-ONLY", "NO-GO"}
    assert report.overall_status != "GO"
    assert report.overall_status != "INDICATIVE-READY"


# ---------------------------------------------------------------------------
# 7 — audit makes no DB writes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_audit_does_not_write_to_db(fr_audit_baseline):
    from apps.cases.models import Simulation
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        ExtractionLog,
    )
    from apps.legal_sources.models import LegalReview, LegalSource

    counts_before = {
        "LegalSource": LegalSource.objects.count(),
        "LegalReview": LegalReview.objects.count(),
        "CompensationDataset": CompensationDataset.objects.count(),
        "CompensationTableRow": CompensationTableRow.objects.count(),
        "CalculationFormula": CalculationFormula.objects.count(),
        "ExtractionLog": ExtractionLog.objects.count(),
        "Simulation": Simulation.objects.count(),
    }

    module = _load_audit_module()
    module.main()

    counts_after = {
        "LegalSource": LegalSource.objects.count(),
        "LegalReview": LegalReview.objects.count(),
        "CompensationDataset": CompensationDataset.objects.count(),
        "CompensationTableRow": CompensationTableRow.objects.count(),
        "CalculationFormula": CalculationFormula.objects.count(),
        "ExtractionLog": ExtractionLog.objects.count(),
        "Simulation": Simulation.objects.count(),
    }
    assert counts_before == counts_after, (counts_before, counts_after)


# ---------------------------------------------------------------------------
# 8 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_audit(db, fr_audit_baseline):
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
    Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-fixture-audit-readiness",
        title="D.P.R. 12/2025 fixture",
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
        code="italy_art_138_tun_2025_audit_smoke",
        name="audit-smoke",
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
    return {"italy": italy}


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_audit(italy_smoke_audit):
    """Run the audit then check Italia 35/10/0 still computes."""
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    module = _load_audit_module()
    module.main()  # the audit itself

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
