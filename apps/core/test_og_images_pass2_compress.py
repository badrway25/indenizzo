"""
Tests F-product-og-images-pass2-compress.

Coprono il post-condition dell'iter di ottimizzazione lossless dei PNG
Open Graph:

1. tutti i 6 PNG esistono in `static/img/og/`;
2. tutti sono 1200×630;
3. tutti sono PNG validi (signature + header parsabile);
4. `scripts/optimize_og_images.py --check` esce 0 (i file sono già al
   minimo raggiungibile dal tool installato → idempotenza);
5. `og:image` continua a puntare a un `.png` country-specific quando
   il manifest Pexels non c'è;
6. `PEXELS_API_KEY` non appare in HTML su nessuna landing;
7. niente "Photo by"/"on Pexels" visibile sulle landing;
8. lo smoke Italia 35/10/0 resta 26 268 / 27 353 / 28 439 EUR.

Lo script di ottimizzazione è esecutabile senza Django (pure Pillow +
opzionale `pyoxipng`); i test che lo invocano usano `subprocess` per
non dipendere da side-effect dell'import.
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings as django_settings
from django.test import Client, override_settings

OG_FILENAMES = [
    "og-country-default.png",
    "og-italy.png",
    "og-france.png",
    "og-belgium.png",
    "og-morocco.png",
    "og-tunisia.png",
]


def _og_path(filename: str) -> Path:
    return Path(django_settings.BASE_DIR) / "static" / "img" / "og" / filename


# ---------------------------------------------------------------------------
# 1+2 — esistenza e dimensioni
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", OG_FILENAMES)
def test_og_png_exists_after_compression(filename):
    p = _og_path(filename)
    assert p.exists(), f"missing {p}"
    assert p.stat().st_size > 0


@pytest.mark.parametrize("filename", OG_FILENAMES)
def test_og_png_size_is_1200x630_after_compression(filename):
    from PIL import Image

    p = _og_path(filename)
    with Image.open(p) as img:
        assert img.size == (1200, 630), f"{filename}: got {img.size}"


# ---------------------------------------------------------------------------
# 3 — file is a valid PNG (signature + parseable)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("filename", OG_FILENAMES)
def test_og_png_is_valid_after_compression(filename):
    from PIL import Image

    p = _og_path(filename)
    raw = p.read_bytes()
    # PNG magic signature
    assert raw.startswith(b"\x89PNG\r\n\x1a\n"), f"{filename}: bad PNG signature"
    # Pillow can verify and re-open
    with Image.open(io.BytesIO(raw)) as img:
        img.verify()
    with Image.open(io.BytesIO(raw)) as img2:
        assert img2.format == "PNG"


# ---------------------------------------------------------------------------
# 4 — `optimize_og_images.py --check` passa (idempotenza)
# ---------------------------------------------------------------------------


def test_optimize_script_check_passes():
    script = Path(django_settings.BASE_DIR) / "scripts" / "optimize_og_images.py"
    assert script.exists()
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        cwd=str(django_settings.BASE_DIR),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert (
        result.returncode == 0
    ), f"--check failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"


# ---------------------------------------------------------------------------
# 5 — og:image continua a puntare a PNG country-specific (no Pexels manifest)
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
def test_og_image_still_points_to_png_after_compression(
    path, expected_filename, tmp_path, settings
):
    settings.MEDIA_ROOT = str(tmp_path)
    body = Client().get(path).content.decode("utf-8")
    og_image = _meta_property(body, "og:image")
    assert og_image is not None
    assert og_image.endswith(".png"), f"og:image not PNG: {og_image!r}"
    assert og_image.endswith(f"/static/img/og/{expected_filename}")


# ---------------------------------------------------------------------------
# 6 — API key never in HTML
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PEXELS_API_KEY="OG-PASS2-LEAK-TEST-KEY-555444333")
@pytest.mark.parametrize(
    "path",
    ["/countries/italy/", "/countries/morocco/", "/"],
)
def test_og_pages_no_api_key_leak_after_compression(path):
    body = Client().get(path).content.decode("utf-8")
    assert "OG-PASS2-LEAK-TEST-KEY-555444333" not in body


# ---------------------------------------------------------------------------
# 7 — no visible Pexels attribution after compression iter
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    ["/countries/italy/", "/countries/france/", "/countries/morocco/"],
)
def test_og_pages_have_no_visible_attribution_after_compression(path):
    body = Client().get(path).content.decode("utf-8")
    assert "Photo by" not in body
    assert "on Pexels" not in body


# ---------------------------------------------------------------------------
# 8 — Italia smoke 35/10/0 invariato
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_og_pass2(db):
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
def test_og_pass2_italy_smoke_run_simulation(italy_smoke_og_pass2):
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
