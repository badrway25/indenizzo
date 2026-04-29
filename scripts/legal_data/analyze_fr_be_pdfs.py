"""
Analisi READ-ONLY dei 4 PDF FR + BE per il planning di estrazione
F-france-belgium-extraction-planning.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/analyze_fr_be_pdfs.py

Non importa nulla nel DB. Non scrive file. Stampa solo a stdout:
- numero pagine
- pagine sospette di tabella (>= 3 righe con >= 2 colonne)
- prime 60 chars del testo della prima pagina di ciascuna sezione
- conteggio token per parole-chiave (Mornet/Gazette/Tableau Indicatif)

Richiede pdfplumber.
"""

from __future__ import annotations

import hashlib
import pathlib
import re
import sys

import pdfplumber

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PDFS = [
    (
        "FR",
        "fr-referentiel-mornet-2024",
        "legal_data/sources/france/downloaded/fr-referentiel-mornet-2024.pdf",
    ),
    (
        "FR",
        "fr-bareme-capitalisation-gazette-palais-2022",
        "legal_data/sources/france/downloaded/fr-bareme-capitalisation-gazette-palais-2022.pdf",
    ),
    (
        "BE",
        "be-tableau-indicatif-2024",
        "legal_data/sources/belgium/downloaded/be-tableau-indicatif-2024.pdf",
    ),
    (
        "BE",
        "be-tableau-indicatif-2020",
        "legal_data/sources/belgium/downloaded/be-tableau-indicatif-2020.pdf",
    ),
]

KEYWORDS = {
    "mornet": [
        "DFP",
        "déficit fonctionnel permanent",
        "souffrances endurées",
        "préjudice esthétique",
        "préjudice d'agrément",
        "perte de gains",
        "tierce personne",
        "DFT",
        "barème",
        "Dintilhac",
    ],
    "gazette": [
        "capitalisation",
        "euro de rente",
        "viager",
        "espérance de vie",
        "TGI",
        "INSEE",
        "table de mortalité",
        "taux d'actualisation",
        "barème",
    ],
    "tableau_indicatif": [
        "incapacité",
        "invalidité",
        "ITT",
        "IPP",
        "préjudice",
        "morale",
        "ménager",
        "économique",
        "consolidation",
        "douleurs",
        "esthétique",
        "agrément",
        "scolaire",
        "sexuel",
        "deuil",
        "survivants",
    ],
}


def sha256(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def is_table_page(page) -> bool:
    try:
        tables = page.find_tables()
    except Exception:
        return False
    if not tables:
        return False
    for t in tables:
        rows = t.extract() or []
        if len(rows) >= 3 and any(len(r) >= 2 for r in rows):
            return True
    return False


def analyze(country: str, slug: str, path: str) -> None:
    p = pathlib.Path(path)
    if not p.exists():
        print(f"[{country}] {slug}: FILE NOT FOUND ({path})")
        return
    print("=" * 78)
    print(f"[{country}] {slug}")
    print(f"  path: {path}")
    print(f"  size: {p.stat().st_size:,} bytes")
    print(f"  sha256: {sha256(p)}")

    with pdfplumber.open(p) as pdf:
        n_pages = len(pdf.pages)
        print(f"  pages: {n_pages}")

        kw_keys = (
            "mornet"
            if "mornet" in slug
            else "gazette" if "gazette" in slug else "tableau_indicatif"
        )
        kw_list = KEYWORDS[kw_keys]
        kw_counts = {k: 0 for k in kw_list}
        table_pages: list[int] = []
        sample_texts: dict[int, str] = {}

        for i, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            for k in kw_list:
                kw_counts[k] += len(re.findall(re.escape(k), text, flags=re.IGNORECASE))
            if is_table_page(page):
                table_pages.append(i)
            if i in (1, 2, 3, max(1, n_pages // 2), n_pages):
                sample_texts[i] = text[:240].replace("\n", " | ")

        print(f"  pages with detected table (>=3 rows, >=2 cols): {len(table_pages)}")
        if table_pages:
            head = table_pages[:25]
            tail = table_pages[-5:] if len(table_pages) > 30 else []
            print(f"    first table pages: {head}")
            if tail:
                print(f"    last table pages: {tail}")
        print("  keyword hits (case-insensitive):")
        for k, c in kw_counts.items():
            if c:
                print(f"    {k!r:38} {c}")
        print("  sample texts:")
        for pg, txt in sample_texts.items():
            print(f"    p.{pg}: {txt[:200]}")


def main() -> int:
    for country, slug, path in PDFS:
        analyze(country, slug, path)
    print("=" * 78)
    print("FINE — analisi read-only, nessuna modifica.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
