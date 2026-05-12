"""
Tests PRODUCT-1-france-activation-signoff-pack.

Documentation-only iter — France is still review-gated. The 4
Studio sign-offs documented in
`docs/product/FRANCE_ACTIVATION_SIGNOFF_PACK.md` have NOT arrived,
so the platform must continue to:

 1. render `/wizard/fr/road-accident/` (form accessible);
 2. NEVER publish a EUR amount on the FR public path;
 3. carry the "preliminary legal assessment" copy that points the
    user to manual Studio review;
 4. surface `unavailable_requires_legal_validation` semantics on
    POST;
 5. keep the 3 product docs in tree so the next iter has a clear
    starting point.

These tests guard against accidental promotion of the FR chain
without going through the documented signoff workflow. If a future
iter intentionally flips FR live, delete the relevant assertions
as part of that iter.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SIGNOFF_PACK = REPO_ROOT / "docs" / "product" / "FRANCE_ACTIVATION_SIGNOFF_PACK.md"
DEV_PLAN = REPO_ROOT / "docs" / "product" / "FRANCE_ACTIVATION_DEV_PLAN.md"
E2E_MATRIX = REPO_ROOT / "docs" / "product" / "FRANCE_E2E_TEST_MATRIX.md"
AUDIT_NON_IT_SCRIPT = (
    REPO_ROOT / "scripts" / "legal_data" / "audit_non_it_readiness.py"
)
AUDIT_READINESS_SCRIPT = (
    REPO_ROOT / "scripts" / "legal_data" / "audit_france_activation_readiness.py"
)
READINESS_AUDIT_DOC = (
    REPO_ROOT
    / "docs"
    / "architecture"
    / "FRANCE_ACTIVATION_READINESS_AUDIT.md"
)


# ---------------------------------------------------------------------------
# 1. The 3 product docs exist and are non-trivial
# ---------------------------------------------------------------------------


def test_signoff_pack_exists():
    assert SIGNOFF_PACK.exists()
    assert SIGNOFF_PACK.stat().st_size > 4000, (
        "FRANCE_ACTIVATION_SIGNOFF_PACK.md must be a substantive "
        "operational doc for Studio, not a stub."
    )


def test_dev_plan_exists():
    assert DEV_PLAN.exists()
    assert DEV_PLAN.stat().st_size > 3000


def test_e2e_matrix_exists():
    assert E2E_MATRIX.exists()
    assert E2E_MATRIX.stat().st_size > 3000


# ---------------------------------------------------------------------------
# 2. Signoff pack carries the 4 sign-offs the user mandated
# ---------------------------------------------------------------------------


def test_signoff_pack_lists_the_four_signatures():
    text = SIGNOFF_PACK.read_text(encoding="utf-8")
    # All four sources Studio must sign must be referenced by their
    # slugs OR human names.
    assert "Mornet 2024" in text or "fr-referentiel-mornet-2024" in text
    assert (
        "Gazette du Palais 2022" in text
        or "fr-bareme-capitalisation-gazette-palais-2022" in text
    )
    assert (
        "Dintilhac" in text or "fr-nomenclature-dintilhac-2005" in text
    )
    assert "Disclaimer" in text and "France" in text


def test_signoff_pack_states_no_calculation_without_signatures():
    """The doc must explicitly state the platform will NOT publish
    amounts before the signatures arrive. This is the golden rule
    the doc is meant to crystallise."""
    text = SIGNOFF_PACK.read_text(encoding="utf-8").lower()
    has_no_calc = any(
        phrase in text
        for phrase in (
            "meglio nessun calcolo che un calcolo falso",
            "non pubblica nessun numero",
            "no automatic amount",
            "nessun importo",
        )
    )
    assert has_no_calc, (
        "Signoff pack must explicitly state the no-amount rule"
    )


def test_signoff_pack_carries_at_least_three_smoke_test_cases():
    """The smoke contract — 3 test cases the Studio must sign
    numbers for — is the load-bearing artefact that turns a Studio
    review session into a deployable activation."""
    text = SIGNOFF_PACK.read_text(encoding="utf-8")
    # Look for the three canonical test-case input tuples from §7.
    matches = re.findall(r"35\s*[×x]\s*5\s*[×x]\s*0", text)
    assert matches, "Smoke case 1 (35×5×0) missing"
    matches = re.findall(r"45\s*[×x]\s*30\s*[×x]\s*0", text)
    assert matches, "Smoke case 2 (45×30×0) missing"
    matches = re.findall(r"60\s*[×x]\s*15\s*[×x]\s*25", text)
    assert matches, "Smoke case 3 (60×15×25) missing"


# ---------------------------------------------------------------------------
# 3. The dev plan and e2e matrix cross-reference the signoff pack
# ---------------------------------------------------------------------------


def test_dev_plan_references_signoff_pack():
    text = DEV_PLAN.read_text(encoding="utf-8")
    assert "FRANCE_ACTIVATION_SIGNOFF_PACK.md" in text


def test_e2e_matrix_references_signoff_pack():
    text = E2E_MATRIX.read_text(encoding="utf-8")
    assert "FRANCE_ACTIVATION_SIGNOFF_PACK.md" in text


def test_e2e_matrix_has_at_least_5_cases():
    text = E2E_MATRIX.read_text(encoding="utf-8")
    # Top-level numbered sections; case sections are `## N <something>`
    # for N >= 2 (section 1 is conventions, sections 2..8 are cases).
    case_headers = re.findall(r"^## \d+\b", text, re.MULTILINE)
    assert len(case_headers) >= 6, (
        f"E2E matrix must enumerate >=6 sections (1 conventions + "
        f">=5 cases), found {len(case_headers)}"
    )


# ---------------------------------------------------------------------------
# 4. The existing audit scripts are still in tree (we did not break them)
# ---------------------------------------------------------------------------


def test_audit_scripts_present():
    """The two read-only audit scripts that gate France activation
    must still be in tree — they are what the dev runs both
    before and after the signature."""
    assert AUDIT_NON_IT_SCRIPT.exists(), (
        "scripts/legal_data/audit_non_it_readiness.py is the canary "
        "for FR/BE/MA/TN readiness. Must not be deleted."
    )
    assert AUDIT_READINESS_SCRIPT.exists(), (
        "scripts/legal_data/audit_france_activation_readiness.py is "
        "the read-only audit referenced by the dev plan. Must not "
        "be deleted."
    )
    assert READINESS_AUDIT_DOC.exists(), (
        "docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md is "
        "the technical audit the Studio doc points at. Must not be "
        "deleted."
    )


# ---------------------------------------------------------------------------
# 5. France stays review-gated — no amount published on POST
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_france_wizard_get_is_accessible(client):
    resp = client.get("/wizard/fr/road-accident/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    # No EUR amount visible on the GET. (Allow page-meta numbers
    # like cache-busting hashes; we only check that no `<...EUR>`
    # or formatted-amount-with-euro pattern leaks.)
    assert not re.search(r"\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)", body), (
        "FR wizard GET leaks a formatted EUR amount in HTML — must "
        "stay review-gated until Studio signs Mornet/Gazette/Dintilhac"
    )


@pytest.mark.django_db
def test_france_wizard_post_returns_no_amount(client):
    """The 3 canonical smoke inputs all currently land on the
    review-gated path because no FR formula is APPROVED in the
    dev DB. This pins the contract: no amount until signature."""
    smoke_inputs = [
        # (victim_age, permanent_disability_percentage, fault_percentage)
        (35, 5, 0),
        (45, 30, 0),
        (60, 15, 25),
    ]
    for age, disability, fault in smoke_inputs:
        resp = client.post(
            "/wizard/fr/road-accident/",
            {
                "accident_country": "FR",
                "victim_age": age,
                "permanent_disability_percentage": disability,
                "fault_percentage": fault,
            },
            HTTP_HOST="127.0.0.1",
            follow=True,
        )
        # The wizard renders either the form (with validation
        # errors) or the result page. Either way no EUR amount
        # must appear pre-activation.
        body = resp.content.decode("utf-8")
        assert not re.search(
            r"\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)", body
        ), (
            f"FR POST {age=}, {disability=}, {fault=} leaked a EUR "
            f"amount. Must stay review-gated until activation."
        )


# ---------------------------------------------------------------------------
# 6. Banned-wording lint — the wizard copy stays in the
# "preliminary legal assessment" register, not in dev terminology
# ---------------------------------------------------------------------------


BANNED_USER_FACING_PHRASES = (
    "scaffold",
    "placeholder",
    "engine pending",
    "module pending",
    "in preparation",
    "coming soon",
    "work in progress",
    "in corso",
    "unavailable_requires_legal_validation",
    "legal validation wizard",
)


@pytest.mark.django_db
def test_france_wizard_uses_studio_copy_not_dev_terminology(client):
    body = client.get(
        "/wizard/fr/road-accident/", HTTP_HOST="127.0.0.1"
    ).content.decode("utf-8").lower()
    leaks = [p for p in BANNED_USER_FACING_PHRASES if p in body]
    assert not leaks, (
        f"FR wizard leaks dev-ese terms in user-facing HTML: {leaks}. "
        "User copy must stay in the 'preliminary legal assessment' "
        "register — see apps/core/public_status.py."
    )
