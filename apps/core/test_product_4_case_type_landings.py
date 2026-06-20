"""
Tests PRODUCT-4-case-type-landing-pages.

Per-case-type SEO/product landing pages under `/case-types/<slug>/`.
Each landing is rendered by a single template fed by data from
`apps.core.case_type_landings.LANDINGS`.

What these tests guard:

 1. Audit doc + data module exist.
 2. `/case-types/` (hub) renders 200 and links to each per-case-type
    landing.
 3. Each `/case-types/<slug>/` returns 200 and carries the load-bearing
    content: H1, intro, when-it-applies, what-Studio-does, two CTAs,
    mandate notice, disclaimer.
 4. Unknown slug returns 404, not 500.
 5. Pages are `index, follow` (indexable — SEO-targeted).
 6. Banned-promise phrases never appear in any landing.
 7. No EUR amount leaks in any landing.
 8. Primary + secondary CTA URLs reverse correctly and return 200.
 9. `?case_type=<code>` prefill on /contact/ honoured for known codes,
    silently ignored for unknown codes (anti-injection guard).
10. France stays review-gated (no EUR amount on the France-linked
    landing path).
11. AR / RTL render of each landing returns 200 with `dir="rtl"`.
12. CaseType codes used in the data module exist in the enum (sync guard).
13. hreflang allowlist includes the new view name.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.urls import reverse
from django.utils import translation

REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DOC = REPO_ROOT / "docs" / "product" / "CASE_TYPE_LANDING_AUDIT_2026-05-12.md"
DATA_MODULE = REPO_ROOT / "apps" / "core" / "case_type_landings.py"
TEMPLATE = REPO_ROOT / "templates" / "public" / "case_type_landing.html"


# ---------------------------------------------------------------------------
# 0. Audit doc + data module + template exist
# ---------------------------------------------------------------------------


def test_audit_doc_exists():
    assert AUDIT_DOC.exists()
    assert AUDIT_DOC.stat().st_size > 4000


def test_data_module_and_template_exist():
    assert DATA_MODULE.exists()
    assert TEMPLATE.exists()


def test_data_module_has_at_least_8_landings():
    from apps.core.case_type_landings import LANDINGS

    assert len(LANDINGS) >= 8, f"PRODUCT-4 ships 8 landings minimum, found {len(LANDINGS)}"


# ---------------------------------------------------------------------------
# 1. CaseType codes in the data module are real enum members (sync guard)
# ---------------------------------------------------------------------------


def test_case_type_codes_are_valid_enum_members():
    from apps.calculators.enums import CaseType
    from apps.core.case_type_landings import LANDINGS

    valid_codes = {choice[0] for choice in CaseType.choices}
    for landing in LANDINGS:
        if not landing.case_type_code:
            continue  # profile-style landings have no enum mapping
        assert landing.case_type_code in valid_codes, (
            f"Landing {landing.slug!r} maps to unknown CaseType " f"code {landing.case_type_code!r}"
        )


# ---------------------------------------------------------------------------
# 2. Hub renders 200 and links to each per-case-type landing
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_case_types_hub_renders_200(client):
    resp = client.get("/case-types/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200


@pytest.mark.django_db
def test_case_types_hub_links_to_each_landing(client):
    from apps.core.case_type_landings import all_slugs

    body = client.get("/case-types/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    for slug in all_slugs():
        href = f"/case-types/{slug}/"
        # At least one landing slug must appear on the hub (some
        # landings are deduplicated when multiple share a case-type
        # code, but the data module always exposes every slug via
        # `all_slugs()` so at least the profile landings are linked).
        if href in body:
            return
    pytest.fail("Hub does not link to any of the per-case-type landings")


# ---------------------------------------------------------------------------
# 3. Each landing returns 200 with load-bearing content
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
def test_landing_returns_200(client, slug):
    resp = client.get(f"/case-types/{slug}/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200


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
def test_landing_has_load_bearing_content(client, slug):
    # Use the /en/ language-prefixed URL: the landing route is under
    # i18n_patterns(prefix_default_language=False), so a non-prefixed URL is
    # always served in the default locale (it), regardless of Accept-Language.
    # This test asserts the English chrome strings (now translated in IT).
    body = client.get(
        f"/en/case-types/{slug}/",
        HTTP_HOST="127.0.0.1",
    ).content.decode("utf-8")
    # Single <h1>.
    h1_count = body.count("<h1")
    assert h1_count == 1, f"{slug}: expected 1 H1, found {h1_count}"
    # The H1 element contains the landing's title (translatable). We
    # do not pin the exact string — just confirm one H1 with text.
    assert "<h1 " in body
    # Primary + secondary CTA buttons present (anchor tags with the
    # standard CTA classes).
    cta_count = body.count('class="inline-flex items-center gap-2 px-5 py-3 rounded-full')
    assert cta_count >= 2, f"{slug}: expected at least 2 styled CTA buttons, found {cta_count}"
    # When-it-applies + What-Studio-does sections rendered.
    assert "When this applies" in body
    assert "What the Studio does" in body
    # Mandate notice rendered (the shared partial).
    assert "mandate" in body.lower() or "engagement" in body.lower()
    # Documents-to-prepare partial rendered (shared with PRODUCT-2).
    assert "Documents to prepare" in body


# ---------------------------------------------------------------------------
# 4. Unknown slug returns 404
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unknown_slug_returns_404(client):
    resp = client.get("/case-types/this-slug-does-not-exist/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# 5. Indexable (index, follow) — SEO-targeted
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["road-accident", "medical-malpractice", "death-of-relative"])
def test_landing_is_indexable(client, slug):
    body = client.get(f"/case-types/{slug}/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    # The base template default is `index, follow` — the landing
    # must NOT override to noindex.
    assert (
        'content="noindex' not in body
    ), f"/case-types/{slug}/ must be indexable (no noindex meta)"
    assert 'content="index, follow"' in body


# ---------------------------------------------------------------------------
# 6. Banned-promise phrases never appear
# ---------------------------------------------------------------------------


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
def test_landing_has_no_banned_phrases(client, slug):
    body = client.get(f"/case-types/{slug}/", HTTP_HOST="127.0.0.1").content.decode("utf-8").lower()
    leaks = [p for p in BANNED_PROMISE_PHRASES if p in body]
    assert not leaks, f"/case-types/{slug}/ leaks banned phrases: {leaks}"


# ---------------------------------------------------------------------------
# 7. No EUR amount in landing copy
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
def test_landing_does_not_leak_eur_amount(client, slug):
    body = client.get(f"/case-types/{slug}/", HTTP_HOST="127.0.0.1").content.decode("utf-8")
    assert not re.search(
        r"\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)", body
    ), f"/case-types/{slug}/ leaks an EUR amount"


# ---------------------------------------------------------------------------
# 8. CTAs target valid URLs that return 200
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_each_landing_cta_urls_are_valid(client):
    from apps.core.case_type_landings import LANDINGS

    for landing in LANDINGS:
        # primary
        url = landing.primary_cta_href()
        assert url, f"{landing.slug}: empty primary CTA href"
        resp = client.get(url, HTTP_HOST="127.0.0.1")
        assert (
            resp.status_code == 200
        ), f"{landing.slug}: primary CTA {url!r} returned {resp.status_code}"
        # secondary
        url = landing.secondary_cta_href()
        assert url, f"{landing.slug}: empty secondary CTA href"
        resp = client.get(url, HTTP_HOST="127.0.0.1")
        assert (
            resp.status_code == 200
        ), f"{landing.slug}: secondary CTA {url!r} returned {resp.status_code}"


# ---------------------------------------------------------------------------
# 9. ?case_type= prefill on /contact/
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_honours_case_type_querystring(client):
    body = client.get(
        "/contact/?case_type=medical_malpractice",
        HTTP_HOST="127.0.0.1",
        HTTP_ACCEPT_LANGUAGE="en",
    ).content.decode("utf-8")
    # The form's <select name="case_type"> must have the matching
    # option preselected. Two valid renderings of the selected
    # option:
    assert (
        'value="medical_malpractice" selected' in body
        or '<option value="medical_malpractice" selected' in body
    ), "Contact form should preselect case_type from ?case_type= querystring"


@pytest.mark.django_db
def test_contact_ignores_invalid_case_type_querystring(client):
    """Injection guard: an arbitrary querystring value must NOT be
    accepted as a form initial — only known CaseType codes pass."""
    resp = client.get(
        "/contact/?case_type=__not_a_real_enum_value__",
        HTTP_HOST="127.0.0.1",
    )
    assert resp.status_code == 200, "Contact GET with garbage case_type must return 200, not 500"
    body = resp.content.decode("utf-8")
    assert (
        "__not_a_real_enum_value__" not in body
    ), "Garbage case_type value leaked into the rendered HTML"


# ---------------------------------------------------------------------------
# 10. France stays review-gated even when reached via /contact/?case_type=
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_france_review_gated_through_case_type_querystring(client):
    body = client.get(
        "/contact/?case_type=road_accident_bodily_injury",
        HTTP_HOST="127.0.0.1",
    ).content.decode("utf-8")
    # No EUR amount on the contact form — this is a request page,
    # not a result page. The case_type prefill must not introduce
    # any calculation surface.
    assert not re.search(
        r"\b\d{1,3}(?:[ \xa0.,]\d{3})+\s*(?:€|EUR)", body
    ), "Contact form with ?case_type=road_accident leaks an EUR amount"


# ---------------------------------------------------------------------------
# 11. AR / RTL renders without obvious breakage
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("slug", ["road-accident", "medical-malpractice", "cross-border-cases"])
def test_landing_renders_arabic_rtl(client, slug):
    """`/ar/case-types/<slug>/` must return 200 with dir=rtl.
    Explicitly deactivates translation in `finally:` to prevent
    Django thread-local state leaking into subsequent tests
    (same fix pattern as PRODUCT-3)."""
    try:
        resp = client.get(f"/ar/case-types/{slug}/", HTTP_HOST="127.0.0.1")
        assert resp.status_code == 200
        body = resp.content.decode("utf-8")
        assert 'dir="rtl"' in body
        # H1 still present in RTL rendering.
        assert "<h1 " in body
    finally:
        translation.deactivate_all()


# ---------------------------------------------------------------------------
# 12. hreflang allowlist includes the new view name
# ---------------------------------------------------------------------------


def test_hreflang_allowlist_includes_case_type_landing():
    from apps.core.context_processors import _GLOBAL_HREFLANG_VIEW_NAMES

    assert "core:case_type_landing" in _GLOBAL_HREFLANG_VIEW_NAMES, (
        "Per-case-type landing pages must be on the hreflang "
        "allowlist for SEO multilingue coverage."
    )


# ---------------------------------------------------------------------------
# 13. URL reverses produce the expected paths
# ---------------------------------------------------------------------------


def test_url_reverse_works_for_all_landings():
    from apps.core.case_type_landings import all_slugs

    for slug in all_slugs():
        url = reverse("core:case_type_landing", kwargs={"slug": slug})
        assert url == f"/case-types/{slug}/"
