"""
QA READ-ONLY del CSV manuale Mornet 2024 (fourchettes).

Iter: F-france-mornet-manual-fourchettes · iter1
Stato: read-only. Non importa nel DB. Non modifica i CSV.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/qa_france_mornet_manual_fourchettes.py [--csv path]

Default: legge
    legal_data/sources/france/mornet_2024/fr-mornet-2024-manual-fourchettes-template.csv

Lo script è progettato per girare quando il CSV viene compilato dallo
Studio. Funziona anche su un CSV vuoto (solo header): in tal caso
verifica solo che l'header sia conforme.

Validazioni:
1. Header esatto.
2. transcription_status in: pending, transcribed, human_checked,
   rejected, needs_clarification.
3. Per righe transcribed o human_checked:
   - amount_min, amount_max definiti (eccetto unità che permettono
     amount_min vuoto, es. "jusqu'à X" = open_lower);
   - amount_min <= amount_mid <= amount_max quando tutti definiti;
   - currency = EUR;
   - source_page non vuoto;
   - source_quote_short non vuoto (almeno 5 caratteri);
   - source_note contiene legal_review_required=true e
     no_human_legal_approval=true.
4. Niente valori negativi negli amount_*.
5. Righe pending: amount_* possono essere vuoti.

Exit code 0 = OK, 1 = anomalie. Le anomalie NON cancellano nulla.
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import sys
from decimal import Decimal, InvalidOperation

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_CSV = (
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "mornet_2024"
    / "fr-mornet-2024-manual-fourchettes-template.csv"
)

EXPECTED_HEADER = [
    "row_type",
    "head_of_loss_code",
    "head_of_loss_label_fr",
    "severity_code",
    "severity_label_fr",
    "victim_age_min",
    "victim_age_max",
    "amount_min",
    "amount_mid",
    "amount_max",
    "unit",
    "currency",
    "source_page",
    "source_quote_short",
    "transcription_status",
    "reviewer_notes",
    "source_note",
]

ALLOWED_STATUS = {
    "pending",
    "transcribed",
    "human_checked",
    "rejected",
    "needs_clarification",
}

REQUIRES_AMOUNT_VALIDATION = {"transcribed", "human_checked"}


def line(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")
    return ok


def parse_optional_decimal(s: str) -> Decimal | None:
    if s is None or s.strip() == "":
        return None
    try:
        return Decimal(s.strip())
    except InvalidOperation:
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", type=pathlib.Path, default=DEFAULT_CSV)
    args = parser.parse_args()

    csv_path = args.csv
    print("=" * 70)
    print("QA — Mornet 2024 manual fourchettes")
    print(f"CSV: {csv_path}")
    print("=" * 70)

    if not csv_path.exists():
        print(f"[FATAL] CSV non trovato: {csv_path}")
        return 2

    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)

    failures = 0

    # 1. Header
    print("\n1. Header")
    if not rows:
        if not line("CSV non vuoto (almeno header)", False, "rows=0"):
            failures += 1
            print("\nQA FAILED — CSV vuoto.")
            return 1
    header = rows[0]
    if not line(
        "header esatto",
        header == EXPECTED_HEADER,
        f"got={header!r}",
    ):
        failures += 1

    data_rows = [dict(zip(header, r, strict=False)) for r in rows[1:] if any(c.strip() for c in r)]
    print(f"  [INFO] data rows = {len(data_rows)}")

    if not data_rows:
        print("\n[INFO] CSV scaffold (solo header). Validazione strutturale OK.")
        print("=" * 70)
        if failures == 0:
            print("QA OK — header conforme, nessun dato da validare.")
            print("=" * 70)
            return 0
        print(f"QA FAILED — {failures} anomalie strutturali.")
        return 1

    # 2. transcription_status valori
    print("\n2. transcription_status in valori ammessi")
    bad_status = []
    for i, r in enumerate(data_rows, start=2):
        s = r.get("transcription_status", "").strip()
        if s not in ALLOWED_STATUS:
            bad_status.append((i, s))
    if not line(
        f"tutti i transcription_status in {sorted(ALLOWED_STATUS)}",
        not bad_status,
        f"violations={bad_status[:3]}{'...' if len(bad_status) > 3 else ''}",
    ):
        failures += 1

    # 3. Validazione monetaria per righe transcribed/human_checked
    print("\n3. Righe transcribed/human_checked — validazione completa")
    bad_amount_present = []
    bad_min_le_mid_le_max = []
    bad_currency = []
    bad_source_page = []
    bad_quote = []
    bad_note_required_tokens = []
    bad_negative = []
    for i, r in enumerate(data_rows, start=2):
        status = r.get("transcription_status", "").strip()
        amin = parse_optional_decimal(r.get("amount_min", ""))
        amid = parse_optional_decimal(r.get("amount_mid", ""))
        amax = parse_optional_decimal(r.get("amount_max", ""))

        if status in REQUIRES_AMOUNT_VALIDATION:
            # Almeno amount_max deve essere definito (amount_min può
            # essere vuoto per casi 'jusqu'à X').
            if amax is None:
                bad_amount_present.append((i, "amount_max vuoto"))
            if r.get("currency", "").strip() != "EUR" and (
                amin is not None or amax is not None or amid is not None
            ):
                bad_currency.append((i, r.get("currency")))
            if not r.get("source_page", "").strip():
                bad_source_page.append((i, ""))
            quote = r.get("source_quote_short", "").strip()
            if len(quote) < 5:
                bad_quote.append((i, quote))
            note = r.get("source_note", "")
            for tok in (
                "legal_review_required=true",
                "no_human_legal_approval=true",
            ):
                if tok not in note:
                    bad_note_required_tokens.append((i, tok))

            # Coerenza min/mid/max quando tutti definiti
            if amin is not None and amid is not None and amax is not None:
                if not (amin <= amid <= amax):
                    bad_min_le_mid_le_max.append((i, f"min={amin} mid={amid} max={amax}"))
            elif amin is not None and amax is not None and amin > amax:
                bad_min_le_mid_le_max.append((i, f"min={amin} > max={amax}"))

        for k, v in (("amount_min", amin), ("amount_mid", amid), ("amount_max", amax)):
            if v is not None and v < 0:
                bad_negative.append((i, k, v))

    if not line(
        "transcribed/human_checked hanno almeno amount_max definito",
        not bad_amount_present,
        f"violations={len(bad_amount_present)}",
    ):
        failures += 1
    if not line(
        "min <= mid <= max coerenti",
        not bad_min_le_mid_le_max,
        f"violations={len(bad_min_le_mid_le_max)}",
    ):
        failures += 1
    if not line(
        "currency=EUR quando ci sono importi",
        not bad_currency,
        f"violations={len(bad_currency)}",
    ):
        failures += 1
    if not line(
        "source_page valorizzato per transcribed/human_checked",
        not bad_source_page,
        f"violations={len(bad_source_page)}",
    ):
        failures += 1
    if not line(
        "source_quote_short presente (>=5 char)",
        not bad_quote,
        f"violations={len(bad_quote)}",
    ):
        failures += 1
    if not line(
        "source_note contiene legal_review_required=true e no_human_legal_approval=true",
        not bad_note_required_tokens,
        f"violations={len(bad_note_required_tokens)}",
    ):
        failures += 1

    # 4. Negativi
    print("\n4. Niente valori negativi")
    if not line(
        "0 valori negativi su amount_*",
        not bad_negative,
        f"violations={len(bad_negative)}",
    ):
        failures += 1

    # 5. Righe pending — non bloccano
    pending_count = sum(
        1 for r in data_rows if r.get("transcription_status", "").strip() == "pending"
    )
    transcribed_count = sum(
        1
        for r in data_rows
        if r.get("transcription_status", "").strip() in REQUIRES_AMOUNT_VALIDATION
    )
    rejected_count = sum(
        1 for r in data_rows if r.get("transcription_status", "").strip() == "rejected"
    )
    print(
        f"\n[INFO] pending={pending_count} | transcribed/human_checked={transcribed_count} "
        f"| rejected={rejected_count} | total={len(data_rows)}"
    )

    print()
    print("=" * 70)
    if failures == 0:
        print(
            f"QA OK — {len(data_rows)} righe validate "
            f"({transcribed_count} transcribed/human_checked)."
        )
        print("STATO: candidate. Lo Studio deve completare la review legale.")
        print("=" * 70)
        return 0
    print(f"QA FAILED — {failures} anomalie da indagare.")
    print("=" * 70)
    return 1


if __name__ == "__main__":
    sys.exit(main())
