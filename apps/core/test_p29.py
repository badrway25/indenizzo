"""P29 — guard the official-source library, smart search, PDF access and platform nav."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client
from django.urls import reverse

from apps.core import official_sources as official
from apps.core.search_index import search

_MONEY = re.compile(r"\d{1,3}[.,]\d{3}\s*(€|EUR|MAD|DH|DHS|TND)")
_PUBLIC_FORBIDDEN = ("crm", "lead", "pipeline", "debug", "webhook", "in revisione",
                     "non disponibile", "da validare", "manual review", "placeholder")


def _get(path, lang="it"):
    return Client().get(path, HTTP_ACCEPT_LANGUAGE=lang).content.decode("utf-8")


# --- Source library data ----------------------------------------------------
def test_library_maps_priority_sources():
    ids = {s.source_id for s in official.all_sources()}
    for needed in ("it-tu-inail-1124", "ma-dahir-1-84-177", "ma-acaps-guide",
                   "tn-code-assurances", "eu-roma-ii-864-2007", "eu-reg-650-2012"):
        assert needed in ids, f"library missing {needed}"
    assert len(official.all_sources()) >= 20


def test_only_eu_regs_offer_a_real_pdf_download():
    pdf = {s.source_id for s in official.all_sources() if s.pdf_available and s.pdf_url}
    assert pdf == {"eu-roma-ii-864-2007", "eu-reg-650-2012"}
    for s in official.all_sources():
        if s.pdf_url:
            assert s.pdf_url.startswith("https://"), s.source_id


def test_filters_work():
    assert all(s.country == "MA" for s in official.filter_sources(country="MA"))
    assert all("road_accident" in s.categories
               for s in official.filter_sources(category="road_accident"))
    assert official.filter_sources(unlock="estimate")  # at least one estimate source


# --- /sources/ page ---------------------------------------------------------
@pytest.mark.django_db
def test_sources_page_200_with_pdf_and_official_links():
    body = _get("/sources/")
    assert "Scarica PDF ufficiale" in body          # EU reg PDF (IT)
    assert "Apri fonte ufficiale" in body           # external official link
    assert 'rel="noopener noreferrer"' in body      # secure external links
    assert "D.P.R. 1124/1965" in body or "INAIL" in body
    assert "1-84-177" in body  # Moroccan Dahir
    assert body.count("<h1") == 1
    assert not _MONEY.search(body)


@pytest.mark.django_db
def test_sources_filters_query_200():
    for qs in ("?country=MA", "?category=road_accident", "?type=eu_regulation", "?use=estimate"):
        assert Client().get(f"/sources/{qs}").status_code == 200


@pytest.mark.django_db
def test_source_detail_200_and_unknown_404():
    assert Client().get("/sources/eu-roma-ii-864-2007/").status_code == 200
    # no arbitrary id is accepted
    assert Client().get("/sources/not-a-real-source/").status_code == 404
    body = _get("/sources/eu-roma-ii-864-2007/")
    assert "Scarica PDF ufficiale" in body
    assert 'rel="noopener noreferrer"' in body


@pytest.mark.django_db
def test_source_card_labels_are_human_not_slug():
    body = _get("/sources/")
    # no raw category/type snake_case keys leak into the visible card text
    visible = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ",
                     re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)))
    assert not re.search(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b", visible), "snake_case leak"


# --- Smart search -----------------------------------------------------------
@pytest.mark.django_db
def test_search_page_200():
    assert Client().get("/search/").status_code == 200
    assert Client().get("/search/?q=inail").status_code == 200


@pytest.mark.parametrize("q,needle", [
    ("inail", "inail"),
    ("incidente marocco", "marocco"),
    ("responsabilità sanitaria", "sanitaria"),
    ("roma ii", "roma"),
])
def test_search_finds_the_right_destination(q, needle):
    results = search(q)
    assert results, f"no results for {q!r}"
    blob = " ".join(f"{r.title} {r.keywords}" for r in results).lower()
    assert needle in blob


def test_search_finds_official_sources():
    results = search("dahir acaps")
    kinds = {r.kind for r in results}
    from apps.core.search_index import KIND_SOURCE
    assert KIND_SOURCE in kinds


# --- Platform navigation ----------------------------------------------------
@pytest.mark.django_db
def test_navbar_has_sources_and_search():
    body = _get("/")
    assert f'href="{reverse("core:sources")}"' in body
    assert f'href="{reverse("core:search")}"' in body


@pytest.mark.django_db
def test_nav_targets_return_200():
    for name in ("core:sources", "core:search"):
        assert Client().get(reverse(name)).status_code == 200


# --- Hygiene: no slug / weak states / money / public CRM jargon -------------
@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/sources/", "/sources/eu-roma-ii-864-2007/",
                                  "/search/?q=inail", "/"])
def test_pages_are_clean(path):
    body = _get(path)
    assert not _MONEY.search(body)
    low = body.lower()
    for tok in _PUBLIC_FORBIDDEN:
        # allow the words only inside attributes/urls, not visible copy
        visible = re.sub(r"<[^>]+>", " ", re.sub(r"<(script|style)[^>]*>.*?</\1>", " ",
                         body, flags=re.S | re.I)).lower()
        assert tok not in visible, f"{path} leaks {tok!r}"
        _ = low


@pytest.mark.django_db
def test_arabic_sources_200_rtl():
    resp = Client().get("/ar/sources/", HTTP_ACCEPT_LANGUAGE="ar")
    assert resp.status_code == 200
    assert 'dir="rtl"' in resp.content.decode("utf-8")


def test_no_external_cdn_in_new_templates():
    tpl = Path(settings.BASE_DIR) / "templates" / "public"
    for name in ("sources.html", "source_detail.html", "search.html"):
        src = (tpl / name).read_text("utf-8")
        assert "cdn." not in src and "https://unpkg" not in src and "googleapis" not in src


def test_engine_canaries_intact():
    from apps.calculators.registry import list_available_calculators
    pairs = {(j, c) for j, c in list_available_calculators()}
    assert ("IT-NATIONAL", "road_accident_bodily_injury") in pairs
    assert ("IT-NATIONAL", "medical_liability_biological_damage") in pairs


@pytest.mark.parametrize("lang", ["it", "fr", "ar"])
def test_catalog_no_fuzzy(lang):
    po = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    assert "#, fuzzy" not in po.read_text("utf-8")
