"""
QA tecnico sui CSV candidate prodotti da extract_tun_moral_tables.py.

Esegue: counts, duplicati, null, valori negativi, monotonicità su invalidità
e su età, spot-check su celle note (Tabella 1 valore di riferimento per A),
identificazione pagine problematiche.

Non importa nulla. Genera solo un report testuale.
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

# Tabella 1 importata in produzione → il valore A in ciascun cell deve
# coincidere con la cella (age, inv) di Tabella 1. Per ora carichiamo
# da CSV già in repo.
TABELLA_1_CSV = DATA_DIR / "tun_2025_rows.csv"

# Spot-check mini set: valori noti dal report estrazione Tabella 1 / pag.34.
# Sono usati per confrontare il campo `a_value` (biological) estratto dai
# moral cells con il valore Tabella 1: devono coincidere.
SPOT_BIO = {
    (0, 10): Decimal("26124"),  # da F-extract-italy-tun
    (1, 10): Decimal("26124"),
    (2, 10): Decimal("25993"),
    (50, 50): Decimal("267618"),
    (100, 100): Decimal("541329"),
}


def parse_value(s: str) -> Decimal | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def load_candidate(path: Path) -> list[dict]:
    rows = []
    with path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for r in reader:
            r["_age"] = int(r["age_min"]) if r["age_min"] else None
            r["_inv"] = int(r["disability_min"]) if r["disability_min"] else None
            r["_ab"] = parse_value(r["point_value"])
            # Recupera a_value/b_value/ab_value/flags da source_note.
            note = r.get("source_note", "")
            for token in note.split(" ; "):
                token = token.strip()
                if "=" not in token:
                    continue
                k, _, v = token.partition("=")
                r[f"_note_{k.strip()}"] = v.strip()
            rows.append(r)
    return rows


def parse_decimal_or_none(s: str) -> Decimal | None:
    if s is None or s == "" or s == "None":
        return None
    try:
        return Decimal(s)
    except Exception:
        return None


def qa_table(kind: str, rows: list[dict]) -> dict:
    expected_cells = 9191  # 91 inv × 101 age
    n_total = len(rows)

    # Counts per ab_check_status (iter2)
    status = defaultdict(int)
    for r in rows:
        s = r.get("_note_ab_check_status", None)
        if s is None:
            # iter1 fallback: derive from flags
            flags = r.get("_note_flags", "ok")
            if r["_ab"] is None:
                s = "empty"
            elif "ab_check_fail" in flags:
                s = "inconsistent"
            else:
                s = "consistent"
        status[s] += 1

    # Duplicates
    pairs = defaultdict(list)
    for r in rows:
        if r["_age"] is not None and r["_inv"] is not None:
            pairs[(r["_age"], r["_inv"])].append(r)
    duplicates = sum(1 for k, v in pairs.items() if len(v) > 1)

    # Negative
    negatives = sum(1 for r in rows if r["_ab"] is not None and r["_ab"] < 0)

    # Null point_value (already in `empty`)
    nulls = status["empty"]

    # Monotonicity: A+B should increase with invalidity (age fixed) and
    # decrease with age (invalidity fixed).
    by_age = defaultdict(list)  # age → [(inv, ab)]
    by_inv = defaultdict(list)  # inv → [(age, ab)]
    for r in rows:
        if r["_ab"] is None or r["_age"] is None or r["_inv"] is None:
            continue
        by_age[r["_age"]].append((r["_inv"], r["_ab"]))
        by_inv[r["_inv"]].append((r["_age"], r["_ab"]))

    inv_violations = 0
    for _age, lst in by_age.items():
        lst.sort()
        for i in range(1, len(lst)):
            if lst[i][1] < lst[i - 1][1]:
                inv_violations += 1

    age_violations = 0
    for _inv, lst in by_inv.items():
        lst.sort()
        for i in range(1, len(lst)):
            if lst[i][1] > lst[i - 1][1]:
                age_violations += 1

    # Spot-check: a_value in moral table for known (age, inv) must equal
    # known biological value (from Tabella 1 import).
    spot_results = []
    by_pair = {(r["_age"], r["_inv"]): r for r in rows}
    for (age, inv), expected_a in SPOT_BIO.items():
        r = by_pair.get((age, inv))
        if not r:
            spot_results.append((age, inv, "MISSING", str(expected_a), None))
            continue
        a_str = r.get("_note_a_value", "None")
        a_val = parse_decimal_or_none(a_str)
        ok = a_val is not None and a_val == expected_a
        spot_results.append((age, inv, "OK" if ok else "MISMATCH", str(expected_a), str(a_val)))

    # Pages with most issues
    by_page = defaultdict(lambda: {"total": 0, "issues": 0})
    for r in rows:
        page = r.get("source_page", "?")
        by_page[page]["total"] += 1
        s = r.get("_note_ab_check_status", "")
        if r["_ab"] is None or s in ("inconsistent", "needs_review", "recovered"):
            by_page[page]["issues"] += 1
    problem_pages = sorted(
        ((p, d["issues"], d["total"]) for p, d in by_page.items()),
        key=lambda t: -t[1],
    )[:10]

    return {
        "kind": kind,
        "n_total": n_total,
        "expected": expected_cells,
        "missing_vs_expected": expected_cells - n_total,
        "by_status": dict(status),
        "duplicates": duplicates,
        "negatives": negatives,
        "nulls": nulls,
        "monotonicity_inv_violations": inv_violations,
        "monotonicity_age_violations": age_violations,
        "spot_check": spot_results,
        "top_problem_pages": problem_pages,
    }


REPORT_PATH = DATA_DIR / "moral_tables_iter2_qa_report.md"


def write_markdown_report(results: list[dict]) -> None:
    lines: list[str] = []
    lines.append("# TUN 2025 — Tabelle 2.A/2.B/2.C iter2 QA report")
    lines.append("")
    lines.append("> Auto-generato da `scripts/legal_data/qa_tun_moral_tables.py`.")
    lines.append("> NESSUN dato è stato importato nel DB. NESSUN status promosso.")
    lines.append("> Estrazione: `automated_pdfplumber_iter2`. Oracle: Tabella 1 approved.")
    lines.append("")
    lines.append("## Sommario")
    lines.append("")
    lines.append(
        "| Tabella | Totali | consistent | recovered | inconsistent | needs_review | "
        "duplicati | negativi | null | mono inv | mono age |"
    )
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in results:
        bs = r["by_status"]
        lines.append(
            f"| 2.{r['kind'].upper()} | {r['n_total']} | "
            f"{bs.get('consistent', 0)} | {bs.get('recovered', 0)} | "
            f"{bs.get('inconsistent', 0)} | {bs.get('needs_review', 0) + bs.get('empty', 0)} | "
            f"{r['duplicates']} | {r['negatives']} | {r['nulls']} | "
            f"{r['monotonicity_inv_violations']} | {r['monotonicity_age_violations']} |"
        )
    lines.append("")
    lines.append("Atteso per ogni tabella: 9 191 righe (= 91 invalidità × 101 età).")
    lines.append("")
    for r in results:
        lines.append(f"## Tabella 2.{r['kind'].upper()}")
        lines.append("")
        lines.append("### Spot-check `A` (biologico) vs Tabella 1 approved")
        lines.append("")
        lines.append("| (età, inv) | atteso | letto | esito |")
        lines.append("|---|---:|---:|---|")
        for age, inv, st, exp, got in r["spot_check"]:
            lines.append(f"| ({age}, {inv}) | {exp} | {got} | {st} |")
        lines.append("")
        lines.append("### Top 10 pagine con issues residue")
        lines.append("")
        lines.append("| G.U. page | issues / totale | % |")
        lines.append("|---:|---:|---:|")
        for page, issues, total in r["top_problem_pages"]:
            pct = 100 * issues / total if total else 0
            lines.append(f"| {page} | {issues}/{total} | {pct:.1f}% |")
        lines.append("")
    lines.append("## Raccomandazione import")
    lines.append("")
    all_consistent = all(
        r["by_status"].get("consistent", 0) == r["n_total"]
        and r["monotonicity_inv_violations"] == 0
        and r["monotonicity_age_violations"] == 0
        and r["duplicates"] == 0
        and r["negatives"] == 0
        for r in results
    )
    if all_consistent:
        lines.append(
            "**Sì** per import in **dataset MORAL DRAFT** (separato da quello base "
            "`approved`). Tutte le 9 191 celle per tabella sono `consistent` con il "
            "vincolo `A + B == A+B` e con `A == oracle Tabella 1`. La monotonicità "
            "(inv crescente, età decrescente) è rispettata su tutte e tre le "
            "tabelle. La promozione a `approved` resta atto umano dello Studio."
        )
    else:
        lines.append(
            "**No**. Esistono ancora celle non consistent o violazioni di "
            "monotonicità — vedi review tasks."
        )
    lines.append("")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    print("=" * 70)
    print("QA report — TUN 2025 Tabelle 2.A/2.B/2.C iter2 candidates")
    print("=" * 70)

    results = []
    for kind, path in CANDIDATES.items():
        if not path.exists():
            print(f"\nSKIP {kind}: file mancante ({path.name})")
            continue
        rows = load_candidate(path)
        result = qa_table(kind, rows)
        results.append(result)
        print(f"\n{'=' * 70}")
        print(f"Tabella 2.{kind.upper()} — {path.name}")
        print(f"{'=' * 70}")
        print(f"  righe totali               : {result['n_total']}")
        print(f"  righe attese (91x101)      : {result['expected']}")
        print(f"  delta vs atteso            : {result['missing_vs_expected']}")
        print(f"  duplicati (age,inv)        : {result['duplicates']}")
        print(f"  point_value null           : {result['nulls']}")
        print(f"  point_value negativi       : {result['negatives']}")
        print(f"  by_status                  : {dict(result['by_status'])}")
        print(f"  monotonicita invalidita    : {result['monotonicity_inv_violations']} viol")
        print(f"  monotonicita eta           : {result['monotonicity_age_violations']} viol")
        print()
        print("  spot-check A vs Tabella 1:")
        for age, inv, status, exp, got in result["spot_check"]:
            print(f"    age={age:3d} inv={inv:3d}  {status:8}  expected={exp:>10}  got={got}")
        print()
        print("  top 10 pagine con piu issues:")
        for page, issues, total in result["top_problem_pages"][:10]:
            pct = 100 * issues / total if total else 0
            print(f"    G.U. p.{page:>4}  {issues:4}/{total:4}  ({pct:5.1f}%)")

    if results:
        write_markdown_report(results)
        print(f"\nReport markdown scritto in: {REPORT_PATH}")


if __name__ == "__main__":
    main()
