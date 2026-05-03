"""Live simulation matrix per F-product-official-source-automation-and-full-site-functional-upgrade.

Esegue una matrice di simulazioni engine-level (no HTTP) per ognuno
dei (jurisdiction, case_type) registrati in `apps.calculators.registry`
e produce un report markdown:

    docs/architecture/LIVE_SIMULATION_MATRIX.md

Casi inclusi:

- Italia road accident, tre input rappresentativi:
    * 35/10/0  → 26 268 / 27 353 / 28 439 EUR (contratto storico TUN 2025).
    * 35/10/50 → range con riduzione 50% per concorso di colpa.
    * 0/100/0  → range "alto" coerente (prossimo al massimo dataset).
- FR/BE road accident → unavailable_requires_legal_validation (placeholder).
- MA/TN international inheritance → unavailable_requires_legal_validation.

Lo script:

- richiede TUN 2025 dataset+formula approved nel DB (preseed via
  `seed_italy_legal_sources` + dataset import). Se mancano, il caso
  Italia esce con `unavailable_requires_legal_validation` e lo script
  segnala "ITALY_DATASET_MISSING" senza fallire — utile in test/CI.
- non crea fonti, dataset o formule.
- non fa HTTP.
- scrive sempre il markdown report.
- exit code 0 se la riga Italia 35/10/0 == 26 268/27 353/28 439 EUR
  (oppure se il dataset è assente in CI; in quel caso flag esplicito).
- exit code 1 se l'Italia restituisce CALCULATED ma con importi
  diversi → regressione bloccante.
"""

from __future__ import annotations

import io
import os
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import django

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.calculators.enums import CalculationStatus, CaseType  # noqa: E402
from apps.cases.services import run_simulation  # noqa: E402

DEFAULT_REPORT_PATH = REPO_ROOT / "docs" / "architecture" / "LIVE_SIMULATION_MATRIX.md"

ITALY_HISTORICAL_CONTRACT = {
    "min": Decimal("26268"),
    "mid": Decimal("27353"),
    "max": Decimal("28439"),
}


@dataclass
class MatrixCase:
    label: str
    jurisdiction_code: str
    case_type: str
    input_data: dict
    expected_status: str
    expected_amounts: dict[str, Decimal] | None = None  # for IT 35/10/0 only
    note: str = ""


CASES = [
    MatrixCase(
        label="Italy road accident — 35/10/0 (historical contract)",
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
        expected_status=CalculationStatus.CALCULATED.value,
        expected_amounts=ITALY_HISTORICAL_CONTRACT,
        note="Contratto storico TUN 2025 — non deve mai cambiare.",
    ),
    MatrixCase(
        label="Italy road accident — 35/10/50 (50% fault reduction)",
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 50,
        },
        expected_status=CalculationStatus.CALCULATED.value,
        note="Fault reduction 50% → range dimezzato esattamente vs 35/10/0.",
    ),
    MatrixCase(
        label="Italy road accident — 0/100/0 (max disability)",
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 0,
            "permanent_disability_percentage": 100,
            "fault_percentage": 0,
        },
        expected_status=CalculationStatus.CALCULATED.value,
        note="Range alto coerente con dataset moral. Dipende da copertura tabellare TUN.",
    ),
    MatrixCase(
        label="France road accident — placeholder",
        jurisdiction_code="FR-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "permanent_disability_percentage": 10},
        expected_status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
        note="Engine placeholder, fonti needs_review.",
    ),
    MatrixCase(
        label="Belgium road accident — placeholder",
        jurisdiction_code="BE-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={"victim_age": 35, "permanent_disability_percentage": 10},
        expected_status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
        note="Engine placeholder, Tableau Indicatif/Schryvers needs_review.",
    ),
    MatrixCase(
        label="Morocco international inheritance — placeholder",
        jurisdiction_code="MA-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={},
        expected_status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
        note="Engine placeholder, mapping conflitti di legge.",
    ),
    MatrixCase(
        label="Tunisia international inheritance — placeholder",
        jurisdiction_code="TN-NATIONAL",
        case_type=CaseType.INTERNATIONAL_INHERITANCE.value,
        input_data={},
        expected_status=CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value,
        note="Engine placeholder, CSP Livre IX + Loi 98-97.",
    ),
]


@dataclass
class MatrixResult:
    case: MatrixCase
    actual_status: str
    actual_min: Decimal | None
    actual_mid: Decimal | None
    actual_max: Decimal | None
    contract_ok: bool
    flag: str = ""


def run_matrix() -> list[MatrixResult]:
    results: list[MatrixResult] = []
    for case in CASES:
        try:
            sim = run_simulation(
                jurisdiction_code=case.jurisdiction_code,
                case_type=case.case_type,
                input_data=case.input_data,
            )
        except Exception as exc:  # noqa: BLE001 — defensive for matrix
            results.append(
                MatrixResult(
                    case=case,
                    actual_status="error",
                    actual_min=None,
                    actual_mid=None,
                    actual_max=None,
                    contract_ok=False,
                    flag=f"EXCEPTION: {exc.__class__.__name__}: {exc}",
                )
            )
            continue

        actual_min = sim.estimated_min
        actual_mid = sim.estimated_mid
        actual_max = sim.estimated_max
        contract_ok = True
        flag = ""

        if (
            case.expected_status == CalculationStatus.CALCULATED.value
            and sim.status != CalculationStatus.CALCULATED.value
        ):
            # Italy without dataset preseeded → flag, do not fail.
            flag = "ITALY_DATASET_MISSING_OR_PLACEHOLDER"
            contract_ok = case.expected_amounts is None
        elif (
            case.expected_status != CalculationStatus.CALCULATED.value
            and sim.status == CalculationStatus.CALCULATED.value
        ):
            flag = "UNEXPECTED_CALCULATED"
            contract_ok = False
        elif case.expected_amounts is not None and sim.status == CalculationStatus.CALCULATED.value:
            # Strict equality on the historical contract.
            if (
                actual_min == case.expected_amounts["min"]
                and actual_mid == case.expected_amounts["mid"]
                and actual_max == case.expected_amounts["max"]
            ):
                contract_ok = True
            else:
                contract_ok = False
                flag = "ITALY_HISTORICAL_CONTRACT_REGRESSION"

        results.append(
            MatrixResult(
                case=case,
                actual_status=sim.status,
                actual_min=actual_min,
                actual_mid=actual_mid,
                actual_max=actual_max,
                contract_ok=contract_ok,
                flag=flag,
            )
        )
    return results


def render_markdown(results: list[MatrixResult]) -> str:
    out = io.StringIO()
    out.write("# Live simulation matrix — engine-level run\n\n")
    out.write(
        f"Generated: `{datetime.now(UTC).isoformat()}` "
        "(F-product-official-source-automation-and-full-site-functional-upgrade)\n\n"
    )
    out.write(
        "Matrice di simulazioni eseguita engine-level via "
        "`apps.cases.services.run_simulation`. Niente HTTP, niente DB write "
        "non previsto: lo script chiama il motore in modalità simulation "
        "save (la persistenza Simulation è una scrittura tracciata, non un "
        "side-effect su layer legale).\n\n"
    )
    out.write("## Riepilogo\n\n")
    italy_contract_row = next(
        (r for r in results if r.case.expected_amounts == ITALY_HISTORICAL_CONTRACT),
        None,
    )
    if italy_contract_row:
        if italy_contract_row.flag == "ITALY_DATASET_MISSING_OR_PLACEHOLDER":
            out.write(
                "- Italia 35/10/0: dataset TUN 2025 non disponibile in questo run "
                "(es. ambiente CI senza fixture). Status engine: "
                f"`{italy_contract_row.actual_status}`.\n"
            )
        elif italy_contract_row.contract_ok:
            out.write("- Italia 35/10/0: **OK** — 26 268 / 27 353 / 28 439 EUR confermato.\n")
        else:
            out.write(
                "- Italia 35/10/0: **REGRESSIONE** — actual "
                f"{italy_contract_row.actual_min}/{italy_contract_row.actual_mid}/"
                f"{italy_contract_row.actual_max} EUR.\n"
            )
    out.write("\n## Tabella completa\n\n")
    out.write("| Case | Jurisdiction | Status | min | mid | max | Flag |\n")
    out.write("|------|--------------|--------|-----|-----|-----|------|\n")
    for r in results:
        out.write(
            f"| {r.case.label} | {r.case.jurisdiction_code} | "
            f"`{r.actual_status}` | "
            f"{r.actual_min if r.actual_min is not None else '—'} | "
            f"{r.actual_mid if r.actual_mid is not None else '—'} | "
            f"{r.actual_max if r.actual_max is not None else '—'} | "
            f"{r.flag or 'OK'} |\n"
        )
    out.write("\n## Dettagli per caso\n\n")
    for r in results:
        out.write(f"### {r.case.label}\n\n")
        out.write(f"- Jurisdiction: `{r.case.jurisdiction_code}`\n")
        out.write(f"- Case type: `{r.case.case_type}`\n")
        out.write(f"- Input: `{r.case.input_data}`\n")
        out.write(f"- Expected status: `{r.case.expected_status}`\n")
        out.write(f"- Actual status: `{r.actual_status}`\n")
        if r.case.expected_amounts:
            out.write(
                "- Expected amounts: "
                f"min={r.case.expected_amounts['min']} mid={r.case.expected_amounts['mid']} "
                f"max={r.case.expected_amounts['max']}\n"
            )
        out.write(f"- Actual amounts: min={r.actual_min} mid={r.actual_mid} max={r.actual_max}\n")
        out.write(f"- Note: {r.case.note}\n")
        out.write(f"- Flag: `{r.flag or 'OK'}`\n\n")
    out.write("---\n\n")
    out.write(
        "Generato da `scripts/live_simulation_matrix.py`. Lo script `run_simulation` persiste "
        "una `Simulation` in DB per ogni caso (scrittura attesa). Nessuna `LegalReview`, "
        "`CompensationDataset` o `CalculationFormula` viene creata o modificata.\n"
    )
    return out.getvalue()


def main() -> int:
    results = run_matrix()
    md = render_markdown(results)
    DEFAULT_REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_REPORT_PATH.write_text(md, encoding="utf-8")
    print(f"[matrix] report -> {DEFAULT_REPORT_PATH}")
    for r in results:
        mark = "OK" if r.contract_ok and not r.flag else (r.flag or "FAIL")
        print(
            f"  [{mark:>32}] {r.case.label:<60} status={r.actual_status} "
            f"amounts=({r.actual_min}/{r.actual_mid}/{r.actual_max})"
        )
    italy_contract_row = next(
        (r for r in results if r.case.expected_amounts == ITALY_HISTORICAL_CONTRACT),
        None,
    )
    if (
        italy_contract_row
        and italy_contract_row.actual_status == CalculationStatus.CALCULATED.value
        and not italy_contract_row.contract_ok
    ):
        print("[matrix] FATAL: Italy 35/10/0 contract broken!", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
