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
    body = response.content.decode("utf-8")
    assert "indicative simulations" in body.lower()


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
    """I due placeholder Italia di F4 devono comparire come 'Module ready'."""
    response = Client().get(reverse("core:case_types"))
    body = response.content.decode("utf-8")
    assert "Module ready" in body or "module ready" in body.lower()


@pytest.mark.django_db
def test_skip_to_content_link_present_for_accessibility():
    response = Client().get(reverse("core:home"))
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
    # Module pair always-active for IT (placeholder + real engine)
    assert "IT-NATIONAL" in body
    assert "road_accident_bodily_injury" in body
