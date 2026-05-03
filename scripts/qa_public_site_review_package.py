"""Read-only QA per F-product-studio-review-package-public-site.

Verifica che gli artefatti del review package esistano e che la
checklist CSV rispetti lo schema concordato (header esatto, righe
non vuote, `status` fra i valori ammessi).

Niente scrittura: lo script è eseguibile in CI o in locale prima di
inviare il pacchetto allo Studio. Exit code:
- 0 → tutti i check verdi.
- 1 → almeno una violazione (stampa la lista).
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

DOC_PATH = REPO_ROOT / "docs" / "review" / "PUBLIC_SITE_STUDIO_REVIEW_PACKAGE.md"
DOC_FIRST_LINE = "# Public site — Studio review package"

CHECKLIST_PATH = REPO_ROOT / "legal_data" / "review" / "public_site_review_checklist_template.csv"
CHECKLIST_HEADER = [
    "area",
    "page_url",
    "language",
    "review_item",
    "current_status",
    "reviewer",
    "status",
    "notes",
    "reviewed_at",
]
ALLOWED_STATUSES = {"pending", "approved", "change_requested", "rejected", "not_applicable"}
MIN_CHECKLIST_ROWS = 50

SCREENSHOT_DIR = REPO_ROOT / "docs" / "screenshots" / "live_qa" / "public_site_qa_polish_pass2"
MIN_SCREENSHOTS = 7

PASS1_TESTS = REPO_ROOT / "apps" / "core" / "test_public_site_qa_polish_pass1.py"
PASS2_TESTS = REPO_ROOT / "apps" / "core" / "test_public_site_qa_polish_pass2.py"
PEXELS_MANIFEST = REPO_ROOT / "media" / "pexels" / "pexels_manifest.json"

# F-product-studio-review-feedback-intake artefacts.
FEEDBACK_PARSER = REPO_ROOT / "scripts" / "parse_public_site_review_feedback.py"
FEEDBACK_TESTS = REPO_ROOT / "apps" / "core" / "test_studio_review_feedback_intake.py"
EXAMPLE_FILLED_CSV = (
    REPO_ROOT / "docs" / "review" / "public_site_review_checklist_example_filled.csv"
)


def _check_doc(violations: list[str]) -> None:
    if not DOC_PATH.exists():
        violations.append(f"missing review doc: {DOC_PATH}")
        return
    first = DOC_PATH.read_text(encoding="utf-8").splitlines()[0].strip()
    if not first.startswith(DOC_FIRST_LINE):
        violations.append(
            f"review doc first line mismatch: {first!r} (expected {DOC_FIRST_LINE!r})"
        )


def _check_checklist(violations: list[str]) -> int:
    if not CHECKLIST_PATH.exists():
        violations.append(f"missing checklist: {CHECKLIST_PATH}")
        return 0
    with CHECKLIST_PATH.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames != CHECKLIST_HEADER:
            violations.append(
                "checklist header mismatch: "
                f"{reader.fieldnames!r} (expected {CHECKLIST_HEADER!r})"
            )
            return 0
        rows = list(reader)
    if len(rows) < MIN_CHECKLIST_ROWS:
        violations.append(f"checklist too small: {len(rows)} rows < {MIN_CHECKLIST_ROWS} required")
    for idx, row in enumerate(rows, start=2):  # csv line numbers (header is line 1)
        if not row["area"].strip():
            violations.append(f"checklist line {idx}: empty `area`")
        if not row["review_item"].strip():
            violations.append(f"checklist line {idx}: empty `review_item`")
        if row["status"] not in ALLOWED_STATUSES:
            violations.append(
                f"checklist line {idx}: status={row['status']!r} not in {sorted(ALLOWED_STATUSES)}"
            )
    return len(rows)


def _check_screenshots(violations: list[str]) -> int:
    if not SCREENSHOT_DIR.exists():
        violations.append(f"missing screenshot dir: {SCREENSHOT_DIR}")
        return 0
    pngs = sorted(SCREENSHOT_DIR.glob("*.png"))
    if len(pngs) < MIN_SCREENSHOTS:
        violations.append(
            f"screenshot count too low: {len(pngs)} < {MIN_SCREENSHOTS} in {SCREENSHOT_DIR}"
        )
    return len(pngs)


def _check_supporting_files(violations: list[str]) -> None:
    for path, label in [
        (PASS1_TESTS, "pass1 tests"),
        (PASS2_TESTS, "pass2 tests"),
        (PEXELS_MANIFEST, "Pexels manifest"),
        (FEEDBACK_PARSER, "feedback parser"),
        (FEEDBACK_TESTS, "feedback intake tests"),
        (EXAMPLE_FILLED_CSV, "example filled CSV"),
    ]:
        if not path.exists():
            violations.append(f"missing {label}: {path}")


def main() -> int:
    violations: list[str] = []
    _check_doc(violations)
    n_rows = _check_checklist(violations)
    n_pngs = _check_screenshots(violations)
    _check_supporting_files(violations)

    print("[qa-review-package] doc:", "OK" if DOC_PATH.exists() else "MISSING")
    print(f"[qa-review-package] checklist rows: {n_rows}")
    print(f"[qa-review-package] screenshots (pass2): {n_pngs}")
    print(f"[qa-review-package] pass1 tests: {'OK' if PASS1_TESTS.exists() else 'MISSING'}")
    print(f"[qa-review-package] pass2 tests: {'OK' if PASS2_TESTS.exists() else 'MISSING'}")
    print(
        "[qa-review-package] pexels manifest:",
        "OK" if PEXELS_MANIFEST.exists() else "MISSING",
    )
    print(
        "[qa-review-package] feedback parser:",
        "OK" if FEEDBACK_PARSER.exists() else "MISSING",
    )
    print(
        "[qa-review-package] feedback intake tests:",
        "OK" if FEEDBACK_TESTS.exists() else "MISSING",
    )
    print(
        "[qa-review-package] example filled CSV:",
        "OK" if EXAMPLE_FILLED_CSV.exists() else "MISSING",
    )

    if violations:
        print("\n[qa-review-package] VIOLATIONS:")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("\n[qa-review-package] all checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
