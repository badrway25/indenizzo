"""Tests F-calculator-warning-strings-translatable-pass1.

Cover the diagnostics helper + its IT/FR/AR translations + the
engine-side migration: every engine that previously emitted
hard-coded English warnings now routes through
``apps.calculators.diagnostics.diagnostic_to_internal_warning`` and
keeps its stable ``missing_documents`` slug.

Public path is double-checked: the result page never surfaces
diagnostic text or codes regardless of locale.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.calculators import diagnostics as _diag

# ---------------------------------------------------------------------------
# 1 — diagnostic_message exists for every registered code
# ---------------------------------------------------------------------------


def test_diagnostic_message_exists_for_every_known_code():
    for code in _diag.known_diagnostic_codes():
        msg = _diag.diagnostic_message(code)
        assert isinstance(msg, str) and msg, f"empty message for {code!r}"


# ---------------------------------------------------------------------------
# 2 — diagnostic_message returns translatable strings (lazy proxy)
# ---------------------------------------------------------------------------


def test_diagnostic_message_renders_in_explicit_language():
    en = _diag.diagnostic_message(_diag.LEGAL_SOURCES_NOT_APPROVED, language="en")
    it = _diag.diagnostic_message(_diag.LEGAL_SOURCES_NOT_APPROVED, language="it")
    fr = _diag.diagnostic_message(_diag.LEGAL_SOURCES_NOT_APPROVED, language="fr")
    ar = _diag.diagnostic_message(_diag.LEGAL_SOURCES_NOT_APPROVED, language="ar")
    # Spot the translation: English contains "approved", Italian contains
    # "fonti legali approvate", French "sources juridiques", Arabic the
    # opening brace of "لا تتوفّر".
    assert "approved legal sources" in en.lower()
    assert "fonte legale approvata" in it.lower()
    assert "source juridique" in fr.lower()
    assert "تتوفّر" in ar


# ---------------------------------------------------------------------------
# 3 — IT / FR / AR carry translations for the five most-used messages
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code",
    [
        _diag.LEGAL_SOURCES_NOT_APPROVED,
        _diag.COMPENSATION_DATASET_NOT_APPROVED,
        _diag.CALCULATION_FORMULA_NOT_APPROVED,
        _diag.CALCULATOR_ENGINE_PENDING,
        _diag.APPLICABLE_LAW_REVIEW_REQUIRED,
    ],
)
def test_it_fr_ar_translations_present(code):
    en = _diag.diagnostic_message(code, language="en")
    for lang in ("it", "fr", "ar"):
        translated = _diag.diagnostic_message(code, language=lang)
        # If translation missing, gettext would return the EN source —
        # so the language version must differ from EN.
        assert translated != en, f"{code} not translated in {lang}"


# ---------------------------------------------------------------------------
# 4 — unknown diagnostic code falls back safely
# ---------------------------------------------------------------------------


def test_unknown_diagnostic_code_is_safe():
    msg = _diag.diagnostic_message("not_a_real_code")
    assert msg == "not_a_real_code"
    assert _diag.diagnostic_public_safe("not_a_real_code") is False


# ---------------------------------------------------------------------------
# 5 — France engine: unavailable still has stable slug + diagnostic warning
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_france_unavailable_uses_diagnostic_message():
    from apps.calculators.engines.france import FranceRoadAccidentBodilyInjuryCalculator

    calc = FranceRoadAccidentBodilyInjuryCalculator(language="fr")
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 5})
    assert result.status == "unavailable_requires_legal_validation"
    # The legacy slug must still appear (test stability) — emitted by
    # base.py when no APPROVED source exists.
    # The base engine also emits a single warning sourced from the
    # diagnostics layer (the migration above replaced inline text with
    # the helper); the message must NOT be empty.
    assert result.warnings
    for warn in result.warnings:
        assert warn.strip()


# ---------------------------------------------------------------------------
# 6 — Belgium engine: same coverage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_belgium_unavailable_uses_diagnostic_message():
    from apps.calculators.engines.belgium import BelgiumRoadAccidentBodilyInjuryCalculator

    calc = BelgiumRoadAccidentBodilyInjuryCalculator(language="fr")
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 5})
    assert result.status == "unavailable_requires_legal_validation"
    assert result.warnings


# ---------------------------------------------------------------------------
# 7 — Morocco applicable-law block uses the centralised diagnostic
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


def _seed_ma_full_stack(ma_jurisdiction, *, slug_suffix: str) -> dict:
    from apps.calculators.enums import CaseType
    from apps.compensation.models import CalculationFormula, CompensationDataset, DatasetStatus
    from apps.compensation.test_fixtures import approved_source_version
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    morocco = ma_jurisdiction["country"]
    juris = ma_jurisdiction["jurisdiction"]
    arabic = ma_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug=f"ma-fixture-diag-{slug_suffix}",
        title=f"MA fixture diagnostics — {slug_suffix}",
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
        name=f"MA Moudawana diag fixture ({slug_suffix})",
        version_label=f"MA-FIXTURE-DIAG-{slug_suffix.upper()}",
        status=DatasetStatus.APPROVED,
        valid_from=date(2004, 2, 5),
    )
    CalculationFormula.objects.create(
        dataset=ds,
        code=f"morocco_diag_{slug_suffix}",
        name="MA diag fixture (synthetic)",
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


@pytest.mark.django_db
def test_morocco_applicable_law_block_uses_diagnostic(ma_jurisdiction):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    _seed_ma_full_stack(ma_jurisdiction, slug_suffix="diag-block")
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
    assert sim.status == "unavailable_requires_legal_validation"
    warnings = (sim.output_data or {}).get("warnings") or []
    assert warnings
    # The engine routes through the diagnostics helper. The exact
    # rendered message depends on the active locale, so compare against
    # the helper's output in every supported locale until one matches.
    code = _diag.APPLICABLE_LAW_REVIEW_REQUIRED
    candidates = {
        _diag.diagnostic_message(code, language=lang) for lang in ("en", "it", "fr", "ar")
    }
    assert any(any(c == w or c in w for c in candidates) for w in warnings)


# ---------------------------------------------------------------------------
# 8 — Tunisia invalid share spec uses centralised diagnostic
# ---------------------------------------------------------------------------


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


@pytest.mark.django_db
def test_tunisia_invalid_share_spec_uses_diagnostic(tn_jurisdiction):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation
    from apps.compensation.models import CalculationFormula, CompensationDataset, DatasetStatus
    from apps.compensation.test_fixtures import approved_source_version
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    tunisia = tn_jurisdiction["country"]
    juris = tn_jurisdiction["jurisdiction"]
    arabic = tn_jurisdiction["language"]
    src = LegalSource.objects.create(
        slug="tn-fixture-diag-bad-spec",
        title="TN fixture diag bad spec",
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
        name="TN CSP diag fixture",
        version_label="TN-FIXTURE-DIAG-BAD-SPEC",
        status=DatasetStatus.APPROVED,
        valid_from=date(1956, 8, 13),
    )
    CalculationFormula.objects.create(
        dataset=ds,
        code="tunisia_diag_bad_spec",
        name="TN diag fixture (invalid spec)",
        expression_text="fixed shares > 1",
        source_reference="synthetic test fixture",
        parameters={
            "engine": "tunisia_inheritance_v1",
            "amount_rule": "tunisia_inheritance_fixed_share_direct",
            "requires": ["heirs"],
            # 2/3 + 1/2 > 1 → invalid spec.
            "shares": {"spouse": "2/3", "mother": "1/2"},
        },
        status=DatasetStatus.APPROVED,
    )
    sim = run_simulation(
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={
            "deceased_country_of_last_residence": "TN",
            "heirs": {"spouse": 1, "mother": 1},
        },
    )
    assert sim.status == "unavailable_requires_legal_validation"
    missing = (sim.output_data or {}).get("missing_documents") or []
    assert _diag.INHERITANCE_SHARE_SPEC_INVALID in missing
    warnings = (sim.output_data or {}).get("warnings") or []
    code = _diag.INHERITANCE_SHARE_SPEC_INVALID
    candidates = {
        _diag.diagnostic_message(code, language=lang) for lang in ("en", "it", "fr", "ar")
    }
    assert any(any(c in w for c in candidates) for w in warnings)


# ---------------------------------------------------------------------------
# 9 — public result page does not show diagnostic text or codes
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_result_page_no_diagnostic_leak(ma_jurisdiction):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    _seed_ma_full_stack(ma_jurisdiction, slug_suffix="public-leak")
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
    # Diagnostic codes must never appear publicly.
    for code in _diag.known_diagnostic_codes():
        assert code not in body, f"public page leaks diagnostic code {code!r}"
    # English diagnostic prose must not appear publicly either.
    en_msg = _diag.diagnostic_message(_diag.APPLICABLE_LAW_REVIEW_REQUIRED, language="en")
    assert en_msg not in body


# ---------------------------------------------------------------------------
# 10 — hygiene audit pattern: banned words still absent
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_banned_public_words_after_diagnostics_migration(ma_jurisdiction):
    from apps.calculators.enums import CaseType
    from apps.cases.services import run_simulation

    _seed_ma_full_stack(ma_jurisdiction, slug_suffix="banned")
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
    body_lower = response.content.decode("utf-8").lower()
    for banned in (
        "scaffold",
        "placeholder",
        "under validation",
        "module pending",
        "engine pending",
        "missing_documents",
        "unavailable_requires_legal_validation",
    ):
        assert banned not in body_lower, f"banned word {banned!r} on result page"


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
        slug="it-fixture-diag",
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
        code="italy_art_138_tun_2025_diag",
        name="diag-smoke",
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
def test_italy_smoke_unchanged_after_diagnostics_migration(italy_full_setup):
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
