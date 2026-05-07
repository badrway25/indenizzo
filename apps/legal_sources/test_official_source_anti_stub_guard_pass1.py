"""Tests F-tunisia-official-source-real-files-restore-pass1 — anti-stub guards.

Background: a previous test run wrote 47-byte / 210-byte / 467-byte
HTML stubs over the real Tunisia / EU sources in
``legal_data/sources/**/official_downloaded/`` and the prior
validation pass blessed them as ``passed``. This iter restored the
real files and now installs durable guards so:

1. No file under ``legal_data/sources/**/official_downloaded/`` whose
   ``[official_sync]`` notes block (or sync manifest) claims
   ``classification=fetch_success`` may be tiny enough to be a stub
   (size ≤ 1024 bytes).
2. The sync manifest in each ``official_downloaded/`` directory must
   stay coherent with the local files: every ``fetch_success`` entry
   points at a file that exists and has the recorded sha + size.
3. ``LegalSource.notes`` ``[official_source_validation]`` blocks
   that claim ``validation_status=passed`` must be backed by a file
   whose recomputed sha matches the validation block's ``sha256``.
4. Regression test: the three slugs targeted by this iter
   (``tn-code-statut-personnel-livre-ix-succession``,
   ``tn-code-dip-loi-98-97``,
   ``eu-regulation-650-2012-successions``) carry the expected
   real-or-blocked state.

These guards are pure file/system inspections — they don't promote,
demote, fetch or write anything. They run against the real
``legal_data`` tree (the autouse conftest fixture redirects writes
but the read paths intentionally see the production tree for these
audit-style checks).
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SOURCES_ROOT = REPO_ROOT / "legal_data" / "sources"

# Anything ≤ this size is considered a stub when the manifest claims
# ``fetch_success``. The smallest legitimate official document we
# track today is 5+ KB; the historical stubs were 47–467 bytes.
STUB_SIZE_THRESHOLD_BYTES = 1024


def _iter_official_manifests() -> list[Path]:
    return sorted(SOURCES_ROOT.glob("**/official_downloaded/official_sync_manifest.json"))


def _read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# 1 — every fetch_success manifest entry points at a file > 1 KB
# ---------------------------------------------------------------------------


def test_no_fetch_success_manifest_entry_points_at_stub():
    """Every manifest result with ``classification=fetch_success`` must
    reference a local file larger than the stub threshold. A small
    file under that classification means a test or stub overwrote
    the real document.
    """
    offenders: list[str] = []
    for manifest_path in _iter_official_manifests():
        data = _read_manifest(manifest_path)
        for result in data.get("results", []):
            if result.get("classification") != "fetch_success":
                continue
            local_rel = result.get("local_path", "")
            if not local_rel:
                offenders.append(
                    f"{manifest_path.name}::{result.get('slug')!r} fetch_success "
                    "but local_path is empty"
                )
                continue
            local_abs = REPO_ROOT / Path(local_rel.replace("\\", "/"))
            if not local_abs.is_file():
                offenders.append(
                    f"{manifest_path.name}::{result.get('slug')!r} fetch_success "
                    f"but file missing: {local_rel}"
                )
                continue
            size = local_abs.stat().st_size
            if size <= STUB_SIZE_THRESHOLD_BYTES:
                offenders.append(
                    f"{manifest_path.name}::{result.get('slug')!r} fetch_success "
                    f"but file is suspiciously small ({size}B ≤ "
                    f"{STUB_SIZE_THRESHOLD_BYTES}B): {local_rel}"
                )
    assert not offenders, "stub-sized files declared as fetch_success:\n  " + "\n  ".join(offenders)


# ---------------------------------------------------------------------------
# 2 — every fetch_success manifest entry's recorded sha matches the file
# ---------------------------------------------------------------------------


def test_fetch_success_manifest_sha_matches_file_on_disk():
    """For every ``fetch_success`` entry, the sha256 in the manifest
    must match the recomputed sha of the file on disk. Drift means
    the file was overwritten without re-syncing the manifest.
    """
    offenders: list[str] = []
    for manifest_path in _iter_official_manifests():
        data = _read_manifest(manifest_path)
        for result in data.get("results", []):
            if result.get("classification") != "fetch_success":
                continue
            local_rel = result.get("local_path", "")
            recorded_sha = result.get("sha256") or ""
            recorded_size = result.get("size_bytes")
            if not local_rel or not recorded_sha:
                continue
            local_abs = REPO_ROOT / Path(local_rel.replace("\\", "/"))
            if not local_abs.is_file():
                offenders.append(
                    f"{manifest_path.name}::{result.get('slug')!r} fetch_success "
                    f"but file missing: {local_rel}"
                )
                continue
            raw = local_abs.read_bytes()
            current_sha = hashlib.sha256(raw).hexdigest()
            if current_sha != recorded_sha:
                offenders.append(
                    f"{manifest_path.name}::{result.get('slug')!r} sha drift: "
                    f"manifest={recorded_sha[:16]} disk={current_sha[:16]}"
                )
                continue
            if recorded_size is not None and len(raw) != recorded_size:
                offenders.append(
                    f"{manifest_path.name}::{result.get('slug')!r} size drift: "
                    f"manifest={recorded_size} disk={len(raw)}"
                )
    assert not offenders, "manifest/disk drift on fetch_success entries:\n  " + "\n  ".join(
        offenders
    )


# ---------------------------------------------------------------------------
# 3 — committed [official_source_validation] passed blocks must hash-match
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_validation_passed_blocks_hash_match_local_files():
    """``LegalSource.notes`` carries a ``[official_source_validation]``
    block. When it says ``validation_status=passed`` and references a
    local_path, the recomputed sha of that file must match the block's
    sha256 — otherwise we have a stub blessed as valid (the bug this
    iter fixed for the TN slugs).
    """
    from apps.legal_sources.models import LegalSource

    pat = re.compile(
        r"\[official_source_validation\] BEGIN\s*(\{.*?\})\s*\[official_source_validation\] END",
        re.DOTALL,
    )
    offenders: list[str] = []
    for ls in LegalSource.objects.exclude(notes=""):
        notes = ls.notes or ""
        m = pat.search(notes)
        if not m:
            continue
        try:
            block = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if block.get("validation_status") != "passed":
            continue
        local_rel = block.get("local_path") or ""
        recorded_sha = block.get("sha256") or ""
        if not local_rel or not recorded_sha:
            continue
        local_abs = REPO_ROOT / Path(local_rel.replace("\\", "/"))
        if not local_abs.is_file():
            offenders.append(f"{ls.slug!r} passed but file missing: {local_rel}")
            continue
        current_sha = hashlib.sha256(local_abs.read_bytes()).hexdigest()
        if current_sha != recorded_sha:
            offenders.append(
                f"{ls.slug!r} passed sha mismatch: "
                f"validation={recorded_sha[:16]} disk={current_sha[:16]}"
            )
    assert not offenders, "validation 'passed' rows without matching disk sha:\n  " + "\n  ".join(
        offenders
    )


# ---------------------------------------------------------------------------
# 4 — regression: TN sources are real (>= 5 KB), EU is blocked
# ---------------------------------------------------------------------------


def test_tn_csp_livre_ix_is_real_file_after_pass1():
    """Restored by F-tunisia-official-source-real-files-restore-pass1.

    The historical (2026-05-03) sync recorded sha
    ``ab8078968ccfa07e…`` and 36 183 bytes. This test pins the
    contract: the real file must come back to that exact state.
    """
    p = (
        SOURCES_ROOT
        / "tunisia"
        / "official_downloaded"
        / ("tn-code-statut-personnel-livre-ix-succession.html")
    )
    assert p.is_file()
    raw = p.read_bytes()
    assert len(raw) == 36183, f"unexpected size {len(raw)}"
    assert hashlib.sha256(raw).hexdigest() == (
        "ab8078968ccfa07eaefc34bb38a1ec49071d000dfe0ffd85b1410d343a348ffd"
    )
    # The body must mention the CSP / Code du statut personnel hook.
    body = raw.decode("utf-8", errors="replace")
    assert "Code du statut personnel" in body or "statut personnel" in body.lower()


def test_tn_dip_loi_98_97_is_real_file_after_pass1():
    p = SOURCES_ROOT / "tunisia" / "official_downloaded" / "tn-code-dip-loi-98-97.html"
    assert p.is_file()
    raw = p.read_bytes()
    assert len(raw) == 15424, f"unexpected size {len(raw)}"
    assert hashlib.sha256(raw).hexdigest() == (
        "d379a07076177f66cf0fc6ad4704b78dd8c7b79acef03954c598a5218eb8e76a"
    )
    body = raw.decode("utf-8", errors="replace")
    # The Code DIP page (TITRE II) doesn't restate the loi number in
    # its body; it's primarily the article text on jurisdiction. We
    # anchor on the Code title plus the structural TITRE marker.
    assert "Code de Droit International" in body
    assert "TITRE II" in body


def test_eu_650_remains_blocked_pending_eurlex_async_fetch():
    """EUR-Lex returns HTTP 202 + empty body for synchronous fetches —
    its content-delivery is asynchronous and our urllib path can't
    follow it. The manifest must keep the EU 650 entry classified
    as ``fetch_failed`` so this fact is explicit. A real download
    will require a manual or session-aware fetch.
    """
    manifest_path = SOURCES_ROOT / "eu" / "official_downloaded" / "official_sync_manifest.json"
    data = _read_manifest(manifest_path)
    eu_entry = next(r for r in data["results"] if r["slug"] == "eu-regulation-650-2012-successions")
    assert eu_entry["classification"] == "fetch_failed", (
        f"EU 650 must remain explicitly classified as fetch_failed until a "
        f"real download succeeds; got {eu_entry['classification']!r}"
    )
    # And the local file (if any) must be flagged: it's still a stub.
    p = SOURCES_ROOT / "eu" / "official_downloaded" / "eu-regulation-650-2012-successions.html"
    if p.is_file():
        assert p.stat().st_size <= STUB_SIZE_THRESHOLD_BYTES, (
            "EU 650 file is larger than the stub threshold but the manifest "
            "still says fetch_failed — sync the manifest or remove the file."
        )


# ---------------------------------------------------------------------------
# 5 — TN public funnel still unavailable (no mapping created in pass1)
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_tn_public_funnel_still_unavailable_after_pass1(db):
    """Pass1 restored the real source files but did NOT create a TN
    mapping draft. The TN public funnel must still produce
    ``unavailable_requires_legal_validation``.
    """
    from django.test import Client
    from django.urls import reverse

    from apps.calculators.enums import CalculationStatus
    from apps.cases.models import Simulation
    from apps.jurisdictions.models import Country, Currency, Jurisdiction

    Country.objects.create(code="TN", code_alpha3="TUN", name="Tunisie")
    if not Currency.objects.filter(code="EUR").exists():
        Currency.objects.create(code="EUR", name="Euro", symbol="€")
    Jurisdiction.objects.create(
        country=Country.objects.get(code="TN"),
        code="TN-NATIONAL",
        name="Tunisie",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    response = Client().post(
        reverse("cases:wizard_tunisia_inheritance"),
        data={
            "deceased_country_of_last_residence": "TN",
            "nationality": "TN",
            "spouse_present": "on",
            "surviving_spouse_gender": "wife",
            "sons_count": "1",
            "daughters_count": "1",
            "estate_value": "500000",
            "consent_simulation": "on",
            "website": "",
        },
        follow=True,
    )
    assert response.status_code == 200
    sim = Simulation.objects.order_by("-id").first()
    assert sim is not None
    assert sim.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value


# ---------------------------------------------------------------------------
# 6 — no Tunisia mapping draft was created by this iter
# ---------------------------------------------------------------------------


def test_no_tunisia_inheritance_mapping_draft_created_in_pass1():
    """F-tunisia-official-source-real-files-restore-pass1 is purely a
    source-restoration iter. The Tunisia mapping draft is out of
    scope and must not exist on disk.
    """
    p = REPO_ROOT / "legal_data" / "mappings" / "tunisia_inheritance_mapping_draft.json"
    assert not p.exists(), (
        "tunisia_inheritance_mapping_draft.json must not be created by "
        "this iter; the brief explicitly forbids it"
    )
