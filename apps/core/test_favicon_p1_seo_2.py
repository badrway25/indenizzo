"""
Tests F-p1-seo-2-favicon (P1-SEO-2 portion).

Regression coverage:

1. /favicon.ico responds 200 with `image/svg+xml` content type;
2. base.html exposes the local SVG favicon link;
3. base.html does NOT reference any external favicon CDN;
4. the favicon SVG file exists on disk under static/;
5. the lighthouserc.json gating set excludes the noindex wizard form;
6. P1-SEC-1 non-regression: no Google Fonts URLs leaked back into
   the public HTML on representative pages.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from django.test import Client

REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.django_db
def test_favicon_ico_returns_svg_200():
    resp = Client().get("/favicon.ico")
    assert resp.status_code == 200
    assert resp["Content-Type"].startswith("image/svg+xml")
    body = resp.content
    assert body.startswith(b"<svg") or b"<svg" in body[:200]


def test_base_html_links_local_favicon():
    base = (REPO_ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    assert 'rel="icon"' in base
    assert 'type="image/svg+xml"' in base
    # Must point at the local static asset, not a CDN.
    assert "favicon.svg" in base


def test_base_html_does_not_use_external_favicon_cdn():
    base = (REPO_ROOT / "templates" / "base.html").read_text(encoding="utf-8")
    forbidden = ("gstatic.com/favicon", "google.com/s2/favicons", "favicon.io")
    for needle in forbidden:
        assert needle not in base, f"base.html links external favicon: {needle}"


def test_favicon_svg_file_exists():
    p = REPO_ROOT / "static" / "img" / "favicon.svg"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "<svg" in text
    assert "</svg>" in text


def test_lighthouserc_excludes_noindex_wizard_forms():
    """The Lighthouse gating set must not include the concrete wizard
    forms — they are noindex by design and would always score low on
    SEO."""
    cfg = json.loads((REPO_ROOT / "lighthouserc.json").read_text(encoding="utf-8"))
    urls = cfg["ci"]["collect"]["url"]
    for needle in (
        "/wizard/it/road-accident",
        "/wizard/fr/road-accident",
        "/wizard/be/road-accident",
        "/wizard/ma/inheritance",
        "/wizard/tn/inheritance",
        "/wizard/result/",
        "/contact/thank-you",
    ):
        assert all(needle not in u for u in urls), (
            f"lighthouserc.json gates a noindex URL: {needle}"
        )


def test_lighthouserc_gates_thresholds_meet_user_brief():
    cfg = json.loads((REPO_ROOT / "lighthouserc.json").read_text(encoding="utf-8"))
    asserts = cfg["ci"]["assert"]["assertions"]
    # The brief asks: perf>=0.80, others>=0.90.
    perf = asserts["categories:performance"]
    assert perf[1]["minScore"] >= 0.80
    for cat in ("categories:accessibility", "categories:best-practices", "categories:seo"):
        spec = asserts[cat]
        assert spec[1]["minScore"] >= 0.90, f"{cat} threshold below 0.90"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "path", ["/", "/contact/", "/privacy/", "/disclaimer/", "/wizard/", "/ar/"],
)
def test_no_google_fonts_regressed(path):
    body = Client().get(path).content.decode("utf-8")
    assert "fonts.googleapis.com" not in body
    assert "fonts.gstatic.com" not in body


@pytest.mark.django_db
def test_csp_header_still_present_after_favicon_changes():
    resp = Client().get("/")
    keys = {k.lower() for k in resp.headers.keys()}
    assert "content-security-policy" in keys
