"""Verify the post-import state of the France candidate datasets.

Iter: F-france-import-datasets-draft-seed.

Asserts (read-only, no DB writes):

- ``FR-MORNET-2024-DRAFT`` and ``FR-GAZETTE-PALAIS-2022-DRAFT`` exist in
  status ``DRAFT`` and only DRAFT.
- Per-row_type counts match the upstream extractor outputs:
  DFP=180, Affection=11, Viagere=416, Temporaire=3752, Anticipated=20.
- No row in either dataset is somehow ``approved`` or ``public``: the
  parent dataset stays DRAFT, so ``is_usable_for_calculations`` is False.
- ``LegalSource(fr-referentiel-mornet-2024)`` and
  ``LegalSource(fr-bareme-capitalisation-gazette-palais-2022)`` stay
  ``needs_review`` (NOT promoted to APPROVED by the import).
- No ``CalculationFormula`` exists for any FR dataset.
- ``run_simulation(FR-NATIONAL, road_accident_bodily_injury)`` returns
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

EXPECTED_COUNTS: dict[str, dict[str, int]] = {
    "FR-MORNET-2024-DRAFT": {
        "fr_dfp_per_age_disability_amount_per_point": 180,
        "fr_prejudice_affection_per_relation_amount": 11,
    },
    "FR-GAZETTE-PALAIS-2022-DRAFT": {
        "fr_capitalisation_viagere_per_age_sex_rate_coefficient": 416,
        "fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient": 3752,
        "fr_anticipated_payment_years_per_age_sex_rate_years": 20,
    },
}


def fail(msg: str, *, code: int = 1) -> int:
    print(f"FAIL: {msg}")
    return code


def main() -> int:
    failures: list[str] = []

    # Datasets exist + DRAFT.
    for label in EXPECTED_COUNTS:
        ds = CompensationDataset.objects.filter(version_label=label).first()
        if ds is None:
            return fail(f"dataset {label!r} not found in DB", code=2)
        if ds.status != DatasetStatus.DRAFT:
            failures.append(f"dataset {label!r} is {ds.status!r} but must be DRAFT")
        if ds.is_usable_for_calculations:
            failures.append(
                f"dataset {label!r} is_usable_for_calculations=True; "
                "DRAFT datasets must never be usable"
            )

        per_type = EXPECTED_COUNTS[label]
        for row_type, expected in per_type.items():
            actual = ds.rows.filter(row_type=row_type).count()
            mark = "PASS" if actual == expected else "FAIL"
            print(f"  [{mark}] {label} :: {row_type:<70} {actual}/{expected}")
            if actual != expected:
                failures.append(f"{label} :: {row_type} count={actual} expected={expected}")

    # LegalSources stay needs_review.
    for slug in (
        "fr-referentiel-mornet-2024",
        "fr-bareme-capitalisation-gazette-palais-2022",
    ):
        src = LegalSource.objects.filter(slug=slug).first()
        if src is None:
            failures.append(f"LegalSource {slug!r} missing")
            continue
        if src.status != SourceStatus.NEEDS_REVIEW:
            failures.append(f"LegalSource {slug!r} status={src.status!r} (must be needs_review)")

    # No FR-specific CalculationFormula.
    fr_formula_count = CalculationFormula.objects.filter(dataset__country__code="FR").count()
    if fr_formula_count != 0:
        failures.append(f"CalculationFormula(FR)={fr_formula_count} (must be 0)")

    # FR calculator stays unavailable.
    fr_sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={},
    )
    if fr_sim.status != CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value:
        failures.append(
            f"FR road_accident sim status={fr_sim.status!r} (must be "
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
    print("All FR candidate import invariants OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
