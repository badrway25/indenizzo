"""
Tests F-p2-perf-1-mobile-performance-pass.

Static-side smoke tests for the perf interventions:

 1. WhiteNoise is installed, configured, in MIDDLEWARE, in INSTALLED_APPS;
 2. GZipMiddleware is in MIDDLEWARE;
 3. base.html serves the inline critical CSS BEFORE the external stylesheets;
 4. base.html preloads above-the-fold LTR fonts via <link rel="preload"
    as="font" crossorigin> — but ONLY for LTR pages;
 5. base.html does NOT load any Google Font URL;
 6. CSP did not regress (no `unsafe-inline` / `unsafe-eval`);
 7. precompress_static management command exists and is importable;
 8. precompress_static targets only project tree, never .venv;
 9. Lighthouse runner scripts call precompress_static;
10. /ar/ home page still renders with dir="rtl" and 200 status.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_HTML = REPO_ROOT / "templates" / "base.html"
SETTINGS_PY = REPO_ROOT / "config" / "settings.py"
RUNNER_DESKTOP = REPO_ROOT / "scripts" / "run_lighthouse_local.sh"
RUNNER_MOBILE = REPO_ROOT / "scripts" / "run_lighthouse_mobile_local.sh"
REQUIREMENTS = REPO_ROOT / "requirements.txt"


# ---------------------------------------------------------------------------
# 1-2. WhiteNoise + GZipMiddleware are wired
# ---------------------------------------------------------------------------


def test_whitenoise_is_in_requirements():
    text = REQUIREMENTS.read_text(encoding="utf-8")
    assert "whitenoise" in text.lower()


def test_whitenoise_middleware_in_settings():
    text = SETTINGS_PY.read_text(encoding="utf-8")
    assert "whitenoise.middleware.WhiteNoiseMiddleware" in text


def test_whitenoise_runserver_nostatic_app_listed_before_staticfiles():
    """`whitenoise.runserver_nostatic` must appear in INSTALLED_APPS
    BEFORE `django.contrib.staticfiles` for the management-command
    resolution to subclass `runserver` correctly."""
    text = SETTINGS_PY.read_text(encoding="utf-8")
    wn_pos = text.find('"whitenoise.runserver_nostatic"')
    sf_pos = text.find('"django.contrib.staticfiles"')
    assert wn_pos > 0
    assert sf_pos > 0
    assert wn_pos < sf_pos, (
        "whitenoise.runserver_nostatic must be listed before "
        "django.contrib.staticfiles in INSTALLED_APPS"
    )


def test_gzip_middleware_in_settings():
    text = SETTINGS_PY.read_text(encoding="utf-8")
    assert "django.middleware.gzip.GZipMiddleware" in text


def test_whitenoise_use_finders_enabled_for_dev():
    text = SETTINGS_PY.read_text(encoding="utf-8")
    assert "WHITENOISE_USE_FINDERS" in text


# ---------------------------------------------------------------------------
# 3-4. base.html: critical CSS first, preload only for LTR
# ---------------------------------------------------------------------------


def _base_html() -> str:
    return BASE_HTML.read_text(encoding="utf-8")


def test_base_html_inline_style_comes_before_external_stylesheets():
    text = _base_html()
    style_pos = text.find('<style nonce="{{ CSP_NONCE }}">')
    site_css_pos = text.find("'css/site.css'")
    fonts_css_pos = text.find("'css/fonts.css'")
    assert style_pos > 0
    assert site_css_pos > 0
    assert fonts_css_pos > 0
    assert style_pos < site_css_pos, (
        "inline critical <style> must be emitted before site.css"
    )
    assert style_pos < fonts_css_pos, (
        "inline critical <style> must be emitted before fonts.css"
    )


def test_base_html_preloads_ltr_fonts():
    text = _base_html()
    # LTR pages preload Inter latin + Cormorant Garamond.
    # F-p2-perf-3 (2026-05-12): Cormorant preload tracks weight 700
    # (h1/h2/h3 default-bold) instead of 600 — see
    # `docs/qa/lighthouse-mobile-baseline/P2_PERF_3_COMPARISON.md`.
    assert 'rel="preload"' in text
    assert 'as="font"' in text
    assert "crossorigin" in text
    assert "inter-400-latin.woff2" in text
    assert "cormorant-garamond-700-latin.woff2" in text


def test_base_html_does_not_preload_rtl_fonts():
    """RTL pages deliberately skip the font preload to avoid competing
    with the hero image for HTTP/1.1 connection slots — preserves LCP
    on /ar/. The preload tags must therefore be guarded by
    `{% if not IS_RTL %}`."""
    text = _base_html()
    # The preload block must be inside a `{% if not IS_RTL %}` guard.
    # Find the preload block and check the surrounding template tag.
    m = re.search(
        r"\{%\s*if\s+not\s+IS_RTL\s*%\}.*?inter-400-latin\.woff2.*?\{%\s*endif\s*%\}",
        text,
        re.DOTALL,
    )
    assert m is not None, (
        "preload for Inter/Cormorant fonts must be inside "
        "`{% if not IS_RTL %}` guard"
    )
    # And the RTL fonts (Tajawal, Amiri) must NOT appear as preloads.
    # They can still be referenced as @font-face inside fonts.css; we
    # only forbid `rel="preload"` lines pointing at them.
    rtl_preload = re.search(
        r'rel="preload"[^>]*tajawal', text, re.IGNORECASE
    )
    assert rtl_preload is None, (
        "tajawal must NOT be in a preload — would compete with hero image on /ar/"
    )
    rtl_preload2 = re.search(
        r'rel="preload"[^>]*amiri', text, re.IGNORECASE
    )
    assert rtl_preload2 is None, (
        "amiri must NOT be in a preload — would compete with hero image on /ar/"
    )


# ---------------------------------------------------------------------------
# 5-6. No Google Fonts URL leak; CSP didn't regress
# ---------------------------------------------------------------------------


def test_base_html_has_no_google_fonts_url():
    text = _base_html()
    forbidden = (
        "fonts.googleapis.com",
        "fonts.gstatic.com",
        "googleapis.com",
    )
    for f in forbidden:
        assert f not in text, f"Google Fonts URL leaked into base.html: {f}"


def test_csp_has_no_unsafe_inline_or_eval():
    text = SETTINGS_PY.read_text(encoding="utf-8")
    # CSP directives are defined via CSP_DIRECTIVES dict; we scan the
    # whole settings file for `'unsafe-inline'` and `'unsafe-eval'`.
    assert "'unsafe-inline'" not in text, "CSP must not allow unsafe-inline"
    assert "'unsafe-eval'" not in text, "CSP must not allow unsafe-eval"


# ---------------------------------------------------------------------------
# 7-8. precompress_static command
# ---------------------------------------------------------------------------


def test_precompress_static_command_imports():
    from apps.core.management.commands import precompress_static  # noqa: F401


def test_precompress_static_command_is_scoped_to_project_tree():
    """The command must NOT walk `.venv` / `site-packages` — that
    would write .gz companions inside third-party packages."""
    cmd_path = (
        REPO_ROOT
        / "apps"
        / "core"
        / "management"
        / "commands"
        / "precompress_static.py"
    )
    text = cmd_path.read_text(encoding="utf-8")
    # Scoping guard: the file must reference BASE_DIR and resolve
    # roots against it.
    assert "BASE_DIR" in text
    assert "relative_to" in text


@pytest.mark.django_db
def test_precompress_static_command_runs_without_writing_to_venv(tmp_path):
    """Run the command and assert it didn't write into .venv/."""
    from apps.core.management.commands.precompress_static import Command

    cmd = Command()
    cmd.stdout = type("S", (), {"write": lambda *_: None})()
    # Just call the collect to get a target list; we don't want to
    # actually rewrite .gz on every test run.
    targets = cmd._collect_targets()
    for t in targets:
        assert ".venv" not in str(t), f"target inside .venv: {t}"
        assert "site-packages" not in str(t), f"target inside site-packages: {t}"


# ---------------------------------------------------------------------------
# 9. Lighthouse runner scripts wire precompress_static
# ---------------------------------------------------------------------------


def test_desktop_lighthouse_runner_calls_precompress():
    text = RUNNER_DESKTOP.read_text(encoding="utf-8")
    assert "precompress_static" in text


def test_mobile_lighthouse_runner_calls_precompress():
    text = RUNNER_MOBILE.read_text(encoding="utf-8")
    assert "precompress_static" in text


# ---------------------------------------------------------------------------
# 10. /ar/ home still renders correctly
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_ar_home_renders_with_rtl(client):
    resp = client.get("/ar/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'dir="rtl"' in html
    # And: the LTR preload block must NOT appear (we're on /ar/).
    assert "inter-400-latin.woff2" not in html


@pytest.mark.django_db
def test_default_home_renders_with_ltr_and_preload(client):
    resp = client.get("/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'dir="ltr"' in html
    # LTR preload block must be present.
    assert "inter-400-latin.woff2" in html
    assert 'rel="preload"' in html
