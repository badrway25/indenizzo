"""
Tests F-product-premium-visual-i18n-pass2-real-images-and-copy.

Coprono:
- pagine principali rispondono 200;
- nessuna pagina pubblica renderizza "Photo by" o "on Pexels";
- API key Pexels non compare in HTML;
- /fr/ contiene molte traduzioni reali (>= soglia pass2);
- /ar/countries/morocco/ ha dir=rtl + parole arabe reali (>= soglia);
- FR/BE/MA/TN: niente claim "calculated estimate available";
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client, override_settings


def _mo_compiled(lang: str) -> bool:
    base = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.mo"
    return base.exists() and base.stat().st_size > 100


PUBLIC_PATHS = [
    "/",
    "/countries/",
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
    "/methodology/",
    "/wizard/",
    "/contact/",
]


# ---------------------------------------------------------------------------
# H.1 — pagine principali 200
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_pass2_public_page_returns_200(path):
    resp = Client().get(path)
    assert resp.status_code == 200, f"GET {path} -> {resp.status_code}"


# ---------------------------------------------------------------------------
# H.2 — niente "Photo by" / "on Pexels" su nessuna pagina
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_pass2_no_visible_pexels_attribution(path):
    body = Client().get(path).content.decode("utf-8")
    assert "Photo by" not in body
    assert "on Pexels" not in body


# ---------------------------------------------------------------------------
# H.3 — API key non in HTML
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PEXELS_API_KEY="PASS2-SECRET-KEY-NEVER-LEAK-XYZABC123")
@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_pass2_api_key_never_appears(path):
    body = Client().get(path).content.decode("utf-8")
    assert "PASS2-SECRET-KEY-NEVER-LEAK-XYZABC123" not in body


# ---------------------------------------------------------------------------
# H.4 — FR contiene molte traduzioni reali (>=5 markers su /fr/countries/france/)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _mo_compiled("fr"), reason="locale/fr .mo not compiled")
def test_pass2_french_landing_has_dense_translations():
    body = Client().get("/fr/countries/france/").content.decode("utf-8")
    fr_markers = [
        "Pays",
        "Méthodologie",
        "Demander une revue juridique",
        "Statut",
        "Base juridique",
        "Accueil",
        "Comment procéder",
        "Sources juridiques en cours de revue",
        "Option 1",
        "Option 2",
    ]
    matched = [m for m in fr_markers if m.lower() in body.lower()]
    assert len(matched) >= 5, f"expected at least 5 French translations, found {matched}"


# ---------------------------------------------------------------------------
# H.5 — AR è RTL + traduzioni arabe reali (>=5 markers)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _mo_compiled("ar"), reason="locale/ar .mo not compiled")
def test_pass2_arabic_landing_is_rtl_and_translated():
    body = Client().get("/ar/countries/morocco/").content.decode("utf-8")
    assert 'dir="rtl"' in body
    arabic_markers = [
        "البلدان",
        "الرئيسية",
        "الحالة",
        "الأساس القانوني",
        "اطلب مراجعة قانونية",
        "كيفية المتابعة",
        "المصادر القانونية قيد المراجعة",
        "الخيار",
    ]
    matched = [m for m in arabic_markers if m in body]
    assert len(matched) >= 5, f"expected at least 5 AR translations, found {matched}"


# ---------------------------------------------------------------------------
# H.6 — FR/BE/MA/TN no "calculated" claim
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/countries/france/",
        "/countries/belgium/",
        "/countries/morocco/",
        "/countries/tunisia/",
    ],
)
def test_pass2_scaffold_landings_no_calculated_claim(path):
    body = Client().get(path).content.decode("utf-8").lower()
    assert "calculated estimate available" not in body
    for forbidden in ("26268", "27353", "28439"):
        assert forbidden not in body


# ---------------------------------------------------------------------------
# H.7 — manifest hero present → image renders, otherwise fallback
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pass2_home_hero_image_when_manifest_present(tmp_path, settings):
    import json

    settings.MEDIA_ROOT = str(tmp_path)
    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    (pexels_dir / "home_hero__global__1.jpg").write_bytes(b"x")
    manifest = {
        "home_hero::GLOBAL": {
            "purpose": "home_hero",
            "country_code": None,
            "query": "elegant law office interior",
            "local_path": "pexels/home_hero__global__1.jpg",
            "photo_id": 1,
            "photographer": "Internal",
            "photographer_url": "https://www.pexels.com/@x",
            "pexels_url": "https://www.pexels.com/photo/1/",
            "alt": "Elegant law office",
            "width": 1920,
            "height": 1080,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "x",
            "extra": {"size_bytes": 1},
        }
    }
    (pexels_dir / "pexels_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    body = Client().get("/").content.decode("utf-8")
    assert "/media/pexels/home_hero__global__1.jpg" in body


@pytest.mark.django_db
def test_pass2_pages_render_without_manifest(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    for path in ("/", "/countries/", "/methodology/", "/wizard/", "/contact/"):
        resp = Client().get(path)
        assert resp.status_code == 200
        # Niente broken /media/pexels/ refs nel body
        assert "/media/pexels/" not in resp.content.decode(
            "utf-8"
        ), f"{path}: pexels refs leaked when manifest missing"


# ---------------------------------------------------------------------------
# H.8 — start italy CTA visibile sulla home
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_pass2_home_has_start_italy_cta_link():
    """Home deve linkare al wizard IT (CTA primaria pass2)."""
    body = Client().get("/").content.decode("utf-8")
    assert "/wizard/it/road-accident/" in body


# ---------------------------------------------------------------------------
# H.9 — Italia smoke contract invariato
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_stack_pass2(db):
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
def test_pass2_italy_smoke_run_simulation_35_10_0(italy_smoke_stack_pass2):
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


# ---------------------------------------------------------------------------
# H.10 — html lang attribute coerente con la URL prefix
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path,expected_lang",
    [("/", "it"), ("/fr/", "fr"), ("/en/", "en"), ("/ar/", "ar")],
)
def test_pass2_html_lang_matches_url(path, expected_lang):
    body = Client().get(path).content.decode("utf-8")
    assert re.search(rf'<html\s+lang="{expected_lang}"', body) is not None
