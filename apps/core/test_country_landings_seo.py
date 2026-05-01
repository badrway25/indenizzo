"""
Tests F-product-country-landing-pass2-canonical-hreflang.

Coprono:
- Italia/Francia landing contengono <link rel="canonical">;
- ogni landing contiene 5 hreflang (it/fr/en/ar/x-default);
- x-default punta alla versione default (italiana, no prefisso);
- /fr/countries/france/ → canonical contiene /fr/;
- /ar/countries/morocco/ → alternate hreflang="ar" presente;
- nessun hreflang duplicato sulla stessa pagina;
- 5 landing rispondono ancora 200;
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


def _extract_alternates(html: str) -> list[tuple[str, str]]:
    """Estrae [(lang, href), ...] dai tag <link rel=alternate hreflang=...>."""
    pattern = re.compile(
        r'<link\s+rel="alternate"\s+hreflang="([^"]+)"\s+href="([^"]+)"',
        flags=re.IGNORECASE,
    )
    return [(m.group(1), m.group(2)) for m in pattern.finditer(html)]


def _extract_canonical(html: str) -> str | None:
    m = re.search(
        r'<link\s+rel="canonical"\s+href="([^"]+)"',
        html,
        flags=re.IGNORECASE,
    )
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Task D.1 — Italia ha canonical
# ---------------------------------------------------------------------------


def test_italy_landing_has_canonical():
    body = Client().get("/countries/italy/").content.decode("utf-8")
    canonical = _extract_canonical(body)
    assert canonical is not None
    assert canonical.endswith("/countries/italy/")


# ---------------------------------------------------------------------------
# Task D.2 — Francia ha canonical
# ---------------------------------------------------------------------------


def test_france_landing_has_canonical():
    body = Client().get("/countries/france/").content.decode("utf-8")
    canonical = _extract_canonical(body)
    assert canonical is not None
    assert canonical.endswith("/countries/france/")


# ---------------------------------------------------------------------------
# Task D.3 — Ogni landing ha alternates it/fr/en/ar/x-default
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landings_have_all_hreflang_alternates(path):
    body = Client().get(path).content.decode("utf-8")
    alternates = _extract_alternates(body)
    langs = {lang for lang, _ in alternates}
    for required in ("it", "fr", "en", "ar", "x-default"):
        assert required in langs, f"{path}: missing hreflang={required}"


# ---------------------------------------------------------------------------
# Task D.4 — x-default punta alla versione italiana (default)
# ---------------------------------------------------------------------------


def test_x_default_points_to_italian_default_version():
    body = Client().get("/countries/italy/").content.decode("utf-8")
    alternates = dict(_extract_alternates(body))
    italian_href = alternates.get("it")
    x_default = alternates.get("x-default")
    assert italian_href is not None
    assert x_default == italian_href
    # Italian default = no prefix.
    assert "/it/" not in x_default
    assert x_default.endswith("/countries/italy/")


# ---------------------------------------------------------------------------
# Task D.5 — /fr/countries/france/ → canonical contiene /fr/
# ---------------------------------------------------------------------------


def test_french_prefixed_path_canonical_contains_fr_prefix():
    body = Client().get("/fr/countries/france/").content.decode("utf-8")
    canonical = _extract_canonical(body)
    assert canonical is not None
    assert "/fr/countries/france/" in canonical


# ---------------------------------------------------------------------------
# Task D.6 — /ar/countries/morocco/ ha alternate ar
# ---------------------------------------------------------------------------


def test_arabic_landing_has_arabic_alternate():
    body = Client().get("/ar/countries/morocco/").content.decode("utf-8")
    alternates = dict(_extract_alternates(body))
    ar_href = alternates.get("ar")
    assert ar_href is not None
    assert "/ar/countries/morocco/" in ar_href


# ---------------------------------------------------------------------------
# Task D.7 — Nessun hreflang duplicato sulla stessa pagina
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_no_duplicate_hreflang(path):
    body = Client().get(path).content.decode("utf-8")
    alternates = _extract_alternates(body)
    langs = [lang for lang, _ in alternates]
    assert len(langs) == len(set(langs)), f"{path}: duplicate hreflang in {langs}"


# ---------------------------------------------------------------------------
# Task D.8 — 5 landing restano 200
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landings_still_200(path):
    resp = Client().get(path)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Task D.9 — Italia smoke contract invariato
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
