"""
Tests F-local-product-hardening-pass3-sentry.

Coprono:
- `scrub_sentry_event` redige campi sensibili a qualunque profondità;
- `scrub_sentry_event` non muta campi innocui;
- `init_sentry_from_settings` ritorna False con DSN vuoto e NON importa
  sentry_sdk (verifica via `sentry_init` mock);
- settings di default: SENTRY_SEND_DEFAULT_PII=False, DSN="";
- smoke Italia 35/10/0 invariato.

Tutti i test sono pure-Python: non richiedono `sentry-sdk` installato.
"""

from __future__ import annotations

import copy
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from django.conf import settings
from django.test import override_settings

# ---------------------------------------------------------------------------
# Task F.1 + F.2 — scrubber redacts sensitive, preserves innocuous
# ---------------------------------------------------------------------------


def test_scrub_redacts_top_level_sensitive_keys():
    from apps.core.observability import REDACTED_VALUE, scrub_sentry_event

    event = {
        "email": "maria.rossi@example.test",
        "phone": "+39 333 0000000",
        "first_name": "Maria",
        "last_name": "Rossi",
        "message": "Ho avuto un incidente — dati sensibili.",
        "session_key": "abcdef0123456789abcdef0123456789",
        "user_agent": "Mozilla/5.0 ...",
        "ip_address": "203.0.113.42",
        "csrfmiddlewaretoken": "supersecret",
    }
    result = scrub_sentry_event(event)
    assert result["email"] == REDACTED_VALUE
    assert result["phone"] == REDACTED_VALUE
    assert result["first_name"] == REDACTED_VALUE
    assert result["last_name"] == REDACTED_VALUE
    assert result["message"] == REDACTED_VALUE
    assert result["session_key"] == REDACTED_VALUE
    assert result["user_agent"] == REDACTED_VALUE
    assert result["ip_address"] == REDACTED_VALUE
    assert result["csrfmiddlewaretoken"] == REDACTED_VALUE


def test_scrub_redacts_nested_dict_and_list():
    """Sentry payload contiene request.data, breadcrumbs[].data: ricorsivo."""
    from apps.core.observability import REDACTED_VALUE, scrub_sentry_event

    event = {
        "request": {
            "url": "/contact/",
            "method": "POST",
            "data": {
                "email": "leak@example.test",
                "country": "IT",
            },
        },
        "breadcrumbs": [
            {"category": "form", "data": {"email": "leak2@example.test"}},
        ],
    }
    result = scrub_sentry_event(event)
    assert result["request"]["data"]["email"] == REDACTED_VALUE
    assert result["request"]["data"]["country"] == "IT"  # innocuo
    assert result["breadcrumbs"][0]["data"]["email"] == REDACTED_VALUE


def test_scrub_does_not_mutate_innocuous_fields():
    from apps.core.observability import scrub_sentry_event

    event = {
        "transaction": "/wizard/it/road-accident/",
        "level": "error",
        "tags": {
            "environment": "local",
            "release": "v0.1",
            "country": "IT",
            "case_type": "road_accident_bodily_injury",
        },
        "extra": {
            "simulation_public_id": "abc-123",
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
        "exception": {
            "values": [
                {"type": "ValueError", "value": "bad input"},
            ]
        },
    }
    snapshot = copy.deepcopy(event)
    result = scrub_sentry_event(event)
    assert result == snapshot  # nessuna modifica


def test_scrub_is_case_insensitive():
    from apps.core.observability import REDACTED_VALUE, scrub_sentry_event

    event = {"EMAIL": "x@y.test", "Phone_Number": "0", "MESSAGE": "leak"}
    result = scrub_sentry_event(event)
    assert result["EMAIL"] == REDACTED_VALUE
    assert result["Phone_Number"] == REDACTED_VALUE
    assert result["MESSAGE"] == REDACTED_VALUE


def test_scrub_handles_non_dict_input_gracefully():
    """Sentry può passare valori non-dict in casi limite. Mai sollevare."""
    from apps.core.observability import scrub_sentry_event

    assert scrub_sentry_event("not a dict") == "not a dict"  # type: ignore[arg-type]
    assert scrub_sentry_event(None) is None  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Task F.3 — init guard with empty DSN
# ---------------------------------------------------------------------------


@override_settings(SENTRY_DSN="")
def test_init_returns_false_when_dsn_empty_and_does_not_call_init():
    from apps.core.observability import init_sentry_from_settings

    init_mock = MagicMock()
    result = init_sentry_from_settings(sentry_init=init_mock)
    assert result is False
    init_mock.assert_not_called()


@override_settings(
    SENTRY_DSN="https://public@sentry.example/1",
    SENTRY_ENVIRONMENT="staging",
    SENTRY_TRACES_SAMPLE_RATE=0.0,
    SENTRY_PROFILES_SAMPLE_RATE=0.0,
    SENTRY_SEND_DEFAULT_PII=False,
)
def test_init_returns_true_when_dsn_set_and_calls_init_with_pii_off():
    from apps.core.observability import init_sentry_from_settings, scrub_sentry_event

    init_mock = MagicMock()
    # integrations_factory injection per evitare di richiedere
    # sentry_sdk.integrations.django (non installato in test).
    result = init_sentry_from_settings(
        sentry_init=init_mock,
        integrations_factory=lambda: [],
    )
    assert result is True
    init_mock.assert_called_once()
    kwargs = init_mock.call_args.kwargs
    assert kwargs["dsn"] == "https://public@sentry.example/1"
    assert kwargs["environment"] == "staging"
    assert kwargs["send_default_pii"] is False
    assert kwargs["traces_sample_rate"] == 0.0
    assert kwargs["profiles_sample_rate"] == 0.0
    assert kwargs["before_send"] is scrub_sentry_event
    assert kwargs["integrations"] == []


# ---------------------------------------------------------------------------
# Task F.4 — settings defaults
# ---------------------------------------------------------------------------


def test_settings_defaults_are_safe():
    """SENTRY_DSN vuoto, send_default_pii False, sample rates a 0."""
    assert getattr(settings, "SENTRY_DSN", None) == ""
    assert getattr(settings, "SENTRY_SEND_DEFAULT_PII", None) is False
    assert getattr(settings, "SENTRY_TRACES_SAMPLE_RATE", None) == 0.0
    assert getattr(settings, "SENTRY_PROFILES_SAMPLE_RATE", None) == 0.0
    # Environment dipende da DEBUG: in test DEBUG è False di default
    # (manage.py test setting), ma importa che il valore sia uno dei
    # due previsti.
    assert getattr(settings, "SENTRY_ENVIRONMENT", None) in {"local", "production"}


# ---------------------------------------------------------------------------
# Task F.5 — Italia smoke contract invariato
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
