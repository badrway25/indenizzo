"""Tests F-frontend-remove-tailwind-cdn-runtime-pass2.

Cover the complete removal of the Tailwind CDN runtime: every public
page must render premium with the local ``static/css/site.css``
alone, no external script tag for ``cdn.tailwindcss.com``.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse

PUBLIC_PATHS = (
    "/",
    "/countries/",
    "/countries/italy/",
    "/countries/france/",
    "/countries/morocco/",
    "/case-types/",
    "/methodology/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
)


# ---------------------------------------------------------------------------
# 1 — base.html does not reference cdn.tailwindcss.com
# ---------------------------------------------------------------------------


def test_base_html_does_not_reference_tailwind_cdn():
    base = Path(__file__).resolve().parents[2] / "templates" / "base.html"
    text = base.read_text(encoding="utf-8")
    assert "cdn.tailwindcss.com" not in text
    assert "tailwind.config" not in text


# ---------------------------------------------------------------------------
# 2 — base.html includes static/css/site.css
# ---------------------------------------------------------------------------


def test_base_html_includes_local_css():
    base = Path(__file__).resolve().parents[2] / "templates" / "base.html"
    text = base.read_text(encoding="utf-8")
    assert "{% static 'css/site.css' %}" in text


# ---------------------------------------------------------------------------
# 3 — home page rendered HTML carries no CDN reference
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_home_page_html_carries_no_tailwind_cdn():
    body = Client().get("/").content.decode("utf-8")
    assert "cdn.tailwindcss.com" not in body
    assert "tailwind.config" not in body
    assert "/static/css/site.css" in body


# ---------------------------------------------------------------------------
# 4 — every public page returns 200 and references the local stylesheet
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_public_pages_return_200_and_link_local_css():
    client = Client()
    for path in PUBLIC_PATHS:
        response = client.get(path)
        assert response.status_code == 200, f"{path} -> {response.status_code}"
        body = response.content.decode("utf-8")
        assert "/static/css/site.css" in body
        assert "cdn.tailwindcss.com" not in body


# ---------------------------------------------------------------------------
# 5 — local CSS file contains required selectors
# ---------------------------------------------------------------------------


def test_site_css_contains_required_selectors():
    css_path = Path(__file__).resolve().parents[2] / "static" / "css" / "site.css"
    text = css_path.read_text(encoding="utf-8")
    required = (
        "--ink-950",
        "--gold-500",
        "--sand-50",
        "--shadow-card",
        ".max-w-3xl",
        ".rounded-3xl",
        ".shadow-card",
        ".bg-sand-50",
        ".grid-cols-3",
        ".sm\\:grid-cols-3",
        ".sm\\:grid-cols-2",
        ".lg\\:grid-cols-3",
        # pass-2 additions
        ".tracking-\\[0\\.18em\\]",
        ".tracking-\\[0\\.22em\\]",
        ".w-1\\.5",
        ".h-1\\.5",
        ".bg-ok-600\\/10",
        ".bg-gold-500\\/15",
        ".border-ink-950\\/15",
    )
    for needle in required:
        assert needle in text, f"site.css missing {needle!r}"


# ---------------------------------------------------------------------------
# 6 — no banned public words on the public pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_banned_public_words():
    banned = (
        "scaffold",
        "placeholder",
        "under validation",
        "in preparation",
        "coming soon",
        "work in progress",
        "module pending",
        "engine pending",
        "missing_documents",
        "unavailable_requires_legal_validation",
    )
    for path in PUBLIC_PATHS:
        body = Client().get(path).content.decode("utf-8").lower()
        for word in banned:
            assert word not in body, f"{path} surfaces banned word {word!r}"


# ---------------------------------------------------------------------------
# 7 — no Pexels attribution
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_pexels_attribution():
    for path in PUBLIC_PATHS:
        body = Client().get(path).content.decode("utf-8")
        assert "pexels.com" not in body.lower()
        assert not ("Photo by" in body and "Pexels" in body)


# ---------------------------------------------------------------------------
# 8 — no API key leak
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_api_key_leak():
    for path in PUBLIC_PATHS:
        body = Client().get(path).content.decode("utf-8")
        for needle in ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY"):
            assert needle not in body, f"{path} leaks {needle!r}"


# ---------------------------------------------------------------------------
# 9 — no duplicate H1 across public pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_duplicate_h1():
    for path in PUBLIC_PATHS:
        body = Client().get(path).content.decode("utf-8")
        h1s = re.findall(r"<h1\b", body, flags=re.IGNORECASE)
        assert len(h1s) == 1, f"{path} has {len(h1s)} H1 tags, expected 1"


# ---------------------------------------------------------------------------
# 10 — Italia smoke unchanged + 11 — PDF IT %PDF
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
        slug="it-fixture-cdn-removal",
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
        code="italy_art_138_tun_2025_cdn_removal",
        name="cdn-removal-smoke",
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
def test_italy_smoke_unchanged_after_cdn_removal(italy_full_setup):
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


@pytest.mark.django_db
def test_italy_pdf_remains_valid_after_cdn_removal(italy_full_setup):
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
    )
    response = Client().get(
        reverse("reports:simulation_pdf", kwargs={"public_id": str(sim.public_id)})
    )
    assert response.status_code == 200
    content = b"".join(response.streaming_content)
    assert content.startswith(b"%PDF")
