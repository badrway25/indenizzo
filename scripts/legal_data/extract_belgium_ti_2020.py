"""
Estrazione READ-ONLY delle 4 famiglie di tabelle strutturate dal PDF
'Tableau Indicatif belge 2020' (édition Union nationale des
magistrats de police / Vereniging Nationale van politierechters).

Iter: F-belgium-extraction-ti-2020 · iter1
Stato: candidate — NON importa nel DB. NON crea LegalReview /
CompensationDataset / CalculationFormula. Output: solo CSV in
legal_data/sources/belgium/tableau_indicatif_2020/ (gitignored).

Scope iter1 — 4 famiglie tabulari:
1. p.17  — Souffrances endurées (douleur / pijn) — Julin 1/7..7/7 x age band -> €.
2. p.22-23 — Indennità forfetaria per età (Tableau 3.7. forfaits par
   degré d'incapacité). NB: il filename rispetta lo spec utente
   ('prejudice-esthetique') ma il row_type interno e la documentazione
   chiariscono che la tabella belga p.22-23 è una INDENNITÀ
   FORFETARIA per anno per 1% incapacité, NON un préjudice esthétique
   in senso stretto. Vedi QA report.
3. p.25-26 — Préjudice par décès — relazione familiare -> €.
4. p.31-32 — Véhicule de remplacement — type véhicule -> €/jour.

Tutte le tabelle BE 2020 sono BILINGUI NL/FR. Strategia:
- preferiamo la versione FR per le label;
- conserviamo codici stabili neutri (snake_case);
- gli importi sono identici tra NL e FR (estraiamo 1 sola volta).

Regola fondamentale: importi normalizzati con
- PUNTO/SPAZIO = separatore migliaia ("2.150" -> 2150, "15 000" -> 15000);
- VIRGOLA = separatore decimale ("0,00" -> .00).

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

import pdfplumber

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]
PDF_PATH = (
    ROOT / "legal_data" / "sources" / "belgium" / "downloaded" / "be-tableau-indicatif-2020.pdf"
)
OUTPUT_DIR = ROOT / "legal_data" / "sources" / "belgium" / "tableau_indicatif_2020"

EXPECTED_PDF_SHA256 = "1b073f5c41c8414018e262143d7e67c496bbeeb832e623f406333b3ece0b8222"

SOUFFRANCES_PAGE = 17  # 1-indexed
ESTHETIQUE_PAGES = (22, 23)
DECES_PAGE_FR = 26  # FR table; NL is on p.25
VEHICULE_PAGE_FR = 32  # FR table; NL is on p.31

SOURCE_NOTE_TEMPLATE = (
    "extraction=automated_pdfplumber;"
    "legal_review_required=true;"
    "no_human_legal_approval=true;"
    "pdf_sha256={pdf_sha256};"
    "pdf_slug=be-tableau-indicatif-2020;"
    "extractor_script=scripts/legal_data/extract_belgium_ti_2020.py;"
    "iter=1;"
    "source_is_historical_2020=true"
)


# ---------- helpers numerici ------------------------------------------------


def parse_eur_amount(raw: str | None) -> Decimal | None:
    """Parser per importi BE 2020: PUNTO/SPAZIO = migliaia, VIRGOLA = decimale.

    Esempi:
      "€ 540,00"  -> Decimal('540.00')
      "€ 2.150,00" -> Decimal('2150.00')
      "15 000,00" -> Decimal('15000.00')
      "10,00 euros" -> Decimal('10.00')
      "150,00 euro" -> Decimal('150.00')
    """
    if raw is None:
        return None
    s = raw.replace("\xa0", " ").strip()
    if not s:
        return None
    # Strip currency symbols / words
    s = s.replace("€", "").strip()
    s = re.sub(r"\b(euros?|EUR)\b", "", s, flags=re.IGNORECASE).strip()
    if not s:
        return None
    # Period / space = thousands separator -> remove
    s_no_thou = re.sub(r"[\s\.](?=\d{3}(?:\D|$))", "", s)
    # Now comma should be decimal separator
    s_norm = s_no_thou.replace(",", ".")
    if not re.fullmatch(r"-?\d+(?:\.\d+)?", s_norm):
        return None
    try:
        return Decimal(s_norm)
    except Exception:  # noqa: BLE001
        return None


def normalize_ws(s: str | None) -> str:
    if s is None:
        return ""
    return re.sub(r"\s+", " ", s).strip()


# ---------- 1. Souffrances endurées (p.17) ----------------------------------

SEVERITY_FR = {
    "1_7": "minime",
    "2_7": "très léger",
    "3_7": "léger",
    "4_7": "moyen",
    "5_7": "grave",
    "6_7": "très grave",
    "7_7": "exceptionnellement grave",
}


def parse_age_band_se(label: str) -> tuple[int, int] | None:
    """'0-10' -> (0,10) ; '81 et plus' -> (81, 120) ;
    '81 en\\nouder' -> (81, 120) ."""
    norm = normalize_ws(label).lower()
    if not norm:
        return None
    m = re.match(r"(\d+)\s*[-–]\s*(\d+)", norm)
    if m:
        return int(m.group(1)), int(m.group(2))
    m = re.match(r"(\d+)\s*(?:et\s*plus|en\s*ouder)", norm)
    if m:
        return int(m.group(1)), 120
    return None


def extract_souffrances_endurees(page, source_note: str) -> list[dict]:
    """Estrae 9 ages × 7 severities = 63 righe attese.

    Usa la tabella FR (table#1) per le label; i numeri sono identici
    nella tabella NL (table#0).
    """
    tables = page.find_tables()
    if len(tables) < 2:
        return []
    # Tabella FR è la seconda
    rows = tables[1].extract() or []
    if len(rows) < 3:
        return []
    header = rows[0]
    # Mappa col_idx -> severity_code
    severity_per_col: dict[int, str] = {}
    for col_idx, h in enumerate(header):
        m = re.match(r"\s*(\d)\s*/\s*7", (h or "").strip())
        if m and col_idx > 0:
            severity_per_col[col_idx] = f"{m.group(1)}_7"

    out: list[dict] = []
    for r in rows[2:]:  # rows[1] è la riga delle label severity (skip)
        if not r or not r[0]:
            continue
        age = parse_age_band_se(r[0])
        if age is None:
            continue
        for col_idx, sev_code in severity_per_col.items():
            if col_idx >= len(r):
                continue
            amount = parse_eur_amount(r[col_idx])
            if amount is None:
                continue
            out.append(
                {
                    "row_type": "be_souffrances_endurees_per_age_severity_amount",
                    "severity_code": sev_code,
                    "severity_label_fr": SEVERITY_FR[sev_code],
                    "victim_age_min": age[0],
                    "victim_age_max": age[1],
                    "amount_min": str(amount),
                    "amount_mid": str(amount),
                    "amount_max": str(amount),
                    "currency": "EUR",
                    "source_page": SOUFFRANCES_PAGE,
                    "source_note": source_note,
                }
            )
    return out


# ---------- 2. "Esthétique" (p.22-23) — in realtà incapacité forfaitaire ----


def parse_age_band_esth(label: str) -> tuple[int, int] | None:
    """'Jusque 15 ans /tot 15 jaar' -> (0,15) ;
    '16 ans/jaar' -> (16,16) ;
    '85 ans et plus/jaar en me' -> (85,120) ."""
    norm = normalize_ws(label).lower()
    if not norm:
        return None
    if "jusque" in norm or "tot" in norm:
        m = re.search(r"(\d+)", norm)
        if m:
            return 0, int(m.group(1))
    if "et plus" in norm or "en me" in norm:
        m = re.search(r"(\d+)", norm)
        if m:
            return int(m.group(1)), 120
    m = re.match(r"(\d+)\s*ans?", norm)
    if m:
        a = int(m.group(1))
        return a, a
    return None


def extract_esthetique(pdf, source_note: str) -> list[dict]:
    """Estrae 71 righe attese da p.22-23 (jusque 15 + 16-55 + 56-84 + 85+).

    Schema con severity_code='default' perché la tabella non ha scala
    di gravità (è un forfait per età).
    """
    out: list[dict] = []
    seen_age_keys: set[tuple[int, int]] = set()
    for pg_num in ESTHETIQUE_PAGES:
        page = pdf.pages[pg_num - 1]
        tables = page.find_tables()
        for t in tables:
            rows = t.extract() or []
            for r in rows:
                if not r or not r[0]:
                    continue
                age = parse_age_band_esth(r[0])
                if age is None:
                    continue
                # Trova la cella più a destra con un importo
                amount: Decimal | None = None
                for cell in reversed(r):
                    if cell and "€" in cell:
                        amount = parse_eur_amount(cell)
                        if amount is not None:
                            break
                if amount is None:
                    continue
                key = age
                if key in seen_age_keys:
                    continue
                seen_age_keys.add(key)
                out.append(
                    {
                        "row_type": "be_indemnite_forfaitaire_per_age_annual_amount",
                        "severity_code": "default",
                        "severity_label_fr": "default (no severity scale)",
                        "victim_age_min": age[0],
                        "victim_age_max": age[1],
                        "annual_amount": str(amount),
                        "currency": "EUR",
                        "source_page": pg_num,
                        "source_note": source_note,
                    }
                )
    return out


# ---------- 3. Décès / affection (p.26 FR) ----------------------------------


# Mapping deterministico (substring victim →, substring beneficiary, code, label_fr).
# Sub-string lowercase, accenti preservati.
DECES_RELATION_MAP: list[tuple[str, str, str, str]] = [
    (
        "conjoint",
        "conjoint",
        "conjoint_perte_conjoint",
        "Conjoint/concubin/pacsé — perte de l'autre conjoint/concubin/pacsé",
    ),
    (
        "parent cohabitant",
        "enfant cohabitant orphelin",
        "parent_cohabitant_perte_enfant_cohabitant_orphelin",
        "Parent cohabitant — perte de l'enfant cohabitant orphelin",
    ),
    (
        "parent cohabitant",
        "enfant cohabitant",
        "parent_cohabitant_perte_enfant_cohabitant",
        "Parent cohabitant — perte de l'enfant cohabitant",
    ),
    (
        "parent non cohabitant",
        "enfant non cohabitant",
        "parent_non_cohabitant_perte_enfant_non_cohabitant",
        "Parent non cohabitant — perte de l'enfant non cohabitant",
    ),
    (
        "enfant cohabitant",
        "parent",
        "enfant_cohabitant_perte_parent",
        "Enfant cohabitant — perte du parent",
    ),
    (
        "enfant en autonomie",
        "parent",
        "enfant_autonome_perte_parent",
        "Enfant en autonomie — perte du parent",
    ),
    (
        "fausse couche",
        "parent",
        "fausse_couche_perte_parent",
        "Fausse couche — perte du parent",
    ),
    (
        "frère/sœur cohabitant",
        "frère/sœur cohabitant",
        "frere_soeur_cohabitant_perte_frere_soeur_cohabitant",
        "Frère/sœur cohabitant — perte du frère/sœur cohabitant",
    ),
    (
        "frère/sœur non cohabitant",
        "frère/sœur non cohabitant",
        "frere_soeur_non_cohabitant_perte_frere_soeur_non_cohabitant",
        "Frère/sœur non cohabitant — perte du frère/sœur non cohabitant",
    ),
    (
        "grands-parents cohabitants",
        "petits-enfants cohabitants",
        "grands_parents_cohabitants_perte_petits_enfants_cohabitants",
        "Grands-parents cohabitants — perte des petits-enfants cohabitants",
    ),
    (
        "grands-parents non cohabitants",
        "petits-enfants non cohabitants",
        "grands_parents_non_cohabitants_perte_petits_enfants_non_cohabitants",
        "Grands-parents non cohabitants — perte des petits-enfants non cohabitants",
    ),
    (
        "petits-enfants cohabitants",
        "grands-parents cohabitants",
        "petits_enfants_cohabitants_perte_grands_parents_cohabitants",
        "Petits-enfants cohabitants — perte des grands-parents cohabitants",
    ),
    (
        "petits-enfants non cohabitants",
        "grands-parents non cohabitants",
        "petits_enfants_non_cohabitants_perte_grands_parents_non_cohabitants",
        "Petits-enfants non cohabitants — perte des grands-parents non cohabitants",
    ),
]


def lookup_deces_relation(victim_lower: str, benef_lower: str) -> tuple[str, str] | None:
    for v_pat, b_pat, code, label in DECES_RELATION_MAP:
        if v_pat in victim_lower and b_pat in benef_lower:
            return code, label
    return None


def extract_deces_affection(page, source_note: str) -> list[dict]:
    """Estrae 13 righe attese da p.26 (FR), parsando direttamente il
    testo della pagina (più affidabile delle celle pdfplumber che
    spezzano le label nelle colonne intermedie)."""
    text = page.extract_text() or ""
    out: list[dict] = []
    for line in text.split("\n"):
        line = line.strip()
        if "→" not in line or "€" not in line:
            continue
        m = re.match(r"\s*(.+?)\s*→\s*(.+?)\s*€\s*([\d\.\s]+,\d{2})\s*$", line)
        if not m:
            continue
        victim_label = m.group(1).strip()
        benef_label = m.group(2).strip()
        amount = parse_eur_amount("€ " + m.group(3))
        if amount is None:
            continue
        rel = lookup_deces_relation(victim_label.lower(), benef_label.lower())
        if rel is None:
            continue
        code, label_fr = rel
        out.append(
            {
                "row_type": "be_prejudice_deces_affection_per_relation_amount",
                "relation_code": code,
                "relation_label_fr": label_fr,
                "amount_min": str(amount),
                "amount_mid": str(amount),
                "amount_max": str(amount),
                "currency": "EUR",
                "source_page": DECES_PAGE_FR,
                "source_note": source_note,
            }
        )
    return out


# ---------- 4. Véhicule de remplacement (p.32 FR) ---------------------------


# Mapping (substring du label FR, code stabile, label FR umana) — l'ordine
# è importante: il primo match vince.
VEHICULE_MAP: list[tuple[str, str, str]] = [
    (
        "bicyclette",
        "fr_bicyclette",
        "Bicyclette (avec/sans assistance, max. 25 km/h)",
    ),
    (
        "2 ou 3 roues motorisées",
        "fr_motorisees_2_3_roues",
        "2 ou 3 roues motorisées, quad et speed pédelec",
    ),
    ("ambulance", "fr_ambulance", "Ambulance"),
    (
        "remorque de camping",
        "fr_remorque_camping",
        "Remorque de camping/caravane",
    ),
    (
        "voiture de location",
        "fr_voiture_location",
        "Voiture de location (hors leasing)",
    ),
    ("mobilhome", "fr_mobilhome", "Mobilhome"),
    (
        "taxi grandes entreprises",
        "fr_taxi_grandes_entreprises",
        "Taxi grandes entreprises",
    ),
    (
        "taxi exploitant indépendant",
        "fr_taxi_independant",
        "Taxi exploitant indépendant",
    ),
    (
        "voitures (également",
        "fr_voiture_perso_pro",
        "Voitures (également usage professionnel et leasing)",
    ),
    (
        "camionnettes",
        "fr_camionnettes_jusqu_3_5t",
        "Camionnettes et petits camions jusqu'à 3,5 t (charge utile)",
    ),
    (
        "propriétaire d",
        "fr_proprietaire_un_camion",
        "Propriétaire d'un seul camion",
    ),
    (
        "véhicules lourds",
        "fr_vehicules_lourds_speciaux",
        "Véhicules lourds de nature particulière (dépanneuse, citerne, grue, "
        "malaxeur, tracteur agricole, semi-remorque, remorque de camion)",
    ),
]

REMORQUE_SUBROWS = [
    (
        "fr_remorque_voiture_moins_750kg",
        "Remorque de voiture < 750 kg",
        "moins de 750 kg",
    ),
    (
        "fr_remorque_voiture_plus_750kg",
        "Remorque de voiture ≥ 750 kg",
        "plus de 750 kg",
    ),
]

AUTOBUS_SUBROWS = [
    ("fr_autobus_lt_50", "Autobus/autocar < 50 places (NL: < 31 places)"),
    ("fr_autobus_50_60", "Autobus/autocar ≥ 50 places (NL: ≥ 31 places)"),
    ("fr_autobus_60_70", "Autobus/autocar ≥ 60 places (NL: ≥ 38 places)"),
    ("fr_autobus_70_80", "Autobus/autocar ≥ 70 places (NL: ≥ 44 places)"),
    ("fr_autobus_80_plus", "Autobus/autocar ≥ 80 places (NL: ≥ 50 places)"),
]


def extract_vehicule(page, source_note: str) -> tuple[list[dict], list[dict]]:
    """Ritorna (rows_extracted, rows_skipped_with_reason)."""
    tables = page.find_tables()
    if not tables:
        return [], []
    rows = tables[0].extract() or []
    out: list[dict] = []
    skipped: list[dict] = []

    def append_row(code: str, label_fr: str, amount: Decimal) -> None:
        out.append(
            {
                "row_type": "be_vehicule_remplacement_per_type_per_day_amount",
                "vehicle_type_code": code,
                "vehicle_type_label_fr": label_fr,
                "daily_amount_min": str(amount),
                "daily_amount_mid": str(amount),
                "daily_amount_max": str(amount),
                "currency": "EUR",
                "source_page": VEHICULE_PAGE_FR,
                "source_note": source_note,
            }
        )

    for r in rows[1:]:  # skip header
        if not r or not r[0]:
            continue
        label_lower = (r[0] or "").lower()
        # Cella amount = ultima cella non vuota
        last_cell = ""
        for cell in reversed(r):
            if cell and cell.strip():
                last_cell = cell
                break

        # Caso speciale 1: remorque (sub-rows)
        if "remorque de voiture" in label_lower or (
            "remorque" in label_lower and "750" in label_lower
        ):
            amounts = [parse_eur_amount(line) for line in last_cell.split("\n") if line.strip()]
            amounts = [a for a in amounts if a is not None]
            if len(amounts) >= 2:
                for (code, label_fr, _hint), amt in zip(
                    REMORQUE_SUBROWS, amounts[:2], strict=False
                ):
                    append_row(code, label_fr, amt)
                continue

        # Caso speciale 2: autobus / autocar (5 sub-rows)
        if "autobus" in label_lower or "autocar" in label_lower:
            amounts = [parse_eur_amount(line) for line in last_cell.split("\n") if line.strip()]
            amounts = [a for a in amounts if a is not None]
            if len(amounts) >= 5:
                for (code, label_fr), amt in zip(AUTOBUS_SUBROWS, amounts[:5], strict=False):
                    append_row(code, label_fr, amt)
                continue

        # Caso speciale 3: formula (camions ≥ 3,5 t — "+ X par tonne")
        if "+" in last_cell and ("tonne" in last_cell.lower() or "ton" in last_cell.lower()):
            skipped.append(
                {
                    "label": normalize_ws(r[0]),
                    "amount_text": normalize_ws(last_cell),
                    "reason": "formula_amount_per_ton — non auto-estraibile come single rate",
                }
            )
            continue

        # Caso ordinario: 1 amount per riga
        amount = parse_eur_amount(last_cell)
        if amount is None:
            continue
        # Lookup
        match = None
        for sub, code, label_fr in VEHICULE_MAP:
            if sub in label_lower:
                match = (code, label_fr)
                break
        if match is None:
            skipped.append(
                {
                    "label": normalize_ws(r[0]),
                    "amount_text": normalize_ws(last_cell),
                    "reason": "no_mapping",
                }
            )
            continue
        code, label_fr = match
        append_row(code, label_fr, amount)
    return out, skipped


# ---------- main ------------------------------------------------------------


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
        souffrances = extract_souffrances_endurees(pdf.pages[SOUFFRANCES_PAGE - 1], source_note)
        esthetique = extract_esthetique(pdf, source_note)
        deces = extract_deces_affection(pdf.pages[DECES_PAGE_FR - 1], source_note)
        vehicule, vehicule_skipped = extract_vehicule(pdf.pages[VEHICULE_PAGE_FR - 1], source_note)

    souffrances_fields = [
        "row_type",
        "severity_code",
        "severity_label_fr",
        "victim_age_min",
        "victim_age_max",
        "amount_min",
        "amount_mid",
        "amount_max",
        "currency",
        "source_page",
        "source_note",
    ]
    esthetique_fields = [
        "row_type",
        "severity_code",
        "severity_label_fr",
        "victim_age_min",
        "victim_age_max",
        "annual_amount",
        "currency",
        "source_page",
        "source_note",
    ]
    deces_fields = [
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
    vehicule_fields = [
        "row_type",
        "vehicle_type_code",
        "vehicle_type_label_fr",
        "daily_amount_min",
        "daily_amount_mid",
        "daily_amount_max",
        "currency",
        "source_page",
        "source_note",
    ]

    write_csv(
        OUTPUT_DIR / "be-ti-2020-souffrances-endurees.csv",
        souffrances,
        souffrances_fields,
    )
    write_csv(
        OUTPUT_DIR / "be-ti-2020-prejudice-esthetique.csv",
        esthetique,
        esthetique_fields,
    )
    write_csv(
        OUTPUT_DIR / "be-ti-2020-prejudice-deces-affection.csv",
        deces,
        deces_fields,
    )
    write_csv(
        OUTPUT_DIR / "be-ti-2020-vehicule-remplacement.csv",
        vehicule,
        vehicule_fields,
    )

    summary = {
        "iter": "F-belgium-extraction-ti-2020 · iter1",
        "pdf_path": str(PDF_PATH.relative_to(ROOT)),
        "pdf_sha256": pdf_sha256,
        "totals": {
            "souffrances_endurees_rows": len(souffrances),
            "esthetique_rows": len(esthetique),
            "deces_affection_rows": len(deces),
            "vehicule_rows": len(vehicule),
            "vehicule_skipped": len(vehicule_skipped),
        },
        "vehicule_skipped_detail": vehicule_skipped,
        "warnings": [
            (
                "p.22-23 ('be-ti-2020-prejudice-esthetique.csv'): la tabella "
                "BE 2020 a p.22-23 è in realtà l'INDENNITÀ FORFETARIA per "
                "anno per 1% incapacité (sezione 3.7. Tableau des indemnités "
                "forfaitaires), NON un préjudice esthétique in senso stretto. "
                "Il filename rispetta lo spec utente; il row_type "
                "'be_indemnite_forfaitaire_per_age_annual_amount' riflette il "
                "contenuto reale. Vedi BELGIUM_TI_2020_EXTRACTION_REPORT.md."
            ),
            (
                "Il préjudice esthétique BE 2020 condivide la stessa scala "
                "Julin di souffrances endurées (douleur/pijn) — vedi sezione "
                "3.4.1.2.b. Mornet francese fa lo stesso. Lo Studio deve "
                "decidere se trattare i 2 préjudices con la stessa tabella o "
                "se il barème esthétique BE è altrove."
            ),
        ],
        "files_written": [
            "be-ti-2020-souffrances-endurees.csv",
            "be-ti-2020-prejudice-esthetique.csv",
            "be-ti-2020-prejudice-deces-affection.csv",
            "be-ti-2020-vehicule-remplacement.csv",
        ],
    }
    (OUTPUT_DIR / "extraction_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"[OK] PDF sha256 = {pdf_sha256}")
    print(
        f"[OK] Souffrances endurées (p.{SOUFFRANCES_PAGE}): "
        f"{len(souffrances)} rows (atteso 63 = 9 ages x 7 severities)"
    )
    print(
        f"[OK] 'Esthétique' = indennità forfetaria (p.22-23): "
        f"{len(esthetique)} rows (atteso 71)"
    )
    print(f"[OK] Décès / affection (p.{DECES_PAGE_FR}): " f"{len(deces)} rows (atteso 13)")
    print(
        f"[OK] Véhicule de remplacement (p.{VEHICULE_PAGE_FR}): "
        f"{len(vehicule)} rows + {len(vehicule_skipped)} scartate"
    )
    if vehicule_skipped:
        print("  [INFO] véhicule scartati:")
        for s in vehicule_skipped:
            print(f"    - {s['label'][:60]}... -> {s['reason']}")
    print(f"[OK] CSV scritti in {OUTPUT_DIR.relative_to(ROOT)} (gitignored)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
