"""
Seed METADATA delle fonti legali marocchine core per le successioni.

REGOLA ASSOLUTA — identica al seed Italia/Francia/Belgio:
Questo command crea SOLO i record `LegalSource` con metadati. Non
inserisce numeri, quote ereditarie, formule o tabelle. Le fonti sono
create con stato ``needs_review`` e devono essere approvate manualmente
da un legal reviewer prima di essere usabili dai calcolatori.

Idempotente: ``update_or_create(slug=...)`` con slug stabile. Lo
``status`` non viene riscritto: un re-seed non retrocede mai una fonte
già ``approved``.

Fonti marocchine caricate (metadati):
- Code de la famille (Moudawana) — Loi n° 70-03 du 3 février 2004,
  Livre III "Successions" — quadro normativo principale per le
  successioni in diritto marocchino;
- Dahir formant Code des obligations et des contrats (DOC) — riferito
  alle disposizioni patrimoniali generali;
- Code de procédure civile — disposizioni sulla devoluzione e sulla
  competenza territoriale per le pratiche successorie;
- Convention de La Haye 1989 sulla legge applicabile alle successioni
  (riferimento di diritto internazionale privato; il Marocco non ha
  ratificato ma è citato come standard internazionale comparato).

Lingua: arabo (lingua ufficiale del diritto marocchino) per le fonti
nazionali; francese per la convenzione internazionale.

GDPR: la trattazione di pratiche successorie reali richiede dati
sensibili (parentela, stato di morte, beni). Questo seed espone SOLO
metadati di fonti normative — nessun dato personale. La regola
permanente del progetto si applica anche qui: nessun calcolo reale
finché lo Studio non ha promosso le fonti a ``approved``.

Esecuzione:
    python manage.py seed_morocco_inheritance_legal_sources
    python manage.py seed_morocco_inheritance_legal_sources --quiet
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
    language_code: str = "ar"


SEED_SOURCES: list[_SourceSeed] = [
    _SourceSeed(
        slug="ma-moudawana-code-famille-livre-3-successions",
        title=(
            "Code de la famille (Moudawana) — Loi n° 70-03 du 3 février "
            "2004, Livre III « Successions »"
        ),
        citation="Loi n° 70-03 (Moudawana), Livre III",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=("http://adala.justice.gov.ma/"),
        publication_date=date(2004, 2, 5),
        effective_date=date(2004, 2, 5),
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. Cornice "
            "normativa principale del diritto delle successioni in "
            "Marocco. Le quote ereditarie (faraïd) sono regolate da "
            "regole di shari'a codificate nel Livre III: la trascrizione "
            "tabellare richiede revisione legale e non viene effettuata "
            "in questa fase di scaffold."
        ),
        language_code="ar",
    ),
    _SourceSeed(
        slug="ma-doc-obligations-contrats",
        title=("Dahir formant Code des obligations et des contrats — " "édition consolidée"),
        citation="Dahir 1913 — Code des obligations et des contrats (MA)",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=("http://adala.justice.gov.ma/"),
        publication_date=date(1913, 8, 12),
        effective_date=None,
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. "
            "Disciplina generale delle obbligazioni e dei contratti, "
            "rilevante per liquidazione del passivo e gestione del "
            "patrimonio successorio. Non contiene quote ereditarie."
        ),
        language_code="fr",
    ),
    _SourceSeed(
        slug="ma-code-procedure-civile",
        title=(
            "Code de procédure civile — disposizioni sulla devoluzione "
            "successoria e competenza territoriale"
        ),
        citation="Code de procédure civile (MA)",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=("http://adala.justice.gov.ma/"),
        publication_date=None,
        effective_date=None,
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. "
            "Procedure per atti di notorietà successoria, competenza "
            "territoriale e riconoscimento di atti stranieri. Quadro "
            "indispensabile per pratiche transfrontaliere."
        ),
        language_code="fr",
    ),
    _SourceSeed(
        slug="ma-international-private-law-comparative-reference",
        title=(
            "Convention de La Haye 1989 — loi applicable aux successions " "(référence comparative)"
        ),
        citation="HCCH 1989 (référence comparative)",
        source_type=SourceType.DOCTRINE,
        official_url=("https://www.hcch.net/en/instruments/conventions/full-text/?cid=62"),
        publication_date=date(1989, 8, 1),
        effective_date=None,
        # Standard di confronto, NON fonte vincolante per il Marocco —
        # reliability MEDIUM.
        reliability=Reliability.MEDIUM,
        notes=(
            "Source metadata only, requires Studio legal review. Il "
            "Marocco non ha ratificato la Convenzione, ma il testo è "
            "ampiamente usato come riferimento comparato per le regole di "
            "diritto internazionale privato applicabili alle successioni "
            "transfrontaliere. NON è fonte vincolante."
        ),
        language_code="fr",
    ),
]


class Command(BaseCommand):
    help = (
        "Crea i metadati delle fonti legali marocchine per le successioni "
        "(status needs_review). Idempotente. NON inserisce quote "
        "ereditarie né tabelle."
    )

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Sopprime l'output.")

    @transaction.atomic
    def handle(self, *args, **options):
        quiet = options["quiet"]

        country = self._get_or_create_morocco()
        jurisdiction = self._get_or_create_morocco_national(country)
        languages = self._get_or_create_languages()

        created = updated = 0
        for seed in SEED_SOURCES:
            language = languages.get(seed.language_code, languages["fr"])
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
                f"seed_morocco_inheritance_legal_sources completato: "
                f"{created} creati, {updated} aggiornati."
            )
        )

    # idempotent helpers for taxonomy objects
    def _get_or_create_morocco(self) -> Country:
        country, _ = Country.objects.get_or_create(
            code="MA",
            defaults={
                "code_alpha3": "MAR",
                "name": "Maroc",
                "is_active": True,
            },
        )
        return country

    def _get_or_create_morocco_national(self, country: Country) -> Jurisdiction:
        jurisdiction, _ = Jurisdiction.objects.get_or_create(
            code="MA-NATIONAL",
            defaults={
                "country": country,
                "name": "Maroc (niveau national)",
                # Sistema misto: shari'a codificata via Moudawana + civil law.
                # Per coerenza con la tassonomia esistente segniamo CIVIL_LAW.
                "legal_system": Jurisdiction.LegalSystem.CIVIL_LAW,
                "is_active": True,
            },
        )
        return jurisdiction

    def _get_or_create_languages(self) -> dict[str, Language]:
        out: dict[str, Language] = {}
        for code, name in (("ar", "العربية"), ("fr", "Français")):
            lang, _ = Language.objects.get_or_create(
                code=code,
                defaults={"name": name, "is_active": True},
            )
            out[code] = lang
        return out
