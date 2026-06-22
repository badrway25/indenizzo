"""Tests F-inheritance-wizard-spouse-gender-pass2.

Cover the new ``surviving_spouse_gender`` wizard input that
disambiguates the MA / TN inheritance husband-* vs wife-* mapping
rules. The pass is wizard-only; no public calculator activation, no
share computation.

Coverage:

1. Form: gender required when ``spouse_present=True`` — empty gender
   triggers a translated form error.
2. Form: gender ignored when ``spouse_present=False`` — the field
   serialises to ``None`` even if a stray value was submitted.
3. Form: gender ``husband`` round-trips into
   ``input_data.heirs.surviving_spouse_gender``.
4. Form: gender ``wife`` round-trips into
   ``input_data.heirs.surviving_spouse_gender``.
5. Form: invalid gender choice is rejected by the form.
6. Mapping JSON: ``wizard_inputs.captured`` declares the new field at
   ``heirs.surviving_spouse_gender``.
7. Mapping JSON: every ``ma-inh-husband-*`` rule has the
   ``surviving_spouse_gender == "husband"`` precondition in its
   scenario.
8. Mapping JSON: every ``ma-inh-wife-*`` rule has the
   ``surviving_spouse_gender == "wife"`` precondition in its
   scenario.
9. Mapping JSON: husband-vs-wife is no longer in the
   ``missing_for_full_faraid`` list (we just resolved it).
10. View: MA POST + spouse + gender still produces an unavailable
    simulation — no monetary fields surface.
11. View: TN POST + spouse + gender still produces an unavailable
    simulation — no monetary fields surface.
12. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
13. IT PDF still serves ``%PDF`` first 4 bytes.
14. Mapping iter pin = ``F-inheritance-wizard-spouse-gender-pass2`` and
    sha256 unchanged.
"""

from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.urls import reverse

from apps.legal_sources.legal_data_test_support import skip_if_absent

REPO_ROOT = Path(__file__).resolve().parents[2]
MAPPING_JSON = REPO_ROOT / "legal_data" / "mappings" / "morocco_inheritance_mapping_draft.json"
MOUDAWANA_PDF = (
    REPO_ROOT
    / "legal_data"
    / "sources"
    / "morocco"
    / "official_downloaded"
    / "ma-code-famille-moudawana-fr-pdf.pdf"
)
REAL_MOUDAWANA_SHA256 = "41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96"


# ---------------------------------------------------------------------------
# fixture builders (mirror existing inheritance tests)
# ---------------------------------------------------------------------------


@pytest.fixture
def morocco_setup(db):
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language

    morocco = Country.objects.create(code="MA", code_alpha3="MAR", name="Maroc")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    arabic, _ = Language.objects.get_or_create(code="ar", defaults={"name": "العربية"})
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
    arabic, _ = Language.objects.get_or_create(code="ar", defaults={"name": "العربية"})
    juris = Jurisdiction.objects.create(
        country=tunisia,
        code="TN-NATIONAL",
        name="Tunisie",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": tunisia, "language": arabic, "jurisdiction": juris}


# ---------------------------------------------------------------------------
# 1 — Form: gender required when spouse_present=True
# ---------------------------------------------------------------------------


def test_form_rejects_spouse_present_without_gender():
    from apps.cases.forms import InternationalInheritanceWizardForm

    form = InternationalInheritanceWizardForm(
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "surviving_spouse_gender": "",
            "sons_count": "1",
            "daughters_count": "0",
            "father_present": "",
            "mother_present": "",
            "siblings_count": "0",
            "estate_value": "100000",
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
        }
    )
    assert not form.is_valid()
    assert "surviving_spouse_gender" in form.errors


# ---------------------------------------------------------------------------
# 2 — Form: gender ignored when spouse_present=False
# ---------------------------------------------------------------------------


def test_form_drops_gender_when_no_spouse():
    from apps.cases.forms import InternationalInheritanceWizardForm

    form = InternationalInheritanceWizardForm(
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "",
            "surviving_spouse_gender": "husband",
            "sons_count": "0",
            "daughters_count": "0",
            "father_present": "",
            "mother_present": "on",
            "siblings_count": "0",
            "estate_value": "100000",
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
        }
    )
    assert form.is_valid(), form.errors
    payload = form.to_input_data()
    assert payload["heirs"]["spouse"] == 0
    assert payload["heirs"]["surviving_spouse_gender"] is None


# ---------------------------------------------------------------------------
# 3 — Form: husband round-trip
# ---------------------------------------------------------------------------


def test_form_husband_round_trips_into_heirs():
    from apps.cases.forms import InternationalInheritanceWizardForm

    form = InternationalInheritanceWizardForm(
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "surviving_spouse_gender": "husband",
            "sons_count": "0",
            "daughters_count": "0",
            "father_present": "",
            "mother_present": "",
            "siblings_count": "0",
            "estate_value": "100000",
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
        }
    )
    assert form.is_valid(), form.errors
    payload = form.to_input_data()
    assert payload["heirs"]["spouse"] == 1
    assert payload["heirs"]["surviving_spouse_gender"] == "husband"


# ---------------------------------------------------------------------------
# 4 — Form: wife round-trip
# ---------------------------------------------------------------------------


def test_form_wife_round_trips_into_heirs():
    from apps.cases.forms import InternationalInheritanceWizardForm

    form = InternationalInheritanceWizardForm(
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "father_present": "",
            "mother_present": "",
            "siblings_count": "0",
            "estate_value": "800000",
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
        }
    )
    assert form.is_valid(), form.errors
    payload = form.to_input_data()
    assert payload["heirs"]["spouse"] == 1
    assert payload["heirs"]["surviving_spouse_gender"] == "wife"


# ---------------------------------------------------------------------------
# 5 — Form: invalid choice rejected
# ---------------------------------------------------------------------------


def test_form_rejects_invalid_gender_choice():
    from apps.cases.forms import InternationalInheritanceWizardForm

    form = InternationalInheritanceWizardForm(
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "surviving_spouse_gender": "child",
            "sons_count": "0",
            "daughters_count": "0",
            "father_present": "",
            "mother_present": "",
            "siblings_count": "0",
            "estate_value": "100000",
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
        }
    )
    assert not form.is_valid()
    assert "surviving_spouse_gender" in form.errors


# ---------------------------------------------------------------------------
# 6 — Mapping declares the new wizard input
# ---------------------------------------------------------------------------


def test_mapping_declares_surviving_spouse_gender_in_wizard_inputs():
    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    captured = payload.get("wizard_inputs", {}).get("captured", [])
    paths = {c["input_data_path"]: c for c in captured}
    assert (
        "heirs.surviving_spouse_gender" in paths
    ), f"wizard_inputs.captured missing heirs.surviving_spouse_gender; got {sorted(paths)}"
    entry = paths["heirs.surviving_spouse_gender"]
    assert entry["form_field"] == "surviving_spouse_gender"
    assert "husband" in entry["type"] and "wife" in entry["type"]


# ---------------------------------------------------------------------------
# 7 — husband-* rules carry the gender precondition
# ---------------------------------------------------------------------------


def test_husband_rules_precondition_on_gender():
    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    husband_rules = [r for r in payload["rules"] if r["rule_id"].startswith("ma-inh-husband-")]
    assert husband_rules, "mapping must contain at least one ma-inh-husband-* rule"
    for rule in husband_rules:
        gender = rule["scenario"].get("surviving_spouse_gender")
        assert gender == "husband", (
            f"rule {rule['rule_id']!r} scenario must require "
            f"surviving_spouse_gender='husband'; got {gender!r}"
        )


# ---------------------------------------------------------------------------
# 8 — wife-* rules carry the gender precondition
# ---------------------------------------------------------------------------


def test_wife_rules_precondition_on_gender():
    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    wife_rules = [r for r in payload["rules"] if r["rule_id"].startswith("ma-inh-wife-")]
    assert wife_rules, "mapping must contain at least one ma-inh-wife-* rule"
    for rule in wife_rules:
        gender = rule["scenario"].get("surviving_spouse_gender")
        assert gender == "wife", (
            f"rule {rule['rule_id']!r} scenario must require "
            f"surviving_spouse_gender='wife'; got {gender!r}"
        )


# ---------------------------------------------------------------------------
# 9 — husband-vs-wife is no longer listed as missing
# ---------------------------------------------------------------------------


def test_missing_for_full_faraid_no_longer_lists_husband_vs_wife():
    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    missing = payload.get("wizard_inputs", {}).get("missing_for_full_faraid", [])
    blob = " ".join(missing).lower()
    assert (
        "husband_vs_wife" not in blob and "husband vs wife" not in blob
    ), f"missing_for_full_faraid still mentions husband-vs-wife: {missing}"


# ---------------------------------------------------------------------------
# 10 — MA POST stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_post_with_gender_still_unavailable(morocco_setup, client):
    from apps.cases.models import Simulation

    response = client.post(
        reverse("cases:wizard_morocco_inheritance"),
        data={
            "deceased_country_of_last_residence": "MA",
            "nationality": "MA",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "father_present": "",
            "mother_present": "",
            "siblings_count": "0",
            "estate_value": "800000",
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
        },
        follow=True,
    )
    assert response.status_code == 200
    sim = Simulation.objects.order_by("-id").first()
    assert sim is not None
    assert sim.input_data["heirs"]["surviving_spouse_gender"] == "wife"
    assert sim.estimated_min in (None, "", Decimal("0"))
    assert sim.estimated_mid in (None, "", Decimal("0"))
    assert sim.estimated_max in (None, "", Decimal("0"))


# ---------------------------------------------------------------------------
# 11 — TN POST stays unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_post_with_gender_still_unavailable(tunisia_setup, client):
    from apps.cases.models import Simulation

    response = client.post(
        reverse("cases:wizard_tunisia_inheritance"),
        data={
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "spouse_present": "on",
            "surviving_spouse_gender": "husband",
            "sons_count": "0",
            "daughters_count": "2",
            "father_present": "",
            "mother_present": "on",
            "siblings_count": "0",
            "estate_value": "500000",
            "consent_simulation": "on",
            "special_categories_consent": "on",
            "website": "",
        },
        follow=True,
    )
    assert response.status_code == 200
    sim = Simulation.objects.order_by("-id").first()
    assert sim is not None
    assert sim.input_data["heirs"]["surviving_spouse_gender"] == "husband"
    assert sim.estimated_min in (None, "", Decimal("0"))
    assert sim.estimated_mid in (None, "", Decimal("0"))
    assert sim.estimated_max in (None, "", Decimal("0"))


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
        slug="it-fixture-spouse-gender-pass2",
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
        code="italy_art_138_spouse_gender_pass2",
        name="spouse-gender-pass2-it-smoke",
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
def test_italy_smoke_unchanged_with_pass2(italy_full_setup):
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
# 13 — IT PDF first 4 bytes still %PDF
# ---------------------------------------------------------------------------


def test_moudawana_pdf_unchanged_after_pass2():
    """The pass2 changes are wizard-side only — they must not modify
    the on-disk Moudawana PDF (sha256 + size + magic bytes).
    """
    skip_if_absent(MOUDAWANA_PDF)
    assert MOUDAWANA_PDF.is_file(), "Moudawana PDF must remain in place"
    raw = MOUDAWANA_PDF.read_bytes()
    assert raw[:4] == b"%PDF"
    assert len(raw) == 489_071, f"Moudawana size changed: {len(raw)} bytes"
    import hashlib

    digest = hashlib.sha256(raw).hexdigest()
    assert digest == REAL_MOUDAWANA_SHA256, f"Moudawana sha256 drifted: {digest}"


# ---------------------------------------------------------------------------
# 14 — Mapping iter pin + sha256 unchanged
# ---------------------------------------------------------------------------


def test_mapping_iter_pin_is_pass2():
    payload = json.loads(MAPPING_JSON.read_text(encoding="utf-8"))
    assert payload["iter"] == "F-inheritance-wizard-spouse-gender-pass2"
    assert payload["source_sha256"] == REAL_MOUDAWANA_SHA256
    assert payload["activation_allowed"] is False
