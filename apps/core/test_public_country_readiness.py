"""E1: public country readiness service + leak-guard tests.

Asserts the transparent unavailable-country flow stays fail-closed (FR/BE/MA/TN
never calculation-ready, no amounts) and — the centerpiece — that NO internal
review detail (hashes, paths, reviewer names, review notes, raw legal text, D1/D2
internals or the status slug) ever reaches a public surface.
"""

from __future__ import annotations

import json
import re

import pytest
from django.test import Client
from django.urls import reverse

from apps.core.country_readiness import (
    build_country_readiness,
    get_country_readiness,
    public_country_readiness,
)

# Tokens that must NEVER appear on a public surface.
FORBIDDEN = [
    "sha256",
    "content_hash",
    "unavailable_requires_legal_validation",
    "review_readiness",
    "review_evidence",
    "internal_reason",
    "legal_data/",
    "manual_attached",
    "official_source_validation",
    "reviewer=",
    "needs_review",
    "scaffold",
    "placeholder",
    "engine pending",
]
EUR_RE = re.compile(r"\d[\d.,]*\s*(?:EUR|€)")


def _get(path, lang_host="127.0.0.1"):
    return Client().get(path, HTTP_HOST=lang_host).content.decode("utf-8")


# --------------------------------------------------------------------------- #
# service
# --------------------------------------------------------------------------- #


def test_italy_is_available_and_can_calculate():
    r = get_country_readiness("IT")
    assert r.public_status == "available"
    assert r.can_calculate is True


@pytest.mark.parametrize("cc", ["FR", "BE", "MA", "TN"])
def test_non_italian_in_validation_cannot_calculate(cc):
    r = get_country_readiness(cc)
    assert r.public_status == "official_guided_path"
    assert r.can_calculate is False
    assert r.manual_review_available is True


def test_public_dict_never_exposes_internal_reason():
    for r in build_country_readiness():
        assert r.internal_reason  # present on the object (for logs/tests)
    for d in public_country_readiness():
        assert "internal_reason" not in d
        # only the public keys
        assert set(d.keys()) == {
            "country_code",
            "label",
            "public_status",
            "can_calculate",
            "public_message",
            "recommended_action",
            "manual_review_available",
        }


def test_can_calculate_matches_calculator_registry():
    """can_calculate must agree with the active (non-scaffold) registry."""
    from apps.calculators.registry import get_calculator

    # Italy has an active road-accident calculator; the others are scaffold-only.
    assert get_calculator("IT-NATIONAL", "road_accident_bodily_injury") is not None
    assert get_country_readiness("IT").can_calculate is True
    assert get_country_readiness("FR").can_calculate is False


# --------------------------------------------------------------------------- #
# readiness.json endpoint
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_readiness_json_endpoint():
    body = _get(reverse("core:country_readiness_json"))
    data = json.loads(body)
    by = {c["country_code"]: c for c in data["countries"]}
    assert by["IT"]["public_status"] == "available" and by["IT"]["can_calculate"] is True
    assert by["FR"]["public_status"] == "official_guided_path"
    assert by["FR"]["can_calculate"] is False
    for tok in FORBIDDEN:
        assert tok not in body, f"leak {tok!r} in readiness.json"


# --------------------------------------------------------------------------- #
# leak guard on rendered public pages
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    [
        "/countries/",
        "/countries/france/",
        "/countries/belgium/",
        "/countries/morocco/",
        "/countries/tunisia/",
        "/countries/italy/",
    ],
)
def test_public_country_pages_do_not_leak_internals(path):
    body = _get(path)
    for tok in FORBIDDEN:
        assert tok not in body, f"leak {tok!r} on {path}"


# --------------------------------------------------------------------------- #
# wizard unavailable: no amounts, no calculated status, no leak
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_fr_wizard_unavailable_no_amount_no_leak():
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="FR-NATIONAL",
        case_type="road_accident_bodily_injury",
        input_data={"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0},
    )
    assert sim.status != "calculated"
    assert sim.estimated_min is None and sim.estimated_mid is None and sim.estimated_max is None
    body = _get(f"/wizard/result/{sim.public_id}/")
    assert not EUR_RE.search(body), "FR unavailable result must show no amount"
    for tok in FORBIDDEN:
        assert tok not in body, f"leak {tok!r} on FR result"
    # the transparent flow keeps a manual-review CTA
    assert "/contact" in body


# --------------------------------------------------------------------------- #
# i18n: readiness copy resolves per language
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "lang,expected_label",
    [("it", "Francia"), ("fr", "France"), ("ar", "فرنسا")],
)
def test_readiness_label_translates(lang, expected_label):
    from django.utils import translation

    with translation.override(lang):
        assert str(get_country_readiness("FR").label) == expected_label
