"""
Tests F-p0-leg-3-consent.

Coprono il doppio consenso GDPR art. 6 + art. 9 sui form pubblici:

1. contact form senza consensi -> errore;
2. contact form con solo art. 6 -> errore (manca art. 9);
3. contact form con entrambi -> Lead salvato + ConsentRecord doppi;
4. wizard Italia senza consensi -> errore;
5. wizard Italia con consensi -> Simulation salvata;
6. wizard Marocco (paese placeholder) con consensi -> Simulation
   `unavailable_requires_legal_validation` MA con campi consenso
   salvati;
7. checkbox NON pre-selezionate nel HTML rendered;
8. versioni consenso salvate sui record (Lead + Simulation);
9. system check `core.E004` fail in prod con versioni `working-copy`;
10. system check passa in prod con versioni firmate (no markers).
"""

from __future__ import annotations

import re

import pytest
from django.core.checks import Error
from django.test import Client, override_settings
from django.utils import translation

from apps.core.checks import check_consent_versions_signed_in_production


@pytest.fixture(autouse=True)
def _reset_active_language():
    yield
    translation.deactivate_all()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _post_contact(client: Client, **overrides) -> Any:
    """Body minimo del contact form. Override per scenario."""
    base = {
        "first_name": "Mario",
        "last_name": "Rossi",
        "email": "mario@example.com",
        "phone_number": "",
        "preferred_language": "it",
        "country": "",
        "case_type": "",
        "message": "Vorrei una valutazione legale per un caso urgente di danno biologico.",
        "privacy_accepted": "",
        "special_categories_accepted": "",
        "simulation_public_id": "",
        "website": "",
    }
    base.update(overrides)
    return client.post("/contact/", data=base)


def _post_wizard_italy(client: Client, **overrides) -> Any:
    base = {
        "victim_age": "35",
        "permanent_disability_percentage": "10",
        "fault_percentage": "0",
        "consent_simulation": "",
        "special_categories_consent": "",
        "website": "",
    }
    base.update(overrides)
    return client.post("/wizard/it/road-accident/", data=base)


def _post_wizard_morocco(client: Client, **overrides) -> Any:
    base = {
        "deceased_country_of_last_residence": "MA",
        "nationality": "MA",
        "consent_simulation": "",
        "special_categories_consent": "",
        "website": "",
    }
    base.update(overrides)
    return client.post("/wizard/ma/inheritance/", data=base)


# ---------------------------------------------------------------------------
# Avoid Any import
# ---------------------------------------------------------------------------

from typing import Any  # noqa: E402


# ---------------------------------------------------------------------------
# Test 1: contact form senza consenso -> errore
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_form_without_consents_fails():
    """Submit senza nessun consenso → form re-renderizzato, NO Lead in DB."""
    from apps.crm.models import Lead

    resp = _post_contact(Client())
    assert resp.status_code == 200, "rejection must re-render form, not redirect"
    assert Lead.objects.count() == 0
    # Verifica che il form abbia errori sui due campi consenso (non
    # ci affidiamo a stringhe localizzate del messaggio: la presenza
    # del nome del campo nei `<p role="alert">` o nel form.errors
    # rendering del partial e' garanzia sufficiente).
    html = resp.content.decode("utf-8")
    assert 'role="alert"' in html, "atteso almeno un error alert nel form re-renderizzato"


# ---------------------------------------------------------------------------
# Test 2: contact form con solo art. 6 -> errore
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_form_with_only_art6_fails():
    """Solo art. 6 spuntato → form rifiuta perche' manca art. 9."""
    from apps.crm.models import Lead

    resp = _post_contact(Client(), privacy_accepted="on")
    assert resp.status_code == 200
    assert Lead.objects.count() == 0
    # Il form deve avere errore sul campo `special_categories_accepted`
    # (verificato a livello di binding form direttamente).
    from apps.crm.forms import ContactForm

    f = ContactForm(
        data={
            "first_name": "x",
            "last_name": "y",
            "email": "a@b.c",
            "phone_number": "",
            "preferred_language": "it",
            "country": "",
            "case_type": "",
            "message": "abcdefghijklmnopqrstuvwxyz",
            "privacy_accepted": "on",
            "special_categories_accepted": "",
            "simulation_public_id": "",
            "website": "",
        }
    )
    assert not f.is_valid()
    assert "special_categories_accepted" in f.errors
    assert "privacy_accepted" not in f.errors


# ---------------------------------------------------------------------------
# Test 3: contact form con entrambi -> Lead salvato
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_contact_form_with_both_consents_creates_lead_and_records():
    from apps.crm.models import Lead
    from apps.compliance.models import ConsentRecord

    resp = _post_contact(
        Client(),
        privacy_accepted="on",
        special_categories_accepted="on",
    )
    assert resp.status_code == 302, f"expected redirect, got {resp.status_code}"
    assert Lead.objects.count() == 1
    lead = Lead.objects.first()
    # Campi denormalizzati popolati
    assert lead.privacy_consent_given is True
    assert lead.privacy_consent_at is not None
    assert lead.privacy_consent_version != ""
    assert lead.special_categories_consent_given is True
    assert lead.special_categories_consent_at is not None
    assert lead.special_categories_consent_version != ""
    # Doppio ConsentRecord creato (lead_contact + special_categories_processing)
    purposes = set(
        ConsentRecord.objects.values_list("purpose__code", flat=True)
    )
    assert "lead_contact" in purposes
    assert "special_categories_processing" in purposes


# ---------------------------------------------------------------------------
# Test 4: wizard Italia senza consensi -> errore
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_italy_without_consents_fails():
    from apps.cases.models import Simulation
    from apps.cases.forms import ItalyRoadAccidentWizardForm

    resp = _post_wizard_italy(Client())
    assert resp.status_code == 200
    assert Simulation.objects.count() == 0
    f = ItalyRoadAccidentWizardForm(
        data={
            "victim_age": "35",
            "permanent_disability_percentage": "10",
            "fault_percentage": "0",
            "consent_simulation": "",
            "special_categories_consent": "",
            "website": "",
        }
    )
    assert not f.is_valid()
    assert "consent_simulation" in f.errors
    assert "special_categories_consent" in f.errors


# ---------------------------------------------------------------------------
# Test 5: wizard Italia con consensi -> Simulation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_italy_with_both_consents_creates_simulation():
    from apps.cases.models import Simulation

    resp = _post_wizard_italy(
        Client(),
        consent_simulation="on",
        special_categories_consent="on",
    )
    assert resp.status_code == 302
    assert Simulation.objects.count() == 1
    sim = Simulation.objects.first()
    assert sim.privacy_consent_given is True
    assert sim.special_categories_consent_given is True


# ---------------------------------------------------------------------------
# Test 6: wizard Marocco con consensi -> Simulation unavailable ma campi salvati
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_wizard_morocco_with_both_consents_creates_unavailable_sim_with_consent():
    from apps.cases.models import Simulation

    resp = _post_wizard_morocco(
        Client(),
        consent_simulation="on",
        special_categories_consent="on",
    )
    assert resp.status_code == 302
    assert Simulation.objects.count() == 1
    sim = Simulation.objects.first()
    assert sim.status == "unavailable_requires_legal_validation"
    # Anche se l'engine MA e' placeholder, il consenso DEVE essere salvato.
    assert sim.privacy_consent_given is True
    assert sim.special_categories_consent_given is True


# ---------------------------------------------------------------------------
# Test 7: checkbox NON pre-selezionate nell'HTML
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_consent_checkboxes_are_not_preselected_on_contact_form():
    resp = Client().get("/contact/")
    html = resp.content.decode("utf-8")
    # Nessun input type=checkbox con `checked` per privacy_accepted /
    # special_categories_accepted.
    pattern = re.compile(
        r'<input[^>]+name="(privacy_accepted|special_categories_accepted)"[^>]*\bchecked\b',
        flags=re.IGNORECASE,
    )
    assert pattern.search(html) is None, (
        "Contact form: checkbox di consenso pre-selezionate (dark pattern) — "
        "violazione GDPR/deontologia"
    )


@pytest.mark.django_db
def test_consent_checkboxes_are_not_preselected_on_wizard_italy():
    resp = Client().get("/wizard/it/road-accident/")
    html = resp.content.decode("utf-8")
    pattern = re.compile(
        r'<input[^>]+name="(consent_simulation|special_categories_consent)"[^>]*\bchecked\b',
        flags=re.IGNORECASE,
    )
    assert pattern.search(html) is None


# ---------------------------------------------------------------------------
# Test 8: versioni consenso salvate sui record
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    PRIVACY_NOTICE_VERSION="test-priv-v1",
    SPECIAL_CATEGORIES_NOTICE_VERSION="test-sc-v1",
)
def test_consent_versions_persisted_on_lead_and_simulation():
    from apps.crm.models import Lead
    from apps.cases.models import Simulation

    client = Client()
    _post_contact(client, privacy_accepted="on", special_categories_accepted="on")
    _post_wizard_italy(
        client,
        consent_simulation="on",
        special_categories_consent="on",
    )
    lead = Lead.objects.latest("created_at")
    sim = Simulation.objects.latest("created_at")
    assert lead.privacy_consent_version == "test-priv-v1"
    assert lead.special_categories_consent_version == "test-sc-v1"
    assert sim.privacy_consent_version == "test-priv-v1"
    assert sim.special_categories_consent_version == "test-sc-v1"


# ---------------------------------------------------------------------------
# Test 9: system check core.E004 fail in prod con versioni working-copy
# ---------------------------------------------------------------------------


@override_settings(
    DEBUG=False,
    PRIVACY_NOTICE_VERSION="working-copy-2026-05-10",
    SPECIAL_CATEGORIES_NOTICE_VERSION="working-copy-2026-05-10",
)
def test_check_e004_fails_in_prod_with_working_copy_versions():
    issues = check_consent_versions_signed_in_production(app_configs=None)
    assert len(issues) == 2
    for issue in issues:
        assert isinstance(issue, Error)
        assert issue.id == "core.E004"


@override_settings(
    DEBUG=False,
    PRIVACY_NOTICE_VERSION="",
    SPECIAL_CATEGORIES_NOTICE_VERSION="",
)
def test_check_e004_fails_in_prod_with_empty_versions():
    issues = check_consent_versions_signed_in_production(app_configs=None)
    assert len(issues) == 2
    for issue in issues:
        assert isinstance(issue, Error)
        assert issue.id == "core.E004"


@override_settings(
    DEBUG=False,
    PRIVACY_NOTICE_VERSION="draft-2026-08",
    SPECIAL_CATEGORIES_NOTICE_VERSION="2026-09-15-final",
)
def test_check_e004_flags_only_draft_marker():
    issues = check_consent_versions_signed_in_production(app_configs=None)
    assert len(issues) == 1
    assert "PRIVACY_NOTICE_VERSION" in issues[0].msg


# ---------------------------------------------------------------------------
# Test 10: system check passa in prod con versioni firmate
# ---------------------------------------------------------------------------


@override_settings(
    DEBUG=False,
    PRIVACY_NOTICE_VERSION="2026-09-15-final",
    SPECIAL_CATEGORIES_NOTICE_VERSION="2026-09-15-final",
)
def test_check_e004_silent_in_prod_with_signed_versions():
    issues = check_consent_versions_signed_in_production(app_configs=None)
    assert issues == []


@override_settings(
    DEBUG=True,
    PRIVACY_NOTICE_VERSION="working-copy-anything",
    SPECIAL_CATEGORIES_NOTICE_VERSION="working-copy-anything",
)
def test_check_e004_silent_in_dev():
    """In dev (DEBUG=True), il check non scatta anche con working-copy."""
    issues = check_consent_versions_signed_in_production(app_configs=None)
    assert issues == []
