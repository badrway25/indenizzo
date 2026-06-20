"""
Tests for the CSP-safe language switcher (REQ-1 multilingua).

The platform enforces a strict CSP (`script-src 'self' <nonce>`, no
`unsafe-inline`; see ``config/settings.py`` and ``apps/core/checks.py``
``core.E002``/``core.E003``). Inline event-handler attributes such as
``onchange="this.form.submit()"`` are blocked by that policy, which would
silently break the language switcher in production (the JS-enabled user
sees a ``<select>`` that changes value but never submits, and the
``<noscript>`` fallback does not render because JS *is* enabled).

These tests lock the regression: the auto-submit must be wired through a
nonce'd ``<script>`` and never via an inline handler.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.test import Client
from django.urls import reverse

PARTIAL = (
    Path(__file__).resolve().parents[2]
    / "templates"
    / "partials"
    / "language_switcher.html"
)


def test_language_switcher_partial_has_no_inline_onchange():
    """No inline `onchange` (or any inline `on*` handler) — CSP would block it."""
    text = PARTIAL.read_text(encoding="utf-8")
    assert "onchange" not in text, (
        "inline onchange handler is blocked by the enforced CSP; "
        "wire auto-submit via the nonce'd <script> instead"
    )


def test_language_switcher_partial_uses_nonced_script():
    """Auto-submit is wired by a nonce'd script attaching a change listener."""
    text = PARTIAL.read_text(encoding="utf-8")
    assert 'nonce="{{ CSP_NONCE }}"' in text
    assert "addEventListener" in text


def test_language_switcher_partial_still_posts_to_set_language():
    """The control still POSTs to Django's set_language view (CSRF-safe)."""
    text = PARTIAL.read_text(encoding="utf-8")
    assert "set_language" in text
    assert 'method="post"' in text


@pytest.mark.django_db
def test_home_renders_switcher_select_without_inline_handler():
    """End-to-end: the rendered home page exposes the select, no inline handler."""
    response = Client().get(reverse("core:home"))
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert 'id="lang-switcher"' in html
    assert 'name="language"' in html
    # The rendered switcher markup carries no inline onchange handler.
    assert "onchange=" not in html
