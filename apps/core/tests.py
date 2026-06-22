"""
Tests F7 — apps.core (UI base).

Verificano:
- pagine pubbliche raggiungibili (200);
- header contiene link al sito madre;
- language switcher presente nel layout;
- lingua araba imposta `dir="rtl"` sul tag <html>;
- nessuna view pubblica crea `Simulation`;
- nessuna view pubblica esegue calcoli (no `compute()` chiamato).
"""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import translation

from apps.cases.models import Simulation

PUBLIC_URLS = [
    "core:home",
    "core:methodology",
    "core:disclaimer",
    "core:privacy",
    "core:countries",
    "core:case_types",
]


@pytest.fixture(autouse=True)
def _reset_active_language():
    """
    `LocaleMiddleware.activate()` modifica thread-local non resettato tra
    test: senza questa fixture un test che richiede `/ar/` lascia attivo
    l'arabo per il test successivo.
    """
    translation.activate("it")
    yield
    translation.deactivate()


@pytest.mark.django_db
@pytest.mark.parametrize("url_name", PUBLIC_URLS)
def test_public_page_returns_200(url_name):
    response = Client().get(reverse(url_name))
    assert response.status_code == 200


@pytest.mark.django_db
def test_header_links_to_parent_institutional_site():
    """Il sito madre deve essere linkato (REQ-6)."""
    response = Client().get(reverse("core:home"))
    body = response.content.decode("utf-8")
    assert "international.studiolegalebadrane.it" in body


@pytest.mark.django_db
def test_language_switcher_is_present():
    response = Client().get(reverse("core:home"))
    body = response.content.decode("utf-8")
    assert 'name="language"' in body
    assert 'action="/i18n/setlang/"' in body
    # Tutti e 4 i locali ufficiali appaiono nello switcher.
    for code in ("it", "fr", "en", "ar"):
        assert f'value="{code}"' in body


@pytest.mark.django_db
def test_arabic_locale_sets_rtl_direction():
    """Switching su /ar/ deve produrre <html dir="rtl">."""
    response = Client().get("/ar/", follow=False)
    # i18n_patterns non monta /ar/ come index esplicito ma su URL home '/'.
    # Usiamo il prefisso /ar/ tramite reverse forzato.
    response = Client().get("/ar/", follow=True)
    if response.status_code == 404:
        # Fallback: chiama set_language e verifica la home in arabo.
        client = Client()
        client.post("/i18n/setlang/", {"language": "ar", "next": "/"})
        response = client.get("/")
    body = response.content.decode("utf-8")
    assert 'dir="rtl"' in body
    assert 'lang="ar"' in body


@pytest.mark.django_db
def test_default_locale_sets_ltr_direction():
    response = Client().get(reverse("core:home"))
    body = response.content.decode("utf-8")
    assert 'dir="ltr"' in body


@pytest.mark.django_db
def test_disclaimer_banner_is_present_on_public_pages():
    response = Client().get(reverse("core:home"))
    body = response.content.decode("utf-8").lower()
    # Accept English source OR Italian translation (default LANGUAGE_CODE=it).
    assert "indicative simulations" in body or "simulazioni indicative" in body


@pytest.mark.django_db
def test_public_views_do_not_create_simulations():
    """REQ-3: nessuna pagina pubblica deve produrre Simulation."""
    initial = Simulation.objects.count()
    client = Client()
    for url_name in PUBLIC_URLS:
        client.get(reverse(url_name))
    assert Simulation.objects.count() == initial


@pytest.mark.django_db
def test_countries_page_lists_mvp_countries():
    response = Client().get(reverse("core:countries"))
    body = response.content.decode("utf-8")
    for code in ("IT", "FR", "BE", "MA", "TN"):
        assert code in body


@pytest.mark.django_db
def test_case_types_page_lists_taxonomy():
    response = Client().get(reverse("core:case_types"))
    body = response.content.decode("utf-8")
    # Almeno questi codici della tassonomia REQ-4 devono apparire.
    for code in (
        "road_accident_bodily_injury",
        "medical_malpractice",
        "inheritance_basic",
    ):
        assert code in body


@pytest.mark.django_db
def test_case_types_page_marks_italy_modules_as_available():
    """Italia case types must surface as available. Pass-5 renamed the
    badge from "Module ready" to "Indicative calculation available".
    Either still satisfies the contract."""

    response = Client().get("/en/case-types/")
    body = response.content.decode("utf-8")
    assert (
        ("Indicative calculation available" in body)
        or ("Module ready" in body)
        or ("module ready" in body.lower())
    )


@pytest.mark.django_db
def test_skip_to_content_link_present_for_accessibility():
    response = Client().get("/en/")
    body = response.content.decode("utf-8")
    assert "Skip to content" in body or 'href="#main"' in body


# ---------------------------------------------------------------------------
# F-post-approval-stabilization — staff dashboard, status labels, wizard fix
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_status_label_helper_returns_localized_strings():
    from apps.calculators.enums import CalculationStatus
    from apps.calculators.status_labels import get_public_status_label

    assert (
        get_public_status_label(CalculationStatus.CALCULATED.value, language="it")
        == "Stima disponibile"
    )
    assert (
        get_public_status_label(
            CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value, language="it"
        )
        == "Validazione legale richiesta"
    )
    assert (
        get_public_status_label(CalculationStatus.INSUFFICIENT_INPUT.value, language="fr")
        == "Données insuffisantes"
    )
    assert (
        get_public_status_label(CalculationStatus.ERROR.value, language="en") == "Technical error"
    )
    # unknown lang → fallback to default (it)
    assert (
        get_public_status_label(CalculationStatus.CALCULATED.value, language="xx")
        == "Stima disponibile"
    )


@pytest.mark.django_db
def test_status_label_helper_falls_back_for_unknown_status():
    from apps.calculators.status_labels import get_public_status_label

    # Unknown status code → returns the code itself (the helper never crashes)
    assert get_public_status_label("never_seen_status") == "never_seen_status"
    assert get_public_status_label(None) == ""


@pytest.mark.django_db
def test_wizard_template_does_not_leak_django_comment():
    """
    The wizard template once contained a multi-line `{# ... #}` comment
    that Django renders as visible text. After the fix it must use
    `{% comment %}` and the body must NOT contain the leaked tokens.
    """
    response = Client().get(reverse("cases:wizard_italy_road_accident"))
    body = response.content.decode("utf-8")
    assert "Tailwind defaults aren't applied" not in body
    assert "JS-free fallback" not in body
    assert "{#" not in body
    assert "#}" not in body


# ---------------------------------------------------------------------------
# Staff project-status dashboard
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_project_status_requires_authentication():
    """Anonymous → redirect to admin login."""
    response = Client().get(reverse("core:project_status"))
    # staff_member_required redirects to admin login (302)
    assert response.status_code == 302
    assert "/admin/login" in response["Location"]


@pytest.mark.django_db
def test_project_status_rejects_non_staff_user():
    from apps.accounts.models import User

    User.objects.create_user(
        username="not_staff_user", password="x", is_staff=False, is_active=True
    )
    client = Client()
    client.login(username="not_staff_user", password="x")
    response = client.get(reverse("core:project_status"))
    assert response.status_code == 302
    assert "/admin/login" in response["Location"]


@pytest.mark.django_db
def test_project_status_returns_200_for_staff():
    from apps.accounts.models import User

    User.objects.create_user(username="staff_user", password="x", is_staff=True, is_active=True)
    client = Client()
    client.login(username="staff_user", password="x")
    response = client.get(reverse("core:project_status"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Static labels that should always be present
    assert "Project status" in body
    assert "LegalSource" in body
    assert "CompensationDataset" in body
    assert "CalculationFormula" in body
    assert "Active calculators" in body
    assert "No-go for production" in body
    # F-staff-dashboard-moral-range-display: new always-present sections.
    assert "Approved datasets" in body
    assert "Active calculation rule" in body
    assert "Reference smoke" in body
    # Module pair always-active for IT (placeholder + real engine)
    assert "IT-NATIONAL" in body
    assert "road_accident_bodily_injury" in body


# ---------------------------------------------------------------------------
# F-staff-dashboard-moral-range-display — content with fixture data.
# REGOLA D'ORO: nessun valore TUN reale qui. I Decimal sono segnaposto
# (1, 100, 200, 300 EUR) per esercitare la dashboard, non per riprodurre
# la fonte legale.
# ---------------------------------------------------------------------------


def _seed_full_stack_with_moral_range(*, range_active: bool):
    """Crea base + moral datasets + formula con o senza range attivo.

    Usato per testare la dashboard staff in due scenari:
    - range_active=True: amount_rule == "row_amount_range_direct" e
      moral dataset APPROVED — la dashboard deve mostrare il range.
    - range_active=False: amount_rule == "row_amount_direct" e moral
      dataset DRAFT — la dashboard deve mostrare il single-value path.
    """
    from datetime import date as _date
    from decimal import Decimal as _Dec

    from apps.calculators.enums import CaseType
    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        CompensationTableRow,
        DatasetStatus,
    )
    from apps.compensation.test_fixtures import approved_source_version
    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    italy = Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")
    juris = Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    italian = Language.objects.create(code="it", name="Italiano")
    src = LegalSource.objects.create(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title="D.P.R. 12/2025 (test stub)",
        country=italy,
        jurisdiction=juris,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=_date(2025, 2, 11),
        effective_date=_date(2025, 1, 13),
    )
    base = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base (test)",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=_date(2025, 1, 13),
    )
    CompensationTableRow.objects.create(
        dataset=base,
        row_type="tun_biological_total_amount",
        age_min=0,
        age_max=0,
        disability_min=10,
        disability_max=10,
        point_value=_Dec("1"),
    )
    moral = CompensationDataset.objects.create(
        source=src,
        source_version=approved_source_version(src),
        jurisdiction=juris,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral (test)",
        version_label="DPR-12-2025-MORAL",
        status=DatasetStatus.APPROVED if range_active else DatasetStatus.DRAFT,
        valid_from=_date(2025, 1, 13),
    )
    for kind, point_value in (("min", "100"), ("mid", "200"), ("max", "300")):
        CompensationTableRow.objects.create(
            dataset=moral,
            row_type=f"tun_biological_moral_{kind}_total_amount",
            age_min=0,
            age_max=0,
            disability_min=10,
            disability_max=10,
            point_value=_Dec(point_value),
        )
    if range_active:
        params = {
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_range_direct",
            "fault_reduction": True,
            "range_dataset_version_label": "DPR-12-2025-MORAL",
            "min_row_type": "tun_biological_moral_min_total_amount",
            "mid_row_type": "tun_biological_moral_mid_total_amount",
            "max_row_type": "tun_biological_moral_max_total_amount",
        }
    else:
        params = {
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_direct",
            "fault_reduction": True,
        }
    CalculationFormula.objects.create(
        dataset=base,
        code="italy_art_138_tun_2025_base",
        name="Stub formula",
        expression_text="placeholder",
        source_reference="placeholder",
        parameters=params,
        status=DatasetStatus.APPROVED,
    )
    return src, base, moral


def _login_staff(client):
    from apps.accounts.models import User

    User.objects.create_user(username="staff2", password="x", is_staff=True, is_active=True)
    client.login(username="staff2", password="x")


@pytest.mark.django_db
def test_project_status_shows_moral_range_when_active():
    _seed_full_stack_with_moral_range(range_active=True)
    client = Client()
    _login_staff(client)
    response = client.get(reverse("core:project_status"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")

    # Both dataset version_labels visible.
    assert "DPR-12-2025" in body
    assert "DPR-12-2025-MORAL" in body
    # Active rule must be the range one.
    assert "row_amount_range_direct" in body
    # All three moral row_types must be listed.
    assert "tun_biological_moral_min_total_amount" in body
    assert "tun_biological_moral_mid_total_amount" in body
    assert "tun_biological_moral_max_total_amount" in body
    # The "min/mid/max range active" hint must be visible.
    assert "min/mid/max range active" in body
    # Reference smoke values surfaced (display-only, no real TUN computation).
    assert "26268" in body
    assert "27353" in body
    assert "28439" in body


@pytest.mark.django_db
def test_project_status_shows_single_value_when_range_inactive():
    _seed_full_stack_with_moral_range(range_active=False)
    client = Client()
    _login_staff(client)
    response = client.get(reverse("core:project_status"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")

    # Single-value rule visible.
    assert "row_amount_direct" in body
    # Range hint NOT shown; the gentle warning IS shown.
    assert "min/mid/max range active" not in body
    assert "Reference range applicable only when row_amount_range_direct is active" in body
    # Moral dataset still listed (it exists, just DRAFT).
    assert "DPR-12-2025-MORAL" in body
    # Status badge "draft" visible somewhere on its card.
    assert "draft" in body


@pytest.mark.django_db
def test_project_status_marks_france_as_scaffold():
    """FR-NATIONAL × road_accident_bodily_injury must show as `scaffold`."""
    from apps.accounts.models import User

    User.objects.create_user(username="staff3", password="x", is_staff=True, is_active=True)
    client = Client()
    client.login(username="staff3", password="x")
    response = client.get(reverse("core:project_status"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # The FR pair must be listed.
    assert "FR-NATIONAL" in body
    assert "road_accident_bodily_injury" in body
    # And badged as scaffold (not as a regular active calculator).
    assert "scaffold" in body


@pytest.mark.django_db
def test_countries_page_shows_france_as_legal_sources_under_review():
    """Public /countries/ marks FR with the scaffold-only badge.

    Pass-5 renamed the badge from "Legal sources under review" to
    "Preliminary legal assessment". Either still satisfies the
    contract that France is not marked as available.
    """
    response = Client().get("/en/countries/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert ("Preliminary legal assessment" in body) or ("Legal sources under review" in body)


@pytest.mark.django_db
def test_wizard_start_page_offers_france_scaffold_link():
    """Public /wizard/ shows the FR option as scaffold."""
    response = Client().get("/en/wizard/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "/en/wizard/fr/road-accident/" in body
    assert (
        ("Submit the case to the Studio" in body)
        or ("Preliminary legal assessment" in body)
        or ("Open scaffold wizard" in body)
        or ("Legal sources under review" in body)
    )


# ---------------------------------------------------------------------------
# F-belgium-road-accident-bootstrap — UI assertions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_project_status_marks_belgium_as_scaffold():
    from apps.accounts.models import User

    User.objects.create_user(username="staff_be", password="x", is_staff=True, is_active=True)
    client = Client()
    client.login(username="staff_be", password="x")
    response = client.get(reverse("core:project_status"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "BE-NATIONAL" in body
    assert "road_accident_bodily_injury" in body
    assert "scaffold" in body


@pytest.mark.django_db
def test_countries_page_shows_belgium_as_legal_sources_under_review():
    response = Client().get("/en/countries/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # Both FR and BE are scaffold-only. Pass-5 renamed the badge.
    badge_hits = body.count("Preliminary legal assessment") + body.count(
        "Legal sources under review"
    )
    assert badge_hits >= 2


@pytest.mark.django_db
def test_wizard_start_page_offers_belgium_scaffold_link():
    response = Client().get(reverse("cases:wizard_start"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "/wizard/be/road-accident/" in body


# ---------------------------------------------------------------------------
# F-ma-tn-international-inheritance-bootstrap — UI assertions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_project_status_marks_morocco_and_tunisia_as_scaffold():
    from apps.accounts.models import User

    User.objects.create_user(username="staff_ma_tn", password="x", is_staff=True, is_active=True)
    client = Client()
    client.login(username="staff_ma_tn", password="x")
    response = client.get(reverse("core:project_status"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "MA-NATIONAL" in body
    assert "TN-NATIONAL" in body
    assert "international_inheritance" in body
    # Both pairs must be flagged as scaffold.
    assert body.count("scaffold") >= 4


@pytest.mark.django_db
def test_countries_page_shows_morocco_and_tunisia_as_legal_sources_under_review():
    response = Client().get("/en/countries/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    # FR, BE, MA, TN all scaffold-only → 4 occurrences of a non-available badge.
    # Pass-5 renamed the badge to "Preliminary legal assessment"; pass-6
    # split MA/TN out into "International inheritance review" while
    # keeping FR/BE on "Preliminary legal assessment". Either way, the
    # 4 scaffolded countries must surface a non-available badge.
    badge_hits = (
        body.count("Preliminary legal assessment")
        + body.count("International inheritance review")
        + body.count("Legal sources under review")
    )
    assert badge_hits >= 4


@pytest.mark.django_db
def test_wizard_start_page_offers_morocco_and_tunisia_inheritance_links():
    response = Client().get(reverse("cases:wizard_start"))
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "/wizard/ma/inheritance/" in body
    assert "/wizard/tn/inheritance/" in body


@pytest.mark.django_db
def test_case_types_page_marks_international_inheritance_as_scaffold():
    """international_inheritance has only scaffold registrations (MA, TN).

    Pass-6 split the inheritance scaffold into its own status so the
    page now reads "International inheritance review" for the
    international_inheritance row. We accept either wording for
    forward / backward compatibility.
    """

    response = Client().get("/en/case-types/")
    assert response.status_code == 200
    body = response.content.decode("utf-8")
    assert "international_inheritance" in body
    assert (
        ("International inheritance review" in body)
        or ("Preliminary legal assessment" in body)
        or ("Legal sources under review" in body)
    )
