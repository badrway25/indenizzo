"""
Tests F-product-pexels-curation-pass1.

Coprono:
- override JSON non contiene la API key;
- comando legge query da override (search_photos chiamata con query
  override, non con il default della slot);
- --slot scarica solo lo slot specificato;
- --photo-id senza API key dà CommandError leggibile;
- --audit non chiama Pexels e non logga la API key;
- pagine pubbliche non mostrano "Photo by" / "on Pexels";
- API key non appare in HTML;
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
from django.core.management.base import CommandError
from django.test import Client, override_settings

# ---------------------------------------------------------------------------
# F.1 — file override non contiene "API_KEY" / chiavi sospette
# ---------------------------------------------------------------------------


def test_override_file_has_no_api_key_or_secret():
    """Hard guard: il JSON di override NON deve contenere indizi di secret."""
    p = Path("config") / "pexels_image_overrides.json"
    assert p.exists(), "config/pexels_image_overrides.json missing"
    raw = p.read_text(encoding="utf-8")
    forbidden = [
        "PEXELS_API_KEY",
        "Authorization",
        "Bearer ",
        "secret",
        "api_key",
    ]
    for token in forbidden:
        assert token.lower() not in raw.lower(), f"override file leaked '{token}'"


# ---------------------------------------------------------------------------
# F.2 — override.query viene usata da fetch_one_slot
# ---------------------------------------------------------------------------


def _fake_search_response(photo_id=999, alt="Studio law office desk", url="https://x"):
    fake = MagicMock()
    fake.status_code = 200
    fake.json.return_value = {
        "photos": [
            {
                "id": photo_id,
                "width": 4000,
                "height": 2667,
                "photographer": "Test Photog",
                "photographer_url": "https://www.pexels.com/@x",
                "url": url,
                "alt": alt,
                "src": {
                    "original": "https://images.pexels.com/orig.jpg",
                    "large2x": "https://images.pexels.com/large2x.jpg",
                    "large": "https://images.pexels.com/large.jpg",
                    "landscape": "https://images.pexels.com/landscape.jpg",
                },
            }
        ]
    }
    return fake


def _fake_cdn_response(content=b"x" * 64):
    fake = MagicMock()
    fake.status_code = 200
    fake.iter_content = lambda chunk_size=8192: [content]
    return fake


@override_settings(PEXELS_API_KEY="testkey-curation")
def test_command_reads_override_query(tmp_path, settings):
    """Il command deve usare la query dell'override JSON, non quella default."""
    settings.MEDIA_ROOT = str(tmp_path)
    captured: dict = {}

    def fake_request(method, url, **kwargs):
        captured["params"] = kwargs.get("params") or {}
        captured["url"] = url
        return _fake_search_response()

    overrides_payload = {
        "slots": {
            "wizard_start_hero": {
                "query": "OVERRIDE-QUERY-FOR-WIZARD-START",
                "photo_id": None,
                "avoid_terms": [],
                "editorial_notes": "test",
            }
        }
    }

    with (
        patch("apps.core.pexels.requests.request", side_effect=fake_request),
        patch("apps.core.pexels.requests.get", return_value=_fake_cdn_response()),
        patch("apps.core.pexels.load_overrides", return_value=overrides_payload["slots"]),
    ):
        call_command(
            "fetch_pexels_site_images",
            "--slot",
            "wizard_start_hero",
            stdout=StringIO(),
        )

    assert captured["params"].get("query") == "OVERRIDE-QUERY-FOR-WIZARD-START"


# ---------------------------------------------------------------------------
# F.3 — --slot accetta una sola slot e ignora le altre
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="testkey-slot")
def test_command_slot_arg_only_fetches_one_slot(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    calls: list[str] = []

    def fake_request(method, url, **kwargs):
        calls.append((kwargs.get("params") or {}).get("query") or url)
        return _fake_search_response()

    with (
        patch("apps.core.pexels.requests.request", side_effect=fake_request),
        patch("apps.core.pexels.requests.get", return_value=_fake_cdn_response()),
    ):
        call_command(
            "fetch_pexels_site_images",
            "--slot",
            "country_landing_IT",
            stdout=StringIO(),
        )
    # Esattamente una search request (no fan-out su altre slot).
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# F.4 — --photo-id senza --slot dà CommandError
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="testkey-pin")
def test_command_photo_id_without_slot_raises():
    with pytest.raises(CommandError):
        call_command("fetch_pexels_site_images", "--photo-id", "12345", stdout=StringIO())


# ---------------------------------------------------------------------------
# F.5 — --audit funziona SENZA API key e SENZA rete
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="")
def test_command_audit_runs_without_api_key_and_without_network(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    out = StringIO()
    with (
        patch("apps.core.pexels.requests.request") as mock_req,
        patch("apps.core.pexels.requests.get") as mock_get,
    ):
        call_command("fetch_pexels_site_images", "--audit", stdout=out)
    # Niente chiamate Pexels.
    assert mock_req.call_count == 0
    assert mock_get.call_count == 0
    # Output contiene la parola AUDIT (sicuro che il path è eseguito).
    assert "AUDIT" in out.getvalue()


# ---------------------------------------------------------------------------
# F.6 — Audit non leak la API key nello stdout anche se settata
# ---------------------------------------------------------------------------


@override_settings(PEXELS_API_KEY="LEAK-TEST-KEY-AUDIT-9999")
def test_command_audit_does_not_leak_api_key(tmp_path, settings):
    settings.MEDIA_ROOT = str(tmp_path)
    out = StringIO()
    call_command("fetch_pexels_site_images", "--audit", stdout=out)
    assert "LEAK-TEST-KEY-AUDIT-9999" not in out.getvalue()


# ---------------------------------------------------------------------------
# F.7 — pagine pubbliche: niente "Photo by" / "on Pexels"
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    ["/", "/countries/", "/countries/morocco/", "/countries/tunisia/", "/wizard/", "/contact/"],
)
def test_curation_no_visible_attribution(path):
    body = Client().get(path).content.decode("utf-8")
    assert "Photo by" not in body
    assert "on Pexels" not in body


# ---------------------------------------------------------------------------
# F.8 — API key non in HTML
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(PEXELS_API_KEY="CURATION-SECRET-KEY-DO-NOT-LEAK-2026")
@pytest.mark.parametrize(
    "path",
    ["/", "/countries/", "/countries/morocco/", "/countries/tunisia/", "/wizard/", "/contact/"],
)
def test_curation_api_key_never_in_html(path):
    body = Client().get(path).content.decode("utf-8")
    assert "CURATION-SECRET-KEY-DO-NOT-LEAK-2026" not in body


# ---------------------------------------------------------------------------
# F.9 — manifest pulito: niente "denmark" sulla landing Morocco se override
# applicato
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_morocco_landing_does_not_serve_denmark_courthouse(tmp_path, settings):
    """
    Force-write un manifest 'corretto' (Rabat) e verifica che il template
    serva esattamente quel file. Test difensivo: anche se in futuro
    qualcuno cambia logica, l'override Rabat deve essere onorato.
    """
    settings.MEDIA_ROOT = str(tmp_path)
    pexels_dir = Path(tmp_path) / "pexels"
    pexels_dir.mkdir(parents=True, exist_ok=True)
    img = pexels_dir / "country_landing__ma__9999.jpg"
    img.write_bytes(b"x")
    manifest = {
        "country_landing::MA": {
            "purpose": "country_landing",
            "country_code": "MA",
            "query": "Rabat architecture Morocco official building",
            "local_path": "pexels/country_landing__ma__9999.jpg",
            "photo_id": 9999,
            "photographer": "Internal",
            "photographer_url": "https://www.pexels.com/@x",
            "pexels_url": "https://www.pexels.com/photo/rabat/",
            "alt": "Mausoleum Mohammed V Rabat",
            "width": 1920,
            "height": 1080,
            "downloaded_at": "2026-05-01T00:00:00+00:00",
            "sha256": "x",
            "extra": {"size_bytes": 1},
        }
    }
    (pexels_dir / "pexels_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    body = Client().get("/countries/morocco/").content.decode("utf-8")
    assert "/media/pexels/country_landing__ma__9999.jpg" in body
    # Niente "denmark" / "odense" sulla landing Morocco (sarebbe il bug
    # che il pass curation ha risolto).
    assert "denmark" not in body.lower()
    assert "odense" not in body.lower()


# ---------------------------------------------------------------------------
# F.10 — slot_override + override_lookup_key contract
# ---------------------------------------------------------------------------


def test_override_lookup_key_for_global_slots():
    from apps.core.pexels import override_lookup_key

    assert override_lookup_key("home_hero", None) == "home_hero"
    assert override_lookup_key("methodology_hero", None) == "methodology_hero"
    assert override_lookup_key("country_landing", "IT") == "country_landing_IT"
    assert override_lookup_key("country_landing", "ma") == "country_landing_MA"


def test_load_overrides_returns_dict_or_empty(tmp_path, settings):
    """Se il file non esiste, ritorna {}."""
    from apps.core import pexels

    # Forziamo un BASE_DIR senza override file.
    with patch.object(pexels, "_OVERRIDES_PATH", Path(tmp_path) / "no_such_overrides.json"):
        assert pexels.load_overrides() == {}


# ---------------------------------------------------------------------------
# F.11 — Italia smoke contract invariato
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_smoke_curation(db):
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
def test_curation_italy_smoke_run_simulation(italy_smoke_curation):
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
