"""Tests F1 — apps.jurisdictions."""

import pytest

from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language


@pytest.mark.django_db
def test_country_normalises_alpha_codes():
    country = Country.objects.create(code="it", code_alpha3="ita", name="Italia")
    assert country.code == "IT"
    assert country.code_alpha3 == "ITA"
    assert str(country) == "IT — Italia"


@pytest.mark.django_db
def test_currency_normalises_code():
    currency = Currency.objects.create(code="eur", name="Euro", symbol="€")
    assert currency.code == "EUR"


@pytest.mark.django_db
def test_language_normalises_code():
    language = Language.objects.create(code="IT", name="Italiano")
    assert language.code == "it"


@pytest.mark.django_db
def test_jurisdiction_minimal_creation():
    country = Country.objects.create(code="IT", name="Italia")
    eur = Currency.objects.create(code="EUR", name="Euro")
    it_lang = Language.objects.create(code="it", name="Italiano")
    jurisdiction = Jurisdiction.objects.create(
        country=country,
        code="it",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency=eur,
        default_language=it_lang,
    )
    assert jurisdiction.code == "IT"
    assert jurisdiction.country == country
    assert jurisdiction.legal_system == Jurisdiction.LegalSystem.CIVIL_LAW
    assert "IT" in str(jurisdiction)
