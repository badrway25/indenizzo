"""Tests F-morocco-engine-activation-blockers-guard-pass1.

The Moudawana mapping draft tags every rule with an
``activation_blockers`` list of preconditions a Studio reviewer must
lift before the rule can fire publicly (e.g. doctrinal hajb-noqsan
modelling, sibling sub-typing, gender disambiguation). This pass adds
the engine guard that enforces the contract: when a Studio reviewer
eventually promotes a rule into ``CalculationFormula.parameters``,
they carry over the blocker list. The engine refuses to fire whenever
the list is non-empty.

The pass is fixture-only. No production ``LegalSource``, dataset or
formula is touched. ``activation_allowed`` on the mapping JSON stays
``false``; the public MA / TN funnels stay ``unavailable_requires_legal_validation``.

Coverage:

1. Empty ``activation_blockers`` (or absent) → engine computes.
2. Non-empty ``activation_blockers`` → engine returns
   ``UNAVAILABLE_REQUIRES_LEGAL_VALIDATION`` with the new
   ``inheritance_rule_activation_blocked`` diagnostic.
3. The blocked-mother rule from the mapping pass3
   (``ma-inh-mother-no-descendants-multi-siblings-blocked``) carries a
   non-empty blocker list — the engine refuses it.
4. ``rule_metadata.activation_blockers`` (nested) also triggers the
   guard (forward-compatibility shape).
5. Malformed blockers (string instead of list) are ignored —
   the engine does not infer a blocker from an invalid payload.
6. The diagnostic ``inheritance_rule_activation_blocked`` is
   ``public_safe=False`` (never surfaced on the public result page).
7. The MA public funnel still produces an unavailable simulation —
   no DB row in the production state is APPROVED.
8. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
9. IT PDF first 4 bytes still ``%PDF``.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPPING_JSON = REPO_ROOT / "legal_data" / "mappings" / "morocco_inheritance_mapping_draft.json"
IT_PDF = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "italy"
    / "official_downloaded"
    / "it-dpr-12-2025-tun-danno-biologico.pdf"
)


SYNTH_SHARES = {
    "spouse": "1/8",
    "sons_group": "remainder_2_to_1",
    "daughters_group": "remainder_2_to_1",
}
SYNTH_ESTATE = Decimal("800000")


# ---------------------------------------------------------------------------
# Fixture builders — mirror the existing inheritance-engine-inactive tests.
# ---------------------------------------------------------------------------


@pytest.fixture
def ma_jurisdiction(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    morocco = Country.objects.create(code="MA", code_alpha3="MAR", name="Maroc")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    french = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=morocco,
        code="MA-NATIONAL",
        name="Maroc",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": morocco, "language": french, "jurisdiction": juris}


def _seed_ma_source_and_dataset(ma_jurisdiction, *, slug_suffix="default"):
    from apps.calculators.enums import CaseType
    from apps.compensation.models import CompensationDataset, DatasetStatus
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    morocco = ma_jurisdiction["country"]
    juris = ma_jurisdiction["jurisdiction"]
    french = ma_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug=f"ma-fixture-source-blockers-{slug_suffix}",
        title=f"MA fixture (synthetic, approved) — {slug_suffix}",
        country=morocco,
        jurisdiction=juris,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.APPROVED,
        publication_date=date(2004, 2, 5),
    )
    ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=morocco,
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        name=f"MA Moudawana fixture blockers ({slug_suffix})",
        version_label=f"MA-FIXTURE-BLOCKERS-{slug_suffix.upper()}",
        status=DatasetStatus.APPROVED,
        valid_from=date(2004, 2, 5),
    )
    return {"source": src, "dataset": ds}


def _seed_ma_formula(handle, *, parameters):
    """Seed an APPROVED formula with the supplied parameters dict."""
    from apps.compensation.models import CalculationFormula, DatasetStatus

    CalculationFormula.objects.create(
        dataset=handle["dataset"],
        code=f"morocco_inheritance_blockers_{handle['source'].slug[-12:]}",
        name="MA inheritance fixture (blockers guard)",
        expression_text="fixed shares + 2:1 residual",
        source_reference="synthetic test fixture",
        parameters=parameters,
        status=DatasetStatus.APPROVED,
    )


def _baseline_params() -> dict:
    return {
        "engine": "morocco_inheritance_v1",
        "amount_rule": "morocco_inheritance_fixed_share_direct",
        "requires": ["heirs"],
        "shares": dict(SYNTH_SHARES),
    }


def _baseline_input() -> dict:
    return {
        "deceased_country_of_last_residence": "MA",
        "heirs": {"spouse": 1, "sons": 1, "daughters": 1},
        "estate_value": str(SYNTH_ESTATE),
    }


# ---------------------------------------------------------------------------
# 1 — no activation_blockers → CALCULATED (baseline still works)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_engine_calculates_when_blockers_absent(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="absent")
    _seed_ma_formula(handle, parameters=_baseline_params())  # no blockers key
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data=_baseline_input(),
    )
    assert sim.status == CalculationStatus.CALCULATED.value


# ---------------------------------------------------------------------------
# 2 — empty list → CALCULATED (an explicit empty list signals
#                  "no blocker", which is the intended semantics)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_engine_calculates_when_blockers_empty_list(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="empty")
    params = _baseline_params() | {"activation_blockers": []}
    _seed_ma_formula(handle, parameters=params)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data=_baseline_input(),
    )
    assert sim.status == CalculationStatus.CALCULATED.value


# ---------------------------------------------------------------------------
# 3 — non-empty blockers → UNAVAILABLE with the new diagnostic
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_engine_unavailable_when_blockers_present(ma_jurisdiction):
    from apps.calculators import diagnostics as _diag
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="present")
    params = _baseline_params() | {
        "activation_blockers": [
            "wizard now captures surviving_spouse_gender; engine must read "
            "heirs.surviving_spouse_gender == 'wife' before firing this rule"
        ],
    }
    _seed_ma_formula(handle, parameters=params)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data=_baseline_input(),
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    missing = (sim.output_data or {}).get("missing_documents", [])
    assert _diag.INHERITANCE_RULE_ACTIVATION_BLOCKED in missing
    # The engine must NOT have produced any breakdown amount.
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 4 — the mapping's blocked-mother rule carries a non-empty list
# ---------------------------------------------------------------------------


def test_mapping_blocked_mother_rule_has_non_empty_blockers():
    """The mapping's
    ``ma-inh-mother-no-descendants-multi-siblings-blocked`` rule is
    the canonical example of an activation-blocked rule. The engine
    guard relies on this list staying non-empty until hajb-noqsan
    modelling lands.
    """
    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    blocked = next(
        r
        for r in payload["rules"]
        if r["rule_id"] == "ma-inh-mother-no-descendants-multi-siblings-blocked"
    )
    blockers = blocked.get("activation_blockers") or []
    assert isinstance(blockers, list)
    assert blockers, (
        "ma-inh-mother-no-descendants-multi-siblings-blocked must "
        "carry at least one activation_blocker until hajb-noqsan "
        "modelling lands"
    )


# ---------------------------------------------------------------------------
# 5 — the blocked-mother rule, when promoted to a fixture formula, is
#     refused by the engine
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_engine_refuses_promoted_blocked_mother_rule(ma_jurisdiction):
    from apps.calculators import diagnostics as _diag
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    blocked = next(
        r
        for r in payload["rules"]
        if r["rule_id"] == "ma-inh-mother-no-descendants-multi-siblings-blocked"
    )
    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="blockedmother")
    # Simulate a future Studio promotion that copies the blocker list
    # over to ``CalculationFormula.parameters``.
    params = _baseline_params() | {
        "activation_blockers": list(blocked["activation_blockers"]),
    }
    _seed_ma_formula(handle, parameters=params)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data=_baseline_input(),
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    missing = (sim.output_data or {}).get("missing_documents", [])
    assert _diag.INHERITANCE_RULE_ACTIVATION_BLOCKED in missing


# ---------------------------------------------------------------------------
# 6 — nested ``rule_metadata.activation_blockers`` also triggers the guard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_engine_guards_on_nested_rule_metadata_blockers(ma_jurisdiction):
    from apps.calculators import diagnostics as _diag
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="nested")
    params = _baseline_params() | {
        "rule_metadata": {
            "rule_id": "ma-inh-husband-without-descendants",
            "activation_blockers": ["engine must read heirs.surviving_spouse_gender == 'husband'"],
        }
    }
    _seed_ma_formula(handle, parameters=params)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data=_baseline_input(),
    )
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    missing = (sim.output_data or {}).get("missing_documents", [])
    assert _diag.INHERITANCE_RULE_ACTIVATION_BLOCKED in missing


# ---------------------------------------------------------------------------
# 7 — malformed activation_blockers (string instead of list) is ignored
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_engine_ignores_malformed_blockers(ma_jurisdiction):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    handle = _seed_ma_source_and_dataset(ma_jurisdiction, slug_suffix="malformed")
    # Pass a string instead of a list — engine should not infer a
    # blocker from it. This protects against a buggy promotion script.
    params = _baseline_params() | {"activation_blockers": "definitely not a list"}
    _seed_ma_formula(handle, parameters=params)
    sim = run_simulation(
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data=_baseline_input(),
    )
    assert sim.status == CalculationStatus.CALCULATED.value


# ---------------------------------------------------------------------------
# 8 — diagnostic is internal-only (public_safe=False)
# ---------------------------------------------------------------------------


def test_diagnostic_is_internal_only():
    from apps.calculators import diagnostics as _diag

    assert _diag.diagnostic_public_safe(_diag.INHERITANCE_RULE_ACTIVATION_BLOCKED) is False


# ---------------------------------------------------------------------------
# 9 — public MA result page does NOT surface the diagnostic slug
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_ma_result_does_not_leak_diagnostic_slug(ma_jurisdiction):
    """The MA public funnel must not expose
    ``inheritance_rule_activation_blocked`` to end users — it stays
    inside ``Simulation.output_data`` for Studio audit only.
    """
    from django.test import Client
    from django.urls import reverse

    from apps.calculators import diagnostics as _diag

    client = Client()
    response = client.post(
        reverse("cases:wizard_morocco_inheritance"),
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "800000",
            "consent_simulation": "on",
            "website": "",
        },
        follow=True,
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8", errors="replace")
    assert _diag.INHERITANCE_RULE_ACTIVATION_BLOCKED not in body


# ---------------------------------------------------------------------------
# 10 — Italia smoke unchanged
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
        slug="it-fixture-blockers-pass1",
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
        code="italy_blockers_pass1",
        name="blockers-pass1-it-smoke",
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
def test_italy_smoke_unchanged_with_pass1_guard(italy_full_setup):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
        locale="it",
    )
    assert Decimal(sim.estimated_min) == Decimal("26268")
    assert Decimal(sim.estimated_mid) == Decimal("27353")
    assert Decimal(sim.estimated_max) == Decimal("28439")


# ---------------------------------------------------------------------------
# 11 — IT PDF still %PDF
# ---------------------------------------------------------------------------


def test_italy_pdf_first_four_bytes_unchanged():
    assert IT_PDF.is_file(), "Italy DPR-12-2025 PDF must remain in place"
    raw = IT_PDF.read_bytes()
    assert raw[:4] == b"%PDF"
