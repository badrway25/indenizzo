"""
Download FR/BE/MA/TN legal sources to ``legal_data/sources/<country>/downloaded/``.

REGOLE ASSOLUTE:
- Nessun calcolo, nessuna formula, nessun dataset approved viene creato.
- Le ``LegalSource`` sono create/aggiornate in stato ``needs_review``.
  Una fonte già ``approved`` non viene mai retrocessa: il command
  aggiunge solo allegati e aggiorna i metadati neutri.
- I PDF/HTML scaricati sono materiale esterno: gitignore li esclude.
  Solo il manifest JSON resta committabile come traccia di audit.
- Il command non legge ``.env``, non fa deploy, non promuove status.

Uso:
    python manage.py download_international_legal_sources --country FR
    python manage.py download_international_legal_sources --country BE
    python manage.py download_international_legal_sources --country MA
    python manage.py download_international_legal_sources --country TN
    python manage.py download_international_legal_sources --all

Comportamento:
1. Per ogni item del package del paese richiesto:
   a. risolvi (Country, Jurisdiction, Language) — get_or_create idempotenti;
   b. mappa il ``source_type`` testuale del package alla enum del progetto
      (vedi ``_TYPE_MAP``);
   c. scarica l'URL con timeout, User-Agent custom, segui redirect;
   d. determina l'estensione da Content-Type (PDF / HTML / fallback bin);
   e. salva in ``legal_data/sources/<country>/downloaded/<slug>.<ext>``;
   f. calcola SHA-256 + size;
   g. upsert ``LegalSource`` (mai retrocede status APPROVED → NEEDS_REVIEW);
   h. per i PDF crea/aggiorna ``LegalSourceAttachment`` (l'HTML resta in
      filesystem + manifest, ma non come Attachment perché in genere è
      navigation page con JS e non è il documento normativo).
2. Scrive un manifest unificato per il paese:
   ``legal_data/sources/<country>/downloaded/download_manifest.json``.
3. Un fallimento di un singolo URL non interrompe il command: viene
   loggato in manifest con ``error`` non vuoto e si passa al successivo.
"""

from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
from apps.legal_sources.models import LegalSource, LegalSourceAttachment
from apps.legal_sources.utils import compute_bytes_sha256

USER_AGENT = "StudioLegaleBadrane-LegalSourceDownloader/0.1"
DOWNLOAD_TIMEOUT_SECONDS = 30
COUNTRY_FOLDER_BY_CODE: dict[str, str] = {
    "FR": "france",
    "BE": "belgium",
    "MA": "morocco",
    "TN": "tunisia",
}

# Mapping dei `source_type` usati nei package alla enum `SourceType`
# del progetto. Le voci che NON esistono nella enum vengono ricondotte
# a quelle più vicine (mai una `OFFICIAL_LAW` arbitraria — una
# capitalization_table è uno strumento giurisprudenziale, non una legge).
_TYPE_MAP: dict[str, str] = {
    "official_law": SourceType.OFFICIAL_LAW,
    "ministry_decree": SourceType.MINISTRY_DECREE,
    "court_table": SourceType.COURT_TABLE,
    "capitalization_table": SourceType.COURT_TABLE,
    "administrative_guideline": SourceType.ADMINISTRATIVE_GUIDELINE,
    "insurance_reference": SourceType.INSURANCE_REFERENCE,
    "doctrine": SourceType.DOCTRINE,
    "methodology": SourceType.DOCTRINE,
    "internal_legal_note": SourceType.INTERNAL_LEGAL_NOTE,
}

_RELIABILITY_MAP: dict[str, str] = {
    "official": Reliability.OFFICIAL,
    "high": Reliability.HIGH,
    "medium": Reliability.MEDIUM,
    "low": Reliability.LOW,
    "unknown": Reliability.UNKNOWN,
}


# ---------------------------------------------------------------------------
# Static packages (provided by the user). Source of truth for what to fetch.
# Adding/removing items here is the only way to change the download set.
# ---------------------------------------------------------------------------

FRANCE_PACKAGE: list[dict] = [
    {
        # Triage applied: Legifrance restituisce 403 sui client programmatici.
        # Manteniamo la fonte come metadata e marchiamo download manuale.
        "slug": "fr-loi-badinter-1985",
        "title": "Loi n°85-677 du 5 juillet 1985 dite Loi Badinter",
        "url": "https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000693454",
        "country": "FR",
        "jurisdiction": "FR-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "official",
        "status": "needs_review",
        "manual_download_required": True,
        "manual_reason": (
            "Legifrance returns HTTP 403 for non-browser User-Agents. "
            "Download the consolidated PDF from the browser and attach via "
            "Django admin (LegalSourceAttachment)."
        ),
    },
    {
        "slug": "fr-nomenclature-dintilhac-2005",
        "title": "Rapport Dintilhac — nomenclature des préjudices corporels",
        "url": (
            "https://www.justice.gouv.fr/documentation/ressources/"
            "elaboration-dune-nomenclature-prejudices-corporels"
        ),
        "country": "FR",
        "jurisdiction": "FR-NATIONAL",
        "language": "fr",
        "source_type": "methodology",
        "reliability": "official",
        "status": "needs_review",
    },
    {
        "slug": "fr-referentiel-mornet-2024",
        "title": "Référentiel Mornet 2024 — indemnisation des préjudices corporels",
        "url": (
            "https://www.hello-victimes.fr/app/download/8580040963/"
            "R%C3%A9f%C3%A9rentiel%2BMORNET%2B2024%2Bpdf.pdf?t=1759423951"
        ),
        "country": "FR",
        "jurisdiction": "FR-NATIONAL",
        "language": "fr",
        "source_type": "court_table",
        "reliability": "high",
        "status": "needs_review",
    },
    {
        "slug": "fr-bareme-capitalisation-gazette-palais-2022",
        "title": "Barème de capitalisation Gazette du Palais 2022",
        "url": (
            "https://www.labase-lextenso.fr/sites/lextenso/files/lextenso_upload/" "gpl441x1.pdf"
        ),
        "country": "FR",
        "jurisdiction": "FR-NATIONAL",
        "language": "fr",
        "source_type": "capitalization_table",
        "reliability": "high",
        "status": "needs_review",
    },
    {
        "slug": "fr-bareme-capitalisation-gazette-palais-2025-page",
        "title": "Barème de capitalisation Gazette du Palais 2025 — page officielle",
        "url": "https://lp.gazette-du-palais.fr/bareme-de-capitalisation",
        "country": "FR",
        "jurisdiction": "FR-NATIONAL",
        "language": "fr",
        "source_type": "capitalization_table",
        "reliability": "high",
        "status": "needs_review",
        # È una landing page con form: il PDF reale non è esposto pubblicamente.
        "classification_hint": "HTML_WARNING_NOT_FINAL_DOCUMENT",
    },
]

BELGIUM_PACKAGE: list[dict] = [
    {
        "slug": "be-loi-1989-11-21-rc-auto",
        "title": "Loi du 21 novembre 1989 — assurance obligatoire RC véhicules automoteurs",
        "url": "https://economie.fgov.be/en/legislation/law-21-november-1989",
        "country": "BE",
        "jurisdiction": "BE-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "official",
        "status": "needs_review",
    },
    {
        "slug": "be-tableau-indicatif-2024",
        "title": "Tableau Indicatif 2024 — dommages corporels",
        "url": "https://docs.fcgb-bgwf.be/documents/Tabl_Ind_2024_Fr.pdf",
        "country": "BE",
        "jurisdiction": "BE-NATIONAL",
        "language": "fr",
        "source_type": "court_table",
        "reliability": "high",
        "status": "needs_review",
    },
    {
        "slug": "be-tableau-indicatif-2020",
        "title": "Tableau Indicatif 2020 — dommages corporels",
        "url": "https://docs.fcgb-bgwf.be/documents/Tabl_Ind_2020_Fr.pdf",
        "country": "BE",
        "jurisdiction": "BE-NATIONAL",
        "language": "fr",
        "source_type": "court_table",
        "reliability": "high",
        "status": "needs_review",
    },
    {
        "slug": "be-tables-schryvers-2026-page",
        "title": "Tables Schryvers — tables de mortalité et de capitalisation prospectives belges",
        "url": "https://www.tafelsschryvers.be/?lang=fr",
        "country": "BE",
        "jurisdiction": "BE-NATIONAL",
        "language": "fr",
        "source_type": "capitalization_table",
        "reliability": "high",
        "status": "needs_review",
    },
    {
        "slug": "be-tables-schryvers-tableurs",
        "title": "Tables Schryvers — tableurs",
        "url": "https://www.tafelsschryvers.be/tableurs/?lang=fr",
        "country": "BE",
        "jurisdiction": "BE-NATIONAL",
        "language": "fr",
        "source_type": "capitalization_table",
        "reliability": "high",
        "status": "needs_review",
    },
]

MOROCCO_PACKAGE: list[dict] = [
    # Triage applied (iter1 → iter2):
    # - REMOVED `ma-code-famille-loi-70-03-dgct`: timeout su DGCT host +
    #   duplicato funzionale di `ma-code-famille-moudawana-fr-pdf` (PDF_OK).
    {
        "slug": "ma-code-famille-moudawana-fr-pdf",
        "title": "Code de la famille marocain / Moudawana — version française",
        "url": "https://www.legal-tools.org/doc/0e057b/pdf/",
        "country": "MA",
        "jurisdiction": "MA-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "high",
        "status": "needs_review",
    },
    {
        "slug": "ma-code-droits-reels-loi-39-08",
        "title": "Loi n°39-08 relative au Code des droits réels",
        "url": "https://faolex.fao.org/docs/pdf/mor225024.pdf",
        "country": "MA",
        "jurisdiction": "MA-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "high",
        "status": "needs_review",
    },
    {
        "slug": "ma-code-droits-reels-traduction-aute",
        "title": "Loi n°39-08 Code des droits réels — traduction",
        "url": "https://aute.gov.ma/s/a/library/2023-11-01/146a1724-a0bf-40ed-9169-973ffda26975.pdf",
        "country": "MA",
        "jurisdiction": "MA-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "medium",
        "status": "needs_review",
    },
    {
        # Triage applied: l'endpoint /TXT/PDF/ di EUR-Lex risponde 202 +
        # body vuoto (rendering PDF asincrono). Switch a /TXT/ HTML.
        "slug": "eu-regulation-650-2012-successions-fr-ma",
        "title": "Règlement UE n°650/2012 — successions transfrontalières",
        "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650",
        "country": "MA",
        "jurisdiction": "MA-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "official",
        "status": "needs_review",
    },
]

TUNISIA_PACKAGE: list[dict] = [
    # Triage applied (iter1 → iter2):
    # - REMOVED `tn-code-dip-pdf-support`: ConnectionRefused su marouani-
    #   avocat.com + duplicato funzionale di `tn-code-dip-loi-98-97`.
    # - `tn-jort-code-statut-personnel-1956` → manual_download_required
    #   (`pist.tn` non raggiungibile dal datacenter; nessuna URL JORT
    #   ufficiale stabile identificata).
    # - `tn-code-statut-personnel-compiled` → manual_download_required
    #   (jafbase.fr ha SSL hostname mismatch; nessun mirror ufficiale TN
    #   verificato come stabile).
    # - EUR-Lex switch a /TXT/ HTML (vedi commento MA).
    {
        "slug": "tn-jort-code-statut-personnel-1956",
        "title": "JORT 1956 — Code du statut personnel tunisien",
        "url": "https://www.pist.tn/jort/1956/1956F/Jo10456.pdf",
        "country": "TN",
        "jurisdiction": "TN-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "official",
        "status": "needs_review",
        "manual_download_required": True,
        "manual_reason": (
            "pist.tn host non raggiungibile dal datacenter (ConnectTimeout). "
            "Nessuna URL JORT alternativa ufficiale identificata come stabile. "
            "Scaricare il fascicolo JORT 1956 da pist.tn o IORT.gov.tn da "
            "browser e attaccare via Django admin."
        ),
    },
    {
        "slug": "tn-code-statut-personnel-compiled",
        "title": "Code du statut personnel tunisien — version compilée",
        "url": "https://jafbase.fr/docMaghreb/TunisieStatutpersonnel.PDF",
        "country": "TN",
        "jurisdiction": "TN-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "high",
        "status": "needs_review",
        "manual_download_required": True,
        "manual_reason": (
            "jafbase.fr presenta SSL hostname mismatch. "
            "Nessun mirror ufficiale TN verificato come stabile. "
            "Per lo scope successioni `tn-code-statut-personnel-livre-ix-"
            "succession` (HTML scaricato) copre il Livre IX. "
            "Scaricare la versione consolidata completa da legislation.tn "
            "(o iort.gov.tn) da browser e attaccare via Django admin se "
            "serve la copertura completa."
        ),
    },
    {
        "slug": "tn-code-statut-personnel-livre-ix-succession",
        "title": "Code du statut personnel — Livre IX De la succession",
        "url": "https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1100.htm",
        "country": "TN",
        "jurisdiction": "TN-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "high",
        "status": "needs_review",
    },
    {
        "slug": "tn-code-dip-loi-98-97",
        "title": "Loi n°98-97 du 27 novembre 1998 portant Code de droit international privé",
        "url": (
            "https://legislation-securite.tn/latest-laws/"
            "loi-n-98-97-du-27-novembre-1998-portant-promulgation-du-"
            "code-de-droit-international-prive/"
        ),
        "country": "TN",
        "jurisdiction": "TN-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "official",
        "status": "needs_review",
    },
    {
        # Triage applied: switch a /TXT/ HTML, vedi commento MA.
        "slug": "eu-regulation-650-2012-successions-fr-tn",
        "title": "Règlement UE n°650/2012 — successions transfrontalières",
        "url": "https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650",
        "country": "TN",
        "jurisdiction": "TN-NATIONAL",
        "language": "fr",
        "source_type": "official_law",
        "reliability": "official",
        "status": "needs_review",
    },
]

PACKAGES: dict[str, list[dict[str, str]]] = {
    "FR": FRANCE_PACKAGE,
    "BE": BELGIUM_PACKAGE,
    "MA": MOROCCO_PACKAGE,
    "TN": TUNISIA_PACKAGE,
}


# ---------------------------------------------------------------------------
# HTTP fetch — abstracted via a function that the tests mock with a fake.
# ---------------------------------------------------------------------------


@dataclass
class FetchResult:
    final_url: str
    http_status: int
    content_type: str
    payload: bytes


def _fetch(url: str, *, timeout: int = DOWNLOAD_TIMEOUT_SECONDS) -> FetchResult:
    """Fetch a URL, follow redirects, return body + headers.

    Raises requests.RequestException on network/timeout/HTTP errors. The
    caller catches it and records an entry in the manifest with ``error``
    non-vuoto.
    """
    response = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    response.raise_for_status()
    return FetchResult(
        final_url=response.url,
        http_status=response.status_code,
        content_type=(response.headers.get("Content-Type") or "").split(";")[0].strip(),
        payload=response.content,
    )


def _extension_for(content_type: str, url: str) -> str:
    """Map a Content-Type header to a file extension. Falls back to URL hint."""
    ct = (content_type or "").lower()
    if "pdf" in ct or url.lower().endswith(".pdf"):
        return "pdf"
    if "html" in ct or "xhtml" in ct:
        return "html"
    # Fallback: try mimetypes from URL.
    guess, _ = mimetypes.guess_type(url)
    if guess and "pdf" in guess:
        return "pdf"
    if guess and "html" in guess:
        return "html"
    return "bin"


# ---------------------------------------------------------------------------
# Idempotent helpers for taxonomy objects.
# ---------------------------------------------------------------------------


def _resolve_country(code: str) -> Country:
    country, _ = Country.objects.get_or_create(
        code=code.upper(),
        defaults={"name": code.upper(), "is_active": True},
    )
    return country


def _resolve_jurisdiction(country: Country, code: str) -> Jurisdiction:
    juris, _ = Jurisdiction.objects.get_or_create(
        code=code,
        defaults={
            "country": country,
            "name": code,
            "legal_system": Jurisdiction.LegalSystem.CIVIL_LAW,
            "is_active": True,
        },
    )
    return juris


def _resolve_language(code: str) -> Language:
    name_map = {"fr": "Français", "it": "Italiano", "en": "English", "ar": "العربية"}
    lang, _ = Language.objects.get_or_create(
        code=code.lower(),
        defaults={"name": name_map.get(code.lower(), code), "is_active": True},
    )
    return lang


# ---------------------------------------------------------------------------
# Main command
# ---------------------------------------------------------------------------


@dataclass
class _ManifestEntry:
    slug: str
    title: str
    source_url: str
    final_url: str = ""
    http_status: int | None = None
    content_type: str = ""
    local_path: str = ""
    sha256: str = ""
    size_bytes: int = 0
    downloaded_at: str = ""
    country: str = ""
    jurisdiction: str = ""
    language: str = ""
    source_type: str = ""
    reliability: str = ""
    status: str = ""
    notes: str = ""
    error: str = ""
    classification: str = ""
    manual_download_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "title": self.title,
            "source_url": self.source_url,
            "final_url": self.final_url,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "local_path": self.local_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "downloaded_at": self.downloaded_at,
            "country": self.country,
            "jurisdiction": self.jurisdiction,
            "language": self.language,
            "source_type": self.source_type,
            "reliability": self.reliability,
            "status": self.status,
            "notes": self.notes,
            "error": self.error,
            "classification": self.classification,
            "manual_download_required": self.manual_download_required,
        }


def _classify_entry(entry: _ManifestEntry, *, ext: str, hint: str | None) -> str:
    """Compute the classification tag for the manifest entry.

    Order of precedence:
    1. manual_download_required → MANUAL_DOWNLOAD_REQUIRED
    2. error not empty → FAILED_NEEDS_REPLACEMENT_URL
    3. http_status == 202 → HTTP_202_WARNING
    4. classification_hint dal package (es. HTML_WARNING_NOT_FINAL_DOCUMENT)
    5. ext == "pdf" → PDF_OK
    6. ext == "html" → HTML_OK_SOURCE_PAGE
    7. fallback → BIN_OK
    """
    if entry.manual_download_required:
        return "MANUAL_DOWNLOAD_REQUIRED"
    if entry.error:
        return "FAILED_NEEDS_REPLACEMENT_URL"
    if entry.http_status == 202:
        return "HTTP_202_WARNING"
    if hint:
        return hint
    if ext == "pdf":
        return "PDF_OK"
    if ext == "html":
        return "HTML_OK_SOURCE_PAGE"
    return "BIN_OK"


@dataclass
class _CountrySummary:
    country: str
    items: list[_ManifestEntry] = field(default_factory=list)

    @property
    def succeeded(self) -> int:
        return sum(1 for i in self.items if not i.error and not i.manual_download_required)

    @property
    def failed(self) -> int:
        return sum(1 for i in self.items if i.error)

    @property
    def manual_required(self) -> int:
        return sum(1 for i in self.items if i.manual_download_required)


class Command(BaseCommand):
    help = (
        "Scarica i pacchetti di fonti legali FR/BE/MA/TN nelle cartelle "
        "legal_data/sources/<country>/downloaded/ e crea/aggiorna le "
        "LegalSource corrispondenti in stato needs_review. NON approva "
        "nulla, NON crea formule o dataset di calcolo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--country",
            choices=sorted(PACKAGES.keys()),
            help="Country code (FR, BE, MA, TN). Mutually exclusive with --all.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            help="Download all 4 packages (FR, BE, MA, TN).",
        )

    def handle(self, *args, **options):
        country = options.get("country")
        do_all = options.get("all")
        if not country and not do_all:
            raise CommandError("Specify --country <FR|BE|MA|TN> or --all.")
        if country and do_all:
            raise CommandError("--country and --all are mutually exclusive.")

        codes = list(PACKAGES.keys()) if do_all else [country]
        for code in codes:
            self._handle_country(code)

    # ------------------------------------------------------------------
    # Per-country pipeline
    # ------------------------------------------------------------------

    def _handle_country(self, code: str) -> None:
        package = PACKAGES[code]
        folder_name = COUNTRY_FOLDER_BY_CODE[code]
        base_dir = Path(settings.BASE_DIR) / "legal_data" / "sources" / folder_name / "downloaded"
        base_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(f"\n=== Country {code}: {len(package)} item(s) ===")
        summary = _CountrySummary(country=code)
        for item in package:
            entry = self._handle_item(item, base_dir=base_dir)
            summary.items.append(entry)
            if entry.manual_download_required:
                mark = "MANUAL"
            elif entry.error:
                mark = "FAIL"
            else:
                mark = "OK"
            self.stdout.write(
                f"  [{mark:>6}] {entry.slug} class={entry.classification:>32} "
                f"http={entry.http_status} type={entry.content_type or '?'} "
                f"-> {entry.local_path or '(no file)'}"
            )

        # Manifest persisted regardless of partial failures.
        manifest_path = base_dir / "download_manifest.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "country": code,
                    "generated_at": datetime.now(UTC).isoformat(),
                    "user_agent": USER_AGENT,
                    "succeeded": summary.succeeded,
                    "failed": summary.failed,
                    "manual_required": summary.manual_required,
                    "items": [e.to_dict() for e in summary.items],
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"  manifest -> {manifest_path} "
                f"(ok={summary.succeeded} fail={summary.failed} "
                f"manual={summary.manual_required})"
            )
        )

    def _handle_item(self, item: dict, *, base_dir: Path) -> _ManifestEntry:
        manual_required = bool(item.get("manual_download_required"))
        manual_reason = item.get("manual_reason", "")
        hint = item.get("classification_hint")

        if manual_required:
            base_notes = (
                "Manual download required: "
                + (manual_reason or "URL not reachable from datacenter.")
                + " Upload via Django admin once retrieved. "
                "Requires Studio legal review before any calculation."
            )
        else:
            base_notes = (
                "Downloaded metadata only. Requires Studio legal review before " "any calculation."
            )

        entry = _ManifestEntry(
            slug=item["slug"],
            title=item["title"],
            source_url=item["url"],
            country=item["country"],
            jurisdiction=item["jurisdiction"],
            language=item["language"],
            source_type=_TYPE_MAP.get(item["source_type"], item["source_type"]),
            reliability=_RELIABILITY_MAP.get(item["reliability"], item["reliability"]),
            status=SourceStatus.NEEDS_REVIEW,
            notes=base_notes,
            manual_download_required=manual_required,
        )

        # Manual path: no fetch, no file, but still create a LegalSource so
        # the metadata is present and the Studio can attach the file via admin.
        if manual_required:
            entry.downloaded_at = datetime.now(UTC).isoformat()
            try:
                self._upsert_legal_source(item, entry, payload=b"", ext="")
            except Exception as exc:  # noqa: BLE001
                entry.error = f"db_upsert_failed: {exc.__class__.__name__}: {exc}"
            entry.classification = _classify_entry(entry, ext="", hint=None)
            return entry

        # 1. Fetch
        try:
            fetched = _fetch(item["url"])
        except requests.RequestException as exc:
            entry.error = f"fetch_failed: {exc.__class__.__name__}: {exc}"
            entry.classification = _classify_entry(entry, ext="", hint=None)
            return entry

        entry.final_url = fetched.final_url
        entry.http_status = fetched.http_status
        entry.content_type = fetched.content_type

        # 2. Persist file
        ext = _extension_for(fetched.content_type, item["url"])
        local_path = base_dir / f"{item['slug']}.{ext}"
        try:
            local_path.write_bytes(fetched.payload)
        except OSError as exc:
            entry.error = f"write_failed: {exc.__class__.__name__}: {exc}"
            entry.classification = _classify_entry(entry, ext=ext, hint=hint)
            return entry

        entry.local_path = str(local_path.relative_to(Path(settings.BASE_DIR)))
        entry.sha256 = compute_bytes_sha256(fetched.payload)
        entry.size_bytes = len(fetched.payload)
        entry.downloaded_at = datetime.now(UTC).isoformat()

        # 3. Upsert LegalSource + (PDF only) Attachment
        try:
            self._upsert_legal_source(item, entry, payload=fetched.payload, ext=ext)
        except Exception as exc:  # noqa: BLE001 — defensive: log and continue
            entry.error = f"db_upsert_failed: {exc.__class__.__name__}: {exc}"

        entry.classification = _classify_entry(entry, ext=ext, hint=hint)
        return entry

    @transaction.atomic
    def _upsert_legal_source(
        self,
        item: dict[str, str],
        entry: _ManifestEntry,
        *,
        payload: bytes,
        ext: str,
    ) -> None:
        country = _resolve_country(item["country"])
        jurisdiction = _resolve_jurisdiction(country, item["jurisdiction"])
        language = _resolve_language(item["language"])

        defaults: dict[str, Any] = {
            "title": item["title"],
            "country": country,
            "jurisdiction": jurisdiction,
            "language": language,
            "source_type": entry.source_type,
            "reliability": entry.reliability,
            "official_url": item["url"],
            "notes": entry.notes,
        }
        source, created = LegalSource.objects.get_or_create(slug=item["slug"], defaults=defaults)
        if not created:
            # Update neutral metadata, NEVER touch status/legal_reviewer.
            updated_fields: list[str] = []
            for f in ("title", "official_url", "source_type", "reliability"):
                if getattr(source, f) != defaults[f]:
                    setattr(source, f, defaults[f])
                    updated_fields.append(f)
            # Lazy-fill missing language/jurisdiction without overwriting.
            if not source.jurisdiction_id:
                source.jurisdiction = jurisdiction
                updated_fields.append("jurisdiction")
            if not source.language_id:
                source.language = language
                updated_fields.append("language")
            if updated_fields:
                source.save(update_fields=updated_fields + ["updated_at"])

        # Initial status only for NEW sources. Existing sources keep their
        # current status (in particular: never downgrade APPROVED).
        if created:
            source.status = SourceStatus.NEEDS_REVIEW
            source.save(update_fields=["status"])

        # Attachment only for PDF binaries. HTML pages are navigation
        # artefacts (often JS-heavy SPAs) and are kept on disk + manifest
        # for audit, but not as Attachment.
        if ext == "pdf":
            existing = source.attachments.filter(sha256=entry.sha256).first()
            if existing is None:
                LegalSourceAttachment.objects.create(
                    source=source,
                    file=ContentFile(payload, name=f"{item['slug']}.pdf"),
                    original_filename=f"{item['slug']}.pdf",
                    mime_type=entry.content_type or "application/pdf",
                    description=(
                        f"Downloaded via download_international_legal_sources from "
                        f"{item['url']}"
                    ),
                )
