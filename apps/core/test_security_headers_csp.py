"""
Tests F-p0-codice-4-csp.

Coprono:
- emissione `Content-Security-Policy` quando `CSP_ENABLED=True` (default);
- emissione `Content-Security-Policy-Report-Only` quando
  `CSP_REPORT_ONLY=True`;
- nessun header CSP quando `CSP_ENABLED=False`;
- direttive minime di sicurezza (default-src, object-src, frame-ancestors,
  base-uri, form-action);
- nonce per-request in `script-src` e `style-src`;
- inline script/style nei template hanno `nonce="{{ CSP_NONCE }}"`;
- system check `core.E002` (CSP_ENABLED=False in prod) e `core.E003`
  (CSP_REPORT_ONLY=True in prod);
- nessuna regressione su hreflang, robots, footer professionale.
"""

from __future__ import annotations

import re

import pytest
from django.core.checks import Error
from django.test import Client, override_settings
from django.utils import translation

from apps.core.checks import (
    check_csp_enabled_in_production,
    check_csp_enforcing_in_production,
)


# ---------------------------------------------------------------------------
# Test isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_active_language():
    yield
    translation.deactivate_all()


CSP_HEADER = "Content-Security-Policy"
CSP_REPORT_ONLY_HEADER = "Content-Security-Policy-Report-Only"


def _csp_directives(header: str) -> dict[str, str]:
    """Parse 'directive-1 v1 v2; directive-2 v3' → {'directive-1': 'v1 v2', ...}."""
    out: dict[str, str] = {}
    for part in header.split(";"):
        part = part.strip()
        if not part:
            continue
        name, _, value = part.partition(" ")
        out[name.strip()] = value.strip()
    return out


# ---------------------------------------------------------------------------
# Header presence / absence
# ---------------------------------------------------------------------------


def test_home_emits_csp_header_when_enabled(db):
    """Default config: CSP enforcing su home."""
    resp = Client().get("/")
    assert resp.status_code == 200
    assert CSP_HEADER in resp.headers, (
        f"Atteso header {CSP_HEADER} ma headers={dict(resp.headers)}"
    )


def test_home_emits_only_enforcing_in_default_config(db):
    """Default: enforcing-only, niente report-only."""
    resp = Client().get("/")
    assert CSP_HEADER in resp.headers
    assert CSP_REPORT_ONLY_HEADER not in resp.headers


# ---------------------------------------------------------------------------
# Direttive minime di sicurezza
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "directive,expected_value",
    [
        ("default-src", "'self'"),
        ("object-src", "'none'"),
        ("frame-ancestors", "'none'"),
        ("base-uri", "'self'"),
        ("form-action", "'self'"),
    ],
)
def test_csp_locks_down_critical_directives(directive, expected_value, db):
    resp = Client().get("/")
    csp = resp.headers[CSP_HEADER]
    directives = _csp_directives(csp)
    assert directive in directives, (
        f"CSP directive {directive!r} mancante; trovate {list(directives.keys())}"
    )
    assert expected_value in directives[directive], (
        f"CSP {directive}={directives[directive]!r}, atteso contenga {expected_value!r}"
    )


def test_csp_does_not_use_unsafe_inline(db):
    """No `unsafe-inline` — usiamo nonce."""
    resp = Client().get("/")
    csp = resp.headers[CSP_HEADER]
    assert "'unsafe-inline'" not in csp, (
        f"CSP non deve usare 'unsafe-inline'; trovato in: {csp}"
    )


def test_csp_does_not_use_unsafe_eval(db):
    """No `unsafe-eval`: nessun eval/Function() ne usa."""
    resp = Client().get("/")
    csp = resp.headers[CSP_HEADER]
    assert "'unsafe-eval'" not in csp


# ---------------------------------------------------------------------------
# Nonce per-request
# ---------------------------------------------------------------------------


_NONCE_RE = re.compile(r"'nonce-([A-Za-z0-9+/=]+)'")


def test_csp_script_src_includes_per_request_nonce(db):
    """`script-src` include un `'nonce-<random>'`."""
    resp = Client().get("/")
    csp = resp.headers[CSP_HEADER]
    directives = _csp_directives(csp)
    script_src = directives.get("script-src", "")
    nonces = _NONCE_RE.findall(script_src)
    assert nonces, f"script-src senza nonce: {script_src!r}"


def test_csp_style_src_includes_per_request_nonce(db):
    resp = Client().get("/")
    csp = resp.headers[CSP_HEADER]
    directives = _csp_directives(csp)
    style_src = directives.get("style-src", "")
    nonces = _NONCE_RE.findall(style_src)
    assert nonces, f"style-src senza nonce: {style_src!r}"


def test_csp_nonce_changes_between_requests(db):
    """Il nonce deve essere diverso ad ogni request (random per-request)."""
    client = Client()
    resp1 = client.get("/")
    resp2 = client.get("/")
    nonce1 = _NONCE_RE.search(resp1.headers[CSP_HEADER]).group(1)
    nonce2 = _NONCE_RE.search(resp2.headers[CSP_HEADER]).group(1)
    assert nonce1 != nonce2, "Il nonce CSP deve essere unico per request"


def test_inline_style_tag_in_base_template_has_nonce_attribute(db):
    """L'inline `<style>` di base.html deve avere `nonce="..."`."""
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    nonce_in_header = _NONCE_RE.search(resp.headers[CSP_HEADER]).group(1)
    # Cerca lo `<style nonce="...">` nel rendering. Il nonce deve coincidere
    # con quello del header.
    style_pattern = re.compile(
        r'<style\s+nonce=["\']([^"\']+)["\']',
        flags=re.IGNORECASE,
    )
    match = style_pattern.search(html)
    assert match, "Inline <style> in base.html senza attributo nonce"
    assert match.group(1) == nonce_in_header, (
        f"<style nonce> ({match.group(1)}) != header nonce ({nonce_in_header})"
    )


def test_cookie_banner_inline_script_has_matching_nonce(db):
    """Il `<script>` del cookie banner deve avere nonce coerente."""
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    nonce_in_header = _NONCE_RE.search(resp.headers[CSP_HEADER]).group(1)
    # Cerca il <script nonce="..."> del banner.
    pattern = re.compile(
        r'<script\s+nonce=["\']([^"\']+)["\'][^>]*>[^<]*cookie-consent-banner',
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(html)
    assert match, "Cookie banner inline <script> senza nonce"
    assert match.group(1) == nonce_in_header


# ---------------------------------------------------------------------------
# Toggle: CSP_REPORT_ONLY
# ---------------------------------------------------------------------------


def _force_csp_report_only_settings():
    """
    Attiva CONTENT_SECURITY_POLICY_REPORT_ONLY senza CONTENT_SECURITY_POLICY,
    riusando la build di settings.
    """
    from csp.constants import NONCE, NONE, SELF

    return {
        "CSP_ENABLED": True,
        "CSP_REPORT_ONLY": True,
        "CONTENT_SECURITY_POLICY": None,
        "CONTENT_SECURITY_POLICY_REPORT_ONLY": {
            "DIRECTIVES": {
                "default-src": [SELF],
                "script-src": [SELF, NONCE],
                "style-src": [SELF, NONCE],
                "object-src": [NONE],
                "frame-ancestors": [NONE],
                "base-uri": [SELF],
                "form-action": [SELF],
            },
        },
    }


@override_settings(**_force_csp_report_only_settings())
def test_report_only_emits_only_report_only_header(db):
    resp = Client().get("/")
    assert resp.status_code == 200
    # Enforcing assente.
    assert CSP_HEADER not in resp.headers
    # Report-only presente.
    assert CSP_REPORT_ONLY_HEADER in resp.headers


# ---------------------------------------------------------------------------
# Toggle: CSP_ENABLED=False
# ---------------------------------------------------------------------------


@override_settings(
    CSP_ENABLED=False,
    CONTENT_SECURITY_POLICY=None,
    CONTENT_SECURITY_POLICY_REPORT_ONLY=None,
)
def test_csp_disabled_emits_no_header(db):
    resp = Client().get("/")
    assert resp.status_code == 200
    assert CSP_HEADER not in resp.headers
    assert CSP_REPORT_ONLY_HEADER not in resp.headers


# ---------------------------------------------------------------------------
# admin/staff: CSP attivo anche su back-office
# ---------------------------------------------------------------------------


def test_admin_login_has_csp_header(db):
    """`/admin/login/` deve essere protetto da CSP."""
    resp = Client().get("/admin/login/")
    # Accettiamo 200/302/404 a seconda della configurazione locale.
    if resp.status_code == 200:
        assert CSP_HEADER in resp.headers


# ---------------------------------------------------------------------------
# System checks core.E002 / core.E003
# ---------------------------------------------------------------------------


@override_settings(DEBUG=True, CSP_ENABLED=False)
def test_check_csp_silent_in_dev_when_disabled():
    """In dev, disattivare CSP e' tollerato (no error)."""
    issues = check_csp_enabled_in_production(app_configs=None)
    assert issues == []


@override_settings(DEBUG=False, CSP_ENABLED=False)
def test_check_csp_fails_in_prod_when_disabled():
    """In prod, CSP_ENABLED=False blocca."""
    issues = check_csp_enabled_in_production(app_configs=None)
    assert len(issues) == 1
    assert isinstance(issues[0], Error)
    assert issues[0].id == "core.E002"


@override_settings(DEBUG=False, CSP_ENABLED=True)
def test_check_csp_silent_in_prod_when_enabled():
    issues = check_csp_enabled_in_production(app_configs=None)
    assert issues == []


@override_settings(DEBUG=False, CSP_ENABLED=True, CSP_REPORT_ONLY=True)
def test_check_report_only_fails_in_prod():
    """In prod, CSP_REPORT_ONLY=True blocca: vogliamo enforcing."""
    issues = check_csp_enforcing_in_production(app_configs=None)
    assert len(issues) == 1
    assert isinstance(issues[0], Error)
    assert issues[0].id == "core.E003"


@override_settings(DEBUG=False, CSP_ENABLED=True, CSP_REPORT_ONLY=False)
def test_check_enforcing_silent_in_prod():
    issues = check_csp_enforcing_in_production(app_configs=None)
    assert issues == []


@override_settings(DEBUG=True, CSP_ENABLED=True, CSP_REPORT_ONLY=True)
def test_check_report_only_silent_in_dev():
    """Report-only in dev e' tollerato (debug aid)."""
    issues = check_csp_enforcing_in_production(app_configs=None)
    assert issues == []


@override_settings(DEBUG=False, CSP_ENABLED=False, CSP_REPORT_ONLY=True)
def test_check_e003_does_not_double_signal_when_e002_already_fires():
    """Se CSP e' disabilitato, core.E003 non deve doppio-segnalare."""
    issues = check_csp_enforcing_in_production(app_configs=None)
    assert issues == []  # E002 copre, E003 silente


# ---------------------------------------------------------------------------
# Niente regressione: hreflang, robots, footer professionale
# ---------------------------------------------------------------------------


def test_csp_does_not_break_hreflang_global(db):
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    # Cerca almeno hreflang it/fr/en/ar/x-default.
    expected = ["it", "fr", "en", "ar", "x-default"]
    for lang in expected:
        assert f'hreflang="{lang}"' in html, (
            f"hreflang={lang} mancante dopo CSP attivo"
        )


def test_csp_does_not_break_meta_robots_default(db):
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    assert 'name="robots" content="index, follow"' in html


def test_csp_does_not_break_footer_section(db):
    resp = Client().get("/")
    html = resp.content.decode("utf-8")
    assert "data-studio-identification" in html


# ---------------------------------------------------------------------------
# robots.txt: nessun CSP atteso (text/plain, irrelevant) ma non rompe.
# ---------------------------------------------------------------------------


def test_robots_txt_still_serves_after_csp(db):
    resp = Client().get("/robots.txt")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("text/plain")
