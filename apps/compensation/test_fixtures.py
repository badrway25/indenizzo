"""Test-only helpers for compensation datasets (H1-9).

These build SYNTHETIC, test-only legal data. They never touch real approved
sources and run only inside test transactions (rolled back). They exist so a
test can create an APPROVED ``CompensationDataset`` that satisfies the H1-9 DB
constraint (``approved`` => ``source_version`` NOT NULL) without inventing a
real official source — the source version is a clearly test-only marker.

NOTE: this module is intentionally NOT a ``test_*`` module, so pytest does not
collect it.
"""

from __future__ import annotations

from typing import Any


def approved_source_version(
    source: Any, *, label: str | None = None, content_hash: str = "test-only-source-hash"
) -> Any:
    """Create a test-only ``LegalSourceVersion`` for ``source``.

    Pass the returned object as ``source_version=`` when creating an APPROVED
    ``CompensationDataset`` so it satisfies the H1-9 constraint. The version
    label is auto-generated unique per source, so this is safe to call multiple
    times for the same source (e.g. a primary + range dataset).
    """
    from apps.legal_sources.models import LegalSourceVersion

    if label is None:
        label = f"TEST-V{source.versions.count() + 1}"
    return LegalSourceVersion.objects.create(
        source=source,
        version_label=label,
        content_hash=content_hash,
    )
