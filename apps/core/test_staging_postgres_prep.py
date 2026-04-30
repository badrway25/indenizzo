"""
Tests F-local-product-hardening-pass4-postgres-prep.

Coprono:
- import + esecuzione di `scripts/staging/check_database_backend.py`;
- `smoke_database_readiness.main()` su DB pulito (caso SKIP);
- `smoke_database_readiness.main()` su DB con dati IT (caso OK
  con valori 26268/27353/28439);
- `POSTGRES_LOCAL_STAGING_PREP.md` contiene le sentinelle minime
  (DATABASE_URL, migrate, rollback, smoke);
- Italia smoke contract via run_simulation invariato.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys
from decimal import Decimal

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts" / "staging"
DOCS_PATH = ROOT / "docs" / "deploy" / "POSTGRES_LOCAL_STAGING_PREP.md"


def _import_script(name: str):
    """Importa un .py da scripts/staging/ come modulo (file-based)."""
    path = SCRIPTS_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_staging_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fixtures
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


# ---------------------------------------------------------------------------
# Task E.1 — check_database_backend importable, esegue, non scrive
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_check_database_backend_runs_without_crashing_and_does_not_write(capsys):
    from apps.compensation.models import CompensationDataset
    from apps.legal_sources.models import LegalSource

    pre_sources = LegalSource.objects.count()
    pre_datasets = CompensationDataset.objects.count()

    module = _import_script("check_database_backend")
    rc = module.main()
    out = capsys.readouterr().out

    # Nessuna scrittura.
    assert LegalSource.objects.count() == pre_sources
    assert CompensationDataset.objects.count() == pre_datasets

    # Output minimale.
    assert "DATABASE BACKEND CHECK" in out
    assert "vendor:" in out
    assert "applied migrations:" in out
    # Su SQLite (test default) si aspetta WARNING + rc=0; su Postgres OK + rc=0.
    assert rc == 0


# ---------------------------------------------------------------------------
# Task E.2 — smoke_database_readiness su DB vuoto (SKIP graceful)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_smoke_database_readiness_skips_gracefully_on_empty_db(capsys):
    """Senza dati IT 'approved', il smoke fa SKIP e ritorna 0."""
    module = _import_script("smoke_database_readiness")
    rc = module.main()
    out = capsys.readouterr().out

    assert "all migrations applied" in out
    assert "SKIP" in out
    assert "Italy smoke skipped" in out
    assert rc == 0


# ---------------------------------------------------------------------------
# Task E.3 — smoke_database_readiness con stack IT seedato (OK + valori)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_smoke_database_readiness_validates_italy_contract(italy_smoke_stack, capsys):
    """Con stack IT presente, il smoke calcola e verifica 26268/27353/28439."""
    module = _import_script("smoke_database_readiness")
    rc = module.main()
    out = capsys.readouterr().out

    assert "Italy smoke 35/10/0" in out
    assert "calculated" in out
    assert "26268" in out
    assert "27353" in out
    assert "28439" in out
    assert "smoke contract Italia confermato" in out
    assert rc == 0


# ---------------------------------------------------------------------------
# Task E.4 — documentazione contiene sentinelle minime
# ---------------------------------------------------------------------------


def test_postgres_prep_doc_contains_required_sentinels():
    """Il doc deve guidare Studio attraverso DATABASE_URL, migrate,
    rollback a SQLite e smoke contract."""
    assert DOCS_PATH.exists(), f"missing: {DOCS_PATH}"
    text = DOCS_PATH.read_text(encoding="utf-8").lower()
    # Sentinelle case-insensitive: importa la presenza concettuale, non
    # la capitalizzazione (es. titoli di sezione possono essere
    # capitalized).
    for sentinel in [
        "database_url",
        "migrate",
        "rollback",
        "smoke",
        "26268",
        "sqlite",
        "postgres",
    ]:
        assert sentinel in text, f"sentinel missing in doc: {sentinel!r}"


# ---------------------------------------------------------------------------
# Task E.5 — Italia smoke run_simulation invariato
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
