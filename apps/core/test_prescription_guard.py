"""Guard rails for the read-only prescription audit phase.

These pin the invariants the audit relies on: the public site must never present
a prescription term as an approved/certain figure, the prudent (non-numeric)
notice must stay and route to a professional verification, the calculator must
not model or consume prescription, and no public route may expose a prescription
term. The audit itself must remain docs-only (no public feature).
See docs/audits/PRESCRIPTION_LEGAL_SOURCE_READONLY_AUDIT_2026-06-24.md.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import translation

# A numeric "period" presented to the user (it/en/fr/ar) or a bare article cited
# as if it were a certain term. The prudent notice must contain none of these.
_PERIOD_RE = re.compile(
    r"\d+\s*(anni|anno|years?|ans?|an\b|mesi|mese|months?|mois|giorni|giorno|days?|jours?|سنة|سنوات|أشهر|شهر|أيام|يوم)",
    re.IGNORECASE,
)
_ARTICLE_AS_TERM_RE = re.compile(r"art\.?\s*\d", re.IGNORECASE)

_LANGS = ("it", "fr", "en", "ar")


def _notice(lang: str) -> str:
    with translation.override(lang):
        return render_to_string("partials/_prescrizione_notice.html")


@pytest.mark.parametrize("lang", _LANGS)
def test_public_prescription_notice_is_non_numeric(lang):
    """No approved/certain numeric term (e.g. '2 anni', 'art. 2947') is shown."""
    html = _notice(lang)
    assert not _PERIOD_RE.search(html), f"[{lang}] prescription notice shows a numeric period"
    assert not _ARTICLE_AS_TERM_RE.search(html), f"[{lang}] prescription notice cites an article as a term"


@pytest.mark.parametrize("lang", _LANGS)
def test_prescription_notice_routes_to_verification(lang):
    """The notice must defer to a professional verification (contact link)."""
    from django.urls import reverse

    with translation.override("it"):
        contact = reverse("crm:contact")
    assert contact in _notice(lang), f"[{lang}] notice does not route to a professional verification"


def test_result_page_includes_prescription_notice():
    """The prudent notice is rendered on the result page (estimate + unavailable)."""
    src = (Path(settings.BASE_DIR) / "templates" / "public" / "wizard_result.html").read_text("utf-8")
    assert "_prescrizione_notice.html" in src


def test_calculator_layer_does_not_model_prescription():
    """The estimate engine/services/schema must not consume or gate on prescription."""
    roots = [
        Path(settings.BASE_DIR) / "apps" / "calculators" / "engines",
        Path(settings.BASE_DIR) / "apps" / "calculators" / "schemas.py",
        Path(settings.BASE_DIR) / "apps" / "compensation" / "services.py",
    ]
    files = []
    for r in roots:
        files += [r] if r.is_file() else list(r.rglob("*.py"))
    for f in files:
        if f.name.startswith("test_"):
            continue
        assert "prescri" not in f.read_text("utf-8").lower(), (
            f"{f}: the calculation layer must not reference prescription"
        )


def test_no_public_route_exposes_prescription():
    """No public URL name/path surfaces prescription as a standalone data page."""
    from apps.core import urls as core_urls

    for p in core_urls.urlpatterns:
        name = getattr(p, "name", "") or ""
        pattern = str(getattr(p, "pattern", ""))
        assert "prescri" not in name.lower(), f"unexpected public route name: {name}"
        assert "prescri" not in pattern.lower(), f"unexpected public route path: {pattern}"


def test_prescription_audit_is_docs_only():
    """The audit lives under docs/audits/ — it is analysis, not a shipped feature."""
    audit = Path(settings.BASE_DIR) / "docs" / "audits" / "PRESCRIPTION_LEGAL_SOURCE_READONLY_AUDIT_2026-06-24.md"
    assert audit.exists(), "prescription audit report is missing"
    text = audit.read_text("utf-8").lower()
    assert "read-only" in text and "approved" in text
