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
    # Manual-required items skip fetch but still create a LegalSource.
    for item in cmd.FRANCE_PACKAGE:
        if item.get("manual_download_required"):
            continue
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
    # Notes flag the manual review requirement (both auto and manual paths).
    for src in fr_sources:
        assert "Studio legal review" in src.notes


@pytest.mark.django_db
def test_country_fr_writes_manifest(tmp_legal_data, fake_fetch):
    auto_items = [i for i in cmd.FRANCE_PACKAGE if not i.get("manual_download_required")]
    manual_items = [i for i in cmd.FRANCE_PACKAGE if i.get("manual_download_required")]
    for item in auto_items:
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
    assert data["succeeded"] == len(auto_items)
    assert data["failed"] == 0
    assert data["manual_required"] == len(manual_items)
    # Auto-fetched entries have sha256 + size + http_status; manual ones don't.
    for entry in data["items"]:
        assert entry["status"] == SourceStatus.NEEDS_REVIEW
        if entry["manual_download_required"]:
            assert entry["sha256"] == ""
            assert entry["size_bytes"] == 0
            assert entry["http_status"] is None
            assert entry["classification"] == "MANUAL_DOWNLOAD_REQUIRED"
        else:
            assert entry["sha256"]
            assert entry["size_bytes"] > 0
            assert entry["http_status"] == 200
            assert entry["classification"]


@pytest.mark.django_db
def test_pdf_payload_creates_attachment(tmp_legal_data, fake_fetch):
    """Check on the full FRANCE batch: PDF items get an Attachment."""
    # Pick the first non-manual item: the manual path never produces an attachment.
    pdf_item = next(i for i in cmd.FRANCE_PACKAGE if not i.get("manual_download_required"))
    for item in cmd.FRANCE_PACKAGE:
        if item.get("manual_download_required"):
            continue
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
    html_item = next(
        i
        for i in cmd.FRANCE_PACKAGE
        if not i.get("manual_download_required") and "nomenclature" in i["slug"]
    )
    for item in cmd.FRANCE_PACKAGE:
        if item.get("manual_download_required"):
            continue
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
    auto_items = [i for i in package if not i.get("manual_download_required")]
    manual_items = [i for i in package if i.get("manual_download_required")]
    # Pick the first auto item to fail; the rest succeed.
    failing_item = auto_items[0]
    fake_fetch["failures"][failing_item["url"]] = "Test connection refused"
    for item in auto_items[1:]:
        fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    call_command("download_international_legal_sources", "--country", "FR", stdout=StringIO())

    # Successful auto items + manual items got a LegalSource; only the failed
    # auto item is missing from DB but present in manifest with `error` set.
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
    assert data["succeeded"] == len(auto_items) - 1
    assert data["failed"] == 1
    assert data["manual_required"] == len(manual_items)
    failed_entry = next(e for e in data["items"] if e["error"])
    assert failed_entry["slug"] == failing_item["slug"]
    assert "fetch_failed" in failed_entry["error"]
    assert failed_entry["classification"] == "FAILED_NEEDS_REPLACEMENT_URL"


# ---------------------------------------------------------------------------
# --all covers 4 packages
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_all_flag_covers_all_four_countries(tmp_legal_data, fake_fetch):
    for _code, package in cmd.PACKAGES.items():
        for item in package:
            if item.get("manual_download_required"):
                continue
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
    # Use a non-manual item so the fetch path is exercised on both runs.
    item = next(i for i in cmd.FRANCE_PACKAGE if not i.get("manual_download_required"))
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
            if item.get("manual_download_required"):
                continue
            fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    pre_count = CompensationDataset.objects.count()
    call_command("download_international_legal_sources", "--all", stdout=StringIO())
    assert CompensationDataset.objects.count() == pre_count


@pytest.mark.django_db
def test_no_attachment_for_html_even_in_full_run(tmp_legal_data, fake_fetch):
    """End-to-end: HTML pages never become Attachments; PDFs do."""
    for _code, package in cmd.PACKAGES.items():
        for item in package:
            if item.get("manual_download_required"):
                continue
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


# ---------------------------------------------------------------------------
# URL-triage iter2 — package shape, manual-required path, classification.
# ---------------------------------------------------------------------------


def test_packages_no_longer_contain_removed_slugs():
    """The triage removed two duplicate-redundant slugs from MA and TN."""
    ma_slugs = {item["slug"] for item in cmd.MOROCCO_PACKAGE}
    tn_slugs = {item["slug"] for item in cmd.TUNISIA_PACKAGE}
    assert "ma-code-famille-loi-70-03-dgct" not in ma_slugs
    assert "tn-code-dip-pdf-support" not in tn_slugs


def test_eur_lex_url_uses_html_endpoint_not_pdf():
    """Triage switched EUR-Lex from /TXT/PDF/ (202 async) to /TXT/ HTML."""
    eur_lex_slugs = (
        "eu-regulation-650-2012-successions-fr-ma",
        "eu-regulation-650-2012-successions-fr-tn",
    )
    found = []
    for package in cmd.PACKAGES.values():
        for item in package:
            if item["slug"] in eur_lex_slugs:
                found.append(item)
                assert "/TXT/?" in item["url"]
                assert "/TXT/PDF/" not in item["url"]
                assert "uri=CELEX:32012R0650" in item["url"]
    assert len(found) == 2


def test_eur_lex_items_are_manual_download_required():
    """Triage iter3: EUR-Lex returns 202 + empty body to programmatic UAs.

    Both endpoints are flagged `manual_download_required` so the command
    skips the fetch and the Studio attaches the official PDF/HTML manually.
    """
    eur_lex_slugs = (
        "eu-regulation-650-2012-successions-fr-ma",
        "eu-regulation-650-2012-successions-fr-tn",
    )
    found = []
    for package in cmd.PACKAGES.values():
        for item in package:
            if item["slug"] in eur_lex_slugs:
                found.append(item)
                assert item.get("manual_download_required") is True
                assert "EUR-Lex" in item.get("manual_reason", "")
                assert "HTTP 202" in item.get("manual_reason", "")
    assert len(found) == 2


@pytest.mark.django_db
def test_eur_lex_creates_legal_source_without_attachment(tmp_legal_data, fake_fetch, monkeypatch):
    """End-to-end: EUR-Lex items skip _fetch and produce no Attachment."""
    fetched_urls: list[str] = []

    def tracking_fetch(url, timeout=cmd.DOWNLOAD_TIMEOUT_SECONDS):
        fetched_urls.append(url)
        if url not in fake_fetch["table"]:
            import requests

            raise requests.HTTPError(f"unmocked URL: {url}")
        return fake_fetch["table"][url]

    monkeypatch.setattr(cmd, "_fetch", tracking_fetch)

    # Populate fakes only for non-manual items in MA + TN.
    for code in ("MA", "TN"):
        for item in cmd.PACKAGES[code]:
            if item.get("manual_download_required"):
                continue
            fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    call_command("download_international_legal_sources", "--country", "MA", stdout=StringIO())
    call_command("download_international_legal_sources", "--country", "TN", stdout=StringIO())

    eur_lex_url = "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650"
    assert eur_lex_url not in fetched_urls

    for slug in (
        "eu-regulation-650-2012-successions-fr-ma",
        "eu-regulation-650-2012-successions-fr-tn",
    ):
        src = LegalSource.objects.get(slug=slug)
        assert src.status == SourceStatus.NEEDS_REVIEW
        assert src.attachments.count() == 0
        assert "EUR-Lex" in src.notes


def test_manual_download_required_skips_fetch(tmp_legal_data, fake_fetch, monkeypatch):
    """Manual items must not call _fetch — the URL is unreachable from the datacenter."""
    fetched_urls: list[str] = []
    real_fake = fake_fetch  # noqa: F841 — keep monkeypatch fixture wired

    def tracking_fetch(url, timeout=cmd.DOWNLOAD_TIMEOUT_SECONDS):
        fetched_urls.append(url)
        # Reuse the table-based fake for non-manual items.
        if url not in fake_fetch["table"]:
            import requests

            raise requests.HTTPError(f"unmocked URL: {url}")
        return fake_fetch["table"][url]

    monkeypatch.setattr(cmd, "_fetch", tracking_fetch)

    # Populate fake responses only for non-manual TN items.
    for item in cmd.TUNISIA_PACKAGE:
        if item.get("manual_download_required"):
            continue
        fake_fetch["table"][item["url"]] = _ok_html(item["url"])

    call_command("download_international_legal_sources", "--country", "TN", stdout=StringIO())

    # No manual URL was passed to _fetch.
    manual_urls = {i["url"] for i in cmd.TUNISIA_PACKAGE if i.get("manual_download_required")}
    assert manual_urls, "test premise broken: TN should have at least one manual item"
    assert manual_urls.isdisjoint(set(fetched_urls))


@pytest.mark.django_db
def test_manual_download_required_creates_source_without_attachment(tmp_legal_data, fake_fetch):
    """Manual path creates a needs_review LegalSource and zero Attachments."""
    manual_item = next(i for i in cmd.TUNISIA_PACKAGE if i.get("manual_download_required"))
    # Populate non-manual TN URLs so the rest of the batch succeeds.
    for item in cmd.TUNISIA_PACKAGE:
        if item.get("manual_download_required"):
            continue
        fake_fetch["table"][item["url"]] = _ok_html(item["url"])

    call_command("download_international_legal_sources", "--country", "TN", stdout=StringIO())

    src = LegalSource.objects.get(slug=manual_item["slug"])
    assert src.status == SourceStatus.NEEDS_REVIEW
    assert src.attachments.count() == 0
    assert "Manual download required" in src.notes


@pytest.mark.django_db
def test_classification_field_in_manifest(tmp_legal_data, fake_fetch):
    """Manifest entries always carry a `classification` tag matching the path."""
    for item in cmd.TUNISIA_PACKAGE:
        if item.get("manual_download_required"):
            continue
        if item["slug"].startswith("eu-regulation"):
            fake_fetch["table"][item["url"]] = _ok_html(item["url"])
        else:
            fake_fetch["table"][item["url"]] = _ok_html(item["url"])

    call_command("download_international_legal_sources", "--country", "TN", stdout=StringIO())

    manifest_path = (
        Path(settings.BASE_DIR)
        / "legal_data"
        / "sources"
        / "tunisia"
        / "downloaded"
        / "download_manifest.json"
    )
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_slug = {e["slug"]: e for e in data["items"]}

    # Manual items get MANUAL_DOWNLOAD_REQUIRED.
    for item in cmd.TUNISIA_PACKAGE:
        if item.get("manual_download_required"):
            assert by_slug[item["slug"]]["classification"] == "MANUAL_DOWNLOAD_REQUIRED"

    # Non-manual HTML responses get HTML_OK_SOURCE_PAGE.
    for item in cmd.TUNISIA_PACKAGE:
        if item.get("manual_download_required"):
            continue
        assert by_slug[item["slug"]]["classification"] == "HTML_OK_SOURCE_PAGE"


@pytest.mark.django_db
def test_full_run_creates_no_legal_review_or_approved_source(tmp_legal_data, fake_fetch):
    """REGOLA ASSOLUTA — `--all` never approves or reviews sources."""
    from apps.legal_sources.models import LegalReview

    for _code, package in cmd.PACKAGES.items():
        for item in package:
            if item.get("manual_download_required"):
                continue
            fake_fetch["table"][item["url"]] = _ok_pdf(item["url"])

    call_command("download_international_legal_sources", "--all", stdout=StringIO())

    intl_codes = ("FR", "BE", "MA", "TN")
    intl_sources = LegalSource.objects.filter(country__code__in=intl_codes)
    assert intl_sources.exists()
    assert not intl_sources.filter(status=SourceStatus.APPROVED).exists()
    assert not LegalReview.objects.filter(source__country__code__in=intl_codes).exists()
