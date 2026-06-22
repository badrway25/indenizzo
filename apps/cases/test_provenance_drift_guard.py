"""H1-8.2: CI drift guard for calculation provenance.

This file is the CI guard target (run as a dedicated step). It exercises the
REAL ``verify_calculation_provenance`` command, fail-closed:

- the IT canary (35/10/0 → 26 268 / 27 353 / 28 439) reproduces against the
  canonical approved data → ``--canary --fail-on-drift`` does NOT exit non-zero;
- a tampered legal-data scenario is caught → ``--fail-on-drift`` exits non-zero;
- on an empty DB the canary cannot reproduce → it fails (documents why a raw
  real-DB ``--canary`` shell step would be fragile, hence the fixture-seeded
  guard).

The data is seeded by a fixture (synthetic, rolled back) — never a real-DB
approval and never a gitignored ``legal_data`` file, so the guard is
deterministic and not flaky.
"""

from __future__ import annotations

import io
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.calculators.enums import CaseType
from apps.cases.services import run_simulation
from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
)
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource, LegalSourceVersion

ROAD = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
_PARAMS = {
    "engine": "italy_tun_point_value_v1",
    "requires": ["victim_age", "permanent_disability_percentage"],
    "row_match": ["victim_age", "permanent_disability_percentage"],
    "amount_rule": "row_amount_range_direct",
    "fault_reduction": True,
    "range_dataset_version_label": "DPR-12-2025-MORAL",
    "min_row_type": "min",
    "mid_row_type": "mid",
    "max_row_type": "max",
}


@pytest.fixture
def canary_stack(db):
    """Seed the calculation-ready IT stack so the canary (35/10/0) reproduces.

    Synthetic test data: created inside the test transaction and rolled back.
    NOT a real-DB approval and NOT a gitignored legal_data file.
    """
    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    lang = Language.objects.create(code="it", name="Italiano")
    jur = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-guard",
        title="DPR test",
        country=italy,
        jurisdiction=jur,
        language=lang,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 2, 26),
    )
    ver = LegalSourceVersion.objects.create(
        source=src,
        version_label="DPR-12-2025",
        content_hash="74d4d4f7guardhash",
    )
    base = CompensationDataset.objects.create(
        source=src,
        source_version=ver,
        jurisdiction=jur,
        country=italy,
        case_type=ROAD,
        name="base",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
    )
    CompensationTableRow.objects.create(
        dataset=base,
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    CalculationFormula.objects.create(
        dataset=base,
        code="italy_art_138",
        name="f",
        status=DatasetStatus.APPROVED,
        parameters=_PARAMS,
    )
    moral = CompensationDataset.objects.create(
        source=src,
        source_version=ver,
        jurisdiction=jur,
        country=italy,
        case_type=ROAD,
        name="moral",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
    )
    rows = {}
    for rt, val in (("min", 26268), ("mid", 27353), ("max", 28439)):
        rows[rt] = CompensationTableRow.objects.create(
            dataset=moral,
            row_type=rt,
            age_min=35,
            age_max=35,
            disability_min=10,
            disability_max=10,
            point_value=Decimal(val),
        )
    return {"ver": ver, "rows": rows}


@pytest.mark.django_db
def test_canary_guard_passes_when_reproducible(canary_stack):
    """The CI guard's core assertion: --canary --fail-on-drift must NOT fail."""
    # Should not raise SystemExit.
    call_command(
        "verify_calculation_provenance", "--canary", "--fail-on-drift", stdout=io.StringIO()
    )


@pytest.mark.django_db
def test_guard_detects_drift_on_tampered_data(canary_stack):
    """A tampered source hash must make --fail-on-drift exit non-zero."""
    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=ROAD,
        input_data={"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0},
    )
    assert sim.status == "calculated"
    canary_stack["ver"].content_hash = "TAMPERED"
    canary_stack["ver"].save(update_fields=["content_hash"])
    with pytest.raises(SystemExit) as exc:
        call_command(
            "verify_calculation_provenance",
            "--all-calculated",
            "--fail-on-drift",
            stdout=io.StringIO(),
        )
    assert exc.value.code != 0


@pytest.mark.django_db
def test_guard_canary_fails_on_empty_db(db):
    """Documents the fragility a raw real-DB --canary step would have: with no
    approved IT data the canary cannot reproduce, so --fail-on-drift fails.
    This is why the CI guard seeds via fixture rather than scanning the CI DB."""
    with pytest.raises(SystemExit):
        call_command(
            "verify_calculation_provenance", "--canary", "--fail-on-drift", stdout=io.StringIO()
        )
