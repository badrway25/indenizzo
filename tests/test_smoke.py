"""Smoke tests F0: scaffolding sano, custom user model, home raggiungibile."""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client


def test_settings_loaded():
    assert settings.AUTH_USER_MODEL == "accounts.User"
    assert "apps.accounts" in settings.INSTALLED_APPS
    assert "apps.legal_sources" in settings.INSTALLED_APPS
    assert "apps.calculators" in settings.INSTALLED_APPS


def test_languages_configured():
    codes = {code for code, _ in settings.LANGUAGES}
    assert {"it", "fr", "en", "ar"}.issubset(codes)


@pytest.mark.django_db
def test_user_model_has_studio_fields():
    User = get_user_model()
    user = User.objects.create_user(username="lawyer1", password="pw")
    assert user.role == User.Role.CLIENT
    assert user.preferred_language == User.Language.IT
    assert user.phone_number == ""
    assert user.company_or_firm_name == ""
    assert user.created_at is not None
    assert user.updated_at is not None


def test_home_reachable():
    response = Client().get("/")
    assert response.status_code == 200


@pytest.mark.django_db
def test_admin_login_reachable():
    response = Client().get("/admin/login/")
    assert response.status_code == 200
