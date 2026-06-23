"""D4: tests for the manual LegalReview decision guard + validator.

Asserts the guard blocks an incoherent approve, allows reject/request_changes,
never permits calculation activation, the admin form enforces the block, the
validator command is read-only + PII-safe, and FR/BE/MA/TN stay fail-closed.
"""

from __future__ import annotations

from datetime import date
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.compensation.models import CompensationDataset
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalReview, LegalSource, LegalSourceAttachment
from apps.legal_sources.review_decision_guard import (
    evaluate_legal_review_decision,
)


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


def _version(src):
    from apps.legal_sources.models import LegalSourceVersion

    return LegalSourceVersion.objects.create(source=src, version_label="v1")


# --------------------------------------------------------------------------- #
# guard
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_approve_without_attachment_blocked():
    src = _source("fr-na", "FR")
    r = evaluate_legal_review_decision(src, "approve")
    assert r.allowed is False
    assert r.severity == "blocking"
    assert r.calculation_activation_allowed is False


@pytest.mark.django_db
def test_approve_with_attachment_no_hash_blocked():
    src = _source("fr-nh", "FR")
    att = _attach(src)
    LegalSourceAttachment.objects.filter(pk=att.pk).update(sha256="")
    r = evaluate_legal_review_decision(src, "approve")
    assert r.allowed is False
    assert any("hash" in b for b in r.blocking_reasons)


@pytest.mark.django_db
def test_approve_with_hash_but_no_version_is_warning_but_allowed():
    src = _source("fr-nv", "FR")
    _attach(src)  # auto-hashed
    r = evaluate_legal_review_decision(src, "approve")
    assert r.allowed is True
    assert r.severity == "warning"
    assert r.calculation_activation_allowed is False  # never activates


@pytest.mark.django_db
def test_approve_full_evidence_allowed_no_activation():
    src = _source("fr-ok", "FR")
    _attach(src)
    _version(src)
    r = evaluate_legal_review_decision(src, "approve")
    assert r.allowed is True
    assert r.calculation_activation_allowed is False


@pytest.mark.django_db
@pytest.mark.parametrize("decision", ["reject", "request_changes", "reopen"])
def test_non_approve_decisions_allowed(decision):
    src = _source(f"fr-{decision}", "FR")
    r = evaluate_legal_review_decision(src, decision)
    assert r.allowed is True
    assert r.severity == "ok"
    assert r.calculation_activation_allowed is False


# --------------------------------------------------------------------------- #
# admin form
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_admin_form_blocks_incoherent_approve():
    from apps.legal_sources.admin import LegalReviewAdminForm

    src = _source("fr-form-na", "FR")  # no attachment
    f = LegalReviewAdminForm(data={"source": src.pk, "decision": "approve", "comment": "x"})
    assert f.is_valid() is False
    assert any("block" in str(e).lower() for e in f.errors.get("__all__", []))


@pytest.mark.django_db
def test_admin_form_allows_request_changes_and_safe_approve():
    from apps.legal_sources.admin import LegalReviewAdminForm

    src = _source("fr-form-rc", "FR")
    assert LegalReviewAdminForm(
        data={"source": src.pk, "decision": "request_changes", "comment": "please fix"}
    ).is_valid()
    _attach(src)
    _version(src)
    assert LegalReviewAdminForm(
        data={"source": src.pk, "decision": "approve", "comment": "authenticated"}
    ).is_valid()


@pytest.mark.django_db
def test_admin_create_review_creates_no_dataset_and_forces_reviewer():
    from django.test import Client

    user = get_user_model().objects.create_superuser("d4admin", "a@x.it", "x")
    src = _source("fr-admin-create", "FR")
    _attach(src)
    _version(src)
    c = Client()
    c.force_login(user)
    ds_before = CompensationDataset.objects.count()
    c.post(
        "/admin/legal_sources/legalreview/add/",
        {
            "source": src.pk,
            "decision": "approve",
            "comment": "ok",
            "previous_status": "",
            "new_status": "",
        },
        HTTP_HOST="127.0.0.1",
    )
    rev = LegalReview.objects.filter(source=src).first()
    assert rev is not None and rev.reviewer_id == user.pk  # reviewer forced
    assert CompensationDataset.objects.count() == ds_before  # no dataset created
    # recording an approval never makes the FR source calculation-ready
    from apps.legal_sources.review_evidence import build_evidence_checklist

    row = next(r for r in build_evidence_checklist("FR") if r.slug == src.slug)
    assert row.calculation_ready is False


# --------------------------------------------------------------------------- #
# validator command
# --------------------------------------------------------------------------- #


@pytest.mark.django_db
def test_validator_is_read_only_and_pii_safe():
    src = _source("fr-val", "FR")
    LegalReview.objects.create(
        source=src,
        reviewer=get_user_model().objects.create_user("rv", "rv@x.it", "x", is_staff=True),
        decision="approve",  # no attachment -> a blocking finding
        comment="sensitive note",
    )
    before = (LegalSource.objects.count(), LegalReview.objects.count())
    out = StringIO()
    call_command(
        "validate_legal_review_decisions", "--country", "FR", "--format", "json", stdout=out
    )
    assert (LegalSource.objects.count(), LegalReview.objects.count()) == before
    body = out.getvalue()
    assert "@" not in body
    assert "sensitive note" not in body


@pytest.mark.django_db
def test_validator_fail_on_blocking():
    src = _source("fr-block", "FR")
    LegalReview.objects.create(
        source=src,
        reviewer=get_user_model().objects.create_user("rv2", "rv2@x.it", "x", is_staff=True),
        decision="approve",  # no attachment -> blocking
    )
    with pytest.raises(CommandError):
        call_command(
            "validate_legal_review_decisions",
            "--country",
            "FR",
            "--fail-on-blocking",
            stdout=StringIO(),
        )


@pytest.mark.django_db
def test_validator_invariants_clean_on_simple_data():
    _source("fr-inv", "FR")
    # no calc-ready sources, no approved datasets -> invariants clean -> exit 0
    call_command("validate_legal_review_decisions", "--country", "FR", stdout=StringIO())
