"""
Tests F-product-premium-visual-i18n-pass1.

Coprono:
- pagine principali rispondono 200;
- nessuna pagina pubblica renderizza "Photo by" o "on Pexels";
- API key Pexels non compare in HTML;
- hero image partial usato dove pexels_image presente, fallback altrove;
- /fr/countries/france/ contiene traduzione francese reale (skip se .mo
  manca);
- /ar/countries/morocco/ ha dir="rtl" e testo arabo reale (skip se .mo
  manca);
- FR/BE/MA/TN: niente claim "calculated estimate available";
- IT smoke 35/10/0 invariato.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client, override_settings


def _mo_compiled(lang: str) -> bool:
    """True se la traduzione è stata compilata in `.mo` per la lingua."""
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
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
    "/disclaimer/",
    "/privacy/",
]


# ---------------------------------------------------------------------------
# G.1 — pagine principali 200
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_public_page_returns_200(path):
    resp = Client().get(path)
    assert resp.status_code == 200, f"GET {path} -> {resp.status_code}"


# ---------------------------------------------------------------------------
# G.2 — niente "Photo by" / "on Pexels" sul sito pubblico
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_no_visible_pexels_attribution_anywhere(path):
    body = Client().get(path).content.decode("utf-8")
    assert "Photo by" not in body, f"{path}: 'Photo by' leaked"
    assert "on Pexels" not in body, f"{path}: 'on Pexels' leaked"


# ---------------------------------------------------------------------------
# G.3 — API key Pexels mai in HTML, anche con valore non vuoto
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PEXELS_API_KEY="STRICT-SECRET-NEVER-SHOW-ME-IN-HTML-XYZ")
@pytest.mark.parametrize("path", PUBLIC_PATHS)
def test_pexels_api_key_never_appears(path):
    body = Client().get(path).content.decode("utf-8")
    assert "STRICT-SECRET-NEVER-SHOW-ME-IN-HTML-XYZ" not in body


# ---------------------------------------------------------------------------
# G.4 — pagine principali renderizzano anche senza manifest Pexels
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PEXELS_API_KEY="")
@pytest.mark.parametrize("path", ["/", "/countries/", "/methodology/", "/wizard/", "/contact/"])
def test_pages_render_with_no_pexels_manifest(path, tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    resp = Client().get(path)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# G.5 — partial hero image renderizza se manifest presente
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_home_hero_image_when_manifest_present(tmp_path, settings):
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
            "photographer_url": "https://www.pexels.com/@internal",
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
    # Niente attribution visibile.
    assert "Photo by" not in body
    assert "Internal" not in body


# ---------------------------------------------------------------------------
# G.6 — /fr/countries/france/ contiene traduzione francese reale
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _mo_compiled("fr"), reason="locale/fr .mo not compiled")
def test_french_landing_has_french_translations():
    body = Client().get("/fr/countries/france/").content.decode("utf-8")
    # Almeno una stringa francese reale (dal nav o breadcrumb).
    french_markers = [
        "Pays",
        "Méthodologie",
        "Demander une revue juridique",
        "Statut",
        "Base juridique",
        "Accueil",
    ]
    matched = [m for m in french_markers if m in body]
    assert len(matched) >= 3, f"expected at least 3 French translations, found {matched}"


# ---------------------------------------------------------------------------
# G.7 — /ar/countries/morocco/ ha dir=rtl + testo arabo reale
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _mo_compiled("ar"), reason="locale/ar .mo not compiled")
def test_arabic_landing_is_rtl_and_translated():
    body = Client().get("/ar/countries/morocco/").content.decode("utf-8")
    assert 'dir="rtl"' in body
    arabic_markers = [
        "البلدان",
        "الرئيسية",
        "الحالة",
        "الأساس القانوني",
        "اطلب مراجعة قانونية",
    ]
    matched = [m for m in arabic_markers if m in body]
    assert len(matched) >= 3, f"expected at least 3 Arabic translations, found {matched}"


# ---------------------------------------------------------------------------
# G.8 — Italia smoke contract invariato
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


# ---------------------------------------------------------------------------
# G.9 — FR/BE/MA/TN no "calculated" claim
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
def test_scaffold_country_landings_have_no_calculated_claim_pass1(path):
    body = Client().get(path).content.decode("utf-8").lower()
    assert "calculated estimate available" not in body
    for forbidden in ("26268", "27353", "28439"):
        assert forbidden not in body


# ---------------------------------------------------------------------------
# G.10 — header link tradotti correttamente in IT
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not _mo_compiled("it"), reason="locale/it .mo not compiled")
def test_italian_default_has_italian_translations():
    body = Client().get("/").content.decode("utf-8")
    italian_markers = [
        "Paesi",
        "Tipi di caso",
        "Metodologia",
        "Richiedi una valutazione legale",
    ]
    matched = [m for m in italian_markers if m in body]
    assert len(matched) >= 3, f"expected at least 3 IT translations on home, found {matched}"


# ---------------------------------------------------------------------------
# G.11 — html lang attribute coerente con la URL
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path,expected_lang",
    [
        ("/", "it"),
        ("/fr/", "fr"),
        ("/en/", "en"),
        ("/ar/", "ar"),
    ],
)
def test_html_lang_attribute_matches_url_language(path, expected_lang):
    body = Client().get(path).content.decode("utf-8")
    assert re.search(rf'<html\s+lang="{expected_lang}"', body) is not None
