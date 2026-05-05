"""Verify the post-import state of the Belgium candidate dataset.

Iter: F-belgium-import-candidate-datasets-draft-seed.

Asserts (read-only, no DB writes):

- ``BE-TABLEAU-INDICATIF-2020-DRAFT`` exists in status ``DRAFT``.
- Per-row_type counts match the upstream extractor outputs:
  Souffrances=63, Forfait=71, Deces=13, Vehicule=19. Total=166.
- ``is_usable_for_calculations`` is False (DRAFT status blocks reads).
- ``LegalSource(be-tableau-indicatif-2020)`` stays ``needs_review`` —
  the import never promotes the source.
- No ``CalculationFormula`` exists for any BE dataset.
- ``run_simulation(BE-NATIONAL, road_accident_bodily_injury)`` returns
  ``unavailable_requires_legal_validation`` (calculator stays off).
- Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.

Exit codes: 0 ok, 1 invariant failure, 2 schema/data missing.
"""

from __future__ import annotations

import os
import pathlib
import sys
from decimal import Decimal

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.calculators.enums import CalculationStatus, CaseType  # noqa: E402
from apps.cases.services import run_simulation  # noqa: E402
from apps.compensation.models import (  # noqa: E402
    CalculationFormula,
    CompensationDataset,
    DatasetStatus,
)
from apps.legal_sources.enums import SourceStatus  # noqa: E402
from apps.legal_sources.models import LegalSource  # noqa: E402

DATASET_LABEL = "BE-TABLEAU-INDICATIF-2020-DRAFT"

EXPECTED_COUNTS: dict[str, int] = {
    "be_souffrances_endurees_per_age_severity_amount": 63,
    "be_indemnite_forfaitaire_per_age_annual_amount": 71,
    "be_prejudice_deces_affection_per_relation_amount": 13,
    "be_vehicule_remplacement_per_type_per_day_amount": 19,
}
EXPECTED_TOTAL = sum(EXPECTED_COUNTS.values())  # 166


def fail(msg: str, *, code: int = 1) -> int:
    print(f"FAIL: {msg}")
    return code


def main() -> int:
    failures: list[str] = []

    # Dataset exists + DRAFT.
    ds = CompensationDataset.objects.filter(version_label=DATASET_LABEL).first()
    if ds is None:
        return fail(f"dataset {DATASET_LABEL!r} not found in DB", code=2)
    if ds.status != DatasetStatus.DRAFT:
        failures.append(f"dataset {DATASET_LABEL!r} is {ds.status!r} but must be DRAFT")
    if ds.is_usable_for_calculations:
        failures.append(
            f"dataset {DATASET_LABEL!r} is_usable_for_calculations=True; "
            "DRAFT datasets must never be usable"
        )

    actual_total = 0
    for row_type, expected in EXPECTED_COUNTS.items():
        actual = ds.rows.filter(row_type=row_type).count()
        actual_total += actual
        mark = "PASS" if actual == expected else "FAIL"
        print(f"  [{mark}] {row_type:<55} {actual}/{expected}")
        if actual != expected:
            failures.append(f"{row_type} count={actual} expected={expected}")

    if actual_total != EXPECTED_TOTAL:
        failures.append(f"total rows={actual_total} expected={EXPECTED_TOTAL}")
    print(
        f"  [{'PASS' if actual_total == EXPECTED_TOTAL else 'FAIL'}] total {actual_total}/{EXPECTED_TOTAL}"
    )

    # LegalSource stays needs_review.
    src = LegalSource.objects.filter(slug="be-tableau-indicatif-2020").first()
    if src is None:
        failures.append("LegalSource 'be-tableau-indicatif-2020' missing")
    elif src.status != SourceStatus.NEEDS_REVIEW:
        failures.append(
            f"LegalSource 'be-tableau-indicatif-2020' status={src.status!r} "
            "(must be needs_review)"
        )

    # No BE-specific CalculationFormula.
    be_formula_count = CalculationFormula.objects.filter(dataset__country__code="BE").count()
    if be_formula_count != 0:
        failures.append(f"CalculationFormula(BE)={be_formula_count} (must be 0)")

    # BE calculator stays unavailable.
    be_sim = run_simulation(
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={},
    )
    if be_sim.status != CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value:
        failures.append(
            f"BE road_accident sim status={be_sim.status!r} (must be "
            "unavailable_requires_legal_validation)"
        )

    # Italia smoke unchanged.
    it_sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
    )
    expected = (Decimal("26268"), Decimal("27353"), Decimal("28439"))
    actual = (it_sim.estimated_min, it_sim.estimated_mid, it_sim.estimated_max)
    if it_sim.status != CalculationStatus.CALCULATED.value or actual != expected:
        failures.append(
            f"IT 35/10/0 sim status={it_sim.status!r} amounts={actual} "
            f"(expected calculated {expected})"
        )

    print()
    if failures:
        for msg in failures:
            print(f"  FAIL: {msg}")
        return 1
    print("All BE candidate import invariants OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
