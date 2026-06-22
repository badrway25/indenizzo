"""C1: guard that public case-type landings render Italian (no English residue).

The landing copy lives in apps/core/case_type_landings.py as gettext strings.
These tests lock the C1 Italian translation so the English source can't silently
resurface on the default (Italian) site.
"""

from __future__ import annotations

import pytest
from django.test import Client

# English source fragments that MUST NOT appear on the default Italian site.
ENGLISH_RESIDUES = [
    "Bodily injury claims",
    "guarantee of outcome",
    "the Studio reviews each case manually",
    "preliminary indicative assessment",
    "without any automatic engagement",
    "validated legal sources",
    "Professional engagement",
]

# Italian markers that SHOULD appear (glossary terms from the C1 translation).
IT_MARKERS = [
    "garanzia di risultato",
    "valutazione",
]

LANDINGS = [
    "/case-types/road-accident/",
    "/case-types/bodily-injury/",
    "/case-types/insurance-offer-review/",
    "/case-types/work-injury/",
    "/case-types/medical-malpractice/",
    "/case-types/death-of-relative/",
    "/case-types/foreigners-in-italy/",
    "/case-types/cross-border-cases/",
]


@pytest.mark.django_db
@pytest.mark.parametrize("path", LANDINGS)
def test_landing_has_no_english_residue(path):
    body = Client().get(path).content.decode("utf-8")
    for residue in ENGLISH_RESIDUES:
        assert residue not in body, f"English residue {residue!r} still on {path}"


@pytest.mark.django_db
def test_landing_renders_italian_markers():
    body = Client().get("/case-types/bodily-injury/").content.decode("utf-8")
    for marker in IT_MARKERS:
        assert marker in body, f"expected Italian marker {marker!r} on bodily-injury landing"


@pytest.mark.django_db
def test_mandate_notice_is_italian_on_result_is_covered_elsewhere():
    """The mandate notice IT rendering is asserted in
    apps/compliance/test_mandate_scaffold.py; kept here as a pointer so the
    public-i18n surface is discoverable from one place."""
    assert True
