"""
OCR SPIKE READ-ONLY del Tableau Indicatif belge 2024.

Iter: F-belgium-ocr-ti-2024-spike · iter1
Stato: read-only / proof-of-concept. Non importa nel DB. Non
genera CSV finali. Non scrive valori OCR come approved.

Obiettivo:
    Verificare se l'estrazione automatica via OCR (Tesseract) è
    praticabile sul PDF be-tableau-indicatif-2024.pdf, che è
    interamente image-scanned (0 testo estraibile in pdfplumber).

Strategia:
    1. Verifica SHA-256 del PDF contro il manifest.
    2. Conferma image-scanned (chars=0, immagini=1 per pagina).
    3. Per le 3 pagine campione (p.9, p.14, p.17), renderizza
       in PNG ad alta risoluzione (300 DPI) usando pdfplumber.
       Sotto cofano pdfplumber sfrutta il proprio backend di
       rendering — NON viene installato pdf2image / poppler.
    4. Esegue Tesseract via subprocess sui PNG.
       NB: solo il pacco lingua 'eng' è installato sul sistema.
       FRA/NLD non sono presenti — questa è una limitazione
       da segnalare al Studio.
    5. Salva PNG + TXT raw OCR sotto
       legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/
       (gitignored).
    6. Genera spike_summary.json con metriche di qualità grezze
       per pagina (cifre rilevate, possibili errori comuni, ecc.).

Pagine campione:
    p.9  → Préjudice esthétique permanent (Julin × age band).
           Equivalente strutturale alla tabella 2020 «souffrances
           endurées» p.17.
    p.14 → Décès / préjudice d'affection (5 relazioni × min/max).
    p.17 → Véhicule de remplacement (€/jour per tipo veicolo).

Uso:
    .venv/Scripts/python.exe scripts/legal_data/ocr_belgium_ti_2024_spike.py

Exit code:
    0 = spike eseguito con successo (anche se OCR di bassa qualità,
        purché il workflow tecnico funzioni).
    1 = errore tecnico (PDF mancante, hash mismatch, tooling
        irrecuperabile).
"""

from __future__ import annotations

import hashlib
import json
import pathlib
import re
import shutil
import subprocess
import sys
from datetime import UTC, datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]
PDF_PATH = (
    ROOT / "legal_data" / "sources" / "belgium" / "downloaded" / "be-tableau-indicatif-2024.pdf"
)
MANIFEST_PATH = (
    ROOT / "legal_data" / "sources" / "belgium" / "downloaded" / "download_manifest.json"
)
SLUG = "be-tableau-indicatif-2024"
EXPECTED_SHA256 = "37b0a0b4606ec39638db4a81c6074928c2275a09274a11597b8fb17e03bc3a45"
OUT_DIR = ROOT / "legal_data" / "sources" / "belgium" / "tableau_indicatif_2024" / "ocr_spike"

SAMPLE_PAGES = [
    {
        "pdf_page": 9,
        "family": "prejudice_esthetique_permanent",
        "expected_2020_equivalent": "souffrances_endurees (p.17, Julin × age band)",
        "expected_shape": "9 age bands × 7 severity Julin = 63 cells",
    },
    {
        "pdf_page": 14,
        "family": "deces_affection",
        "expected_2020_equivalent": "deces / prejudice d'affection (p.26-29)",
        "expected_shape": "5+ relations × min/max",
    },
    {
        "pdf_page": 17,
        "family": "vehicule_remplacement",
        "expected_2020_equivalent": "vehicule de remplacement (p.32)",
        "expected_shape": "diversi tipi veicolo × indemnité/jour",
    },
]

DPI = 300

TESSERACT_CANDIDATES = [
    shutil.which("tesseract"),
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
    r"C:\Program Files\Tesseract-OCR\tesseract.EXE",
]


def find_tesseract() -> str | None:
    for c in TESSERACT_CANDIDATES:
        if c and pathlib.Path(c).exists():
            return c
    return None


def list_tesseract_langs(tess: str) -> list[str]:
    try:
        r = subprocess.run([tess, "--list-langs"], capture_output=True, text=True, timeout=15)
        out = (r.stdout or "") + (r.stderr or "")
        langs = []
        for line in out.splitlines():
            line = line.strip()
            if not line or ":" in line or line.startswith("List"):
                continue
            if re.fullmatch(r"[a-z_]{2,}", line):
                langs.append(line)
        return langs
    except Exception:
        return []


def sha256_of(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def confirm_image_scanned(pdf_path: pathlib.Path) -> dict:
    import pdfplumber

    info: dict = {"pages": 0, "per_page": []}
    with pdfplumber.open(str(pdf_path)) as pdf:
        info["pages"] = len(pdf.pages)
        total_chars = 0
        total_images = 0
        for i, page in enumerate(pdf.pages, start=1):
            chars = len(page.chars)
            imgs = len(page.images)
            total_chars += chars
            total_images += imgs
            info["per_page"].append({"page": i, "chars": chars, "images": imgs})
        info["total_chars"] = total_chars
        info["total_images"] = total_images
        info["is_image_scanned"] = total_chars == 0 and total_images > 0
    return info


def render_page_png(pdf_path: pathlib.Path, page_num: int, dpi: int, out_png: pathlib.Path) -> None:
    import pdfplumber

    with pdfplumber.open(str(pdf_path)) as pdf:
        page = pdf.pages[page_num - 1]
        page.to_image(resolution=dpi).save(str(out_png), format="PNG")


def run_ocr(tess: str, png_path: pathlib.Path, out_stem: pathlib.Path, lang: str) -> str:
    """Esegue tesseract e ritorna il testo letto dal file <stem>.txt.

    PSM 4 = «single column of text of variable sizes». Empiricamente
    funziona meglio di PSM 6 sulle tabelle del Tableau Indicatif: PSM 6
    perde righe quando le celle sono sparse (vedi BELGIUM_TI_2024_OCR_SPIKE_REPORT
    per il confronto PSM 6 vs PSM 4).
    """
    cmd = [tess, str(png_path), str(out_stem), "-l", lang, "--psm", "4"]
    subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    txt_path = out_stem.with_suffix(".txt")
    if not txt_path.exists():
        return ""
    return txt_path.read_text(encoding="utf-8", errors="replace")


_AMOUNT_RE = re.compile(r"\b\d{1,3}(?:[.\s,]\d{3})*(?:,\d{2})?\b")
_ANY_NUM_RE = re.compile(r"\b\d+(?:[.,]\d+)?\b")
_EUR_RE = re.compile(r"euros?\b|€", re.IGNORECASE)


def assess_quality(text: str, family: str) -> dict:
    """Metriche grezze di qualità OCR — non bloccanti, solo informative."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    nonempty_lines = len(lines)

    eur_hits = len(_EUR_RE.findall(text))
    amount_hits = len(_AMOUNT_RE.findall(text))
    any_num_hits = len(_ANY_NUM_RE.findall(text))

    suspicious_patterns = {
        "comma_in_thousands": len(re.findall(r"\d,\d{3}\b", text)),
        "fused_unit_curos": text.lower().count("curos"),
        "fused_unit_cures": text.lower().count("cures"),
        "fused_unit_euros_ok": text.lower().count("euros"),
        "missing_dash_age_band": len(re.findall(r"\b\d{1,2}\.\d{2}\b", text)),
        "weird_punctuation_braces": text.count("{") + text.count("}"),
    }

    digits_per_nonempty_line = (any_num_hits / nonempty_lines) if nonempty_lines else 0

    family_specific: dict = {}
    if family == "prejudice_esthetique_permanent":
        age_band_pattern = re.compile(r"\b(\d{1,2})\s*[-‐–—.]\s*(\d{2})\b")
        bands = age_band_pattern.findall(text)
        family_specific = {
            "age_bands_detected": len(bands),
            "age_bands_expected_min": 8,
            "julin_keyword": "julin" in text.lower() or "Julin" in text,
            "severity_labels_seen": [
                kw
                for kw in [
                    "minime",
                    "très léger",
                    "trésléger",
                    "léger",
                    "moyen",
                    "grave",
                    "très grave",
                    "trésgrave",
                    "exception",
                ]
                if kw in text.lower()
            ],
        }
    elif family == "deces_affection":
        family_specific = {
            "relation_keywords_seen": [
                kw
                for kw in [
                    "partenaire",
                    "parents",
                    "enfants",
                    "frères",
                    "freres",
                    "soeurs",
                    "grands-parents",
                    "petits-enfants",
                    "fausse couche",
                ]
                if kw in text.lower()
            ],
            "min_max_pairs_estimate": len(
                re.findall(
                    r"\d[\.,\d ]*\s*euros[^\n]{0,80}\d[\.,\d ]*\s*euros", text, re.IGNORECASE
                )
            ),
        }
    elif family == "vehicule_remplacement":
        family_specific = {
            "vehicle_keywords_seen": [
                kw
                for kw in [
                    "bicyclette",
                    "remorque",
                    "voiture",
                    "moto",
                    "camion",
                    "autobus",
                    "tracteur",
                    "pédélec",
                    "pedelec",
                    "quad",
                    "speed",
                ]
                if kw in text.lower()
            ],
            "indemnite_per_day_hits": len(
                re.findall(r"\d+[,.]\d{2}\s*euros?\s*/?\s*jour", text, re.IGNORECASE)
            )
            + len(re.findall(r"indemnit[eé][^\n]{0,40}jour", text, re.IGNORECASE)),
        }

    return {
        "nonempty_lines": nonempty_lines,
        "char_count": len(text),
        "eur_hits": eur_hits,
        "amount_hits": amount_hits,
        "any_num_hits": any_num_hits,
        "digits_per_nonempty_line": round(digits_per_nonempty_line, 2),
        "suspicious_patterns": suspicious_patterns,
        "family_specific": family_specific,
    }


def main() -> int:
    print("=" * 70)
    print("OCR SPIKE — BE Tableau Indicatif 2024 (read-only / candidate)")
    print(f"PDF: {PDF_PATH}")
    print("=" * 70)

    if not PDF_PATH.exists():
        print(f"[FATAL] PDF non trovato: {PDF_PATH}")
        return 1

    # 1. SHA-256 + manifest
    print("\n1. Verifica SHA-256")
    actual_sha = sha256_of(PDF_PATH)
    print(f"  computed : {actual_sha}")
    print(f"  expected : {EXPECTED_SHA256}")
    sha_ok = actual_sha == EXPECTED_SHA256
    print(f"  match    : {'PASS' if sha_ok else 'FAIL'}")
    manifest_sha = None
    if MANIFEST_PATH.exists():
        try:
            mf = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
            for item in mf.get("items", []):
                if item.get("slug") == SLUG:
                    manifest_sha = item.get("sha256")
                    break
            print(f"  manifest : {manifest_sha}")
            if manifest_sha and manifest_sha != actual_sha:
                print("  [WARN] manifest SHA differente da quello computato")
        except Exception as e:
            print(f"  [WARN] manifest non leggibile: {e}")

    if not sha_ok:
        print("\n[FATAL] hash mismatch — interrompo per non operare su PDF sbagliato.")
        return 1

    # 2. Conferma image-scanned
    print("\n2. Conferma image-scanned")
    img_info = confirm_image_scanned(PDF_PATH)
    print(f"  pagine totali       : {img_info['pages']}")
    print(f"  testo estraibile    : {img_info['total_chars']} char (atteso ~0)")
    print(f"  immagini totali     : {img_info['total_images']}")
    print(f"  is_image_scanned    : {img_info['is_image_scanned']}")

    # 3. Tesseract availability
    print("\n3. Tooling OCR")
    tess = find_tesseract()
    if not tess:
        print("  [FATAL] tesseract non trovato (né su PATH né nei percorsi noti).")
        print("  Installazione richiesta: https://github.com/UB-Mannheim/tesseract/wiki")
        return 1
    print(f"  tesseract           : {tess}")
    langs = list_tesseract_langs(tess)
    print(f"  lingue installate   : {langs}")
    has_fra = "fra" in langs
    has_nld = "nld" in langs
    has_eng = "eng" in langs
    print(f"  fra disponibile     : {has_fra}")
    print(f"  nld disponibile     : {has_nld}")
    print(f"  eng disponibile     : {has_eng}")

    if not has_eng and not has_fra and not has_nld:
        print("  [FATAL] nessuna lingua utile installata (eng/fra/nld).")
        return 1

    use_lang = "eng"
    if has_fra:
        use_lang = "fra+eng" if has_eng else "fra"
    if has_fra and has_nld:
        use_lang = "fra+nld"
    print(f"  lang scelta         : {use_lang}")
    if not has_fra:
        print("  [WARN] pacchetto 'fra' NON installato. La qualità OCR sarà degradata")
        print("         (accenti, riconoscimento parole francesi). Documentato in report.")

    # 4. Render + OCR sample pages
    print("\n4. Render + OCR pagine campione")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    spike_results = []
    for sample in SAMPLE_PAGES:
        pn = sample["pdf_page"]
        print(f"\n  -- p.{pn} ({sample['family']}) --")
        png = OUT_DIR / f"be-ti-2024-p{pn:02d}.png"
        stem = OUT_DIR / f"be-ti-2024-p{pn:02d}"
        try:
            render_page_png(PDF_PATH, pn, DPI, png)
            print(f"     PNG: {png.name} ({png.stat().st_size} bytes, {DPI} DPI)")
        except Exception as e:
            print(f"     [ERROR] render fallito: {e}")
            spike_results.append({**sample, "render_ok": False, "error": str(e)})
            continue

        try:
            text = run_ocr(tess, png, stem, use_lang)
        except subprocess.TimeoutExpired:
            print("     [ERROR] tesseract timeout")
            spike_results.append({**sample, "render_ok": True, "ocr_ok": False})
            continue
        except Exception as e:
            print(f"     [ERROR] tesseract fallito: {e}")
            spike_results.append({**sample, "render_ok": True, "ocr_ok": False, "error": str(e)})
            continue

        print(f"     TXT: {stem.with_suffix('.txt').name} ({len(text)} char)")
        quality = assess_quality(text, sample["family"])
        print(f"     righe non vuote   : {quality['nonempty_lines']}")
        print(f"     hit 'euros|€'     : {quality['eur_hits']}")
        print(f"     amount detected   : {quality['amount_hits']}")
        print(f"     digit/line        : {quality['digits_per_nonempty_line']}")
        sp = quality["suspicious_patterns"]
        print(f"     comma-thousands   : {sp['comma_in_thousands']}")
        print(f"     'curos' typo      : {sp['fused_unit_curos']}")
        print(f"     'cures' typo      : {sp['fused_unit_cures']}")
        print(f"     'euros' ok        : {sp['fused_unit_euros_ok']}")
        print(f"     family-specific   : {quality['family_specific']}")
        spike_results.append(
            {
                **sample,
                "render_ok": True,
                "ocr_ok": True,
                "png_path_relative": str(png.relative_to(ROOT)).replace("\\", "/"),
                "txt_path_relative": str(stem.with_suffix(".txt").relative_to(ROOT)).replace(
                    "\\", "/"
                ),
                "quality": quality,
            }
        )

    # 5. Spike summary JSON
    summary = {
        "iter": "F-belgium-ocr-ti-2024-spike/iter1",
        "generated_at": datetime.now(UTC).isoformat(),
        "pdf": {
            "slug": SLUG,
            "path_relative": str(PDF_PATH.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": PDF_PATH.stat().st_size,
            "sha256_actual": actual_sha,
            "sha256_expected": EXPECTED_SHA256,
            "sha256_manifest": manifest_sha,
            "sha256_match": sha_ok,
        },
        "image_scanned": img_info,
        "tooling": {
            "tesseract_path": tess,
            "tesseract_langs_installed": langs,
            "lang_used": use_lang,
            "has_fra": has_fra,
            "has_nld": has_nld,
            "has_eng": has_eng,
            "warning_no_fra": not has_fra,
        },
        "dpi": DPI,
        "sample_pages": spike_results,
        "scope": (
            "Read-only spike. Nessun CSV finale, nessun import DB, "
            "nessuna creazione di LegalReview/CompensationDataset/CalculationFormula. "
            "Output destinati a essere review-ati dal Studio."
        ),
    }
    summary_path = OUT_DIR / "spike_summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n5. Summary scritto: {summary_path.relative_to(ROOT)}")
    print("=" * 70)
    print("OCR SPIKE COMPLETATO — vedere report markdown per analisi qualitativa.")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
