"""C2: guard that FR/AR public case-type landings render their own language.

Locks the C2 translation + the fuzzy/stale-.mo fix: no English source residue
on /fr/ or /ar/ landings, Arabic stays RTL, and the per-case <title> renders the
page's own language (not a left-over Italian/English string).
"""

from __future__ import annotations

import re

import pytest
from django.test import Client

CASE_TYPES = [
    "road-accident",
    "bodily-injury",
    "insurance-offer-review",
    "work-injury",
    "medical-malpractice",
    "death-of-relative",
    "foreigners-in-italy",
    "cross-border-cases",
]

ENGLISH_RESIDUES = [
    "guarantee of outcome",
    "the Studio reviews each case manually",
    "preliminary indicative assessment",
    "without any automatic engagement",
    "Professional engagement",
    "Bodily injury claims",
]

ARABIC_RE = re.compile(r"[؀-ۿ]")


def _get(path: str) -> str:
    return Client().get(path).content.decode("utf-8")


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["fr", "ar"])
@pytest.mark.parametrize("ct", CASE_TYPES)
def test_landing_has_no_english_residue(lang, ct):
    body = _get(f"/{lang}/case-types/{ct}/")
    for residue in ENGLISH_RESIDUES:
        assert residue not in body, f"English residue {residue!r} on /{lang}/case-types/{ct}/"


@pytest.mark.django_db
def test_fr_landing_renders_french():
    body = _get("/fr/case-types/bodily-injury/")
    assert "dommage corporel" in body.lower()
    # title is French, not the left-over Italian (fuzzy/stale-.mo regression).
    title = re.search(r"<title>(.*?)</title>", body, re.S).group(1)
    assert "accompagné" in title.lower()  # "parcours juridique accompagné"
    assert "valutazione" not in title.lower()


@pytest.mark.django_db
def test_ar_landing_is_rtl_and_arabic():
    body = _get("/ar/case-types/bodily-injury/")
    assert 'dir="rtl"' in body
    assert 'lang="ar"' in body
    title = re.search(r"<title>(.*?)</title>", body, re.S).group(1)
    assert ARABIC_RE.search(title), "AR <title> should contain Arabic script"
    assert "valutazione" not in title.lower()


@pytest.mark.django_db
@pytest.mark.parametrize("lang", ["fr", "ar"])
def test_mandate_notice_not_english(lang):
    """The mandate notice on the result page is not the English source."""
    from apps.cases.models import Simulation

    sim = Simulation.objects.create(case_type="road_accident", locale=lang)
    body = _get(f"/{lang}/wizard/result/{sim.public_id}/")
    assert "data-mandate-notice" in body
    assert "Professional engagement" not in body
