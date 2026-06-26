"""P10 — guard complete official section coverage & public finish.

Every case-type section must read as a professional state with a visible
official source chip, never a weak/blocked label, and the new product-liability
section must exist. The existing numeric flows (medical, offer, micro, TUN)
keep working — guarded in their own suites; here we guard the public finish.
"""

from __future__ import annotations

import pytest
from django.test import Client

from apps.core.case_type_landings import LANDINGS, LANDINGS_BY_SLUG

# Tokens that must NEVER appear in public copy (user-facing weak/blocked labels).
_WEAK_PUBLIC = (
    "non disponibile",
    "in revisione",
    "da validare",
    "manual review",
    "unresolved",
    "fail-closed",
    "fail closed",
    "placeholder",
    "non pronto",
    "fonte non approvata",
)


def test_every_landing_has_official_basis():
    """P10: every section names its official legal basis (source chip)."""
    missing = [land.slug for land in LANDINGS if not land.official_basis]
    assert not missing, f"landings without an official_basis chip: {missing}"


def test_official_basis_entries_are_non_empty_strings():
    for land in LANDINGS:
        for src in land.official_basis:
            assert isinstance(src, str) and src.strip(), land.slug


def test_product_liability_section_exists():
    assert "product-liability" in LANDINGS_BY_SLUG


@pytest.mark.django_db
def test_product_liability_landing_renders_official_guided_path():
    body = Client().get(
        "/case-types/product-liability/", HTTP_ACCEPT_LANGUAGE="it"
    ).content.decode("utf-8")
    assert "Responsabilità da prodotto difettoso" in body
    assert "Base normativa ufficiale" in body  # source chip label
    assert "artt. 114–127 Cod. del Consumo" in body  # official norm chip


@pytest.mark.django_db
def test_inail_section_shows_official_source_chip():
    body = Client().get(
        "/case-types/work-injury/", HTTP_ACCEPT_LANGUAGE="it"
    ).content.decode("utf-8")
    assert "D.P.R. 1124/1965" in body
    assert "D.M. 12/07/2000" in body


@pytest.mark.django_db
@pytest.mark.parametrize("slug", [land.slug for land in LANDINGS])
def test_no_weak_label_on_any_landing(slug):
    body = Client().get(
        f"/case-types/{slug}/", HTTP_ACCEPT_LANGUAGE="it"
    ).content.decode("utf-8").lower()
    leaks = [t for t in _WEAK_PUBLIC if t in body]
    assert not leaks, f"{slug} shows weak public label(s): {leaks}"


@pytest.mark.django_db
def test_road_wizard_has_no_manual_review_label():
    body = Client().get(
        "/wizard/it/road-accident/", HTTP_ACCEPT_LANGUAGE="it"
    ).content.decode("utf-8").lower()
    assert "manual review" not in body
    assert "verifica documentale" in body  # reworded to the approved wording
