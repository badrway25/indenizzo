"""
QA READ-ONLY dei CSV candidate generati da extract_france_gazette_2022.py.

Iter: F-france-extraction-gazette-capitalisation · iter1
Stato: read-only. Non importa nel DB. Non modifica i CSV.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/qa_france_gazette_2022.py

Verifica:
- conteggi attesi / trovati per (sex, rate) e per page;
- duplicati (chiave: row_type + sex + age + rate + target_age?);
- celle null (coefficient mancante);
- valori negativi (vietati per coefficient);
- monotonicità: per (sex, rate) fissati, viager(coefficient) deve
  decrescere con l'età (più anziano = capitale minore);
- monotonicità rate: per (sex, age) fissati, viager(rate=-1.00) >
  viager(rate=0.00) (tasso più basso = capitale maggiore);
- spot-check ufficiale presente nel PDF (p.4):
  F, age 32, rate=-1.00 -> 72.459
  F, age 32, rate=0.00  -> 53.564
- temporaire: per (sex, rate, age) fissati, coefficient cresce con
  target_age;
- copertura completa: 4 (sex,rate) combos x 104 ages = 416 viager;
- anticipated: 2 rates x 5 ages x 2 sex = 20 rows.

Exit code 0 = tutto OK. Exit code 1 = anomalie rilevate (le stampa).
Le anomalie NON sono fatali: i CSV sono candidate, lo Studio review.
"""

from __future__ import annotations

import csv
import json
import pathlib
import sys
from collections import defaultdict
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]
CSV_DIR = ROOT / "legal_data" / "sources" / "france" / "gazette_2022"

VIAGER = CSV_DIR / "fr-gazette-2022-capitalisation-viagere.csv"
TEMPORAIRE = CSV_DIR / "fr-gazette-2022-capitalisation-temporaire.csv"
ANTICIPATED = CSV_DIR / "fr-gazette-2022-anticipated-payment-years.csv"
SUMMARY = CSV_DIR / "extraction_summary.json"

EXPECTED = {
    "viager_rows_total": 416,  # 4 combos x 104 ages
    "anticipated_rows_total": 20,  # 2 rates x 5 ages x 2 sex
    "viager_per_combo_age_count": 104,  # ages 0..103
    "sex_rate_combos": [("F", "-1.00"), ("M", "-1.00"), ("F", "0.00"), ("M", "0.00")],
}

SPOT_CHECKS_PDF_EXAMPLE = [
    # (sex, age, rate_pct, expected_coefficient, source = PDF p.4 esempio)
    ("F", 32, "-1.00", Decimal("72.459")),
    ("F", 32, "0.00", Decimal("53.564")),
]


def line(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")
    return ok


def load_csv(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        print(f"[FATAL] CSV non trovato: {path}")
        sys.exit(2)
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    print("=" * 70)
    print("QA — fr-bareme-capitalisation-gazette-palais-2022")
    print("(read-only, nessuna modifica ai CSV)")
    print("=" * 70)

    failures = 0

    viager = load_csv(VIAGER)
    temporaire = load_csv(TEMPORAIRE)
    anticipated = load_csv(ANTICIPATED)
    if SUMMARY.exists():
        json.loads(SUMMARY.read_text(encoding="utf-8"))

    print("\n1. Conteggi totali")
    if not line(
        "viager rows == 416",
        len(viager) == EXPECTED["viager_rows_total"],
        f"got={len(viager)}",
    ):
        failures += 1
    if not line(
        "anticipated rows == 20",
        len(anticipated) == EXPECTED["anticipated_rows_total"],
        f"got={len(anticipated)}",
    ):
        failures += 1
    print(f"  [INFO] temporaire rows = {len(temporaire)} (varia per via di target_age <= age)")

    print("\n2. Distribuzione viager per (sex, rate)")
    by_combo: dict[tuple, int] = defaultdict(int)
    for r in viager:
        by_combo[(r["sex"], r["interest_rate_pct"])] += 1
    for sex, rate in EXPECTED["sex_rate_combos"]:
        c = by_combo.get((sex, rate), 0)
        if not line(
            f"({sex}, {rate}) ages = 104",
            c == EXPECTED["viager_per_combo_age_count"],
            f"got={c}",
        ):
            failures += 1

    print("\n3. Range età viager (atteso 0..103)")
    ages = sorted({int(r["age"]) for r in viager})
    if not line("min age == 0", ages[0] == 0, f"min={ages[0]}"):
        failures += 1
    if not line("max age == 103", ages[-1] == 103, f"max={ages[-1]}"):
        failures += 1
    if not line(
        "ages contigue da 0 a 103",
        ages == list(range(0, 104)),
        f"len={len(ages)}",
    ):
        failures += 1

    print("\n4. Duplicati (chiave: sex + age + rate per viager)")
    seen = set()
    dups = 0
    for r in viager:
        key = (r["sex"], r["age"], r["interest_rate_pct"])
        if key in seen:
            dups += 1
        seen.add(key)
    if not line("0 duplicati viager", dups == 0, f"dups={dups}"):
        failures += 1

    seen_t = set()
    dups_t = 0
    for r in temporaire:
        key = (r["sex"], r["age"], r["interest_rate_pct"], r["target_age"])
        if key in seen_t:
            dups_t += 1
        seen_t.add(key)
    if not line("0 duplicati temporaire", dups_t == 0, f"dups={dups_t}"):
        failures += 1

    print("\n5. Null / negativi sul coefficient")
    nulls = sum(1 for r in viager if not r["coefficient"])
    negs = sum(1 for r in viager if Decimal(r["coefficient"]) < 0)
    if not line("0 null in viager.coefficient", nulls == 0, f"nulls={nulls}"):
        failures += 1
    if not line("0 negativi in viager.coefficient", negs == 0, f"negs={negs}"):
        failures += 1
    nulls_t = sum(1 for r in temporaire if not r["coefficient"])
    negs_t = sum(1 for r in temporaire if Decimal(r["coefficient"]) < 0)
    if not line("0 null in temporaire.coefficient", nulls_t == 0, f"nulls={nulls_t}"):
        failures += 1
    if not line("0 negativi in temporaire.coefficient", negs_t == 0, f"negs={negs_t}"):
        failures += 1

    print("\n6. Monotonicità viager: coefficient decresce con l'età (per sex,rate)")
    by_sr: dict[tuple, list[tuple]] = defaultdict(list)
    for r in viager:
        by_sr[(r["sex"], r["interest_rate_pct"])].append((int(r["age"]), Decimal(r["coefficient"])))
    for combo, items in by_sr.items():
        items.sort()
        prev = None
        violations = 0
        for _age, c in items:
            if prev is not None and c >= prev:
                violations += 1
            prev = c
        if not line(
            f"viager strict decreasing for {combo}",
            violations == 0,
            f"violations={violations}",
        ):
            failures += 1

    print("\n7. Monotonicità rate: viager(rate=-1.00) > viager(rate=0.00)")
    cap = {
        (r["sex"], int(r["age"]), r["interest_rate_pct"]): Decimal(r["coefficient"]) for r in viager
    }
    rate_violations = 0
    for sex in ("M", "F"):
        for age in range(0, 104):
            v_neg = cap.get((sex, age, "-1.00"))
            v_zero = cap.get((sex, age, "0.00"))
            if v_neg is None or v_zero is None:
                continue
            if v_neg <= v_zero:
                rate_violations += 1
    if not line(
        "rate=-1.00 > rate=0.00 in tutti i (sex, age)",
        rate_violations == 0,
        f"violations={rate_violations}",
    ):
        failures += 1

    print("\n8. Spot-check ufficiali (esempio PDF p.4)")
    for sex, age, rate, expected in SPOT_CHECKS_PDF_EXAMPLE:
        actual = cap.get((sex, age, rate))
        if not line(
            f"({sex}, {age}, {rate}%) == {expected}",
            actual == expected,
            f"got={actual}",
        ):
            failures += 1

    print("\n9. Monotonicità temporaire: per (sex,rate,age), coefficient cresce con target_age")
    by_srao: dict[tuple, list[tuple]] = defaultdict(list)
    for r in temporaire:
        by_srao[(r["sex"], r["interest_rate_pct"], int(r["age"]))].append(
            (int(r["target_age"]), Decimal(r["coefficient"]))
        )
    bucket_violations = 0
    bucket_total = 0
    for items in by_srao.values():
        items.sort()
        bucket_total += 1
        prev = None
        for _ta, c in items:
            if prev is not None and c <= prev:
                bucket_violations += 1
                break
            prev = c
    if not line(
        "temporaire strict increasing per target_age",
        bucket_violations == 0,
        f"violations={bucket_violations} / {bucket_total} buckets",
    ):
        failures += 1

    print("\n10. source_note presente e coerente")
    notes = {r["source_note"] for r in viager + temporaire + anticipated}
    if not line(
        "source_note unico per tutti i record",
        len(notes) == 1,
        f"distinct={len(notes)}",
    ):
        failures += 1
    note = next(iter(notes))
    if not line(
        "source_note contiene legal_review_required=true",
        "legal_review_required=true" in note,
    ):
        failures += 1
    if not line(
        "source_note contiene no_human_legal_approval=true",
        "no_human_legal_approval=true" in note,
    ):
        failures += 1
    if not line(
        "source_note contiene extraction=automated_pdfplumber",
        "extraction=automated_pdfplumber" in note,
    ):
        failures += 1

    print("\n11. Anticipated payment years — 2 tassi x 5 ages x 2 sex")
    by_anticipated: dict[tuple, int] = defaultdict(int)
    for r in anticipated:
        by_anticipated[(r["interest_rate_pct"], r["sex"])] += 1
    for rate in ("-1.00", "0.00"):
        for sex in ("M", "F"):
            if not line(
                f"anticipated ({sex}, {rate}) ages = 5",
                by_anticipated.get((rate, sex), 0) == 5,
                f"got={by_anticipated.get((rate, sex), 0)}",
            ):
                failures += 1

    print()
    print("=" * 70)
    if failures == 0:
        print(
            f"QA OK — {len(viager)} viager + {len(temporaire)} temporaire + "
            f"{len(anticipated)} anticipated rows. Spot-check ufficiale PASS."
        )
        print("STATO: candidate. Lo Studio deve ancora effettuare la review legale.")
        print("=" * 70)
        return 0
    print(f"QA FAILED — {failures} anomalie da indagare.")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
