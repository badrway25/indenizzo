"""H1-8: calculation provenance for audited simulations.

Verifies that a CALCULATED simulation records a deterministic, PII-safe
provenance snapshot (dataset version, source version + content hash, formula
params hash, matched-row value hashes), that the snapshot is honest when a
source version is absent (never faked), that non-calculated simulations carry no
provenance, that historical simulations (empty provenance) still render, and
that the IT canary is unchanged.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators.enums import CalculationStatus, CaseType
from apps.cases.models import Simulation
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
from apps.reports.pdf_renderer import render_simulation_pdf_bytes

ROAD = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value
_FORMULA_PARAMS = {
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


def _setup(*, with_source_version: bool) -> dict:
    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    lang = Language.objects.create(code="it", name="Italiano")
    jur = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-prov-test",
        title="D.P.R. 12/2025 (test)",
        country=italy,
        jurisdiction=jur,
        language=lang,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 2, 26),
    )
    version = None
    if with_source_version:
        version = LegalSourceVersion.objects.create(
            source=src,
            version_label="DPR-12-2025",
            content_hash="74d4d4f7b4154694deadbeef",
        )
    base = CompensationDataset.objects.create(
        source=src,
        source_version=version,
        jurisdiction=jur,
        country=italy,
        case_type=ROAD,
        name="TUN base",
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
        code="italy_art_138_tun_2025",
        name="art138",
        status=DatasetStatus.APPROVED,
        parameters=_FORMULA_PARAMS,
    )
    moral = CompensationDataset.objects.create(
        source=src,
        source_version=version,
        jurisdiction=jur,
        country=italy,
        case_type=ROAD,
        name="TUN moral",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
    )
    for rt, val in (("min", 26268), ("mid", 27353), ("max", 28439)):
        CompensationTableRow.objects.create(
            dataset=moral,
            row_type=rt,
            age_min=35,
            age_max=35,
            disability_min=10,
            disability_max=10,
            point_value=Decimal(val),
        )
    return {"jur": jur, "src": src, "base": base, "moral": moral}


def _calculate() -> Simulation:
    return run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=ROAD,
        input_data={"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0},
    )


@pytest.mark.django_db
def test_calculated_simulation_saves_provenance():
    _setup(with_source_version=True)
    sim = _calculate()
    assert sim.status == CalculationStatus.CALCULATED.value
    p = sim.calculation_provenance
    assert p["engine"] == "italy_tun_point_value_v1"
    assert p["engine_version"] == "italy-1.0"
    assert p["amount_rule"] == "row_amount_range_direct"
    # dataset + source version + content hash captured
    assert p["dataset"]["version_label"] == "DPR-12-2025"
    assert p["dataset"]["source_version_present"] is True
    assert p["dataset"]["source_version_label"] == "DPR-12-2025"
    assert p["dataset"]["source_content_hash"] == "74d4d4f7b4154694deadbeef"
    assert p["range_dataset"]["version_label"] == "DPR-12-2025-MORAL"
    # formula params hash + 3 row value hashes (range path)
    assert len(p["formula"]["params_hash"]) == 64
    assert len(p["table_rows"]) == 3
    assert all(len(r["value_hash"]) == 64 for r in p["table_rows"])
    assert "calculated_at" in p


@pytest.mark.django_db
def test_provenance_honest_when_source_version_absent():
    """An approved dataset without a source version must NOT fake provenance."""
    _setup(with_source_version=False)
    sim = _calculate()
    assert sim.status == CalculationStatus.CALCULATED.value
    ds = sim.calculation_provenance["dataset"]
    assert ds["source_version_present"] is False
    assert ds["source_content_hash"] is None
    assert ds["source_version_label"] == ""


@pytest.mark.django_db
def test_canary_amounts_unchanged_with_provenance():
    _setup(with_source_version=True)
    sim = _calculate()
    assert (sim.estimated_min, sim.estimated_mid, sim.estimated_max) == (
        Decimal("26268"),
        Decimal("27353"),
        Decimal("28439"),
    )


@pytest.mark.django_db
def test_provenance_is_deterministic():
    _setup(with_source_version=True)
    a = _calculate().calculation_provenance
    b = _calculate().calculation_provenance
    # Everything except the runtime timestamp is identical.
    a.pop("calculated_at"), b.pop("calculated_at")
    assert a == b


@pytest.mark.django_db
def test_unavailable_simulation_has_no_provenance():
    # No approved dataset/source at all → unavailable, empty provenance.
    Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    Jurisdiction.objects.create(
        country=Country.objects.get(code="IT"),
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    sim = _calculate()
    assert sim.status != CalculationStatus.CALCULATED.value
    assert sim.calculation_provenance == {}


@pytest.mark.django_db
def test_result_page_shows_provenance_block_when_present():
    _setup(with_source_version=True)
    sim = _calculate()
    resp = Client().get(reverse("cases:wizard_result", kwargs={"public_id": sim.public_id}))
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'data-testid="calculation-provenance"' in html
    assert "DPR-12-2025" in html  # source version label shown
    assert "74d4d4f7b415" in html  # abbreviated hash (12 chars)


@pytest.mark.django_db
def test_result_page_renders_for_historical_simulation_without_provenance(db):
    # A simulation predating H1-8: empty provenance, must still render fine.
    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    jur = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    sim = Simulation.objects.create(
        case_type=ROAD,
        locale="it",
        jurisdiction=jur,
        country=italy,
        output_data={
            "status": "calculated",
            "estimated_min": "1",
            "estimated_mid": "1",
            "estimated_max": "1",
            "legal_disclaimer": "x",
        },
        status=CalculationStatus.CALCULATED.value,
        confidence="medium",
        currency="EUR",
        estimated_min=Decimal("1"),
        estimated_mid=Decimal("1"),
        estimated_max=Decimal("1"),
        calculation_provenance={},
    )
    resp = Client().get(reverse("cases:wizard_result", kwargs={"public_id": sim.public_id}))
    assert resp.status_code == 200
    assert 'data-testid="calculation-provenance"' not in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_pdf_renders_with_and_without_provenance():
    _setup(with_source_version=True)
    sim = _calculate()
    pdf = render_simulation_pdf_bytes(sim)
    assert pdf[:4] == b"%PDF"
    # Historical sim without provenance: PDF still renders.
    sim.calculation_provenance = {}
    sim.save(update_fields=["calculation_provenance"])
    pdf2 = render_simulation_pdf_bytes(sim)
    assert pdf2[:4] == b"%PDF"
