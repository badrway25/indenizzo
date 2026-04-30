"""
Read-only smoke test della prontezza del database (qualunque backend).

Iter: F-local-product-hardening-pass4-postgres-prep.

Uso:
    .venv/Scripts/python.exe scripts/staging/smoke_database_readiness.py

Verifica:
1. **Migrazioni**: nessuna migrazione non applicata.
2. **Conteggi**: stampa LegalSource / CompensationDataset /
   CalculationFormula totali (per dare un colpo d'occhio).
3. **Italy smoke 35/10/0**: se esiste almeno una `LegalSource` IT
   `approved` collegata a un `CompensationDataset` `approved` per
   `road_accident_bodily_injury`, chiama il calculator direttamente
   (`ItalyRoadAccidentBodilyInjuryCalculator(language='it').compute(...)`)
   e verifica che ritorni `status=calculated` con min/mid/max =
   26 268 / 27 353 / 28 439 EUR.
   **Pure-compute**: il calculator legge solo righe `approved` e NON
   persiste alcuna `Simulation` (a differenza di `run_simulation` che
   è il path utente). Lo smoke quindi non scrive nel DB.
   Se i dati IT non sono presenti (DB fresco, pre-import), stampa
   `SKIP` con motivo chiaro e ritorna 0 — NON è un errore: il
   smoke è progettato per essere eseguito anche su un DB vuoto
   appena migrato.

Politica exit code:
- 0 = tutto OK (o legittimo SKIP).
- 1 = anomalia riproducibile (es. valori IT diversi da
  contratto, migrazioni non applicate).

NON modifica DB, NON crea record, NON applica migrate.
"""

from __future__ import annotations

import os
import pathlib
import sys
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Contratto smoke Italia: pinnato e versionato. Cambia solo via iter
# esplicito di update Italia.
SMOKE_INPUT = {
    "victim_age": 35,
    "permanent_disability_percentage": 10,
    "fault_percentage": 0,
}
SMOKE_EXPECTED_MIN = Decimal("26268")
SMOKE_EXPECTED_MID = Decimal("27353")
SMOKE_EXPECTED_MAX = Decimal("28439")


def _bootstrap_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import django

    django.setup()


def _check_migrations() -> int:
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor

    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    if plan:
        print(f"[FAIL] migrations not applied: {len(plan)} pending")
        for migration, _ in plan:
            print(f"   - {migration}")
        return 1
    print("[OK] all migrations applied")
    return 0


def _print_counts() -> None:
    from apps.compensation.models import CalculationFormula, CompensationDataset
    from apps.legal_sources.models import LegalSource

    print()
    print("Counts:")
    print(f"  LegalSource:           {LegalSource.objects.count()}")
    print(f"  CompensationDataset:   {CompensationDataset.objects.count()}")
    print(f"  CalculationFormula:    {CalculationFormula.objects.count()}")


def _can_run_italy_smoke() -> tuple[bool, str]:
    """Ritorna (ok, reason). Se ok=False, reason spiega il SKIP."""
    from apps.calculators.enums import CaseType
    from apps.compensation.models import CompensationDataset, DatasetStatus
    from apps.jurisdictions.models import Country
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.filter(code="IT").first()
    if italy is None:
        return False, "Country 'IT' non presente nel DB"
    src = LegalSource.objects.filter(country=italy, status=SourceStatus.APPROVED).first()
    if src is None:
        return False, "Nessuna LegalSource IT in stato 'approved'"
    ds = CompensationDataset.objects.filter(
        country=italy,
        status=DatasetStatus.APPROVED,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
    ).first()
    if ds is None:
        return False, "Nessun CompensationDataset IT 'approved' per road_accident"
    return True, ""


def _run_italy_smoke() -> int:
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    # Pure-compute: il calculator NON persiste Simulation. È
    # equivalente al contratto smoke usato da scripts/staging/smoke.sh.
    calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
    result = calc.compute(SMOKE_INPUT)

    print()
    print("Italy smoke 35/10/0 (pure-compute, no DB write):")
    print(f"  status:        {result.status}")
    print(f"  estimated_min: {result.estimated_min}")
    print(f"  estimated_mid: {result.estimated_mid}")
    print(f"  estimated_max: {result.estimated_max}")

    failures = []
    if result.status != CalculationStatus.CALCULATED.value:
        failures.append(f"status != calculated (got {result.status})")
    if result.estimated_min != SMOKE_EXPECTED_MIN:
        failures.append(f"min != {SMOKE_EXPECTED_MIN} (got {result.estimated_min})")
    if result.estimated_mid != SMOKE_EXPECTED_MID:
        failures.append(f"mid != {SMOKE_EXPECTED_MID} (got {result.estimated_mid})")
    if result.estimated_max != SMOKE_EXPECTED_MAX:
        failures.append(f"max != {SMOKE_EXPECTED_MAX} (got {result.estimated_max})")

    if failures:
        print("[FAIL] smoke contract violato:")
        for f in failures:
            print(f"   - {f}")
        return 1
    print(
        f"[OK] smoke contract Italia confermato: "
        f"{SMOKE_EXPECTED_MIN}/{SMOKE_EXPECTED_MID}/{SMOKE_EXPECTED_MAX}"
    )
    return 0


def main() -> int:
    _bootstrap_django()

    print("=" * 64)
    print("DATABASE READINESS SMOKE (read-only)")
    print("=" * 64)

    failures = 0
    failures += _check_migrations()
    _print_counts()

    can_run, reason = _can_run_italy_smoke()
    if not can_run:
        print()
        print(f"[SKIP] Italy smoke skipped — {reason}")
        print(
            "       (DB pre-import o senza approval IT: NON è un errore di per sé. "
            "Eseguire bootstrap_italy_tun + LegalReview firmata per attivare il "
            "contratto smoke 26268/27353/28439.)"
        )
        print()
        if failures == 0:
            print("OK (no smoke run, but DB readiness checks passed).")
        else:
            print(f"FAILED ({failures} anomalie).")
        return failures

    failures += _run_italy_smoke()

    print()
    if failures == 0:
        print("OK — DB pronto e contratto Italia confermato.")
        return 0
    print(f"FAILED ({failures} anomalie).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
