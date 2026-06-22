"""
Tests F-product-og-images-pass1.

Coprono:
- script generate_og_images.py produce 6 PNG 1200×630;
- og:image per Italy termina con og-italy.png (no Pexels manifest);
- og:image per France termina con og-france.png;
- og:image fallback default PNG quando country_code è None;
- twitter:image è PNG;
- og:image:width=1200 e og:image:height=630 quando PNG;
- HTML non contiene PEXELS_API_KEY anche con valore stringente;
- HTML non contiene "Photo by" / "on Pexels";
- FR/BE/MA/TN OG title/description senza claim "calculated";
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.test import Client, override_settings

# ---------------------------------------------------------------------------
# A.1 — i 6 PNG esistono e sono 1200×630
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "og-country-default.png",
        "og-italy.png",
        "og-france.png",
        "og-belgium.png",
        "og-morocco.png",
        "og-tunisia.png",
    ],
)
def test_og_png_exists_and_is_1200x630(filename):
    """Tutti i PNG OG generati esistono in static/img/og/ e sono 1200×630."""
    from PIL import Image

    p = Path(django_settings.BASE_DIR) / "static" / "img" / "og" / filename
    assert p.exists(), f"missing {p}"
    with Image.open(p) as img:
        assert img.size == (1200, 630), f"{filename}: got {img.size} (want 1200×630)"


# ---------------------------------------------------------------------------
# A.2 — og:image country-specific quando manifest Pexels NON c'è
# ---------------------------------------------------------------------------


def _meta_property(html: str, prop: str) -> str | None:
    m = re.search(
        rf'<meta\s+property="{re.escape(prop)}"\s+content="([^"]*)"',
        html,
        flags=re.IGNORECASE,
    )
    return m.group(1) if m else None


def _meta_name(html: str, name: str) -> str | None:
    m = re.search(
        rf'<meta\s+name="{re.escape(name)}"\s+content="([^"]*)"',
        html,
        flags=re.IGNORECASE,
    )
    return m.group(1) if m else None


@pytest.mark.parametrize(
    "path,expected_filename",
    [
        ("/countries/italy/", "og-italy.png"),
        ("/countries/france/", "og-france.png"),
        ("/countries/belgium/", "og-belgium.png"),
        ("/countries/morocco/", "og-morocco.png"),
        ("/countries/tunisia/", "og-tunisia.png"),
    ],
)
def test_og_image_uses_country_png_when_no_manifest(path, expected_filename, tmp_path, settings):
    """Senza Pexels manifest, og:image punta al PNG country-specific."""
    settings.MEDIA_ROOT = str(tmp_path)  # manifest assente in tmp_path
    body = Client().get(path).content.decode("utf-8")
    og_image = _meta_property(body, "og:image")
    assert og_image is not None
    assert og_image.endswith(
        f"/static/img/og/{expected_filename}"
    ), f"{path}: og:image={og_image!r}"
    # twitter:image deve coincidere
    tw_image = _meta_name(body, "twitter:image")
    assert tw_image == og_image
    # PNG → og:image:width=1200 e og:image:height=630 presenti
    assert _meta_property(body, "og:image:width") == "1200"
    assert _meta_property(body, "og:image:height") == "630"


# ---------------------------------------------------------------------------
# A.3 — twitter:image è PNG (non SVG, non JPG remoto Pexels) quando no
# manifest
# ---------------------------------------------------------------------------


def test_twitter_image_is_png_no_manifest(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    body = Client().get("/countries/italy/").content.decode("utf-8")
    tw_image = _meta_name(body, "twitter:image")
    assert tw_image is not None
    assert tw_image.endswith(".png")
    # Niente .svg di fallback dato che il PNG default + country PNG esistono
    assert not tw_image.endswith(".svg")


# ---------------------------------------------------------------------------
# A.4 — og:image fallback PNG default quando country_code = None
# ---------------------------------------------------------------------------


def test_resolve_og_image_static_path_picks_country_then_default():
    """Helper unit: country-specific PNG > default PNG > SVG."""
    from apps.core.seo import _resolve_og_image_static_path

    # Tutti i 6 PNG sono presenti → ci aspettiamo og-italy.png per IT.
    assert _resolve_og_image_static_path("italy") == "img/og/og-italy.png"
    assert _resolve_og_image_static_path("france") == "img/og/og-france.png"
    # country_code = None → default PNG
    assert _resolve_og_image_static_path(None) == "img/og/og-country-default.png"
    # country sconosciuto → default PNG
    assert _resolve_og_image_static_path("zzz") == "img/og/og-country-default.png"


# ---------------------------------------------------------------------------
# A.5 — pagine pubbliche: niente "Photo by" / "on Pexels"
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    ["/countries/italy/", "/countries/france/", "/countries/morocco/", "/wizard/"],
)
def test_og_pages_have_no_visible_attribution(path):
    body = Client().get(path).content.decode("utf-8")
    assert "Photo by" not in body
    assert "on Pexels" not in body


# ---------------------------------------------------------------------------
# A.6 — API key non in HTML
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PEXELS_API_KEY="OG-PASS1-LEAK-TEST-KEY-987654321")
@pytest.mark.parametrize(
    "path",
    ["/countries/italy/", "/countries/france/", "/countries/morocco/", "/"],
)
def test_og_pages_no_api_key_leak(path):
    body = Client().get(path).content.decode("utf-8")
    assert "OG-PASS1-LEAK-TEST-KEY-987654321" not in body


# ---------------------------------------------------------------------------
# A.7 — FR/BE/MA/TN: og:title/og:description non promettono calculated
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    ["/countries/france/", "/countries/belgium/", "/countries/morocco/", "/countries/tunisia/"],
)
def test_og_scaffold_country_no_calculated_claim(path, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    body = Client().get(path).content.decode("utf-8")
    og_title = (_meta_property(body, "og:title") or "").lower()
    og_desc = (_meta_property(body, "og:description") or "").lower()
    tw_title = (_meta_name(body, "twitter:title") or "").lower()
    tw_desc = (_meta_name(body, "twitter:description") or "").lower()
    for blob in (og_title, og_desc, tw_title, tw_desc):
        assert "calculated estimate available" not in blob
        assert "calculated" not in blob


# ---------------------------------------------------------------------------
# A.8 — Quando Pexels manifest presente, og:image è il media file e NON ci
# sono og:image:width/height (dimensioni JPG arbitrarie).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_og_image_uses_pexels_media_when_manifest_present(tmp_path, settings):
    import json

    settings.MEDIA_ROOT = str(tmp_path)
    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    (pexels_dir / "country_landing__it__1.jpg").write_bytes(b"x")
    manifest = {
        "country_landing::IT": {
            "purpose": "country_landing",
            "country_code": "IT",
            "query": "x",
            "local_path": "pexels/country_landing__it__1.jpg",
            "photo_id": 1,
            "photographer": "x",
            "photographer_url": "",
            "pexels_url": "",
            "alt": "x",
            "width": 1920,
            "height": 1080,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "x",
            "extra": {},
        }
    }
    (pexels_dir / "pexels_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    body = Client().get("/countries/italy/").content.decode("utf-8")
    og_image = _meta_property(body, "og:image") or ""
    assert "/media/pexels/country_landing__it__1.jpg" in og_image
    # Width/height dropped (JPG dimensions arbitrary)
    assert _meta_property(body, "og:image:width") is None
    assert _meta_property(body, "og:image:height") is None


# ---------------------------------------------------------------------------
# A.9 — Italia smoke contract invariato
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_og(db):
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
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=italian,
    )
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title="D.P.R. 12/2025",
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
        code="italy_art_138_tun_2025_base",
        name="smoke",
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
def test_og_italy_smoke_run_simulation(italy_smoke_og):
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
