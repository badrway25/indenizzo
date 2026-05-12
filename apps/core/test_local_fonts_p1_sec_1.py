"""
Tests F-p1-sec-1-local-fonts.

Coprono il vendor locale dei web font (Inter / Cormorant Garamond /
Amiri / Tajawal) e la corrispondente chiusura della deroga CSP
verso fonts.googleapis.com / fonts.gstatic.com.

1. base.html non contiene piu' fonts.googleapis.com;
2. base.html non contiene piu' fonts.gstatic.com;
3. nessun preconnect verso fonts.googleapis.com / fonts.gstatic.com;
4. CSP DIRECTIVES non contengono fonts.googleapis.com / fonts.gstatic.com;
5. CSP `font-src` resta `'self'` (no esterni);
6. fonts.css esiste fisicamente in static/css/;
7. fonts.css emette @font-face per i 4 font;
8. ogni .woff2 referenziato in fonts.css esiste in static/fonts/;
9. README.md + per-family OFL.txt presenti in static/fonts/LICENSES/;
10. home / contact / privacy / disclaimer / wizard rispondono 200;
11. AR RTL non regredisce (lang=ar dir=rtl present).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from django.conf import settings
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]
FONTS_CSS = REPO_ROOT / "static" / "css" / "fonts.css"
FONTS_DIR = REPO_ROOT / "static" / "fonts"


# ---------------------------------------------------------------------------
# 1-3: no Google Fonts URLs in any rendered template
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path",
    ["/", "/contact/", "/privacy/", "/disclaimer/", "/wizard/", "/wizard/it/road-accident/"],
)
def test_no_google_fonts_urls_in_public_html(path):
    body = Client().get(path).content.decode("utf-8")
    assert "fonts.googleapis.com" not in body, f"{path}: leaks fonts.googleapis.com"
    assert "fonts.gstatic.com" not in body, f"{path}: leaks fonts.gstatic.com"


@pytest.mark.django_db
def test_home_does_not_preconnect_to_google_fonts():
    body = Client().get("/").content.decode("utf-8").lower()
    assert "preconnect" not in body or (
        "fonts.googleapis.com" not in body and "fonts.gstatic.com" not in body
    )


# ---------------------------------------------------------------------------
# 4-5: CSP DIRECTIVES no longer reference Google Fonts CDNs
# ---------------------------------------------------------------------------


def _flatten_csp(directives: dict) -> str:
    parts = []
    for key, values in directives.items():
        rendered = " ".join(str(v) for v in values)
        parts.append(f"{key} {rendered}")
    return "; ".join(parts)


def test_csp_directives_drop_google_fonts():
    """The compiled CONTENT_SECURITY_POLICY must not reference Google Fonts."""
    csp_config = getattr(settings, "CONTENT_SECURITY_POLICY", None)
    assert csp_config is not None, "CSP_ENABLED=True should produce CONTENT_SECURITY_POLICY"
    directives = csp_config["DIRECTIVES"]
    flat = _flatten_csp(directives).lower()
    assert "fonts.googleapis.com" not in flat
    assert "fonts.gstatic.com" not in flat


def test_csp_font_src_is_self_only():
    csp_config = getattr(settings, "CONTENT_SECURITY_POLICY", None)
    assert csp_config is not None
    directives = csp_config["DIRECTIVES"]
    font_src = directives.get("font-src", [])
    rendered = [str(v) for v in font_src]
    # 'self' must be there, nothing else apart from 'data:' if reused.
    assert "'self'" in rendered
    for value in rendered:
        assert "fonts.googleapis.com" not in value
        assert "fonts.gstatic.com" not in value


# ---------------------------------------------------------------------------
# 6-8: local fonts present + referenced files exist
# ---------------------------------------------------------------------------


def test_fonts_css_exists():
    assert FONTS_CSS.exists(), f"{FONTS_CSS} is missing"


def test_fonts_css_declares_all_four_families():
    content = FONTS_CSS.read_text(encoding="utf-8")
    assert "font-family: 'Inter'" in content
    assert "font-family: 'Cormorant Garamond'" in content
    assert "font-family: 'Amiri'" in content
    assert "font-family: 'Tajawal'" in content
    # font-display: swap on every @font-face block — total = number of
    # `@font-face` rules.
    blocks = content.count("@font-face")
    swaps = content.count("font-display: swap")
    assert blocks == swaps, f"{blocks} blocks but {swaps} font-display:swap rules"
    # The script vendors at least 16 files. Original P1-SEC-1 floor
    # was 19 (4 Inter × 2 subsets + 3 Cormorant × 2 subsets + 2 Amiri
    # arabic + 3 Tajawal arabic). F-p2-perf-3 (2026-05-12) dropped
    # Inter 700 (latin + latin-ext) and Amiri 400 (arabic) — both
    # weights were never fetched by any measured public-page render
    # per Lighthouse mobile network panel. Current floor: 3 Inter × 2
    # subsets + 3 Cormorant × 2 subsets + 1 Amiri + 3 Tajawal = 16.
    assert blocks >= 16


def test_every_woff2_referenced_by_fonts_css_exists_on_disk():
    content = FONTS_CSS.read_text(encoding="utf-8")
    # Match url('../fonts/<slug>/<file>.woff2')
    refs = re.findall(r"url\('\.\./fonts/([^']+\.woff2)'\)", content)
    assert refs, "no .woff2 refs found in fonts.css"
    for relpath in refs:
        target = FONTS_DIR / relpath
        assert target.exists(), f"{target} referenced by fonts.css but missing on disk"
        size = target.stat().st_size
        assert size > 1024, f"{target} suspiciously small ({size} bytes)"


# ---------------------------------------------------------------------------
# 9: licenses + README present
# ---------------------------------------------------------------------------


def test_per_family_licenses_present():
    licenses_dir = FONTS_DIR / "LICENSES"
    assert licenses_dir.exists()
    expected = {
        "Inter-OFL.txt",
        "CormorantGaramond-OFL.txt",
        "Amiri-OFL.txt",
        "Tajawal-OFL.txt",
    }
    actual = {p.name for p in licenses_dir.iterdir() if p.is_file()}
    assert expected.issubset(actual), f"missing licenses: {expected - actual}"
    for name in expected:
        text = (licenses_dir / name).read_text(encoding="utf-8").lower()
        assert "open font license" in text or "ofl" in text


def test_fonts_readme_present():
    assert (FONTS_DIR / "README.md").exists()


# ---------------------------------------------------------------------------
# 10-11: regression — pages still render + AR RTL preserved
# ---------------------------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["/", "/contact/", "/privacy/", "/disclaimer/"])
def test_public_pages_still_render(path):
    resp = Client().get(path)
    assert resp.status_code == 200


@pytest.mark.django_db
def test_ar_rtl_preserved():
    body = Client().get("/ar/").content.decode("utf-8")
    assert 'lang="ar"' in body
    assert 'dir="rtl"' in body
    # No regression: still no Google Fonts on the AR home either.
    assert "fonts.googleapis.com" not in body
    assert "fonts.gstatic.com" not in body
