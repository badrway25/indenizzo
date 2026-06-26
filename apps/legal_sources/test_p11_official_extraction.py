"""P11 — guard the official numeric-extraction outcome.

No engine was built for INAIL / Morocco / Tunisia / Belgium / France because the
official value tables could not be extracted and verified to the cent in this
environment (scanned PDFs / values not published machine-readable / non-binding
references). Instead, evidence-rich approval packs document exactly what to
validate. These guards keep that state honest: the packs exist, no engine was
silently added for those jurisdictions, no euro estimate leaks for them, and no
heavy PDF was committed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

AUDITS = Path(settings.BASE_DIR) / "docs" / "audits"

_REQUIRED_PACKS = (
    "FOR_CHATGPT_APPROVAL_INAIL_TABLE_2026-06-26.md",
    "FOR_CHATGPT_APPROVAL_MOROCCO_BAREME_2026-06-26.md",
    "P11_TUNISIA_BELGIUM_FRANCE_NUMERIC_OUTCOMES_2026-06-26.md",
)


@pytest.mark.parametrize("name", _REQUIRED_PACKS)
def test_approval_pack_exists_and_non_trivial(name):
    path = AUDITS / name
    assert path.exists(), f"missing approval pack: {name}"
    assert len(path.read_text("utf-8")) > 800, f"approval pack too thin: {name}"


def test_inail_pack_carries_verified_chain():
    """The INAIL pack must name the current official table chain, not be vague."""
    text = (AUDITS / "FOR_CHATGPT_APPROVAL_INAIL_TABLE_2026-06-26.md").read_text("utf-8")
    for token in ("D.M. Lavoro n. 45", "2019", "Delibera", "canary"):
        assert token in text, token


def test_morocco_pack_carries_formula_and_canary():
    text = (AUDITS / "FOR_CHATGPT_APPROVAL_MOROCCO_BAREME_2026-06-26.md").read_text("utf-8")
    assert "Capital de référence" in text
    assert "34 650" in text  # the official ACAPS worked-example canary


def test_no_active_numeric_engine_for_morocco_tunisia_road_injury():
    """P11 added no road-injury engine for MA/TN. (FR/BE keep their pre-existing
    inactive placeholder calculators, guarded by test_france/belgium_engine_inactive
    and the no-euro country-page test below.)"""
    from apps.calculators.registry import list_available_calculators

    registered = set(list_available_calculators())
    forbidden = [
        ("MA-NATIONAL", "road_accident_bodily_injury"),
        ("TN-NATIONAL", "road_accident_bodily_injury"),
    ]
    leaked = [pair for pair in forbidden if pair in registered]
    assert not leaked, f"unexpected MA/TN numeric engine registered: {leaked}"


def test_p11_downloaded_pdfs_not_committed():
    """The official PDFs fetched for P11 were processed in a temp dir and must
    never be committed (the repo's curated source PDFs under legal_data/ are a
    separate, intentional archive)."""
    base = Path(settings.BASE_DIR)
    forbidden_names = {
        "inail_allegato5.pdf", "dm_20000712.pdf",
        "ma_acaps_guide.pdf", "ma_dahir_1984.pdf",
    }
    found = [str(p) for p in base.rglob("*.pdf") if p.name in forbidden_names]
    assert not found, f"P11 temp PDF leaked into repo: {found}"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/countries/france/", "/countries/belgium/",
                                  "/countries/morocco/", "/countries/tunisia/"])
def test_no_euro_estimate_for_countries_without_engine(path):
    import re
    body = Client().get(path, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert not re.search(r"\d{1,3}[.,]\d{3}\s*(€|EUR)", body), f"euro estimate leaked on {path}"
