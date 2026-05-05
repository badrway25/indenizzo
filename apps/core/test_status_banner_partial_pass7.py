"""Tests F-product-status-banner-partial-pass7.

Pin the contract of ``templates/partials/_public_status_panel.html``:

1. The partial renders the badge label of the public_status it
   receives.
2. ``/wizard/fr/road-accident/`` surfaces the FR
   ``Preliminary legal assessment`` badge (or its translation), through
   the partial and the public_status helper.
3. ``/wizard/be/road-accident/`` does the same for Belgium.
4. ``/wizard/ma/inheritance/`` surfaces the
   ``International inheritance review`` badge (or its translation).
5. ``/wizard/tn/inheritance/`` does the same for Tunisia.
6. The result page never surfaces the technical
   ``unavailable_requires_legal_validation`` token (the user must read
   the centralised public_status copy).
7. No banned public words on principal pages, default + i18n locales.
8. No high-priority English fallback on FR / AR.
9. No duplicate H1 on any of the four new wizard pages.
10. No Pexels attribution leaks.
11. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains unchanged.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.template.loader import render_to_string
from django.test import Client

from apps.core.public_status import get_country_public_status

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
# 1 — partial renders the public_status badge
# ---------------------------------------------------------------------------


def test_partial_renders_public_status_badge():
    ps = get_country_public_status("FR", "road_accident_bodily_injury")
    html = render_to_string(
        "partials/_public_status_panel.html",
        {"public_status": ps, "show_no_amounts_message": True, "variant": "wizard"},
    )
    visible = _visible(html)
    # Badge label must be present (FR default IT translation).
    assert ("Preliminary legal assessment" in visible) or (
        "Valutazione legale preliminare" in visible
    )
    # CTA must be present too.
    assert ("Submit the case to the Studio" in visible) or (
        "Trasmetti il caso allo Studio" in visible
    )


# ---------------------------------------------------------------------------
# 2-5 — wizards surface the centralised badge through the partial
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_france_wizard_uses_public_status_panel():
    body = Client().get("/wizard/fr/road-accident/").content.decode("utf-8")
    visible = _visible(body)
    assert ("Preliminary legal assessment" in visible) or (
        "Valutazione legale preliminare" in visible
    )
    # The legal_basis line of the partial must surface the framework.
    assert "Loi Badinter" in visible
    assert "Référentiel Mornet" in visible


@pytest.mark.django_db
def test_belgium_wizard_uses_public_status_panel():
    body = Client().get("/wizard/be/road-accident/").content.decode("utf-8")
    visible = _visible(body)
    assert ("Preliminary legal assessment" in visible) or (
        "Valutazione legale preliminare" in visible
    )
    assert "Tableau Indicatif" in visible
    assert "Schryvers" in visible


@pytest.mark.django_db
def test_morocco_wizard_uses_public_status_panel():
    body = Client().get("/wizard/ma/inheritance/").content.decode("utf-8")
    visible = _visible(body)
    assert ("International inheritance review" in visible) or (
        "Analisi successoria internazionale" in visible
    )
    assert "Moudawana" in visible
    assert "650/2012" in visible


@pytest.mark.django_db
def test_tunisia_wizard_uses_public_status_panel():
    body = Client().get("/wizard/tn/inheritance/").content.decode("utf-8")
    visible = _visible(body)
    assert ("International inheritance review" in visible) or (
        "Analisi successoria internazionale" in visible
    )
    assert "Code du statut personnel" in visible
    assert "98-97" in visible


# ---------------------------------------------------------------------------
# 6 — result page never surfaces the technical token
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_result_page_does_not_surface_technical_status_token():
    """The unavailable card on the result page now reads from
    public_status. The raw technical status code must never appear in
    the visible body."""

    from apps.cases.forms import FranceRoadAccidentWizardForm
    from apps.cases.views import _run_france_road_accident

    form = FranceRoadAccidentWizardForm(
        {
            "accident_country": "FR",
            "consent_simulation": "on",
        }
    )
    assert form.is_valid(), form.errors

    class _Req:
        method = "POST"
        user = type("U", (), {"is_authenticated": False})()
        path = "/wizard/fr/road-accident/"
        META = {}

    sim = _run_france_road_accident(_Req(), form)

    body = Client().get(f"/wizard/result/{sim.public_id}/").content.decode("utf-8")
    visible = _visible(body)
    assert "unavailable_requires_legal_validation" not in visible.lower()
    assert "missing_documents" not in visible.lower()


# ---------------------------------------------------------------------------
# 7 — no banned public words
# ---------------------------------------------------------------------------


PRINCIPAL_PATHS = [
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
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
def test_pass7_principal_pages_have_no_banned_words(locale_prefix):
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
# 8 — no FR / AR English fallback on the wizard pages
# ---------------------------------------------------------------------------


HIGH_PRIORITY_EN = (
    "Preliminary legal assessment",
    "International inheritance review",
    "Studio reviews each",
    "applicable-law mapping",
    "Submit the case to the Studio",
    "Recognised quantification",
    "Applicable framework",
)


@pytest.mark.django_db
@pytest.mark.parametrize("locale_prefix", ["/fr", "/ar"])
def test_pass7_translated_locales_no_english_fallback(locale_prefix):
    client = Client()
    for path in PRINCIPAL_PATHS:
        body = client.get(locale_prefix + path).content.decode("utf-8", errors="replace")
        visible = _visible(body)
        for phrase in HIGH_PRIORITY_EN:
            assert phrase not in visible, f"{locale_prefix}{path}: surfaces EN fallback {phrase!r}"


# ---------------------------------------------------------------------------
# 9 — no duplicate H1 on the four new wizard pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRINCIPAL_PATHS)
def test_pass7_wizards_have_single_h1(path):
    body = Client().get(path).content.decode("utf-8")
    h1_count = len(re.findall(r"<h1[\s>]", body, flags=re.IGNORECASE))
    assert h1_count == 1, f"{path}: expected 1 H1, found {h1_count}"


# ---------------------------------------------------------------------------
# 10 — no Pexels attribution leak
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRINCIPAL_PATHS)
def test_pass7_wizards_have_no_pexels_attribution(path):
    body = Client().get(path).content.decode("utf-8", errors="replace")
    visible = _visible(body)
    assert "Photo by" not in visible, f"{path}: Pexels caption leak"
    assert "pexels.com/" not in body.lower(), f"{path}: Pexels link leak"


# ---------------------------------------------------------------------------
# 11 — Italia 35/10/0 unchanged
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
        slug="it-pass7-fixture",
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
        name="TUN base pass7",
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
        name="TUN moral pass7",
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
        code="italy_art_138_tun_2025_pass7",
        name="pass7",
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
def test_italy_smoke_unchanged_after_pass7(italy_calculator_fixture):
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
