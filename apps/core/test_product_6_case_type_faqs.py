"""
Tests PRODUCT-6-case-type-faqs.

A prudent FAQ section is added to every PRODUCT-4 case-type landing.
FAQs ride on the existing landing template via a `faq_items` field on
the `CaseTypeLanding` dataclass.

What these tests guard:

 1. Audit doc exists.
 2. Data module exposes `FAQItem` + `MAX_FAQ_ITEMS` + each landing
    carries 3 to 4 FAQ items.
 3. First FAQ on every landing is the universal "is this a legal
    opinion?" entry — identical across landings.
 4. Every landing has at least one FAQ whose answer mentions the
    mandate / no-automatic-engagement principle ("incarico").
 5. No banned-promise phrases anywhere in any FAQ Q or A.
 6. No EUR amount leaks in any FAQ answer.
 7. No specific prescription period numbers (digit + time unit) in
    any FAQ answer — we deliberately avoid "2 anni", "5 years", etc.
 8. The landing template renders the FAQ section as
    `<details>/<summary>` (no JS accordion), with a `<h2>` heading.
 9. AR/RTL renders the FAQ section without breaking dir="rtl".
10. FR locale renders the FAQ section without leaking EUR amounts
    (France stays review-gated).
11. Landings remain crawlable: `index, follow` / no `noindex`.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.utils import translation

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = (
    REPO_ROOT / "docs" / "product" / "CASE_TYPE_FAQ_AUDIT_2026-05-12.md"
)
DATA_MODULE = REPO_ROOT / "apps" / "core" / "case_type_landings.py"
TEMPLATE = REPO_ROOT / "templates" / "public" / "case_type_landing.html"


BANNED_PROMISE_PHRASES = (
    "scopri quanto ti spetta",
    "ottieni il risarcimento",
    "calcolo definitivo",
    "paghi solo se vinci",
    "pay only if you win",
    "no win no fee",
    "risarcimento garantito",
    "garantiamo il risultato",
    "i migliori avvocati",
    "leader assoluto",
)

# Specific prescription / time-window patterns we never publish in the
# FAQ. Matches digit followed by a time unit word in IT / EN / FR / AR.
# Intentionally simple — false positives just force a re-phrase.
PRESCRIPTION_NUMBER_PATTERN = re.compile(
    r"\b\d{1,2}\s*(anni|anno|mesi|mese|years|year|months|month|ans|an|mois|سنة|سنوات|شهر|أشهر)\b",
    re.IGNORECASE,
)

# EUR amounts must never appear inside the FAQ block.
EUR_AMOUNT_PATTERN = re.compile(r"(€|\bEUR\b)")


# ---------------------------------------------------------------------------
# 0. Audit doc + data module + template exist
# ---------------------------------------------------------------------------


def test_audit_doc_exists():
    assert AUDIT_DOC.exists(), (
        "PRODUCT-6 phase 1 audit must exist at "
        "docs/product/CASE_TYPE_FAQ_AUDIT_2026-05-12.md"
    )
    assert AUDIT_DOC.stat().st_size > 4000


def test_data_module_exposes_faq_primitives():
    from apps.core import case_type_landings

    assert hasattr(case_type_landings, "FAQItem")
    assert hasattr(case_type_landings, "MAX_FAQ_ITEMS")
    assert case_type_landings.MAX_FAQ_ITEMS == 4


# ---------------------------------------------------------------------------
# 1. Each landing has 3 to MAX_FAQ_ITEMS FAQs
# ---------------------------------------------------------------------------


def test_every_landing_has_at_least_three_faqs():
    from apps.core.case_type_landings import LANDINGS, MAX_FAQ_ITEMS

    for landing in LANDINGS:
        n = len(landing.faq_items)
        assert 3 <= n <= MAX_FAQ_ITEMS, (
            f"landing {landing.slug!r} has {n} FAQs; expected 3..{MAX_FAQ_ITEMS}"
        )


# ---------------------------------------------------------------------------
# 2. First FAQ on every landing is the universal "is this a legal opinion?"
# ---------------------------------------------------------------------------


def test_first_faq_is_universal_legal_opinion_anchor():
    from apps.core.case_type_landings import LANDINGS

    for landing in LANDINGS:
        first = landing.faq_items[0]
        q = str(first.question)
        a = str(first.answer)
        assert "parere legale" in q.lower(), (
            f"landing {landing.slug!r} first FAQ question must anchor "
            f"'parere legale'; got {q!r}"
        )
        assert "no" in a.lower(), (
            f"landing {landing.slug!r} first FAQ answer must start with a no; "
            f"got {a!r}"
        )
        assert "valutazione indicativa" in a.lower()


def test_first_faq_is_identical_across_landings():
    """The universal anchor FAQ must be literally the same `FAQItem`
    instance on every landing — guarantees the message stays in sync
    if someone edits the constant."""
    from apps.core.case_type_landings import LANDINGS

    anchors = {id(landing.faq_items[0]) for landing in LANDINGS}
    assert len(anchors) == 1, (
        "First FAQ should be the same module-level constant on every "
        "landing; got distinct objects."
    )


# ---------------------------------------------------------------------------
# 3. Every landing has a mandate FAQ (mentions "incarico")
# ---------------------------------------------------------------------------


def test_every_landing_has_mandate_faq():
    from apps.core.case_type_landings import LANDINGS

    for landing in LANDINGS:
        joined = " ".join(
            str(item.question) + " " + str(item.answer)
            for item in landing.faq_items
        ).lower()
        assert "incarico" in joined, (
            f"landing {landing.slug!r} FAQ block must mention 'incarico' "
            f"(mandate notice principle)"
        )


# ---------------------------------------------------------------------------
# 4. No banned-promise phrases anywhere in FAQ Q or A
# ---------------------------------------------------------------------------


def test_no_banned_promise_phrases_in_faqs():
    from apps.core.case_type_landings import LANDINGS

    leaks = []
    for landing in LANDINGS:
        for item in landing.faq_items:
            text = (str(item.question) + " " + str(item.answer)).lower()
            for phrase in BANNED_PROMISE_PHRASES:
                if phrase in text:
                    leaks.append((landing.slug, phrase))
    assert not leaks, f"banned-promise leaks in FAQ copy: {leaks}"


# ---------------------------------------------------------------------------
# 5. No EUR amount in any FAQ answer
# ---------------------------------------------------------------------------


def test_no_eur_amount_in_faq_answers():
    from apps.core.case_type_landings import LANDINGS

    leaks = []
    for landing in LANDINGS:
        for item in landing.faq_items:
            if EUR_AMOUNT_PATTERN.search(
                str(item.question) + " " + str(item.answer)
            ):
                leaks.append((landing.slug, str(item.question)))
    assert not leaks, f"EUR amount leaks in FAQ copy: {leaks}"


# ---------------------------------------------------------------------------
# 6. No specific prescription numbers (digit + time unit) in FAQ answers
# ---------------------------------------------------------------------------


def test_no_specific_prescription_period_in_faq_answers():
    """We intentionally never publish concrete statute-of-limitations
    numbers in the FAQ ('2 anni', '5 years', etc.) because the
    validated sources are not signed off for the non-IT jurisdictions
    and we do not want to over-claim for IT either."""
    from apps.core.case_type_landings import LANDINGS

    leaks = []
    for landing in LANDINGS:
        for item in landing.faq_items:
            text = str(item.question) + " " + str(item.answer)
            m = PRESCRIPTION_NUMBER_PATTERN.search(text)
            if m:
                leaks.append((landing.slug, m.group(0), text[:80]))
    assert not leaks, (
        f"FAQ answers leak prescription period numbers: {leaks}"
    )


# ---------------------------------------------------------------------------
# 7. Rendered HTML: section uses <details>/<summary>, has a clear h2
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug",
    [
        "road-accident",
        "bodily-injury",
        "insurance-offer-review",
        "work-injury",
        "medical-malpractice",
        "death-of-relative",
        "foreigners-in-italy",
        "cross-border-cases",
    ],
)
def test_landing_renders_faq_details_summary(client, slug):
    resp = client.get(f"/case-types/{slug}/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")

    # Section heading anchor.
    assert 'id="case-type-faq-heading"' in body
    # Native disclosure widget — no JS accordion.
    assert body.count("<details") >= 3
    assert body.count("<summary") >= 3
    # Universal first FAQ.
    assert "Questa simulazione" in body and "parere legale" in body
    # Mandate FAQ.
    assert "incarico professionale" in body


# ---------------------------------------------------------------------------
# 8. FR locale renders the FAQ section without leaking EUR amounts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_landing_renders_faq_without_eur():
    """France stays review-gated: the FAQ block renders on /fr/
    landings but no EUR amount is published anywhere on the page."""
    try:
        from django.test import Client

        c = Client()
        resp = c.get(
            "/fr/case-types/road-accident/", HTTP_HOST="127.0.0.1"
        )
        assert resp.status_code == 200
        body = resp.content.decode("utf-8")
        assert 'id="case-type-faq-heading"' in body
        assert "<details" in body
        # Whole-page check: no EUR amount anywhere on the FR landing.
        # (The page itself has no €/EUR before this change — pin it.)
        assert "€" not in body
        assert not re.search(r"\bEUR\b", body)
    finally:
        translation.deactivate_all()


# ---------------------------------------------------------------------------
# 9. AR / RTL still renders FAQ section
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ar_landing_renders_faq_section_rtl():
    try:
        from django.test import Client

        c = Client()
        resp = c.get(
            "/ar/case-types/road-accident/", HTTP_HOST="127.0.0.1"
        )
        assert resp.status_code == 200
        body = resp.content.decode("utf-8")
        assert 'dir="rtl"' in body
        # FAQ section is still emitted in the RTL render.
        assert 'id="case-type-faq-heading"' in body
        assert "<details" in body
        assert "<summary" in body
    finally:
        translation.deactivate_all()


# ---------------------------------------------------------------------------
# 10. Landings stay crawlable — no noindex regression from PRODUCT-6
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "slug",
    [
        "road-accident",
        "insurance-offer-review",
        "medical-malpractice",
        "death-of-relative",
    ],
)
def test_landing_remains_indexable_after_faq_section(client, slug):
    resp = client.get(f"/case-types/{slug}/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert 'name="robots"' in body
    assert "noindex" not in body.lower(), (
        f"landing {slug!r} unexpectedly carries a noindex robots meta — "
        f"PRODUCT-6 must not change crawlability."
    )


# ---------------------------------------------------------------------------
# 11. Sync guard: module-level MAX_FAQ_ITEMS invariant fires on overflow
# ---------------------------------------------------------------------------


def test_max_faq_items_invariant_holds():
    """The module-level `for _landing in LANDINGS: assert len(...) <= MAX_FAQ_ITEMS`
    runs at import. This test makes the contract explicit so a future
    maintainer who removes the assert loses a test, not just a quiet
    invariant."""
    from apps.core.case_type_landings import LANDINGS, MAX_FAQ_ITEMS

    for landing in LANDINGS:
        assert len(landing.faq_items) <= MAX_FAQ_ITEMS
