"""Manual-attach pipeline for official sources blocked by HTTP fetch.

Some official authorities reject programmatic clients (HTTP 403, JS-only
SPA, anti-bot WAF, TLS strictness). For those entries the registry sets
``ingest_mode="manual_attach"`` + ``manual_attach_allowed=true`` and the
Studio operator runs::

    python manage.py attach_official_source_file \\
        --slug fr-loi-badinter-1985 \\
        --file C:/path/to/badinter-consolidee.pdf

Behaviour mirrors ``sync_official_sources`` for the parts that matter:

- compute sha256 + size_bytes of the supplied file;
- run ``content_must_contain`` marker check (raw bytes for HTML/text,
  pdfplumber text extraction fallback for PDF) — same helper used by
  the auto-fetch pipeline so the integrity contract stays uniform;
- copy the file into ``legal_data/sources/<country>/manual_attached/<slug>.<ext>``;
- update a cumulative ``manual_attach_manifest.json`` per country;
- annotate ``LegalSource.notes`` with a ``[manual_attach] BEGIN…END``
  trailer that **coexists** with any prior ``[official_sync]`` block.

What it never does (same hard invariants as the auto-fetch pipeline):

- never creates ``LegalReview``;
- never creates ``CompensationDataset`` / ``CalculationFormula`` /
  ``CompensationTableRow``;
- never promotes ``LegalSource.status`` to ``APPROVED``;
- never extends the ``SourceStatus`` enum.

Marker failure → ``CommandError``, **no** file copy, **no** notes write.
This protects against the operator attaching a wrong document by mistake.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.legal_sources.enums import Reliability, SourceStatus, SourceType
from apps.legal_sources.management.commands.sync_official_sources import (
    COUNTRY_FOLDER_BY_CODE,
    _extract_pdf_text,
    _resolve_country,
    _resolve_jurisdiction,
    _resolve_language,
    _resolve_language_code_for,
    validate_registry,
)
from apps.legal_sources.models import LegalSource
from apps.legal_sources.utils import compute_bytes_sha256

DEFAULT_REGISTRY_PATH = Path(settings.BASE_DIR) / "config" / "official_source_registry.json"

NOTES_MARKER_BEGIN = "[manual_attach] BEGIN"
NOTES_MARKER_END = "[manual_attach] END"


@dataclass
class AttachResult:
    slug: str
    country: str
    source_kind: str
    authority: str
    sha256: str = ""
    size_bytes: int = 0
    local_path: str = ""
    attached_at: str = ""
    classification: str = ""
    marker_check_passed: bool | None = None
    legal_source_id: int | None = None
    legal_source_status_before: str = ""
    legal_source_status_after: str = ""
    note_appended: bool = False
    error: str = ""


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


def _strip_existing_manual_attach_block(notes: str) -> str:
    """Remove a previous ``[manual_attach]`` block in-place, leaving any
    other content (including ``[official_sync]`` blocks) untouched."""
    if NOTES_MARKER_BEGIN not in notes:
        return notes.rstrip()
    head, _, rest = notes.partition(NOTES_MARKER_BEGIN)
    _, _, tail = rest.partition(NOTES_MARKER_END)
    return (head.rstrip() + "\n" + tail.lstrip()).strip()


def build_manual_attach_block(result: AttachResult) -> str:
    body = json.dumps(
        {
            "attached_at": result.attached_at,
            "registry_slug": result.slug,
            "source_kind": result.source_kind,
            "authority": result.authority,
            "sha256": result.sha256,
            "size_bytes": result.size_bytes,
            "local_path": result.local_path,
            "classification": result.classification,
            "marker_check_passed": result.marker_check_passed,
            "no_calculator_activation": True,
            "no_dataset_creation": True,
            "error": result.error,
        },
        ensure_ascii=False,
        indent=2,
    )
    return f"\n\n{NOTES_MARKER_BEGIN}\n{body}\n{NOTES_MARKER_END}\n"


def _markers_present(payload: bytes, markers: list[str]) -> bool:
    """Return True if any of ``markers`` appears in the body. Mirrors the
    ``sync_official_sources.validate_fetch_response`` semantics: raw bytes
    first, then pdfplumber text fallback when the body looks like a PDF.
    """
    body_lower = payload.lower()
    if any(marker.lower().encode("utf-8") in body_lower for marker in markers):
        return True
    if payload[:5] == b"%PDF-":
        text = _extract_pdf_text(payload).lower()
        if text and any(marker.lower() in text for marker in markers):
            return True
    return False


class Command(BaseCommand):
    help = (
        "Attacca manualmente un file ufficiale (PDF/HTML) a una fonte già "
        "registrata in `config/official_source_registry.json` con "
        "`manual_attach_allowed=true`. Calcola sha256, verifica marker, "
        "scrive manifest e LegalSource.notes. NON crea LegalReview, "
        "dataset, formule, righe; NON promuove APPROVED."
    )

    def add_arguments(self, parser):
        parser.add_argument("--slug", required=True, help="source_slug del registry.")
        parser.add_argument(
            "--file",
            required=True,
            help="Path al file ufficiale fornito dallo Studio.",
        )
        parser.add_argument(
            "--registry",
            default=str(DEFAULT_REGISTRY_PATH),
            help="Path al registry JSON (default config/official_source_registry.json).",
        )

    def handle(self, *args, **options):
        registry_path = Path(options["registry"]).resolve()
        slug: str = options["slug"]
        file_arg: str = options["file"]

        if not registry_path.exists():
            raise CommandError(f"Registry not found: {registry_path}")

        payload = json.loads(registry_path.read_text(encoding="utf-8"))
        errors = validate_registry(payload)
        if errors:
            self.stdout.write(self.style.ERROR("Registry validation failed:"))
            for err in errors:
                self.stdout.write(f"  - {err}")
            raise CommandError("Aborting: registry has schema/data errors.")

        entry = next((e for e in payload["entries"] if e["source_slug"] == slug), None)
        if entry is None:
            raise CommandError(f"slug {slug!r} not found in registry")
        if not entry.get("manual_attach_allowed"):
            raise CommandError(
                f"slug {slug!r} does not allow manual_attach "
                "(set 'manual_attach_allowed': true in the registry)"
            )

        file_path = Path(file_arg).expanduser().resolve()
        if not file_path.exists() or not file_path.is_file():
            raise CommandError(f"File not found: {file_path}")

        body = file_path.read_bytes()
        if not body:
            raise CommandError(f"File is empty: {file_path}")

        result = AttachResult(
            slug=slug,
            country=entry["country"],
            source_kind=entry["source_kind"],
            authority=entry["authority"],
            attached_at=datetime.now(UTC).isoformat(),
            sha256=compute_bytes_sha256(body),
            size_bytes=len(body),
        )

        markers = entry.get("content_must_contain") or []
        if markers:
            ok = _markers_present(body, markers)
            result.marker_check_passed = ok
            if not ok:
                result.classification = "manual_attach_marker_failed"
                result.error = (
                    "manual_attach_marker_failed: missing required content "
                    f"markers {markers!r} in {file_path.name}"
                )
                # Persist nothing else (no file copy, no notes write,
                # no manifest update). Surface the failure to the operator.
                raise CommandError(result.error)
        else:
            # Registry without markers: accept by default but flag the gap.
            result.marker_check_passed = None

        # Copy file into the per-country manual_attached folder.
        ext = file_path.suffix.lstrip(".") or "bin"
        folder = COUNTRY_FOLDER_BY_CODE.get(result.country.upper(), result.country.lower())
        base_dir = Path(settings.LEGAL_DATA_ROOT) / "sources" / folder / "manual_attached"
        base_dir.mkdir(parents=True, exist_ok=True)
        dest = base_dir / f"{slug}.{ext}"
        shutil.copyfile(file_path, dest)
        try:
            result.local_path = str(dest.relative_to(Path(settings.BASE_DIR)))
        except ValueError:
            # LEGAL_DATA_ROOT overridden outside BASE_DIR (pytest tmp_path).
            result.local_path = str(dest)
        result.classification = "manual_attach_success"

        # Annotate LegalSource (creates a NEEDS_REVIEW row if none exists).
        self._upsert_and_annotate(entry, result)

        # Append to the per-country cumulative manifest.
        self._append_manifest(base_dir, result)

        self.stdout.write(
            self.style.SUCCESS(
                f"  [  OK] {slug}  sha256={result.sha256[:12]} "
                f"size={result.size_bytes}B -> {result.local_path}"
            )
        )

    @transaction.atomic
    def _upsert_and_annotate(self, entry: dict[str, Any], result: AttachResult) -> None:
        country = _resolve_country(result.country)
        jurisdiction = _resolve_jurisdiction(country, entry["jurisdiction"])
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

        if created:
            source.status = SourceStatus.NEEDS_REVIEW
            source.save(update_fields=["status"])

        new_notes = _strip_existing_manual_attach_block(
            source.notes or ""
        ) + build_manual_attach_block(result)
        if source.notes != new_notes:
            source.notes = new_notes
            source.save(update_fields=["notes", "updated_at"])
            result.note_appended = True

        result.legal_source_status_after = source.status

    def _append_manifest(self, base_dir: Path, result: AttachResult) -> None:
        manifest_path = base_dir / "manual_attach_manifest.json"
        existing: dict[str, Any]
        if manifest_path.exists():
            existing = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            existing = {
                "schema_version": "1.0",
                "country": result.country,
                "results": [],
            }
        # Replace any prior entry for the same slug (idempotent), then
        # append the new one in chronological order.
        existing["results"] = [
            r for r in existing.get("results", []) if r.get("slug") != result.slug
        ]
        existing["results"].append(
            {
                "slug": result.slug,
                "country": result.country,
                "source_kind": result.source_kind,
                "authority": result.authority,
                "sha256": result.sha256,
                "size_bytes": result.size_bytes,
                "local_path": result.local_path,
                "attached_at": result.attached_at,
                "classification": result.classification,
                "marker_check_passed": result.marker_check_passed,
                "legal_source_id": result.legal_source_id,
                "legal_source_status_before": result.legal_source_status_before,
                "legal_source_status_after": result.legal_source_status_after,
                "note_appended": result.note_appended,
                "error": result.error,
            }
        )
        existing["last_updated_at"] = datetime.now(UTC).isoformat()
        manifest_path.write_text(
            json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        self.stdout.write(self.style.SUCCESS(f"  manifest -> {manifest_path}"))
