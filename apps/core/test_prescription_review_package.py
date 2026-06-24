"""Guard rails for the prescription Studio review package (F-prescription-studio-review-iter1).

The package is docs-only preparatory material: it must never be loaded as a
LegalSource, must surface no public term, must add no public route, and the
estimate engine must not read it. The checklist stays `pending` (no `approved`
decision, no numeric term) until the Studio signs each decision.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.conf import settings

_PKG_DIR = Path(settings.BASE_DIR) / "docs" / "review_packages"
_PACKAGE = _PKG_DIR / "PRESCRIPTION_STUDIO_REVIEW_PACKAGE_2026-06-24.md"
_TEMPLATE = _PKG_DIR / "templates" / "prescription_review_decision_template.md"
_CHECKLIST = _PKG_DIR / "prescription_review_checklist.csv"

# numeric period presented as a term, e.g. "2 anni" / "3 years" — must NOT appear
_PERIOD_RE = re.compile(r"\d+\s*(anni|anno|years?|ans?|mesi|mese|months?|giorni|giorno|days?)", re.IGNORECASE)


def test_review_package_artifacts_present():
    assert _PACKAGE.exists(), "prescription review package is missing"
    assert _TEMPLATE.exists(), "prescription review decision template is missing"
    assert _CHECKLIST.exists(), "prescription review checklist is missing"


def test_review_package_is_isolated_from_app_code():
    """No NON-test application code may import or read the review-package docs
    (they are review material, never a LegalSource loader / data source)."""
    needles = ("review_packages", "prescription_review", "PRESCRIPTION_STUDIO_REVIEW")
    apps_root = Path(settings.BASE_DIR) / "apps"
    offenders = []
    for f in apps_root.rglob("*.py"):
        if f.name.startswith("test_"):
            continue  # tests may reference the paths to assert isolation
        text = f.read_text("utf-8")
        if any(n in text for n in needles):
            offenders.append(str(f.relative_to(settings.BASE_DIR)))
    assert not offenders, f"app code references the review package as data: {offenders}"


def test_review_checklist_is_pending_and_non_numeric():
    """The checklist carries no signed `approved`/`go` decision and no numeric
    prescription term — it is a blank template until the Studio fills it."""
    text = _CHECKLIST.read_text("utf-8")
    # header row defines the columns; data rows must all carry `pending` decision
    lines = [l for l in text.splitlines() if l.strip()]
    header = lines[0].split(",")
    dec_idx = header.index("decision")
    for row in lines[1:]:
        cells = row.split(",")
        assert cells[dec_idx].strip().lower() == "pending", f"non-pending decision in checklist: {row[:60]}"
    lowered = text.lower()
    assert "approved" not in lowered, "checklist must not contain an approved decision"
    assert not _PERIOD_RE.search(text), "checklist must not state a numeric prescription term"


def test_review_package_states_read_only_and_no_public_activation():
    text = _PACKAGE.read_text("utf-8").lower()
    assert "read-only" in text
    assert "manual_review_required" in text
    # the package must explicitly keep terms out of the public site
    assert "nessun termine" in text or "no public" in text
