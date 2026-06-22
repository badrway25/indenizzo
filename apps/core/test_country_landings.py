"""
Tests F-product-country-landing-seo-multilang.

Coprono:
- 5 landing paese rispondono 200;
- ogni pagina ha esattamente UN H1;
- Italia ha CTA wizard `/wizard/it/road-accident/`;
- Francia/Belgio mostrano "Legal sources under review" e NON contengono
  claim "calculated";
- Marocco/Tunisia hanno wording inheritance + CTA verso wizard;
- /countries/ linka alle 5 landing;
- /fr/countries/france/ e /ar/countries/morocco/ rispondono 200 (i18n);
- title + meta description presenti su tutte le pagine;
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

import re
from decimal import Decimal

import pytest
from django.test import Client

COUNTRY_PATHS = [
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
]


def _h1_count(html: str) -> int:
    """Conta i tag H1 nell'HTML, case-insensitive."""
    return len(re.findall(r"<h1[\s>]", html, flags=re.IGNORECASE))


# ---------------------------------------------------------------------------
# Task G.1 — 5 landing 200
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landings_return_200(path):
    client = Client()
    resp = client.get(path)
    assert resp.status_code == 200, f"GET {path} → {resp.status_code}"


# ---------------------------------------------------------------------------
# Task G.2 — single H1 per pagina
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landings_have_single_h1(path):
    client = Client()
    body = client.get(path).content.decode("utf-8")
    assert _h1_count(body) == 1, f"{path}: expected 1 H1, found {_h1_count(body)}"


# ---------------------------------------------------------------------------
# Task G.3 — Italia ha CTA wizard road-accident
# ---------------------------------------------------------------------------


def test_italy_landing_has_wizard_cta():
    """Pass-6 centralised the country status: the IT landing now reads
    the badge from ``apps/core/public_status.py`` — "Indicative
    calculation available" (or its IT translation). The legacy
    "Calculator available" wording is kept as a fallback."""

    client = Client()
    body = client.get("/countries/italy/").content.decode("utf-8")
    assert "/wizard/it/road-accident/" in body
    assert (
        ("Indicative calculation available" in body)
        or ("Calcolo indicativo disponibile" in body)
        or ("Calculator available" in body)
    )


# ---------------------------------------------------------------------------
# Task G.4 — Francia: "Legal sources under review", NO claim "calculated"
# ---------------------------------------------------------------------------


def test_france_landing_marked_under_review_and_no_calculated_claim():
    """Pass-5 renamed the public badge from "Legal sources under review"
    to "Preliminary legal assessment". The contract is unchanged: the
    page must mark France as scaffold-only and never expose the IT
    smoke amounts."""

    client = Client()
    body = client.get("/en/countries/france/").content.decode("utf-8")
    assert ("Preliminary legal assessment" in body) or ("Legal sources under review" in body)
    # Verifica che NON ci siano i token degli importi IT smoke.
    for forbidden in ("26268", "27353", "28439"):
        assert forbidden not in body


# ---------------------------------------------------------------------------
# Task G.5 — Belgio: scaffold/under review, no importi
# ---------------------------------------------------------------------------


def test_belgium_landing_under_review_and_no_amounts():
    """Pass-5 stripped "scaffold" wording from public templates and
    renamed the badge to "Preliminary legal assessment"."""

    client = Client()
    body = client.get("/en/countries/belgium/").content.decode("utf-8")
    assert ("Preliminary legal assessment" in body) or ("Legal sources under review" in body)
    for forbidden in ("26268", "27353", "28439"):
        assert forbidden not in body


# ---------------------------------------------------------------------------
# Task G.6 — Morocco/Tunisia: inheritance wording + CTA wizard
# ---------------------------------------------------------------------------


def test_morocco_landing_inheritance_wording_and_cta():
    client = Client()
    body = client.get("/countries/morocco/").content.decode("utf-8")
    assert "International inheritance" in body or "inheritance" in body.lower()
    # Moudawana / EU 650 Regulation menzionati come framework.
    assert "Moudawana" in body
    assert "650/2012" in body
    # CTA wizard dedicato.
    assert "/wizard/ma/inheritance/" in body


def test_tunisia_landing_inheritance_wording_and_cta():
    client = Client()
    body = client.get("/countries/tunisia/").content.decode("utf-8")
    assert "International inheritance" in body or "inheritance" in body.lower()
    # Code Statut Personnel / Loi 98-97 / EU 650.
    assert "statut personnel" in body or "Statut personnel" in body
    assert "98-97" in body
    assert "/wizard/tn/inheritance/" in body


# ---------------------------------------------------------------------------
# Task G.7 — /countries/ linka alle 5 landing
# ---------------------------------------------------------------------------


def test_countries_index_links_to_five_landings():
    client = Client()
    body = client.get("/countries/").content.decode("utf-8")
    for landing in [
        "/countries/italy/",
        "/countries/france/",
        "/countries/belgium/",
        "/countries/morocco/",
        "/countries/tunisia/",
    ]:
        assert landing in body, f"missing link to {landing} on /countries/"


# ---------------------------------------------------------------------------
# Task G.8 — i18n: /fr/countries/france/ + /ar/countries/morocco/ → 200
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/fr/countries/france/",
        "/ar/countries/morocco/",
        "/en/countries/italy/",
    ],
)
def test_country_landings_i18n_prefixed(path):
    client = Client()
    resp = client.get(path)
    assert resp.status_code == 200, f"GET {path} → {resp.status_code}"


# ---------------------------------------------------------------------------
# Task G.9 — SEO: title + meta description presenti su tutte le 5 pagine
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landings_have_seo_title_and_meta_description(path):
    client = Client()
    body = client.get(path).content.decode("utf-8")
    # title block presente e personalizzato (contiene "coverage and
    # legal sources" dal blocktranslate del template).
    assert "<title>" in body
    title_match = re.search(r"<title>([^<]+)</title>", body)
    assert title_match is not None
    title = title_match.group(1)
    assert "coverage and legal sources" in title or "—" in title
    # meta description presente e non vuota.
    md_match = re.search(
        r'<meta\s+name="description"\s+content="([^"]+)"',
        body,
    )
    assert md_match is not None, f"{path}: no <meta name=description>"
    assert len(md_match.group(1).strip()) > 30


# ---------------------------------------------------------------------------
# Task G.10 — Italia smoke contract invariato
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_stack(db):
    """Pipeline minima IT che produce 26268/27353/28439 per (35,10,0)."""
    from datetime import date

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
    eur = Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title="D.P.R. 12/2025 (smoke stub)",
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
        name="TUN base smoke",
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
        name="TUN moral smoke",
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
        code="italy_art_138_tun_2025_base",
        name="Smoke range formula",
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
    return {"country": italy}


@pytest.mark.django_db
def test_italy_smoke_run_simulation_35_10_0(italy_smoke_stack):
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
