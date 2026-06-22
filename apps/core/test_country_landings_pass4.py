"""
Tests F-product-country-landing-pass4-og-twitter-cards.

Coprono:
- ogni country landing emette og:title, og:description, og:url,
  og:type=website, og:site_name, og:locale, og:image, og:image:alt;
- og:url == canonical;
- og:locale:alternate copre le lingue ≠ corrente;
- og:image è URL assoluto;
- twitter:card=summary_large_image, twitter:title, twitter:description,
  twitter:image;
- FR/BE/MA/TN: og:title/description NON contengono "calculated" né
  numeri smoke IT;
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


def _meta_property(html: str, prop: str) -> str | None:
    """Estrae content di <meta property="<prop>" content="...">."""
    m = re.search(
        rf'<meta\s+property="{re.escape(prop)}"\s+content="([^"]*)"',
        html,
        flags=re.IGNORECASE,
    )
    return m.group(1) if m else None


def _meta_name(html: str, name: str) -> str | None:
    """Estrae content di <meta name="<name>" content="...">."""
    m = re.search(
        rf'<meta\s+name="{re.escape(name)}"\s+content="([^"]*)"',
        html,
        flags=re.IGNORECASE,
    )
    return m.group(1) if m else None


def _all_meta_property(html: str, prop: str) -> list[str]:
    return re.findall(
        rf'<meta\s+property="{re.escape(prop)}"\s+content="([^"]*)"',
        html,
        flags=re.IGNORECASE,
    )


# ---------------------------------------------------------------------------
# Task C.1 — og:title presente su ogni landing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landing_has_og_title(path):
    body = Client().get(path).content.decode("utf-8")
    og_title = _meta_property(body, "og:title")
    assert og_title is not None and len(og_title) > 5, f"{path}: missing og:title"


# ---------------------------------------------------------------------------
# Task C.2 — og:description presente
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landing_has_og_description(path):
    body = Client().get(path).content.decode("utf-8")
    og_desc = _meta_property(body, "og:description")
    assert og_desc is not None and len(og_desc) > 30, f"{path}: missing og:description"


# ---------------------------------------------------------------------------
# Task C.3 — og:url uguale a canonical
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landing_og_url_equals_canonical(path):
    body = Client().get(path).content.decode("utf-8")
    og_url = _meta_property(body, "og:url")
    canonical_match = re.search(
        r'<link\s+rel="canonical"\s+href="([^"]+)"',
        body,
        flags=re.IGNORECASE,
    )
    assert canonical_match is not None
    assert og_url == canonical_match.group(1)


# ---------------------------------------------------------------------------
# Task C.4 — og:type = website
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landing_og_type_is_website(path):
    body = Client().get(path).content.decode("utf-8")
    assert _meta_property(body, "og:type") == "website"


# ---------------------------------------------------------------------------
# Task C.5 — twitter:card = summary_large_image
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landing_twitter_card_is_summary_large_image(path):
    body = Client().get(path).content.decode("utf-8")
    assert _meta_name(body, "twitter:card") == "summary_large_image"


# ---------------------------------------------------------------------------
# Task C.6 — og:locale presente e coerente con lingua corrente
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,expected_locale",
    [
        ("/countries/italy/", "it_IT"),
        ("/fr/countries/france/", "fr_FR"),
        ("/en/countries/italy/", "en_US"),
        ("/ar/countries/morocco/", "ar_AR"),
    ],
)
def test_country_landing_og_locale_matches_current_language(path, expected_locale):
    body = Client().get(path).content.decode("utf-8")
    assert _meta_property(body, "og:locale") == expected_locale


# ---------------------------------------------------------------------------
# Task C.7 — og:locale:alternate per lingue diverse dalla corrente
# ---------------------------------------------------------------------------


def test_default_landing_has_locale_alternates_for_other_languages():
    body = Client().get("/countries/italy/").content.decode("utf-8")
    alternates = set(_all_meta_property(body, "og:locale:alternate"))
    # lingua corrente IT → alternates devono contenere fr/en/ar
    assert "fr_FR" in alternates
    assert "en_US" in alternates
    assert "ar_AR" in alternates
    # NON deve contenere la lingua corrente
    assert "it_IT" not in alternates


def test_arabic_landing_has_locale_alternates_for_other_languages():
    body = Client().get("/ar/countries/morocco/").content.decode("utf-8")
    alternates = set(_all_meta_property(body, "og:locale:alternate"))
    assert "it_IT" in alternates
    assert "fr_FR" in alternates
    assert "en_US" in alternates
    assert "ar_AR" not in alternates


# ---------------------------------------------------------------------------
# Task C.8 — og:image è URL assoluto
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landing_og_image_is_absolute_url(path):
    body = Client().get(path).content.decode("utf-8")
    og_image = _meta_property(body, "og:image")
    assert og_image is not None
    # URL assoluto: deve iniziare con http:// o https://
    assert og_image.startswith(("http://", "https://")), f"og:image not absolute: {og_image!r}"
    # og:image è una risorsa OG valida. La logica reale
    # (`apps.core.seo._resolve_og_image_static_path`) sceglie, in ordine:
    #   1. la PNG country-specific `static/img/og/og-<slug>.png`,
    #   2. il default `static/img/og/og-country-default.png`,
    #   3. il fallback SVG `static/img/og-country-default.svg`,
    # e in `_render_country_landing` può fare override su una Pexels image
    # cached (`/media/pexels/...`) quando il media è presente. Su un checkout
    # senza media Pexels (es. CI) si ricade sulla PNG static country-specific:
    # accettiamo tutte queste forme valide, senza ipotizzare la presenza del
    # media.
    assert (
        ("/static/img/og/" in og_image)  # country-specific or default PNG
        or ("og-country-default" in og_image)  # default PNG or SVG fallback
        or ("/media/pexels/" in og_image)  # Pexels override (media present)
    ), f"og:image is not a recognised OG asset: {og_image!r}"
    # Coerenza twitter:image
    assert _meta_name(body, "twitter:image") == og_image


# ---------------------------------------------------------------------------
# Task C.9 — FR/BE/MA/TN: og:title/description non contengono claim vietati
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/countries/france/", "/countries/belgium/", "/countries/morocco/", "/countries/tunisia/"],
)
def test_scaffold_country_og_metadata_has_no_calculated_claim(path):
    body = Client().get(path).content.decode("utf-8")
    og_title = (_meta_property(body, "og:title") or "").lower()
    og_desc = (_meta_property(body, "og:description") or "").lower()
    tw_title = (_meta_name(body, "twitter:title") or "").lower()
    tw_desc = (_meta_name(body, "twitter:description") or "").lower()
    for blob in (og_title, og_desc, tw_title, tw_desc):
        assert "calculated estimate available" not in blob
        assert "calculated" not in blob
    # Niente importi smoke IT in alcun og/twitter content.
    for forbidden in ("26268", "27353", "28439"):
        for blob in (og_title, og_desc, tw_title, tw_desc):
            assert forbidden not in blob


# ---------------------------------------------------------------------------
# Task C.10 — og:site_name presente
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landing_has_og_site_name(path):
    body = Client().get(path).content.decode("utf-8")
    site_name = _meta_property(body, "og:site_name")
    assert site_name is not None and len(site_name) > 0


# ---------------------------------------------------------------------------
# Task C.11 — niente tag duplicati che contano come unici
#
# og:title, og:description, og:url, og:type, og:site_name, og:image,
# og:locale, og:image:alt: ognuno deve apparire UNA sola volta.
# (og:locale:alternate può apparire N volte — è il punto.)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", COUNTRY_PATHS)
def test_country_landing_has_no_duplicate_singleton_og_tags(path):
    body = Client().get(path).content.decode("utf-8")
    for prop in (
        "og:title",
        "og:description",
        "og:url",
        "og:type",
        "og:site_name",
        "og:image",
        "og:locale",
        "og:image:alt",
    ):
        assert len(_all_meta_property(body, prop)) == 1, f"{path}: {prop} duplicated"


# ---------------------------------------------------------------------------
# Task C.12 — Italia smoke contract invariato
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
