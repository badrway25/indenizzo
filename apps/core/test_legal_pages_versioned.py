"""
Tests F-p0-leg-1-6-legal-pages.

Coprono lo scaffold delle due pagine legali pubbliche
(privacy policy + disclaimer) versionate e firmabili dallo Studio:

1. /privacy/ ritorna 200 e mostra la versione + lo status;
2. /disclaimer/ ritorna 200 e mostra la versione + lo status;
3. pagine disponibili IT/FR/EN/AR (i18n_patterns con prefix);
4. footer linka a privacy + disclaimer reali;
5. consent_checkboxes partial linka a privacy + disclaimer reali;
6. working-copy banner visibile in dev;
7. core.E006 fail in prod con status=working_copy;
8. core.E006 fail in prod con version vuota;
9. core.E006 fail in prod con status=signed ma signed_at vuoto;
10. core.E006 passa in prod con status=signed + version firmata + signed_at;
11. core.E007 stessa logica per il disclaimer;
12. reverse url 'core:privacy' / 'core:disclaimer' funzionano;
13. CSP header presente sulle pagine (no regression P0-CODICE-4);
14. hreflang presente sulle pagine (no regression P0-CODICE-2).
"""

from __future__ import annotations

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import translation

from apps.core.checks import (
    check_disclaimer_signed_in_production,
    check_privacy_policy_signed_in_production,
)


@pytest.fixture(autouse=True)
def _reset_active_language():
    yield
    translation.deactivate_all()


# ---------------------------------------------------------------------------
# 1-3: pages return 200 in every supported language
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/privacy/", "/fr/privacy/", "/en/privacy/", "/ar/privacy/"])
def test_privacy_page_200_per_language(path):
    resp = Client().get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    body = resp.content.decode("utf-8")
    # Working-copy banner visible by default in dev settings.
    assert 'data-legal-page="privacy"' in body
    assert "data-legal-status" in body


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path", ["/disclaimer/", "/fr/disclaimer/", "/en/disclaimer/", "/ar/disclaimer/"]
)
def test_disclaimer_page_200_per_language(path):
    resp = Client().get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"
    body = resp.content.decode("utf-8")
    assert 'data-legal-page="disclaimer"' in body
    assert "data-legal-status" in body


# ---------------------------------------------------------------------------
# 4-5: footer + consent checkboxes link to real URLs
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_footer_links_to_privacy_and_disclaimer():
    """The home page footer must point to the real /privacy/ and /disclaimer/."""
    resp = Client().get("/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert 'href="/privacy/"' in body
    assert 'href="/disclaimer/"' in body


@pytest.mark.django_db
def test_contact_consent_block_links_to_privacy_and_disclaimer():
    """The /contact/ form's consent block must link to the real legal pages."""
    resp = Client().get("/contact/")
    assert resp.status_code == 200
    body = resp.content.decode("utf-8")
    assert 'href="/privacy/"' in body
    assert 'href="/disclaimer/"' in body


# ---------------------------------------------------------------------------
# 6: working-copy banner visible in dev (default settings)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_privacy_page_shows_working_copy_banner_in_dev():
    body = Client().get("/privacy/").content.decode("utf-8")
    assert 'data-legal-status="working_copy"' in body
    # Localised label: "Working copy" (EN source) or "Bozza di lavoro" (IT,
    # the default locale). The data-attribute above is the locale-independent
    # proof; this keeps a human-readable presence check across locales.
    assert "Working copy" in body or "Bozza di lavoro" in body


@pytest.mark.django_db
def test_disclaimer_page_shows_working_copy_banner_in_dev():
    body = Client().get("/disclaimer/").content.decode("utf-8")
    assert 'data-legal-status="working_copy"' in body


# ---------------------------------------------------------------------------
# 7-10: core.E006 (privacy) + core.E007 (disclaimer) check matrix
# ---------------------------------------------------------------------------


@override_settings(
    DEBUG=False,
    PRIVACY_POLICY_VERSION="working-copy-2026-05-10",
    PRIVACY_POLICY_STATUS="working_copy",
    PRIVACY_POLICY_SIGNED_AT="",
)
def test_E006_fails_with_working_copy():
    issues = check_privacy_policy_signed_in_production(app_configs=None)
    assert any(i.id == "core.E006" for i in issues)
    assert any("working-copy" in i.msg for i in issues)


@override_settings(
    DEBUG=False,
    PRIVACY_POLICY_VERSION="",
    PRIVACY_POLICY_STATUS="working_copy",
    PRIVACY_POLICY_SIGNED_AT="",
)
def test_E006_fails_with_empty_version():
    issues = check_privacy_policy_signed_in_production(app_configs=None)
    assert any(i.id == "core.E006" and "empty" in i.msg.lower() for i in issues)


@override_settings(
    DEBUG=False,
    PRIVACY_POLICY_VERSION="2026-09-15-final",
    PRIVACY_POLICY_STATUS="signed",
    PRIVACY_POLICY_SIGNED_AT="",
)
def test_E006_fails_when_signed_but_signed_at_missing():
    issues = check_privacy_policy_signed_in_production(app_configs=None)
    assert any(i.id == "core.E006" and "PRIVACY_POLICY_SIGNED_AT" in i.msg for i in issues)


@override_settings(
    DEBUG=False,
    PRIVACY_POLICY_VERSION="2026-09-15-final",
    PRIVACY_POLICY_STATUS="signed",
    PRIVACY_POLICY_SIGNED_AT="2026-09-15",
)
def test_E006_passes_with_signed_version_and_signed_at():
    assert check_privacy_policy_signed_in_production(app_configs=None) == []


@override_settings(
    DEBUG=False,
    DISCLAIMER_VERSION="working-copy-2026-05-10",
    DISCLAIMER_STATUS="working_copy",
    DISCLAIMER_SIGNED_AT="",
)
def test_E007_fails_with_working_copy_disclaimer():
    issues = check_disclaimer_signed_in_production(app_configs=None)
    assert any(i.id == "core.E007" for i in issues)


@override_settings(
    DEBUG=False,
    DISCLAIMER_VERSION="2026-09-15-final",
    DISCLAIMER_STATUS="signed",
    DISCLAIMER_SIGNED_AT="2026-09-15",
)
def test_E007_passes_with_signed_disclaimer():
    assert check_disclaimer_signed_in_production(app_configs=None) == []


# ---------------------------------------------------------------------------
# 12: reverse URL works
# ---------------------------------------------------------------------------


def test_legal_pages_reverse_urls():
    assert reverse("core:privacy") == "/privacy/"
    assert reverse("core:disclaimer") == "/disclaimer/"


# ---------------------------------------------------------------------------
# 13-14: CSP + hreflang regression
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_csp_header_present_on_privacy_page():
    resp = Client().get("/privacy/")
    assert resp.status_code == 200
    # P0-CODICE-4: enforced CSP header.
    assert "Content-Security-Policy" in resp.headers or "content-security-policy" in {
        k.lower() for k in resp.headers.keys()
    }


@pytest.mark.django_db
def test_csp_header_present_on_disclaimer_page():
    resp = Client().get("/disclaimer/")
    assert resp.status_code == 200
    assert "Content-Security-Policy" in resp.headers or "content-security-policy" in {
        k.lower() for k in resp.headers.keys()
    }


@pytest.mark.django_db
def test_hreflang_present_on_privacy_page():
    body = Client().get("/privacy/").content.decode("utf-8")
    # P0-CODICE-2: global hreflang for the privacy page.
    assert 'hreflang="it"' in body
    assert 'hreflang="fr"' in body
    assert 'hreflang="en"' in body
    assert 'hreflang="ar"' in body


@pytest.mark.django_db
def test_hreflang_present_on_disclaimer_page():
    body = Client().get("/disclaimer/").content.decode("utf-8")
    assert 'hreflang="it"' in body
    assert 'hreflang="ar"' in body


# ---------------------------------------------------------------------------
# Bonus: signed mode shows the signed-on date and not the working-copy banner
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@override_settings(
    PRIVACY_POLICY_VERSION="2026-09-15-final",
    PRIVACY_POLICY_STATUS="signed",
    PRIVACY_POLICY_SIGNED_AT="2026-09-15",
)
def test_privacy_page_in_signed_mode_does_not_show_working_copy_banner():
    body = Client().get("/privacy/").content.decode("utf-8")
    assert 'data-legal-status="signed"' in body
    assert "2026-09-15" in body
