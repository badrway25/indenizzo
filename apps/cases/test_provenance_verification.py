"""H1-8.1: tests for provenance reproducibility verification.

Covers every verifier status (reproducible / drifted / incomplete /
legacy_no_provenance / not_calculated), the command's --fail-on-drift exit
code, PII-safe output, and the IT canary.
"""

from __future__ import annotations

import io
import json
from datetime import date
from decimal import Decimal

import pytest
from django.core.management import call_command

from apps.calculators.enums import CalculationStatus, CaseType
from apps.cases.models import Simulation
from apps.cases.provenance_verifier import (
    DRIFTED,
    INCOMPLETE,
    LEGACY_NO_PROVENANCE,
    NOT_CALCULATED,
    REPRODUCIBLE,
    verify_simulation,
)
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
def stack(db):
    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    lang = Language.objects.create(code="it", name="Italiano")
    jur = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-verify",
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
        content_hash="74d4d4f7original",
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
    formula = CalculationFormula.objects.create(
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
    return {"ver": ver, "base": base, "moral": moral, "formula": formula, "rows": rows}


def _calc() -> Simulation:
    return run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=ROAD,
        input_data={"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0},
    )


@pytest.mark.django_db
def test_reproducible(stack):
    res = verify_simulation(_calc())
    assert res["status"] == REPRODUCIBLE
    assert res["pii_safe"] is True
    assert all(c["ok"] for c in res["checks"])


@pytest.mark.django_db
def test_legacy_no_provenance(stack):
    sim = _calc()
    sim.calculation_provenance = {}
    sim.save(update_fields=["calculation_provenance"])
    assert verify_simulation(sim)["status"] == LEGACY_NO_PROVENANCE


@pytest.mark.django_db
def test_not_calculated(db):
    sim = Simulation.objects.create(
        case_type=ROAD,
        status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
    )
    assert verify_simulation(sim)["status"] == NOT_CALCULATED


@pytest.mark.django_db
def test_drift_on_source_hash_change(stack):
    sim = _calc()
    stack["ver"].content_hash = "TAMPERED"
    stack["ver"].save(update_fields=["content_hash"])
    res = verify_simulation(sim)
    assert res["status"] == DRIFTED
    assert any(c["name"] == "dataset_source_hash_matches" and not c["ok"] for c in res["checks"])


@pytest.mark.django_db
def test_drift_on_row_value_change(stack):
    sim = _calc()
    stack["rows"]["mid"].point_value = Decimal("99999")
    stack["rows"]["mid"].save(update_fields=["point_value"])
    assert verify_simulation(sim)["status"] == DRIFTED


@pytest.mark.django_db
def test_drift_on_formula_params_change(stack):
    sim = _calc()
    params = dict(_PARAMS)
    params["amount_rule"] = "something_else"
    stack["formula"].parameters = params
    stack["formula"].save(update_fields=["parameters"])
    assert verify_simulation(sim)["status"] == DRIFTED


@pytest.mark.django_db
def test_drift_on_dataset_unapproved(stack):
    sim = _calc()
    stack["base"].status = DatasetStatus.DRAFT
    stack["base"].save(update_fields=["status"])
    res = verify_simulation(sim)
    assert res["status"] == DRIFTED
    assert any(c["name"] == "dataset_still_approved" and not c["ok"] for c in res["checks"])


@pytest.mark.django_db
def test_incomplete_provenance(stack):
    sim = _calc()
    prov = dict(sim.calculation_provenance)
    prov.pop("formula")  # remove a required key
    sim.calculation_provenance = prov
    sim.save(update_fields=["calculation_provenance"])
    assert verify_simulation(sim)["status"] == INCOMPLETE


@pytest.mark.django_db
def test_command_fail_on_drift_exit_code(stack):
    sim = _calc()
    stack["ver"].content_hash = "TAMPERED"
    stack["ver"].save(update_fields=["content_hash"])
    with pytest.raises(SystemExit) as exc:
        call_command(
            "verify_calculation_provenance",
            "--simulation",
            str(sim.public_id),
            "--fail-on-drift",
            stdout=io.StringIO(),
        )
    assert exc.value.code != 0


@pytest.mark.django_db
def test_command_output_is_pii_safe(stack):
    _calc()
    buf = io.StringIO()
    call_command(
        "verify_calculation_provenance", "--all-calculated", "--format", "json", stdout=buf
    )
    out = buf.getvalue()
    data = json.loads(out)
    assert data["results"][0]["pii_safe"] is True
    assert "input_data" not in out
    assert "victim_age" not in out


@pytest.mark.django_db
def test_command_canary_ok(stack):
    buf = io.StringIO()
    call_command("verify_calculation_provenance", "--canary", "--format", "json", stdout=buf)
    data = json.loads(buf.getvalue())
    assert data["canary"]["ok"] is True
    assert [Decimal(a) for a in data["canary"]["amounts"]] == [
        Decimal("26268"),
        Decimal("27353"),
        Decimal("28439"),
    ]
