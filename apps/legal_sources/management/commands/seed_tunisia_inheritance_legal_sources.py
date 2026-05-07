"""
Seed METADATA delle fonti legali tunisine core per le successioni.

REGOLA ASSOLUTA — identica al seed Italia/Francia/Belgio/Marocco:
Questo command crea SOLO i record `LegalSource` con metadati. Non
inserisce numeri, quote ereditarie, formule o tabelle. Le fonti sono
create con stato ``needs_review`` e devono essere approvate manualmente
da un legal reviewer prima di essere usabili dai calcolatori.

Idempotente: ``update_or_create(slug=...)`` con slug stabile. Lo
``status`` non viene riscritto: un re-seed non retrocede mai una fonte
già ``approved``.

Fonti tunisine caricate (metadati):
- Code du statut personnel — Loi du 13 août 1956, Livre IX
  "Successions" — quadro normativo principale per le successioni in
  diritto tunisino;
- Code des obligations et des contrats (COC) — disciplina generale
  per la liquidazione del passivo successorio;
- Code de droit international privé — Loi n° 98-97 du 27 novembre 1998
  — articoli sulla legge applicabile alle successioni transfrontaliere;
- Convention de La Haye 1989 — riferimento comparato (la Tunisia non
  ha ratificato).

Lingua: arabo (lingua ufficiale del diritto tunisino) per le fonti
nazionali; francese per il riferimento internazionale.

GDPR: la trattazione di pratiche successorie reali richiede dati
sensibili. Questo seed espone SOLO metadati di fonti normative —
nessun dato personale. Nessun calcolo reale finché non sono
``approved``.

Esecuzione:
    python manage.py seed_tunisia_inheritance_legal_sources
    python manage.py seed_tunisia_inheritance_legal_sources --quiet
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
        slug="tn-code-statut-personnel-livre-9-successions",
        title=("Code du statut personnel — Loi du 13 août 1956, Livre IX " "« Successions »"),
        citation="CSP TN, Livre IX",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=("https://legislation.tn/"),
        publication_date=date(1956, 8, 13),
        effective_date=date(1957, 1, 1),
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. Cornice "
            "normativa principale del diritto delle successioni in "
            "Tunisia. Le quote ereditarie (faraïd) sono codificate nel "
            "Livre IX: la trascrizione tabellare richiede revisione "
            "legale e non viene effettuata in questa fase di scaffold."
        ),
        language_code="ar",
    ),
    _SourceSeed(
        slug="tn-coc-obligations-contrats",
        title=("Code des obligations et des contrats — édition consolidée"),
        citation="COC TN — Code des obligations et des contrats",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=("https://legislation.tn/"),
        publication_date=date(1906, 12, 15),
        effective_date=None,
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. "
            "Disciplina generale delle obbligazioni e dei contratti, "
            "rilevante per la liquidazione del passivo e la gestione "
            "del patrimonio successorio. Non contiene quote ereditarie."
        ),
        language_code="fr",
    ),
    _SourceSeed(
        slug="tn-code-droit-international-prive-1998",
        title=("Code de droit international privé — Loi n° 98-97 du 27 " "novembre 1998"),
        citation="Loi n° 98-97 — CDIP TN",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=("https://legislation.tn/"),
        publication_date=date(1998, 11, 27),
        effective_date=date(1999, 3, 1),
        reliability=Reliability.OFFICIAL,
        notes=(
            "Source metadata only, requires Studio legal review. "
            "Articoli specifici sulla legge applicabile alle successioni "
            "transfrontaliere e sulla competenza dei tribunali tunisini. "
            "Riferimento normativo essenziale per le pratiche cross-"
            "border."
        ),
        language_code="fr",
    ),
    _SourceSeed(
        slug="tn-international-private-law-comparative-reference",
        title=(
            "Convention de La Haye 1989 — loi applicable aux successions " "(référence comparative)"
        ),
        citation="HCCH 1989 (référence comparative)",
        source_type=SourceType.DOCTRINE,
        official_url=("https://www.hcch.net/en/instruments/conventions/full-text/?cid=62"),
        publication_date=date(1989, 8, 1),
        effective_date=None,
        # Standard di confronto, NON fonte vincolante per la Tunisia —
        # reliability MEDIUM.
        reliability=Reliability.MEDIUM,
        notes=(
            "Source metadata only, requires Studio legal review. La "
            "Tunisia non ha ratificato la Convenzione, ma il testo è "
            "ampiamente usato come riferimento comparato per il diritto "
            "internazionale privato delle successioni. NON è fonte "
            "vincolante."
        ),
        language_code="fr",
    ),
]


class Command(BaseCommand):
    help = (
        "Crea i metadati delle fonti legali tunisine per le successioni "
        "(status needs_review). Idempotente. NON inserisce quote "
        "ereditarie né tabelle."
    )

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Sopprime l'output.")

    @transaction.atomic
    def handle(self, *args, **options):
        quiet = options["quiet"]

        country = self._get_or_create_tunisia()
        jurisdiction = self._get_or_create_tunisia_national(country)
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
                f"seed_tunisia_inheritance_legal_sources completato: "
                f"{created} creati, {updated} aggiornati."
            )
        )

    # idempotent helpers for taxonomy objects
    def _get_or_create_tunisia(self) -> Country:
        country, _ = Country.objects.get_or_create(
            code="TN",
            defaults={
                "code_alpha3": "TUN",
                "name": "Tunisie",
                "is_active": True,
            },
        )
        return country

    def _get_or_create_tunisia_national(self, country: Country) -> Jurisdiction:
        jurisdiction, _ = Jurisdiction.objects.get_or_create(
            code="TN-NATIONAL",
            defaults={
                "country": country,
                "name": "Tunisie (niveau national)",
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
