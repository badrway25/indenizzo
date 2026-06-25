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
_CHECKLIST_YML = _PKG_DIR / "prescription_review_checklist.yml"
_UNRESOLVED = _PKG_DIR / "PRESCRIPTION_UNRESOLVED_FOR_CHATGPT_2026-06-24.md"

# numeric period presented as a term, e.g. "2 anni" / "3 years" — must NOT appear.
# Word-boundaries so the unit is a whole word (avoids matching "an" inside the
# English "and" after an article number, e.g. "125 and 126").
_PERIOD_RE = re.compile(
    r"\b\d+\s*(anni|anno|years?|ans?|mesi|mese|months?|giorni|giorno|days?)\b", re.IGNORECASE
)

# F-source-validation-official-hardening final status vocabulary (INTERNAL).
# A verified official source is still NEVER a public term.
_ALLOWED_STATUSES = {
    "source_verified_official_internal_only",
    "source_verified_official_limited_scope",
    "source_verified_official_procedure_only",
    "not_found_in_official_sources",
    "excluded_from_public_display",
}
# Forbidden as a FINAL status in the validation record.
_FORBIDDEN_STATUSES = {
    "manual_review_required",
    "unresolved_for_chatgpt_or_human_validation",
    "approved_for_public_display",
    "public_approved",
}
# Tokens that must NEVER appear in a PUBLIC template (internal states / "to validate").
_PUBLIC_FORBIDDEN_TOKENS = (
    "manual_review_required",
    "unresolved",
    "da validare",
    "in validazione",
    "source_verified",
    "approved_for_public_display",
    "public_approved",
)


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
    low = _PACKAGE.read_text("utf-8").lower()
    assert "read-only" in low
    # hardened: validated internal-only, never a public-approval state
    assert "source_verified_official_internal_only" in low
    assert "approved_for_public_display: true" not in low
    assert "public_approved: true" not in low


# --- F-source-validation-official-hardening guards --------------------------

def test_validation_record_never_approves_public_display():
    """A verified official source must NEVER become an approved public term."""
    for f in (_CHECKLIST_YML, _PACKAGE, _UNRESOLVED):
        low = f.read_text("utf-8").lower()
        for bad in (
            "approved_for_public_display: true",
            "status: approved_for_public_display",
            "public_approved: true",
            "status: public_approved",
        ):
            assert bad not in low, f"{f.name}: {bad!r}"
    yml = _CHECKLIST_YML.read_text("utf-8").lower()
    assert "approved_for_public_display: false" in yml
    assert "public_approved: false" in yml


def test_validation_statuses_are_in_hardened_vocabulary():
    """Every per-source status uses the hardened internal vocabulary; none of the
    forbidden final states (manual_review_required / unresolved / *approved) survive."""
    text = _CHECKLIST_YML.read_text("utf-8")
    statuses = re.findall(r"^\s*status:\s*([a-z_]+)\s*$", text, re.MULTILINE)
    assert statuses, "no per-source status entries found in the validation record"
    for s in statuses:
        assert s in _ALLOWED_STATUSES, f"unexpected validation status: {s}"
        assert s not in _FORBIDDEN_STATUSES, f"forbidden final status survived: {s}"


def test_no_internal_validation_state_in_public_templates():
    """Internal validation states / "to validate" must NEVER reach a public template."""
    roots = [
        Path(settings.BASE_DIR) / "templates" / "public",
        Path(settings.BASE_DIR) / "templates" / "partials",
    ]
    for root in roots:
        for f in root.rglob("*.html"):
            low = f.read_text("utf-8").lower()
            for tok in _PUBLIC_FORBIDDEN_TOKENS:
                assert tok not in low, f"{f.name}: public template contains internal token {tok!r}"


def test_unresolved_file_documents_zero_not_found_and_is_non_numeric():
    assert _UNRESOLVED.exists(), "unresolved-for-chatgpt file is missing"
    raw = _UNRESOLVED.read_text("utf-8")
    assert "not_found" in raw.lower()
    assert not _PERIOD_RE.search(raw), "unresolved file must not state a numeric prescription term"
