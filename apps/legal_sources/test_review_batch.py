"""D3: tests for the read-only Studio review batch workflow.

Asserts the batch is leak-safe, read-only, fail-closed, includes a manual (never
parsed) decision template, and keeps FR/BE/MA/TN not calculation-ready.
"""

from __future__ import annotations

import re
from datetime import date
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalReview, LegalSource, LegalSourceAttachment
from apps.legal_sources.review_batch import (
    DECISION_TEMPLATE,
    build_review_batch,
    render_review_batch_json,
    render_review_batch_markdown,
)

# Forbidden in any batch output (full hash, absolute path, email, raw markers).
_FORBIDDEN = [
    "legal_data/",
    ".env",
    "review_readiness",
    "review_evidence",
    "official_source_validation",
    "content_hash",
    "C:\\",
    "/home/",
    "reviewer=",
]
_HEX40 = re.compile(r"\b[0-9a-f]{40,}\b")
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _source(slug, cc="FR", *, status=SourceStatus.NEEDS_REVIEW):
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
        status=status,
        publication_date=date(2025, 1, 1),
        effective_date=date(2025, 1, 1),
    )


def _attach(src):
    return LegalSourceAttachment.objects.create(
        source=src,
        file=SimpleUploadedFile(f"{src.slug}.pdf", b"%PDF-1.4 test"),
        original_filename=f"{src.slug}.pdf",
        mime_type="application/pdf",
        size_bytes=12,
    )


# --------------------------------------------------------------------------- #
# builder
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_fr_batch_has_blocked_sources_not_calculation_ready():
    _source("fr-b1", "FR")
    _source("fr-b2", "FR")
    batch = build_review_batch(country="FR")
    assert batch["totals"]["items"] >= 2
    assert all(it["calculation_ready"] is False for it in batch["items"])
    # each item carries the manual decision template (a placeholder, not a decision)
    assert all(it["decision_template"] == list(DECISION_TEMPLATE) for it in batch["items"])


@pytest.mark.django_db
def test_all_summary_counts():
    _source("fr-s", "FR")
    _source("be-s", "BE")
    batch = build_review_batch(country=None)
    assert batch["totals"]["items"] >= 2
    assert "FR" in batch["summaries"] and "BE" in batch["summaries"]


@pytest.mark.django_db
def test_include_ready_excluded_by_default():
    # default include_ready=False, include_blocked=True -> only blocked sources
    _source("fr-only", "FR")
    batch = build_review_batch(country="FR")
    assert all(it["calculation_ready"] is False for it in batch["items"])


@pytest.mark.django_db
def test_limit_truncates():
    for i in range(4):
        _source(f"fr-l{i}", "FR")
    batch = build_review_batch(country="FR", limit=2)
    assert batch["totals"]["items"] == 2
    assert batch["totals"]["truncated"] is True
    assert batch["totals"]["matched_before_limit"] >= 4


# --------------------------------------------------------------------------- #
# leak safety
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_batch_output_is_leak_safe():
    src = _source("fr-leak", "FR")
    _attach(src)  # gives a real sha256 on the attachment
    LegalReview.objects.create(
        source=src,
        reviewer=get_user_model().objects.create_user("rev", "rev@x.it", "x", is_staff=True),
        decision="request_changes",
        comment="internal sensitive note must not leak",
    )
    batch = build_review_batch(country="FR", include_ready=True)
    for rendered in (render_review_batch_json(batch), render_review_batch_markdown(batch)):
        for tok in _FORBIDDEN:
            assert tok not in rendered, f"leak {tok!r}"
        assert not _HEX40.search(rendered), "full hash leaked"
        assert not _EMAIL.search(rendered), "email leaked"
        assert "internal sensitive note" not in rendered, "review note leaked"


# --------------------------------------------------------------------------- #
# command: read-only, fail-closed
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_command_is_read_only():
    _source("fr-ro", "FR")
    before = (LegalSource.objects.count(), LegalReview.objects.count())
    call_command(
        "prepare_studio_review_batch", "--country", "FR", "--format", "json", stdout=StringIO()
    )
    after = (LegalSource.objects.count(), LegalReview.objects.count())
    assert before == after


@pytest.mark.django_db
def test_command_does_not_create_legalreview_from_template():
    _source("fr-tpl", "FR")
    before = LegalReview.objects.count()
    out = StringIO()
    call_command("prepare_studio_review_batch", "--country", "FR", stdout=out)
    assert LegalReview.objects.count() == before
    # the markdown carries the unparsed decision template + the no-activation note
    assert "[ ] Approve for dataset seed review" in out.getvalue()
    assert "Do not use this batch for automatic calculation activation" in out.getvalue()


@pytest.mark.django_db
def test_command_fail_if_empty():
    # no sources for ZZ -> empty -> guard fails
    with pytest.raises(CommandError):
        call_command(
            "prepare_studio_review_batch", "--country", "ZZ", "--fail-if-empty", stdout=StringIO()
        )


@pytest.mark.django_db
def test_command_fail_closed_guards_pass_on_clean_data():
    _source("fr-clean", "FR")
    call_command(
        "prepare_studio_review_batch",
        "--country",
        "ALL",
        "--fail-if-calculation-ready-without-review",
        "--fail-if-approved-without-source-version",
        stdout=StringIO(),
    )  # must not raise


@pytest.mark.django_db
@pytest.mark.parametrize("cc", ["FR", "BE", "MA", "TN"])
def test_non_italian_items_never_calculation_ready(cc):
    _source(f"{cc.lower()}-x", cc, status=SourceStatus.APPROVED)
    batch = build_review_batch(country=cc, include_ready=True)
    assert all(it["calculation_ready"] is False for it in batch["items"])


# --------------------------------------------------------------------------- #
# admin action read-only
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_admin_batch_action_is_read_only():
    from django.contrib.admin.sites import AdminSite
    from django.test import RequestFactory

    from apps.legal_sources.admin import LegalSourceAdmin

    src = _source("fr-admin", "FR")
    before = (LegalSource.objects.count(), LegalReview.objects.count())
    ma = LegalSourceAdmin(LegalSource, AdminSite())
    req = RequestFactory().get("/admin/legal_sources/legalsource/")
    req.user = get_user_model().objects.create_superuser("admin_d3", "a@x.it", "x")
    # message framework needs a session/messages; use a stub
    req._messages = type("M", (), {"add": lambda *a, **k: None})()
    ma.show_studio_review_batch_summary_action(req, LegalSource.objects.filter(pk=src.pk))
    assert (LegalSource.objects.count(), LegalReview.objects.count()) == before
