"""Tests F-eu-650-2012-applicable-law-decision-engine-skeleton.

Cover the applicable-law decision skeleton + its wiring into the
wizard form / ``run_simulation`` flow. The skeleton is fixture-only:
no real legal advice, no automatic renvoi / public-policy outcomes.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators.inheritance_applicable_law import (
    DECISION_CROSS_BORDER_FRAGMENTATION,
    DECISION_HABITUAL_RESIDENCE,
    DECISION_INSUFFICIENT_CONTEXT,
    DECISION_PROFESSIO_JURIS_CANDIDATE,
    ApplicableLawInput,
    evaluate_inheritance_applicable_law,
    normalise_assets_countries,
)

# ---------------------------------------------------------------------------
# 1 — last_residence MA → habitual residence default; manual review
#     stays False if no other gate fires.
# ---------------------------------------------------------------------------


def test_last_residence_only_yields_habitual_residence_default():
    decision = evaluate_inheritance_applicable_law(
        ApplicableLawInput(deceased_country_of_last_residence="MA")
    )
    assert decision.decision_key == DECISION_HABITUAL_RESIDENCE
    assert decision.preliminary_law_country == "MA"
    assert decision.requires_manual_review is False
    assert "rule_habitual_residence_default" in decision.applied_rules


# ---------------------------------------------------------------------------
# 2 — has_will=True forces manual review
# ---------------------------------------------------------------------------


def test_has_will_true_forces_manual_review():
    decision = evaluate_inheritance_applicable_law(
        ApplicableLawInput(
            deceased_country_of_last_residence="MA",
            has_will=True,
        )
    )
    assert decision.decision_key == DECISION_PROFESSIO_JURIS_CANDIDATE
    assert decision.requires_manual_review is True
    assert decision.confidence == "low"
    assert "rule_has_will_present" in decision.applied_rules


# ---------------------------------------------------------------------------
# 3 — multi-country assets force manual review
# ---------------------------------------------------------------------------


def test_multi_country_assets_force_manual_review():
    decision = evaluate_inheritance_applicable_law(
        ApplicableLawInput(
            deceased_country_of_last_residence="MA",
            assets_countries=("MA", "FR"),
        )
    )
    assert decision.requires_manual_review is True
    assert "rule_assets_multi_country" in decision.applied_rules


def test_three_countries_trigger_cross_border_fragmentation():
    decision = evaluate_inheritance_applicable_law(
        ApplicableLawInput(
            deceased_country_of_last_residence="MA",
            assets_countries=("MA", "FR", "IT"),
        )
    )
    assert decision.decision_key == DECISION_CROSS_BORDER_FRAGMENTATION
    assert decision.requires_manual_review is True


# ---------------------------------------------------------------------------
# 4 — nationality differs from residence forces manual review
# ---------------------------------------------------------------------------


def test_nationality_differs_from_residence_forces_manual_review():
    decision = evaluate_inheritance_applicable_law(
        ApplicableLawInput(
            deceased_country_of_last_residence="MA",
            nationality="FR",
        )
    )
    assert decision.requires_manual_review is True
    assert "rule_nationality_differs_from_residence" in decision.applied_rules


# ---------------------------------------------------------------------------
# 5 — missing last_residence → insufficient_context
# ---------------------------------------------------------------------------


def test_missing_last_residence_yields_insufficient_context():
    decision = evaluate_inheritance_applicable_law(ApplicableLawInput())
    assert decision.decision_key == DECISION_INSUFFICIENT_CONTEXT
    assert decision.preliminary_law_country is None
    assert decision.requires_manual_review is True
    assert decision.confidence == "low"


# ---------------------------------------------------------------------------
# 6 — no legal-certainty wording in reasons / warnings
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "payload",
    [
        ApplicableLawInput(deceased_country_of_last_residence="MA"),
        ApplicableLawInput(deceased_country_of_last_residence="MA", has_will=True),
        ApplicableLawInput(
            deceased_country_of_last_residence="MA",
            nationality="FR",
            assets_countries=("MA", "FR", "IT"),
        ),
        ApplicableLawInput(),
    ],
)
def test_no_legal_certainty_wording(payload):
    """Reasons / warnings must avoid wording that could be read as a
    final legal conclusion. The skeleton is preliminary by design."""
    decision = evaluate_inheritance_applicable_law(payload)
    forbidden = (
        "shall apply",
        "is the applicable law",
        "applies definitively",
        "must apply",
        "the law applicable is",
        "this is the applicable law",
    )
    blob = " ".join(decision.reasons + decision.warnings).lower()
    for token in forbidden:
        assert token not in blob, f"forbidden certainty wording {token!r} surfaced: {blob}"


# ---------------------------------------------------------------------------
# 7 — to_input_data normalises assets_countries
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_to_input_data_normalises_assets_countries():
    from apps.cases.forms import InternationalInheritanceWizardForm

    form = InternationalInheritanceWizardForm(
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "0",
            "assets_countries": "ma, fr, IT, fr",  # mixed case + duplicate
            "consent_simulation": "on",
            "website": "",
        }
    )
    assert form.is_valid(), form.errors
    data = form.to_input_data()
    ctx = data["applicable_law_context"]
    assert ctx["deceased_country_of_last_residence"] == "MA"
    assert ctx["nationality"] == "MA"
    assert ctx["assets_countries"] == ["MA", "FR", "IT"]


def test_normalise_assets_countries_helper():
    assert normalise_assets_countries(None) == ()
    assert normalise_assets_countries("") == ()
    assert normalise_assets_countries("MA") == ("MA",)
    assert normalise_assets_countries("MA, fr,IT") == ("MA", "FR", "IT")
    # Reject non-ISO entries silently.
    assert normalise_assets_countries("MA, garbage, FR") == ("MA", "FR")
    assert normalise_assets_countries(["ma", "FR"]) == ("MA", "FR")


# ---------------------------------------------------------------------------
# 8 — MA POST persists applicable_law_context in input_data
# ---------------------------------------------------------------------------


@pytest.fixture
def morocco_setup(db):
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
def tunisia_setup(db):
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


@pytest.mark.django_db
def test_ma_post_persists_applicable_law_context(morocco_setup):
    from apps.cases.models import Simulation

    Client().post(
        reverse("cases:wizard_morocco_inheritance"),
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "assets_countries": "MA, FR",
            "consent_simulation": "on",
            "website": "",
        },
    )
    sim = Simulation.objects.get()
    ctx = sim.input_data["applicable_law_context"]
    assert ctx["deceased_country_of_last_residence"] == "MA"
    assert ctx["nationality"] == "FR"
    assert ctx["assets_countries"] == ["MA", "FR"]


# ---------------------------------------------------------------------------
# 9 — TN POST persists applicable_law_context in input_data
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_post_persists_applicable_law_context(tunisia_setup):
    from apps.cases.models import Simulation

    Client().post(
        reverse("cases:wizard_tunisia_inheritance"),
        {
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "0",
            "assets_countries": "TN",
            "consent_simulation": "on",
            "website": "",
        },
    )
    sim = Simulation.objects.get()
    ctx = sim.input_data["applicable_law_context"]
    assert ctx["deceased_country_of_last_residence"] == "TN"
    assert ctx["assets_countries"] == ["TN"]


# ---------------------------------------------------------------------------
# 10 — output_data["internal"]["applicable_law_decision"] populated
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_output_data_contains_internal_applicable_law_decision(morocco_setup):
    from apps.cases.models import Simulation

    Client().post(
        reverse("cases:wizard_morocco_inheritance"),
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "assets_countries": "MA, FR, IT",
            "consent_simulation": "on",
            "website": "",
        },
    )
    sim = Simulation.objects.get()
    decision = sim.output_data["internal"]["applicable_law_decision"]
    assert decision["preliminary_law_country"] == "MA"
    assert decision["requires_manual_review"] is True
    assert decision["decision_key"] in (
        DECISION_HABITUAL_RESIDENCE,
        DECISION_PROFESSIO_JURIS_CANDIDATE,
        DECISION_CROSS_BORDER_FRAGMENTATION,
    )
    assert "rule_assets_multi_country" in decision["applied_rules"]


# ---------------------------------------------------------------------------
# 11 — public result page does not surface technical decision details
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_result_does_not_surface_decision_details(morocco_setup):
    response = Client().post(
        reverse("cases:wizard_morocco_inheritance"),
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "FR",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "assets_countries": "MA, FR, IT",
            "consent_simulation": "on",
            "website": "",
        },
        follow=True,
    )
    body = response.content.decode("utf-8", errors="replace")
    technical = (
        "applicable_law_decision",
        "decision_key",
        "preliminary_law_country",
        "applied_rules",
        "rule_habitual_residence_default",
        "rule_assets_multi_country",
        "rule_nationality_differs_from_residence",
        "habitual_residence_default",
        "professio_juris_candidate",
        "cross_border_fragmentation",
        "insufficient_context",
        "requires_manual_review",
    )
    for needle in technical:
        assert needle not in body, f"public result page leaks {needle!r}"
    # The premium translatable hint is surfaced (default IT locale here).
    assert (
        "esaminerà la legge applicabile" in body
        or "examinera la loi applicable" in body
        or "review the applicable law" in body
        or "سيراجع المكتب القانون" in body
    )


# ---------------------------------------------------------------------------
# 12 — Italia smoke unchanged
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
        slug="it-fixture-applicable-law",
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
        code="italy_art_138_tun_2025_applicable_law",
        name="applicable-law-smoke",
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
def test_italy_smoke_unchanged_with_applicable_law_skeleton(italy_full_setup):
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
    # Road-accident simulations must NOT receive the inheritance
    # applicable-law enrichment.
    internal = (sim.output_data or {}).get("internal") or {}
    assert "applicable_law_decision" not in internal


# Regression: result page renders no `<h1>` duplicates for inheritance
# variants regardless of whether the applicable-law hint surfaces.


@pytest.mark.django_db
def test_inheritance_result_renders_single_h1(morocco_setup):
    response = Client().post(
        reverse("cases:wizard_morocco_inheritance"),
        {
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "consent_simulation": "on",
            "website": "",
        },
        follow=True,
    )
    body = response.content.decode("utf-8")
    h1s = re.findall(r"<h1\b", body, flags=re.IGNORECASE)
    assert len(h1s) == 1
