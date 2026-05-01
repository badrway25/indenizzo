"""
Tests F-product-pexels-photo-id-freeze.

Coprono:
- tutti i 15 override hanno `photo_id` valorizzato (non null) e
  `approved_visual=True`;
- override file non contiene secret;
- precedence: override.photo_id batte override.query (no search call);
- precedence: CLI --photo-id batte override.photo_id;
- --audit mostra FROZEN_MATCH quando manifest e override coincidono e
  il file locale esiste;
- --audit mostra OVERRIDE_DIFFERS quando i photo_id divergono;
- --audit mostra UNPINNED se override esiste ma photo_id è null;
- --audit non leak la API key;
- pagine pubbliche: niente "Photo by" / "on Pexels";
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

import json
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.test import Client, override_settings

# ---------------------------------------------------------------------------
# A.1 — tutti i 15 slot SITE_IMAGE_SLOTS hanno override.photo_id valido
# ---------------------------------------------------------------------------


def test_all_slots_have_frozen_photo_id_in_overrides():
    """Ogni slot di SITE_IMAGE_SLOTS deve avere photo_id e approved_visual."""
    from apps.core import pexels

    overrides = pexels.load_overrides()
    missing = []
    not_approved = []
    for slot in pexels.SITE_IMAGE_SLOTS:
        key = pexels.override_lookup_key(slot["purpose"], slot.get("country"))
        over = overrides.get(key, {}) or {}
        if not over.get("photo_id"):
            missing.append(key)
        if not over.get("approved_visual"):
            not_approved.append(key)
    assert not missing, f"Slot senza photo_id congelato: {missing}"
    assert not not_approved, f"Slot senza approved_visual=True: {not_approved}"


# ---------------------------------------------------------------------------
# A.2 — override file non contiene secret né API key references
# ---------------------------------------------------------------------------


def test_override_file_no_secret_after_freeze():
    raw = (Path("config") / "pexels_image_overrides.json").read_text(encoding="utf-8")
    for token in ("PEXELS_API_KEY", "Authorization", "Bearer ", "secret", "api_key"):
        assert token.lower() not in raw.lower(), f"override file leaked '{token}'"


# ---------------------------------------------------------------------------
# A.3 — precedence: override.photo_id batte override.query (no search call)
# ---------------------------------------------------------------------------


def _fake_photo_response(photo_id=99999, alt="Test", url="https://example/x"):
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {
        "id": photo_id,
        "width": 4000,
        "height": 2667,
        "photographer": "Test",
        "photographer_url": "https://www.pexels.com/@x",
        "url": url,
        "alt": alt,
        "src": {
            "original": "https://images.pexels.com/o.jpg",
            "large2x": "https://images.pexels.com/l2.jpg",
            "large": "https://images.pexels.com/l.jpg",
            "landscape": "https://images.pexels.com/lan.jpg",
        },
    }
    return fake


def _fake_cdn_response():
    fake = MagicMock()
    fake.status_code = 200
    fake.iter_content = lambda chunk_size=8192: [b"x" * 64]
    return fake


@override_settings(PEXELS_API_KEY="testkey-precedence")
def test_override_photo_id_beats_query(tmp_path, settings):
    """Quando override ha photo_id, fetch_one_slot usa /v1/photos/{id} e NON cerca."""
    settings.MEDIA_ROOT = str(tmp_path)
    captured: dict = {"urls": []}

    def fake_request(method, url, **kwargs):
        captured["urls"].append(url)
        # photos/{id} endpoint → photo detail; search endpoint → list
        if "/photos/" in url and "/search" not in url:
            return _fake_photo_response(photo_id=11111)
        # Should not be called!
        return MagicMock(status_code=200, json=lambda: {"photos": []})

    overrides_payload = {
        "wizard_start_hero": {
            "query": "should-not-be-used",
            "photo_id": 11111,
            "approved_visual": True,
            "avoid_terms": [],
            "editorial_notes": "test",
        }
    }

    with (
        patch("apps.core.pexels.requests.request", side_effect=fake_request),
        patch("apps.core.pexels.requests.get", return_value=_fake_cdn_response()),
        patch("apps.core.pexels.load_overrides", return_value=overrides_payload),
    ):
        call_command(
            "fetch_pexels_site_images",
            "--slot",
            "wizard_start_hero",
            "--force",
            stdout=StringIO(),
        )

    # Esattamente UNA chiamata a /photos/{id}, ZERO chiamate a /search
    photos_calls = [u for u in captured["urls"] if "/photos/" in u and "/search" not in u]
    search_calls = [u for u in captured["urls"] if "/search" in u]
    assert len(photos_calls) == 1, f"expected 1 photo_by_id call, got {photos_calls}"
    assert len(search_calls) == 0, f"expected 0 search calls, got {search_calls}"
    assert "11111" in photos_calls[0]


# ---------------------------------------------------------------------------
# A.4 — precedence: CLI --photo-id batte override.photo_id
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="testkey-cli-pin")
def test_cli_photo_id_beats_override_photo_id(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    captured: dict = {"urls": []}

    def fake_request(method, url, **kwargs):
        captured["urls"].append(url)
        return _fake_photo_response(photo_id=22222)

    overrides_payload = {
        "wizard_start_hero": {
            "query": "x",
            "photo_id": 11111,
            "approved_visual": True,
            "avoid_terms": [],
            "editorial_notes": "test",
        }
    }

    with (
        patch("apps.core.pexels.requests.request", side_effect=fake_request),
        patch("apps.core.pexels.requests.get", return_value=_fake_cdn_response()),
        patch("apps.core.pexels.load_overrides", return_value=overrides_payload),
    ):
        call_command(
            "fetch_pexels_site_images",
            "--slot",
            "wizard_start_hero",
            "--photo-id",
            "22222",
            "--force",
            stdout=StringIO(),
        )

    photos_calls = [u for u in captured["urls"] if "/photos/" in u]
    assert len(photos_calls) == 1
    assert "22222" in photos_calls[0]
    assert "11111" not in photos_calls[0]


# ---------------------------------------------------------------------------
# A.5 — --audit mostra FROZEN_MATCH quando match
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_audit_shows_frozen_match_when_manifest_and_override_match(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    (pexels_dir / "home_hero__global__777.jpg").write_bytes(b"x")
    manifest = {
        "home_hero::GLOBAL": {
            "purpose": "home_hero",
            "country_code": None,
            "query": "x",
            "local_path": "pexels/home_hero__global__777.jpg",
            "photo_id": 777,
            "photographer": "Test",
            "photographer_url": "",
            "pexels_url": "",
            "alt": "Test",
            "width": 1920,
            "height": 1080,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "x",
            "extra": {},
        }
    }
    (pexels_dir / "pexels_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    fake_overrides = {"home_hero": {"photo_id": 777, "approved_visual": True}}

    out = StringIO()
    with patch("apps.core.pexels.load_overrides", return_value=fake_overrides):
        call_command("fetch_pexels_site_images", "--audit", stdout=out)
    text = out.getvalue()
    assert "FROZEN_MATCH" in text
    assert "[home_hero::GLOBAL]" in text


# ---------------------------------------------------------------------------
# A.6 — --audit mostra OVERRIDE_DIFFERS quando photo_id divergono
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_audit_shows_override_differs(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    (pexels_dir / "home_hero__global__777.jpg").write_bytes(b"x")
    manifest = {
        "home_hero::GLOBAL": {
            "purpose": "home_hero",
            "country_code": None,
            "query": "x",
            "local_path": "pexels/home_hero__global__777.jpg",
            "photo_id": 777,
            "photographer": "Test",
            "photographer_url": "",
            "pexels_url": "",
            "alt": "Test",
            "width": 1920,
            "height": 1080,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "x",
            "extra": {},
        }
    }
    (pexels_dir / "pexels_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # Override pinned a un photo_id DIVERSO da quello del manifest.
    fake_overrides = {"home_hero": {"photo_id": 999, "approved_visual": True}}

    out = StringIO()
    with patch("apps.core.pexels.load_overrides", return_value=fake_overrides):
        call_command("fetch_pexels_site_images", "--audit", stdout=out)
    text = out.getvalue()
    assert "OVERRIDE_DIFFERS" in text


# ---------------------------------------------------------------------------
# A.7 — --audit mostra UNPINNED se override.photo_id è null
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_audit_shows_unpinned_when_no_photo_id(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    (pexels_dir / "home_hero__global__777.jpg").write_bytes(b"x")
    manifest = {
        "home_hero::GLOBAL": {
            "purpose": "home_hero",
            "country_code": None,
            "query": "x",
            "local_path": "pexels/home_hero__global__777.jpg",
            "photo_id": 777,
            "photographer": "Test",
            "photographer_url": "",
            "pexels_url": "",
            "alt": "Test",
            "width": 1920,
            "height": 1080,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "x",
            "extra": {},
        }
    }
    (pexels_dir / "pexels_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    fake_overrides = {"home_hero": {"photo_id": None, "query": "x"}}

    out = StringIO()
    with patch("apps.core.pexels.load_overrides", return_value=fake_overrides):
        call_command("fetch_pexels_site_images", "--audit", stdout=out)
    text = out.getvalue()
    assert "UNPINNED" in text


# ---------------------------------------------------------------------------
# A.8 — --audit non leak API key (anche con valore stringente settato)
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="FREEZE-AUDIT-LEAK-CHECK-987654321")
def test_audit_does_not_leak_api_key_post_freeze(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    out = StringIO()
    call_command("fetch_pexels_site_images", "--audit", stdout=out)
    assert "FREEZE-AUDIT-LEAK-CHECK-987654321" not in out.getvalue()


# ---------------------------------------------------------------------------
# A.9 — pagine pubbliche: niente "Photo by" / "on Pexels" post-freeze
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    ["/", "/countries/", "/countries/morocco/", "/wizard/", "/methodology/", "/contact/"],
)
def test_freeze_no_visible_attribution(path):
    body = Client().get(path).content.decode("utf-8")
    assert "Photo by" not in body
    assert "on Pexels" not in body


# ---------------------------------------------------------------------------
# A.10 — Italia smoke contract invariato
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_freeze(db):
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
def test_freeze_italy_smoke_run_simulation(italy_smoke_freeze):
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
