"""Tests F-inheritance-wizard-input-completeness-visual-pass1.

Cover the wizard form input completeness for MA / TN inheritance:

1. MA wizard renders the new heirs fields.
2. TN wizard renders the new heirs fields.
3. MA POST persists ``input_data["heirs"]`` with the expected shape.
4. TN POST persists ``input_data["heirs"]`` with the expected shape.
5. estate_value optional — when omitted, ``input_data["estate_value"]``
   stays ``None`` and the simulation still records.
6. sons_count negative is rejected by the form.
7. MA POST result remains unavailable (no monetary fields produced).
8. TN POST result remains unavailable (no monetary fields produced).
9. MA + TN public_status pinned to "International inheritance review".
10. FR / AR wizard render the new strings translated, no English
    fallback for the in-iter strings.
11. No banned public words on the wizard pages.
12. No duplicate H1 on the wizard pages.
13. No Pexels attribution string leaks into the wizard pages.
14. No API key leak (Pexels API key) on the wizard pages.
15. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains unchanged
    when the new wizard form coexists with the Italy calculator.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

# ---------------------------------------------------------------------------
# fixture builders
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
    arabic, _ = Language.objects.get_or_create(code="ar", defaults={"name": "العربية"})
    juris = Jurisdiction.objects.create(
        country=tunisia,
        code="TN-NATIONAL",
        name="Tunisie",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return {"country": tunisia, "language": arabic, "jurisdiction": juris}


VALID_PAYLOAD = {
    "deceased_country_of_last_residence": "MA",
    "nationality": "MA",
    "spouse_present": "on",
    # F-inheritance-wizard-spouse-gender-pass2: gender is required
    # whenever a surviving spouse is declared, otherwise the form
    # rejects the submission.
    "surviving_spouse_gender": "wife",
    "sons_count": "1",
    "daughters_count": "1",
    "consent_simulation": "on",
    "special_categories_consent": "on",
    "website": "",
}


# ---------------------------------------------------------------------------
# 1 — MA wizard renders new heirs fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_wizard_renders_heirs_fields():
    response = Client().get(reverse("cases:wizard_morocco_inheritance"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    for field in (
        'name="spouse_present"',
        'name="sons_count"',
        'name="daughters_count"',
        'name="father_present"',
        'name="mother_present"',
        'name="siblings_count"',
        'name="estate_value"',
        'name="deceased_country_of_last_residence"',
        'name="nationality"',
    ):
        assert field in body, f"Missing field rendering: {field}"


# ---------------------------------------------------------------------------
# 2 — TN wizard renders new heirs fields
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_wizard_renders_heirs_fields():
    response = Client().get(reverse("cases:wizard_tunisia_inheritance"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    for field in (
        'name="spouse_present"',
        'name="sons_count"',
        'name="daughters_count"',
        'name="father_present"',
        'name="mother_present"',
        'name="siblings_count"',
        'name="estate_value"',
    ):
        assert field in body


# ---------------------------------------------------------------------------
# 3 — MA POST persists heirs structure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_post_persists_heirs_structure(morocco_setup):
    from apps.cases.models import Simulation

    Client().post(
        reverse("cases:wizard_morocco_inheritance"),
        {
            **VALID_PAYLOAD,
            "father_present": "on",
            "mother_present": "on",
            "siblings_count": "2",
        },
    )
    sim = Simulation.objects.get()
    heirs = sim.input_data["heirs"]
    assert heirs == {
        "spouse": 1,
        "surviving_spouse_gender": "wife",
        "sons": 1,
        "daughters": 1,
        "father": 1,
        "mother": 1,
        "siblings": 2,
    }


# ---------------------------------------------------------------------------
# 4 — TN POST persists heirs structure
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_post_persists_heirs_structure(tunisia_setup):
    from apps.cases.models import Simulation

    Client().post(
        reverse("cases:wizard_tunisia_inheritance"),
        {
            **VALID_PAYLOAD,
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "mother_present": "on",
        },
    )
    sim = Simulation.objects.get()
    heirs = sim.input_data["heirs"]
    assert heirs["spouse"] == 1
    assert heirs["mother"] == 1
    assert heirs["sons"] == 1
    assert heirs["daughters"] == 1
    assert heirs["father"] == 0


# ---------------------------------------------------------------------------
# 5 — estate_value optional
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_estate_value_optional_persisted(morocco_setup):
    from apps.cases.models import Simulation

    # Without estate_value
    Client().post(
        reverse("cases:wizard_morocco_inheritance"),
        VALID_PAYLOAD,
    )
    sim = Simulation.objects.get()
    assert sim.input_data["estate_value"] is None
    sim.delete()
    # With estate_value
    Client().post(
        reverse("cases:wizard_morocco_inheritance"),
        {**VALID_PAYLOAD, "estate_value": "800000"},
    )
    sim = Simulation.objects.get()
    # The form's Decimal coerces the input but the str() representation
    # depends on the user's typed precision; accept either form.
    assert Decimal(sim.input_data["estate_value"]) == Decimal("800000")


# ---------------------------------------------------------------------------
# 6 — sons_count negative rejected
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_sons_count_negative_rejected():
    from apps.cases.forms import InternationalInheritanceWizardForm

    payload = {**VALID_PAYLOAD, "sons_count": "-1"}
    form = InternationalInheritanceWizardForm(data=payload)
    assert not form.is_valid()
    assert "sons_count" in form.errors


# ---------------------------------------------------------------------------
# 7 — MA POST result remains unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ma_post_result_unavailable(morocco_setup):
    from apps.calculators.enums import CalculationStatus
    from apps.cases.models import Simulation

    Client().post(
        reverse("cases:wizard_morocco_inheritance"),
        {**VALID_PAYLOAD, "estate_value": "800000"},
    )
    sim = Simulation.objects.get()
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 8 — TN POST result remains unavailable
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_post_result_unavailable(tunisia_setup):
    from apps.calculators.enums import CalculationStatus
    from apps.cases.models import Simulation

    Client().post(
        reverse("cases:wizard_tunisia_inheritance"),
        {
            **VALID_PAYLOAD,
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "mother_present": "on",
            "estate_value": "1200000",
        },
    )
    sim = Simulation.objects.get()
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert sim.estimated_min is None
    assert sim.estimated_mid is None
    assert sim.estimated_max is None


# ---------------------------------------------------------------------------
# 9 — public_status pinned
# ---------------------------------------------------------------------------


def test_public_status_ma_tn_pinned_to_review():
    from apps.core.public_status import (
        STATUS_INHERITANCE_REVIEW,
        get_country_public_status,
    )

    for code in ("MA", "TN"):
        ps = get_country_public_status(code, "international_inheritance")
        assert ps.status_key == STATUS_INHERITANCE_REVIEW
        assert ps.is_calculation_available is False


# ---------------------------------------------------------------------------
# 10 — FR/AR wizard pages render new strings translated
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_ar_no_english_fallback_for_in_iter_strings():
    fr = Client().get("/fr/wizard/ma/inheritance/").content.decode("utf-8")
    ar = Client().get("/ar/wizard/ma/inheritance/").content.decode("utf-8")
    # FR must contain the translated headings and not the English ones
    # for in-iter strings.
    assert "Situation familiale" in fr
    assert "Patrimoine et contexte" in fr
    assert "Soumettre le dossier au Cabinet" in fr
    assert "Family situation" not in fr
    assert "Patrimony and context" not in fr
    assert "Submit the case to the Studio" not in fr
    # AR must contain the Arabic strings.
    assert "الوضع العائلي" in ar
    assert "التركة والسياق" in ar
    assert "أرسل الملف إلى المكتب" in ar
    assert "Family situation" not in ar
    assert "Patrimony and context" not in ar


# ---------------------------------------------------------------------------
# 11 — no banned public words on wizard pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_banned_words_on_wizard_pages():
    banned = (
        "scaffold",
        "placeholder",
        "under validation",
        "in preparation",
        "coming soon",
        "work in progress",
        "in corso",
        "legal validation wizard",
        "module pending",
        "engine pending",
        "missing_documents",
        "unavailable_requires_legal_validation",
    )
    for path in (
        "/wizard/ma/inheritance/",
        "/wizard/tn/inheritance/",
        "/fr/wizard/ma/inheritance/",
        "/ar/wizard/ma/inheritance/",
    ):
        body = Client().get(path).content.decode("utf-8").lower()
        for word in banned:
            assert word not in body, f"banned word '{word}' present in {path}"


# ---------------------------------------------------------------------------
# 12 — no duplicate H1 on wizard pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_duplicate_h1_on_wizard_pages():
    for path in (
        "/wizard/ma/inheritance/",
        "/wizard/tn/inheritance/",
    ):
        body = Client().get(path).content.decode("utf-8")
        h1s = re.findall(r"<h1\b", body, flags=re.IGNORECASE)
        assert len(h1s) == 1, f"{path} has {len(h1s)} H1 tags, expected 1"


# ---------------------------------------------------------------------------
# 13 — no Pexels attribution leaks
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_pexels_attribution_on_wizard_pages():
    for path in (
        "/wizard/ma/inheritance/",
        "/wizard/tn/inheritance/",
        "/fr/wizard/ma/inheritance/",
        "/ar/wizard/ma/inheritance/",
    ):
        body = Client().get(path).content.decode("utf-8")
        # No "Photo by ... on Pexels" / "Pexels.com" attribution string.
        assert "Photo by" not in body or "Pexels" not in body, f"Pexels attribution found in {path}"
        assert "pexels.com" not in body.lower()


# ---------------------------------------------------------------------------
# 14 — no API key leak
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_api_key_leak_on_wizard_pages():
    for path in (
        "/wizard/ma/inheritance/",
        "/wizard/tn/inheritance/",
    ):
        body = Client().get(path).content.decode("utf-8")
        assert "PEXELS_API_KEY" not in body
        # No Authorization header value pattern.
        assert not re.search(r"Authorization:\s*[A-Za-z0-9_-]{20,}", body)


# ---------------------------------------------------------------------------
# 15 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke(db):
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
        slug="it-fixture-pass1-wizard",
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
        code="italy_art_138_tun_2025_pass1_wizard_smoke",
        name="pass1-wizard-smoke",
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
def test_italy_smoke_unchanged_with_new_inheritance_wizard(italy_smoke):
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
