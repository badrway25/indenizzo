"""
Seed METADATA delle fonti legali francesi core per il danno corporale RCA.

REGOLA ASSOLUTA — identica al seed italiano:
Questo command crea SOLO i record `LegalSource` con metadati (titolo,
citation, URL ufficiale, tipo, paese, lingua). Non inserisce numeri,
coefficienti, formule o tabelle. Le fonti sono create con stato
``needs_review`` (o ``draft``) e devono essere approvate manualmente
da un legal reviewer prima di essere usabili dai calcolatori.

Idempotente: chiamabile N volte. ``update_or_create(slug=...)`` con
slug stabile per evitare duplicati. Lo `status` non viene riscritto:
un re-seed non retrocede mai una fonte già `approved` a `needs_review`.

Fonti francesi caricate (metadati):
- Loi du 5 juillet 1985 (Loi Badinter) — indemnisation des victimes
  d'accidents de la circulation. Cornice giuridica;
- Code des assurances — chapitre risque automobile (articles L211-*),
  base contrattuale dell'assicurazione obbligatoria;
- Référentiel indicatif d'indemnisation des préjudices corporels —
  cours d'appel (versione 2022). NON è atto normativo, è
  ``court_table`` (orientamento giurisprudenziale, reliability HIGH);
- Barème de capitalisation Gazette du Palais 2022 — coefficienti per
  la capitalizzazione delle rendite. ``court_table`` indicativo.

Esecuzione:
    python manage.py seed_france_legal_sources
    python manage.py seed_france_legal_sources --quiet
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
        slug="fr-loi-1985-07-05-badinter",
        title=(
            "Loi n° 85-677 du 5 juillet 1985 — Loi Badinter, indemnisation des "
            "victimes d'accidents de la circulation"
        ),
        citation="Loi n° 85-677 du 5 juillet 1985",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=("https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000693454/"),
        publication_date=date(1985, 7, 6),
        effective_date=date(1986, 1, 1),
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. Cornice "
            "giuridica primaria per l'indennizzo delle vittime di incidenti "
            "stradali in Francia. Non contiene tabelle quantitative: i valori "
            "monetari derivano da Référentiel indicatif e prassi giurisprudenziale."
        ),
    ),
    _SourceSeed(
        slug="fr-code-assurances-l211",
        title=("Code des assurances — chapitre risque automobile (articles " "L211-1 et suivants)"),
        citation="Code des assurances, art. L211-* (FR)",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=(
            "https://www.legifrance.gouv.fr/codes/section_lc/LEGITEXT000006073984/"
            "LEGISCTA000006159338/"
        ),
        publication_date=None,
        effective_date=None,
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. Disciplina "
            "contrattuale dell'assicurazione obbligatoria della responsabilità "
            "civile auto. Riferimento normativo per i poteri ispettivi e i "
            "termini di indennizzo (offerta d'indennizzo, prescrizioni, ecc.)."
        ),
    ),
    _SourceSeed(
        slug="fr-referentiel-indicatif-cours-appel-2022",
        title=(
            "Référentiel indicatif d'indemnisation des préjudices corporels "
            "des cours d'appel — édition 2022"
        ),
        citation="Référentiel indicatif cours d'appel, éd. 2022",
        source_type=SourceType.COURT_TABLE,
        official_url=("https://www.cours-appel.justice.fr/"),
        publication_date=date(2022, 9, 1),
        effective_date=None,
        # NON è atto normativo: è uno standard giurisprudenziale —
        # reliability HIGH, non OFFICIAL.
        reliability=Reliability.HIGH,
        notes=(
            "Source metadata only, requires Studio legal review. Référentiel "
            "indicatif (non vincolante) frutto di lavori inter-cour d'appel "
            "per uniformare la liquidazione dei préjudices corporels. La "
            "trascrizione tabellare richiede revisione legale e attribuzione "
            "esplicita dell'edizione di riferimento prima di qualunque "
            "passaggio a status APPROVED."
        ),
    ),
    _SourceSeed(
        slug="fr-bareme-capitalisation-gazette-palais-2022",
        title=("Barème de capitalisation — Gazette du Palais (édition 2022)"),
        citation="Barème Gazette du Palais 2022",
        source_type=SourceType.COURT_TABLE,
        official_url=("https://www.gazette-du-palais.fr/"),
        publication_date=date(2022, 1, 1),
        effective_date=None,
        reliability=Reliability.HIGH,
        notes=(
            "Source metadata only, requires Studio legal review. Tavole di "
            "capitalizzazione utilizzate per la conversione di rendite vitalizie "
            "(perte de gains professionnels futurs, tierce personne) in capitale. "
            "Standard giurisprudenziale, non atto normativo."
        ),
    ),
]


class Command(BaseCommand):
    help = (
        "Crea i metadati delle fonti legali francesi core (status "
        "needs_review). Idempotente. NON inserisce importi tabellari."
    )

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Sopprime l'output.")

    @transaction.atomic
    def handle(self, *args, **options):
        quiet = options["quiet"]

        country = self._get_or_create_france()
        jurisdiction = self._get_or_create_france_national(country)
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
                f"seed_france_legal_sources completato: " f"{created} creati, {updated} aggiornati."
            )
        )

    # idempotent helpers for taxonomy objects
    def _get_or_create_france(self) -> Country:
        country, _ = Country.objects.get_or_create(
            code="FR",
            defaults={
                "code_alpha3": "FRA",
                "name": "France",
                "is_active": True,
            },
        )
        return country

    def _get_or_create_france_national(self, country: Country) -> Jurisdiction:
        jurisdiction, _ = Jurisdiction.objects.get_or_create(
            code="FR-NATIONAL",
            defaults={
                "country": country,
                "name": "France (niveau national)",
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
