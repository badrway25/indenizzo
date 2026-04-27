"""
Export di sicurezza dello stato approvato per il modulo Italia TUN 2025.

Produce un singolo file JSON con TUTTI i record necessari a ricostruire
lo stato legale approvato:
- `LegalSource` (slug, status, citation, dates, ...);
- `LegalSourceAttachment` (metadata: filename, mime, size, sha256 — NON
  il binario, solo i metadati);
- `CompensationDataset`;
- `CalculationFormula` con `parameters` runtime;
- 9 191 `CompensationTableRow` (la sostanza del dataset);
- `LegalReview` (audit umano);
- `ExtractionLog` (audit tecnico import).

NESSUN dato personale è incluso: `Simulation`, `Lead`, `ConsentRecord`,
`PrivacyAuditEvent`, `User` sono esplicitamente esclusi. La whitelist
dei modelli esportati è chiusa: estendere richiede modifica di codice
+ test.

Output:
    legal_data/exports/italy_tun_2025_<YYYYMMDD-HHMMSS>.json

La cartella `legal_data/exports/` è coperta da `.gitignore`: i file
prodotti restano in locale o vanno trasferiti via canale sicuro.

Esecuzione:
    python manage.py export_italy_tun_dataset
    python manage.py export_italy_tun_dataset --output /tmp/snapshot.json
    python manage.py export_italy_tun_dataset --quiet
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    ExtractionLog,
)
from apps.legal_sources.models import LegalReview, LegalSource

SCHEMA_VERSION = "1.0"
SOURCE_SLUG = "it-dpr-12-2025-tun-danno-biologico"
DATASET_VERSION_LABEL = "DPR-12-2025"
FORMULA_CODE = "italy_art_138_tun_2025_base"

DEFAULT_EXPORT_DIR = Path(settings.BASE_DIR) / "legal_data" / "exports"


def _date_iso(value):
    return value.isoformat() if value else None


def _decimal_str(value):
    return str(value) if isinstance(value, Decimal) else (None if value is None else str(value))


def _serialize_source(src: LegalSource) -> dict:
    return {
        "slug": src.slug,
        "title": src.title,
        "citation": src.citation,
        "country_code": src.country.code if src.country_id else None,
        "jurisdiction_code": src.jurisdiction.code if src.jurisdiction_id else None,
        "language_code": src.language.code if src.language_id else None,
        "source_type": src.source_type,
        "official_url": src.official_url,
        "publication_date": _date_iso(src.publication_date),
        "effective_date": _date_iso(src.effective_date),
        "valid_until": _date_iso(src.valid_until),
        "last_checked_at": _date_iso(src.last_checked_at),
        "status": src.status,
        "reliability": src.reliability,
        "legal_reviewer_username": (src.legal_reviewer.username if src.legal_reviewer_id else None),
        "notes": src.notes,
        "created_at": src.created_at.isoformat() if src.created_at else None,
        "updated_at": src.updated_at.isoformat() if src.updated_at else None,
    }


def _serialize_attachment(att) -> dict:
    """Solo metadata. Il binario non viene esportato (canale separato)."""
    return {
        "original_filename": att.original_filename,
        "mime_type": att.mime_type,
        "size_bytes": att.size_bytes,
        "sha256": att.sha256,
        "description": att.description,
        "created_at": att.created_at.isoformat() if att.created_at else None,
    }


def _serialize_dataset(ds: CompensationDataset) -> dict:
    return {
        "name": ds.name,
        "version_label": ds.version_label,
        "case_type": ds.case_type,
        "status": ds.status,
        "country_code": ds.country.code if ds.country_id else None,
        "jurisdiction_code": ds.jurisdiction.code if ds.jurisdiction_id else None,
        "source_slug": ds.source.slug if ds.source_id else None,
        "valid_from": _date_iso(ds.valid_from),
        "valid_to": _date_iso(ds.valid_to),
        "notes": ds.notes,
        "created_at": ds.created_at.isoformat() if ds.created_at else None,
        "updated_at": ds.updated_at.isoformat() if ds.updated_at else None,
    }


def _serialize_formula(f: CalculationFormula) -> dict:
    return {
        "code": f.code,
        "name": f.name,
        "status": f.status,
        "expression_text": f.expression_text,
        "source_reference": f.source_reference,
        "parameters": f.parameters or {},
        "notes": f.notes,
        "created_at": f.created_at.isoformat() if f.created_at else None,
        "updated_at": f.updated_at.isoformat() if f.updated_at else None,
    }


def _serialize_row(row: CompensationTableRow) -> dict:
    return {
        "row_type": row.row_type,
        "age_min": row.age_min,
        "age_max": row.age_max,
        "disability_min": row.disability_min,
        "disability_max": row.disability_max,
        "point_value": _decimal_str(row.point_value),
        "daily_amount": _decimal_str(row.daily_amount),
        "coefficient": _decimal_str(row.coefficient),
        "extra": row.extra or {},
        "notes": row.notes,
    }


def _serialize_review(r: LegalReview) -> dict:
    return {
        "decision": r.decision,
        "previous_status": r.previous_status,
        "new_status": r.new_status,
        "reviewer_username": r.reviewer.username if r.reviewer_id else None,
        "comment": r.comment,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


def _serialize_extraction_log(log: ExtractionLog) -> dict:
    return {
        "method": log.method,
        "result": log.result,
        "file_path": log.file_path,
        "file_sha256": log.file_sha256,
        "file_size_bytes": log.file_size_bytes,
        "rows_imported": log.rows_imported,
        "rows_skipped": log.rows_skipped,
        "error_message": log.error_message,
        "metadata": log.metadata or {},
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


class Command(BaseCommand):
    help = (
        "Esporta in JSON lo stato approvato del modulo Italia TUN 2025. "
        "NON include dati personali (Simulation/Lead/ConsentRecord/User)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            help="Path file di output. Default: legal_data/exports/italy_tun_2025_<ts>.json",
        )
        parser.add_argument("--quiet", action="store_true", help="Sopprime l'output verboso.")

    def handle(self, *args, **options):
        quiet = options["quiet"]

        src = LegalSource.objects.filter(slug=SOURCE_SLUG).first()
        if src is None:
            raise CommandError(f"LegalSource '{SOURCE_SLUG}' non trovata.")
        dataset = (
            CompensationDataset.objects.filter(version_label=DATASET_VERSION_LABEL)
            .select_related("source", "jurisdiction", "country")
            .first()
        )
        if dataset is None:
            raise CommandError(
                f"CompensationDataset version_label='{DATASET_VERSION_LABEL}' non trovato."
            )
        formula = CalculationFormula.objects.filter(code=FORMULA_CODE, dataset=dataset).first()
        if formula is None:
            raise CommandError(f"CalculationFormula code='{FORMULA_CODE}' non trovata.")

        rows = list(CompensationTableRow.objects.filter(dataset=dataset).order_by("pk"))
        attachments = list(src.attachments.all().order_by("pk"))
        reviews = list(LegalReview.objects.filter(source=src).order_by("created_at", "pk"))
        logs = list(ExtractionLog.objects.filter(source=src).order_by("created_at", "pk"))

        export = {
            "schema_version": SCHEMA_VERSION,
            "exported_at": datetime.now(tz=UTC).isoformat(),
            "module": {
                "country": "IT",
                "jurisdiction": "IT-NATIONAL",
                "case_type": dataset.case_type,
            },
            "source": _serialize_source(src),
            "attachments": [_serialize_attachment(a) for a in attachments],
            "dataset": _serialize_dataset(dataset),
            "formula": _serialize_formula(formula),
            "rows_count": len(rows),
            "rows": [_serialize_row(r) for r in rows],
            "legal_reviews": [_serialize_review(r) for r in reviews],
            "extraction_logs": [_serialize_extraction_log(log) for log in logs],
        }

        out_path = (
            Path(options["output"])
            if options["output"]
            else DEFAULT_EXPORT_DIR
            / f"italy_tun_2025_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)

        payload = json.dumps(export, ensure_ascii=False, indent=2)
        out_path.write_text(payload, encoding="utf-8")

        # Hash del payload come prova di integrità — utile per restore.
        payload_sha = hashlib.sha256(payload.encode("utf-8")).hexdigest()

        if not quiet:
            self.stdout.write(
                f"  source.status   : {src.status}\n"
                f"  dataset.status  : {dataset.status}\n"
                f"  formula.status  : {formula.status}\n"
                f"  rows count      : {len(rows)}\n"
                f"  attachments     : {len(attachments)}\n"
                f"  reviews         : {len(reviews)}\n"
                f"  extraction_logs : {len(logs)}"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Export written: {out_path} "
                f"({out_path.stat().st_size} bytes, sha256 {payload_sha[:16]}…)"
            )
        )
