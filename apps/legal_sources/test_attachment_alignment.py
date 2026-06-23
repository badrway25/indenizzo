"""D5: tests for the read-only legacy attachment-alignment audit.

Asserts the classification (missing attachment / version / manual-required / ok),
leak-safe output, read-only command, fail-closed guards, the validator hint, and
that the audit never attaches/approves/activates.
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

from apps.compensation.models import CompensationDataset
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.attachment_alignment import (
    build_legacy_attachment_alignment_report,
    classify_attachment_gap,
)
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import (
    LegalReview,
    LegalSource,
    LegalSourceAttachment,
    LegalSourceVersion,
)

# A real registry candidate slug (documented official source).
REGISTRY_SLUG = "be-loi-1989-11-21-rc-auto"


def _source(slug, cc="FR", *, status=SourceStatus.APPROVED):
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


def _approve(src):
    LegalReview.objects.create(
        source=src,
        reviewer=get_user_model().objects.create_user(
            f"r-{src.slug}"[:30], f"{src.pk}@x.it", "x", is_staff=True
        ),
        decision="approve",
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
# classification
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_legacy_approve_no_attachment_registry_candidate():
    src = _source(REGISTRY_SLUG, "BE")
    _approve(src)
    item = classify_attachment_gap(src)
    assert item.classification == "missing_attachment_row"
    assert item.strict_validator_impact == "blocking"
    assert item.in_registry is True


@pytest.mark.django_db
def test_legacy_approve_no_attachment_not_registry_is_manual_required():
    src = _source("fr-not-in-registry-xyz", "FR")
    _approve(src)
    item = classify_attachment_gap(src)
    assert item.classification == "manual_review_required"
    assert item.strict_validator_impact == "blocking"


@pytest.mark.django_db
def test_approve_with_attachment_no_version_is_warning():
    src = _source("fr-nv", "FR")
    _attach(src)
    _approve(src)
    item = classify_attachment_gap(src)
    assert item.classification == "missing_source_version"
    assert item.strict_validator_impact == "warning"


@pytest.mark.django_db
def test_aligned_source_is_ok():
    src = _source("fr-ok", "FR")
    _attach(src)
    LegalSourceVersion.objects.create(source=src, version_label="v1")
    _approve(src)
    item = classify_attachment_gap(src)
    assert item.classification == "ok"
    assert item.strict_validator_impact == "none"


@pytest.mark.django_db
def test_non_approve_latest_is_ok():
    src = _source("fr-rc", "FR")
    LegalReview.objects.create(
        source=src,
        reviewer=get_user_model().objects.create_user("rc", "rc@x.it", "x", is_staff=True),
        decision="request_changes",
    )
    assert classify_attachment_gap(src).classification == "ok"


# --------------------------------------------------------------------------- #
# command: leak-safe, read-only, fail-closed
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_command_output_leak_safe():
    src = _source(REGISTRY_SLUG, "BE")
    _attach(src)  # real sha256 on the attachment
    _approve(src)
    out = StringIO()
    call_command(
        "audit_legacy_attachment_alignment", "--include-ok", "--format", "json", stdout=out
    )
    body = out.getvalue()
    assert "@" not in body
    assert not re.search(r"[0-9a-f]{40,}", body)
    for tok in ("legal_data/", ".env", "C:\\", "/home/"):
        assert tok not in body


@pytest.mark.django_db
def test_command_is_read_only():
    src = _source(REGISTRY_SLUG, "BE")
    _approve(src)
    before = (
        LegalSource.objects.count(),
        LegalReview.objects.count(),
        LegalSourceAttachment.objects.count(),
    )
    call_command("audit_legacy_attachment_alignment", "--country", "BE", stdout=StringIO())
    after = (
        LegalSource.objects.count(),
        LegalReview.objects.count(),
        LegalSourceAttachment.objects.count(),
    )
    assert before == after


@pytest.mark.django_db
def test_command_fail_on_blocking():
    src = _source(REGISTRY_SLUG, "BE")
    _approve(src)
    with pytest.raises(CommandError):
        call_command(
            "audit_legacy_attachment_alignment",
            "--country",
            "BE",
            "--fail-on-blocking",
            stdout=StringIO(),
        )


@pytest.mark.django_db
def test_command_fail_on_manual_required():
    src = _source("fr-manual-xyz", "FR")
    _approve(src)
    with pytest.raises(CommandError):
        call_command(
            "audit_legacy_attachment_alignment",
            "--country",
            "FR",
            "--fail-on-manual-required",
            stdout=StringIO(),
        )


@pytest.mark.django_db
def test_command_default_exit_zero_with_findings():
    src = _source(REGISTRY_SLUG, "BE")
    _approve(src)
    # no --fail flags -> reports findings but exits 0
    call_command("audit_legacy_attachment_alignment", "--country", "BE", stdout=StringIO())


# --------------------------------------------------------------------------- #
# validator hint + no calculation activation
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_validator_shows_attachment_hint_on_blocking():
    src = _source(REGISTRY_SLUG, "BE")
    _approve(src)
    out = StringIO()
    call_command(
        "validate_legal_review_decisions", "--country", "BE", "--format", "text", stdout=out
    )
    assert "audit_legacy_attachment_alignment" in out.getvalue()


@pytest.mark.django_db
def test_audit_creates_no_dataset_and_keeps_fr_not_calc_ready():
    src = _source("fr-noact", "FR")
    _approve(src)
    ds_before = CompensationDataset.objects.count()
    report = build_legacy_attachment_alignment_report("FR")
    assert CompensationDataset.objects.count() == ds_before
    # no FR item is calculation-ready (the audit never activates anything)
    assert report["totals"]["blocking"] >= 1
    from apps.legal_sources.review_evidence import build_evidence_checklist

    assert all(ev.calculation_ready is False for ev in build_evidence_checklist("FR"))


# --------------------------------------------------------------------------- #
# admin action read-only
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_admin_alignment_action_read_only():
    from django.contrib.admin.sites import AdminSite
    from django.test import RequestFactory

    from apps.legal_sources.admin import LegalSourceAdmin

    src = _source(REGISTRY_SLUG, "BE")
    _approve(src)
    before = (LegalSource.objects.count(), LegalSourceAttachment.objects.count())
    ma = LegalSourceAdmin(LegalSource, AdminSite())
    req = RequestFactory().get("/admin/legal_sources/legalsource/")
    req.user = get_user_model().objects.create_superuser("a5", "a5@x.it", "x")
    req._messages = type("M", (), {"add": lambda *a, **k: None})()
    ma.show_attachment_alignment_action(req, LegalSource.objects.filter(pk=src.pk))
    assert (LegalSource.objects.count(), LegalSourceAttachment.objects.count()) == before
