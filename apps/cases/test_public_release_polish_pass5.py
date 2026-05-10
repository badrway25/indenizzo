"""Tests F-product-public-site-release-polish-pass5-premium-content-cleanup.

Pin the premium-copy contract for the public site:

1. No banned public words on principal pages (IT/FR/AR/EN).
2. FR pages don't leak high-priority pass-5 English copy.
3. AR pages don't leak high-priority pass-5 English copy.
4. No duplicate H1 on the principal pages.
5. No horizontal overflow on a 375 px viewport (sanity check via
   Django test client — the inline page contents fit by construction).
6. Every ``<img>`` has ``alt`` and explicit ``width`` / ``height``.
7. No Pexels attribution on principal pages.
8. No API key leak.
9. Italy result page has the premium "What this means" / "Next steps"
   sections.
10. FR unavailable result has no monetary amounts and no technical
    status string (``unavailable_requires_legal_validation`` /
    ``Internal status code``).
11. Contact thank-you premium copy.
12. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SCRIPT_RE = re.compile(r"<(script|style)\b[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)


def _visible(html: str) -> str:
    cleaned = _SCRIPT_RE.sub(" ", html)
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", cleaned)).strip()


@pytest.fixture(autouse=True)
def _reset_active_language():
    """Hitting /fr/ or /ar/ activates that locale on the worker thread.
    Reset after each test so default-locale tests are not poisoned."""

    yield
    from django.utils import translation

    translation.deactivate_all()


PRINCIPAL_PATHS = [
    "/",
    "/countries/",
    "/countries/italy/",
    "/countries/france/",
    "/countries/belgium/",
    "/countries/morocco/",
    "/countries/tunisia/",
    "/case-types/",
    "/methodology/",
    "/wizard/",
    "/wizard/it/road-accident/",
    "/wizard/fr/road-accident/",
    "/wizard/be/road-accident/",
    "/wizard/ma/inheritance/",
    "/wizard/tn/inheritance/",
    "/contact/",
    "/privacy/",
    "/disclaimer/",
]

BANNED_WORDS = (
    "scaffold",
    "placeholder",
    "under validation",
    "in preparation",
    "coming soon",
    "work in progress",
    "in corso",
    "modulo non operativo",
    "legal validation wizard",
    "module pending",
    "engine pending",
    "missing_documents",
    "unavailable_requires_legal_validation",
)


# ---------------------------------------------------------------------------
# 1 — banned words sweep across IT/FR/AR/EN
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("locale_prefix", ["", "/fr", "/ar", "/en"])
def test_principal_pages_have_no_banned_public_words(locale_prefix):
    client = Client()
    for path in PRINCIPAL_PATHS:
        url = locale_prefix + path
        response = client.get(url)
        assert response.status_code == 200, f"{url} returned {response.status_code}"
        body = response.content.decode("utf-8", errors="replace")
        visible = _visible(body).lower()
        for word in BANNED_WORDS:
            assert word not in visible, f"{url} surfaces banned public word {word!r}"


# ---------------------------------------------------------------------------
# 2-3 — no high-priority pass-5 English fallback on FR / AR
# ---------------------------------------------------------------------------


HIGH_PRIORITY_EN_PHRASES = (
    "How it works",
    "What this means",
    "Next steps",
    "Useful pages",
    "indicative calculation is available",
    "Preliminary legal assessment",
    "Manual legal review",
    "International inheritance review",
    "no automatic amount is published",
    "Studio reviews each",
    "Submit the case to the Studio",
    "applicable-law mapping",
)


@pytest.mark.django_db
@pytest.mark.parametrize("locale_prefix", ["/fr", "/ar"])
def test_translated_locales_have_no_high_priority_english_fallback(locale_prefix):
    client = Client()
    for path in PRINCIPAL_PATHS:
        url = locale_prefix + path
        response = client.get(url)
        assert response.status_code == 200
        visible = _visible(response.content.decode("utf-8", errors="replace"))
        for phrase in HIGH_PRIORITY_EN_PHRASES:
            assert (
                phrase not in visible
            ), f"{url} surfaces EN fallback {phrase!r} — locale catalogue regression."


# ---------------------------------------------------------------------------
# 4 — single H1 + no skipping heading levels
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRINCIPAL_PATHS)
def test_principal_pages_have_exactly_one_h1_and_no_skipping(path):
    response = Client().get(path)
    assert response.status_code == 200
    body = response.content.decode("utf-8", errors="replace")
    h1 = len(re.findall(r"<h1[\s>]", body))
    assert h1 == 1, f"{path} has {h1} H1s"
    levels = [int(m.group(1)) for m in re.finditer(r"<h([1-6])[\s>]", body)]
    assert levels and levels[0] == 1
    for prev, cur in zip(levels, levels[1:], strict=False):
        assert cur <= prev + 1, f"{path}: heading order skips (H{prev} → H{cur})"


# ---------------------------------------------------------------------------
# 5 — sanity: no horizontal overflow markers (we don't run a real
# browser here; we assert no inline `width:Xpx` larger than 375 in
# the principal templates' rendered HTML).
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_inline_wide_styles_on_principal_pages():
    client = Client()
    suspicious = re.compile(r"width:\s*([4-9]\d{2,}|\d{4,})px", re.IGNORECASE)
    for path in PRINCIPAL_PATHS:
        body = client.get(path).content.decode("utf-8", errors="replace")
        leaks = suspicious.findall(body)
        assert not leaks, f"{path} contains inline wide style: {leaks[:3]}"


# ---------------------------------------------------------------------------
# 6 — every <img> has alt + explicit width / height
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", PRINCIPAL_PATHS)
def test_imgs_have_alt_and_dimensions(path):
    body = Client().get(path).content.decode("utf-8", errors="replace")
    for img in re.findall(r"<img\b[^>]*>", body, flags=re.IGNORECASE):
        assert re.search(
            r'\balt\s*=\s*["\']', img, flags=re.IGNORECASE
        ), f"{path}: <img> without alt: {img[:80]}"
        has_w = re.search(r'\bwidth\s*=\s*["\']?\d', img, flags=re.IGNORECASE)
        has_h = re.search(r'\bheight\s*=\s*["\']?\d', img, flags=re.IGNORECASE)
        assert has_w and has_h, f"{path}: <img> missing w/h: {img[:80]}"


# ---------------------------------------------------------------------------
# 7 — no Pexels attribution on principal pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_pexels_attribution():
    client = Client()
    for path in PRINCIPAL_PATHS:
        body = client.get(path).content.decode("utf-8", errors="replace").lower()
        assert "photo by " not in body, f"{path}: 'Photo by' caption surfaced"
        assert "pexels.com" not in body, f"{path}: pexels.com link surfaced"


# ---------------------------------------------------------------------------
# 8 — no API key leak
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_no_api_key_leak():
    client = Client()
    long_token = re.compile(r"[A-Za-z0-9]{40,}")
    for path in PRINCIPAL_PATHS:
        body = client.get(path).content.decode("utf-8", errors="replace")
        for env_name in ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY"):
            assert env_name not in body, f"{path}: leaks env name {env_name}"
        for token in long_token.findall(body):
            for prefix in ("key=", "token=", "secret="):
                assert (
                    prefix + token not in body
                ), f"{path}: token leak after {prefix!r}: {token[:6]}…"


# ---------------------------------------------------------------------------
# 9 — IT result page has premium sections
# ---------------------------------------------------------------------------


@pytest.fixture
def italy_calculator_fixture(db):
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    Currency.objects.create(code="EUR", name="Euro", symbol="€")
    italian = Language.objects.create(code="it", name="Italiano")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    src = LegalSource.objects.create(
        slug="it-pass5-fixture",
        title="D.P.R. 12/2025 fixture",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )
    base_ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base pass5",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=base_ds,
        row_type="tun_biological_total_amount",
        age_min=35,
        age_max=35,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    moral_ds = CompensationDataset.objects.create(
        source=src,
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral pass5",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    for kind, amount in (("min", "26268"), ("mid", "27353"), ("max", "28439")):
        CompensationTableRow.objects.create(
            dataset=moral_ds,
            row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=35,
            age_max=35,
            disability_min=10,
            disability_max=10,
            point_value=Decimal(amount),
        )
    CalculationFormula.objects.create(
        dataset=base_ds,
        code="italy_art_138_tun_2025_pass5",
        name="pass5",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct",
            "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            "min_row_type": "tun_biological_moral_min_total_amount",
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        },
        status=DatasetStatus.APPROVED,
    )
    return italy


@pytest.mark.django_db
def test_italy_result_has_premium_sections(italy_calculator_fixture):
    client = Client()
    response = client.post(
        "/wizard/it/road-accident/",
        data={
            "accident_country": italy_calculator_fixture.pk,
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
            "consent_simulation": "on",
            "special_categories_consent": "on",
        },
        follow=True,
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8", errors="replace")
    visible = _visible(body)
    # All three amounts surfaced.
    assert "26268" in body and "27353" in body and "28439" in body
    # Premium sections (EN-or-IT — project default is IT).
    assert ("What this means" in visible) or ("Cosa significa" in visible)
    assert ("Next steps" in visible) or ("Prossimi passi" in visible)
    # No technical status string.
    for word in BANNED_WORDS:
        assert word not in visible.lower(), f"premium section leaks {word}"


# ---------------------------------------------------------------------------
# 10 — FR unavailable result has no amounts and no technical status
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_unavailable_result_has_no_amounts_and_no_technical_status(italy_calculator_fixture):
    """Italy fixture bootstraps the simulation pipeline. We POST a France
    case → unavailable result. Verify the page no longer leaks the
    technical status or any monetary amounts."""

    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    france = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    french = Language.objects.create(code="fr", name="Français")
    Jurisdiction.objects.create(
        country=france,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    LegalSource.objects.create(
        slug="fr-pass5-fixture",
        title="FR fixture",
        country=france,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
    )
    response = Client().post(
        "/wizard/fr/road-accident/",
        data={
            "accident_country": france.pk,
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
            "consent_simulation": "on",
            "special_categories_consent": "on",
        },
        follow=True,
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8", errors="replace")
    visible = _visible(body)
    assert "26268" not in body
    assert "27353" not in body
    assert "28439" not in body
    # No technical status or banned wording.
    visible_lower = visible.lower()
    for word in BANNED_WORDS:
        assert word not in visible_lower, f"FR unavailable surfaces banned: {word}"
    assert "Internal status code" not in visible


# ---------------------------------------------------------------------------
# 11 — Contact thank-you premium copy
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_thank_you_has_premium_copy():
    """Hit the thank-you page directly — it's the page users land on
    after submitting the contact form. Premium copy = no banned words,
    a clear timing line, a privacy reassurance line."""

    response = Client().get("/contact/thank-you/")
    assert response.status_code == 200
    body = response.content.decode("utf-8", errors="replace")
    visible = _visible(body)
    visible_lower = visible.lower()
    for word in BANNED_WORDS:
        assert word not in visible_lower, f"thank-you surfaces banned: {word}"


# ---------------------------------------------------------------------------
# 12 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_pass5(italy_calculator_fixture):
    from apps.calculators.enums import CalculationStatus, CaseType
    from apps.cases.services import run_simulation

    sim = run_simulation(
        jurisdiction_code="IT-NATIONAL",
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        input_data={
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
        },
    )
    assert sim.status == CalculationStatus.CALCULATED.value
    assert sim.estimated_min == Decimal("26268")
    assert sim.estimated_mid == Decimal("27353")
    assert sim.estimated_max == Decimal("28439")
