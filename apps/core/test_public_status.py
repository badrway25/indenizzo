"""Tests F-product-public-status-centralization-pass6.

Pin the contract of ``apps/core/public_status.py``:

1. IT + road accident → calculation available.
2. FR + road accident → preliminary legal assessment.
3. BE + road accident → preliminary legal assessment.
4. MA + international inheritance → inheritance review.
5. TN + international inheritance → inheritance review.
6. Unknown country → manual legal review.
7. Templates render badge labels from public_status (not hardcoded).
8. No banned words on principal pages (IT/FR/AR/EN).
9. FR pages have no high-priority English fallback.
10. AR pages have no high-priority English fallback.
11. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client

from apps.core.public_status import (
    STATUS_AVAILABLE,
    STATUS_INHERITANCE_REVIEW,
    STATUS_LEGAL_ASSESSMENT,
    STATUS_MANUAL_REVIEW,
    PublicStatus,
    get_country_no_amounts_message,
    get_country_primary_cta,
    get_country_public_status,
    get_country_status_description,
    get_country_status_label,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SCRIPT_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def _visible(html: str) -> str:
    cleaned = _SCRIPT_RE.sub(" ", html)
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", cleaned)).strip()


@pytest.fixture(autouse=True)
def _reset_active_language():
    yield
    from django.utils import translation

    translation.deactivate_all()


# ---------------------------------------------------------------------------
# 1-6 — helper API contract
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "country, case_type, expected_key, expected_calc",
    [
        ("IT", "road_accident_bodily_injury", STATUS_AVAILABLE, True),
        ("FR", "road_accident_bodily_injury", STATUS_LEGAL_ASSESSMENT, False),
        ("BE", "road_accident_bodily_injury", STATUS_LEGAL_ASSESSMENT, False),
        ("MA", "international_inheritance", STATUS_INHERITANCE_REVIEW, False),
        ("TN", "international_inheritance", STATUS_INHERITANCE_REVIEW, False),
        # Unknown country / case → manual review.
        ("ES", None, STATUS_MANUAL_REVIEW, False),
        ("DE", "", STATUS_MANUAL_REVIEW, False),
        # Empty inputs are tolerated.
        (None, None, STATUS_MANUAL_REVIEW, False),
    ],
)
def test_get_country_public_status(country, case_type, expected_key, expected_calc):
    ps = get_country_public_status(country, case_type)
    assert isinstance(ps, PublicStatus)
    assert ps.status_key == expected_key
    assert ps.is_calculation_available is expected_calc
    # Every status carries at minimum a non-empty badge label and a
    # non-empty primary CTA.
    assert str(ps.badge_label).strip()
    assert str(ps.primary_cta_label).strip()


def test_convenience_getters_match_full_object():
    cc, ct = "FR", "road_accident_bodily_injury"
    ps = get_country_public_status(cc, ct)
    assert get_country_status_label(cc, ct) == ps.badge_label
    assert get_country_status_description(cc, ct) == ps.short_description
    assert get_country_primary_cta(cc, ct) == ps.primary_cta_label
    assert get_country_no_amounts_message(cc, ct) == ps.no_amounts_message


# ---------------------------------------------------------------------------
# 7 — templates render labels from public_status
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_countries_page_renders_public_status_badges():
    """Three distinct badges should appear on /countries/, one per
    status variant. We check default-IT translations to keep the
    test robust to future copy adjustments."""

    body = Client().get("/countries/").content.decode("utf-8")
    visible = _visible(body)
    assert "Calcolo indicativo disponibile" in visible
    assert "Valutazione legale preliminare" in visible
    assert "Analisi successoria internazionale" in visible


@pytest.mark.django_db
def test_wizard_start_renders_public_status_badges_and_ctas():
    body = Client().get("/wizard/").content.decode("utf-8")
    visible = _visible(body)
    # Badges
    assert "Calcolo indicativo disponibile" in visible
    assert "Valutazione legale preliminare" in visible
    assert "Analisi successoria internazionale" in visible
    # Primary CTA per IT (calculation available).
    assert ("Avvia una simulazione indicativa" in visible) or (
        "Run an indicative simulation" in visible
    )


# ---------------------------------------------------------------------------
# 8 — no banned words on principal pages
# ---------------------------------------------------------------------------


PRINCIPAL_PATHS = [
    "/",
    "/countries/",
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
    "/case-types/",
    "/methodology/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
    "/privacy/",
    "/disclaimer/",
]

BANNED_WORDS = (
    "scaffold",
    "placeholder",
    "under validation",
    "in preparation",
    "coming soon",
    "work in progress",
    "in corso",
    "modulo non operativo",
    "legal validation wizard",
    "module pending",
    "engine pending",
    "missing_documents",
    "unavailable_requires_legal_validation",
)


@pytest.mark.django_db
@pytest.mark.parametrize("locale_prefix", ["", "/fr", "/ar", "/en"])
def test_principal_pages_have_no_banned_words(locale_prefix):
    client = Client()
    for path in PRINCIPAL_PATHS:
        response = client.get(locale_prefix + path)
        assert response.status_code == 200, f"{locale_prefix}{path} → {response.status_code}"
        visible = _visible(response.content.decode("utf-8", errors="replace")).lower()
        for word in BANNED_WORDS:
            assert (
                word not in visible
            ), f"{locale_prefix}{path} surfaces banned public word {word!r}"


# ---------------------------------------------------------------------------
# 9-10 — no FR / AR English fallback
# ---------------------------------------------------------------------------


HIGH_PRIORITY_EN = (
    "How it works",
    "What this means",
    "Next steps",
    "Useful pages",
    "indicative calculation is available",
    "Preliminary legal assessment",
    "Manual legal review",
    "International inheritance review",
    "Studio reviews each",
    "Submit the case to the Studio",
    "Studio offers a preliminary",
    "applicable-law mapping",
)


@pytest.mark.django_db
@pytest.mark.parametrize("locale_prefix", ["/fr", "/ar"])
def test_translated_locales_have_no_high_priority_english_fallback(locale_prefix):
    client = Client()
    for path in PRINCIPAL_PATHS:
        body = client.get(locale_prefix + path).content.decode("utf-8", errors="replace")
        visible = _visible(body)
        for phrase in HIGH_PRIORITY_EN:
            assert phrase not in visible, f"{locale_prefix}{path}: surfaces EN fallback {phrase!r}"


# ---------------------------------------------------------------------------
# 11 — Italia smoke unchanged
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
    from apps.compensation.test_fixtures import approved_source_version
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
        slug="it-pass6-fixture",
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
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base pass6",
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
        name="TUN moral pass6",
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
        code="italy_art_138_tun_2025_pass6",
        name="pass6",
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
def test_italy_smoke_unchanged_after_pass6(italy_calculator_fixture):
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
