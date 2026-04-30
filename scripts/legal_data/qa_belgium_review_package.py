"""
QA READ-ONLY del pacchetto di review legale Belgio.

Iter: F-belgium-legal-review-package · iter1
Stato: read-only. Non importa nulla. Non modifica file.

Verifica:
1. Esistenza dei CSV candidate BE 2020 (4 file).
2. Esistenza dei report doc (BELGIUM_*.md) inclusi extraction
   report e OCR spike report BE 2024.
3. Esistenza del template di review checklist.
4. Tutti i CSV candidate non sono vuoti e dichiarano
   `legal_review_required=true` nella colonna `source_note`.
5. Nessun CSV candidate dichiara `no_human_legal_approval=false`
   (sarebbe un'auto-approvazione vietata).
6. Nessuna `LegalSource` BE già `approved` nel DB.
7. Il package doc contiene i warning espliciti su BE 2024 OCR
   non pronto e sul flag historical_fallback per BE 2020.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/qa_belgium_review_package.py

Exit 0 = OK, 1 = anomalie. NON cancella nulla.
"""

from __future__ import annotations

import csv
import os
import pathlib
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]

CANDIDATE_CSVS = [
    ROOT
    / "legal_data"
    / "sources"
    / "belgium"
    / "tableau_indicatif_2020"
    / "be-ti-2020-souffrances-endurees.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "belgium"
    / "tableau_indicatif_2020"
    / "be-ti-2020-prejudice-esthetique.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "belgium"
    / "tableau_indicatif_2020"
    / "be-ti-2020-prejudice-deces-affection.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "belgium"
    / "tableau_indicatif_2020"
    / "be-ti-2020-vehicule-remplacement.csv",
]

REPORTS = [
    ROOT / "docs" / "legal_sources" / "BELGIUM_EXTRACTION_PLANNING.md",
    ROOT / "docs" / "legal_sources" / "BELGIUM_TI_2020_EXTRACTION_REPORT.md",
    ROOT / "docs" / "legal_sources" / "BELGIUM_TI_2024_OCR_SPIKE_REPORT.md",
    ROOT / "docs" / "legal_sources" / "BELGIUM_LEGAL_REVIEW_PACKAGE.md",
]

PACKAGE_DOC = ROOT / "docs" / "legal_sources" / "BELGIUM_LEGAL_REVIEW_PACKAGE.md"

CHECKLIST_TEMPLATE = (
    ROOT
    / "legal_data"
    / "sources"
    / "belgium"
    / "review"
    / "belgium_legal_review_checklist_template.csv"
)

CHECKLIST_HEADER = [
    "package",
    "source_slug",
    "csv_path",
    "review_item",
    "sample_size",
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
    "approved_for_import",
}

# Sentinelle che il package doc DEVE contenere per essere coerente
# con la sua natura di "warning BE 2024 not ready" + "historical
# fallback BE 2020". Se mancano, è il segnale che il documento è
# stato editato perdendo l'avvertenza.
REQUIRED_PACKAGE_PHRASES = [
    "BE 2024 NON è oggi pronto",
    "historical_fallback",
    "no_human_legal_approval",
    "source_is_historical_2020",
]


def line(label: str, ok: bool, detail: str = "") -> bool:
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")
    return ok


def check_files_exist() -> int:
    print("\n1. Esistenza file")
    failures = 0
    for p in CANDIDATE_CSVS:
        if not line(f"CSV esiste: {p.relative_to(ROOT)}", p.exists()):
            failures += 1
    for p in REPORTS:
        if not line(f"Report esiste: {p.relative_to(ROOT)}", p.exists()):
            failures += 1
    if not line(
        f"Template checklist esiste: {CHECKLIST_TEMPLATE.relative_to(ROOT)}",
        CHECKLIST_TEMPLATE.exists(),
    ):
        failures += 1
    return failures


def check_files_not_empty() -> int:
    print("\n2. File non vuoti")
    failures = 0
    for p in CANDIDATE_CSVS + REPORTS + [CHECKLIST_TEMPLATE]:
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


def check_source_note_flags() -> int:
    print("\n3. source_note flags coerenti (legal_review_required=true,")
    print("   no_human_legal_approval != false)")
    failures = 0
    for p in CANDIDATE_CSVS:
        if not p.exists():
            continue
        with p.open(encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if "source_note" not in (reader.fieldnames or []):
                if not line(
                    f"colonna source_note presente: {p.name}",
                    False,
                    f"fieldnames={reader.fieldnames}",
                ):
                    failures += 1
                continue
            rows_total = 0
            rows_missing_required = 0
            rows_with_auto_approve = 0
            for row in reader:
                rows_total += 1
                note = row.get("source_note", "") or ""
                if "legal_review_required=true" not in note:
                    rows_missing_required += 1
                if "no_human_legal_approval=false" in note:
                    rows_with_auto_approve += 1
            if not line(
                f"{p.name}: tutte le righe hanno legal_review_required=true",
                rows_missing_required == 0,
                f"missing={rows_missing_required}/{rows_total}",
            ):
                failures += 1
            if not line(
                f"{p.name}: nessuna riga con no_human_legal_approval=false",
                rows_with_auto_approve == 0,
                f"violations={rows_with_auto_approve}/{rows_total}",
            ):
                failures += 1
    return failures


def check_checklist_template() -> int:
    print("\n4. Checklist template — struttura e status validi")
    failures = 0
    if not CHECKLIST_TEMPLATE.exists():
        return 0
    with CHECKLIST_TEMPLATE.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        if not line("template non vuoto", False):
            failures += 1
        return failures
    header = rows[0]
    if not line(
        "header esatto",
        header == CHECKLIST_HEADER,
        f"got={header!r}",
    ):
        failures += 1
    data_rows = [r for r in rows[1:] if any(c.strip() for c in r)]
    bad_status = []
    for i, r in enumerate(data_rows, start=2):
        try:
            status = dict(zip(header, r, strict=False)).get("status", "").strip()
        except ValueError:
            bad_status.append((i, "row malformed"))
            continue
        if status not in CHECKLIST_ALLOWED_STATUS:
            bad_status.append((i, status))
    if not line(
        f"tutti gli status in {sorted(CHECKLIST_ALLOWED_STATUS)}",
        not bad_status,
        f"violations={bad_status[:3]}{'...' if len(bad_status) > 3 else ''}",
    ):
        failures += 1
    print(f"  [INFO] data rows = {len(data_rows)}")
    return failures


def check_package_warnings() -> int:
    print("\n5. Package doc contiene warnings espliciti (BE 2024 not ready,")
    print("   historical_fallback BE 2020)")
    failures = 0
    if not PACKAGE_DOC.exists():
        if not line(f"package doc esiste: {PACKAGE_DOC.relative_to(ROOT)}", False):
            failures += 1
        return failures
    text = PACKAGE_DOC.read_text(encoding="utf-8")
    for phrase in REQUIRED_PACKAGE_PHRASES:
        if not line(
            f"package contiene: '{phrase}'",
            phrase in text,
        ):
            failures += 1
    return failures


def check_db_no_be_approved() -> int:
    print("\n6. DB invariants — nessuna LegalSource BE già approved")
    failures = 0
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        import django

        django.setup()
        from apps.jurisdictions.models import Country
        from apps.legal_sources.models import LegalSource
    except Exception as e:
        print(f"  [SKIP] Django setup error: {e}")
        return 0
    be = Country.objects.filter(code="BE").first()
    if be is None:
        if not line("Country BE esiste nel DB", False):
            failures += 1
        return failures
    be_sources = LegalSource.objects.filter(country=be)
    total = be_sources.count()
    approved = be_sources.filter(status="approved").count()
    needs_review = be_sources.filter(status="needs_review").count()
    print(
        f"  [INFO] BE LegalSource: total={total}, needs_review={needs_review}, approved={approved}"
    )
    if not line(
        "nessuna LegalSource BE è in stato approved",
        approved == 0,
        f"approved={approved}",
    ):
        failures += 1
    expected_slugs = {
        "be-loi-1989-11-21-rc-auto",
        "be-tableau-indicatif-2020",
        "be-tableau-indicatif-2024",
        "be-tables-schryvers-2026-page",
        "be-tables-schryvers-tableurs",
    }
    actual_slugs = set(be_sources.values_list("slug", flat=True))
    missing = expected_slugs - actual_slugs
    if not line(
        "tutte le 5 fonti BE attese sono presenti come LegalSource",
        not missing,
        f"missing={sorted(missing)}",
    ):
        failures += 1
    return failures


def main() -> int:
    print("=" * 72)
    print("QA — Belgium legal review package (read-only)")
    print(f"ROOT: {ROOT}")
    print("=" * 72)

    failures = 0
    failures += check_files_exist()
    failures += check_files_not_empty()
    failures += check_source_note_flags()
    failures += check_checklist_template()
    failures += check_package_warnings()
    failures += check_db_no_be_approved()

    print()
    print("=" * 72)
    if failures == 0:
        print("QA OK — package di review BE coerente. Nessuna auto-approvazione.")
        print("STATO: candidate read-only. Lo Studio deve completare la review.")
        print("BE 2020 = historical_fallback. BE 2024 = OCR/manual review NON pronto.")
        print("=" * 72)
        return 0
    print(f"QA FAILED — {failures} anomalie da indagare.")
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
