"""D6: tests for the verified disk evidence bridge.

Uses a TEMP legal_data_root (never the real legal_data/) so it is deterministic
in CI. Proves the conservative bar: a registry candidate with a validated
official_downloaded file whose hash matches the validation marker is recognised;
a failed/absent marker, a missing file, or a hash mismatch are rejected. No DB
write, leak-safe, FR/BE/MA/TN stay not calculation-ready.
"""

from __future__ import annotations

import json
import re
from datetime import date
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.attachment_alignment import classify_attachment_gap
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalReview, LegalSource, LegalSourceAttachment
from apps.legal_sources.review_decision_guard import evaluate_legal_review_decision
from apps.legal_sources.utils import compute_bytes_sha256
from apps.legal_sources.verified_disk_evidence import (
    KIND_VERIFIED_DISK,
    evaluate_verified_disk_evidence,
)

# A real registry candidate slug (BE folder = belgium, expected_format html).
REGISTRY_SLUG = "be-loi-1989-11-21-rc-auto"
BE_FOLDER = "belgium"


def _source(slug, cc="BE", *, notes=""):
    country, _ = Country.objects.get_or_create(
        code=cc, defaults={"code_alpha3": cc + "X", "name": cc}
    )
    lang, _ = Language.objects.get_or_create(code="it", defaults={"name": "Italiano"})
    juris, _ = Jurisdiction.objects.get_or_create(
        country=country,
        code=f"{cc}-NATIONAL",
        defaults={"name": cc, "legal_system": Jurisdiction.LegalSystem.CIVIL_LAW},
    )
    return LegalSource.objects.create(
        slug=slug,
        title=f"Source {slug}",
        country=country,
        jurisdiction=juris,
        language=lang,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 1, 1),
        effective_date=date(2025, 1, 1),
        notes=notes,
    )


def _approve(src):
    LegalReview.objects.create(
        source=src,
        reviewer=get_user_model().objects.create_user(
            f"r-{src.pk}"[:30], f"{src.pk}@x.it", "x", is_staff=True
        ),
        decision="approve",
    )


def _write_official_file(root, slug, payload: bytes, folder=BE_FOLDER, ext="html"):
    d = root / "sources" / folder / "official_downloaded"
    d.mkdir(parents=True, exist_ok=True)
    f = d / f"{slug}.{ext}"
    f.write_bytes(payload)
    return f


def _validation_notes(sha256: str, *, status="passed") -> str:
    block = json.dumps(
        {"validation_status": status, "sha256": sha256, "official_source_verified": True}
    )
    return f"[official_source_validation] BEGIN\n{block}\n[official_source_validation] END"


# --------------------------------------------------------------------------- #
# the conservative bar
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_verified_when_file_passed_and_hash_matches(tmp_path):
    payload = b"<html>official 21 novembre 1989</html>"
    sha = compute_bytes_sha256(payload)
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes(sha))
    _write_official_file(tmp_path, REGISTRY_SLUG, payload)
    r = evaluate_verified_disk_evidence(src, legal_data_root=tmp_path)
    assert r.has_verified_disk_evidence is True
    assert r.evidence_kind == KIND_VERIFIED_DISK
    assert r.safe_relative_path.startswith("sources/belgium/official_downloaded/")


@pytest.mark.django_db
def test_rejected_when_validation_failed(tmp_path):
    payload = b"<html>x</html>"
    sha = compute_bytes_sha256(payload)
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes(sha, status="failed"))
    _write_official_file(tmp_path, REGISTRY_SLUG, payload)
    r = evaluate_verified_disk_evidence(src, legal_data_root=tmp_path)
    assert r.has_verified_disk_evidence is False
    assert any("not 'passed'" in b for b in r.blocking_reasons)


@pytest.mark.django_db
def test_rejected_when_file_absent(tmp_path):
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes("deadbeef"))
    r = evaluate_verified_disk_evidence(src, legal_data_root=tmp_path)
    assert r.has_verified_disk_evidence is False
    assert any("no official_downloaded file" in b for b in r.blocking_reasons)


@pytest.mark.django_db
def test_rejected_when_hash_mismatch(tmp_path):
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes("0" * 64))
    _write_official_file(tmp_path, REGISTRY_SLUG, b"<html>different bytes</html>")
    r = evaluate_verified_disk_evidence(src, legal_data_root=tmp_path)
    assert r.has_verified_disk_evidence is False
    assert any("does not match" in b for b in r.blocking_reasons)


@pytest.mark.django_db
def test_rejected_when_not_registry_candidate(tmp_path):
    payload = b"<html>x</html>"
    sha = compute_bytes_sha256(payload)
    src = _source("fr-not-in-registry-zzz", "FR", notes=_validation_notes(sha))
    r = evaluate_verified_disk_evidence(src, legal_data_root=tmp_path)
    assert r.has_verified_disk_evidence is False
    assert any("not a registry candidate" in b for b in r.blocking_reasons)


@pytest.mark.django_db
def test_attachment_row_is_primary_evidence(tmp_path):
    src = _source(REGISTRY_SLUG, "BE")
    LegalSourceAttachment.objects.create(
        source=src,
        file=__import__(
            "django.core.files.uploadedfile", fromlist=["SimpleUploadedFile"]
        ).SimpleUploadedFile("f.pdf", b"%PDF-1.4 x"),
        original_filename="f.pdf",
        mime_type="application/pdf",
        size_bytes=9,
    )
    r = evaluate_verified_disk_evidence(src, legal_data_root=tmp_path)
    assert r.has_verified_disk_evidence is True
    assert r.evidence_kind == "legal_source_attachment"


# --------------------------------------------------------------------------- #
# integration: D5 alignment + D4 guard
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_alignment_classifies_verified_disk_as_ok(tmp_path, monkeypatch):
    payload = b"<html>official</html>"
    sha = compute_bytes_sha256(payload)
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes(sha))
    _write_official_file(tmp_path, REGISTRY_SLUG, payload)
    _approve(src)
    monkeypatch.setattr("django.conf.settings.LEGAL_DATA_ROOT", tmp_path)
    item = classify_attachment_gap(src)
    assert item.classification == "ok_verified_disk_evidence"
    assert item.strict_validator_impact == "none"
    assert item.evidence_kind == "verified_official_downloaded_file"


@pytest.mark.django_db
def test_guard_allows_approve_with_verified_disk_evidence(tmp_path, monkeypatch):
    payload = b"<html>official</html>"
    sha = compute_bytes_sha256(payload)
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes(sha))
    _write_official_file(tmp_path, REGISTRY_SLUG, payload)
    monkeypatch.setattr("django.conf.settings.LEGAL_DATA_ROOT", tmp_path)
    res = evaluate_legal_review_decision(src, "approve")
    assert res.allowed is True
    assert res.severity != "blocking"
    assert res.calculation_activation_allowed is False


@pytest.mark.django_db
def test_guard_blocks_approve_without_any_evidence(tmp_path, monkeypatch):
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes("0" * 64))
    monkeypatch.setattr("django.conf.settings.LEGAL_DATA_ROOT", tmp_path)  # no file
    res = evaluate_legal_review_decision(src, "approve")
    assert res.allowed is False
    assert res.severity == "blocking"


# --------------------------------------------------------------------------- #
# safety: leak-safe, read-only, no activation
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_no_full_hash_or_abs_path_leaked(tmp_path, monkeypatch):
    payload = b"<html>official</html>"
    sha = compute_bytes_sha256(payload)
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes(sha))
    _write_official_file(tmp_path, REGISTRY_SLUG, payload)
    _approve(src)
    monkeypatch.setattr("django.conf.settings.LEGAL_DATA_ROOT", tmp_path)
    out = StringIO()
    call_command(
        "audit_legacy_attachment_alignment",
        "--country",
        "BE",
        "--include-ok",
        "--format",
        "json",
        stdout=out,
    )
    body = out.getvalue()
    assert sha not in body  # never the full hash
    assert not re.search(r"[0-9a-f]{40,}", body)
    assert str(tmp_path) not in body  # never the absolute path
    assert "official" not in body or "official_downloaded" in body  # no raw content tokens


@pytest.mark.django_db
def test_evaluation_writes_no_db(tmp_path, monkeypatch):
    payload = b"<html>official</html>"
    sha = compute_bytes_sha256(payload)
    src = _source(REGISTRY_SLUG, "BE", notes=_validation_notes(sha))
    _write_official_file(tmp_path, REGISTRY_SLUG, payload)
    before = (LegalSourceAttachment.objects.count(), LegalReview.objects.count())
    evaluate_verified_disk_evidence(src, legal_data_root=tmp_path)
    assert (LegalSourceAttachment.objects.count(), LegalReview.objects.count()) == before
