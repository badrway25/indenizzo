"""Repo-root conftest — F-legal-data-test-fixture-isolation-pass1.

Every test that touches a legal-data command must write into a
disposable per-test directory, never into the real
``legal_data/sources/**`` tree. We enforce this with an
``autouse=True`` fixture that redirects ``settings.LEGAL_DATA_ROOT``
to a temporary directory for the duration of the test.

The bug this prevents: the previous test suite called the
production fetch command (``sync_official_sources``) with a
synthetic payload (``b"%PDF-1.4 fake test payload " + b"x" * 200``,
exactly 227 bytes), and the command wrote that stub straight on top
of the real ``legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf``
download. With this fixture in place, the same call lands in a
``tmp_path``-rooted clone of the tree and the real bytes on disk
stay untouched.

A separate guard test (``apps/legal_sources/test_legal_data_test_fixture_isolation.py``)
double-checks the protection by asserting (a) the setting is
overridden during pytest, (b) "fake test payload" never appears
under the real ``legal_data/sources/**`` tree, and (c) the three
fetch / attach / download commands all read their base directory
from ``settings.LEGAL_DATA_ROOT``.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

_REAL_LEGAL_DATA_ROOT = (Path(__file__).resolve().parent / "legal_data").resolve()


@pytest.fixture(autouse=True)
def _isolate_media_root(tmp_path, settings):
    """Redirect ``settings.MEDIA_ROOT`` to a per-test tmp dir.

    Sibling guard to ``_isolate_legal_data_root``. Several tests create a
    ``LegalSourceAttachment`` with a real ``SimpleUploadedFile``; without this
    isolation Django's ``FileSystemStorage`` writes the bytes straight into the
    repo's ``media/legal_sources/<pk>/`` tree and, because the storage appends a
    random suffix on every collision, the files accumulate unbounded across runs
    (the bug that left ~28k orphan PDFs / 54 MB on disk). Pointing ``MEDIA_ROOT``
    at ``tmp_path`` keeps every test upload disposable and out of the repo. The
    8 real DB-referenced attachments under the repo ``media/`` are untouched
    because no test reads them — uploads are always self-seeded.
    """
    isolated_media = tmp_path / "media_isolated"
    isolated_media.mkdir(parents=True, exist_ok=True)
    settings.MEDIA_ROOT = str(isolated_media)
    yield isolated_media
    shutil.rmtree(isolated_media, ignore_errors=True)


@pytest.fixture(autouse=True)
def _isolate_legal_data_root(tmp_path, settings):
    """Redirect ``settings.LEGAL_DATA_ROOT`` to a per-test tmp dir.

    The dir is seeded with a copy of the existing ``legal_data``
    structure (directories only, no files) so that tests which
    expect the per-country folder layout can write into the right
    sub-paths without crashing on a missing parent.

    We deliberately do NOT copy the file contents over: tests that
    need a real source must seed it themselves into ``tmp_path``,
    making the dependency explicit.
    """
    isolated_root = tmp_path / "legal_data_isolated"
    isolated_root.mkdir(parents=True, exist_ok=True)
    # Mirror the directory tree (folders only) so commands that
    # ``mkdir(parents=True, exist_ok=True)`` find a familiar shape.
    if _REAL_LEGAL_DATA_ROOT.is_dir():
        for src_dir in _REAL_LEGAL_DATA_ROOT.rglob("*"):
            if src_dir.is_dir():
                rel = src_dir.relative_to(_REAL_LEGAL_DATA_ROOT)
                (isolated_root / rel).mkdir(parents=True, exist_ok=True)
    settings.LEGAL_DATA_ROOT = str(isolated_root)
    yield isolated_root
    # tmp_path cleanup is handled by pytest. Defensive guard: never
    # let a test leave bytes inside the real legal_data tree.
    shutil.rmtree(isolated_root, ignore_errors=True)
