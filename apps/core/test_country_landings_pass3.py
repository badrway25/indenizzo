"""
Tests F-product-country-landing-pass3-sitemap-schema-ux-live.

Coprono:
- /sitemap.xml → 200 + XML;
- sitemap contiene le 5 country landing;
- sitemap NON contiene /admin/ né /staff/;
- 5 landing emettono uno script type="application/ld+json";
- JSON-LD è parseabile e ha @type=LegalService, name, url, serviceType;
- serviceType è coerente: Italia "compensation simulation",
  FR/BE "legal review", MA/TN "inheritance legal review";
- FR/BE/MA/TN non contengono claim "calculated" / numeri smoke IT;
- /countries/ index linka alle 5 landing;
- /ar/countries/morocco/ è servita con dir="rtl";
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

import json
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


def _extract_json_ld(html: str) -> dict | None:
    """Estrae il primo blocco <script type="application/ld+json">.

    Tollera attributi addizionali (es. `nonce="..."` aggiunto dal
    F-p0-codice-4-csp): il `type` puo' apparire in qualunque posizione
    tra gli attributi del tag.
    """
    m = re.search(
        r'<script\b[^>]*\btype="application/ld\+json"[^>]*>(.+?)</script>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except json.JSONDecodeError:
        return None


# ---------------------------------------------------------------------------
# Task F.1 — /sitemap.xml risponde 200 + content-type XML
# ---------------------------------------------------------------------------


def test_sitemap_returns_200_xml():
    resp = Client().get("/sitemap.xml")
    assert resp.status_code == 200
    ct = resp.get("Content-Type", "")
    assert "xml" in ct.lower(), f"unexpected Content-Type: {ct}"


# ---------------------------------------------------------------------------
# Task F.2 — sitemap contiene le 5 country landing
# ---------------------------------------------------------------------------


def test_sitemap_contains_five_country_landings():
    body = Client().get("/sitemap.xml").content.decode("utf-8")
    for path in COUNTRY_PATHS:
        assert path in body, f"sitemap missing {path}"


# ---------------------------------------------------------------------------
# Task F.3 — sitemap esclude back-office
# ---------------------------------------------------------------------------


def test_sitemap_excludes_admin_and_staff():
    body = Client().get("/sitemap.xml").content.decode("utf-8")
    assert "/admin/" not in body
    assert "/staff/" not in body


# ---------------------------------------------------------------------------
# Task F.4 — 5 landing hanno JSON-LD parseabile
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landings_emit_parseable_json_ld(path):
    body = Client().get(path).content.decode("utf-8")
    data = _extract_json_ld(body)
    assert data is not None, f"{path}: no parseable JSON-LD"
    assert data.get("@type") == "LegalService"
    assert data.get("name") == "Studio Legale Internazionale Badrane"
    assert "url" in data
    assert "serviceType" in data


# ---------------------------------------------------------------------------
# Task F.5 — JSON-LD url == canonical_url
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_json_ld_url_matches_canonical(path):
    body = Client().get(path).content.decode("utf-8")
    data = _extract_json_ld(body)
    canonical_match = re.search(
        r'<link\s+rel="canonical"\s+href="([^"]+)"',
        body,
        flags=re.IGNORECASE,
    )
    assert canonical_match is not None
    assert data is not None
    assert data["url"] == canonical_match.group(1)


# ---------------------------------------------------------------------------
# Task F.6 — serviceType italiano = compensation simulation
# ---------------------------------------------------------------------------


def test_italy_json_ld_service_type_is_compensation_simulation():
    body = Client().get("/countries/italy/").content.decode("utf-8")
    data = _extract_json_ld(body)
    assert data is not None
    assert "compensation simulation" in data["serviceType"].lower()
    assert data["areaServed"] == "Italy"


# ---------------------------------------------------------------------------
# Task F.7 — serviceType FR/BE = road accident legal review
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,country", [("/countries/france/", "France"), ("/countries/belgium/", "Belgium")]
)
def test_france_belgium_json_ld_service_type_is_legal_review(path, country):
    body = Client().get(path).content.decode("utf-8")
    data = _extract_json_ld(body)
    assert data is not None
    assert "legal review" in data["serviceType"].lower()
    assert "road accident" in data["serviceType"].lower()
    assert data["areaServed"] == country


# ---------------------------------------------------------------------------
# Task F.8 — serviceType MA/TN = international inheritance legal review
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,country", [("/countries/morocco/", "Morocco"), ("/countries/tunisia/", "Tunisia")]
)
def test_morocco_tunisia_json_ld_service_type_is_inheritance_review(path, country):
    body = Client().get(path).content.decode("utf-8")
    data = _extract_json_ld(body)
    assert data is not None
    assert "inheritance" in data["serviceType"].lower()
    assert "legal review" in data["serviceType"].lower()
    assert data["areaServed"] == country


# ---------------------------------------------------------------------------
# Task F.9 — FR/BE/MA/TN: no "calculated" claim né smoke IT amounts
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/countries/france/", "/countries/belgium/", "/countries/morocco/", "/countries/tunisia/"],
)
def test_scaffold_country_landings_have_no_calculated_claim(path):
    body = Client().get(path).content.decode("utf-8").lower()
    # Niente claim "calculated" attivo nel body. La parola "estimate"
    # può apparire nel testo "no automatic estimate is issued" — quindi
    # cerchiamo solo "calculated" come parola intera in contesti
    # affermativi. Approccio conservativo: la sostringa esatta
    # "calculated" non deve apparire (il template non la usa per
    # paesi scaffold).
    assert "calculated" not in body, f"{path}: 'calculated' leaked into scaffold landing"
    for forbidden in ("26268", "27353", "28439"):
        assert forbidden not in body, f"{path}: smoke IT amount {forbidden} leaked"


# ---------------------------------------------------------------------------
# Task F.10 — /countries/ index linka alle 5 landing
# ---------------------------------------------------------------------------


def test_countries_index_links_to_five_landings():
    body = Client().get("/countries/").content.decode("utf-8")
    for landing in COUNTRY_PATHS:
        assert landing in body, f"missing link to {landing} on /countries/"


# ---------------------------------------------------------------------------
# Task F.11 — /ar/countries/morocco/ è in RTL
# ---------------------------------------------------------------------------


def test_arabic_landing_is_rtl():
    body = Client().get("/ar/countries/morocco/").content.decode("utf-8")
    # base.html: <html lang="..." dir="rtl">.
    assert 'dir="rtl"' in body, "AR landing missing dir=rtl"
    # Coerenza: la risposta è 200.
    resp = Client().get("/ar/countries/morocco/")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Task F.12 — Italia smoke contract invariato
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
