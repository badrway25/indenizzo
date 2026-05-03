"""Verify the manually-attached Badinter PDF against Légifrance canonical markers.

Iter: F-official-source-fr-badinter-manual-attach-and-legal-source-validation.

Read-only by design. Reads ``legal_data/sources/france/manual_attached/
fr-loi-badinter-1985.pdf`` (the file produced by ``manage.py
attach_official_source_file``), extracts the visible text via
``pdfplumber``, and verifies a list of structural markers that any
authentic copy of Loi n°85-677 du 5 juillet 1985 must contain. The
canonical reference URL on Légifrance is recorded but not fetched (the
auto-fetch pipeline is blocked by HTTP 403 there — see
``docs/legal_sources/MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md``).

Output: a Markdown report at
``docs/legal_sources/FR_BADINTER_OFFICIAL_SOURCE_VALIDATION.md`` with
sha256, size, marker table (PASS/FAIL), Légifrance canonical URL, and a
final "source authenticity verified / failed" verdict.

Hard guarantees mirrored from the manual_attach pipeline:

- read-only on the DB and the filesystem (only writes the report);
- never creates ``LegalReview``;
- never promotes ``LegalSource.status`` to ``APPROVED``;
- never triggers calculator activation.
"""

from __future__ import annotations

import hashlib
import io
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PDF_PATH = (
    REPO_ROOT / "legal_data" / "sources" / "france" / "manual_attached" / "fr-loi-badinter-1985.pdf"
)
REPORT_PATH = REPO_ROOT / "docs" / "legal_sources" / "FR_BADINTER_OFFICIAL_SOURCE_VALIDATION.md"
LEGIFRANCE_CANONICAL_URL = "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000693454"

# Each entry is (label, marker, why-it-matters). Markers are matched
# case-sensitively against the pdfplumber-extracted text. The set
# covers identity, scope, fault doctrine, offer-deadline, and
# administrative articles — enough to refute trivial substitutions
# (e.g. wrong decree, redacted scan, OCR-corrupted copy).
STRUCTURAL_MARKERS: list[tuple[str, str, str]] = [
    ("law_number", "Loi n° 85-677", "law identity"),
    ("signature_date", "5 juillet 1985", "law signing date"),
    (
        "title_object",
        "amélioration de la situation des victimes d'accidents de la circulation",
        "law subject — opening clause",
    ),
    ("article_1", "Article 1", "scope: roadway accidents"),
    (
        "vehicle_definition",
        "véhicule terrestre à moteur",
        "art. 1 — vehicles in scope",
    ),
    ("article_3", "Article 3", "non-driver victim indemnification regime"),
    (
        "faute_inexcusable",
        "faute inexcusable",
        "art. 3 — only inexcusable fault excludes non-driver victims",
    ),
    ("article_4", "Article 4", "driver fault doctrine"),
    (
        "faute_conducteur",
        "faute commise par le conducteur",
        "art. 4 — driver-fault clause",
    ),
    ("article_12", "Article 12", "insurer offer deadline regime"),
    (
        "offer_deadline_8_months",
        "délai maximum de huit mois",
        "art. 12 — 8-month maximum offer deadline",
    ),
]


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _extract_pdf_text(payload: bytes) -> str:
    try:
        import pdfplumber
    except ImportError:
        return ""
    chunks: list[str] = []
    try:
        with pdfplumber.open(io.BytesIO(payload)) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
    except Exception as exc:  # noqa: BLE001 — diagnostic only
        print(f"  [warn] pdfplumber raised {exc.__class__.__name__}: {exc}")
        return ""
    return "\n".join(chunks)


def verify_text_against_markers(
    text: str,
    markers: list[tuple[str, str, str]],
) -> tuple[bool, list[tuple[str, str, bool, str]]]:
    """Pure function: given extracted text and the marker spec, return
    ``(all_pass, [(label, marker, ok, reason), ...])``.

    Whitespace inside the extracted text is collapsed to a single space
    before matching, so a marker spanning a soft line wrap in the source
    PDF (e.g. the law's title) still matches a one-line marker.
    """
    import re

    normalized = re.sub(r"\s+", " ", text)
    rows: list[tuple[str, str, bool, str]] = []
    all_pass = True
    for label, marker, reason in markers:
        normalized_marker = re.sub(r"\s+", " ", marker)
        ok = normalized_marker in normalized
        rows.append((label, marker, ok, reason))
        all_pass = all_pass and ok
    return all_pass, rows


def main() -> int:
    if not PDF_PATH.exists():
        print(f"FAIL: PDF not found at {PDF_PATH}")
        return 2
    payload = PDF_PATH.read_bytes()
    if not payload.startswith(b"%PDF-"):
        print(f"FAIL: file does not start with %PDF- magic at {PDF_PATH}")
        return 2

    sha256_hex = _sha256(payload)
    size_bytes = len(payload)
    print(f"PDF: {PDF_PATH.relative_to(REPO_ROOT)}")
    print(f"  size_bytes: {size_bytes}")
    print(f"  sha256:     {sha256_hex}")

    text = _extract_pdf_text(payload)
    if not text:
        print("FAIL: pdfplumber extracted no text — image-only or corrupted PDF.")
        return 1
    print(f"  extracted_chars: {len(text)}")
    all_pass, rows = verify_text_against_markers(text, STRUCTURAL_MARKERS)
    for label, marker, ok, _ in rows:
        print(f"  [{'PASS' if ok else 'FAIL'}] {label:<22} {marker!r}")

    verdict = (
        "source authenticity verified"
        if all_pass
        else "source authenticity FAILED — at least one structural marker missing"
    )
    print(f"\nVerdict: {verdict}")

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    now = datetime.now(UTC).isoformat(timespec="seconds")
    lines = [
        "# FR Loi Badinter — Official Source Validation",
        "",
        "**Iter:** `F-official-source-fr-badinter-manual-attach-and-legal-source-validation`.",
        "",
        f"**Generated:** `{now}`.",
        "",
        "Read-only validation of the manually-attached PDF against the structural",
        "markers expected on any authentic copy of Loi n°85-677 du 5 juillet 1985.",
        "This report does not approve the source for calculator use; it only attests",
        "that the file matches the canonical Légifrance text on the markers checked.",
        "",
        "## File integrity",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Local path | `{PDF_PATH.relative_to(REPO_ROOT).as_posix()}` |",
        f"| Size (bytes) | {size_bytes} |",
        f"| sha256 | `{sha256_hex}` |",
        "| Magic bytes | `%PDF-` (verified) |",
        f"| Légifrance canonical URL | <{LEGIFRANCE_CANONICAL_URL}> |",
        "",
        "## Structural markers",
        "",
        "Match policy: case-sensitive substring search on `pdfplumber`-extracted text",
        "(all pages). Missing any marker fails the verification: a single absence is",
        "evidence of substitution, redaction, or OCR corruption.",
        "",
        "| # | Label | Marker | Status | Reason for inclusion |",
        "|---|-------|--------|--------|----------------------|",
    ]
    for i, (label, marker, ok, reason) in enumerate(rows, 1):
        status_cell = "PASS" if ok else "**FAIL**"
        lines.append(f"| {i} | `{label}` | `{marker}` | {status_cell} | {reason} |")
    lines += [
        "",
        "## Conclusion",
        "",
        f"**Verdict:** *{verdict}.*",
        "",
        "## What this verification does NOT do",
        "",
        "- It does **not** create a `LegalReview` row. Source authenticity is not",
        "  the same as Studio approval; only a human reviewer can promote",
        "  `LegalSource.status` to `APPROVED`.",
        "- It does **not** activate the FR road-accident calculator. The engine,",
        "  the dataset, and the formula remain pending; `run_simulation`",
        "  continues to return `unavailable_requires_legal_validation` for",
        "  `FR-NATIONAL × road_accident_bodily_injury`.",
        "- It does **not** alter Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR.",
        "",
        "## What is still required to make FR road-accident calculable",
        "",
        "1. Studio legal review of Loi Badinter scope on `road_accident_bodily_injury`",
        "   → `LegalReview.decision=approve` → manual promotion of",
        "   `LegalSource.status` to `APPROVED`.",
        "2. A validated quantification source (Référentiel Mornet, Gazette du Palais,",
        "   or jurisprudence-derived bareme): currently `private_bareme` /",
        "   `human_exception_only` in the registry.",
        "3. A `CompensationDataset` + `CalculationFormula` matching the validated",
        "   bareme (separate import pipeline).",
        "4. An `apps/calculators/engines/france.py` engine with deterministic mapping",
        "   victim_age × disability % × case category → amount.",
        "5. Smoke tests for at least one age × disability × fault triple, locked in",
        "   `apps/calculators/test_*.py`.",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nReport written: {REPORT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    # Ensure the script runs both with and without DJANGO_SETTINGS_MODULE
    # — it doesn't touch the DB, only files.
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    sys.exit(main())
