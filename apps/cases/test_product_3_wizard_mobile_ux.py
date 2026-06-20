"""
Tests PRODUCT-3-wizard-mobile-ux.

Wizard UX improvements covered:

 1. Shared partial `_road_accident_wizard_form_fields.html` is in
    tree; the three country wizards (IT / FR / BE) include it.
 2. Each road-accident wizard renders the new "Essential
    information" fieldset legend AND the collapsed `<details>`
    "Additional details" block.
 3. Required-driving fields (accident_date, victim_age,
    permanent_disability_percentage) live OUTSIDE the <details>
    block; informational fields (ITT/ITP days, medical_expenses,
    lost_income, fault_percentage) live INSIDE the <details> block.
 4. Consents stay OUTSIDE the <details> block — never hidden
    behind the disclosure toggle.
 5. Italy wizard CTA copy is "Calculate indicative estimate"
    (sharpened from "Run simulation").
 6. France + Belgium wizards keep "Submit for legal review" CTA
    (correct for review-gated paths).
 7. Submitting the wizard with only consents (no domain fields)
    still succeeds — the "all domain fields optional" pattern is
    preserved.
 8. Submitting the wizard with all 8 domain fields still succeeds.
 9. France stays review-gated (no EUR amount leaks).
10. AR / RTL render of the wizard still returns 200 with dir="rtl".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "product" / "WIZARD_MOBILE_UX_AUDIT_2026-05-12.md"
PARTIAL = REPO_ROOT / "templates" / "public" / "_road_accident_wizard_form_fields.html"
WIZARD_IT = REPO_ROOT / "templates" / "public" / "wizard_italy_road_accident.html"
WIZARD_FR = REPO_ROOT / "templates" / "public" / "wizard_france_road_accident.html"
WIZARD_BE = REPO_ROOT / "templates" / "public" / "wizard_belgium_road_accident.html"


# ---------------------------------------------------------------------------
# 0. Audit doc + partial exist
# ---------------------------------------------------------------------------


def test_wizard_ux_audit_doc_exists():
    assert AUDIT_DOC.exists()
    assert AUDIT_DOC.stat().st_size > 4000


def test_road_accident_wizard_partial_exists():
    assert PARTIAL.exists()
    text = PARTIAL.read_text(encoding="utf-8")
    # Partial must reference the 3 essential fields AND the 5
    # optional ones — and it must mark the optional ones inside
    # `<details>`.
    assert "form.accident_date" in text
    assert "form.victim_age" in text
    assert "form.permanent_disability_percentage" in text
    assert "form.total_temporary_disability_days" in text
    assert "form.partial_temporary_disability_days" in text
    assert "form.medical_expenses" in text
    assert "form.lost_income" in text
    assert "form.fault_percentage" in text
    assert "<details" in text
    assert "<summary" in text


def test_road_accident_wizards_include_shared_partial():
    """All three country wizards must include the shared partial,
    NOT re-implement the fieldsets inline."""
    for wizard in (WIZARD_IT, WIZARD_FR, WIZARD_BE):
        text = wizard.read_text(encoding="utf-8")
        assert (
            "_road_accident_wizard_form_fields.html" in text
        ), f"{wizard.name} must include the shared field-rendering partial"
        # And the inlined fieldsets that were there before must be
        # gone — no fieldset legend "About the accident" /
        # "Documented economic impact" should appear directly in
        # the wizard template (they're now in the partial as
        # "Essential information" + "Additional details").
        assert (
            "Documented economic impact" not in text
        ), f"{wizard.name} still has inlined economic-impact fieldset"


# ---------------------------------------------------------------------------
# 1. Partial structure: <details> wraps only the optional fields
# ---------------------------------------------------------------------------


def _find_details_element_start(text: str) -> int:
    """Return the index of the real opening tag `<details ...>`,
    skipping any mention of `<details` inside `{% comment %}` blocks.
    Doc-comments in the partial mention the element by name."""
    body = re.sub(r"\{% comment %\}.*?\{% endcomment %\}", "", text, flags=re.DOTALL)
    offset_in_body = body.find("<details")
    assert offset_in_body >= 0, "partial must contain a real <details> element"
    # Translate back to the original-text offset.
    return text.find(body[offset_in_body : offset_in_body + 30])


def test_essential_fields_outside_details_block():
    """The 3 calculator-driving fields must appear BEFORE the
    real <details> element — otherwise they'd be hidden by
    default on mobile."""
    text = PARTIAL.read_text(encoding="utf-8")
    details_idx = _find_details_element_start(text)
    head = text[:details_idx]
    assert (
        "form.accident_date" in head
    ), "accident_date must be in the essential section, not in <details>"
    assert (
        "form.victim_age" in head
    ), "victim_age must be in the essential section, not in <details>"
    assert (
        "form.permanent_disability_percentage" in head
    ), "permanent_disability_percentage must be in the essential section"


def test_optional_fields_inside_details_block():
    """The 5 informational fields must be INSIDE the real <details>
    block so they collapse by default on mobile."""
    text = PARTIAL.read_text(encoding="utf-8")
    details_idx = _find_details_element_start(text)
    close_idx = text.rfind("</details>")
    assert close_idx > details_idx
    # Skip past the opening tag itself.
    tag_end = text.index(">", details_idx) + 1
    inside = text[tag_end:close_idx]
    for field in (
        "form.total_temporary_disability_days",
        "form.partial_temporary_disability_days",
        "form.medical_expenses",
        "form.lost_income",
        "form.fault_percentage",
    ):
        assert field in inside, (
            f"{field} must live inside the <details> block " "(collapsed by default)"
        )


# ---------------------------------------------------------------------------
# 2. Consents stay OUTSIDE the <details> block in every wizard
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("wizard_path", [WIZARD_IT, WIZARD_FR, WIZARD_BE])
def test_consents_outside_details_block(wizard_path):
    text = wizard_path.read_text(encoding="utf-8")
    # The consent partial is included in the country template,
    # outside the include of the shared partial. We assert the
    # include order: the consent partial appears AFTER the form-
    # fields partial in the source.
    fields_idx = text.find("_road_accident_wizard_form_fields.html")
    consent_idx = text.find("consent_checkboxes.html")
    assert fields_idx > 0
    assert consent_idx > 0
    assert consent_idx > fields_idx, (
        f"{wizard_path.name}: consent_checkboxes.html must be "
        "included AFTER the field partial, not inside it"
    )


# ---------------------------------------------------------------------------
# 3. CTA copy
# ---------------------------------------------------------------------------


def test_italy_wizard_cta_is_sharpened():
    text = WIZARD_IT.read_text(encoding="utf-8")
    assert "Calculate indicative estimate" in text, (
        "IT wizard must use the sharpened 'Calculate indicative " "estimate' CTA"
    )
    # The previous label must be gone.
    assert (
        "Run simulation" not in text
    ), "IT wizard still references the legacy 'Run simulation' CTA"


def test_france_and_belgium_cta_stays_review_gated():
    for wizard in (WIZARD_FR, WIZARD_BE):
        text = wizard.read_text(encoding="utf-8")
        assert "Submit for legal review" in text, (
            f"{wizard.name} must keep the 'Submit for legal review' "
            "CTA — it's review-gated, not calculating"
        )


# ---------------------------------------------------------------------------
# 4. Banned wording stays absent
# ---------------------------------------------------------------------------


# Marketing-promise phrases that must NOT appear in any wizard
# template. These are user-facing copy that would breach the
# deontological guardrail. We deliberately exclude phrases like
# "guaranteed payout" because the IT wizard explicitly says "NOT
# a guaranteed payout" — the negation is correct copy.
BANNED_PROMISE_PHRASES = (
    "scopri quanto ti spetta",
    "ottieni il risarcimento",
    "calcolo definitivo",
    "paghi solo se vinci",
    "pay only if you win",
    "no win no fee",
)


@pytest.mark.parametrize("wizard_path", [WIZARD_IT, WIZARD_FR, WIZARD_BE, PARTIAL])
def test_no_banned_marketing_promises(wizard_path):
    text = wizard_path.read_text(encoding="utf-8").lower()
    leaks = [p for p in BANNED_PROMISE_PHRASES if p in text]
    assert not leaks, f"{wizard_path.name} leaks banned phrases: {leaks}"


# ---------------------------------------------------------------------------
# 5. Form submit still works (consents-only + full-data paths)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_wizard_submit_with_only_consents(client):
    """The 'all domain fields optional' pattern is preserved:
    you can submit with only the two consents ticked."""
    resp = client.post(
        "/wizard/it/road-accident/",
        {
            "accident_country": "IT",
            "consent_simulation": "on",
            "special_categories_consent": "on",
        },
        HTTP_HOST="127.0.0.1",
        follow=False,
    )
    # Should redirect (302) to the result page, not re-render the
    # form with errors.
    assert resp.status_code == 302, (
        f"IT wizard rejected consents-only submit (status={resp.status_code}). "
        "Field-required regression — pattern broken."
    )


@pytest.mark.django_db
def test_italy_wizard_submit_with_all_fields(client):
    resp = client.post(
        "/wizard/it/road-accident/",
        {
            "accident_country": "IT",
            "accident_date": "2025-01-15",
            "victim_age": 40,
            "permanent_disability_percentage": "12.5",
            "total_temporary_disability_days": "30",
            "partial_temporary_disability_days": "15",
            "medical_expenses": "2500.00",
            "lost_income": "1800.00",
            "fault_percentage": "10",
            "consent_simulation": "on",
            "special_categories_consent": "on",
        },
        HTTP_HOST="127.0.0.1",
        follow=False,
    )
    assert (
        resp.status_code == 302
    ), f"IT wizard rejected full-fields submit (status={resp.status_code})"


@pytest.mark.django_db
def test_italy_wizard_submit_without_consents_is_rejected(client):
    """Sanity: consents are still required — the new layout did
    not accidentally make them optional."""
    resp = client.post(
        "/wizard/it/road-accident/",
        {
            "accident_country": "IT",
            "victim_age": 35,
        },
        HTTP_HOST="127.0.0.1",
        follow=False,
    )
    # Form re-renders with errors; status stays 200, not 302.
    assert resp.status_code == 200, "Wizard accepted submit without consents — required gate broke"


# ---------------------------------------------------------------------------
# 6. Live rendering: <details> + "Essential information" appear
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "/wizard/it/road-accident/",
        "/wizard/fr/road-accident/",
        "/wizard/be/road-accident/",
    ],
)
def test_wizard_renders_progressive_disclosure(client, url):
    # /en/ prefix: non-prefixed URLs render in the default locale (it). This
    # test asserts the English legend/toggle strings (now translated in IT).
    resp = client.get("/en" + url, HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    # The <details>/<summary> elements are rendered (native HTML).
    assert "<details" in body
    assert "<summary" in body
    # The data-attribute marker we added survives.
    assert "data-product-3-optional-details" in body
    # The "Essential information" legend appears.
    assert "Essential information" in body
    # The "Additional details" toggle text appears.
    assert "Additional details" in body


# ---------------------------------------------------------------------------
# 7. France stays review-gated
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_france_wizard_no_eur_amount_after_ux_refactor(client):
    body = client.get("/wizard/fr/road-accident/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    assert not re.search(r"\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)", body), (
        "FR wizard leaks a EUR amount after the UX refactor — "
        "review-gated state must be preserved"
    )


# ---------------------------------------------------------------------------
# 8. AR / RTL still renders the wizard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_arabic_wizard_renders_with_rtl(client):
    """Hitting an `/ar/...` URL activates Django's translation
    thread-local. The LocaleMiddleware normally deactivates on
    response, but the test client occasionally leaves the
    thread-local in the Arabic state, which then breaks
    subsequent tests that assume Italian. We explicitly
    deactivate after the assertions to keep test isolation."""
    from django.utils import translation

    try:
        resp = client.get("/ar/wizard/it/road-accident/", HTTP_HOST="127.0.0.1")
        assert resp.status_code == 200
        body = resp.content.decode("utf-8")
        assert 'dir="rtl"' in body
        # The new <details> partial must still render.
        assert "<details" in body
    finally:
        translation.deactivate_all()
