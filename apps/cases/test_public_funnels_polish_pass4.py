"""Tests F-product-public-funnels-polish-pass4-a11y-perf-i18n.

Cover the i18n / a11y / perf hardening of pass-4:

1. FR wizard start renders the FR translation of "How it works" and
   does NOT leak the EN string in visible body text.
2. AR wizard start renders the AR translation and does NOT leak EN
   "How it works".
3. FR contact renders the FR translation of "Useful pages".
4. AR contact renders the AR translation of "Useful pages" AND of the
   four multi-line blocktranslates that fell back to EN before pass-4
   ("What happens next", "A lawyer of the Studio reads your message
   manually …", "You receive a written reply …", "If your case fits
   our scope …").
5. FR result (calculated, IT engine) translates "What this means" and
   "Next steps" cards.
6. AR result (unavailable, FR scaffold) translates the contact CTA.
7. Each public funnel page has exactly one ``<h1>`` and no duplicate
   H1s.
8. The base layout exposes a global ``:focus-visible`` ring style so
   keyboard users see focus on every CTA.
9. No Pexels attribution surfaces on FR / AR funnels.
10. No API key leaks on FR / AR funnels.
11. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.
"""

from __future__ import annotations

import re
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse

REPO_ROOT = Path(__file__).resolve().parents[2]
LOCALE_DIR = REPO_ROOT / "locale"


@pytest.fixture(autouse=True)
def _reset_active_language():
    """Hitting /fr/ or /ar/ URLs activates that language on the worker
    thread via LocaleMiddleware. Without an explicit reset, the active
    language leaks into subsequent tests in the same process and breaks
    any test that asserts default-locale (it/en) copy. Always reset
    after the test runs."""

    yield
    from django.utils import translation

    translation.deactivate_all()


@pytest.fixture
def italy_calculator_fixture(db):
    """Same shape as pass-3: 35/10/0 → 26 268 / 27 353 / 28 439 EUR."""
    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
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
        slug="it-fixture-pass4-funnels",
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
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base pass4",
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
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral pass4",
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
        code="italy_art_138_tun_2025_pass4",
        name="pass4-funnels",
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
    return {"italy": italy}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _visible_text(html: str) -> str:
    return _WS_RE.sub(" ", _TAG_RE.sub(" ", html)).strip()


# ---------------------------------------------------------------------------
# 1 — FR wizard start: FR copy renders, no EN fallback
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_wizard_start_translates_how_it_works():
    response = Client().get("/fr/wizard/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    visible = _visible_text(body)
    assert "Comment ça marche" in visible, "FR wizard should show 'Comment ça marche'"
    assert (
        "How it works" not in visible
    ), "FR wizard still leaks EN 'How it works' — locale catalogue regression."


# ---------------------------------------------------------------------------
# 2 — AR wizard start: AR copy renders, no EN fallback
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ar_wizard_start_translates_how_it_works():
    response = Client().get("/ar/wizard/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    visible = _visible_text(body)
    assert "كيف يعمل" in visible, "AR wizard should show 'كيف يعمل' (How it works)"
    assert (
        "How it works" not in visible
    ), "AR wizard still leaks EN 'How it works' — locale catalogue regression."


# ---------------------------------------------------------------------------
# 3 — FR contact: 'Pages utiles' renders
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_contact_translates_useful_pages():
    response = Client().get("/fr/contact/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # "Pages utiles" lives in the <nav>'s aria-label, plus the nav links
    # are translated visible text. We check both (raw body for the aria
    # attribute, visible text for the link labels).
    assert 'aria-label="Pages utiles"' in body, "FR aria-label 'Pages utiles' missing"
    visible = _visible_text(body)
    assert (
        "Retour à l’assistant" in visible or "Retour à l'assistant" in visible
    ), "FR 'Back to the wizard' link missing"
    assert "Lire la méthodologie" in visible, "FR 'Read the methodology' link missing"
    assert (
        "Useful pages" not in visible
    ), "FR contact still leaks EN 'Useful pages' in visible body."


# ---------------------------------------------------------------------------
# 4 — AR contact: 'صفحات مفيدة' renders + multi-line blocktranslates
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ar_contact_translates_useful_pages_and_aside():
    response = Client().get("/ar/contact/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # The "Useful pages" wording is the <nav>'s aria-label; the visible
    # link labels carry the actual AR translations.
    assert 'aria-label="صفحات مفيدة"' in body, "AR aria-label 'صفحات مفيدة' missing"
    visible = _visible_text(body)
    # The four "What happens next" multi-line blocktranslates that were
    # EMPTY in pass-3 and forcibly filled in pass-4. We assert the FIRST
    # word/phrase of each AR translation appears.
    assert "ما الذي يحدث بعد ذلك" in visible, "AR aside header missing"
    assert "يقرأ محامٍ من المكتب" in visible, "AR step 1 missing"
    assert "ستتلقى رداً مكتوباً" in visible, "AR step 2 missing"
    assert "إذا كان ملفك ضمن نطاق عملنا" in visible, "AR step 3 missing"
    # And no leakage of the EN multi-line wording.
    assert "What happens next" not in visible
    assert "A lawyer of the Studio reads your message manually" not in visible


# ---------------------------------------------------------------------------
# 5 — FR result calculated translates 'What this means' / 'Next steps'
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_result_calculated_translates_new_sections(italy_calculator_fixture):
    """POST IT 35/10/0 to /fr/wizard/it/road-accident/ — the engine is the
    Italian one (only approved formula), but the result page is rendered
    under the FR locale. We assert the new pass-3 section headers are
    translated to FR."""

    client = Client()
    response = client.post(
        "/fr/wizard/it/road-accident/",
        data={
            "accident_country": italy_calculator_fixture["italy"].pk,
            "victim_age": 35,
            "permanent_disability_percentage": 10,
            "fault_percentage": 0,
            "consent_simulation": "on",
            "special_categories_consent": "on",
        },
        follow=True,
    )
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    visible = _visible_text(body)
    assert "Ce que cela signifie" in visible, "FR 'What this means' missing"
    assert "Étapes suivantes" in visible, "FR 'Next steps' missing"
    assert "What this means" not in visible, "EN 'What this means' leaked on FR result"
    assert "Next steps" not in visible, "EN 'Next steps' leaked on FR result"


# ---------------------------------------------------------------------------
# 6 — AR result unavailable translates the contact CTA
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ar_result_unavailable_translates_contact_cta(italy_calculator_fixture):
    """The Italy fixture is enough to bootstrap the simulation pipeline.
    POST a France case → unavailable result. We render under /ar/ and
    expect the AR translation of 'Request a Studio review of this case'."""

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
        slug="fr-pass4-fixture",
        title="FR fixture",
        country=france,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
    )
    client = Client()
    response = client.post(
        "/ar/wizard/fr/road-accident/",
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
    body = response.content.decode("utf-8")
    visible = _visible_text(body)
    # Pass-7 wires the CTA through ``public_status.primary_cta_label``.
    # For FR (LEGAL_ASSESSMENT) the AR translation is "أرسل الملف
    # إلى المكتب". The legacy AR phrasing is also accepted.
    assert ("أرسل الملف إلى المكتب" in visible) or (
        "اطلب من المكتب مراجعة هذا الملف" in visible
    ), "AR contact CTA missing"
    assert (
        "Request a Studio review of this case" not in visible
    ), "EN CTA leaked on AR unavailable result"
    assert "Submit the case to the Studio" not in visible, "EN CTA leaked on AR unavailable result"
    # No leaked monetary amounts on the unavailable card.
    assert "26268" not in body
    assert "27353" not in body
    assert "28439" not in body


# ---------------------------------------------------------------------------
# 7 — exactly one <h1> per public funnel page
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url",
    [
        "/wizard/",
        "/fr/wizard/",
        "/ar/wizard/",
        "/wizard/it/road-accident/",
        "/fr/wizard/fr/road-accident/",
        "/ar/wizard/ma/inheritance/",
        "/contact/",
        "/fr/contact/",
        "/ar/contact/",
    ],
)
def test_funnel_page_has_exactly_one_h1(url):
    response = Client().get(url)
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    h1_count = len(re.findall(r"<h1[\s>]", body))
    assert h1_count == 1, f"{url} has {h1_count} H1 elements (expected exactly 1)"
    # Heading order: extract levels in document order; the first heading
    # must be H1, and no level should jump by more than +1 from the
    # previous level.
    levels = [int(m.group(1)) for m in re.finditer(r"<h([1-6])[\s>]", body)]
    assert levels and levels[0] == 1, f"{url}: first heading is not H1 ({levels[:5]})"
    for prev, cur in zip(levels, levels[1:], strict=False):
        assert cur <= prev + 1, f"{url}: heading order skips a level (... H{prev} → H{cur})"


# ---------------------------------------------------------------------------
# 8 — global :focus-visible ring is in the base layout
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_funnels_expose_focus_visible_ring():
    """Keyboard users must always see focus on links/buttons. The shared
    base.html ships a :focus-visible outline that applies to all CTAs."""

    response = Client().get(reverse("cases:wizard_start"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # The base layout defines the global ring inline.
    assert "a:focus-visible" in body
    assert "button:focus-visible" in body
    assert "outline: 2px solid" in body


# ---------------------------------------------------------------------------
# 9 — no Pexels attribution on FR / AR funnels
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_ar_funnels_have_no_pexels_attribution():
    client = Client()
    for path in (
        "/fr/wizard/",
        "/fr/wizard/it/road-accident/",
        "/fr/contact/",
        "/ar/wizard/",
        "/ar/wizard/it/road-accident/",
        "/ar/contact/",
    ):
        body = client.get(path).content.decode("utf-8").lower()
        assert "photo by" not in body, f"{path}: 'Photo by' caption surfaced"
        assert "pexels.com" not in body, f"{path}: pexels.com link surfaced"


# ---------------------------------------------------------------------------
# 10 — no API key leak on FR / AR funnels
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_fr_ar_funnels_do_not_leak_api_key():
    client = Client()
    needle_env_names = ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY")
    long_token = re.compile(r"[A-Za-z0-9]{40,}")
    for path in ("/fr/wizard/", "/ar/wizard/", "/fr/contact/", "/ar/contact/"):
        body = client.get(path).content.decode("utf-8")
        for name in needle_env_names:
            assert name not in body, f"{path} leaks env var name {name!r}"
        for match in long_token.findall(body):
            for prefix in ("key=", "token=", "secret="):
                assert (
                    prefix + match not in body
                ), f"{path} appears to leak a token after {prefix!r}: {match[:8]}…"


# ---------------------------------------------------------------------------
# 11 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_pass4_polish(italy_calculator_fixture):
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
