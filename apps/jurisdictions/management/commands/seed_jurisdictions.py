"""
Seed dati di sistema per `apps.jurisdictions`.

NON è un seed legale (importi, coefficienti, tabelle): qui si caricano
SOLO oggetti tassonomici (paesi, lingue, valute) e le giurisdizioni
nazionali per i 5 paesi MVP. Questa distinzione è dichiarata in
`docs/architecture/PRODUCT_REQUIREMENTS.md` (REQ-3).

Idempotente: chiamabile N volte, non crea duplicati. Usa
`update_or_create` con `defaults`, in modo che:
- una nuova run aggiunge ciò che manca;
- aggiorna `name`/`is_active` se la riga di seed è cambiata;
- non tocca campi modificati manualmente non presenti nei `defaults`.

Esecuzione:
    python manage.py seed_jurisdictions
    python manage.py seed_jurisdictions --quiet
"""

from __future__ import annotations

from dataclasses import dataclass

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language


@dataclass(frozen=True)
class _LangSeed:
    code: str
    name: str


@dataclass(frozen=True)
class _CurrencySeed:
    code: str
    name: str
    symbol: str = ""


@dataclass(frozen=True)
class _CountrySeed:
    code: str
    code_alpha3: str
    name: str


@dataclass(frozen=True)
class _JurisdictionSeed:
    code: str
    country_code: str
    name: str
    legal_system: str
    default_currency: str
    default_language: str


# REQ-1: 4 lingue pubbliche + 2 lingue di lavoro per fonti BE/DE future.
LANGUAGES: list[_LangSeed] = [
    _LangSeed("it", "Italiano"),
    _LangSeed("fr", "Français"),
    _LangSeed("en", "English"),
    _LangSeed("ar", "العربية"),
    _LangSeed("nl", "Nederlands"),
    _LangSeed("de", "Deutsch"),
]

CURRENCIES: list[_CurrencySeed] = [
    _CurrencySeed("EUR", "Euro", "€"),
    _CurrencySeed("MAD", "Moroccan Dirham", "DH"),
    _CurrencySeed("TND", "Tunisian Dinar", "DT"),
]

# Paesi MVP (REQ-4). Nessun campo legale qui, solo tassonomia ISO.
COUNTRIES: list[_CountrySeed] = [
    _CountrySeed("IT", "ITA", "Italia"),
    _CountrySeed("FR", "FRA", "Francia"),
    _CountrySeed("BE", "BEL", "Belgio"),
    _CountrySeed("MA", "MAR", "Marocco"),
    _CountrySeed("TN", "TUN", "Tunisia"),
]

JURISDICTIONS: list[_JurisdictionSeed] = [
    _JurisdictionSeed(
        code="IT-NATIONAL",
        country_code="IT",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency="EUR",
        default_language="it",
    ),
    _JurisdictionSeed(
        code="FR-NATIONAL",
        country_code="FR",
        name="France (niveau national)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency="EUR",
        default_language="fr",
    ),
    _JurisdictionSeed(
        code="BE-NATIONAL",
        country_code="BE",
        name="Belgique (niveau fédéral)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
        default_currency="EUR",
        default_language="fr",
    ),
    _JurisdictionSeed(
        code="MA-NATIONAL",
        country_code="MA",
        name="المغرب (المستوى الوطني)",
        legal_system=Jurisdiction.LegalSystem.MIXED,
        default_currency="MAD",
        default_language="ar",
    ),
    _JurisdictionSeed(
        code="TN-NATIONAL",
        country_code="TN",
        name="تونس (المستوى الوطني)",
        legal_system=Jurisdiction.LegalSystem.MIXED,
        default_currency="TND",
        default_language="ar",
    ),
]


class Command(BaseCommand):
    help = "Seed idempotente per lingue, valute, paesi e giurisdizioni MVP."

    def add_arguments(self, parser):
        parser.add_argument(
            "--quiet",
            action="store_true",
            help="Sopprime l'output riga-per-riga.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        quiet = options["quiet"]
        stats = {
            "languages": self._seed_languages(quiet),
            "currencies": self._seed_currencies(quiet),
            "countries": self._seed_countries(quiet),
            "jurisdictions": self._seed_jurisdictions(quiet),
        }
        self.stdout.write(self.style.SUCCESS("seed_jurisdictions completato:"))
        for kind, (created, updated) in stats.items():
            self.stdout.write(f"  {kind}: {created} creati, {updated} aggiornati")

    # -- helpers ---------------------------------------------------------

    def _log(self, quiet: bool, msg: str) -> None:
        if not quiet:
            self.stdout.write(msg)

    def _seed_languages(self, quiet: bool) -> tuple[int, int]:
        # I `name` possono contenere caratteri non-ASCII (es. arabo, ç francese)
        # che la console Windows cp1252 non sa renderizzare. Logghiamo solo
        # i codici ISO (sempre ASCII); i nomi pieni restano nel DB.
        created = updated = 0
        for seed in LANGUAGES:
            obj, was_created = Language.objects.update_or_create(
                code=seed.code,
                defaults={"name": seed.name, "is_active": True},
            )
            if was_created:
                created += 1
                self._log(quiet, f"  + Language {obj.code}")
            else:
                updated += 1
        return created, updated

    def _seed_currencies(self, quiet: bool) -> tuple[int, int]:
        created = updated = 0
        for seed in CURRENCIES:
            obj, was_created = Currency.objects.update_or_create(
                code=seed.code,
                defaults={
                    "name": seed.name,
                    "symbol": seed.symbol,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self._log(quiet, f"  + Currency {obj.code}")
            else:
                updated += 1
        return created, updated

    def _seed_countries(self, quiet: bool) -> tuple[int, int]:
        created = updated = 0
        for seed in COUNTRIES:
            obj, was_created = Country.objects.update_or_create(
                code=seed.code,
                defaults={
                    "code_alpha3": seed.code_alpha3,
                    "name": seed.name,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self._log(quiet, f"  + Country {obj.code}")
            else:
                updated += 1
        return created, updated

    def _seed_jurisdictions(self, quiet: bool) -> tuple[int, int]:
        created = updated = 0
        for seed in JURISDICTIONS:
            country = Country.objects.get(code=seed.country_code)
            currency = Currency.objects.get(code=seed.default_currency)
            language = Language.objects.get(code=seed.default_language)
            obj, was_created = Jurisdiction.objects.update_or_create(
                code=seed.code,
                defaults={
                    "country": country,
                    "name": seed.name,
                    "legal_system": seed.legal_system,
                    "default_currency": currency,
                    "default_language": language,
                    "is_active": True,
                },
            )
            if was_created:
                created += 1
                self._log(quiet, f"  + Jurisdiction {obj.code}")
            else:
                updated += 1
        return created, updated
