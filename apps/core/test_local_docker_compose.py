"""
Tests F-local-product-hardening-pass6-docker-compose.

Coprono (test STATICI, no Docker daemon richiesto):
1. `docker-compose.local.yml` esiste e dichiara servizi web/db/redis;
2. `.env.local.docker.example` contiene DATABASE_URL e REDIS_URL,
   nessun secret reale;
3. `docs/deploy/LOCAL_DOCKER_COMPOSE.md` contiene smoke, rollback
   SQLite, Redis, cancellazione volumi;
4. script `scripts/local/{up,down,manage,logs,smoke}` esistono in
   coppia (.sh + .ps1);
5. Italia smoke 35/10/0 invariato.
"""

from __future__ import annotations

import pathlib
import re
from decimal import Decimal

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]

COMPOSE_PATH = ROOT / "docker-compose.local.yml"
ENV_EXAMPLE_PATH = ROOT / ".env.local.docker.example"
DOCS_PATH = ROOT / "docs" / "deploy" / "LOCAL_DOCKER_COMPOSE.md"
SCRIPTS_DIR = ROOT / "scripts" / "local"


# ---------------------------------------------------------------------------
# Task F.1 — compose ha web + db + redis
# ---------------------------------------------------------------------------


def test_compose_local_declares_web_db_redis_services():
    assert COMPOSE_PATH.exists(), f"missing: {COMPOSE_PATH}"
    text = COMPOSE_PATH.read_text(encoding="utf-8")
    # Match a livello di indentazione 2 (services list).
    for service in ("web:", "db:", "redis:"):
        # Cerca la chiave del servizio come indentata di 2 spazi.
        assert re.search(
            rf"^  {re.escape(service)}", text, flags=re.MULTILINE
        ), f"service '{service}' not declared at indent 2 in compose file"
    # Postgres + Redis healthcheck dichiarati.
    assert "pg_isready" in text
    assert "redis-cli" in text
    assert "ping" in text
    # Build dal Dockerfile esistente.
    assert "dockerfile: Dockerfile" in text


# ---------------------------------------------------------------------------
# Task F.2 — env example: DATABASE_URL, REDIS_URL, no secret reali
# ---------------------------------------------------------------------------


def test_env_example_has_required_keys_and_no_real_secrets():
    assert ENV_EXAMPLE_PATH.exists(), f"missing: {ENV_EXAMPLE_PATH}"
    text = ENV_EXAMPLE_PATH.read_text(encoding="utf-8")
    # Chiavi obbligatorie.
    for key in [
        "DJANGO_SECRET_KEY",
        "DJANGO_DEBUG",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "POSTGRES_DB",
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "DATABASE_URL",
        "REDIS_URL",
        "LEAD_NOTIFICATION_ENABLED=False",
        "SENTRY_DSN=",
        "ADMIN_MFA_REQUIRED=False",
        "PUBLIC_POST_RATE_LIMIT_ENABLED=True",
    ]:
        assert key in text, f"missing key in env example: {key!r}"
    # Niente secret reali: secret_key deve essere il pattern dev
    # `django-insecure-...`. Niente sk_live, niente API keys reali.
    assert "django-insecure-" in text
    for forbidden in ("sk_live_", "AKIA", "ghp_", "AIza"):
        assert forbidden not in text, (
            f"forbidden pattern '{forbidden}' in env example — "
            "potrebbe essere una credenziale reale committata per errore"
        )


# ---------------------------------------------------------------------------
# Task F.3 — doc contiene smoke, rollback SQLite, Redis, volumi
# ---------------------------------------------------------------------------


def test_local_docker_compose_doc_contains_required_sentinels():
    assert DOCS_PATH.exists(), f"missing: {DOCS_PATH}"
    text = DOCS_PATH.read_text(encoding="utf-8").lower()
    for sentinel in [
        "smoke",
        "26268",
        "27353",
        "28439",
        "rollback",
        "sqlite",
        "redis",
        "down -v",
        "celery",  # menzione che Redis è predisposto per Celery futuro
    ]:
        assert sentinel in text, f"sentinel missing in doc: {sentinel!r}"


# ---------------------------------------------------------------------------
# Task F.4 — script locali (.sh + .ps1) esistono in coppia
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["up", "down", "manage", "logs", "smoke"])
def test_local_scripts_exist_for_both_shells(name):
    sh_path = SCRIPTS_DIR / f"{name}.sh"
    ps1_path = SCRIPTS_DIR / f"{name}.ps1"
    assert sh_path.exists(), f"missing: {sh_path}"
    assert ps1_path.exists(), f"missing: {ps1_path}"
    # Ogni script deve riferirsi al compose file locale.
    sh_text = sh_path.read_text(encoding="utf-8")
    ps1_text = ps1_path.read_text(encoding="utf-8")
    assert "docker-compose.local.yml" in sh_text
    assert "docker-compose.local.yml" in ps1_text


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
