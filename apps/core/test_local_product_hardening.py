"""
Tests F-local-product-hardening-pass1.

Coprono:
- /healthz/ (200 + JSON);
- rate-limit pubblico sui POST (contact + wizard Italia);
- override_settings disabilita il rate-limit;
- cookie consent banner presente sulla home + link privacy;
- smoke Italia invariato: run_simulation 35/10/0 -> 26268/27353/28439.

Note:
- I test che esercitano il rate-limit usano `cache.clear()` per
  azzerare il contatore tra un test e l'altro (LocMemCache è
  per-process, e pytest-django non resetta la cache da solo).
- Il limite di test è abbassato via `override_settings` per
  simulare il superamento senza fare 21 POST in un test.
"""

from __future__ import annotations

import json
from decimal import Decimal

import pytest
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse

# ---------------------------------------------------------------------------
# Fixtures: minimo stack IT per smoke run_simulation 35/10/0
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_rate_limit_cache():
    """Azzera la cache prima e dopo ogni test del modulo."""
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def italy_smoke_stack(db):
    """
    Costruisce la pipeline minima IT che produce 26268/27353/28439
    per (victim_age=35, permanent_disability_percentage=10,
    fault_percentage=0).

    NON è un'estrazione completa dei 9 191 / 27 573 row di produzione:
    è uno stub deterministico che pinna il contratto smoke. Se la
    realtà cambia, questo test va aggiornato esplicitamente — è il
    canarino.
    """
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
    # Riga base per (age=35, inv=10): il valore non è usato nel calcolo
    # range — serve solo a far passare il match riga.
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
    # Le 3 row che pinnano il contratto smoke 26268/27353/28439.
    CompensationTableRow.objects.create(
        dataset=moral_ds,
        row_type="tun_biological_moral_min_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("26268"),
    )
    CompensationTableRow.objects.create(
        dataset=moral_ds,
        row_type="tun_biological_moral_mid_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("27353"),
    )
    CompensationTableRow.objects.create(
        dataset=moral_ds,
        row_type="tun_biological_moral_max_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("28439"),
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
    return {"country": italy, "jurisdiction": juris}


# ---------------------------------------------------------------------------
# Task A — /healthz/
# ---------------------------------------------------------------------------


def test_healthz_returns_200_and_status_ok(client: Client):
    """GET /healthz/ ritorna 200 con JSON {"status": "ok"} ed è
    indipendente dalla lingua (path NON i18n-prefixed)."""
    resp = client.get("/healthz/")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("application/json")
    payload = json.loads(resp.content)
    assert payload == {"status": "ok"}


def test_healthz_does_not_require_db(client: Client):
    """Il healthcheck non deve crashare anche senza db marker pytest."""
    # Il test gira senza @pytest.mark.django_db: se la view interroga il DB,
    # il test fallirebbe con DatabaseError.
    resp = client.get("/healthz/")
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Task B — rate-limit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_get_endpoints_are_not_rate_limited(client: Client):
    """Il rate-limit colpisce solo POST. GET deve restare libero."""
    # Anche con max_attempts=1, 5 GET di fila NON devono restituire 429.
    with override_settings(PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS=1):
        for _ in range(5):
            resp = client.get(reverse("crm:contact"))
            assert resp.status_code in (200, 302)


@pytest.mark.django_db
def test_contact_post_under_limit_creates_lead(client: Client):
    """Un singolo POST valido deve creare un Lead (sotto limite)."""
    from apps.crm.models import Lead

    payload = {
        "first_name": "Maria",
        "last_name": "Rossi",
        "email": "maria.rossi@example.test",
        "phone_number": "",
        "preferred_language": "it",
        "country": "",
        "case_type": "",
        "message": "Ho avuto un incidente stradale a Milano e vorrei capire i passi.",
        "privacy_accepted": "on",
        "simulation_public_id": "",
        "website": "",
    }
    resp = client.post(reverse("crm:contact"), data=payload)
    # Redirect alla thank-you = lead creato.
    assert resp.status_code == 302
    assert Lead.objects.count() == 1


@pytest.mark.django_db
def test_contact_post_over_limit_returns_429_and_no_lead(client: Client):
    """Sopra il limite: 429 + nessun Lead creato."""
    from apps.crm.models import Lead

    payload = {
        "first_name": "Maria",
        "last_name": "Rossi",
        "email": "maria.rossi@example.test",
        "phone_number": "",
        "preferred_language": "it",
        "country": "",
        "case_type": "",
        "message": "Ho avuto un incidente stradale a Milano e vorrei capire i passi.",
        "privacy_accepted": "on",
        "simulation_public_id": "",
        "website": "",
    }
    with override_settings(PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS=2):
        # 2 POST validi: passano e creano lead.
        client.post(reverse("crm:contact"), data=payload)
        client.post(reverse("crm:contact"), data=payload)
        assert Lead.objects.count() == 2
        # Terzo POST: 429, niente nuovo lead.
        resp = client.post(reverse("crm:contact"), data=payload)
        assert resp.status_code == 429
        assert Lead.objects.count() == 2


@pytest.mark.django_db
def test_wizard_italy_post_over_limit_returns_429_and_no_simulation(
    client: Client, italy_smoke_stack
):
    """Sopra il limite il wizard IT non crea Simulation."""
    from apps.cases.models import Simulation

    payload = {
        "victim_age": 35,
        "permanent_disability_percentage": 10,
        "fault_percentage": 0,
        "consent_simulation_processing": "on",
        "website": "",
    }
    with override_settings(PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS=1):
        # Primo POST: passa (può creare o no Simulation a seconda della
        # validità del form, ma non è 429).
        client.post(reverse("cases:wizard_italy_road_accident"), data=payload)
        baseline = Simulation.objects.count()
        # Secondo POST: 429.
        resp = client.post(reverse("cases:wizard_italy_road_accident"), data=payload)
        assert resp.status_code == 429
        # Nessun nuovo Simulation oltre la baseline.
        assert Simulation.objects.count() == baseline


@pytest.mark.django_db
def test_rate_limit_disable_via_override_settings(client: Client):
    """Con PUBLIC_POST_RATE_LIMIT_ENABLED=False, nessun limite si applica."""
    from apps.crm.models import Lead

    payload = {
        "first_name": "Maria",
        "last_name": "Rossi",
        "email": "maria.rossi@example.test",
        "phone_number": "",
        "preferred_language": "it",
        "country": "",
        "case_type": "",
        "message": "Ho avuto un incidente stradale a Milano e vorrei capire i passi.",
        "privacy_accepted": "on",
        "simulation_public_id": "",
        "website": "",
    }
    with override_settings(
        PUBLIC_POST_RATE_LIMIT_ENABLED=False,
        PUBLIC_POST_RATE_LIMIT_MAX_ATTEMPTS=1,
    ):
        # Anche con max=1, 3 POST consecutivi devono passare.
        for _ in range(3):
            resp = client.post(reverse("crm:contact"), data=payload)
            assert resp.status_code == 302
        assert Lead.objects.count() == 3


# ---------------------------------------------------------------------------
# Task C — cookie consent banner
# ---------------------------------------------------------------------------


def test_cookie_banner_is_present_on_home(client: Client):
    """La home deve includere il banner cookie."""
    resp = client.get(reverse("core:home"))
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert 'id="cookie-consent-banner"' in body
    assert 'role="region"' in body
    # aria-label è gettext-tradotta: accettiamo source EN o IT translation.
    assert 'aria-label="Cookie notice"' in body or 'aria-label="Informativa cookie"' in body
    # localStorage usato per persistenza.
    assert "localStorage" in body


def test_cookie_banner_links_to_privacy_page(client: Client):
    """Il banner deve linkare alla privacy notice."""
    resp = client.get(reverse("core:home"))
    body = resp.content.decode("utf-8")
    privacy_url = reverse("core:privacy")
    # Il link compare DENTRO il banner. Verifichiamo che il banner contenga
    # un href all'URL privacy.
    banner_start = body.index('id="cookie-consent-banner"')
    banner_end = body.index("</script>", banner_start)
    banner_block = body[banner_start:banner_end]
    assert privacy_url in banner_block


# ---------------------------------------------------------------------------
# Task E.9 — Italia smoke contract 35/10/0 -> 26268/27353/28439
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_smoke_run_simulation_35_10_0(italy_smoke_stack):
    """Smoke contract Italia: run_simulation deterministico."""
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
