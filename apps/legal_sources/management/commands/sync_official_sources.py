"""
Sync ufficiale: legge ``config/official_source_registry.json`` e per
ogni entry con ``can_auto_ingest=true`` annota la sincronizzazione
nel filesystem (manifest + sha256) e nel DB (campo ``LegalSource.notes``).

REGOLE ASSOLUTE (iter F-product-official-source-automation-and-full-site-functional-upgrade):

- **Mai** crea ``LegalReview``.
- **Mai** crea ``CompensationDataset`` / ``CalculationFormula`` /
  ``CompensationTableRow``.
- **Mai** retrocede ``LegalSource.status`` da ``APPROVED``.
- **Mai** estende l'enum ``SourceStatus`` (no migrazione distruttiva).
  L'evento "official_synced" resta nel manifest JSON + ``notes`` con
  un trailer machine-readable strutturato.
- **Mai** scarica fonti con ``can_auto_ingest=false``: sono in scope
  ``human_exception_review`` permanente.
- I file scaricati vanno in ``legal_data/sources/<country>/official_downloaded/``
  (cartella separata da ``downloaded/`` di
  ``download_international_legal_sources``).

Uso:

    python manage.py sync_official_sources
    python manage.py sync_official_sources --slug eu-regulation-650-2012-successions
    python manage.py sync_official_sources --metadata-only
    python manage.py sync_official_sources --dry-run

In modalità ``--metadata-only`` non viene fatto nessun GET HTTP: si
annota solo la presenza della fonte nel registry, si scrive il manifest
e si aggiorna ``LegalSource.notes`` (utile in CI / test offline).

In modalità ``--dry-run`` non si scrive nulla né su disco né su DB:
serve a validare il registro e mostrare il piano.

Output:

- ``legal_data/sources/<country>/official_downloaded/<slug>.<ext>`` per
  ogni download riuscito;
- ``legal_data/sources/<country>/official_downloaded/official_sync_manifest.json``
  con la lista di tutte le sync della run;
- ``LegalSource.notes`` annotato con un blocco delimitato:
  ``[official_sync] iso_timestamp=…  sha256=…  manifest=…  registry_entry=…``.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
from apps.legal_sources.models import LegalSource
from apps.legal_sources.utils import compute_bytes_sha256

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_REGISTRY_PATH = Path(settings.BASE_DIR) / "config" / "official_source_registry.json"
USER_AGENT = "StudioLegaleBadrane-OfficialSourceSync/0.1"
DOWNLOAD_TIMEOUT_SECONDS = 30
COUNTRY_FOLDER_BY_CODE: dict[str, str] = {
    "IT": "italy",
    "FR": "france",
    "BE": "belgium",
    "MA": "morocco",
    "TN": "tunisia",
    "EU": "eu",
}

NOTES_MARKER_BEGIN = "[official_sync] BEGIN"
NOTES_MARKER_END = "[official_sync] END"


@dataclass
class SyncResult:
    slug: str
    country: str
    jurisdiction: str
    case_type: str
    source_kind: str
    authority: str
    can_auto_ingest: bool
    human_exception_review_required: bool
    ingest_mode: str
    official_url: str
    final_url: str = ""
    http_status: int | None = None
    sha256: str = ""
    size_bytes: int = 0
    local_path: str = ""
    synced_at: str = ""
    legal_source_id: int | None = None
    legal_source_status_before: str = ""
    legal_source_status_after: str = ""
    note_appended: bool = False
    error: str = ""
    skipped_reason: str = ""
    classification: str = ""
    fetched_at: str = ""


@dataclass
class RunManifest:
    schema_version: str
    iter: str
    started_at: str
    finished_at: str = ""
    dry_run: bool = False
    metadata_only: bool = False
    slug_filter: str | None = None
    results: list[SyncResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Registry validation
# ---------------------------------------------------------------------------

REQUIRED_KEYS = {
    "country",
    "jurisdiction",
    "case_type",
    "source_slug",
    "title",
    "official_url",
    "source_kind",
    "authority",
    "machine_readable",
    "expected_format",
    "can_auto_ingest",
    "human_exception_review_required",
}
ALLOWED_SOURCE_KINDS = {
    "official_law",
    "official_decree",
    "official_table",
    "eu_regulation",
    "official_guidance",
    "court_indicative_table",
    "private_bareme",
}
ALLOWED_FORMATS = {"pdf", "html", "csv", "json", "xml"}


def validate_registry(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if "schema_version" not in payload:
        errors.append("registry: missing schema_version")
    entries = payload.get("entries")
    if not isinstance(entries, list):
        errors.append("registry: entries must be a list")
        return errors
    seen_slugs: set[str] = set()
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry {idx}: not an object")
            continue
        for key in REQUIRED_KEYS:
            if key not in entry:
                errors.append(f"entry {idx} ({entry.get('source_slug', '?')}): missing {key}")
        slug = entry.get("source_slug")
        if slug:
            if slug in seen_slugs:
                errors.append(f"entry {idx}: duplicate slug {slug!r}")
            seen_slugs.add(slug)
        kind = entry.get("source_kind")
        if kind and kind not in ALLOWED_SOURCE_KINDS:
            errors.append(
                f"entry {idx} ({slug}): source_kind={kind!r} not in {sorted(ALLOWED_SOURCE_KINDS)}"
            )
        fmt = entry.get("expected_format")
        if fmt and fmt not in ALLOWED_FORMATS:
            errors.append(
                f"entry {idx} ({slug}): expected_format={fmt!r} not in {sorted(ALLOWED_FORMATS)}"
            )
        if (
            entry.get("can_auto_ingest") is True
            and entry.get("human_exception_review_required") is True
        ):
            errors.append(
                f"entry {idx} ({slug}): can_auto_ingest and human_exception_review_required "
                "are mutually exclusive"
            )
        if entry.get("can_auto_ingest") is False and not entry.get(
            "human_exception_review_required"
        ):
            errors.append(
                f"entry {idx} ({slug}): can_auto_ingest=false requires "
                "human_exception_review_required=true"
            )
    return errors


# ---------------------------------------------------------------------------
# HTTP fetch (mockable in tests)
# ---------------------------------------------------------------------------


def _fetch(url: str, *, timeout: int = DOWNLOAD_TIMEOUT_SECONDS) -> tuple[str, int, str, bytes]:
    response = requests.get(
        url,
        timeout=timeout,
        allow_redirects=True,
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
    )
    response.raise_for_status()
    return (
        response.url,
        response.status_code,
        (response.headers.get("Content-Type") or "").split(";")[0].strip(),
        response.content,
    )


# ---------------------------------------------------------------------------
# Notes helper — embeds an "[official_sync]" trailer in LegalSource.notes
# without losing existing free text.
# ---------------------------------------------------------------------------


def _strip_existing_marker(notes: str) -> str:
    if NOTES_MARKER_BEGIN not in notes:
        return notes.rstrip()
    head, _, rest = notes.partition(NOTES_MARKER_BEGIN)
    _, _, tail = rest.partition(NOTES_MARKER_END)
    return (head.rstrip() + "\n" + tail.lstrip()).strip()


def build_notes_block(result: SyncResult) -> str:
    body = json.dumps(
        {
            "synced_at": result.synced_at,
            "fetched_at": result.fetched_at,
            "registry_slug": result.slug,
            "official_url": result.official_url,
            "final_url": result.final_url,
            "http_status": result.http_status,
            "sha256": result.sha256,
            "size_bytes": result.size_bytes,
            "local_path": result.local_path,
            "ingest_mode": result.ingest_mode,
            "classification": result.classification,
            "source_kind": result.source_kind,
            "authority": result.authority,
            "can_auto_ingest": result.can_auto_ingest,
            "no_calculator_activation": True,
            "error": result.error,
        },
        ensure_ascii=False,
        indent=2,
    )
    return f"\n\n{NOTES_MARKER_BEGIN}\n{body}\n{NOTES_MARKER_END}\n"


# ---------------------------------------------------------------------------
# Idempotent helpers (taxonomy)
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


def _resolve_language_code_for(country_code: str) -> str:
    return {"IT": "it", "FR": "fr", "BE": "fr", "MA": "fr", "TN": "fr", "EU": "fr"}.get(
        country_code.upper(), "en"
    )


def _resolve_language(code: str) -> Language:
    name_map = {"fr": "Français", "it": "Italiano", "en": "English", "ar": "العربية"}
    lang, _ = Language.objects.get_or_create(
        code=code.lower(),
        defaults={"name": name_map.get(code.lower(), code), "is_active": True},
    )
    return lang


# ---------------------------------------------------------------------------
# Source-type mapping (registry → DB enum)
# ---------------------------------------------------------------------------

_KIND_TO_SOURCE_TYPE: dict[str, str] = {
    "official_law": SourceType.OFFICIAL_LAW,
    "official_decree": SourceType.MINISTRY_DECREE,
    "official_table": SourceType.MINISTRY_DECREE,
    "eu_regulation": SourceType.OFFICIAL_LAW,
    "official_guidance": SourceType.ADMINISTRATIVE_GUIDELINE,
    "court_indicative_table": SourceType.COURT_TABLE,
    "private_bareme": SourceType.DOCTRINE,
}
_KIND_TO_RELIABILITY: dict[str, str] = {
    "official_law": Reliability.OFFICIAL,
    "official_decree": Reliability.OFFICIAL,
    "official_table": Reliability.OFFICIAL,
    "eu_regulation": Reliability.OFFICIAL,
    "official_guidance": Reliability.OFFICIAL,
    "court_indicative_table": Reliability.HIGH,
    "private_bareme": Reliability.MEDIUM,
}


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Sincronizza le fonti ufficiali dal registro "
        "config/official_source_registry.json. NON crea LegalReview, "
        "dataset, formule. Annota LegalSource.notes con un trailer "
        "[official_sync] machine-readable."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--registry",
            default=str(DEFAULT_REGISTRY_PATH),
            help="Path al registry JSON (default config/official_source_registry.json).",
        )
        parser.add_argument(
            "--slug",
            help="Sincronizza solo l'entry con questo source_slug.",
        )
        parser.add_argument(
            "--country",
            help="Filtra entry per ISO country code (es. MA, FR, IT, EU).",
        )
        parser.add_argument(
            "--metadata-only",
            action="store_true",
            help="Skip HTTP GET. Annota solo la presenza nel registry + manifest.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida il registry e stampa il piano senza scrivere nulla.",
        )
        parser.add_argument(
            "--include-review-required",
            action="store_true",
            help="Includi anche entry con can_auto_ingest=false (per audit).",
        )

    def handle(self, *args, **options):
        registry_path = Path(options["registry"]).resolve()
        slug_filter: str | None = options.get("slug")
        country_filter: str | None = options.get("country")
        metadata_only: bool = bool(options.get("metadata_only"))
        dry_run: bool = bool(options.get("dry_run"))
        include_review: bool = bool(options.get("include_review_required"))

        if not registry_path.exists():
            raise CommandError(f"Registry not found: {registry_path}")

        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        errors = validate_registry(payload)
        if errors:
            self.stdout.write(self.style.ERROR("Registry validation failed:"))
            for err in errors:
                self.stdout.write(f"  - {err}")
            raise CommandError("Aborting: registry has schema/data errors.")

        run = RunManifest(
            schema_version=payload.get("schema_version", "1.0"),
            iter=payload.get("iter", ""),
            started_at=datetime.now(UTC).isoformat(),
            dry_run=dry_run,
            metadata_only=metadata_only,
            slug_filter=slug_filter,
        )

        candidates = []
        for entry in payload["entries"]:
            if slug_filter and entry["source_slug"] != slug_filter:
                continue
            if country_filter and entry["country"].upper() != country_filter.upper():
                continue
            if not entry["can_auto_ingest"] and not include_review:
                continue
            candidates.append(entry)

        if not candidates:
            self.stdout.write(
                self.style.WARNING(
                    "No registry entries match the selection. "
                    "Use --include-review-required to inspect human_exception entries."
                )
            )

        for entry in candidates:
            result = self._handle_entry(
                entry,
                metadata_only=metadata_only,
                dry_run=dry_run,
            )
            run.results.append(result)
            mark = "OK"
            if result.skipped_reason:
                mark = "SKIP"
            elif result.error:
                mark = "FAIL"
            self.stdout.write(
                f"  [{mark:>4}] {result.slug}  http={result.http_status} "
                f"sha256={result.sha256[:12] or '—':<12} "
                f"-> {result.local_path or '(metadata-only)'}"
            )

        run.finished_at = datetime.now(UTC).isoformat()

        # Manifest globale: per ogni country interessato scriviamo un
        # file dedicato. Lo facciamo solo fuori dry-run.
        if not dry_run:
            self._write_manifests(run)

        self.stdout.write(
            self.style.SUCCESS(
                f"sync_official_sources done. candidates={len(candidates)} "
                f"results={len(run.results)} dry_run={dry_run} metadata_only={metadata_only}"
            )
        )

    # ------------------------------------------------------------------
    # Entry pipeline
    # ------------------------------------------------------------------

    def _handle_entry(
        self,
        entry: dict[str, Any],
        *,
        metadata_only: bool,
        dry_run: bool,
    ) -> SyncResult:
        result = SyncResult(
            slug=entry["source_slug"],
            country=entry["country"],
            jurisdiction=entry["jurisdiction"],
            case_type=entry["case_type"],
            source_kind=entry["source_kind"],
            authority=entry["authority"],
            can_auto_ingest=entry["can_auto_ingest"],
            human_exception_review_required=entry["human_exception_review_required"],
            ingest_mode=entry.get("ingest_mode", "metadata_only"),
            official_url=entry["official_url"],
            synced_at=datetime.now(UTC).isoformat(),
        )

        # Decision tree:
        # - human_exception_review_required → record but never download
        # - ingest_mode == "manual_attach"/"human_exception_only" → record only
        # - metadata_only flag → skip HTTP, just write notes
        # - ingest_mode == "metadata_only" → skip HTTP, just write notes
        # - else (ingest_mode == "fetch" or absent and can_auto_ingest=true) → fetch
        if result.human_exception_review_required or result.ingest_mode in {
            "manual_attach",
            "human_exception_only",
        }:
            result.skipped_reason = "human_exception_review or manual_attach"
            result.classification = "human_exception_only"
        elif metadata_only or result.ingest_mode == "metadata_only":
            result.skipped_reason = "metadata_only"
            result.classification = "metadata_only"

        # Try HTTP only if not skipped.
        payload_bytes: bytes = b""
        ext = entry.get("expected_format", "bin")
        if not result.skipped_reason and not dry_run:
            try:
                final_url, status, content_type, payload_bytes = _fetch(result.official_url)
                result.final_url = final_url
                result.http_status = status
                result.sha256 = compute_bytes_sha256(payload_bytes)
                result.size_bytes = len(payload_bytes)
                ext = self._extension_for(content_type, result.official_url, ext)
                result.fetched_at = datetime.now(UTC).isoformat()
                result.classification = "fetch_success"
            except requests.RequestException as exc:
                result.error = f"fetch_failed: {exc.__class__.__name__}: {exc}"
                result.classification = "fetch_failed"

        # Persist file when we have payload.
        if payload_bytes and not dry_run and not result.error:
            folder = COUNTRY_FOLDER_BY_CODE.get(result.country.upper(), result.country.lower())
            base_dir = (
                Path(settings.BASE_DIR) / "legal_data" / "sources" / folder / "official_downloaded"
            )
            try:
                base_dir.mkdir(parents=True, exist_ok=True)
                local_path = base_dir / f"{result.slug}.{ext}"
                local_path.write_bytes(payload_bytes)
                result.local_path = str(local_path.relative_to(Path(settings.BASE_DIR)))
            except OSError as exc:
                result.error = f"write_failed: {exc.__class__.__name__}: {exc}"

        # Upsert LegalSource + annotate notes (DB step).
        if not dry_run:
            try:
                self._upsert_and_annotate(entry, result)
            except Exception as exc:  # noqa: BLE001 — defensive
                result.error = (
                    f"db_upsert_failed: {exc.__class__.__name__}: {exc}"
                    if not result.error
                    else result.error
                )

        return result

    def _extension_for(self, content_type: str, url: str, fallback: str) -> str:
        ct = (content_type or "").lower()
        if "pdf" in ct or url.lower().endswith(".pdf"):
            return "pdf"
        if "html" in ct or "xhtml" in ct:
            return "html"
        if "json" in ct:
            return "json"
        if "xml" in ct:
            return "xml"
        return fallback or "bin"

    @transaction.atomic
    def _upsert_and_annotate(self, entry: dict[str, Any], result: SyncResult) -> None:
        country = _resolve_country(result.country)
        jurisdiction = _resolve_jurisdiction(country, result.jurisdiction)
        language = _resolve_language(_resolve_language_code_for(result.country))
        source_type = _KIND_TO_SOURCE_TYPE.get(result.source_kind, SourceType.OFFICIAL_LAW)
        reliability = _KIND_TO_RELIABILITY.get(result.source_kind, Reliability.HIGH)

        defaults = {
            "title": entry["title"],
            "country": country,
            "jurisdiction": jurisdiction,
            "language": language,
            "source_type": source_type,
            "reliability": reliability,
            "official_url": entry["official_url"],
        }
        source, created = LegalSource.objects.get_or_create(
            slug=result.slug,
            defaults={**defaults, "notes": ""},
        )
        result.legal_source_id = source.pk
        result.legal_source_status_before = source.status

        # Lazy backfill: aggiorniamo solo metadati neutri (mai status né
        # legal_reviewer). Una fonte già APPROVED non viene retrocessa.
        if not created:
            updated_fields: list[str] = []
            for key in ("title", "official_url", "source_type", "reliability"):
                if getattr(source, key) != defaults[key]:
                    setattr(source, key, defaults[key])
                    updated_fields.append(key)
            if not source.jurisdiction_id:
                source.jurisdiction = jurisdiction
                updated_fields.append("jurisdiction")
            if not source.language_id:
                source.language = language
                updated_fields.append("language")
            if updated_fields:
                source.save(update_fields=updated_fields + ["updated_at"])

        if created:
            # Per le fonti nuove fissiamo lo status iniziale a NEEDS_REVIEW.
            # Il sync ufficiale **non** promuove APPROVED: serve sempre
            # uno step Studio (LegalReview) o fixture dataset/formula
            # gia` validate (caso TUN 2025).
            source.status = SourceStatus.NEEDS_REVIEW
            source.save(update_fields=["status"])

        # Notes annotation.
        new_notes = _strip_existing_marker(source.notes or "") + build_notes_block(result)
        if source.notes != new_notes:
            source.notes = new_notes
            source.save(update_fields=["notes", "updated_at"])
            result.note_appended = True

        result.legal_source_status_after = source.status

    # ------------------------------------------------------------------
    # Manifest writers
    # ------------------------------------------------------------------

    def _write_manifests(self, run: RunManifest) -> None:
        # Per ogni paese coinvolto scriviamo un manifest cumulativo.
        per_country: dict[str, list[SyncResult]] = {}
        for r in run.results:
            per_country.setdefault(r.country, []).append(r)

        for country_code, results in per_country.items():
            folder = COUNTRY_FOLDER_BY_CODE.get(country_code.upper(), country_code.lower())
            base_dir = (
                Path(settings.BASE_DIR) / "legal_data" / "sources" / folder / "official_downloaded"
            )
            base_dir.mkdir(parents=True, exist_ok=True)
            manifest_path = base_dir / "official_sync_manifest.json"
            manifest = {
                "schema_version": run.schema_version,
                "iter": run.iter,
                "country": country_code,
                "generated_at": run.finished_at,
                "started_at": run.started_at,
                "dry_run": run.dry_run,
                "metadata_only": run.metadata_only,
                "slug_filter": run.slug_filter,
                "results": [asdict(r) for r in results],
            }
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.stdout.write(self.style.SUCCESS(f"  manifest -> {manifest_path}"))
