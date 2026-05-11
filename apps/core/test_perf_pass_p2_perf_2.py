"""
Tests F-p2-perf-2-critical-css-performance.

Negative-result iter. The async-CSS approach was implemented +
measured + reverted on the same branch (see
`docs/qa/lighthouse-mobile-baseline/P2_PERF_2_COMPARISON.md`).
These tests pin the post-revert state of base.html so a future
drive-by edit doesn't silently re-introduce the experimental
change without going through a fresh iter.

Specifically we assert:
 1. The P2-PERF-2 report exists and is non-trivial.
 2. The P2-PERF-2 NOTES exist.
 3. base.html still loads site.css as a render-blocking <link>
    (the conservative baseline).
 4. base.html does NOT include the experimental partial
    `partials/_critical_css.html`.
 5. base.html does NOT load a `css-loader.js` script.
 6. The experimental partial / JS file are NOT in the tree.
 7. CSP did not regress (no 'unsafe-inline' / 'unsafe-eval').
 8. base.html carries the in-file pointer to the comparison report.
 9. /  and /ar/ still render 200 with the expected dir.

If a future iter intentionally wants to retry the async path,
delete these tests as part of that iter.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE_HTML = REPO_ROOT / "templates" / "base.html"
SETTINGS_PY = REPO_ROOT / "config" / "settings.py"
REPORT = (
    REPO_ROOT
    / "docs"
    / "qa"
    / "lighthouse-mobile-baseline"
    / "P2_PERF_2_COMPARISON.md"
)
NOTES = (
    REPO_ROOT
    / "docs"
    / "screenshots"
    / "delta_audit_2026-05-10"
    / "after"
    / "p2-critical-css-performance"
    / "NOTES.md"
)
EXPERIMENTAL_PARTIAL = (
    REPO_ROOT / "templates" / "partials" / "_critical_css.html"
)
EXPERIMENTAL_JS = REPO_ROOT / "static" / "js" / "css-loader.js"


def _base() -> str:
    return BASE_HTML.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 1-2. Report + NOTES exist
# ---------------------------------------------------------------------------


def test_p2_perf_2_report_exists():
    assert REPORT.exists()
    assert REPORT.stat().st_size > 2000


def test_p2_perf_2_notes_exist():
    assert NOTES.exists()


def test_report_documents_experiment_was_reverted():
    text = REPORT.read_text(encoding="utf-8")
    assert "Experiment NOT shipped" in text
    assert "Reverted" in text or "reverted" in text


# ---------------------------------------------------------------------------
# 3-5. base.html stays on the conservative path
# ---------------------------------------------------------------------------


def test_base_html_loads_site_css_as_render_blocking_link():
    text = _base()
    # Plain render-blocking stylesheet link, no media-swap tricks.
    assert "<link rel=\"stylesheet\" href=\"{% static 'css/site.css' %}\">" in text


def test_base_html_does_not_include_experimental_critical_partial():
    text = _base()
    assert "_critical_css.html" not in text


def test_base_html_does_not_load_css_loader_script():
    text = _base()
    assert "css-loader.js" not in text


def test_base_html_does_not_preload_site_css_as_style():
    text = _base()
    # The experiment used `<link rel="preload" as="style" href="site.css">`.
    # The conservative baseline does not.
    assert 'as="style"' not in text


def test_base_html_carries_pointer_to_comparison_report():
    text = _base()
    # The in-file note may use either P2-PERF-2 / p2-perf-2 / F-p2-perf-2
    # — accept any variant. The load-bearing string is the report path.
    assert "P2_PERF_2_COMPARISON.md" in text
    assert "p2-perf-2" in text.lower()


# ---------------------------------------------------------------------------
# 6. Experimental files are NOT in the tree
# ---------------------------------------------------------------------------


def test_experimental_critical_partial_is_deleted():
    assert not EXPERIMENTAL_PARTIAL.exists(), (
        "The experimental critical-CSS partial must be deleted. If a "
        "future iter intentionally wants to re-add it, delete this "
        "assertion as part of that iter."
    )


def test_experimental_css_loader_js_is_deleted():
    assert not EXPERIMENTAL_JS.exists(), (
        "The experimental css-loader.js must be deleted. If a future "
        "iter intentionally wants to re-add it, delete this assertion "
        "as part of that iter."
    )


# ---------------------------------------------------------------------------
# 7. CSP didn't regress
# ---------------------------------------------------------------------------


def test_csp_has_no_unsafe_inline_or_eval():
    text = SETTINGS_PY.read_text(encoding="utf-8")
    assert "'unsafe-inline'" not in text
    assert "'unsafe-eval'" not in text


# ---------------------------------------------------------------------------
# 8-9. / and /ar/ still render correctly
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_home_renders_with_ltr(client):
    resp = client.get("/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    assert 'dir="ltr"' in resp.content.decode("utf-8")


@pytest.mark.django_db
def test_ar_home_renders_with_rtl(client):
    resp = client.get("/ar/", HTTP_HOST="127.0.0.1")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert 'dir="rtl"' in html
    # Site.css is a render-blocking <link>, not async.
    assert "css/site.css" in html
    assert "css-loader.js" not in html
