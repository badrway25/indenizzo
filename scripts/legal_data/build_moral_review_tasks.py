"""
Genera review_tasks per le Tabelle 2.A/2.B/2.C (iter2).

Una review task è una riga che lo Studio deve verificare manualmente
prima di promuovere i dati a `approved`. Includiamo:
- celle con `ab_check_status` != consistent (al momento 0);
- celle empty/null (al momento 0);
- celle "recovered" (al momento 0);
- celle delle pagine storicamente calde (G.U. 63/95/128 della rispettiva
  tabella — sono le pagine con valori >1M);
- celle con `point_value` >= 1 000 000 (sample obbligatoriamente
  human-checked perché magnitudo elevata);
- monotonicity issue (al momento 0).

Output:
    legal_data/sources/italy/tun_2025/tun_2025_moral_review_tasks.csv

Schema (richiesta utente):
    table_type, issue_type, priority, row_type, age_min, age_max,
    disability_min, disability_max, current_point_value, source_page,
    source_note, reviewer_corrected_value, reviewer_status, reviewer_notes
"""

from __future__ import annotations

import csv
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "legal_data" / "sources" / "italy" / "tun_2025"

CANDIDATES = {
    "min": DATA_DIR / "tun_2025_moral_min_candidate.csv",
    "mid": DATA_DIR / "tun_2025_moral_mid_candidate.csv",
    "max": DATA_DIR / "tun_2025_moral_max_candidate.csv",
}

# Pagine storicamente calde dell'estrazione iter1 (>1M cells, primo page
# di ciascuna fascia inv 71-100).
HOT_PAGES = {"min": "63", "mid": "95", "max": "128"}

OUT_PATH = DATA_DIR / "tun_2025_moral_review_tasks.csv"

ONE_MILLION = Decimal("1000000")


def load(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        for row in csv.DictReader(fh):
            ab_status = "consistent"
            for tok in row["source_note"].split(" ; "):
                if tok.strip().startswith("ab_check_status="):
                    ab_status = tok.strip().split("=", 1)[1]
                    break
            row["_ab_check_status"] = ab_status
            try:
                row["_pv"] = Decimal(row["point_value"]) if row["point_value"] else None
            except Exception:
                row["_pv"] = None
            rows.append(row)
    return rows


def detect_monotonicity_issues(rows: list[dict]) -> set[tuple[int, int]]:
    by_age: dict[int, list[tuple[int, Decimal]]] = defaultdict(list)
    by_inv: dict[int, list[tuple[int, Decimal]]] = defaultdict(list)
    for r in rows:
        if r["_pv"] is None:
            continue
        a = int(r["age_min"])
        i = int(r["disability_min"])
        by_age[a].append((i, r["_pv"]))
        by_inv[i].append((a, r["_pv"]))
    bad: set[tuple[int, int]] = set()
    for a, lst in by_age.items():
        lst.sort()
        for k in range(1, len(lst)):
            if lst[k][1] < lst[k - 1][1]:
                bad.add((a, lst[k][0]))
                bad.add((a, lst[k - 1][0]))
    for i, lst in by_inv.items():
        lst.sort()
        for k in range(1, len(lst)):
            if lst[k][1] > lst[k - 1][1]:
                bad.add((lst[k][0], i))
                bad.add((lst[k - 1][0], i))
    return bad


def main():
    out_rows = []
    for kind, path in CANDIDATES.items():
        if not path.exists():
            continue
        rows = load(path)
        mono_issues = detect_monotonicity_issues(rows)
        hot_page = HOT_PAGES.get(kind)

        for r in rows:
            issue_types: list[str] = []
            priority = "low"

            ab = r["_ab_check_status"]
            if ab == "inconsistent":
                issue_types.append("inconsistent")
                priority = "high"
            elif ab == "needs_review" or r["_pv"] is None:
                issue_types.append("empty_or_null")
                priority = "high"
            elif ab == "recovered":
                issue_types.append("recovered")
                priority = "medium"

            if hot_page is not None and r["source_page"] == hot_page:
                issue_types.append("hot_page")
                if priority == "low":
                    priority = "medium"

            if r["_pv"] is not None and r["_pv"] >= ONE_MILLION:
                issue_types.append("over_one_million")
                if priority == "low":
                    priority = "medium"

            age = int(r["age_min"])
            inv = int(r["disability_min"])
            if (age, inv) in mono_issues:
                issue_types.append("monotonicity_violation")
                priority = "high"

            if not issue_types:
                continue

            out_rows.append(
                {
                    "table_type": f"2.{kind.upper()}",
                    "issue_type": ",".join(issue_types),
                    "priority": priority,
                    "row_type": r["row_type"],
                    "age_min": r["age_min"],
                    "age_max": r["age_max"],
                    "disability_min": r["disability_min"],
                    "disability_max": r["disability_max"],
                    "current_point_value": r["point_value"],
                    "source_page": r["source_page"],
                    "source_note": r["source_note"],
                    "reviewer_corrected_value": "",
                    "reviewer_status": "pending",
                    "reviewer_notes": "",
                }
            )

    out_rows.sort(
        key=lambda x: (x["priority"], x["table_type"], int(x["age_min"]), int(x["disability_min"]))
    )

    with OUT_PATH.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=[
                "table_type",
                "issue_type",
                "priority",
                "row_type",
                "age_min",
                "age_max",
                "disability_min",
                "disability_max",
                "current_point_value",
                "source_page",
                "source_note",
                "reviewer_corrected_value",
                "reviewer_status",
                "reviewer_notes",
            ],
        )
        writer.writeheader()
        for row in out_rows:
            writer.writerow(row)

    print(f"Review tasks scritti: {len(out_rows)} -> {OUT_PATH}")
    from collections import Counter

    by_priority = Counter(r["priority"] for r in out_rows)
    by_table = Counter(r["table_type"] for r in out_rows)
    by_issue = Counter(t for r in out_rows for t in r["issue_type"].split(","))
    print(f"  by priority : {dict(by_priority)}")
    print(f"  by table    : {dict(by_table)}")
    print(f"  by issue    : {dict(by_issue)}")


if __name__ == "__main__":
    main()
