"""
Seed METADATA delle fonti legali belghe core per il danno corporale RCA.

REGOLA ASSOLUTA — identica al seed Italia/Francia:
Questo command crea SOLO i record `LegalSource` con metadati (titolo,
citation, URL ufficiale, tipo, paese, lingua). Non inserisce numeri,
coefficienti, formule o tabelle. Le fonti sono create con stato
``needs_review`` e devono essere approvate manualmente da un legal
reviewer prima di essere usabili dai calcolatori.

Idempotente: chiamabile N volte. ``update_or_create(slug=...)`` con
slug stabile per evitare duplicati. Lo `status` non viene riscritto:
un re-seed non retrocede mai una fonte già `approved` a `needs_review`.

Fonti belghe caricate (metadati):
- Loi du 21 novembre 1989 — assurance obligatoire de la responsabilité
  civile en matière de véhicules automoteurs (cornice giuridica RCA);
- Code civil belge — articles 1382-1383 — responsabilité extra-
  contractuelle (cornice civile generale per il préjudice);
- Tableau indicatif des cours et tribunaux — édition 2020/2024:
  ``court_table`` (orientamento giurisprudenziale, reliability HIGH);
- Barème de capitalisation Schryvers (édition 2020): ``court_table``
  per la conversione di rendite (perte de revenus, aide d'une tierce
  personne).

Lingua: il Belgio è plurilingue. I documenti sono spesso emessi in fr
e nl. Per il seed iniziale usiamo `fr` come default (Studio Badrane
opera in francese); le versioni nl potranno essere aggiunte in futuro
come `LegalSource` distinte sullo stesso slug-base.

Esecuzione:
    python manage.py seed_belgium_legal_sources
    python manage.py seed_belgium_legal_sources --quiet
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
from apps.legal_sources.models import LegalSource


@dataclass(frozen=True)
class _SourceSeed:
    slug: str
    title: str
    citation: str
    source_type: str
    official_url: str = ""
    publication_date: date | None = None
    effective_date: date | None = None
    reliability: str = Reliability.OFFICIAL
    initial_status: str = SourceStatus.NEEDS_REVIEW
    notes: str = ""
    language_code: str = "fr"


SEED_SOURCES: list[_SourceSeed] = [
    _SourceSeed(
        slug="be-loi-1989-11-21-assurance-rc-auto",
        title=(
            "Loi du 21 novembre 1989 — assurance obligatoire de la "
            "responsabilité civile en matière de véhicules automoteurs"
        ),
        citation="Loi du 21 novembre 1989 (BE)",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=(
            "https://www.ejustice.just.fgov.be/cgi_loi/change_lg.pl?"
            "language=fr&la=F&cn=1989112135&table_name=loi"
        ),
        publication_date=date(1989, 12, 8),
        effective_date=date(1990, 6, 1),
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. Cornice "
            "giuridica primaria per l'assicurazione obbligatoria RCA "
            "in Belgio. Non contiene tabelle quantitative per il danno "
            "alla persona: i valori monetari derivano dal Tableau "
            "indicatif e dalla giurisprudenza dei cours et tribunaux."
        ),
    ),
    _SourceSeed(
        slug="be-code-civil-art-1382-1383",
        title=("Code civil belge — articles 1382-1383 — responsabilité " "extracontractuelle"),
        citation="Code civil BE, art. 1382-1383",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=(
            "https://www.ejustice.just.fgov.be/cgi_loi/change_lg.pl?"
            "language=fr&la=F&cn=1804032132&table_name=loi"
        ),
        publication_date=None,
        effective_date=None,
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. "
            "Riferimento normativo per la responsabilità extra-"
            "contrattuale e l'obbligo di riparazione integrale del "
            "danno. Base giuridica complementare alla Loi du 21 "
            "novembre 1989 per il danno alla persona da incidente "
            "stradale."
        ),
    ),
    _SourceSeed(
        slug="be-tableau-indicatif-cours-tribunaux-2020",
        title=(
            "Tableau indicatif des cours et tribunaux — édition 2020 "
            "(évaluation forfaitaire du dommage)"
        ),
        citation="Tableau indicatif BE, éd. 2020",
        source_type=SourceType.COURT_TABLE,
        official_url=("https://www.juridat.be/"),
        publication_date=date(2020, 6, 1),
        effective_date=None,
        # NON è atto normativo: è uno strumento giurisprudenziale —
        # reliability HIGH, non OFFICIAL.
        reliability=Reliability.HIGH,
        notes=(
            "Source metadata only, requires Studio legal review. "
            "Tableau indicatif (non vincolante) curato dall'Union royale "
            "des juges de paix et de police con riferimenti a importi "
            "forfaitari per voci di danno (incapacité temporaire, "
            "pretium doloris, dommage esthétique, ecc.). La trascrizione "
            "tabellare richiede revisione legale e attribuzione "
            "esplicita dell'edizione di riferimento prima di qualunque "
            "passaggio a status APPROVED."
        ),
    ),
    _SourceSeed(
        slug="be-bareme-capitalisation-schryvers-2020",
        title=("Barème de capitalisation Schryvers — édition 2020"),
        citation="Barème Schryvers 2020",
        source_type=SourceType.COURT_TABLE,
        official_url=("https://www.larcier-intersentia.com/"),
        publication_date=date(2020, 1, 1),
        effective_date=None,
        reliability=Reliability.HIGH,
        notes=(
            "Source metadata only, requires Studio legal review. Tavole "
            "di capitalizzazione utilizzate dai cours et tribunaux belgi "
            "per la conversione di rendite vitalizie (perte de revenus "
            "futurs, aide d'une tierce personne) in capitale. Standard "
            "giurisprudenziale, non atto normativo."
        ),
    ),
]


class Command(BaseCommand):
    help = (
        "Crea i metadati delle fonti legali belghe core (status "
        "needs_review). Idempotente. NON inserisce importi tabellari."
    )

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Sopprime l'output.")

    @transaction.atomic
    def handle(self, *args, **options):
        quiet = options["quiet"]

        country = self._get_or_create_belgium()
        jurisdiction = self._get_or_create_belgium_national(country)
        language = self._get_or_create_french()

        created = updated = 0
        for seed in SEED_SOURCES:
            obj, was_created = LegalSource.objects.update_or_create(
                slug=seed.slug,
                defaults={
                    "title": seed.title,
                    "citation": seed.citation,
                    "country": country,
                    "jurisdiction": jurisdiction,
                    "language": language,
                    "source_type": seed.source_type,
                    "official_url": seed.official_url,
                    "publication_date": seed.publication_date,
                    "effective_date": seed.effective_date,
                    "reliability": seed.reliability,
                    "notes": seed.notes,
                    "last_checked_at": date.today(),
                },
            )
            if was_created:
                obj.status = seed.initial_status
                obj.save(update_fields=["status"])
                created += 1
                if not quiet:
                    self.stdout.write(f"  + {seed.slug} ({obj.status})")
            else:
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"seed_belgium_legal_sources completato: "
                f"{created} creati, {updated} aggiornati."
            )
        )

    # idempotent helpers for taxonomy objects
    def _get_or_create_belgium(self) -> Country:
        country, _ = Country.objects.get_or_create(
            code="BE",
            defaults={
                "code_alpha3": "BEL",
                "name": "Belgique",
                "is_active": True,
            },
        )
        return country

    def _get_or_create_belgium_national(self, country: Country) -> Jurisdiction:
        jurisdiction, _ = Jurisdiction.objects.get_or_create(
            code="BE-NATIONAL",
            defaults={
                "country": country,
                "name": "Belgique (niveau fédéral)",
                "legal_system": Jurisdiction.LegalSystem.CIVIL_LAW,
                "is_active": True,
            },
        )
        return jurisdiction

    def _get_or_create_french(self) -> Language:
        language, _ = Language.objects.get_or_create(
            code="fr",
            defaults={"name": "Français", "is_active": True},
        )
        return language
