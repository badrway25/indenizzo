"""
QA READ-ONLY dei CSV candidate generati da extract_france_mornet_2024.py.

Iter: F-france-mornet-extraction-tables · iter1
Stato: read-only. Non importa nel DB. Non modifica i CSV.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/qa_france_mornet_2024.py

Verifica:
- conteggi attesi vs trovati;
- range coverage (DFP: 20 disability bands x 9 age bands = 180);
- duplicati;
- null sui campi monetari;
- negativi;
- min <= mid <= max in tutte le righe;
- monotonicità DFP: per disability_band fissato, amount decresce con
  l'età (più anziano = punto più basso); per age_band fissato, amount
  cresce con disability_band (più grave = punto più alto);
- spot-check ufficiale: l'esempio del PDF a p.71 dice
  "Un homme de 25 ans atteint d'un déficit fonctionnel de 32% pourra
  être indemnisé à hauteur de 3.740 € le point" -> riga (age 21-30,
  disability 31-35) = 3740 EUR per punto;
- copertura affection: 11 relation_code distinti;
- source_note presente e coerente.

Exit code 0 = OK, 1 = anomalie.
"""

from __future__ import annotations

import csv
import pathlib
import sys
from collections import defaultdict
from decimal import Decimal

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]
CSV_DIR = ROOT / "legal_data" / "sources" / "france" / "mornet_2024"
DFP_CSV = CSV_DIR / "fr-mornet-2024-dfp-per-age-disability.csv"
AFFECTION_CSV = CSV_DIR / "fr-mornet-2024-prejudice-affection-per-relation.csv"

EXPECTED_DFP_ROWS = 180
EXPECTED_AFFECTION_ROWS = 11

EXPECTED_AFFECTION_CODES = {
    "conjoint_perte_conjoint",
    "enfant_mineur_perte_parent",
    "enfant_majeur_au_foyer_perte_parent",
    "enfant_majeur_hors_foyer_perte_parent",
    "parent_perte_enfant",
    "freres_soeurs_meme_foyer",
    "freres_soeurs_hors_foyer",
    "grand_parent_perte_petit_enfant_freq",
    "grand_parent_perte_petit_enfant_peu_freq",
    "petit_enfant_perte_grand_parent_freq",
    "petit_enfant_perte_grand_parent_peu_freq",
}

EXPECTED_AGE_BANDS = [
    (0, 10),
    (11, 20),
    (21, 30),
    (31, 40),
    (41, 50),
    (51, 60),
    (61, 70),
    (71, 80),
    (81, 120),
]

EXPECTED_DISABILITY_BANDS = [
    (1, 5),
    (6, 10),
    (11, 15),
    (16, 20),
    (21, 25),
    (26, 30),
    (31, 35),
    (36, 40),
    (41, 45),
    (46, 50),
    (51, 55),
    (56, 60),
    (61, 65),
    (66, 70),
    (71, 75),
    (76, 80),
    (81, 85),
    (86, 90),
    (91, 95),
    (96, 100),
]


def line(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")
    return ok


def load_csv(p: pathlib.Path) -> list[dict]:
    if not p.exists():
        print(f"[FATAL] CSV non trovato: {p}")
        sys.exit(2)
    with p.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main() -> int:
    print("=" * 70)
    print("QA — fr-referentiel-mornet-2024 (DFP p.71 + affection p.94)")
    print("(read-only, nessuna modifica ai CSV)")
    print("=" * 70)

    failures = 0
    dfp = load_csv(DFP_CSV)
    aff = load_csv(AFFECTION_CSV)

    # 1. Conteggi
    print("\n1. Conteggi totali")
    if not line(
        f"DFP rows == {EXPECTED_DFP_ROWS}",
        len(dfp) == EXPECTED_DFP_ROWS,
        f"got={len(dfp)}",
    ):
        failures += 1
    if not line(
        f"Affection rows == {EXPECTED_AFFECTION_ROWS}",
        len(aff) == EXPECTED_AFFECTION_ROWS,
        f"got={len(aff)}",
    ):
        failures += 1

    # 2. DFP — range coverage
    print("\n2. DFP — copertura range (20 disability x 9 age)")
    pairs = {
        (
            int(r["victim_age_min"]),
            int(r["victim_age_max"]),
            int(r["disability_min"]),
            int(r["disability_max"]),
        )
        for r in dfp
    }
    expected_pairs = {
        (a_min, a_max, d_min, d_max)
        for (a_min, a_max) in EXPECTED_AGE_BANDS
        for (d_min, d_max) in EXPECTED_DISABILITY_BANDS
    }
    missing = expected_pairs - pairs
    extra = pairs - expected_pairs
    if not line("nessun (age, disability) mancante", not missing, f"missing={len(missing)}"):
        failures += 1
    if not line("nessun (age, disability) extra", not extra, f"extra={len(extra)}"):
        failures += 1

    # 3. Duplicati
    print("\n3. Duplicati")
    seen = set()
    dups = 0
    for r in dfp:
        k = (
            r["victim_age_min"],
            r["victim_age_max"],
            r["disability_min"],
            r["disability_max"],
        )
        if k in seen:
            dups += 1
        seen.add(k)
    if not line("0 duplicati DFP su (age, disability)", dups == 0, f"dups={dups}"):
        failures += 1
    aff_codes = [r["relation_code"] for r in aff]
    aff_dups = len(aff_codes) - len(set(aff_codes))
    if not line(
        "0 duplicati Affection su relation_code",
        aff_dups == 0,
        f"dups={aff_dups}",
    ):
        failures += 1

    # 4. Null / negativi
    print("\n4. Null / negativi sui campi monetari")
    for csv_name, rows, fields in (
        ("DFP", dfp, ["amount_min", "amount_mid", "amount_max"]),
        ("Affection", aff, ["amount_min", "amount_mid", "amount_max"]),
    ):
        nulls = sum(1 for r in rows for f in fields if not r[f])
        if not line(f"{csv_name} 0 null", nulls == 0, f"nulls={nulls}"):
            failures += 1
        negs = sum(1 for r in rows for f in fields if r[f] and Decimal(r[f]) < 0)
        if not line(f"{csv_name} 0 negativi", negs == 0, f"negs={negs}"):
            failures += 1

    # 5. min <= mid <= max
    print("\n5. min <= mid <= max")
    for csv_name, rows in (("DFP", dfp), ("Affection", aff)):
        bad = 0
        for r in rows:
            amin = Decimal(r["amount_min"])
            amid = Decimal(r["amount_mid"])
            amax = Decimal(r["amount_max"])
            if not (amin <= amid <= amax):
                bad += 1
        if not line(f"{csv_name} min<=mid<=max", bad == 0, f"violations={bad}"):
            failures += 1

    # 6. DFP monotonicità per età (per disability_band fissato, amount decresce con l'età)
    print("\n6. DFP monotonicità per età (decresce)")
    by_dis: dict[tuple, list[tuple]] = defaultdict(list)
    for r in dfp:
        by_dis[(int(r["disability_min"]), int(r["disability_max"]))].append(
            (int(r["victim_age_min"]), Decimal(r["amount_mid"]))
        )
    age_violations = 0
    for items in by_dis.values():
        items.sort()
        prev = None
        for _age, v in items:
            if prev is not None and v >= prev:
                age_violations += 1
                break
            prev = v
    if not line(
        "DFP strict decreasing in age per ogni disability_band",
        age_violations == 0,
        f"violations={age_violations} / {len(by_dis)} buckets",
    ):
        failures += 1

    # 7. DFP monotonicità per disability (per age_band fissato, amount cresce con %DFP)
    print("\n7. DFP monotonicità per disability (cresce)")
    by_age: dict[tuple, list[tuple]] = defaultdict(list)
    for r in dfp:
        by_age[(int(r["victim_age_min"]), int(r["victim_age_max"]))].append(
            (int(r["disability_min"]), Decimal(r["amount_mid"]))
        )
    dis_violations = 0
    for items in by_age.values():
        items.sort()
        prev = None
        for _dmin, v in items:
            if prev is not None and v <= prev:
                dis_violations += 1
                break
            prev = v
    if not line(
        "DFP strict increasing in disability per ogni age_band",
        dis_violations == 0,
        f"violations={dis_violations} / {len(by_age)} buckets",
    ):
        failures += 1

    # 8. Spot-check ufficiale (esempio PDF p.71)
    print("\n8. Spot-check ufficiale (p.71 EXEMPLE)")
    spot = next(
        (
            r
            for r in dfp
            if r["victim_age_min"] == "21"
            and r["victim_age_max"] == "30"
            and r["disability_min"] == "31"
            and r["disability_max"] == "35"
        ),
        None,
    )
    if not line(
        "(age 21-30, dis 31-35) trovato",
        spot is not None,
    ):
        failures += 1
    elif not line(
        "(age 21-30, dis 31-35) amount_mid == 3740",
        spot is not None and Decimal(spot["amount_mid"]) == Decimal("3740"),
        f"got={spot['amount_mid']}",
    ):
        failures += 1

    # 9. Affection — copertura relation_code attesi
    print("\n9. Affection — copertura relation_code")
    found_codes = set(aff_codes)
    missing_codes = EXPECTED_AFFECTION_CODES - found_codes
    extra_codes = found_codes - EXPECTED_AFFECTION_CODES
    if not line(
        f"tutti gli {len(EXPECTED_AFFECTION_CODES)} relation_code attesi presenti",
        not missing_codes,
        f"missing={sorted(missing_codes)}",
    ):
        failures += 1
    if not line(
        "nessun relation_code extra",
        not extra_codes,
        f"extra={sorted(extra_codes)}",
    ):
        failures += 1

    # 10. source_note coerenza
    print("\n10. source_note coerenza")
    notes = {r["source_note"] for r in dfp + aff}
    if not line("source_note unico", len(notes) == 1, f"distinct={len(notes)}"):
        failures += 1
    note = next(iter(notes))
    for tok in (
        "extraction=automated_pdfplumber",
        "legal_review_required=true",
        "no_human_legal_approval=true",
        "pdf_sha256=2dd2e760bc057b38275a7a6de24a62c009f6d04dd79573c00ee052f4f6df72b4",
        "pdf_slug=fr-referentiel-mornet-2024",
        "iter=1",
    ):
        if not line(f"source_note contiene '{tok}'", tok in note):
            failures += 1

    # 11. Affection — sanity range plausibility (importi ragionevoli)
    print("\n11. Affection — plausibilità importi (>= 1.000 €, <= 50.000 €)")
    bad = 0
    for r in aff:
        amin = Decimal(r["amount_min"])
        amax = Decimal(r["amount_max"])
        if amin < Decimal("1000") or amax > Decimal("50000"):
            bad += 1
    if not line(
        "tutti gli amount in [1.000, 50.000] EUR",
        bad == 0,
        f"out_of_range={bad}",
    ):
        failures += 1

    print()
    print("=" * 70)
    if failures == 0:
        print(
            f"QA OK — {len(dfp)} DFP rows + {len(aff)} affection rows. "
            "Spot-check ufficiale PASS."
        )
        print("STATO: candidate. Lo Studio deve effettuare la review legale.")
        print("=" * 70)
        return 0
    print(f"QA FAILED — {failures} anomalie.")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
