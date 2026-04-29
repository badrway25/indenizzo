"""
QA READ-ONLY dei 4 CSV candidate generati da extract_belgium_ti_2020.py.

Iter: F-belgium-extraction-ti-2020 · iter1
Stato: read-only. Non importa nel DB. Non modifica i CSV.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/qa_belgium_ti_2020.py

Verifica:
- conteggi attesi vs trovati per i 4 CSV;
- duplicati (per chiavi naturali);
- null sui campi monetari;
- negativi;
- min <= mid <= max;
- monotonicità:
  * SE: amount cresce con severity (per età), decresce con età (per severity);
  * Esthétique forfait: annual_amount decresce con età;
- spot-check dai sample del PDF;
- copertura relation_code décès;
- copertura vehicle_type_code véhicule;
- source_note coerenza (legal_review_required=true,
  no_human_legal_approval=true, source_is_historical_2020=true).

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
CSV_DIR = ROOT / "legal_data" / "sources" / "belgium" / "tableau_indicatif_2020"

SE_CSV = CSV_DIR / "be-ti-2020-souffrances-endurees.csv"
ESTH_CSV = CSV_DIR / "be-ti-2020-prejudice-esthetique.csv"
DECES_CSV = CSV_DIR / "be-ti-2020-prejudice-deces-affection.csv"
VEHIC_CSV = CSV_DIR / "be-ti-2020-vehicule-remplacement.csv"

EXPECTED_SE = 63  # 9 ages × 7 severities
EXPECTED_ESTH = 71  # 1 (jusque 15) + 40 (16-55) + 29 (56-84) + 1 (85+)
EXPECTED_DECES = 13
EXPECTED_VEHIC = 19  # 12 simple + 2 remorque sub + 5 autobus sub

EXPECTED_SE_AGE_BANDS = [
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
EXPECTED_SEVERITIES = ["1_7", "2_7", "3_7", "4_7", "5_7", "6_7", "7_7"]

EXPECTED_DECES_CODES = {
    "conjoint_perte_conjoint",
    "parent_cohabitant_perte_enfant_cohabitant",
    "parent_cohabitant_perte_enfant_cohabitant_orphelin",
    "parent_non_cohabitant_perte_enfant_non_cohabitant",
    "enfant_cohabitant_perte_parent",
    "enfant_autonome_perte_parent",
    "fausse_couche_perte_parent",
    "frere_soeur_cohabitant_perte_frere_soeur_cohabitant",
    "frere_soeur_non_cohabitant_perte_frere_soeur_non_cohabitant",
    "grands_parents_cohabitants_perte_petits_enfants_cohabitants",
    "grands_parents_non_cohabitants_perte_petits_enfants_non_cohabitants",
    "petits_enfants_cohabitants_perte_grands_parents_cohabitants",
    "petits_enfants_non_cohabitants_perte_grands_parents_non_cohabitants",
}

EXPECTED_VEHIC_CODES = {
    "fr_bicyclette",
    "fr_motorisees_2_3_roues",
    "fr_remorque_voiture_moins_750kg",
    "fr_remorque_voiture_plus_750kg",
    "fr_voiture_perso_pro",
    "fr_mobilhome",
    "fr_taxi_grandes_entreprises",
    "fr_taxi_independant",
    "fr_voiture_location",
    "fr_camionnettes_jusqu_3_5t",
    "fr_proprietaire_un_camion",
    "fr_vehicules_lourds_speciaux",
    "fr_ambulance",
    "fr_remorque_camping",
    "fr_autobus_lt_50",
    "fr_autobus_50_60",
    "fr_autobus_60_70",
    "fr_autobus_70_80",
    "fr_autobus_80_plus",
}

# Spot-check dai sample del PDF
SE_SPOTS = [
    # (age_min, age_max, severity, expected)
    (0, 10, "1_7", Decimal("540.00")),
    (0, 10, "7_7", Decimal("30000.00")),
    (81, 120, "1_7", Decimal("115.00")),
    (81, 120, "7_7", Decimal("6400.00")),
]
ESTH_SPOTS = [
    # (age_min, age_max, expected_annual)
    (0, 15, Decimal("1220.00")),
    (16, 16, Decimal("1200.00")),
    (85, 120, Decimal("165.00")),
]
DECES_SPOTS = [
    ("conjoint_perte_conjoint", Decimal("15000.00")),
    ("parent_cohabitant_perte_enfant_cohabitant_orphelin", Decimal("24000.00")),
    ("petits_enfants_non_cohabitants_perte_grands_parents_non_cohabitants", Decimal("1500.00")),
]
VEHIC_SPOTS = [
    ("fr_bicyclette", Decimal("10.00")),
    ("fr_voiture_perso_pro", Decimal("20.00")),
    ("fr_vehicules_lourds_speciaux", Decimal("150.00")),
    ("fr_autobus_80_plus", Decimal("180.00")),
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


def main() -> int:  # noqa: C901, PLR0915
    print("=" * 70)
    print("QA — be-tableau-indicatif-2020 (4 CSVs)")
    print("(read-only, nessuna modifica ai CSV)")
    print("=" * 70)
    failures = 0

    se = load_csv(SE_CSV)
    esth = load_csv(ESTH_CSV)
    deces = load_csv(DECES_CSV)
    vehic = load_csv(VEHIC_CSV)

    # 1. Conteggi
    print("\n1. Conteggi totali")
    for name, rows, expected in (
        ("Souffrances endurées", se, EXPECTED_SE),
        ("Esthétique (forfait per età)", esth, EXPECTED_ESTH),
        ("Décès / affection", deces, EXPECTED_DECES),
        ("Véhicule remplacement", vehic, EXPECTED_VEHIC),
    ):
        if not line(f"{name} == {expected}", len(rows) == expected, f"got={len(rows)}"):
            failures += 1

    # 2. SE — copertura range (9 ages × 7 severities)
    print("\n2. SE — copertura (ages × severities)")
    se_pairs = {
        (int(r["victim_age_min"]), int(r["victim_age_max"]), r["severity_code"]) for r in se
    }
    expected_se_pairs = {
        (a_min, a_max, sev)
        for (a_min, a_max) in EXPECTED_SE_AGE_BANDS
        for sev in EXPECTED_SEVERITIES
    }
    missing = expected_se_pairs - se_pairs
    extra = se_pairs - expected_se_pairs
    if not line("nessun (age, severity) mancante", not missing, f"missing={len(missing)}"):
        failures += 1
    if not line("nessun (age, severity) extra", not extra, f"extra={len(extra)}"):
        failures += 1

    # 3. Esthétique — copertura ages
    print("\n3. Esthétique — copertura ages")
    esth_pairs = sorted({(int(r["victim_age_min"]), int(r["victim_age_max"])) for r in esth})
    if not line("min age == 0", esth_pairs[0][0] == 0, f"min={esth_pairs[0]}"):
        failures += 1
    if not line(
        "max age band == (85, 120)",
        esth_pairs[-1] == (85, 120),
        f"max={esth_pairs[-1]}",
    ):
        failures += 1

    # 4. Duplicati
    print("\n4. Duplicati")
    se_seen: set = set()
    se_dups = 0
    for r in se:
        k = (
            r["victim_age_min"],
            r["victim_age_max"],
            r["severity_code"],
        )
        if k in se_seen:
            se_dups += 1
        se_seen.add(k)
    if not line("0 duplicati SE", se_dups == 0, f"dups={se_dups}"):
        failures += 1
    esth_seen: set = set()
    esth_dups = 0
    for r in esth:
        k = (r["victim_age_min"], r["victim_age_max"])
        if k in esth_seen:
            esth_dups += 1
        esth_seen.add(k)
    if not line("0 duplicati Esthétique", esth_dups == 0, f"dups={esth_dups}"):
        failures += 1
    deces_codes = [r["relation_code"] for r in deces]
    if not line("0 duplicati Décès", len(deces_codes) == len(set(deces_codes)), ""):
        failures += 1
    vehic_codes = [r["vehicle_type_code"] for r in vehic]
    if not line("0 duplicati Véhicule", len(vehic_codes) == len(set(vehic_codes)), ""):
        failures += 1

    # 5. Null / negativi sui campi monetari
    print("\n5. Null / negativi")
    for name, rows, fields in (
        ("SE", se, ["amount_min", "amount_mid", "amount_max"]),
        ("Esthétique", esth, ["annual_amount"]),
        ("Décès", deces, ["amount_min", "amount_mid", "amount_max"]),
        (
            "Véhicule",
            vehic,
            ["daily_amount_min", "daily_amount_mid", "daily_amount_max"],
        ),
    ):
        nulls = sum(1 for r in rows for f in fields if not r[f])
        if not line(f"{name} 0 null", nulls == 0, f"nulls={nulls}"):
            failures += 1
        negs = sum(1 for r in rows for f in fields if r[f] and Decimal(r[f]) < 0)
        if not line(f"{name} 0 negativi", negs == 0, f"negs={negs}"):
            failures += 1

    # 6. min <= mid <= max
    print("\n6. min <= mid <= max")
    for name, rows, mn, md, mx in (
        ("SE", se, "amount_min", "amount_mid", "amount_max"),
        ("Décès", deces, "amount_min", "amount_mid", "amount_max"),
        ("Véhicule", vehic, "daily_amount_min", "daily_amount_mid", "daily_amount_max"),
    ):
        bad = sum(1 for r in rows if not (Decimal(r[mn]) <= Decimal(r[md]) <= Decimal(r[mx])))
        if not line(f"{name} min<=mid<=max", bad == 0, f"violations={bad}"):
            failures += 1

    # 7. SE — monotonicità severity (per età, amount cresce con severity)
    print("\n7. SE — monotonicità severity (cresce)")
    by_age: dict[tuple, list[tuple]] = defaultdict(list)
    for r in se:
        by_age[(int(r["victim_age_min"]), int(r["victim_age_max"]))].append(
            (r["severity_code"], Decimal(r["amount_mid"]))
        )
    sev_violations = 0
    sev_order = {s: i for i, s in enumerate(EXPECTED_SEVERITIES)}
    for items in by_age.values():
        items.sort(key=lambda kv: sev_order[kv[0]])
        prev = None
        for _sev, v in items:
            if prev is not None and v <= prev:
                sev_violations += 1
                break
            prev = v
    if not line(
        "SE strict increasing in severity per ogni age_band",
        sev_violations == 0,
        f"violations={sev_violations} / {len(by_age)} buckets",
    ):
        failures += 1

    # 8. SE — monotonicità età (per severity, amount decresce con età)
    print("\n8. SE — monotonicità età (decresce)")
    by_sev: dict[str, list[tuple]] = defaultdict(list)
    for r in se:
        by_sev[r["severity_code"]].append((int(r["victim_age_min"]), Decimal(r["amount_mid"])))
    age_violations = 0
    for items in by_sev.values():
        items.sort()
        prev = None
        for _age, v in items:
            if prev is not None and v >= prev:
                age_violations += 1
                break
            prev = v
    if not line(
        "SE strict decreasing in age per ogni severity",
        age_violations == 0,
        f"violations={age_violations} / {len(by_sev)} buckets",
    ):
        failures += 1

    # 9. Esthétique — monotonicità (decresce con età)
    print("\n9. Esthétique — annual_amount decresce con età")
    items = sorted(
        ((int(r["victim_age_min"]), Decimal(r["annual_amount"])) for r in esth),
        key=lambda kv: kv[0],
    )
    esth_violations = 0
    prev = None
    for _age, v in items:
        if prev is not None and v >= prev:
            esth_violations += 1
        prev = v
    if not line(
        "Esthétique strict decreasing in age",
        esth_violations == 0,
        f"violations={esth_violations}",
    ):
        failures += 1

    # 10. Spot-checks
    print("\n10. Spot-check ufficiali")
    se_map = {
        (int(r["victim_age_min"]), int(r["victim_age_max"]), r["severity_code"]): Decimal(
            r["amount_mid"]
        )
        for r in se
    }
    for a_min, a_max, sev, expected in SE_SPOTS:
        actual = se_map.get((a_min, a_max, sev))
        if not line(
            f"SE ({a_min}-{a_max}, {sev}) == {expected}",
            actual == expected,
            f"got={actual}",
        ):
            failures += 1

    esth_map = {
        (int(r["victim_age_min"]), int(r["victim_age_max"])): Decimal(r["annual_amount"])
        for r in esth
    }
    for a_min, a_max, expected in ESTH_SPOTS:
        actual = esth_map.get((a_min, a_max))
        if not line(
            f"Esth ({a_min}-{a_max}) == {expected}",
            actual == expected,
            f"got={actual}",
        ):
            failures += 1

    deces_map = {r["relation_code"]: Decimal(r["amount_mid"]) for r in deces}
    for code, expected in DECES_SPOTS:
        actual = deces_map.get(code)
        if not line(
            f"Décès {code} == {expected}",
            actual == expected,
            f"got={actual}",
        ):
            failures += 1

    vehic_map = {r["vehicle_type_code"]: Decimal(r["daily_amount_mid"]) for r in vehic}
    for code, expected in VEHIC_SPOTS:
        actual = vehic_map.get(code)
        if not line(
            f"Véhicule {code} == {expected}",
            actual == expected,
            f"got={actual}",
        ):
            failures += 1

    # 11. Décès relation_codes — copertura
    print("\n11. Décès — copertura relation_code")
    found = set(deces_codes)
    missing_d = EXPECTED_DECES_CODES - found
    extra_d = found - EXPECTED_DECES_CODES
    if not line("nessun relation_code mancante", not missing_d, f"missing={sorted(missing_d)}"):
        failures += 1
    if not line("nessun relation_code extra", not extra_d, f"extra={sorted(extra_d)}"):
        failures += 1

    # 12. Véhicule vehicle_type_codes — copertura
    print("\n12. Véhicule — copertura vehicle_type_code")
    found_v = set(vehic_codes)
    missing_v = EXPECTED_VEHIC_CODES - found_v
    extra_v = found_v - EXPECTED_VEHIC_CODES
    if not line("nessun vehicle_type_code mancante", not missing_v, f"missing={sorted(missing_v)}"):
        failures += 1
    if not line("nessun vehicle_type_code extra", not extra_v, f"extra={sorted(extra_v)}"):
        failures += 1

    # 13. source_note coerenza
    print("\n13. source_note coerenza")
    all_notes = {r["source_note"] for r in se + esth + deces + vehic}
    if not line(
        "source_note unico per tutti i record",
        len(all_notes) == 1,
        f"distinct={len(all_notes)}",
    ):
        failures += 1
    note = next(iter(all_notes))
    for tok in (
        "extraction=automated_pdfplumber",
        "legal_review_required=true",
        "no_human_legal_approval=true",
        "pdf_sha256=1b073f5c41c8414018e262143d7e67c496bbeeb832e623f406333b3ece0b8222",
        "pdf_slug=be-tableau-indicatif-2020",
        "iter=1",
        "source_is_historical_2020=true",
    ):
        if not line(f"source_note contiene '{tok}'", tok in note):
            failures += 1

    # 14. Currency=EUR
    print("\n14. Currency = EUR")
    bad_curr = sum(1 for r in se + esth + deces + vehic if r.get("currency") != "EUR")
    if not line("tutti i record hanno currency=EUR", bad_curr == 0, f"violations={bad_curr}"):
        failures += 1

    print()
    print("=" * 70)
    if failures == 0:
        print(
            f"QA OK — {len(se)} SE + {len(esth)} esthétique + {len(deces)} "
            f"décès + {len(vehic)} véhicule = {len(se)+len(esth)+len(deces)+len(vehic)} righe."
        )
        print("STATO: candidate. Lo Studio deve effettuare la review legale.")
        print("=" * 70)
        return 0
    print(f"QA FAILED — {failures} anomalie da indagare.")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
