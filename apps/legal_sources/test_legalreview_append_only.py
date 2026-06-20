"""H-1 item 3: ``LegalReviewAdmin`` è append-only e non falsificabile.

Invarianti verificati al layer admin (prevenzione, non solo audit detective):

- mai cancellabile;
- righe esistenti congelate (sola lettura);
- in creazione il ``reviewer`` è forzato a ``request.user``.
"""

from __future__ import annotations

from datetime import date

import pytest
from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory


@pytest.fixture
def legal_source(db):
    from apps.jurisdictions.models import Country, Jurisdiction, Language
    from apps.legal_sources.enums import SourceStatus, SourceType
    from apps.legal_sources.models import LegalSource

    country = Country.objects.create(code="FR", code_alpha3="FRA", name="France")
    lang = Language.objects.create(code="fr", name="Français")
    juris = Jurisdiction.objects.create(
        country=country,
        code="FR-NATIONAL",
        name="France",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )
    return LegalSource.objects.create(
        slug="fr-test-src-append-only",
        title="Test source",
        country=country,
        jurisdiction=juris,
        language=lang,
        source_type=SourceType.OFFICIAL_LAW,
        status=SourceStatus.NEEDS_REVIEW,
        publication_date=date(2020, 1, 1),
    )


@pytest.fixture
def staff_user(db):
    return get_user_model().objects.create_user(
        username="staff_rev",
        email="s@x.org",
        password="x",
        is_staff=True,
        is_superuser=True,
    )


def _admin():
    from apps.legal_sources.admin import LegalReviewAdmin
    from apps.legal_sources.models import LegalReview

    return LegalReviewAdmin(LegalReview, AdminSite())


@pytest.mark.django_db
def test_legalreview_admin_never_allows_delete(staff_user):
    req = RequestFactory().get("/")
    req.user = staff_user
    assert _admin().has_delete_permission(req) is False


@pytest.mark.django_db
def test_legalreview_admin_freezes_existing_rows(legal_source, staff_user):
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    review = LegalReview.objects.create(
        source=legal_source,
        reviewer=staff_user,
        decision=LegalReview.Decision.APPROVE,
        previous_status=SourceStatus.NEEDS_REVIEW,
        new_status=SourceStatus.APPROVED,
    )
    admin_obj = _admin()
    req = RequestFactory().get("/")
    req.user = staff_user

    # Riga esistente: non modificabile. Accesso al modulo / add: consentito.
    assert admin_obj.has_change_permission(req, review) is False
    assert admin_obj.has_change_permission(req, None) is True

    ro = admin_obj.get_readonly_fields(req, review)
    for field in ("source", "reviewer", "decision", "previous_status", "new_status", "comment"):
        assert field in ro


@pytest.mark.django_db
def test_legalreview_admin_forces_reviewer_to_request_user(legal_source, staff_user):
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview

    other = get_user_model().objects.create_user(
        username="someone_else",
        email="o@x.org",
        password="x",
        is_staff=True,
    )
    admin_obj = _admin()
    req = RequestFactory().post("/")
    req.user = staff_user

    # Creazione con reviewer impostato a un ALTRO utente: save_model deve
    # forzarlo all'utente loggato.
    obj = LegalReview(
        source=legal_source,
        reviewer=other,
        decision=LegalReview.Decision.APPROVE,
        previous_status=SourceStatus.NEEDS_REVIEW,
        new_status=SourceStatus.APPROVED,
    )
    admin_obj.save_model(req, obj, form=None, change=False)
    obj.refresh_from_db()
    assert obj.reviewer_id == staff_user.id

    # `reviewer` non è esposto nel form di creazione.
    assert "reviewer" not in admin_obj.get_fields(req, None)
