"""Import Belgium Tableau Indicatif 2020 candidate dataset in DRAFT.

Iter: F-belgium-import-candidate-datasets-draft-seed.

REGOLE ASSOLUTE (mirrored from import_france_candidate_datasets):

- Il command **non** attiva il calculator Belgio.
- Il command **non** crea ``CalculationFormula`` (di nessun tipo: né
  draft né approved). L'engine BE è un capitolo separato.
- Il command **non** promuove ``LegalSource.status`` a APPROVED.
- Il command **non** crea ``LegalReview``.
- Il command **non** ha alcun delete distruttivo: nessuna riga è mai
  cancellata; le re-run aggiornano i campi via ``update_or_create``
  su una chiave naturale per riga.
- Il dataset creato resta in stato ``DRAFT``. Se un dataset con lo
  stesso ``version_label`` esiste già con status ``!= DRAFT``, il
  command si rifiuta di scriverlo (errore esplicito).
- Le righe portano sempre nei loro ``extra`` JSON i flag di
  ``legal_review_required`` / ``no_human_legal_approval`` ricavati
  dal ``source_note`` del CSV upstream.
- Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR resta invariato.

Uso:

    python manage.py import_belgium_candidate_datasets \\
        --souffrances legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-souffrances-endurees.csv \\
        --forfait     legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-prejudice-esthetique.csv \\
        --deces       legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-prejudice-deces-affection.csv \\
        --vehicule    legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-vehicule-remplacement.csv

Tutti gli argomenti sono opzionali individualmente — si possono
passare solo i CSV disponibili o aggiornarne uno alla volta. Il
dataset ``BE-TABLEAU-INDICATIF-2020-DRAFT`` viene creato al primo
run; le re-run aggiornano le righe esistenti senza duplicarle.

Whitelist row_type
==================

I valori ``row_type`` accettati sono **gli stessi prodotti
dall'extractor upstream** (``scripts/legal_data/extract_belgium_ti_2020.py``).
La whitelist effettiva è in ``ROW_TYPE_TO_DATASET`` qui sotto:

- be_souffrances_endurees_per_age_severity_amount
- be_indemnite_forfaitaire_per_age_annual_amount
- be_prejudice_deces_affection_per_relation_amount
- be_vehicule_remplacement_per_type_per_day_amount
"""

from __future__ import annotations

import csv
import hashlib
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.calculators.enums import CaseType
from apps.compensation.models import (
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
    ExtractionLog,
)
from apps.jurisdictions.models import Country, Jurisdiction
from apps.legal_sources.models import LegalSource

BE_SOURCE_SLUG = "be-tableau-indicatif-2020"

BE_DATASET_NAME = "BE Tableau Indicatif 2020 (candidate, DRAFT)"
BE_DATASET_VERSION_LABEL = "BE-TABLEAU-INDICATIF-2020-DRAFT"

DATASET_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value

ROW_TYPE_SOUFFRANCES = "be_souffrances_endurees_per_age_severity_amount"
ROW_TYPE_FORFAIT = "be_indemnite_forfaitaire_per_age_annual_amount"
ROW_TYPE_DECES = "be_prejudice_deces_affection_per_relation_amount"
ROW_TYPE_VEHICULE = "be_vehicule_remplacement_per_type_per_day_amount"

# Whitelist: any row_type not present here is rejected at import.
ROW_TYPE_TO_DATASET: dict[str, str] = {
    ROW_TYPE_SOUFFRANCES: BE_DATASET_VERSION_LABEL,
    ROW_TYPE_FORFAIT: BE_DATASET_VERSION_LABEL,
    ROW_TYPE_DECES: BE_DATASET_VERSION_LABEL,
    ROW_TYPE_VEHICULE: BE_DATASET_VERSION_LABEL,
}

# Per row_type, which CSV columns make up the natural key for upsert.
ROW_TYPE_NATURAL_KEY_FIELDS: dict[str, tuple[str, ...]] = {
    ROW_TYPE_SOUFFRANCES: ("severity_code", "victim_age_min", "victim_age_max"),
    ROW_TYPE_FORFAIT: ("severity_code", "victim_age_min", "victim_age_max"),
    ROW_TYPE_DECES: ("relation_code",),
    ROW_TYPE_VEHICULE: ("vehicle_type_code",),
}


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class FileResult:
    file_path: Path
    file_sha256: str = ""
    file_size_bytes: int = 0
    rows_imported: int = 0
    rows_skipped: int = 0
    error_message: str = ""
    result: str = ExtractionLog.Result.SUCCESS
    metadata: dict = field(default_factory=dict)


@dataclass
class DatasetHandle:
    dataset: CompensationDataset
    legal_source: LegalSource
    created: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_source_note_flags(source_note: str) -> dict[str, str | bool | dict]:
    """Parse a ``key=value;key=value`` source_note into a dict.

    Recognises ``legal_review_required`` and ``no_human_legal_approval``
    explicitly so the import can never silently drop them.
    """
    raw: dict[str, str] = {}
    for part in (source_note or "").split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, value = part.partition("=")
        raw[key.strip()] = value.strip()
    flags: dict[str, str | bool | dict] = {}
    if "legal_review_required" in raw:
        flags["legal_review_required"] = raw["legal_review_required"].lower() == "true"
    if "no_human_legal_approval" in raw:
        flags["no_human_legal_approval"] = raw["no_human_legal_approval"].lower() == "true"
    if raw:
        flags["raw_flags"] = raw
    return flags


def _to_decimal_or_none(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except (InvalidOperation, ValueError):
        return None


def _nat_key_string(values: list[str]) -> str:
    return "|".join(values)


def _sha256_file(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Importa in DRAFT i CSV Belgio Tableau Indicatif 2020 già "
        "estratti. Non attiva il calculator Belgio, non crea formule, "
        "non promuove LegalSource."
    )

    def add_arguments(self, parser):
        parser.add_argument("--souffrances", default=None)
        parser.add_argument("--forfait", default=None)
        parser.add_argument("--deces", default=None)
        parser.add_argument("--vehicule", default=None)

    def handle(self, *args, **options):
        any_input = any(options.get(k) for k in ("souffrances", "forfait", "deces", "vehicule"))
        if not any_input:
            raise CommandError(
                "Provide at least one of --souffrances / --forfait / " "--deces / --vehicule"
            )

        try:
            be_source = LegalSource.objects.get(slug=BE_SOURCE_SLUG)
        except LegalSource.DoesNotExist as exc:
            raise CommandError(f"LegalSource {BE_SOURCE_SLUG!r} not found in DB") from exc

        # Capture the source status so we can assert it never moves.
        source_status_before = be_source.status

        handle = self._get_or_create_draft_dataset(
            legal_source=be_source,
            name=BE_DATASET_NAME,
            version_label=BE_DATASET_VERSION_LABEL,
            notes=(
                "Candidate dataset for BE Tableau Indicatif 2020 — DRAFT only.\n"
                "Source rows extracted by scripts/legal_data/extract_belgium_ti_2020.py.\n"
                "Historical 2020 reference: not the active edition. No "
                "calculator activation. No CalculationFormula attached. "
                "Awaits Studio legal review for promotion."
            ),
        )

        results: list[tuple[str, FileResult]] = []
        for arg, label in (
            ("souffrances", "Souffrances"),
            ("forfait", "Forfait"),
            ("deces", "Deces"),
            ("vehicule", "Vehicule"),
        ):
            file_arg = options.get(arg)
            if not file_arg:
                continue
            res = self._import_csv(Path(file_arg).resolve(), handle)
            results.append((label, res))
            self._log_extraction(handle, res)
            mark = "OK" if res.result == ExtractionLog.Result.SUCCESS else res.result.upper()
            self.stdout.write(
                f"  [{mark:>4}] {label:<11} rows_imported={res.rows_imported} "
                f"rows_skipped={res.rows_skipped} -> {res.file_path.name}"
            )
            if res.error_message:
                self.stdout.write(self.style.WARNING(f"         err: {res.error_message}"))

        # Self-check: the LegalSource status must not have moved. We
        # never write to it, but a defensive read keeps the contract
        # explicit in the command output.
        be_source.refresh_from_db(fields=["status"])
        if be_source.status != source_status_before:
            raise CommandError(
                f"LegalSource {BE_SOURCE_SLUG!r} status moved from "
                f"{source_status_before!r} to {be_source.status!r} — refusing "
                "to continue. This command must never promote a legal source."
            )

        self.stdout.write(
            self.style.SUCCESS(
                "import_belgium_candidate_datasets done. "
                f"dataset={BE_DATASET_VERSION_LABEL} "
                f"files={len(results)} "
                f"source_status={be_source.status} (unchanged)"
            )
        )

    # ------------------------------------------------------------------
    # Dataset bootstrap
    # ------------------------------------------------------------------

    def _get_or_create_draft_dataset(
        self,
        *,
        legal_source: LegalSource,
        name: str,
        version_label: str,
        notes: str,
    ) -> DatasetHandle:
        country = legal_source.country
        jurisdiction = legal_source.jurisdiction
        if country is None:
            country = Country.objects.get(code="BE")
        if jurisdiction is None:
            jurisdiction = Jurisdiction.objects.filter(country=country, code="BE-NATIONAL").first()
            if jurisdiction is None:
                raise CommandError("BE-NATIONAL jurisdiction missing in DB.")

        existing = CompensationDataset.objects.filter(
            source=legal_source,
            version_label=version_label,
        ).first()
        if existing is not None:
            if existing.status != DatasetStatus.DRAFT:
                raise CommandError(
                    f"Dataset {version_label!r} already exists with "
                    f"status={existing.status!r}. Refusing to write into a "
                    "non-DRAFT dataset; this command is only allowed to "
                    "create or update DRAFT data."
                )
            return DatasetHandle(dataset=existing, legal_source=legal_source, created=False)

        dataset = CompensationDataset.objects.create(
            source=legal_source,
            jurisdiction=jurisdiction,
            country=country,
            case_type=DATASET_CASE_TYPE,
            name=name,
            version_label=version_label,
            status=DatasetStatus.DRAFT,
            notes=notes,
        )
        return DatasetHandle(dataset=dataset, legal_source=legal_source, created=True)

    # ------------------------------------------------------------------
    # Per-CSV import
    # ------------------------------------------------------------------

    def _import_csv(self, file_path: Path, handle: DatasetHandle) -> FileResult:
        if not file_path.exists():
            return FileResult(
                file_path=file_path,
                error_message=f"file_not_found: {file_path}",
                result=ExtractionLog.Result.FAILED,
            )
        sha256_hex, size_bytes = _sha256_file(file_path)
        result = FileResult(
            file_path=file_path,
            file_sha256=sha256_hex,
            file_size_bytes=size_bytes,
        )
        try:
            with file_path.open("r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        self._upsert_row(row=row, handle=handle)
                        result.rows_imported += 1
                    except _RowSkipped as exc:
                        result.rows_skipped += 1
                        if not result.error_message:
                            result.error_message = str(exc)
        except OSError as exc:
            result.error_message = f"read_failed: {exc.__class__.__name__}: {exc}"
            result.result = ExtractionLog.Result.FAILED
            return result

        if result.rows_skipped and result.rows_imported:
            result.result = ExtractionLog.Result.PARTIAL
        elif result.rows_skipped and not result.rows_imported:
            result.result = ExtractionLog.Result.FAILED
        else:
            result.result = ExtractionLog.Result.SUCCESS
        return result

    @transaction.atomic
    def _upsert_row(self, *, row: dict[str, str], handle: DatasetHandle) -> None:
        row_type = (row.get("row_type") or "").strip()
        if not row_type:
            raise _RowSkipped("missing row_type")
        if row_type not in ROW_TYPE_TO_DATASET:
            raise _RowSkipped(f"row_type {row_type!r} not in whitelist")

        # Build natural-key string from the per-row_type fields.
        nk_fields = ROW_TYPE_NATURAL_KEY_FIELDS[row_type]
        nk_values: list[str] = []
        for field_name in nk_fields:
            raw = (row.get(field_name) or "").strip()
            if not raw:
                raise _RowSkipped(
                    f"missing natural-key field {field_name!r} for row_type {row_type!r}"
                )
            nk_values.append(raw)
        nat_key = _nat_key_string(nk_values)

        # Validate amounts per row_type.
        amount_min = _to_decimal_or_none(row.get("amount_min"))
        amount_mid = _to_decimal_or_none(row.get("amount_mid"))
        amount_max = _to_decimal_or_none(row.get("amount_max"))
        annual_amount = _to_decimal_or_none(row.get("annual_amount"))
        daily_min = _to_decimal_or_none(row.get("daily_amount_min"))
        daily_mid = _to_decimal_or_none(row.get("daily_amount_mid"))
        daily_max = _to_decimal_or_none(row.get("daily_amount_max"))

        if row_type == ROW_TYPE_SOUFFRANCES:
            if any(v is None for v in (amount_min, amount_mid, amount_max)):
                raise _RowSkipped(
                    "amount_min/amount_mid/amount_max must all be present "
                    f"for row_type {row_type!r}"
                )
            if any(v < 0 for v in (amount_min, amount_mid, amount_max)):  # type: ignore[operator]
                raise _RowSkipped("amount values must be non-negative")
        elif row_type == ROW_TYPE_FORFAIT:
            if annual_amount is None:
                raise _RowSkipped(f"annual_amount must be present for row_type {row_type!r}")
            if annual_amount < 0:
                raise _RowSkipped("annual_amount must be non-negative")
        elif row_type == ROW_TYPE_DECES:
            if any(v is None for v in (amount_min, amount_mid, amount_max)):
                raise _RowSkipped(
                    "amount_min/amount_mid/amount_max must all be present "
                    f"for row_type {row_type!r}"
                )
            if any(v < 0 for v in (amount_min, amount_mid, amount_max)):  # type: ignore[operator]
                raise _RowSkipped("amount values must be non-negative")
        elif row_type == ROW_TYPE_VEHICULE:
            if any(v is None for v in (daily_min, daily_mid, daily_max)):
                raise _RowSkipped(
                    "daily_amount_min/daily_amount_mid/daily_amount_max must all be present "
                    f"for row_type {row_type!r}"
                )
            if any(v < 0 for v in (daily_min, daily_mid, daily_max)):  # type: ignore[operator]
                raise _RowSkipped("daily amount values must be non-negative")

        # Numeric mapping per row_type. Use the model's existing slots
        # when applicable; everything else lives in ``extra`` JSON. We
        # do **not** invent columns or extend the model.
        defaults: dict = {}
        extra: dict = {}

        source_note = (row.get("source_note") or "").strip()
        if source_note:
            extra["source_note"] = source_note
            extra["source_flags"] = _parse_source_note_flags(source_note)
        if page := (row.get("source_page") or "").strip():
            extra["source_page"] = page
        currency = (row.get("currency") or "").strip()
        if currency:
            extra["currency"] = currency
        extra["nat_key"] = nat_key
        extra["row_type"] = row_type

        if row_type == ROW_TYPE_SOUFFRANCES:
            defaults["age_min"] = int(row["victim_age_min"])
            defaults["age_max"] = int(row["victim_age_max"])
            extra["severity_code"] = (row.get("severity_code") or "").strip()
            extra["severity_label_fr"] = (row.get("severity_label_fr") or "").strip()
            extra["amount_min"] = str(amount_min)
            extra["amount_mid"] = str(amount_mid)
            extra["amount_max"] = str(amount_max)
        elif row_type == ROW_TYPE_FORFAIT:
            defaults["age_min"] = int(row["victim_age_min"])
            defaults["age_max"] = int(row["victim_age_max"])
            extra["severity_code"] = (row.get("severity_code") or "").strip()
            extra["severity_label_fr"] = (row.get("severity_label_fr") or "").strip()
            extra["annual_amount"] = str(annual_amount)
        elif row_type == ROW_TYPE_DECES:
            extra["relation_code"] = (row.get("relation_code") or "").strip()
            extra["relation_label_fr"] = (row.get("relation_label_fr") or "").strip()
            extra["amount_min"] = str(amount_min)
            extra["amount_mid"] = str(amount_mid)
            extra["amount_max"] = str(amount_max)
        elif row_type == ROW_TYPE_VEHICULE:
            extra["vehicle_type_code"] = (row.get("vehicle_type_code") or "").strip()
            extra["vehicle_type_label_fr"] = (row.get("vehicle_type_label_fr") or "").strip()
            extra["daily_amount_min"] = str(daily_min)
            extra["daily_amount_mid"] = str(daily_mid)
            extra["daily_amount_max"] = str(daily_max)

        defaults["extra"] = extra
        defaults["row_type"] = row_type

        CompensationTableRow.objects.update_or_create(
            dataset=handle.dataset,
            row_type=row_type,
            extra__nat_key=nat_key,
            defaults=defaults,
        )

    # ------------------------------------------------------------------
    # ExtractionLog
    # ------------------------------------------------------------------

    def _log_extraction(self, handle: DatasetHandle, result: FileResult) -> None:
        ExtractionLog.objects.create(
            source=handle.legal_source,
            dataset=handle.dataset,
            method=ExtractionLog.Method.CSV_IMPORT,
            file_path=str(result.file_path),
            file_sha256=result.file_sha256,
            file_size_bytes=result.file_size_bytes,
            rows_imported=result.rows_imported,
            rows_skipped=result.rows_skipped,
            result=result.result,
            error_message=result.error_message,
            metadata=result.metadata,
        )


class _RowSkipped(Exception):
    """Raised when a CSV row fails per-row validation."""
