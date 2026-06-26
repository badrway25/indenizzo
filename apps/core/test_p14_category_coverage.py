"""P14 — guard coherent country × category coverage.

Every country reads as a multi-category platform grounded in official sources,
never a single generic page. Morocco and Tunisia must cover road injury / death
on the Dahir 1984 / loi 2005-86 — not succession only — and no country without
an approved engine may publish a euro/MAD/TND estimate.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

MATRIX = Path(settings.BASE_DIR) / "docs" / "audits" / "CATEGORY_COUNTRY_OFFICIAL_ESTIMATE_MATRIX_2026-06-26.md"
_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")


def test_matrix_exists_and_covers_countries_and_categories():
    assert MATRIX.exists(), "missing category × country matrix"
    text = MATRIX.read_text("utf-8")
    for country in ("ITALIA", "MAROCCO", "TUNISIA", "FRANCIA", "BELGIO", "INTERNAZIONALE"):
        assert country in text, country
    for cat in ("Road accident", "Death", "Medical liability", "Work injury",
                "Defective product", "Insurance offer", "applicable law"):
        assert cat in text, cat


@pytest.mark.django_db
@pytest.mark.parametrize("path,road_src", [
    ("/countries/morocco/", "Dahir 1-84-177 (1984)"),
    ("/countries/tunisia/", "Loi 2005-86"),
])
def test_country_not_succession_only(path, road_src):
    body = Client().get(path, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    # the multi-category section is present with a road-accident category
    assert "Categorie coperte" in body
    assert "Incidenti stradali e danno alla persona" in body
    assert "Decesso e aventi diritto" in body
    # the road-injury official source is cited (not only inheritance sources)
    assert road_src in body


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/countries/morocco/", "/countries/tunisia/"])
def test_country_pages_show_category_source_chips(path):
    body = Client().get(path, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    # at least one official source chip in the categories section
    assert "§" in body
    assert ("ACAPS" in body) or ("CGA" in body) or ("Code des assurances" in body)


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/countries/morocco/", "/countries/tunisia/",
                                  "/countries/france/", "/countries/belgium/"])
def test_no_money_estimate_for_countries_without_engine(path):
    body = Client().get(path, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8")
    assert not _MONEY.search(body), f"money estimate leaked on {path}"


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/countries/morocco/", "/countries/tunisia/"])
def test_no_review_state_on_expanded_country_pages(path):
    body = Client().get(path, HTTP_ACCEPT_LANGUAGE="it").content.decode("utf-8").lower()
    for tok in ("in revisione", "needs review", "non disponibile", "generico"):
        assert tok not in body, f"{path} leaks {tok!r}"
