"""
Estrazione READ-ONLY delle 2 sole tabelle di riferimento dal PDF
'Référentiel Mornet 2024' (Conseiller Benoît Mornet, Cour de cassation,
septembre 2024).

Iter: F-france-mornet-extraction-tables · iter1
Stato: candidate — NON importa nel DB. NON crea LegalReview /
CompensationDataset / CalculationFormula. Output: solo CSV in
legal_data/sources/france/mornet_2024/ (gitignored come da
.gitignore: legal_data/sources/**/*.csv).

Scope iter1 — solo le 2 tabelle riferimento stabili:
- p.71 — DFP (Déficit Fonctionnel Permanent), grid % invalidità x classe
  d'età, valore = € per "punto" DFP.
- p.94 — Préjudice d'affection, fourchette per relazione familiare in
  caso di décès.

Esplicitamente ESCLUSE (sono esempi pedagogici, non riferimento):
- p.88 (esempio CPAM/mutuelle, aritmetica del riparto);
- p.108 (esempio accident du travail);
- tutto il narrativo sulle altre voci (souffrances endurées,
  esthétique, agrément, sexuel, ...) — quelle voci richiedono
  transcrizione manuale dello Studio in iter successivo.

Convenzioni numeriche del PDF Mornet (DIVERSE dalla Gazette del
barème di capitalisation):
- Il PUNTO è separatore di MIGLIAIA: "2.310" -> 2310.
- Lo SPAZIO è separatore di MIGLIAIA: "25 000" -> 25000.
- "880" senza separatore -> 880.
- I range sono "X € à Y €" (preposizione "à").
- "Majoration de 40% à 60%" non è un range monetario assoluto; le
  righe "Majoration ..." sono SCARTATE (richiedono interpretazione
  legale dello Studio durante la review).

Uso:
    .venv/Scripts/python.exe scripts/legal_data/extract_france_mornet_2024.py

Output:
    legal_data/sources/france/mornet_2024/
        fr-mornet-2024-dfp-per-age-disability.csv
        fr-mornet-2024-prejudice-affection-per-relation.csv
        extraction_summary.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import pathlib
import re
import sys
from decimal import Decimal

import pdfplumber

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]
PDF_PATH = (
    ROOT / "legal_data" / "sources" / "france" / "downloaded" / "fr-referentiel-mornet-2024.pdf"
)
OUTPUT_DIR = ROOT / "legal_data" / "sources" / "france" / "mornet_2024"

EXPECTED_PDF_SHA256 = "2dd2e760bc057b38275a7a6de24a62c009f6d04dd79573c00ee052f4f6df72b4"

# 1-indexed PDF pages
DFP_PAGE = 71
AFFECTION_PAGE = 94

SOURCE_NOTE_TEMPLATE = (
    "extraction=automated_pdfplumber;"
    "legal_review_required=true;"
    "no_human_legal_approval=true;"
    "pdf_sha256={pdf_sha256};"
    "pdf_slug=fr-referentiel-mornet-2024;"
    "extractor_script=scripts/legal_data/extract_france_mornet_2024.py;"
    "iter=1"
)


def normalize_ws(s: str | None) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s).strip()


def normalize_apostrophes(s: str) -> str:
    """Curly U+2019 -> straight ' so RELATION_MAP patterns match consistently."""
    return s.replace("’", "'")


def parse_eur_amount(raw: str | None) -> Decimal | None:
    """Parser per importi Mornet: PUNTO/SPAZIO = separatore di MIGLIAIA.

    Esempi:
      "2.310" -> 2310
      "25 000" -> 25000
      "880" -> 880
      "20.000 €" -> 20000
    """
    if raw is None:
        return None
    s = raw.replace("\xa0", " ").replace("€", "").strip()
    if not s:
        return None
    s_clean = re.sub(r"[\s\.]", "", s)
    if not s_clean.isdigit():
        return None
    return Decimal(s_clean)


def parse_age_band(label: str) -> tuple[int, int] | None:
    """'0 à 10\\nans' -> (0,10) ; '81 ans\\net plus' -> (81, 120) ."""
    norm = normalize_ws(label).lower()
    if not norm:
        return None
    m = re.match(r"(\d+)\s*à\s*(\d+)\s*ans?", norm)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"(\d+)\s*ans?\s*et\s*plus", norm)
    if m:
        return int(m.group(1)), 120
    return None


def parse_disability_band(label: str) -> tuple[int, int] | None:
    """'1 à 5 %' -> (1,5) ; '11 à 15%' -> (11,15) ; '96 % plus' -> (96, 100) ."""
    norm = normalize_ws(label).lower()
    if not norm:
        return None
    m = re.match(r"(\d+)\s*à\s*(\d+)\s*%?", norm)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"(\d+)\s*%?\s*plus", norm)
    if m:
        return int(m.group(1)), 100
    return None


def extract_dfp_table(page, source_note: str) -> list[dict]:
    """Estrae i 180 (atteso) cell dalla tabella p.71."""
    tables = page.find_tables()
    if not tables:
        return []
    rows = tables[0].extract() or []
    if len(rows) < 2:
        return []
    header = rows[0]
    age_per_col: list[tuple[int, int] | None] = [None]
    for col_idx in range(1, len(header)):
        age_per_col.append(parse_age_band(header[col_idx] or ""))

    out: list[dict] = []
    for r in rows[1:]:
        if not r or not r[0]:
            continue
        dis = parse_disability_band(r[0])
        if dis is None:
            continue
        d_min, d_max = dis
        for col_idx in range(1, len(r)):
            if col_idx >= len(age_per_col):
                break
            age = age_per_col[col_idx]
            if age is None:
                continue
            amount = parse_eur_amount(r[col_idx])
            if amount is None:
                continue
            out.append(
                {
                    "row_type": "fr_dfp_per_age_disability_amount_per_point",
                    "victim_age_min": age[0],
                    "victim_age_max": age[1],
                    "disability_min": d_min,
                    "disability_max": d_max,
                    "amount_min": str(amount),
                    "amount_mid": str(amount),
                    "amount_max": str(amount),
                    "currency": "EUR",
                    "source_page": DFP_PAGE,
                    "source_note": source_note,
                }
            )
    return out


# ---- p.94 — préjudice d'affection ------------------------------------------

# Mapping deterministico (heading_substring, sub_item_substring_or_None)
# verso (relation_code, relation_label_fr). Heading NON case-sensitive.
# Sub-item se presente DEVE matchare su una linea che inizia con "-".
# Se la riga 'Majoration ...' viene incontrata, la riga è SCARTATA (no
# absolute amount).
RELATION_MAP: list[tuple[str, str | None, str, str]] = [
    (
        "conjoint",
        None,
        "conjoint_perte_conjoint",
        "Conjoint ou concubin — décès de l'autre conjoint",
    ),
    (
        "enfant en cas de décès",
        "mineur déjà orphelin",
        "enfant_mineur_orphelin_perte_parent",
        "Enfant mineur déjà orphelin — décès du père ou de la mère",
    ),
    (
        "enfant en cas de décès",
        "enfant mineur",
        "enfant_mineur_perte_parent",
        "Enfant mineur — décès du père ou de la mère",
    ),
    (
        "enfant en cas de décès",
        "majeur vivant au foyer",
        "enfant_majeur_au_foyer_perte_parent",
        "Enfant majeur vivant au foyer — décès du père ou de la mère",
    ),
    (
        "enfant en cas de décès",
        "majeur vivant hors",
        "enfant_majeur_hors_foyer_perte_parent",
        "Enfant majeur vivant hors du foyer — décès du père ou de la mère",
    ),
    (
        "parent pour la perte",
        None,
        "parent_perte_enfant",
        "Parent — perte d'un enfant",
    ),
    (
        "frères et sœurs",
        "vivant au sein du même foyer",
        "freres_soeurs_meme_foyer",
        "Frères et sœurs — vivant au sein du même foyer",
    ),
    (
        "frères et sœurs",
        "ne vivant pas au même foyer",
        "freres_soeurs_hors_foyer",
        "Frères et sœurs — ne vivant pas au même foyer",
    ),
    (
        "grand-parent pour la perte d'un petit-enfant",
        "relations peu fréquentes",
        "grand_parent_perte_petit_enfant_peu_freq",
        "Grand-parent — perte d'un petit-enfant — relations peu fréquentes",
    ),
    (
        "grand-parent pour la perte d'un petit-enfant",
        "relations fréquentes",
        "grand_parent_perte_petit_enfant_freq",
        "Grand-parent — perte d'un petit-enfant — relations fréquentes",
    ),
    (
        "petit-enfant pour la perte d'un grand-parent",
        "relations peu fréquentes",
        "petit_enfant_perte_grand_parent_peu_freq",
        "Petit-enfant — perte d'un grand-parent — relations peu fréquentes",
    ),
    (
        "petit-enfant pour la perte d'un grand-parent",
        "relations fréquentes",
        "petit_enfant_perte_grand_parent_freq",
        "Petit-enfant — perte d'un grand-parent — relations fréquentes",
    ),
]


def lookup_relation(heading_lower: str, sub_lower: str | None) -> tuple[str, str] | None:
    for h_pat, s_pat, code, label in RELATION_MAP:
        if h_pat not in heading_lower:
            continue
        if s_pat is None and sub_lower is None:
            return code, label
        if s_pat is not None and sub_lower is not None and s_pat in sub_lower:
            return code, label
    return None


def parse_amount_range_line(text: str) -> tuple[Decimal, Decimal] | None:
    """ "20.000 € à 30.000 €" -> (20000, 30000) ;
    "5.000 €" -> (5000, 5000) ;
    "Majoration de 40% à 60%" -> None (modificatore percentuale, non range absolute).
    """
    t = text.replace("\xa0", " ").strip()
    if not t:
        return None
    if "majoration" in t.lower():
        return None
    if "%" in t:
        return None
    matches = re.findall(r"([\d\.\s]+?)\s*€", t)
    if not matches:
        return None
    nums: list[Decimal] = []
    for m in matches:
        v = parse_eur_amount(m)
        if v is not None:
            nums.append(v)
    if not nums:
        return None
    if len(nums) == 1:
        return nums[0], nums[0]
    return min(nums), max(nums)


def extract_affection_table(page, source_note: str) -> tuple[list[dict], list[dict]]:
    """Estrae le 11 (atteso) righe da p.94 come amount_range.

    Ritorna (rows_extracted, rows_skipped) — le righe scartate sono
    quelle "Majoration ..." (non sono importi assoluti).
    """
    tables = page.find_tables()
    if not tables:
        return [], []
    table = tables[0]
    raw_rows = table.extract() or []
    out: list[dict] = []
    skipped: list[dict] = []
    for row in raw_rows:
        if not row or len(row) < 2 or not row[0] or not row[1]:
            continue
        label_cell = row[0]
        amount_cell = row[1]
        label_lines = [normalize_ws(line) for line in label_cell.split("\n") if normalize_ws(line)]
        amount_lines = [
            normalize_ws(line) for line in amount_cell.split("\n") if normalize_ws(line)
        ]
        sub_items = [line.lstrip("- ").strip() for line in label_lines if line.startswith("-")]
        heading_parts = [line for line in label_lines if not line.startswith("-")]
        heading = " ".join(heading_parts).rstrip(":").strip()
        heading_lower = normalize_apostrophes(heading.lower())

        if not sub_items:
            if len(amount_lines) != 1:
                continue
            rng = parse_amount_range_line(amount_lines[0])
            if rng is None:
                skipped.append({"heading": heading, "amount": amount_lines[0]})
                continue
            rel = lookup_relation(heading_lower, None)
            if rel is None:
                continue
            code, label_fr = rel
            amin, amax = rng
            mid = (amin + amax) / Decimal(2)
            out.append(
                {
                    "row_type": "fr_prejudice_affection_per_relation_amount",
                    "relation_code": code,
                    "relation_label_fr": label_fr,
                    "amount_min": str(amin),
                    "amount_mid": str(mid.quantize(Decimal("1"))),
                    "amount_max": str(amax),
                    "currency": "EUR",
                    "source_page": AFFECTION_PAGE,
                    "source_note": source_note,
                }
            )
            continue

        # Compound row con sub-items
        if len(sub_items) != len(amount_lines):
            continue
        for sub, amt in zip(sub_items, amount_lines, strict=True):
            sub_lower = sub.lower()
            rng = parse_amount_range_line(amt)
            if rng is None:
                skipped.append({"heading": heading, "sub": sub, "amount": amt})
                continue
            rel = lookup_relation(heading_lower, sub_lower)
            if rel is None:
                continue
            code, label_fr = rel
            amin, amax = rng
            mid = (amin + amax) / Decimal(2)
            out.append(
                {
                    "row_type": "fr_prejudice_affection_per_relation_amount",
                    "relation_code": code,
                    "relation_label_fr": label_fr,
                    "amount_min": str(amin),
                    "amount_mid": str(mid.quantize(Decimal("1"))),
                    "amount_max": str(amax),
                    "currency": "EUR",
                    "source_page": AFFECTION_PAGE,
                    "source_note": source_note,
                }
            )
    return out, skipped


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

    with pdfplumber.open(PDF_PATH) as pdf:
        dfp_rows = extract_dfp_table(pdf.pages[DFP_PAGE - 1], source_note)
        affection_rows, affection_skipped = extract_affection_table(
            pdf.pages[AFFECTION_PAGE - 1], source_note
        )

    dfp_fields = [
        "row_type",
        "victim_age_min",
        "victim_age_max",
        "disability_min",
        "disability_max",
        "amount_min",
        "amount_mid",
        "amount_max",
        "currency",
        "source_page",
        "source_note",
    ]
    affection_fields = [
        "row_type",
        "relation_code",
        "relation_label_fr",
        "amount_min",
        "amount_mid",
        "amount_max",
        "currency",
        "source_page",
        "source_note",
    ]

    write_csv(
        OUTPUT_DIR / "fr-mornet-2024-dfp-per-age-disability.csv",
        dfp_rows,
        dfp_fields,
    )
    write_csv(
        OUTPUT_DIR / "fr-mornet-2024-prejudice-affection-per-relation.csv",
        affection_rows,
        affection_fields,
    )

    summary = {
        "pdf_path": str(PDF_PATH.relative_to(ROOT)),
        "pdf_sha256": pdf_sha256,
        "iter": "F-france-mornet-extraction-tables · iter1",
        "scope": {
            "included_pages": [DFP_PAGE, AFFECTION_PAGE],
            "excluded_pages": [88, 108],
            "exclusion_reason": (
                "p.88 e p.108 contengono esempi pedagogici (riparto CPAM/"
                "mutuelle, accident du travail), non tabelle di riferimento"
            ),
        },
        "totals": {
            "dfp_rows": len(dfp_rows),
            "affection_rows": len(affection_rows),
            "affection_rows_skipped_majoration": len(affection_skipped),
        },
        "affection_skipped_detail": affection_skipped,
        "output_dir": str(OUTPUT_DIR.relative_to(ROOT)),
        "files_written": [
            "fr-mornet-2024-dfp-per-age-disability.csv",
            "fr-mornet-2024-prejudice-affection-per-relation.csv",
        ],
    }
    (OUTPUT_DIR / "extraction_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] PDF sha256 = {pdf_sha256}")
    print(
        f"[OK] DFP (p.{DFP_PAGE}): {len(dfp_rows)} rows estratte "
        f"(atteso 180 = 20 disability x 9 age)"
    )
    print(
        f"[OK] Affection (p.{AFFECTION_PAGE}): {len(affection_rows)} rows estratte "
        f"+ {len(affection_skipped)} 'Majoration' scartate"
    )
    if affection_skipped:
        print("  [INFO] righe scartate (Majoration % — interpretazione legale):")
        for s in affection_skipped:
            print(f"    - {s}")
    print(f"[OK] CSV scritti in {OUTPUT_DIR.relative_to(ROOT)} (gitignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
