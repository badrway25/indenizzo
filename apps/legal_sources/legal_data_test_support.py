"""Test support: skip checks that need gitignored local assets.

Some tests verify the integrity of official legal-source documents
(``legal_data/sources/**/*.pdf|*.html``) or Pexels hero media
(``MEDIA_ROOT/pexels/*.webp``). Those raw assets are **gitignored**: present
on a developer machine with a local ``legal_data`` tree / media, or after a
``manual_attach``, but **absent on a fresh CI checkout**.

These helpers let such tests still run their real assertions when the asset is
present, and SKIP (never FALSE-pass, never fail) when it is absent. This keeps
the checks meaningful locally without making CI red for an environmental gap.

NOTE: this module is intentionally NOT a ``test_*`` module, so pytest does not
collect it.
"""

from __future__ import annotations

from pathlib import Path

import pytest


def skip_if_absent(*paths) -> None:
    """Skip the current test if any of ``paths`` does not exist on disk."""
    missing = [str(p) for p in paths if not Path(p).exists()]
    if missing:
        pytest.skip(
            "legal_data source file(s) absent (gitignored — present only with a "
            "local legal_data tree or after manual_attach; e.g. a fresh CI "
            "checkout). Missing: " + ", ".join(missing)
        )


def skip_if_no_pexels_webp() -> None:
    """Skip when no Pexels WebP companions are present under MEDIA_ROOT/pexels.

    The home/landing hero emits a ``<picture>`` only when the WebP companions
    exist on disk (see ``apps.core.views._pexels_hero``). On a checkout without
    Pexels media (CI) the page renders only the ``<img>`` fallback, so a test
    asserting ``<picture>`` must skip rather than fail.
    """
    from django.conf import settings

    pexels_dir = Path(settings.MEDIA_ROOT) / "pexels"
    if not pexels_dir.is_dir() or not any(pexels_dir.glob("*.webp")):
        pytest.skip(
            "Pexels WebP media absent under MEDIA_ROOT/pexels (gitignored; "
            "absent on a fresh CI checkout) — the hero <picture> is not emitted."
        )
