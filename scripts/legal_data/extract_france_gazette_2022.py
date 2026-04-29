"""
Estrazione READ-ONLY dei coefficient di capitalisation dal PDF
'Barème de capitalisation 2022' della Gazette du Palais.

Iter: F-france-extraction-gazette-capitalisation · iter1
Stato: candidate — NON importa nel DB. NON crea LegalReview /
CompensationDataset / CalculationFormula. Output: solo CSV
in legal_data/sources/france/gazette_2022/ (gitignored come da
.gitignore: legal_data/sources/**/*.csv).

Uso:
    .venv/Scripts/python.exe scripts/legal_data/extract_france_gazette_2022.py

Output:
    legal_data/sources/france/gazette_2022/
        fr-gazette-2022-capitalisation-viagere.csv
        fr-gazette-2022-capitalisation-temporaire.csv
        fr-gazette-2022-anticipated-payment-years.csv
        extraction_summary.json   (contatori per QA)

Dipendenze: pdfplumber (già installato).

Convenzioni numeriche del PDF:
- Tabelle di capitalisation (p.5-20): il PUNTO è separatore decimale
  ("66.602" -> Decimal("66.602")). VIETATO interpretare come migliaia.
- Tabella anticipated payment years (p.4): la VIRGOLA è separatore
  decimale ("59,6" -> Decimal("59.6")).
- Spazi non-breaking interni vengono rimossi prima del parsing.

Nessuna modifica a calculator/wizard/Italia/TUN. Nessun import DB.
"""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import sys
from decimal import Decimal
from typing import Any

import pdfplumber

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]
PDF_PATH = (
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "downloaded"
    / "fr-bareme-capitalisation-gazette-palais-2022.pdf"
)
OUTPUT_DIR = ROOT / "legal_data" / "sources" / "france" / "gazette_2022"

EXPECTED_PDF_SHA256 = "686a557b23fa9e76fcd30795e61fda1cc2396d230290b93398874203ebbef3ee"

CAPITALISATION_PAGES = list(range(5, 21))  # 16 capitalisation tables

SOURCE_NOTE_TEMPLATE = (
    "extraction=automated_pdfplumber;"
    "legal_review_required=true;"
    "no_human_legal_approval=true;"
    "pdf_sha256={pdf_sha256};"
    "pdf_slug=fr-bareme-capitalisation-gazette-palais-2022;"
    "extractor_script=scripts/legal_data/extract_france_gazette_2022.py;"
    "iter=F-france-extraction-gazette-capitalisation"
)


def normalize_ws(s: str | None) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def parse_capital_decimal(raw: str | None) -> Decimal | None:
    """Parser per i coefficient di capitalisation (PUNTO = decimale)."""
    if raw is None:
        return None
    s = re.sub(r"[\s ]", "", raw)
    if s == "":
        return None
    if not re.fullmatch(r"\d+\.\d+|\d+", s):
        return None
    return Decimal(s)


def parse_year_decimal(raw: str | None) -> Decimal | None:
    """Parser per gli anni di prestazione (VIRGOLA = decimale)."""
    if raw is None:
        return None
    s = re.sub(r"[\s ]", "", raw).replace(",", ".")
    if s == "":
        return None
    if not re.fullmatch(r"\d+\.\d+|\d+", s):
        return None
    return Decimal(s)


def fmt_rate(rate: Decimal) -> str:
    """Format rate as fixed 2-decimal string for CSV consistency."""
    return f"{rate.quantize(Decimal('0.00')):.2f}"


def parse_target_age_label(label: str) -> int | None:
    """'69 ans' -> 69 ; 'viagère' / 'via- gère' -> None ."""
    label_norm = normalize_ws(label).lower()
    if not label_norm:
        return None
    if "viag" in label_norm.replace("- ", "").replace(" ", ""):
        return None
    m = re.match(r"(\d+)\s*ans?", label_norm)
    return int(m.group(1)) if m else None


SEX_MAP = {"masculin": "M", "féminin": "F", "feminin": "F"}


def detect_metadata_from_table_meta_row(meta_row: list[str | None]) -> dict[str, Any]:
    """Estrae sex/mortality_table/rate dalla testata (riga 0)."""
    blob = " | ".join(c or "" for c in meta_row)
    sex = None
    if re.search(r"\(Sexe\s+masculin\)", blob, flags=re.IGNORECASE):
        sex = "M"
    elif re.search(r"\(Sexe\s+féminin\)", blob, flags=re.IGNORECASE):
        sex = "F"
    mortality = None
    m = re.search(r"INSEE([HF])\s+\d{4}-\d{4}", blob)
    if m:
        mortality = f"INSEE{m.group(1)}-2017-2019"
    rate_match = re.search(
        r"Taux\s+d['’]int[ée]r[êe]t\s*=\s*(-?\d+(?:[.,]\d+)?)\s*%",
        blob,
        flags=re.IGNORECASE,
    )
    rate = None
    if rate_match:
        rate = Decimal(rate_match.group(1).replace(",", "."))
    return {
        "sex": sex,
        "mortality_table": mortality,
        "interest_rate_pct": rate,
    }


def extract_capitalisation_page(
    page, page_number: int, source_note: str
) -> tuple[list[dict], list[dict], dict]:
    """Estrae viagere + temporaire da una pagina capitalisation.

    Ritorna (viager_rows, temporaire_rows, page_meta).
    """
    tables = page.find_tables()
    if not tables:
        return [], [], {"page": page_number, "metadata": None, "skipped": "no_table"}
    table = tables[0]
    rows = table.extract() or []
    if len(rows) < 5:
        return (
            [],
            [],
            {"page": page_number, "metadata": None, "skipped": "too_few_rows"},
        )

    metadata = detect_metadata_from_table_meta_row(rows[0])
    if (
        metadata["sex"] is None
        or metadata["mortality_table"] is None
        or metadata["interest_rate_pct"] is None
    ):
        return (
            [],
            [],
            {
                "page": page_number,
                "metadata": metadata,
                "skipped": "incomplete_metadata",
            },
        )

    header_row = rows[3]
    target_age_per_col: list[int | None] = []
    for col_idx, label in enumerate(header_row):
        if col_idx == 0:
            target_age_per_col.append(None)
            continue
        target_age_per_col.append(parse_target_age_label(label or ""))

    viager_rows: list[dict] = []
    temporaire_rows: list[dict] = []

    for r in rows[4:]:
        if not r or not r[0]:
            continue
        age_label = normalize_ws(r[0])
        if not re.fullmatch(r"\d+", age_label):
            continue
        age = int(age_label)
        for col_idx, raw in enumerate(r):
            if col_idx == 0:
                continue
            if col_idx >= len(header_row):
                break
            coeff = parse_capital_decimal(raw)
            if coeff is None:
                continue
            target_age = target_age_per_col[col_idx]
            if col_idx == 1:
                viager_rows.append(
                    {
                        "row_type": "fr_capitalisation_viagere_per_age_sex_rate_coefficient",
                        "mortality_table": metadata["mortality_table"],
                        "sex": metadata["sex"],
                        "age": age,
                        "interest_rate_pct": fmt_rate(metadata["interest_rate_pct"]),
                        "coefficient": str(coeff),
                        "source_page": page_number,
                        "source_note": source_note,
                    }
                )
            else:
                if target_age is None:
                    continue
                temporaire_rows.append(
                    {
                        "row_type": (
                            "fr_capitalisation_temporaire" "_per_age_sex_rate_targetage_coefficient"
                        ),
                        "mortality_table": metadata["mortality_table"],
                        "sex": metadata["sex"],
                        "age": age,
                        "interest_rate_pct": fmt_rate(metadata["interest_rate_pct"]),
                        "target_age": target_age,
                        "coefficient": str(coeff),
                        "source_page": page_number,
                        "source_note": source_note,
                    }
                )

    return (
        viager_rows,
        temporaire_rows,
        {
            "page": page_number,
            "metadata": {
                "sex": metadata["sex"],
                "mortality_table": metadata["mortality_table"],
                "interest_rate_pct": fmt_rate(metadata["interest_rate_pct"]),
            },
            "viager_rows": len(viager_rows),
            "temporaire_rows": len(temporaire_rows),
        },
    )


def extract_anticipated_years_page(page, source_note: str) -> list[dict]:
    """Estrae le 2 micro-tabelle 'années de prestation anticipées' di p.4."""
    text = page.extract_text() or ""
    rate_blocks = re.split(r"TAUX\s+D[’']?ACTUALISATION", text, flags=re.IGNORECASE)
    rates_in_order: list[Decimal] = []
    for block in rate_blocks[1:]:
        head = block[:200]
        m = re.match(r"\s+(NUL|DE\s*-?\s*\d+(?:[.,]\d+)?)\s*%?", head, flags=re.IGNORECASE)
        if not m:
            continue
        token = m.group(1).strip().upper()
        if token == "NUL":
            rates_in_order.append(Decimal("0.00"))
        else:
            num = re.search(r"-?\s*(\d+(?:[.,]\d+)?)", token)
            if num:
                v = num.group(1).replace(",", ".")
                rates_in_order.append(Decimal("-" + v) if "-" in token else Decimal(v))
    tables = page.find_tables()
    out: list[dict] = []
    for table_idx, table in enumerate(tables):
        rows = table.extract() or []
        if not rows or len(rows) < 2:
            continue
        header = [normalize_ws(c or "") for c in rows[0]]
        if "Âge" not in (header[0] if header else ""):
            continue
        rate = rates_in_order[table_idx] if table_idx < len(rates_in_order) else None
        if rate is None:
            continue
        for r in rows[1:]:
            if not r or not r[0]:
                continue
            age_label = normalize_ws(r[0])
            if not re.fullmatch(r"\d+", age_label):
                continue
            age = int(age_label)
            for col_idx, sex_code in enumerate(("M", "F"), start=1):
                if col_idx >= len(r):
                    break
                v = parse_year_decimal(r[col_idx])
                if v is None:
                    continue
                out.append(
                    {
                        "row_type": "fr_anticipated_payment_years_per_age_sex_rate_years",
                        "mortality_table": "INSEE-2017-2019",
                        "sex": sex_code,
                        "age": age,
                        "interest_rate_pct": fmt_rate(rate),
                        "years_value": str(v),
                        "source_page": 4,
                        "source_note": source_note,
                    }
                )
    return out


def write_csv(path: pathlib.Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    if not PDF_PATH.exists():
        print(f"[FATAL] PDF non trovato: {PDF_PATH}")
        return 2

    pdf_sha256 = hashlib.sha256(PDF_PATH.read_bytes()).hexdigest()
    if pdf_sha256 != EXPECTED_PDF_SHA256:
        print(f"[FATAL] hash PDF non corrisponde: {pdf_sha256!r} != {EXPECTED_PDF_SHA256!r}")
        return 2

    source_note = SOURCE_NOTE_TEMPLATE.format(pdf_sha256=pdf_sha256)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    viager_all: list[dict] = []
    temporaire_all: list[dict] = []
    anticipated_all: list[dict] = []
    page_summaries: list[dict] = []

    with pdfplumber.open(PDF_PATH) as pdf:
        anticipated_all = extract_anticipated_years_page(pdf.pages[3], source_note)
        for pg in CAPITALISATION_PAGES:
            page = pdf.pages[pg - 1]
            v, t, summary = extract_capitalisation_page(page, pg, source_note)
            viager_all.extend(v)
            temporaire_all.extend(t)
            page_summaries.append(summary)

    viager_fields = [
        "row_type",
        "mortality_table",
        "sex",
        "age",
        "interest_rate_pct",
        "coefficient",
        "source_page",
        "source_note",
    ]
    temporaire_fields = [
        "row_type",
        "mortality_table",
        "sex",
        "age",
        "interest_rate_pct",
        "target_age",
        "coefficient",
        "source_page",
        "source_note",
    ]
    anticipated_fields = [
        "row_type",
        "mortality_table",
        "sex",
        "age",
        "interest_rate_pct",
        "years_value",
        "source_page",
        "source_note",
    ]

    write_csv(
        OUTPUT_DIR / "fr-gazette-2022-capitalisation-viagere.csv",
        viager_all,
        viager_fields,
    )
    write_csv(
        OUTPUT_DIR / "fr-gazette-2022-capitalisation-temporaire.csv",
        temporaire_all,
        temporaire_fields,
    )
    write_csv(
        OUTPUT_DIR / "fr-gazette-2022-anticipated-payment-years.csv",
        anticipated_all,
        anticipated_fields,
    )

    summary = {
        "pdf_path": str(PDF_PATH.relative_to(ROOT)),
        "pdf_sha256": pdf_sha256,
        "pages_processed_capitalisation": CAPITALISATION_PAGES,
        "page_summaries": page_summaries,
        "totals": {
            "viager_rows": len(viager_all),
            "temporaire_rows": len(temporaire_all),
            "anticipated_rows": len(anticipated_all),
        },
        "output_dir": str(OUTPUT_DIR.relative_to(ROOT)),
        "files_written": [
            "fr-gazette-2022-capitalisation-viagere.csv",
            "fr-gazette-2022-capitalisation-temporaire.csv",
            "fr-gazette-2022-anticipated-payment-years.csv",
        ],
    }
    (OUTPUT_DIR / "extraction_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] PDF sha256 = {pdf_sha256}")
    print("[OK] Pagine capitalisation processate:")
    for s in page_summaries:
        if "skipped" in s:
            print(f"   p.{s['page']:>2}  SKIP {s['skipped']}")
        else:
            md = s["metadata"]
            print(
                f"   p.{s['page']:>2}  {md['mortality_table']:<18} sex={md['sex']} "
                f"rate={md['interest_rate_pct']:<7}  "
                f"viager={s['viager_rows']:>4}  temporaire={s['temporaire_rows']:>4}"
            )
    print(
        f"[OK] Totali: viager={len(viager_all)} "
        f"temporaire={len(temporaire_all)} anticipated={len(anticipated_all)}"
    )
    print(f"[OK] CSV scritti in {OUTPUT_DIR.relative_to(ROOT)} (gitignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
