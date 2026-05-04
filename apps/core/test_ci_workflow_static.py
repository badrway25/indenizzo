"""Tests F-ci-public-site-audit-workflow.

Static checks that pin the contract of
``.github/workflows/public-site-audit.yml`` so a future edit cannot
silently weaken the audit.

We deliberately do NOT parse the YAML with PyYAML — keeping the
checks string-based avoids adding a dependency that the rest of the
project does not need. Each rule looks for an unambiguous substring
that captures the intent.

1. workflow file exists.
2. workflow invokes ``scripts/run_public_lighthouse_audit.py``.
3. workflow uses ``--mode playwright``.
4. workflow sets ``PEXELS_ENABLED: "false"``.
5. workflow sets ``SENTRY_DSN: ""``.
6. workflow uploads the audit artefacts via ``actions/upload-artifact``.
7. workflow does NOT contain the literal ``PEXELS_API_KEY`` (no real
   API key, and no env-var passthrough that could leak in logs).
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "public-site-audit.yml"


def _workflow_text() -> str:
    return WORKFLOW_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1 — workflow exists
# ---------------------------------------------------------------------------


def test_workflow_file_exists():
    assert WORKFLOW_PATH.exists(), f"missing {WORKFLOW_PATH.relative_to(REPO_ROOT)}"
    assert WORKFLOW_PATH.is_file()
    # Sanity: minimum size for a real workflow.
    assert WORKFLOW_PATH.stat().st_size > 500


# ---------------------------------------------------------------------------
# 2 — workflow uses the audit script
# ---------------------------------------------------------------------------


def test_workflow_invokes_audit_script():
    text = _workflow_text()
    assert "scripts/run_public_lighthouse_audit.py" in text


# ---------------------------------------------------------------------------
# 3 — workflow uses --mode playwright (deterministic in CI)
# ---------------------------------------------------------------------------


def test_workflow_uses_mode_playwright():
    text = _workflow_text()
    assert "--mode playwright" in text, (
        "Until the Lighthouse CLI is pinned, CI must use the deterministic "
        "structural fallback. See PERF_PASS2_LIGHTHOUSE_CI_READY.md."
    )
    # And it should NOT silently use --mode lighthouse without a pinned CLI.
    assert "--mode lighthouse" not in text, (
        "--mode lighthouse requires a pinned Lighthouse CLI. Don't enable "
        "without an explicit migration step (doc + install)."
    )


# ---------------------------------------------------------------------------
# 4 — workflow disables Pexels in CI
# ---------------------------------------------------------------------------


def test_workflow_disables_pexels():
    text = _workflow_text()
    assert 'PEXELS_ENABLED: "false"' in text, (
        "CI must run with the Pexels image flow disabled — no external "
        "fetches, no API-key handling."
    )


# ---------------------------------------------------------------------------
# 5 — workflow sets SENTRY_DSN to empty string
# ---------------------------------------------------------------------------


def test_workflow_blanks_sentry_dsn():
    text = _workflow_text()
    assert 'SENTRY_DSN: ""' in text, "CI must not ship telemetry to Sentry — keep SENTRY_DSN empty."


# ---------------------------------------------------------------------------
# 6 — workflow uploads the audit artefact
# ---------------------------------------------------------------------------


def test_workflow_uploads_audit_artifact():
    text = _workflow_text()
    assert "actions/upload-artifact" in text
    assert "name: public-site-audit" in text
    assert "docs/reports/lighthouse/ci_public_site/" in text


# ---------------------------------------------------------------------------
# 7 — workflow does NOT mention the real Pexels API key var
# ---------------------------------------------------------------------------


def test_workflow_does_not_mention_pexels_api_key():
    """Defence in depth: even if a future edit tried to pass through the
    real Pexels secret, the test would catch it. The audit harness can
    work without the key (PEXELS_ENABLED=false), so there is no
    legitimate reason to surface PEXELS_API_KEY in the workflow."""

    text = _workflow_text()
    assert "PEXELS_API_KEY" not in text


# ---------------------------------------------------------------------------
# 8 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_calculator_fixture(db):
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
        slug="it-fixture-ci-workflow",
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
        name="TUN base ci-workflow",
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
        name="TUN moral ci-workflow",
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
        code="italy_art_138_tun_2025_ci_workflow",
        name="ci-workflow",
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
    return italy


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_ci_workflow(italy_calculator_fixture):
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
