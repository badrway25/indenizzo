"""Tests F1 + F2 — apps.jurisdictions."""

from io import StringIO

import pytest
from django.core.management import call_command

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


# ---------------------------------------------------------------------------
# F2 — seed_jurisdictions
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_seed_jurisdictions_creates_mvp_dataset():
    call_command("seed_jurisdictions", "--quiet", stdout=StringIO())

    assert Language.objects.filter(code__in=["it", "fr", "en", "ar", "nl", "de"]).count() == 6
    assert Currency.objects.filter(code__in=["EUR", "MAD", "TND"]).count() == 3

    country_codes = set(Country.objects.values_list("code", flat=True))
    assert {"IT", "FR", "BE", "MA", "TN"}.issubset(country_codes)

    jurisdiction_codes = set(Jurisdiction.objects.values_list("code", flat=True))
    assert {
        "IT-NATIONAL",
        "FR-NATIONAL",
        "BE-NATIONAL",
        "MA-NATIONAL",
        "TN-NATIONAL",
    }.issubset(jurisdiction_codes)


@pytest.mark.django_db
def test_seed_jurisdictions_is_idempotent():
    out = StringIO()
    call_command("seed_jurisdictions", "--quiet", stdout=out)

    counts_after_first = (
        Language.objects.count(),
        Currency.objects.count(),
        Country.objects.count(),
        Jurisdiction.objects.count(),
    )

    call_command("seed_jurisdictions", "--quiet", stdout=StringIO())

    counts_after_second = (
        Language.objects.count(),
        Currency.objects.count(),
        Country.objects.count(),
        Jurisdiction.objects.count(),
    )
    assert counts_after_first == counts_after_second


@pytest.mark.django_db
def test_seed_jurisdictions_links_defaults_correctly():
    call_command("seed_jurisdictions", "--quiet", stdout=StringIO())

    italy_nat = Jurisdiction.objects.get(code="IT-NATIONAL")
    assert italy_nat.country.code == "IT"
    assert italy_nat.default_currency.code == "EUR"
    assert italy_nat.default_language.code == "it"
    assert italy_nat.legal_system == Jurisdiction.LegalSystem.CIVIL_LAW

    morocco_nat = Jurisdiction.objects.get(code="MA-NATIONAL")
    assert morocco_nat.default_currency.code == "MAD"
    assert morocco_nat.default_language.code == "ar"
    assert morocco_nat.legal_system == Jurisdiction.LegalSystem.MIXED


@pytest.mark.django_db
def test_seed_jurisdictions_updates_existing_record_without_duplicating():
    Country.objects.create(code="IT", code_alpha3="ITA", name="WRONG_NAME")
    call_command("seed_jurisdictions", "--quiet", stdout=StringIO())
    italy = Country.objects.get(code="IT")
    assert italy.name == "Italia"
    assert Country.objects.filter(code="IT").count() == 1
