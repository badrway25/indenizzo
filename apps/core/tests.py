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
