"""Tests F-product-public-funnels-polish-pass3.

Cover the new copy / structure introduced by pass-3 polish:

1. wizard start has both the calculator-available CTA and the new
   "Open validation wizard" CTA, plus the new "How it works" 3-step
   section.
2. Italy wizard contains TUN 2025 wording AND the new
   "After you submit" preview block.
3. Each scaffold wizard (FR/BE/MA/TN) includes the explicit
   "no automatic estimate" / "no automatic shares" wording.
4. Calculated result page has min/mid/max values + PDF download CTA
   + the new "What this means" / "Next steps" sections.
5. Unavailable result page has a contact CTA and never shows numeric
   amounts.
6. Contact page advertises next steps + privacy reassurance + the
   new return-paths nav.
7. Compiled translation catalogues exist for it/fr/ar (smoke).
8. Public funnel pages do not surface a Pexels attribution caption.
9. Public funnel pages don't leak a Pexels API key.
10. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.
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


@pytest.fixture
def italy_calculator_fixture(db):
    """Seed Italy 35/10/0 → 26 268 / 27 353 / 28 439 EUR."""
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
        slug="it-fixture-pass3-funnels",
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
        name="TUN base",
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
        name="TUN moral",
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
        code="italy_art_138_tun_2025_pass3",
        name="pass3-funnels",
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
# 1 — wizard start CTAs + How it works
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_start_has_italy_cta_validation_cta_and_how_it_works():
    """Project default is IT — assertions match the IT translations the
    page actually renders. Each phrase is checked in EN-or-IT to remain
    robust if the project's default locale changes."""
    response = Client().get(reverse("cases:wizard_start"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Pass-6 centralised the IT primary CTA in apps/core/public_status.py
    # — the rendered text is now "Run an indicative simulation" /
    # "Avvia una simulazione indicativa". Old wording is kept as a
    # fallback for forward compatibility.
    assert (
        ("Run an indicative simulation" in body)
        or ("Avvia una simulazione indicativa" in body)
        or ("Start this simulation" in body)
        or ("Avvia questa simulazione" in body)
    )
    # Pass-5 renamed "Open validation wizard" → "Submit the case to the Studio".
    # Either still satisfies the contract that scaffolds expose a CTA.
    assert (
        ("Submit the case to the Studio" in body)
        or ("Invia il caso allo Studio" in body)
        or ("Open validation wizard" in body)
        or ("Apri la procedura di validazione" in body)
    )
    assert ("How it works" in body) or ("Come funziona" in body)
    # Step 1/2/3 — IT renders "Passo 1/2/3".
    assert ("Step 1" in body) or ("Passo 1" in body)
    assert ("Step 2" in body) or ("Passo 2" in body)
    assert ("Step 3" in body) or ("Passo 3" in body)


# ---------------------------------------------------------------------------
# 2 — Italy wizard TUN 2025 + After you submit
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_italy_has_tun_2025_and_result_preview():
    response = Client().get(reverse("cases:wizard_italy_road_accident"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "TUN 2025" in body
    assert ("After you submit" in body) or ("Dopo l’invio" in body) or ("Dopo l'invio" in body)
    # The preview block enumerates min/mid/max as three columns. The
    # middle label is translated to "Centrale" in the project's default
    # IT locale, so accept either form.
    has_min = ">Min<" in body
    has_max = ">Max<" in body
    has_mid = (">Mid<" in body) or (">Centrale<" in body)
    assert (
        has_min and has_mid and has_max
    ), f"min/mid/max preview missing — has_min={has_min} has_mid={has_mid} has_max={has_max}"


# ---------------------------------------------------------------------------
# 3 — scaffold wizards have explicit "no automatic estimate/shares"
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "url_name",
    [
        "cases:wizard_france_road_accident",
        "cases:wizard_belgium_road_accident",
        "cases:wizard_morocco_inheritance",
        "cases:wizard_tunisia_inheritance",
    ],
)
def test_scaffold_wizards_say_no_automatic(url_name):
    """Pass-5 rephrased the "no automatic" disclaimer from
    "no automatic estimate" / "no automatic shares" to
    "no automatic amount" / "shares not computed automatically".
    The contract is that the page communicates it does not publish a
    number — we accept any of the canonical phrasings."""

    response = Client().get(reverse(url_name))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    candidates = (
        "no automatic estimate",
        "no automatic amount",
        "no automatic shares",
        "shares not computed automatically",
        # Pass-7 panel wording: long_description / no_amounts_message
        # surface "Inheritance shares are not computed automatically".
        "Inheritance shares are not computed automatically",
        "shares are not computed automatically",
        "nessuna stima automatica",
        "nessun importo automatico",
        "nessuna quota calcolata automaticamente",
        "quote non calcolate automaticamente",
        "non vengono calcolate automaticamente",
    )
    assert any(
        c in body for c in candidates
    ), f"{url_name}: no recognised 'no automatic' disclaimer in body"


# ---------------------------------------------------------------------------
# 4 — calculated result has min/mid/max + PDF CTA + new sections
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_calculated_result_has_amounts_pdf_cta_and_new_sections(italy_calculator_fixture):
    client = Client()
    response = client.post(
        reverse("cases:wizard_italy_road_accident"),
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
    # Amounts present.
    assert "26268" in body
    assert "27353" in body
    assert "28439" in body
    # New sections (EN-or-IT).
    assert ("What this means" in body) or ("Cosa significa" in body)
    assert ("Next steps" in body) or ("Prossimi passi" in body)
    assert ("What you can do with this result" in body) or (
        "Cosa puoi fare con questo risultato" in body
    )
    # PDF CTA — the URL fragment is locale-agnostic.
    assert "/pdf" in body


# ---------------------------------------------------------------------------
# 5 — unavailable result has contact CTA and no amounts
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_unavailable_result_has_contact_cta_and_no_amounts(italy_calculator_fixture):
    """France path: no APPROVED FR formula → unavailable. The result page
    must surface the new "Request a Studio review of this case" CTA inside
    the unavailable card and expose no monetary amount."""
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
        slug="fr-pass3-fixture",
        title="FR fixture",
        country=france,
        language=french,
        source_type=SourceType.OFFICIAL_LAW,
        reliability=Reliability.OFFICIAL,
        status=SourceStatus.NEEDS_REVIEW,
    )
    client = Client()
    response = client.post(
        reverse("cases:wizard_france_road_accident"),
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
    # Contact CTA inside the unavailable flow. Pass-7 routes the CTA
    # label through ``public_status.primary_cta_label`` — for FR
    # (LEGAL_ASSESSMENT) that is "Submit the case to the Studio" /
    # "Invia il caso allo Studio". The legacy "Request a Studio review
    # of this case" / "Richiedi allo Studio la revisione di questo
    # caso" wording is also accepted as a fallback.
    assert (
        ("Submit the case to the Studio" in body)
        or ("Invia il caso allo Studio" in body)
        or ("Request a Studio review of this case" in body)
        or ("Richiedi allo Studio la revisione di questo caso" in body)
    )
    # No leaked amounts. The page should not mention "EUR" anywhere near a
    # number; we approximate by checking absence of the IT contract digits.
    assert "26268" not in body
    assert "27353" not in body
    assert "28439" not in body


# ---------------------------------------------------------------------------
# 6 — contact page has return-paths nav
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_has_next_steps_privacy_and_return_paths():
    response = Client().get(reverse("crm:contact"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Existing aside (pre-pass3) — EN or IT (the existing IT translation
    # covers it; either way the aside renders).
    assert (
        ("What happens next" in body)
        or ("Cosa succede dopo" in body)
        or ("Cosa succederà" in body)
        or ("Cosa succede ora" in body)
    )
    # New return-paths nav (EN-or-IT).
    assert ("Useful pages" in body) or ("Pagine utili" in body)
    assert ("Back to the wizard" in body) or ("Torna alla procedura guidata" in body)
    assert ("Read the methodology" in body) or ("Leggi la metodologia" in body)
    assert ("Open the disclaimer" in body) or ("Apri il disclaimer" in body)


# ---------------------------------------------------------------------------
# 7 — compiled translations exist for it/fr/ar
# ---------------------------------------------------------------------------


def test_compiled_translations_exist_for_it_fr_ar():
    for code in ("it", "fr", "ar"):
        mo_path = LOCALE_DIR / code / "LC_MESSAGES" / "django.mo"
        assert mo_path.exists(), f"compiled .mo missing for {code}: {mo_path}"
        # Sanity: mo is non-trivially sized (>1 KB).
        assert mo_path.stat().st_size > 1024


# ---------------------------------------------------------------------------
# 8 — no Pexels attribution surfaces in the polished funnels
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_funnels_do_not_show_pexels_attribution():
    client = Client(HTTP_ACCEPT_LANGUAGE="en")
    for url_name in (
        "cases:wizard_start",
        "cases:wizard_italy_road_accident",
        "cases:wizard_france_road_accident",
        "crm:contact",
    ):
        response = client.get(reverse(url_name))
        body = response.content.decode("utf-8").lower()
        assert "photo by" not in body, f"{url_name} surfaces a Pexels-style 'Photo by' caption"
        assert "pexels.com" not in body, f"{url_name} surfaces pexels.com link"


# ---------------------------------------------------------------------------
# 9 — no API key leak on the public funnel pages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_funnels_do_not_leak_api_key():
    client = Client(HTTP_ACCEPT_LANGUAGE="en")
    # A leaked Pexels API key would be a 56-char hex-ish string; we approximate
    # the leak check by searching for the env var name and any 40+ char
    # uppercase-and-digits run on the page.
    needle_env_names = ("PEXELS_API_KEY", "STRIPE_SECRET", "SENDGRID_API_KEY")
    long_token = re.compile(r"[A-Za-z0-9]{40,}")
    for url_name in (
        "cases:wizard_start",
        "cases:wizard_italy_road_accident",
        "crm:contact",
    ):
        response = client.get(reverse(url_name))
        body = response.content.decode("utf-8")
        for name in needle_env_names:
            assert name not in body, f"{url_name} leaks env var name {name!r}"
        # A long opaque token in the rendered HTML is a smell. We allow up
        # to 60 chars in URL paths (e.g. CSS hashes) by checking the token
        # never appears immediately after "key=" or "token=".
        for match in long_token.findall(body):
            for prefix in ("key=", "token=", "secret="):
                assert (
                    prefix + match not in body
                ), f"{url_name} appears to leak a token after {prefix!r}: {match[:8]}…"


# ---------------------------------------------------------------------------
# 10 — Italia smoke unchanged
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_italy_smoke_unchanged_after_pass3_polish(italy_calculator_fixture):
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
