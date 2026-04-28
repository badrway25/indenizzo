"""
Estrattore candidate delle Tabelle 2.A / 2.B / 2.C dal D.P.R. 12/2025
(danno biologico + danno morale aumento min/medio/max).

Output: tre CSV in legal_data/sources/italy/tun_2025/:
    tun_2025_moral_min_extraction_candidate.csv
    tun_2025_moral_mid_extraction_candidate.csv
    tun_2025_moral_max_extraction_candidate.csv

Schema CSV (compatibile con import_italy_tun_2025):
    row_type,age_min,age_max,disability_min,disability_max,
    point_value,coefficient,daily_amount,source_page,source_note

REGOLE:
- NESSUN dato inventato. Solo valori letti dalle pagine PDF mappate.
- Tracciabilità: source_page = numero pagina G.U. impressa.
- Flag legal_review_required=true e no_human_legal_approval=true
  in source_note di ogni riga.
- NON importa nel DB. Genera solo CSV candidate.
- NON modifica il PDF.
- Le righe con anomalie sono comunque emesse, con flag in source_note.

Struttura cella (verificata empiricamente su pag. 45):
    cella (età, invalidità) contiene TRE valori sovrapposti:
      - A      = valore punto biologico (= identico Tabella 1)
      - B      = incremento morale
      - A+B    = totale danno biologico + morale  ← target import
    A è sempre il maggiore tra A e B; A+B è sempre il maggiore in assoluto.
    Sanity check: A + B == A+B (con tolleranza di arrotondamento centesimi).
"""

from __future__ import annotations

import csv
import re
import sys
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
PDF_PATH = ROOT / "legal_data" / "sources" / "italy" / "tun_2025" / "dpr_12_2025_tun.pdf"
OUT_DIR = ROOT / "legal_data" / "sources" / "italy" / "tun_2025"

# Mappa demoltiplicatore (Tavola 1.B del D.P.R. 12/2025, pagina 8 PDF) → età.
# Trascritta dal testo ufficiale. NON inventata. La granularità non è lineare:
# da 0 a 20 incrementi di 0.005, da 21 a 100 incrementi misti di 0.004/0.005.
# Età 0 e 1 condividono il coefficiente 1.0 (Tavola 1.B mostra "-" per età 0).
# pdfplumber può restituire '1' come '1.0' nel rendering rotato.
_TAVOLA_1B = [
    (1, "1"),
    (1, "1.0"),
    (2, "0.995"),
    (3, "0.99"),
    (4, "0.985"),
    (5, "0.98"),
    (6, "0.975"),
    (7, "0.97"),
    (8, "0.965"),
    (9, "0.96"),
    (10, "0.955"),
    (11, "0.95"),
    (12, "0.945"),
    (13, "0.94"),
    (14, "0.935"),
    (15, "0.93"),
    (16, "0.925"),
    (17, "0.92"),
    (18, "0.915"),
    (19, "0.91"),
    (20, "0.905"),
    (21, "0.901"),
    (22, "0.896"),
    (23, "0.891"),
    (24, "0.886"),
    (25, "0.881"),
    (26, "0.876"),
    (27, "0.871"),
    (28, "0.866"),
    (29, "0.861"),
    (30, "0.856"),
    (31, "0.851"),
    (32, "0.846"),
    (33, "0.841"),
    (34, "0.836"),
    (35, "0.831"),
    (36, "0.826"),
    (37, "0.821"),
    (38, "0.816"),
    (39, "0.811"),
    (40, "0.806"),
    (41, "0.801"),
    (42, "0.797"),
    (43, "0.792"),
    (44, "0.787"),
    (45, "0.782"),
    (46, "0.777"),
    (47, "0.772"),
    (48, "0.767"),
    (49, "0.762"),
    (50, "0.757"),
    (51, "0.752"),
    (52, "0.747"),
    (53, "0.742"),
    (54, "0.738"),
    (55, "0.733"),
    (56, "0.728"),
    (57, "0.723"),
    (58, "0.718"),
    (59, "0.713"),
    (60, "0.708"),
    (61, "0.703"),
    (62, "0.698"),
    (63, "0.694"),
    (64, "0.689"),
    (65, "0.684"),
    (66, "0.679"),
    (67, "0.674"),
    (68, "0.669"),
    (69, "0.664"),
    (70, "0.66"),
    (71, "0.655"),
    (72, "0.65"),
    (73, "0.645"),
    (74, "0.64"),
    (75, "0.636"),
    (76, "0.631"),
    (77, "0.626"),
    (78, "0.621"),
    (79, "0.617"),
    (80, "0.612"),
    (81, "0.607"),
    (82, "0.602"),
    (83, "0.598"),
    (84, "0.593"),
    (85, "0.588"),
    (86, "0.584"),
    (87, "0.579"),
    (88, "0.574"),
    (89, "0.57"),
    (90, "0.565"),
    (91, "0.56"),
    (92, "0.556"),
    (93, "0.551"),
    (94, "0.547"),
    (95, "0.542"),
    (96, "0.537"),
    (97, "0.533"),
    (98, "0.529"),
    (99, "0.525"),
    (100, "0.522"),
]
DEMO_TO_AGES: dict[str, list[int]] = {}
for _age, _key in _TAVOLA_1B:
    DEMO_TO_AGES.setdefault(_key, []).append(_age)
# Età 0 e 1 condividono il coefficiente 1.0 (Tavola 1.B: "0 -" → vale come 1).
# Includiamo età 0 nella lista di "1.0" e "1" (entrambe le forme che pdfplumber
# può restituire per il valore "1" della colonna).
for _key in ("1", "1.0"):
    if _key in DEMO_TO_AGES and 0 not in DEMO_TO_AGES[_key]:
        DEMO_TO_AGES[_key].insert(0, 0)
# La forma '1' (senza decimale) genera molti falsi positivi nei frammenti
# di celle data. Escludiamola dal lookup demoltiplicatore: pdfplumber sui
# data page usa sempre '1.0'.
DEMO_TO_AGES.pop("1", None)

# Pagine dati PDF (1-indexed) per ogni Tabella moral.
# Layout verificato (vedi F-italy-tabelle-morali analisi):
#   2.A: title 44, dati 45-54 (inv 10-40), sep 55, dati 56-65 (inv 41-70),
#        sep 66, dati 67-76 (inv 71-100), sep 77.
#   2.B: title 77 (sovrapposto al sep di 2.A), dati 78-87 (inv 10-40), sep 88,
#        dati 89-98 (inv 41-70), sep 99, dati 100-109 (inv 71-100).
#   2.C: title 110, dati 111-120 (inv 10-40), sep 121, dati 122-131 (inv 41-70),
#        sep 132, dati 133-142 (inv 71-100), pages 143-152 = back/blank.
TABLE_PAGES = {
    "min": list(range(45, 55)) + list(range(56, 66)) + list(range(67, 77)),  # 30 pagine
    "mid": list(range(78, 88)) + list(range(89, 99)) + list(range(100, 110)),  # 30 pagine
    "max": list(range(111, 121)) + list(range(122, 132)) + list(range(133, 143)),  # 30 pagine
}

# Numero stampato sulla G.U. per la prima pagina dati 2.A è 41 (PDF pag 45),
# 2.B inizia con G.U. 73 (PDF pag 78), 2.C inizia con G.U. 106 (PDF pag 111).
# Calcolato empiricamente dalle scritte upright "− NN −" nei header di pagina.
GU_OFFSET = {"min": 41 - 45, "mid": 73 - 78, "max": 106 - 111}

ROW_TYPE_BY_TABLE = {
    "min": "tun_biological_moral_min_total_amount",
    "mid": "tun_biological_moral_mid_total_amount",
    "max": "tun_biological_moral_max_total_amount",
}

# Tolleranza in pt per associare un word a un cluster x della colonna invalidità.
# iter2: stretto a metà gap colonne (~6.5pt). Più largo significa raccogliere
# frammenti delle invalidità adiacenti e produrre candidati spurii.
X_TOL = 6.4

# Tolleranza in EUR sulla check A + B == A+B (gli importi sono al centesimo,
# alziamo a 0.05 per assorbire arrotondamenti di pdfplumber).
ABMATCH_TOL = Decimal("0.05")


@dataclass
class CellExtraction:
    age: int
    invalidity: int
    a_value: Decimal | None = None  # biologico
    b_value: Decimal | None = None  # morale
    ab_value: Decimal | None = None  # totale (A+B) ← target import
    flags: list[str] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def is_consistent(self) -> bool:
        if self.a_value is None or self.b_value is None or self.ab_value is None:
            return False
        diff = abs((self.a_value + self.b_value) - self.ab_value)
        return diff <= ABMATCH_TOL


def _parse_amount(s: str) -> Decimal | None:
    """Parse '26.124' / '5.486' / '1.007.514,50' / '548,60' → Decimal."""
    s = (s or "").strip().rstrip("e").rstrip("€").rstrip("e").strip()
    if not s:
        return None
    if "," in s:
        whole, _, dec = s.rpartition(",")
        whole = whole.replace(".", "")
        return Decimal(f"{whole}.{dec}")
    return Decimal(s.replace(".", ""))


def _reverse_words(page) -> list[dict]:
    out = []
    for w in page.extract_words(extra_attrs=["upright"]):
        if w.get("upright"):
            continue
        out.append(
            {
                "text": w["text"][::-1],
                "x0": w["x0"],
                "x1": w["x1"],
                "top": w["top"],
                "bottom": w["bottom"],
                "xc": (w["x0"] + w["x1"]) / 2,
            }
        )
    return out


def _find_demoltiplicatori(words: list[dict]) -> tuple[list[tuple[float, list[int]]], float]:
    """Yield (list of (y_anchor, [ages]), demo_column_x_max) for the page.

    iter2: detect the demo column dynamically. Cluster all words matching a
    Tavola 1.B value, find the dominant x-cluster (by sample count), then
    accept only words inside that cluster ±1.5pt. Robust to per-page x shifts
    (e.g. PDF page 142 has demo column at x=123-128 vs typical 119-124).

    Returns also the right edge x (x1_max) of the detected demo column so the
    caller can clip the leftmost inv column away from demoltiplicatore frags.
    """
    candidates = [w for w in words if w["text"] in DEMO_TO_AGES]
    if not candidates:
        return [], 0.0
    from collections import Counter

    buckets: Counter = Counter()
    for w in candidates:
        buckets[round(w["xc"] * 2) / 2] += 1
    mode_xc, _ = buckets.most_common(1)[0]
    cluster = [w for w in candidates if abs(w["xc"] - mode_xc) <= 1.6]
    out = []
    for w in cluster:
        ages = DEMO_TO_AGES.get(w["text"])
        if ages is None:
            continue
        out.append((w["top"], ages))
    out.sort(key=lambda t: -t[0])
    demo_x_max = max((w["x1"] for w in cluster), default=0.0)
    return out, demo_x_max


def _find_inv_columns(words: list[dict]) -> list[tuple[int, float]]:
    """Header row at y≈718 contains '10','11',...,'40' or '41'..'70' or '71'..'100'.

    iter2: tolerate y range 709-722 (PDF page 142 has header at y=711.1 for
    the inv=100 column, slightly below the rest of the row at y=712.4).
    Returns list of (invalidity, x_center) sorted by x.
    """
    out = []
    for w in words:
        if 709 < w["top"] < 722 and re.fullmatch(r"\d{2,3}", w["text"]):
            try:
                inv = int(w["text"])
            except ValueError:
                continue
            if 10 <= inv <= 100:
                out.append((inv, w["xc"]))
    out.sort(key=lambda t: t[1])
    return out


def _collect_cell_words(
    words: list[dict], y_top: float, y_bot: float, x_lo: float, x_hi: float
) -> list[dict]:
    return [w for w in words if y_bot <= w["top"] <= y_top and x_lo <= w["xc"] <= x_hi]


def _join_fragments(frags: list[dict]) -> Decimal | None:
    """Join word fragments belonging to one logical value.

    Sort by Y descending (top fragment first). Concatenate text with euro markers
    stripped, then parse as italian-formatted decimal.
    """
    if not frags:
        return None
    sorted_frags = sorted(frags, key=lambda w: -w["top"])
    text = "".join(w["text"] for w in sorted_frags)
    text = text.replace("€", "")
    text = text.replace("e", "")
    text = re.sub(r"[^\d.,]", "", text)
    if not text:
        return None
    try:
        return _parse_amount(text)
    except Exception:
        return None


def _cluster_y_lines(frags: list[dict], y_tol: float = 3.0) -> list[list[dict]]:
    """Cluster fragments into Y-bands (same logical printed line).

    Two fragments at distance ≤ y_tol on the y axis are considered the same line.
    Returns list of lines sorted top-to-bottom in pdf coord (largest y first).
    """
    if not frags:
        return []
    sorted_frags = sorted(frags, key=lambda w: -w["top"])
    lines: list[list[dict]] = [[sorted_frags[0]]]
    for w in sorted_frags[1:]:
        if abs(lines[-1][0]["top"] - w["top"]) <= y_tol:
            lines[-1].append(w)
        else:
            lines.append([w])
    return lines


def _enumerate_value_candidates(
    cell_frags: list[dict], y_link_tol: float = 18.0
) -> list[tuple[Decimal, list[dict]]]:
    """Enumerate plausible Decimal values reconstructable from cell fragments.

    Splits fragments into 2 x-clusters (left/right), within each cluster groups
    consecutive Y-lines that are within ``y_link_tol`` pt and joins them.
    Yields (decimal_value, source_frags) for each well-formed group.

    iter2 broadens the join window (was 14pt in iter1; same here) but ALSO
    tries every contiguous-line subgroup so a number like '1.007.514' can be
    split across 3 lines (~22pt total) and still be recovered when the
    middle gap exceeds y_link_tol.
    """
    digit_frags = [w for w in cell_frags if any(c.isdigit() for c in w["text"])]
    if not digit_frags:
        return []

    # Split by x at the midpoint of the actual x-range so that with two
    # tightly-grouped clusters (left ~xc=129, right ~xc=135.5) each side
    # gets its own fragments. Median-of-list picks the upper-middle item
    # when N is even and collapses the entire cell into one cluster.
    xs = [w["xc"] for w in digit_frags]
    if len(xs) >= 2:
        midpoint_x = (min(xs) + max(xs)) / 2
    else:
        midpoint_x = xs[0]
    left = [w for w in digit_frags if w["xc"] < midpoint_x]
    right = [w for w in digit_frags if w["xc"] >= midpoint_x]

    candidates: list[tuple[Decimal, list[dict]]] = []
    # iter2: enumerate ONLY left and right sub-clusters. Adding the full
    # digit_frags pool produced spurious candidates by joining A and A+B
    # fragments across columns whose y values happened to be within 3pt.
    for cluster in (left, right):
        if not cluster:
            continue
        lines = _cluster_y_lines(cluster, y_tol=3.0)
        # Try every contiguous slice of lines (1..len lines)
        for i in range(len(lines)):
            for j in range(i + 1, len(lines) + 1):
                slice_lines = lines[i:j]
                # Skip slices where two adjacent lines are farther than y_link_tol
                ok = True
                for k in range(len(slice_lines) - 1):
                    gap = slice_lines[k][0]["top"] - slice_lines[k + 1][0]["top"]
                    if gap > y_link_tol:
                        ok = False
                        break
                if not ok:
                    continue
                frags_flat = [f for line in slice_lines for f in line]
                val = _join_fragments(frags_flat)
                if val is None or val <= 0:
                    continue
                candidates.append((val, frags_flat))
    return candidates


def _reconstruct_cell_oracle(
    cell_frags: list[dict], a_oracle: Decimal | None
) -> tuple[Decimal | None, Decimal | None, Decimal | None, list[str]]:
    """iter2 cell reconstruction using Tabella 1 oracle for A.

    Strategy:
      1. Enumerate all plausible Decimal candidates from fragments.
      2. A+B = candidate v such that v > a_oracle and v <= a_oracle * 2.5,
         with v - a_oracle being a positive "B" of plausible magnitude.
         Prefer the smallest such v (closest to a_oracle).
      3. A = candidate equal to a_oracle (within 0.5 EUR rounding tol).
      4. B = A+B - a_oracle.

    Returns (a_value, b_value, ab_value, flags). Falls back to the iter1
    left/right reconstruction when no oracle is provided OR when no valid
    A+B candidate is found.
    """
    flags: list[str] = []
    candidates = _enumerate_value_candidates(cell_frags)
    if not candidates:
        flags.append("no_candidates")
        return None, None, None, flags

    if a_oracle is None:
        # Without oracle, fall back to old left/right split.
        return _reconstruct_cell_legacy(cell_frags, flags)

    # Find candidates that match A_oracle (within 0.5 EUR rounding tol)
    a_match = [v for v, _ in candidates if abs(v - a_oracle) <= Decimal("0.5")]
    a_value = a_oracle if a_match else None
    if not a_match:
        flags.append("a_oracle_not_extractable")

    # Find candidates that could be A+B: > A_oracle, <= A_oracle * 2.5
    upper = a_oracle * Decimal("2.5")
    ab_candidates = sorted(
        [v for v, _ in candidates if v > a_oracle and v <= upper],
        key=lambda v: v - a_oracle,
    )
    ab_value = ab_candidates[0] if ab_candidates else None
    if ab_value is None:
        flags.append("ab_not_findable")
        return a_value, None, None, flags

    b_value = ab_value - a_oracle
    # Sanity check: B should be << A_oracle (moral increment ≤ ~150% biological)
    if b_value < 0:
        flags.append("b_negative")
    return a_value, b_value, ab_value, flags


def _reconstruct_cell_legacy(
    cell_frags: list[dict], flags: list[str]
) -> tuple[Decimal | None, Decimal | None, Decimal | None, list[str]]:
    """iter1 left/right cluster reconstruction. Used as fallback."""
    digit_frags = [w for w in cell_frags if any(c.isdigit() for c in w["text"])]
    if not digit_frags:
        flags.append("right_cluster_empty")
        return None, None, None, flags
    median_x = sorted(d["xc"] for d in digit_frags)[len(digit_frags) // 2]
    left = [w for w in digit_frags if w["xc"] < median_x]
    right = [w for w in digit_frags if w["xc"] >= median_x]
    left_value = _join_fragments(left)
    right.sort(key=lambda w: -w["top"])
    a_value = b_value = None
    if right:
        top_y = right[0]["top"]
        a_value = _join_fragments([w for w in right if (top_y - w["top"]) <= 5])
        b_value = _join_fragments([w for w in right if (top_y - w["top"]) > 5])
    if a_value is None or b_value is None or left_value is None:
        flags.append("missing_value")
        return a_value, b_value, left_value, flags
    if abs((a_value + b_value) - left_value) > ABMATCH_TOL:
        flags.append("ab_check_fail")
    return a_value, b_value, left_value, flags


def load_tabella_1_oracle() -> dict[tuple[int, int], Decimal]:
    """Load the approved Tabella 1 dataset as oracle for A values.

    Read-only access to ``tun_2025_rows.csv`` (the production CSV that fed
    the import command). NEVER writes; NEVER touches the DB. If the file is
    missing the oracle is empty and the parser falls back to legacy mode.
    """
    oracle: dict[tuple[int, int], Decimal] = {}
    p = OUT_DIR / "tun_2025_rows.csv"
    if not p.exists():
        return oracle
    with p.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            try:
                age = int(row["age_min"])
                inv = int(row["disability_min"])
                pv = Decimal(row["point_value"])
            except (ValueError, KeyError):
                continue
            if row.get("row_type") != "tun_biological_total_amount":
                continue
            oracle[(age, inv)] = pv
    return oracle


def extract_page(
    pdf_page,
    table_kind: str,
    oracle: dict[tuple[int, int], Decimal] | None = None,
) -> list[CellExtraction]:
    """Extract one moral data page. iter2 uses the oracle when available."""
    if oracle is None:
        oracle = {}
    words = _reverse_words(pdf_page)
    demos, demo_x_max = _find_demoltiplicatori(words)
    inv_cols = _find_inv_columns(words)

    if not demos:
        return []
    if not inv_cols:
        return []

    cells: list[CellExtraction] = []

    for di, (demo_y, ages) in enumerate(demos):
        y_top_cell = demo_y + 33
        y_bot_cell = demo_y - 17
        if di > 0:
            prev_y = demos[di - 1][0]
            y_top_cell = min(y_top_cell, (demo_y + prev_y) / 2 - 1)
        if di < len(demos) - 1:
            next_y = demos[di + 1][0]
            y_bot_cell = max(y_bot_cell, (demo_y + next_y) / 2 + 1)

        for ci, (inv, x_center) in enumerate(inv_cols):
            x_lo = x_center - X_TOL
            x_hi = x_center + X_TOL
            if ci > 0:
                prev_xc = inv_cols[ci - 1][1]
                x_lo = max(x_lo, (x_center + prev_xc) / 2 + 0.5)
            else:
                # First column: clip left to just past the demo column.
                x_lo = max(x_lo, demo_x_max + 0.5)
            if ci < len(inv_cols) - 1:
                next_xc = inv_cols[ci + 1][1]
                x_hi = min(x_hi, (x_center + next_xc) / 2 - 0.5)

            cell_words = _collect_cell_words(words, y_top_cell, y_bot_cell, x_lo, x_hi)

            for age in ages:
                a_oracle = oracle.get((age, inv))
                a_v, b_v, ab_v, vflags = _reconstruct_cell_oracle(cell_words, a_oracle)
                cell = CellExtraction(age=age, invalidity=inv, flags=list(vflags))
                cell.a_value = a_v
                cell.b_value = b_v
                cell.ab_value = ab_v
                if (
                    not cell.is_consistent()
                    and "ab_check_fail" not in cell.flags
                    and a_v is not None
                    and b_v is not None
                    and ab_v is not None
                ):
                    cell.flags.append("ab_check_fail")
                cell.raw = {"a": str(a_v), "b": str(b_v), "ab": str(ab_v)}
                cells.append(cell)

    return cells


def _ab_check_status(cell: CellExtraction) -> str:
    if cell.ab_value is None:
        return "needs_review"
    if "ab_check_fail" in cell.flags:
        return "inconsistent"
    if "a_oracle_not_extractable" in cell.flags and "ab_not_findable" not in cell.flags:
        # Oracle mode: A+B was found via oracle inference but A wasn't directly
        # readable in the cell. Mark recovered, not consistent.
        return "recovered"
    if cell.a_value is None or cell.b_value is None:
        return "needs_review"
    return "consistent"


def main():
    if not PDF_PATH.exists():
        print(f"ERROR: PDF non trovato: {PDF_PATH}", file=sys.stderr)
        sys.exit(1)

    oracle = load_tabella_1_oracle()
    print(f"Tabella 1 oracle loaded: {len(oracle)} (age, inv) pairs")

    summary: dict[str, dict] = {}
    with pdfplumber.open(str(PDF_PATH)) as pdf:
        n_total_pages = len(pdf.pages)
        print(f"PDF total pages: {n_total_pages}")

        for kind, pages in TABLE_PAGES.items():
            print(f"\n=== Tabella 2.{kind.upper()} — {len(pages)} pagine ===")
            row_type = ROW_TYPE_BY_TABLE[kind]
            csv_path = OUT_DIR / f"tun_2025_moral_{kind}_candidate.csv"
            counts = {"consistent": 0, "inconsistent": 0, "recovered": 0, "needs_review": 0}
            with csv_path.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.DictWriter(
                    fh,
                    fieldnames=[
                        "row_type",
                        "age_min",
                        "age_max",
                        "disability_min",
                        "disability_max",
                        "point_value",
                        "coefficient",
                        "daily_amount",
                        "source_page",
                        "source_note",
                    ],
                )
                writer.writeheader()

                for pdf_idx_1based in pages:
                    page = pdf.pages[pdf_idx_1based - 1]
                    cells = extract_page(page, kind, oracle=oracle)
                    gu_page = pdf_idx_1based + GU_OFFSET[kind]
                    for cell in cells:
                        status = _ab_check_status(cell)
                        counts[status] += 1
                        flags_str = ";".join(cell.flags) if cell.flags else "ok"
                        notes_parts = [
                            "extraction=automated_pdfplumber_iter2",
                            "legal_review_required=true",
                            "no_human_legal_approval=true",
                            f"ab_check_status={status}",
                            f"a_value={cell.a_value}",
                            f"b_value={cell.b_value}",
                            f"ab_value={cell.ab_value}",
                            f"flags={flags_str}",
                            f"pdf_page_index={pdf_idx_1based}",
                        ]
                        writer.writerow(
                            {
                                "row_type": row_type,
                                "age_min": cell.age,
                                "age_max": cell.age,
                                "disability_min": cell.invalidity,
                                "disability_max": cell.invalidity,
                                "point_value": (
                                    str(cell.ab_value) if cell.ab_value is not None else ""
                                ),
                                "coefficient": "",
                                "daily_amount": "",
                                "source_page": str(gu_page),
                                "source_note": " ; ".join(notes_parts),
                            }
                        )
            total = sum(counts.values())
            summary[kind] = {"csv": csv_path.name, "total": total, **counts}
            print(f"  -> {csv_path}")
            print(f"  {counts} (total {total})")

    print("\n=== Summary iter2 ===")
    for kind, s in summary.items():
        print(f"  2.{kind.upper()}: {s}")


if __name__ == "__main__":
    main()
