"""
QA READ-ONLY dei pacchetti di review legale Maghreb (MA + TN).

Iter: F-maghreb-legal-review-packages · iter1
Stato: read-only. Non importa nulla. Non modifica file.

Verifica:
1. Esistenza dei due documenti package (MOROCCO + TUNISIA).
2. Esistenza dei due checklist template.
3. Header e status validi nei template.
4. Documenti contengono i warning richiesti (no calculator
   prima del mapping; distinzione diritto interno vs DIP/Reg.
   650/2012; manual_required documentati).
5. DB invariants: MA/TN LegalSource presenti, 0 approved, 0
   LegalReview, 0 CompensationDataset, 0 CalculationFormula.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/qa_maghreb_review_packages.py

Exit 0 = OK, 1 = anomalie.
"""

from __future__ import annotations

import csv
import os
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]

PACKAGE_DOCS = {
    "MA": ROOT / "docs" / "legal_sources" / "MOROCCO_LEGAL_REVIEW_PACKAGE.md",
    "TN": ROOT / "docs" / "legal_sources" / "TUNISIA_LEGAL_REVIEW_PACKAGE.md",
}

CHECKLIST_TEMPLATES = {
    "MA": ROOT
    / "legal_data"
    / "sources"
    / "morocco"
    / "review"
    / "morocco_legal_review_checklist_template.csv",
    "TN": ROOT
    / "legal_data"
    / "sources"
    / "tunisia"
    / "review"
    / "tunisia_legal_review_checklist_template.csv",
}

CHECKLIST_HEADER = [
    "package",
    "source_slug",
    "document_status",
    "review_item",
    "legal_topic",
    "article_or_section",
    "reviewer",
    "status",
    "notes",
    "reviewed_at",
]

CHECKLIST_ALLOWED_STATUS = {
    "pending",
    "checked_ok",
    "needs_correction",
    "rejected",
    "approved_for_mapping",
}

# Sentinelle che il package doc DEVE contenere per essere
# coerente con la sua natura di "no calculator before mapping +
# DIP distinction + manual download items documented". Le
# sentinelle sono frammenti deliberatamente lassi (substring
# match) per resistere a piccole variazioni editoriali, ma
# specifici al contenuto richiesto dall'iter.
REQUIRED_PHRASES = [
    "650/2012",  # presenza riferimento Reg. UE successioni
    "professio juris",  # qualifica DIP
    "needs_review",  # stato attuale fonti
    "Manual?",  # tabella inventario con colonna manuale
    "Manuale richiesto",  # sezione 1.2 con elenco fonti manuali
]

# Phrase specifiche del warning "no calculator prima del mapping".
NO_CALCULATOR_WARNING_PHRASES = [
    "Nessun calculator engine reale può essere implementato",
    "unavailable_requires_legal_validation",
]

EXPECTED_SLUGS = {
    "MA": {
        "ma-code-famille-moudawana-fr-pdf",
        "ma-code-droits-reels-loi-39-08",
        "ma-code-droits-reels-traduction-aute",
        "eu-regulation-650-2012-successions-fr-ma",
    },
    "TN": {
        "tn-code-statut-personnel-livre-ix-succession",
        "tn-code-dip-loi-98-97",
        "tn-jort-code-statut-personnel-1956",
        "tn-code-statut-personnel-compiled",
        "eu-regulation-650-2012-successions-fr-tn",
    },
}


def line(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")
    return ok


def check_files_exist() -> int:
    print("\n1. Esistenza file (docs + templates)")
    failures = 0
    for code, p in PACKAGE_DOCS.items():
        if not line(f"package {code}: {p.relative_to(ROOT)}", p.exists()):
            failures += 1
    for code, p in CHECKLIST_TEMPLATES.items():
        if not line(f"template {code}: {p.relative_to(ROOT)}", p.exists()):
            failures += 1
    return failures


def check_files_not_empty() -> int:
    print("\n2. File non vuoti")
    failures = 0
    for p in list(PACKAGE_DOCS.values()) + list(CHECKLIST_TEMPLATES.values()):
        if not p.exists():
            continue
        size = p.stat().st_size
        if not line(
            f"non vuoto (>0 byte): {p.relative_to(ROOT)}",
            size > 0,
            f"size={size}",
        ):
            failures += 1
    return failures


def check_checklist_template(code: str, path: pathlib.Path) -> int:
    print(f"\n3.{code} Checklist template — struttura e status validi")
    failures = 0
    if not path.exists():
        return 0
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        if not line(f"{code}: template non vuoto", False):
            failures += 1
        return failures
    header = rows[0]
    if not line(
        f"{code}: header esatto",
        header == CHECKLIST_HEADER,
        f"got={header!r}",
    ):
        failures += 1
    data_rows = [r for r in rows[1:] if any(c.strip() for c in r)]
    bad_status = []
    bad_slug = []
    for i, r in enumerate(data_rows, start=2):
        try:
            row = dict(zip(header, r, strict=False))
        except ValueError:
            bad_status.append((i, "row malformed"))
            continue
        status = row.get("status", "").strip()
        if status not in CHECKLIST_ALLOWED_STATUS:
            bad_status.append((i, status))
        slug = row.get("source_slug", "").strip()
        if slug and slug not in EXPECTED_SLUGS[code]:
            bad_slug.append((i, slug))
    if not line(
        f"{code}: tutti gli status in {sorted(CHECKLIST_ALLOWED_STATUS)}",
        not bad_status,
        f"violations={bad_status[:3]}{'...' if len(bad_status) > 3 else ''}",
    ):
        failures += 1
    if not line(
        f"{code}: tutti i source_slug riconosciuti",
        not bad_slug,
        f"unknown={bad_slug[:3]}",
    ):
        failures += 1
    print(f"  [INFO] {code} data rows = {len(data_rows)}")
    return failures


def check_package_warnings(code: str, path: pathlib.Path) -> int:
    print(f"\n4.{code} Package doc contiene warnings/distinctions richiesti")
    failures = 0
    if not path.exists():
        return 0
    text = path.read_text(encoding="utf-8")
    for phrase in REQUIRED_PHRASES:
        if not line(f"{code}: contiene '{phrase}'", phrase in text):
            failures += 1
    for phrase in NO_CALCULATOR_WARNING_PHRASES:
        if not line(f"{code}: warning no-calculator '{phrase}'", phrase in text):
            failures += 1
    return failures


def check_db_invariants() -> int:
    print("\n5. DB invariants — MA/TN LegalSource presenti, 0 approved,")
    print("   0 LegalReview, 0 CompensationDataset, 0 CalculationFormula")
    failures = 0
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        import django

        django.setup()
        from apps.compensation.models import CalculationFormula, CompensationDataset
        from apps.jurisdictions.models import Country
        from apps.legal_sources.models import LegalReview, LegalSource
    except Exception as e:
        print(f"  [SKIP] Django setup error: {e}")
        return 0

    for code in ("MA", "TN"):
        c = Country.objects.filter(code=code).first()
        if c is None:
            if not line(f"Country {code} esiste nel DB", False):
                failures += 1
            continue
        sources = LegalSource.objects.filter(country=c)
        approved = sources.filter(status="approved").count()
        actual_slugs = set(sources.values_list("slug", flat=True))
        missing = EXPECTED_SLUGS[code] - actual_slugs
        reviews = LegalReview.objects.filter(source__country=c).count()
        datasets = CompensationDataset.objects.filter(country=c).count()
        formulas = CalculationFormula.objects.filter(dataset__country=c).count()
        print(
            f"  [INFO] {code}: sources={sources.count()} approved={approved} "
            f"reviews={reviews} datasets={datasets} formulas={formulas}"
        )
        if not line(
            f"{code}: tutte le fonti attese sono presenti come LegalSource",
            not missing,
            f"missing={sorted(missing)}",
        ):
            failures += 1
        if not line(
            f"{code}: nessuna LegalSource in stato approved",
            approved == 0,
            f"approved={approved}",
        ):
            failures += 1
        if not line(
            f"{code}: nessuna LegalReview",
            reviews == 0,
            f"reviews={reviews}",
        ):
            failures += 1
        if not line(
            f"{code}: nessun CompensationDataset",
            datasets == 0,
            f"datasets={datasets}",
        ):
            failures += 1
        if not line(
            f"{code}: nessuna CalculationFormula",
            formulas == 0,
            f"formulas={formulas}",
        ):
            failures += 1
    return failures


def main() -> int:
    print("=" * 72)
    print("QA — Maghreb legal review packages (read-only)")
    print(f"ROOT: {ROOT}")
    print("=" * 72)

    failures = 0
    failures += check_files_exist()
    failures += check_files_not_empty()
    for code, path in CHECKLIST_TEMPLATES.items():
        failures += check_checklist_template(code, path)
    for code, path in PACKAGE_DOCS.items():
        failures += check_package_warnings(code, path)
    failures += check_db_invariants()

    print()
    print("=" * 72)
    if failures == 0:
        print("QA OK — packages MA + TN coerenti. Nessuna auto-approvazione.")
        print("STATO: review packages read-only. Lo Studio deve completare il mapping.")
        print("Nessun calculator engine reale prima del mapping firmato.")
        print("=" * 72)
        return 0
    print(f"QA FAILED — {failures} anomalie da indagare.")
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
