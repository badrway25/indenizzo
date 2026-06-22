"""
Tests F-product-pexels-image-integration.

Coprono:
- search_photos invia Authorization SENZA "Bearer";
- API key mancante → PexelsAPIKeyMissing;
- command --dry-run NON scarica file e NON chiama il CDN;
- command normale salva manifest + attribution;
- country landing renderizza anche senza manifest;
- country landing usa immagine locale se manifest presente;
- og:image usa Pexels locale se manifest presente;
- API key NON appare nel rendered HTML;
- PEXELS_API_KEY non richiesto per renderizzare pagine;
- Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

import json
import re
from decimal import Decimal
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings


def _fake_search_response(photo_id: int = 1234567) -> MagicMock:
    """Risposta `requests.get` simulata che rispetta il contratto Pexels."""
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {
        "photos": [
            {
                "id": photo_id,
                "width": 4000,
                "height": 2667,
                "photographer": "Jane Doe",
                "photographer_url": "https://www.pexels.com/@janedoe",
                "url": f"https://www.pexels.com/photo/{photo_id}/",
                "alt": "Marble courthouse facade",
                "src": {
                    "original": "https://images.pexels.com/photos/X/orig.jpg",
                    "large2x": "https://images.pexels.com/photos/X/large2x.jpg",
                    "large": "https://images.pexels.com/photos/X/large.jpg",
                    "landscape": "https://images.pexels.com/photos/X/landscape.jpg",
                },
            }
        ]
    }
    return fake


def _fake_cdn_response(content: bytes = b"\x89PNGfake\x00bytes" * 16) -> MagicMock:
    """Risposta CDN simulata (stream chunked)."""
    fake = MagicMock()
    fake.status_code = 200
    fake.iter_content = lambda chunk_size=8192: [content]
    return fake


# ---------------------------------------------------------------------------
# Task I.1 — search_photos manda Authorization corretto (no Bearer)
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="secret-test-key-NEVER-LOG")
def test_search_photos_sends_authorization_header_without_bearer():
    from apps.core import pexels

    with patch("apps.core.pexels.requests.request") as mock_req:
        mock_req.return_value = _fake_search_response()
        result = pexels.search_photos("Rome courthouse", per_page=3)

    mock_req.assert_called_once()
    _, kwargs = mock_req.call_args
    headers = kwargs["headers"]
    auth = headers["Authorization"]
    # Il valore deve essere ESATTAMENTE la key, niente "Bearer ".
    assert auth == "secret-test-key-NEVER-LOG"
    assert not auth.lower().startswith("bearer")
    assert len(result) == 1
    assert result[0].photographer == "Jane Doe"


# ---------------------------------------------------------------------------
# Task I.2 — variant: il prefisso "Bearer" non deve mai comparire
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="another-key")
def test_auth_headers_never_include_bearer_prefix():
    from apps.core import pexels

    headers = pexels._auth_headers()
    assert "Authorization" in headers
    assert headers["Authorization"] == "another-key"
    assert "Bearer" not in headers["Authorization"]


# ---------------------------------------------------------------------------
# Task I.3 — API key mancante solleva errore controllato
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_search_photos_without_key_raises_controlled_error():
    from apps.core import pexels

    with pytest.raises(pexels.PexelsAPIKeyMissing):
        pexels.search_photos("anything")


# ---------------------------------------------------------------------------
# Task I.4 — command --dry-run NON scarica file
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="dry-run-key")
def test_command_dry_run_does_not_call_network(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)

    out = StringIO()
    with (
        patch("apps.core.pexels.requests.request") as mock_req,
        patch("apps.core.pexels.requests.get") as mock_get,
    ):
        call_command(
            "fetch_pexels_site_images",
            "--dry-run",
            "--all",
            stdout=out,
        )

    # Nessuna chiamata a Pexels (search) né al CDN (download).
    assert mock_req.call_count == 0
    assert mock_get.call_count == 0
    # Manifest non scritto.
    assert not (Path(tmp_path) / "pexels" / "pexels_manifest.json").exists()
    out_text = out.getvalue()
    assert "DRY RUN" in out_text


# ---------------------------------------------------------------------------
# Task I.5 — command salva manifest con attribution
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="real-key")
def test_command_writes_manifest_with_attribution(tmp_path, settings):
    """
    Pre-freeze test: simula il path search → download. Force overrides
    a `{}` perché dopo il freeze pass tutti gli slot hanno photo_id
    pinned, che farebbe partire `photo_by_id()` con un payload mock
    incompatibile con la search.
    """
    settings.MEDIA_ROOT = str(tmp_path)

    with (
        patch("apps.core.pexels.requests.request") as mock_req,
        patch("apps.core.pexels.requests.get") as mock_get,
        patch("apps.core.pexels.load_overrides", return_value={}),
    ):
        mock_req.return_value = _fake_search_response(photo_id=42)
        mock_get.return_value = _fake_cdn_response()
        call_command(
            "fetch_pexels_site_images",
            "--country",
            "IT",
            stdout=StringIO(),
        )

    manifest_path = Path(tmp_path) / "pexels" / "pexels_manifest.json"
    assert manifest_path.exists()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    key = "country_landing::IT"
    assert key in manifest
    entry = manifest[key]
    assert entry["photographer"] == "Jane Doe"
    assert entry["pexels_url"].startswith("https://www.pexels.com/photo/42/")
    assert entry["sha256"]  # non vuoto
    # File scaricato esiste.
    assert (Path(tmp_path) / entry["local_path"]).exists()


# ---------------------------------------------------------------------------
# Task I.6 — country landing renderizza anche senza manifest
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_country_landing_renders_without_manifest(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    resp = Client().get("/countries/italy/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    # Non deve apparire il blocco <figure> Pexels.
    # Useremo la classe "rounded-3xl overflow-hidden shadow-card" che
    # è presente solo se pexels_image è truthy (la usiamo nel
    # banner dedicato Pexels). Il template ha la classe shadow-card
    # anche su altri card, quindi controlliamo l'assenza di img tag
    # con src=/media/pexels/.
    assert "/media/pexels/" not in body


# ---------------------------------------------------------------------------
# Task I.7 — country landing usa immagine locale se manifest presente
#
# Pass "pexels-polish-no-caption-live-server-and-i18n-status":
# l'attribution NON deve più essere visibile nel HTML pubblico,
# ma deve restare nel manifest.
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_country_landing_uses_local_pexels_image_when_manifest_present(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)

    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    image_path = pexels_dir / "country_landing__it__999.jpg"
    image_path.write_bytes(b"fake-jpg-bytes")
    manifest = {
        "country_landing::IT": {
            "purpose": "country_landing",
            "country_code": "IT",
            "query": "Rome courthouse architecture",
            "local_path": "pexels/country_landing__it__999.jpg",
            "photo_id": 999,
            "photographer": "Live Photographer",
            "photographer_url": "https://www.pexels.com/@livephotographer",
            "pexels_url": "https://www.pexels.com/photo/999/",
            "alt": "Rome courthouse facade",
            "width": 4000,
            "height": 2667,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "deadbeef",
            "extra": {"size_bytes": 14},
        }
    }
    (pexels_dir / "pexels_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    body = Client().get("/countries/italy/").content.decode("utf-8")
    # L'<img> deve renderizzarsi e puntare al file locale.
    assert "/media/pexels/country_landing__it__999.jpg" in body
    assert 'alt="Rome courthouse facade"' in body
    # NIENTE attribution visibile.
    assert "Photo by" not in body
    assert "on Pexels" not in body
    assert "Live Photographer" not in body
    assert "https://www.pexels.com/@livephotographer" not in body
    assert "https://www.pexels.com/photo/999/" not in body


# ---------------------------------------------------------------------------
# Task B.5 — il manifest mantiene photographer / photographer_url / pexels_url
# (anche se non vengono renderizzati in HTML).
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_manifest_keeps_attribution_metadata_even_if_not_rendered(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)

    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    (pexels_dir / "country_landing__it__555.jpg").write_bytes(b"x")
    manifest = {
        "country_landing::IT": {
            "purpose": "country_landing",
            "country_code": "IT",
            "query": "Rome courthouse architecture",
            "local_path": "pexels/country_landing__it__555.jpg",
            "photo_id": 555,
            "photographer": "Internal Only Photographer",
            "photographer_url": "https://www.pexels.com/@internal",
            "pexels_url": "https://www.pexels.com/photo/555/",
            "alt": "Rome courthouse facade",
            "width": 4000,
            "height": 2667,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "deadbeef",
            "extra": {"size_bytes": 1},
        }
    }
    manifest_path = pexels_dir / "pexels_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    # Render the page just to ensure no side effect mutates the manifest.
    Client().get("/countries/italy/")

    saved = json.loads(manifest_path.read_text(encoding="utf-8"))
    entry = saved["country_landing::IT"]
    # I tre campi attribution restano nel manifest, anche se non vanno in HTML.
    assert entry["photographer"] == "Internal Only Photographer"
    assert entry["photographer_url"] == "https://www.pexels.com/@internal"
    assert entry["pexels_url"] == "https://www.pexels.com/photo/555/"

    # Helper interno deve continuare a produrre l'attribution string —
    # serve per future feature (audit log, credits page, ecc.).
    from apps.core.pexels import attribution_for_entry

    assert attribution_for_entry(entry) == "Photo by Internal Only Photographer on Pexels"


# ---------------------------------------------------------------------------
# Task I.8 — og:image usa Pexels locale se manifest presente
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_og_image_uses_local_pexels_when_manifest_present(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)

    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    image_path = pexels_dir / "country_landing__fr__777.jpg"
    image_path.write_bytes(b"fr-image")
    manifest = {
        "country_landing::FR": {
            "purpose": "country_landing",
            "country_code": "FR",
            "query": "Paris courthouse architecture",
            "local_path": "pexels/country_landing__fr__777.jpg",
            "photo_id": 777,
            "photographer": "FR Photographer",
            "photographer_url": "https://www.pexels.com/@fr",
            "pexels_url": "https://www.pexels.com/photo/777/",
            "alt": "Paris courthouse",
            "width": 1920,
            "height": 1080,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "cafebabe",
            "extra": {"size_bytes": 8},
        }
    }
    (pexels_dir / "pexels_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    body = Client().get("/countries/france/").content.decode("utf-8")
    og_image_match = re.search(
        r'<meta\s+property="og:image"\s+content="([^"]+)"', body, flags=re.IGNORECASE
    )
    assert og_image_match is not None
    og_image = og_image_match.group(1)
    assert og_image.endswith("/media/pexels/country_landing__fr__777.jpg")
    # twitter:image deve coincidere
    tw_image_match = re.search(
        r'<meta\s+name="twitter:image"\s+content="([^"]+)"', body, flags=re.IGNORECASE
    )
    assert tw_image_match is not None
    assert tw_image_match.group(1) == og_image


# ---------------------------------------------------------------------------
# Task I.9 — API key NON appare nel rendered HTML
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="ULTRA-SECRET-KEY-DO-NOT-LEAK-1234567890abcdef")
def test_api_key_never_appears_in_rendered_html():
    """
    Anche se la key è settata, NESSUNA pagina pubblica deve contenerla.
    Non viene mai passata in context, mai in template, mai in client JS.
    """
    paths = [
        "/",
        "/countries/",
        "/countries/italy/",
        "/countries/france/",
        "/countries/morocco/",
        "/methodology/",
        "/disclaimer/",
        "/privacy/",
    ]
    secret = "ULTRA-SECRET-KEY-DO-NOT-LEAK-1234567890abcdef"
    for path in paths:
        resp = Client().get(path)
        assert resp.status_code in (200, 301, 302), f"{path} → {resp.status_code}"
        assert secret not in resp.content.decode("utf-8"), f"API key leaked on {path}!"


# ---------------------------------------------------------------------------
# Task I.10 — PEXELS_API_KEY non richiesto per render pagine
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="", PEXELS_ENABLED=False)
def test_pages_render_without_pexels_api_key():
    paths = [
        "/countries/italy/",
        "/countries/france/",
        "/countries/morocco/",
        "/ar/countries/morocco/",
    ]
    for path in paths:
        resp = Client().get(path)
        assert resp.status_code == 200, f"{path} → {resp.status_code}"


# ---------------------------------------------------------------------------
# Task I.11 — command senza key → CommandError leggibile (non distruttivo)
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_command_without_key_raises_command_error():
    out = StringIO()
    with pytest.raises(CommandError):
        call_command("fetch_pexels_site_images", "--all", stdout=out)


# ---------------------------------------------------------------------------
# Task I.12 — Italia smoke contract invariato
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
