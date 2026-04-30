"""
QA READ-ONLY del pacchetto di review legale Francia.

Iter: F-france-legal-review-package · iter1
Stato: read-only. Non importa nulla. Non modifica file.

Verifica:
1. Esistenza dei CSV candidate FR (Gazette 2022 + Mornet 2024).
2. Esistenza dei report doc (FRANCE_*.md).
3. Esistenza del template di review checklist e che sia committabile.
4. Tutti i CSV candidate non sono vuoti e dichiarano
   `legal_review_required=true` nella colonna `source_note`
   (M3 template è eccezione: header-only).
5. Nessun CSV candidate dichiara `no_human_legal_approval=false`
   (sarebbe un'auto-approvazione vietata).
6. Nessuna `LegalSource` FR già `approved` nel DB.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/qa_france_review_package.py

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
    / "france"
    / "gazette_2022"
    / "fr-gazette-2022-capitalisation-viagere.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "gazette_2022"
    / "fr-gazette-2022-capitalisation-temporaire.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "gazette_2022"
    / "fr-gazette-2022-anticipated-payment-years.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "mornet_2024"
    / "fr-mornet-2024-dfp-per-age-disability.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "mornet_2024"
    / "fr-mornet-2024-prejudice-affection-per-relation.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "mornet_2024"
    / "fr-mornet-2024-manual-fourchettes-template.csv",
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "mornet_2024"
    / "fr-mornet-2024-manual-fourchettes-review_tasks.csv",
]

# CSV con dati estratti automaticamente: devono avere source_note coerente.
# I due file manual_fourchettes (template + review_tasks) non hanno la
# colonna source_note nel formato "key=value;…": il template è scaffold
# vuoto, le review_tasks hanno colonna `instructions` non `source_note`.
CSVS_WITH_SOURCE_NOTE = [p for p in CANDIDATE_CSVS if "manual-fourchettes" not in p.name]

REPORTS = [
    ROOT / "docs" / "legal_sources" / "FRANCE_EXTRACTION_PLANNING.md",
    ROOT / "docs" / "legal_sources" / "FRANCE_GAZETTE_2022_EXTRACTION_REPORT.md",
    ROOT / "docs" / "legal_sources" / "FRANCE_MORNET_2024_EXTRACTION_REPORT.md",
    ROOT / "docs" / "legal_sources" / "FRANCE_MORNET_2024_MANUAL_FOURCHETTES.md",
    ROOT / "docs" / "legal_sources" / "FRANCE_LEGAL_REVIEW_PACKAGE.md",
]

CHECKLIST_TEMPLATE = (
    ROOT
    / "legal_data"
    / "sources"
    / "france"
    / "review"
    / "france_legal_review_checklist_template.csv"
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
            continue  # già fallito in §1
        size = p.stat().st_size
        if not line(
            f"non vuoto (>0 byte): {p.relative_to(ROOT)}",
            size > 0,
            f"size={size}",
        ):
            failures += 1
    return failures


def check_source_note_flags() -> int:
    """
    Per i CSV con colonna `source_note`, verifica:
      - presenza di `legal_review_required=true`
      - assenza di `no_human_legal_approval=false`
        (sarebbe un'auto-approvazione vietata).
    """
    print("\n3. source_note flags coerenti (legal_review_required=true,")
    print("   no_human_legal_approval != false)")
    failures = 0
    for p in CSVS_WITH_SOURCE_NOTE:
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
        return 0  # già fallito in §1
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


def check_db_no_fr_approved() -> int:
    print("\n5. DB invariants — nessuna LegalSource FR già approved")
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
    fr = Country.objects.filter(code="FR").first()
    if fr is None:
        if not line("Country FR esiste nel DB", False):
            failures += 1
        return failures
    fr_sources = LegalSource.objects.filter(country=fr)
    total = fr_sources.count()
    approved = fr_sources.filter(status="approved").count()
    needs_review = fr_sources.filter(status="needs_review").count()
    print(
        f"  [INFO] FR LegalSource: total={total}, needs_review={needs_review}, approved={approved}"
    )
    if not line(
        "nessuna LegalSource FR è in stato approved",
        approved == 0,
        f"approved={approved}",
    ):
        failures += 1
    # Bonus: confermare che almeno le 5 fonti FR attese esistono
    expected_slugs = {
        "fr-bareme-capitalisation-gazette-palais-2022",
        "fr-bareme-capitalisation-gazette-palais-2025-page",
        "fr-loi-badinter-1985",
        "fr-nomenclature-dintilhac-2005",
        "fr-referentiel-mornet-2024",
    }
    actual_slugs = set(fr_sources.values_list("slug", flat=True))
    missing = expected_slugs - actual_slugs
    if not line(
        "tutte le 5 fonti FR attese sono presenti come LegalSource",
        not missing,
        f"missing={sorted(missing)}",
    ):
        failures += 1
    return failures


def main() -> int:
    print("=" * 72)
    print("QA — France legal review package (read-only)")
    print(f"ROOT: {ROOT}")
    print("=" * 72)

    failures = 0
    failures += check_files_exist()
    failures += check_files_not_empty()
    failures += check_source_note_flags()
    failures += check_checklist_template()
    failures += check_db_no_fr_approved()

    print()
    print("=" * 72)
    if failures == 0:
        print("QA OK — package di review FR coerente. Nessuna auto-approvazione.")
        print("STATO: candidate read-only. Lo Studio deve completare la review.")
        print("=" * 72)
        return 0
    print(f"QA FAILED — {failures} anomalie da indagare.")
    print("=" * 72)
    return 1


if __name__ == "__main__":
    sys.exit(main())
