"""
Tests F-local-product-hardening-pass7-celery-async.

Coprono:
- Celery app importabile;
- task send_lead_notification_task gestisce lead inesistente
  (return False, no email);
- task in EAGER mode invia email reale (locmem);
- contact POST sync path invia email;
- contact POST async path chiama delay (mocked);
- delay() exception → fallback sync, redirect thank-you preservato;
- docker-compose.local.yml contiene servizio celery-worker;
- doc Pass 7 contiene Celery, Redis, fallback,
  LEAD_NOTIFICATION_ASYNC_ENABLED;
- Italia smoke 35/10/0 invariato.

Nessun broker reale richiesto: i test usano `CELERY_TASK_ALWAYS_EAGER=True`
e mock di `.delay()`.
"""

from __future__ import annotations

import pathlib
from decimal import Decimal
from unittest.mock import patch

import pytest
from django.core import mail
from django.core.cache import cache
from django.test import Client, override_settings
from django.urls import reverse

ROOT = pathlib.Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.local.yml"
DOC_PATH = ROOT / "docs" / "architecture" / "LOCAL_PRODUCT_HARDENING_PASS7_CELERY.md"

LOCMEM_BACKEND = "django.core.mail.backends.locmem.EmailBackend"


@pytest.fixture(autouse=True)
def _clear_cache_and_outbox():
    cache.clear()
    mail.outbox = []
    yield
    cache.clear()
    mail.outbox = []


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_country(db):
    from apps.jurisdictions.models import Country

    return Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")


@pytest.fixture
def lead(db, italy_country):
    from apps.crm.models import Lead

    return Lead.objects.create(
        first_name="Maria",
        last_name="Rossi",
        email="maria.rossi@example.test",
        phone_number="+39 333 0000000",
        preferred_language="it",
        country=italy_country,
        case_type="road_accident_bodily_injury",
        message="placeholder message of sufficient length for the model",
    )


CONTACT_PAYLOAD = {
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


# ---------------------------------------------------------------------------
# Task G.1 — Celery app importable
# ---------------------------------------------------------------------------


def test_celery_app_is_importable():
    """Sia config.celery che config.celery_app devono essere importabili."""
    from config.celery import app as direct_app

    assert direct_app.main == "badrane_legaltech"
    # Il re-export da config.__init__ deve puntare alla stessa istanza.
    from config import celery_app

    assert celery_app is direct_app


# ---------------------------------------------------------------------------
# Task G.2 — task con lead inesistente
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
    CELERY_TASK_ALWAYS_EAGER=True,
)
@pytest.mark.django_db
def test_task_returns_false_when_lead_does_not_exist():
    from apps.crm.tasks import send_lead_notification_task

    # PK irragionevolmente alto, sicuro vuoto.
    result = send_lead_notification_task.apply(args=[999_999_999])
    assert result.successful()
    assert result.result is False
    assert len(mail.outbox) == 0


# ---------------------------------------------------------------------------
# Task G.3 — task in EAGER mode con lead reale invia email
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
    CELERY_TASK_ALWAYS_EAGER=True,
)
@pytest.mark.django_db
def test_task_in_eager_mode_sends_email(lead):
    from apps.crm.tasks import send_lead_notification_task

    result = send_lead_notification_task.apply(args=[lead.pk])
    assert result.successful()
    assert result.result is True
    assert len(mail.outbox) == 1
    assert str(lead.public_id) in mail.outbox[0].body


# ---------------------------------------------------------------------------
# Task G.4 — contact POST sync path invia email
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
    LEAD_NOTIFICATION_ASYNC_ENABLED=False,
)
@pytest.mark.django_db
def test_contact_post_sync_path_sends_email():
    from apps.crm.models import Lead

    client = Client()
    resp = client.post(reverse("crm:contact"), data=CONTACT_PAYLOAD)
    assert resp.status_code == 302
    assert Lead.objects.count() == 1
    assert len(mail.outbox) == 1


# ---------------------------------------------------------------------------
# Task G.5 — contact POST async path chiama delay (mocked)
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
    LEAD_NOTIFICATION_ASYNC_ENABLED=True,
)
@pytest.mark.django_db
def test_contact_post_async_path_calls_delay():
    """Async ON: delay() chiamata; il sync NON deve essere triggered."""
    from apps.crm.models import Lead

    with patch("apps.crm.tasks.send_lead_notification_task.delay") as mock_delay:
        client = Client()
        resp = client.post(reverse("crm:contact"), data=CONTACT_PAYLOAD)
        assert resp.status_code == 302
        assert Lead.objects.count() == 1
        # delay() chiamata con il PK del Lead.
        mock_delay.assert_called_once()
        args, _ = mock_delay.call_args
        assert args == (Lead.objects.first().pk,)
        # Sync NON triggered: outbox vuota (delay non esegue il task,
        # solo lo enqueue).
        assert len(mail.outbox) == 0


# ---------------------------------------------------------------------------
# Task G.6 — delay exception → fallback sync, redirect preserved
# ---------------------------------------------------------------------------


@override_settings(
    EMAIL_BACKEND=LOCMEM_BACKEND,
    LEAD_NOTIFICATION_ENABLED=True,
    LEAD_NOTIFICATION_TO_EMAILS=["studio@example.test"],
    LEAD_NOTIFICATION_ASYNC_ENABLED=True,
)
@pytest.mark.django_db
def test_contact_post_async_delay_exception_falls_back_to_sync():
    """delay() solleva (broker down) → fallback sync, Lead resta,
    thank-you raggiunto."""
    from apps.crm.models import Lead

    with patch(
        "apps.crm.tasks.send_lead_notification_task.delay",
        side_effect=RuntimeError("simulated broker outage"),
    ):
        client = Client()
        resp = client.post(reverse("crm:contact"), data=CONTACT_PAYLOAD)
        # Redirect preservato.
        assert resp.status_code == 302
        assert resp.url == reverse("crm:contact_thank_you")
        # Lead committed.
        assert Lead.objects.count() == 1
        # Fallback sync ha inviato 1 email.
        assert len(mail.outbox) == 1


# ---------------------------------------------------------------------------
# Task G.7 — docker-compose.local.yml contiene celery-worker
# ---------------------------------------------------------------------------


def test_compose_local_includes_celery_worker_service():
    assert COMPOSE_PATH.exists(), f"missing: {COMPOSE_PATH}"
    text = COMPOSE_PATH.read_text(encoding="utf-8")
    assert "celery-worker:" in text
    assert "celery -A config worker" in text
    # Stesso Dockerfile del web.
    assert "dockerfile: Dockerfile" in text


# ---------------------------------------------------------------------------
# Task G.8 — doc Pass 7 contiene sentinelle minime
# ---------------------------------------------------------------------------


def test_pass7_doc_contains_required_sentinels():
    assert DOC_PATH.exists(), f"missing: {DOC_PATH}"
    text = DOC_PATH.read_text(encoding="utf-8").lower()
    for sentinel in [
        "celery",
        "redis",
        "fallback",
        "lead_notification_async_enabled",
        "broker",
        "26268",
    ]:
        assert sentinel in text, f"sentinel missing: {sentinel!r}"


# ---------------------------------------------------------------------------
# Task G.9 — Italia smoke contract invariato
# ---------------------------------------------------------------------------


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
