"""Tests F-applicable-law-skeleton-engine-integration-pass1.

Cover the wiring between
:func:`apps.calculators.inheritance_applicable_law.can_run_inheritance_share_engine`
and the MA / TN inheritance engines. The skeleton blocks the
fixture-only share path whenever the applicable-law decision flags
manual review, insufficient context, low confidence or a missing
preliminary law country. Public DB stays unavailable (no APPROVED
sources for FR / BE / MA / TN).
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

# ---------------------------------------------------------------------------
# Fixture builders (mirror the existing inheritance test files)
# ---------------------------------------------------------------------------


@pytest.fixture
def ma_jurisdiction(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    morocco = Country.objects.create(code="MA", code_alpha3="MAR", name="Maroc")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    arabic = Language.objects.create(code="ar", name="العربية")
    juris = Jurisdiction.objects.create(
        country=morocco,
        code="MA-NATIONAL",
        name="Maroc",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": morocco, "language": arabic, "jurisdiction": juris}


@pytest.fixture
def tn_jurisdiction(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    tunisia = Country.objects.create(code="TN", code_alpha3="TUN", name="Tunisie")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    arabic = Language.objects.get_or_create(code="ar", defaults={"name": "العربية"})[0]
    juris = Jurisdiction.objects.create(
        country=tunisia,
        code="TN-NATIONAL",
        name="Tunisie",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": tunisia, "language": arabic, "jurisdiction": juris}


def _seed_ma_stack(handle_jurisdiction, *, slug_suffix: str) -> dict:
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    morocco = handle_jurisdiction["country"]
    juris = handle_jurisdiction["jurisdiction"]
    arabic = handle_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug=f"ma-fixture-applaw-{slug_suffix}",
        title=f"MA fixture (applaw integration) — {slug_suffix}",
        country=morocco,
        jurisdiction=juris,
        language=arabic,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2004, 2, 5),
    )
    ds = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=morocco,
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        name=f"MA Moudawana applaw fixture ({slug_suffix})",
        version_label=f"MA-FIXTURE-APPLAW-{slug_suffix.upper()}",
        status=DatasetStatus.APPROVED,
        valid_from=date(2004, 2, 5),
    )
    CalculationFormula.objects.create(
        dataset=ds,
        code=f"morocco_applaw_{slug_suffix}",
        name="MA applaw fixture (synthetic)",
        expression_text="fixed shares + 2:1 residual",
        source_reference="synthetic test fixture",
        parameters={
            "engine": "morocco_inheritance_v1",
            "amount_rule": "morocco_inheritance_fixed_share_direct",
            "requires": ["heirs"],
            "shares": {
                "spouse": "1/8",
                "sons_group": "remainder_2_to_1",
                "daughters_group": "remainder_2_to_1",
            },
        },
        status=DatasetStatus.APPROVED,
    )
    return {"source": src, "dataset": ds}


def _seed_tn_stack(handle_jurisdiction, *, slug_suffix: str) -> dict:
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    tunisia = handle_jurisdiction["country"]
    juris = handle_jurisdiction["jurisdiction"]
    arabic = handle_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug=f"tn-fixture-applaw-{slug_suffix}",
        title=f"TN fixture (applaw integration) — {slug_suffix}",
        country=tunisia,
        jurisdiction=juris,
        language=arabic,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(1956, 8, 13),
    )
    ds = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=tunisia,
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        name=f"TN CSP applaw fixture ({slug_suffix})",
        version_label=f"TN-FIXTURE-APPLAW-{slug_suffix.upper()}",
        status=DatasetStatus.APPROVED,
        valid_from=date(1956, 8, 13),
    )
    CalculationFormula.objects.create(
        dataset=ds,
        code=f"tunisia_applaw_{slug_suffix}",
        name="TN applaw fixture (synthetic)",
        expression_text="fixed shares + 2:1 residual",
        source_reference="synthetic test fixture",
        parameters={
            "engine": "tunisia_inheritance_v1",
            "amount_rule": "tunisia_inheritance_fixed_share_direct",
            "requires": ["heirs"],
            "shares": {
                "spouse": "1/8",
                "mother": "1/6",
                "sons_group": "remainder_2_to_1",
                "daughters_group": "remainder_2_to_1",
            },
        },
        status=DatasetStatus.APPROVED,
    )
    return {"source": src, "dataset": ds}


# ---------------------------------------------------------------------------
# 1 — MA simple context → engine computes shares
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_simple_context_runs_share_engine(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_ma_stack(ma_jurisdiction, slug_suffix="simple")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "has_will": False,
            "assets_countries": ["MA"],
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("800000")


# ---------------------------------------------------------------------------
# 2 — MA + has_will → blocked by gate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_has_will_blocked_by_gate(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_ma_stack(ma_jurisdiction, slug_suffix="has-will")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "has_will": True,
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    missing = (sim.output_data or {}).get("missing_documents") or []
    assert "applicable_law_manual_review_required" in missing


# ---------------------------------------------------------------------------
# 3 — MA + multi-country assets → blocked by gate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_multi_country_assets_blocked_by_gate(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_ma_stack(ma_jurisdiction, slug_suffix="multi-asset")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "assets_countries": ["MA", "FR"],
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    missing = (sim.output_data or {}).get("missing_documents") or []
    assert "applicable_law_manual_review_required" in missing


# ---------------------------------------------------------------------------
# 4 — MA + nationality differs from residence → blocked by gate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_nationality_mismatch_blocked_by_gate(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_ma_stack(ma_jurisdiction, slug_suffix="nationality-mismatch")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


# ---------------------------------------------------------------------------
# 5 — MA missing residence → insufficient_context branch
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_missing_residence_blocked_with_insufficient_context(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_ma_stack(ma_jurisdiction, slug_suffix="no-residence")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    missing = (sim.output_data or {}).get("missing_documents") or []
    assert "applicable_law_insufficient_context" in missing


# ---------------------------------------------------------------------------
# 6 — TN simple context → engine computes shares
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_simple_context_runs_share_engine(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_tn_stack(tn_jurisdiction, slug_suffix="simple")
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "has_will": False,
            "assets_countries": ["TN"],
            "heirs": {"spouse": 1, "mother": 1, "sons": 1, "daughters": 1},
            "estate_value": "1200000",
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("1200000")


# ---------------------------------------------------------------------------
# 7 — TN cross-border → blocked by gate
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_cross_border_blocked_by_gate(tn_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    _seed_tn_stack(tn_jurisdiction, slug_suffix="cross-border")
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "TN",
            "assets_countries": ["TN", "FR", "IT"],
            "heirs": {"spouse": 1, "mother": 1, "sons": 1, "daughters": 1},
            "estate_value": "1200000",
        },
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    missing = (sim.output_data or {}).get("missing_documents") or []
    assert "applicable_law_manual_review_required" in missing


# ---------------------------------------------------------------------------
# 8 — internal applicable_law_decision stored in output_data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_internal_applicable_law_decision_recorded(ma_jurisdiction):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    _seed_ma_stack(ma_jurisdiction, slug_suffix="internal")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    decision = (sim.output_data or {})["internal"]["applicable_law_decision"]
    assert decision["preliminary_law_country"] == "MA"
    assert decision["requires_manual_review"] is True
    assert "rule_nationality_differs_from_residence" in decision["applied_rules"]


# ---------------------------------------------------------------------------
# 9 — public result page does NOT show decision_key / applied_rules /
#     requires_manual_review / block_reason slugs
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_result_page_hides_decision_internals(ma_jurisdiction):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    _seed_ma_stack(ma_jurisdiction, slug_suffix="public-leak")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "has_will": True,
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    response = Client().get(
        reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    )
    body = response.content.decode("utf-8", errors="replace")
    technical = (
        "applicable_law_decision",
        "decision_key",
        "applied_rules",
        "requires_manual_review",
        "applicable_law_manual_review_required",
        "applicable_law_insufficient_context",
        "applicable_law_low_confidence",
        "applicable_law_missing_law_country",
        "applicable_law_decision_missing",
        "rule_habitual_residence_default",
        "rule_has_will_present",
        "rule_assets_multi_country",
        "rule_nationality_differs_from_residence",
        "professio_juris_candidate",
        "habitual_residence_default",
        "cross_border_fragmentation",
        "insufficient_context",
    )
    for needle in technical:
        assert needle not in body, f"public result page leaks {needle!r}"


# ---------------------------------------------------------------------------
# 10 — public_status MA / TN remains International inheritance review
# ---------------------------------------------------------------------------


def test_public_status_ma_tn_pinned_to_review_after_gate():
    from apps.core.public_status import (
        STATUS_INHERITANCE_REVIEW,
        get_country_public_status,
    )

    for code in ("MA", "TN"):
        ps = get_country_public_status(code, "international_inheritance")
        assert ps.status_key == STATUS_INHERITANCE_REVIEW
        assert ps.is_calculation_available is False


# ---------------------------------------------------------------------------
# 11 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_full_setup(db):
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-fixture-applaw-integration",
        title="D.P.R. 12/2025 fixture",
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
        source_version=approved_source_version(src),
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
        source_version=approved_source_version(src),
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
        code="italy_art_138_tun_2025_applaw_integration",
        name="applaw-integration-smoke",
        expression_text="placeholder-test",
        source_reference="placeholder-test",
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
def test_italy_smoke_unchanged_with_applaw_integration(italy_full_setup):
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
    # Road-accident simulations must not receive the inheritance
    # applicable-law enrichment.
    internal = (sim.output_data or {}).get("internal") or {}
    assert "applicable_law_decision" not in internal


# ---------------------------------------------------------------------------
# Regression net for the can_run helper itself.
# ---------------------------------------------------------------------------


def test_can_run_helper_smoke():
    from apps.calculators.inheritance_applicable_law import (
        ApplicableLawInput,
        can_run_inheritance_share_engine,
        evaluate_inheritance_applicable_law,
    )

    # Simple — runs.
    assert (
        can_run_inheritance_share_engine(
            evaluate_inheritance_applicable_law(
                ApplicableLawInput(deceased_country_of_last_residence="MA")
            )
        )
        is True
    )
    # Cross-border — blocks.
    assert (
        can_run_inheritance_share_engine(
            evaluate_inheritance_applicable_law(
                ApplicableLawInput(
                    deceased_country_of_last_residence="MA",
                    assets_countries=("MA", "FR"),
                )
            )
        )
        is False
    )
    # Insufficient context — blocks.
    assert (
        can_run_inheritance_share_engine(evaluate_inheritance_applicable_law(ApplicableLawInput()))
        is False
    )
    # None — blocks.
    assert can_run_inheritance_share_engine(None) is False


# Single H1 net for the result pages of the new fixtures.


@pytest.mark.django_db
def test_inheritance_result_renders_single_h1_after_gate(ma_jurisdiction):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    _seed_ma_stack(ma_jurisdiction, slug_suffix="single-h1")
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "MA",
            "has_will": True,
            "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
            "estate_value": "800000",
        },
    )
    response = Client().get(
        reverse("cases:wizard_result", kwargs={"public_id": str(sim.public_id)})
    )
    body = response.content.decode("utf-8")
    h1s = re.findall(r"<h1\b", body, flags=re.IGNORECASE)
    assert len(h1s) == 1
