"""
Tests for download_international_legal_sources — fully mocked HTTP.

REGOLA D'ORO: nessuna chiamata di rete reale nei test. Il monkeypatch
sostituisce ``_fetch`` del command con un fake deterministico che
restituisce bytes finti. Verifichiamo:

- il manifest JSON viene scritto in legal_data/sources/<country>/downloaded/;
- ``LegalSource`` viene creata in stato ``needs_review``;
- nessuna fonte viene approvata, nessun ``CompensationDataset`` o
  ``CalculationFormula`` creato;
- un singolo URL fallito non interrompe il batch;
- ``--country`` filtra correttamente; ``--all`` copre 4 paesi;
- ``LegalSourceAttachment`` viene creato per i PDF (non per HTML);
- una fonte già ``approved`` non viene retrocessa.
"""

from __future__ import annotations

import json
import shutil
from io import StringIO
from pathlib import Path

import pytest
from django.conf import settings
from django.core.management import CommandError, call_command

from apps.compensation.models import CompensationDataset
from apps.legal_sources.enums import SourceStatus
from apps.legal_sources.management.commands import download_international_legal_sources as cmd
from apps.legal_sources.models import LegalSource, LegalSourceAttachment


@pytest.fixture
def tmp_legal_data(tmp_path, monkeypatch):
    """Redirect legal_data/ writes into a tmp folder so tests don't pollute repo."""
    fake_base = tmp_path / "fake_repo"
    fake_base.mkdir()
    monkeypatch.setattr(settings, "BASE_DIR", fake_base)
    yield fake_base
    if fake_base.exists():
        shutil.rmtree(fake_base, ignore_errors=True)


@pytest.fixture
def fake_fetch(monkeypatch):
    """Replace `_fetch` with a deterministic table indexed by URL.

    Each test populates the dict before invoking call_command. Missing
    URLs raise the same exception type the real ``requests`` would raise,
    so the command treats it as a fetch_failed entry in manifest.
    """
    import requests

    table: dict[str, cmd.FetchResult] = {}
    failures: dict[str, str] = {}

    def fake(url, timeout=cmd.DOWNLOAD_TIMEOUT_SECONDS):  # noqa: ARG001 - signature mirror
        if url in failures:
            raise requests.ConnectionError(failures[url])
        if url not in table:
            raise requests.HTTPError(f"unmocked URL: {url}")
        return table[url]

    monkeypatch.setattr(cmd, "_fetch", fake)
    return {"table": table, "failures": failures}


def _ok_pdf(url: str) -> cmd.FetchResult:
    # Fake "PDF" payload: real magic header + filler. Not a real PDF, but
    # the command treats it as bytes (no parsing).
    payload = b"%PDF-1.4\n% fake pdf for tests\n%%EOF\n"
    return cmd.FetchResult(
        final_url=url, http_status=200, content_type="application/pdf", payload=payload
    )


def _ok_html(url: str) -> cmd.FetchResult:
    payload = b"<!doctype html><html><head><title>test</title></head><body>x</body></html>"
    return cmd.FetchResult(
        final_url=url, http_status=200, content_type="text/html; charset=utf-8", payload=payload
    )


# ---------------------------------------------------------------------------
# CLI argument validation
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_command_requires_country_or_all():
    with pytest.raises(CommandError, match="--country .* or --all"):
        call_command("download_international_legal_sources")


@pytest.mark.django_db
def test_command_rejects_country_and_all_together():
    with pytest.raises(CommandError, match="mutually exclusive"):
        call_command("download_international_legal_sources", "--country", "FR", "--all")


# ---------------------------------------------------------------------------
# --country FR
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_country_fr_creates_legal_sources_in_needs_review(tmp_legal_data, fake_fetch):
    for item in cmd.FRANCE_PACKAGE:
        # 3 PDFs + 2 HTML pages.
        if "page" in item["slug"] or "nomenclature" in item["slug"]:
            fake_fetch["table"][item["url"]] = _ok_html(item["url"])
        else:
            fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    out = StringIO()
    call_command("download_international_legal_sources", "--country", "FR", stdout=out)

    fr_sources = LegalSource.objects.filter(country__code="FR")
    assert fr_sources.count() == len(cmd.FRANCE_PACKAGE)
    # All start in needs_review.
    assert not fr_sources.filter(status=SourceStatus.APPROVED).exists()
    assert fr_sources.filter(status=SourceStatus.NEEDS_REVIEW).count() == fr_sources.count()
    # Each has the source_url populated with the original URL.
    expected_urls = {item["url"] for item in cmd.FRANCE_PACKAGE}
    assert set(fr_sources.values_list("official_url", flat=True)) == expected_urls
    # Notes flag the manual review requirement.
    for src in fr_sources:
        assert "Studio legal review" in src.notes


@pytest.mark.django_db
def test_country_fr_writes_manifest(tmp_legal_data, fake_fetch):
    for item in cmd.FRANCE_PACKAGE:
        fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    call_command("download_international_legal_sources", "--country", "FR", stdout=StringIO())

    manifest_path = (
        Path(settings.BASE_DIR)
        / "legal_data"
        / "sources"
        / "france"
        / "downloaded"
        / "download_manifest.json"
    )
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["country"] == "FR"
    assert data["succeeded"] == len(cmd.FRANCE_PACKAGE)
    assert data["failed"] == 0
    # All entries have sha256 + size + http_status.
    for entry in data["items"]:
        assert entry["sha256"]
        assert entry["size_bytes"] > 0
        assert entry["http_status"] == 200
        assert entry["status"] == SourceStatus.NEEDS_REVIEW


@pytest.mark.django_db
def test_pdf_payload_creates_attachment(tmp_legal_data, fake_fetch):
    """Check on the full FRANCE batch: PDF items get an Attachment."""
    pdf_item = cmd.FRANCE_PACKAGE[0]  # Loi Badinter
    for item in cmd.FRANCE_PACKAGE:
        if item is pdf_item:
            fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])
        else:
            fake_fetch["table"][item["url"]] = _ok_html(item["url"])

    call_command("download_international_legal_sources", "--country", "FR", stdout=StringIO())

    src = LegalSource.objects.get(slug=pdf_item["slug"])
    assert src.attachments.count() == 1
    att = src.attachments.first()
    assert att.mime_type == "application/pdf"
    assert att.size_bytes > 0
    assert len(att.sha256) == 64


@pytest.mark.django_db
def test_html_payload_does_not_create_attachment(tmp_legal_data, fake_fetch):
    """Check on the full FRANCE batch: HTML items do NOT get an Attachment."""
    html_item = cmd.FRANCE_PACKAGE[1]  # nomenclature dintilhac
    for item in cmd.FRANCE_PACKAGE:
        if item is html_item:
            fake_fetch["table"][item["url"]] = _ok_html(item["url"])
        else:
            fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    call_command("download_international_legal_sources", "--country", "FR", stdout=StringIO())

    src = LegalSource.objects.get(slug=html_item["slug"])
    assert src.attachments.count() == 0


# ---------------------------------------------------------------------------
# Resilience: a single failed URL does NOT abort the batch.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_single_url_failure_does_not_abort_batch(tmp_legal_data, fake_fetch):
    package = cmd.FRANCE_PACKAGE
    # First item fails, all others succeed.
    fake_fetch["failures"][package[0]["url"]] = "Test connection refused"
    for item in package[1:]:
        fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    call_command("download_international_legal_sources", "--country", "FR", stdout=StringIO())

    # Only the successful items got a LegalSource — the failed item is in
    # the manifest with `error` set, but no DB row yet.
    fr_count = LegalSource.objects.filter(country__code="FR").count()
    assert fr_count == len(package) - 1

    manifest_path = (
        Path(settings.BASE_DIR)
        / "legal_data"
        / "sources"
        / "france"
        / "downloaded"
        / "download_manifest.json"
    )
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["succeeded"] == len(package) - 1
    assert data["failed"] == 1
    failed_entry = next(e for e in data["items"] if e["error"])
    assert failed_entry["slug"] == package[0]["slug"]
    assert "fetch_failed" in failed_entry["error"]


# ---------------------------------------------------------------------------
# --all covers 4 packages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_all_flag_covers_all_four_countries(tmp_legal_data, fake_fetch):
    for _code, package in cmd.PACKAGES.items():
        for item in package:
            fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    call_command("download_international_legal_sources", "--all", stdout=StringIO())

    for code in ("FR", "BE", "MA", "TN"):
        assert LegalSource.objects.filter(country__code=code).exists()
        manifest_path = (
            Path(settings.BASE_DIR)
            / "legal_data"
            / "sources"
            / cmd.COUNTRY_FOLDER_BY_CODE[code]
            / "downloaded"
            / "download_manifest.json"
        )
        assert manifest_path.exists()


# ---------------------------------------------------------------------------
# Idempotence: re-running NEVER downgrades an APPROVED source.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_re_run_does_not_downgrade_approved_source(tmp_legal_data, fake_fetch):
    item = cmd.FRANCE_PACKAGE[0]
    fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    # First run: creates source as needs_review.
    call_command("download_international_legal_sources", "--country", "FR", stdout=StringIO())
    src = LegalSource.objects.get(slug=item["slug"])
    assert src.status == SourceStatus.NEEDS_REVIEW

    # Studio promotes manually.
    src.status = SourceStatus.APPROVED
    src.save(update_fields=["status"])

    # Second run: must NOT downgrade the source.
    call_command("download_international_legal_sources", "--country", "FR", stdout=StringIO())
    src.refresh_from_db()
    assert src.status == SourceStatus.APPROVED


# ---------------------------------------------------------------------------
# REGOLA ASSOLUTA — no calculation artefacts created.
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_command_creates_no_compensation_dataset(tmp_legal_data, fake_fetch):
    for _code, package in cmd.PACKAGES.items():
        for item in package:
            fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    pre_count = CompensationDataset.objects.count()
    call_command("download_international_legal_sources", "--all", stdout=StringIO())
    assert CompensationDataset.objects.count() == pre_count


@pytest.mark.django_db
def test_no_attachment_for_html_even_in_full_run(tmp_legal_data, fake_fetch):
    """End-to-end: HTML pages never become Attachments; PDFs do."""
    for _code, package in cmd.PACKAGES.items():
        for item in package:
            if "page" in item["slug"] or "tableurs" in item["slug"]:
                fake_fetch["table"][item["url"]] = _ok_html(item["url"])
            else:
                fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    call_command("download_international_legal_sources", "--all", stdout=StringIO())

    # Each Attachment is bound to a slug whose payload was PDF.
    for att in LegalSourceAttachment.objects.select_related("source"):
        assert att.mime_type == "application/pdf"
        assert "page" not in att.source.slug
        assert "tableurs" not in att.source.slug
