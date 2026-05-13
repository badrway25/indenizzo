"""
Tests F-p0-codice-3-footer-pass1.

Coprono:
- footer renderizza la sezione "Professional identification" in tutte
  le lingue (IT/FR/EN/AR);
- placeholder `[da configurare prima del go-live]` visibile quando una
  env var manca, NEL CONTAINER del campo specifico;
- quando le env var sono valorizzate, i valori appaiono al posto del
  placeholder;
- system check `core.W001` in dev (DEBUG=True): un solo Warning;
- system check `core.E001` in prod (DEBUG=False): un Error per ogni
  campo obbligatorio mancante;
- system check passa (zero issues) quando i campi obbligatori sono
  valorizzati in prod;
- nessuna regressione su hreflang globale (count==5 sulle pagine in
  allowlist) e su meta robots.
"""

from __future__ import annotations

import re

import pytest
from django.core.checks import Error, Warning
from django.test import Client, override_settings
from django.utils import translation

from apps.core.checks import check_studio_professional_identification

# ---------------------------------------------------------------------------
# Test isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_active_language():
    yield
    translation.deactivate_all()


PLACEHOLDER_TEXT = "[da configurare prima del go-live]"

REQUIRED_FIELDS = (
    "STUDIO_LEAD_LAWYER_NAME",
    "STUDIO_BAR_ASSOCIATION",
    "STUDIO_VAT_NUMBER",
    "STUDIO_PEC_EMAIL",
    "STUDIO_PHYSICAL_ADDRESS",
    "STUDIO_PROFESSIONAL_INSURANCE_INSURER",
    "STUDIO_PROFESSIONAL_INSURANCE_POLICY",
)

ALL_STUDIO_FIELDS = (
    *REQUIRED_FIELDS,
    "STUDIO_BAR_REGISTRATION_NUMBER",
    "STUDIO_TAX_CODE",
    "STUDIO_PROFESSIONAL_INSURANCE_CEILING",
)

ALL_STUDIO_FIELDS_FILLED = {
    "STUDIO_LEAD_LAWYER_NAME": "Avv. Test Foo",
    "STUDIO_BAR_ASSOCIATION": "Ordine degli Avvocati di Test",
    "STUDIO_BAR_REGISTRATION_NUMBER": "A12345",
    "STUDIO_VAT_NUMBER": "IT12345678901",
    "STUDIO_TAX_CODE": "FOOXXX00X00X000X",
    "STUDIO_PEC_EMAIL": "studio@pec.test.local",
    "STUDIO_PHYSICAL_ADDRESS": "Via Test 1, 00000 Test City, Italy",
    "STUDIO_PROFESSIONAL_INSURANCE_INSURER": "Test Insurance Spa",
    "STUDIO_PROFESSIONAL_INSURANCE_POLICY": "POL-TEST-2026-0001",
    "STUDIO_PROFESSIONAL_INSURANCE_CEILING": "EUR 2.500.000",
}

EMPTY_STUDIO_FIELDS = {field: "" for field in ALL_STUDIO_FIELDS}


# ---------------------------------------------------------------------------
# Footer rendering — placeholder when env vars are empty
# ---------------------------------------------------------------------------


@override_settings(**EMPTY_STUDIO_FIELDS)
def test_footer_renders_section_with_placeholder_when_empty(db):
    resp = Client().get("/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "Professional identification" in html, (
        "Sezione Professional identification mancante nel footer"
    )
    assert PLACEHOLDER_TEXT in html, (
        "Placeholder visibile mancante quando le env var sono vuote"
    )


@override_settings(**EMPTY_STUDIO_FIELDS)
def test_footer_placeholder_appears_for_each_required_field(db):
    """Ogni campo obbligatorio mostra il proprio placeholder (visibile)."""
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    # Conta le occorrenze del placeholder. Almeno una per ogni macro-area
    # del footer (5 dl items: lawyer/bar, vat, pec, address, insurance).
    placeholder_count = html.count(PLACEHOLDER_TEXT)
    assert placeholder_count >= 5, (
        f"Atteso >=5 placeholder visibili (una per macro-area), "
        f"trovate {placeholder_count}"
    )


# ---------------------------------------------------------------------------
# Footer rendering — values appear when env vars are set
# ---------------------------------------------------------------------------


@override_settings(**ALL_STUDIO_FIELDS_FILLED)
def test_footer_renders_real_values_when_configured(db):
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    assert PLACEHOLDER_TEXT not in html, (
        "Placeholder ancora presente nonostante tutti i campi siano "
        "valorizzati: il footer non sta leggendo il context"
    )
    for value in ALL_STUDIO_FIELDS_FILLED.values():
        assert value in html, f"Valore atteso mancante nel footer: {value!r}"


# ---------------------------------------------------------------------------
# Footer rendering — i18n IT/FR/EN/AR
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", ["/", "/fr/", "/en/", "/ar/"])
@override_settings(**ALL_STUDIO_FIELDS_FILLED)
def test_footer_section_present_in_all_languages(path, db):
    resp = Client().get(path)
    assert resp.status_code == 200, f"GET {path} → {resp.status_code}"
    html = resp.content.decode("utf-8")
    # La sezione header e' tradotta via gettext. Testiamo l'attributo
    # data-* del DOM, che e' invariante per lingua.
    assert "data-studio-identification" in html, (
        f"{path}: sezione Professional identification mancante"
    )
    # L'avvocato Test Foo deve apparire (independente da lingua).
    assert "Avv. Test Foo" in html, f"{path}: valore lawyer mancante"


# ---------------------------------------------------------------------------
# System check core.W001 in dev (DEBUG=True)
# ---------------------------------------------------------------------------


@override_settings(DEBUG=True, **EMPTY_STUDIO_FIELDS)
def test_check_emits_warning_in_dev_when_fields_empty():
    issues = check_studio_professional_identification(app_configs=None)
    assert len(issues) == 1, f"Atteso 1 Warning consolidato, trovate {len(issues)}"
    issue = issues[0]
    assert isinstance(issue, Warning)
    assert issue.id == "core.W001"
    # Tutti i campi mancanti sono nominati nel messaggio.
    for field in REQUIRED_FIELDS:
        assert field in issue.msg


@override_settings(DEBUG=True, **ALL_STUDIO_FIELDS_FILLED)
def test_check_silent_in_dev_when_fields_configured():
    issues = check_studio_professional_identification(app_configs=None)
    assert issues == []


# ---------------------------------------------------------------------------
# System check core.E001 in prod (DEBUG=False)
# ---------------------------------------------------------------------------


@override_settings(DEBUG=False, **EMPTY_STUDIO_FIELDS)
def test_check_emits_errors_in_prod_when_fields_empty():
    issues = check_studio_professional_identification(app_configs=None)
    # Un Error per ogni campo obbligatorio mancante.
    assert len(issues) == len(REQUIRED_FIELDS), (
        f"Atteso {len(REQUIRED_FIELDS)} Error (uno per campo obbligatorio), "
        f"trovate {len(issues)}"
    )
    for issue in issues:
        assert isinstance(issue, Error)
        assert issue.id == "core.E001"
        assert issue.hint is not None


@override_settings(DEBUG=False, **ALL_STUDIO_FIELDS_FILLED)
def test_check_silent_in_prod_when_fields_configured():
    issues = check_studio_professional_identification(app_configs=None)
    assert issues == []


_PARTIAL_PROD = {**EMPTY_STUDIO_FIELDS, "STUDIO_LEAD_LAWYER_NAME": "Avv. X", "DEBUG": False}


@override_settings(**_PARTIAL_PROD)
def test_check_only_flags_missing_fields():
    """Se 1 campo e' valorizzato, vengono flaggati solo gli altri."""
    issues = check_studio_professional_identification(app_configs=None)
    # 7 obbligatori - 1 valorizzato = 6 errori attesi.
    assert len(issues) == len(REQUIRED_FIELDS) - 1
    flagged_fields = []
    for issue in issues:
        # L'errore include il nome del campo nel messaggio.
        for field in REQUIRED_FIELDS:
            if field in issue.msg:
                flagged_fields.append(field)
                break
    assert "STUDIO_LEAD_LAWYER_NAME" not in flagged_fields


_WHITESPACE_PROD = {**ALL_STUDIO_FIELDS_FILLED, "STUDIO_PEC_EMAIL": "   ", "DEBUG": False}


@override_settings(**_WHITESPACE_PROD)
def test_check_treats_whitespace_as_empty():
    """Una stringa di soli spazi deve essere trattata come vuota."""
    issues = check_studio_professional_identification(app_configs=None)
    assert len(issues) == 1
    assert issues[0].id == "core.E001"
    assert "STUDIO_PEC_EMAIL" in issues[0].msg


# ---------------------------------------------------------------------------
# Niente regressione su hreflang e meta robots
# ---------------------------------------------------------------------------


_HREFLANG_RE = re.compile(
    r'<link\s+[^>]*rel=["\']alternate["\'][^>]*hreflang=["\']([^"\']+)["\']',
    flags=re.IGNORECASE,
)


@override_settings(**ALL_STUDIO_FIELDS_FILLED)
def test_footer_does_not_break_hreflang_global(db):
    """Il footer non deve interferire con l'emissione hreflang."""
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    langs = {m.lower() for m in _HREFLANG_RE.findall(html)}
    assert {"it", "fr", "en", "ar", "x-default"}.issubset(langs)


@override_settings(**ALL_STUDIO_FIELDS_FILLED)
def test_footer_does_not_change_meta_robots_default(db):
    """Footer non interferisce con `index, follow` di default."""
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    assert 'name="robots" content="index, follow"' in html
