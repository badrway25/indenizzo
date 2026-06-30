"""P12 — guard the consolidated approval queue & final non-numeric outcomes.

P12 attempted real extraction (text + OCR tooling). Outcome: Morocco's full
coefficient structure was text-extracted (only the scanned capital-de-référence
table is missing); Tunisia's official hosts were unreachable; INAIL's value
table is not machine-readable; Belgium/France have no state barème (final).
No public numeric engine was added for any of them. These guards keep that
honest and keep the paste-ready approval queue complete.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

AUDITS = Path(settings.BASE_DIR) / "docs" / "audits"

_P12_DOCS = (
    "CHATGPT_APPROVAL_QUEUE_2026-06-26.md",
    "MOROCCO_BAREME_CANDIDATE_2026-06-26.md",
    "FOR_CHATGPT_APPROVAL_TUNISIA_NUMERIC_ENGINE_2026-06-26.md",
    "BELGIUM_FINAL_NO_STATE_BAREME_2026-06-26.md",
    "FRANCE_FINAL_NO_STATE_BAREME_2026-06-26.md",
)


@pytest.mark.parametrize("name", _P12_DOCS)
def test_p12_doc_exists_and_non_trivial(name):
    path = AUDITS / name
    assert path.exists(), f"missing P12 doc: {name}"
    assert len(path.read_text("utf-8")) > 600, f"P12 doc too thin: {name}"


def test_approval_queue_lists_all_candidates_with_decisions():
    text = (AUDITS / "CHATGPT_APPROVAL_QUEUE_2026-06-26.md").read_text("utf-8")
    for token in ("Morocco", "Tunisia", "INAIL", "Belgium", "France",
                  "APPROVARE", "canary"):
        assert token in text, token


def test_morocco_candidate_has_formula_canary_and_hash():
    text = (AUDITS / "MOROCCO_BAREME_CANDIDATE_2026-06-26.md").read_text("utf-8")
    assert "capital_de_référence" in text
    assert "34 650" in text          # official canary
    assert "b4d6f9e8b2c61f70" in text  # source hash reference
    # coefficient table extracted (pretium doloris percentages)
    assert "Pretium doloris" in text and "%" in text


def test_belgium_france_final_state_no_engine():
    be = (AUDITS / "BELGIUM_FINAL_NO_STATE_BAREME_2026-06-26.md").read_text("utf-8")
    fr = (AUDITS / "FRANCE_FINAL_NO_STATE_BAREME_2026-06-26.md").read_text("utf-8")
    assert "non-binding" in be or "non vincolante" in be
    assert "Badinter" in fr and "guided" in fr.lower()


def test_no_road_injury_engine_for_morocco_tunisia():
    from apps.calculators.registry import list_available_calculators

    registered = set(list_available_calculators())
    forbidden = [("MA-NATIONAL", "road_accident_bodily_injury"),
                 ("TN-NATIONAL", "road_accident_bodily_injury")]
    assert not [p for p in forbidden if p in registered]


def test_p12_temp_pdfs_not_committed():
    base = Path(settings.BASE_DIR)
    names = {"tn_code_assurances.pdf", "inail_allegato5.pdf",
             "ma_dahir_1984.pdf", "ma_acaps_guide.pdf"}
    found = [str(p) for p in base.rglob("*.pdf") if p.name in names]
    assert not found, f"P12 temp PDF leaked into repo: {found}"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/countries/france/", "/countries/belgium/",
                                  "/countries/morocco/", "/countries/tunisia/"])
def test_no_euro_estimate_for_countries_without_engine(path):
    import re
    body = Client().get(path, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert not re.search(r"\d{1,3}[.,]\d{3}\s*(€|EUR)", body), f"euro leaked on {path}"
