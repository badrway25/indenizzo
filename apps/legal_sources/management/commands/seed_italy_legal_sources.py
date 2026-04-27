"""
Seed METADATA delle fonti legali italiane core per il danno biologico RCA.

REGOLA ASSOLUTA:
Questo command crea SOLO i record `LegalSource` con metadati (titolo,
citazione, URL ufficiale, tipo, paese, lingua). Non inserisce numeri,
coefficienti, formule o tabelle. Le fonti sono create con stato
`needs_review` e devono essere approvate manualmente da un legal
reviewer prima di essere usabili dai calcolatori.

Idempotente: chiamabile N volte. Usa `update_or_create(slug=...)` con
slug stabile per evitare duplicati. I `defaults` aggiornano titolo,
citation, source_type, official_url, publication/effective dates,
reliability e last_checked_at — ma NON status, perché lo stato è
proprietà del workflow umano (un re-seed non deve mai retrocedere
una fonte da `approved` a `needs_review`).

Fonti italiane caricate:
- D.P.R. 13 gennaio 2025 n. 12 — Tabella Unica Nazionale danno biologico
  RCA (decreto attuativo dell'art. 138 CAP, gravi lesioni);
- MIMIT decreto 18 luglio 2025 — aggiornamento importi danno biologico
  da lievi lesioni (art. 139 CAP);
- MIMIT decreto 10 dicembre 2025 — aggiornamento importi danno biologico
  da lesioni di non lieve entità / macrolesioni;
- D.Lgs. 7 settembre 2005 n. 209 (Codice delle Assicurazioni Private),
  art. 138 e art. 139, struttura giuridica del danno biologico RCA;
- Tabelle Milano 2024 — orientamento giurisprudenziale del Tribunale
  di Milano per danno non patrimoniale (NON è fonte ministeriale, è
  caricata come `court_table` con reliability `high`).

Esecuzione:
    python manage.py seed_italy_legal_sources
    python manage.py seed_italy_legal_sources --quiet
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
    """Spec di una fonte. NESSUN dato tabellare qui — solo metadati."""

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

    # Le fonti italiane sono in italiano. Lingua è obbligatoria per essere
    # promosse `approved` (clean() di LegalSource).
    language_code: str = "it"


# ---------------------------------------------------------------------------
# Lista delle fonti. Tutti gli URL ufficiali sono Gazzetta Ufficiale o
# portali ministeriali pubblici. NESSUNO contiene importi inseriti qui:
# i numeri stanno solo nel contenuto delle fonti, non nel codice.
# ---------------------------------------------------------------------------
SEED_SOURCES: list[_SourceSeed] = [
    _SourceSeed(
        slug="it-dpr-12-2025-tun-danno-biologico",
        title=(
            "D.P.R. 13 gennaio 2025, n. 12 — Tabella Unica Nazionale danno "
            "biologico per lesioni di non lieve entità (art. 138 CAP)"
        ),
        citation="D.P.R. 13 gennaio 2025, n. 12",
        source_type=SourceType.MINISTRY_DECREE,
        official_url="https://www.gazzettaufficiale.it/eli/id/2025/02/11/25G00018/sg",
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 2, 26),
        reliability=Reliability.OFFICIAL,
        notes=(
            "Decreto attuativo della Tabella Unica Nazionale prevista "
            "dall'art. 138 del Codice delle Assicurazioni Private. La "
            "trascrizione tabellare richiede revisione legale prima del "
            "passaggio a status APPROVED."
        ),
    ),
    _SourceSeed(
        slug="it-mimit-2025-07-aggiornamento-art-139",
        title=(
            "Decreto MIMIT 18 luglio 2025 — aggiornamento importi danno "
            "biologico da lievi lesioni (art. 139 CAP)"
        ),
        citation="D.M. MIMIT 18 luglio 2025",
        source_type=SourceType.MINISTRY_DECREE,
        official_url="https://www.mimit.gov.it/it/normativa/decreti-ministeriali",
        publication_date=date(2025, 7, 18),
        effective_date=None,
        reliability=Reliability.OFFICIAL,
        notes=(
            "Aggiornamento annuale ISTAT degli importi unitari ex art. 139 "
            "CAP per il danno biologico da lesioni di lieve entità (1-9 "
            "punti). Trascrizione tabellare in fase successiva."
        ),
    ),
    _SourceSeed(
        slug="it-mimit-2025-12-aggiornamento-macrolesioni",
        title=(
            "Decreto MIMIT 10 dicembre 2025 — aggiornamento importi danno "
            "biologico da lesioni di non lieve entità (art. 138 CAP)"
        ),
        citation="D.M. MIMIT 10 dicembre 2025",
        source_type=SourceType.MINISTRY_DECREE,
        official_url="https://www.mimit.gov.it/it/normativa/decreti-ministeriali",
        publication_date=date(2025, 12, 10),
        effective_date=None,
        reliability=Reliability.OFFICIAL,
        notes=(
            "Aggiornamento ISTAT degli importi della Tabella Unica "
            "Nazionale (macrolesioni). Da abbinare al D.P.R. 12/2025 "
            "tramite legame `supersedes`/versionamento in fase successiva."
        ),
    ),
    _SourceSeed(
        slug="it-dlgs-209-2005-cap-art-138-139",
        title=(
            "D.Lgs. 7 settembre 2005, n. 209 — Codice delle Assicurazioni "
            "Private, articoli 138 e 139"
        ),
        citation="D.Lgs. 209/2005, artt. 138-139",
        source_type=SourceType.OFFICIAL_LAW,
        official_url=(
            "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:"
            "decreto.legislativo:2005-09-07;209"
        ),
        publication_date=date(2005, 10, 13),
        effective_date=date(2006, 1, 1),
        reliability=Reliability.OFFICIAL,
        notes=(
            "Struttura giuridica del danno biologico in materia RCA. "
            "Cornice di abilitazione per i decreti attuativi MIMIT/TUN."
        ),
    ),
    _SourceSeed(
        slug="it-tabelle-milano-2024",
        title="Tabelle del Tribunale di Milano 2024 — danno non patrimoniale",
        citation="Tabelle Milano 2024",
        source_type=SourceType.COURT_TABLE,
        official_url="https://www.tribunale.milano.giustizia.it/",
        publication_date=date(2024, 4, 1),
        effective_date=None,
        # Le Tabelle Milano sono uno *standard giurisprudenziale*, non una
        # fonte ministeriale: reliability HIGH, non OFFICIAL.
        reliability=Reliability.HIGH,
        notes=(
            "Standard giurisprudenziale milanese per la liquidazione del "
            "danno non patrimoniale (biologico, morale, parentale). NON è "
            "fonte ministeriale né ha forza di legge: utile come "
            "orientamento ma non automaticamente vincolante. Da NON "
            "trattare come decreto."
        ),
    ),
]


class Command(BaseCommand):
    help = (
        "Crea i metadati delle fonti legali italiane core (status "
        "needs_review). Idempotente. NON inserisce importi tabellari."
    )

    def add_arguments(self, parser):
        parser.add_argument("--quiet", action="store_true", help="Sopprime l'output.")

    @transaction.atomic
    def handle(self, *args, **options):
        quiet = options["quiet"]

        country = self._get_or_create_italy()
        jurisdiction = self._get_or_create_italy_national(country)
        language = self._get_or_create_italian()

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
            # Lo status NON viene riscritto da defaults: lo gestiamo qui in
            # modo idempotente. Per nuovi record assegniamo lo status
            # iniziale del seed (NEEDS_REVIEW). Per record esistenti,
            # rispettiamo lo stato corrente — NON retrocediamo mai un
            # APPROVED a NEEDS_REVIEW per via di un re-seed.
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
                f"seed_italy_legal_sources completato: " f"{created} creati, {updated} aggiornati."
            )
        )

    # -- supporto idempotente per oggetti tassonomici (in caso il seed
    #    jurisdictions non sia ancora stato eseguito su questa istanza). --

    def _get_or_create_italy(self) -> Country:
        country, _ = Country.objects.get_or_create(
            code="IT",
            defaults={
                "code_alpha3": "ITA",
                "name": "Italia",
                "is_active": True,
            },
        )
        return country

    def _get_or_create_italy_national(self, country: Country) -> Jurisdiction:
        jurisdiction, _ = Jurisdiction.objects.get_or_create(
            code="IT-NATIONAL",
            defaults={
                "country": country,
                "name": "Italia (livello nazionale)",
                "legal_system": Jurisdiction.LegalSystem.CIVIL_LAW,
                "is_active": True,
            },
        )
        return jurisdiction

    def _get_or_create_italian(self) -> Language:
        language, _ = Language.objects.get_or_create(
            code="it",
            defaults={"name": "Italiano", "is_active": True},
        )
        return language
