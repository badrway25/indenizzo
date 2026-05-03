"""Import France candidate datasets (Mornet 2024 + Gazette du Palais 2022) in DRAFT.

Iter: F-france-import-datasets-draft-seed.

REGOLE ASSOLUTE (mirrored from import_italy_tun_2025 + reinforced by the
iter spec):

- Il command **non** attiva il calculator Francia.
- Il command **non** crea ``CalculationFormula`` (di nessun tipo: né
  draft né approved). L'engine FR è un capitolo separato.
- Il command **non** promuove ``LegalSource.status`` a APPROVED.
- Il command **non** crea ``LegalReview``.
- Il command **non** ha alcun delete distruttivo: nessuna riga è mai
  cancellata; le re-run aggiornano i campi via ``update_or_create`` su
  una chiave naturale per riga.
- Tutti i dataset creati restano in stato ``DRAFT``. Se un dataset con
  lo stesso ``version_label`` esiste già con status ``!= DRAFT``, il
  command si rifiuta di scriverlo (errore esplicito).
- Le righe portano sempre nei loro ``extra`` JSON i flag di
  ``legal_review_required`` / ``no_human_legal_approval`` ricavati dal
  ``source_note`` del CSV upstream (se presenti).
- Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR resta invariato.

Uso:

    python manage.py import_france_candidate_datasets \
        --mornet-dfp legal_data/sources/france/mornet_2024/fr-mornet-2024-dfp-per-age-disability.csv \
        --mornet-affection legal_data/sources/france/mornet_2024/fr-mornet-2024-prejudice-affection-per-relation.csv \
        --gazette-viagere legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-viagere.csv \
        --gazette-temporaire legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-temporaire.csv \
        --gazette-anticipated legal_data/sources/france/gazette_2022/fr-gazette-2022-anticipated-payment-years.csv

Tutti gli argomenti sono opzionali individualmente — si possono passare
solo i CSV disponibili o aggiornarne uno alla volta. I dataset
``FR-MORNET-2024-DRAFT`` e ``FR-GAZETTE-PALAIS-2022-DRAFT`` vengono
creati al primo run; le re-run aggiornano le righe esistenti senza
duplicarle.

Whitelist row_type
==================

I valori ``row_type`` accettati sono **gli stessi prodotti dagli
extractor upstream** (``scripts/legal_data/extract_france_mornet_2024.py``,
``scripts/legal_data/extract_france_gazette_2022.py``), per preservare
la tracciabilità tra CSV su disco e righe in DB. Lo iter spec menziona
forme abbreviate (``fr_dfp_per_pct_age_amount`` ecc.); quelle restano
shorthand documentale, **non** valori canonici. La whitelist effettiva
è in ``ROW_TYPE_TO_DATASET`` qui sotto.
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

MORNET_SOURCE_SLUG = "fr-referentiel-mornet-2024"
GAZETTE_SOURCE_SLUG = "fr-bareme-capitalisation-gazette-palais-2022"

MORNET_DATASET_NAME = "FR Mornet 2024 (candidate, DRAFT)"
MORNET_DATASET_VERSION_LABEL = "FR-MORNET-2024-DRAFT"

GAZETTE_DATASET_NAME = "FR Gazette du Palais 2022 capitalisation (candidate, DRAFT)"
GAZETTE_DATASET_VERSION_LABEL = "FR-GAZETTE-PALAIS-2022-DRAFT"

DATASET_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value

# Map each accepted row_type to its target dataset version_label.
# Any row_type not present here is rejected at import time — this is the
# whitelist required by the iter spec.
ROW_TYPE_TO_DATASET: dict[str, str] = {
    "fr_dfp_per_age_disability_amount_per_point": MORNET_DATASET_VERSION_LABEL,
    "fr_prejudice_affection_per_relation_amount": MORNET_DATASET_VERSION_LABEL,
    "fr_capitalisation_viagere_per_age_sex_rate_coefficient": GAZETTE_DATASET_VERSION_LABEL,
    "fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient": GAZETTE_DATASET_VERSION_LABEL,
    "fr_anticipated_payment_years_per_age_sex_rate_years": GAZETTE_DATASET_VERSION_LABEL,
}

# Per row_type, which CSV columns make up the **natural key** for upsert.
# A re-run with the same key updates fields in place; a re-run with a new
# key inserts a new row. The key always implicitly includes
# ``(dataset, row_type)`` — these per-row tuples are appended.
ROW_TYPE_NATURAL_KEY_FIELDS: dict[str, tuple[str, ...]] = {
    "fr_dfp_per_age_disability_amount_per_point": (
        "victim_age_min",
        "victim_age_max",
        "disability_min",
        "disability_max",
    ),
    "fr_prejudice_affection_per_relation_amount": ("relation_code",),
    "fr_capitalisation_viagere_per_age_sex_rate_coefficient": (
        "mortality_table",
        "sex",
        "age",
        "interest_rate_pct",
    ),
    "fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient": (
        "mortality_table",
        "sex",
        "age",
        "interest_rate_pct",
        "target_age",
    ),
    "fr_anticipated_payment_years_per_age_sex_rate_years": (
        "mortality_table",
        "sex",
        "age",
        "interest_rate_pct",
    ),
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


def _parse_source_note_flags(source_note: str) -> dict[str, str | bool]:
    """Parse a ``key=value;key=value`` source_note into a dict.

    Recognises ``legal_review_required`` and ``no_human_legal_approval``
    explicitly so the import can never silently drop them. All other
    keys are stored verbatim under ``raw_flags`` for auditability.
    """
    raw: dict[str, str] = {}
    for part in (source_note or "").split(";"):
        part = part.strip()
        if not part or "=" not in part:
            continue
        key, _, value = part.partition("=")
        raw[key.strip()] = value.strip()
    flags: dict[str, str | bool] = {}
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
    """Deterministic natural-key string for upsert lookup."""
    return "|".join(values)


def _sha256_file(path: Path) -> tuple[str, int]:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest(), len(payload)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = (
        "Importa in DRAFT i CSV France già estratti (Mornet 2024 + "
        "Gazette du Palais 2022). Non attiva il calculator Francia, "
        "non crea formule, non promuove LegalSource."
    )

    def add_arguments(self, parser):
        parser.add_argument("--mornet-dfp", default=None)
        parser.add_argument("--mornet-affection", default=None)
        parser.add_argument("--gazette-viagere", default=None)
        parser.add_argument("--gazette-temporaire", default=None)
        parser.add_argument("--gazette-anticipated", default=None)

    def handle(self, *args, **options):
        any_input = any(
            options.get(k)
            for k in (
                "mornet_dfp",
                "mornet_affection",
                "gazette_viagere",
                "gazette_temporaire",
                "gazette_anticipated",
            )
        )
        if not any_input:
            raise CommandError(
                "Provide at least one of --mornet-dfp / --mornet-affection / "
                "--gazette-viagere / --gazette-temporaire / --gazette-anticipated"
            )

        try:
            mornet_source = LegalSource.objects.get(slug=MORNET_SOURCE_SLUG)
        except LegalSource.DoesNotExist as exc:
            raise CommandError(f"LegalSource {MORNET_SOURCE_SLUG!r} not found in DB") from exc
        try:
            gazette_source = LegalSource.objects.get(slug=GAZETTE_SOURCE_SLUG)
        except LegalSource.DoesNotExist as exc:
            raise CommandError(f"LegalSource {GAZETTE_SOURCE_SLUG!r} not found in DB") from exc

        # Resolve / create both datasets in DRAFT before touching any rows.
        mornet_handle = self._get_or_create_draft_dataset(
            legal_source=mornet_source,
            name=MORNET_DATASET_NAME,
            version_label=MORNET_DATASET_VERSION_LABEL,
            notes=(
                "Candidate dataset for FR Référentiel Mornet 2024 — DRAFT only.\n"
                "Source rows extracted by scripts/legal_data/extract_france_mornet_2024.py.\n"
                "No calculator activation. No CalculationFormula attached. Awaits "
                "Studio legal review for promotion."
            ),
        )
        gazette_handle = self._get_or_create_draft_dataset(
            legal_source=gazette_source,
            name=GAZETTE_DATASET_NAME,
            version_label=GAZETTE_DATASET_VERSION_LABEL,
            notes=(
                "Candidate dataset for FR Gazette du Palais 2022 capitalisation — DRAFT.\n"
                "Source rows extracted by scripts/legal_data/extract_france_gazette_2022.py.\n"
                "No calculator activation. No CalculationFormula attached. Awaits "
                "Studio legal review for promotion."
            ),
        )

        results: list[tuple[str, FileResult]] = []
        for arg, label in (
            ("mornet_dfp", "DFP"),
            ("mornet_affection", "Affection"),
            ("gazette_viagere", "Viagere"),
            ("gazette_temporaire", "Temporaire"),
            ("gazette_anticipated", "Anticipated"),
        ):
            file_arg = options.get(arg)
            if not file_arg:
                continue
            handle = mornet_handle if arg.startswith("mornet_") else gazette_handle
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

        self.stdout.write(
            self.style.SUCCESS(
                "import_france_candidate_datasets done. "
                f"datasets=[{MORNET_DATASET_VERSION_LABEL}, {GAZETTE_DATASET_VERSION_LABEL}] "
                f"files={len(results)}"
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
            country = Country.objects.get(code="FR")
        if jurisdiction is None:
            jurisdiction = Jurisdiction.objects.filter(country=country, code="FR-NATIONAL").first()
            if jurisdiction is None:
                raise CommandError("FR-NATIONAL jurisdiction missing in DB.")

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
                        # Record the first failure reason; downstream operators
                        # can re-run with a corrected CSV.
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
        expected_label = ROW_TYPE_TO_DATASET[row_type]
        if handle.dataset.version_label != expected_label:
            raise _RowSkipped(
                f"row_type {row_type!r} belongs to dataset {expected_label!r}, "
                f"not {handle.dataset.version_label!r}"
            )

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

        # Validate amounts/coefficients per row_type. Empty values are
        # rejected upfront; we never insert a row with no signal.
        amount_min = _to_decimal_or_none(row.get("amount_min"))
        amount_mid = _to_decimal_or_none(row.get("amount_mid"))
        amount_max = _to_decimal_or_none(row.get("amount_max"))
        coefficient = _to_decimal_or_none(row.get("coefficient"))
        years_value = _to_decimal_or_none(row.get("years_value"))

        if row_type in {
            "fr_dfp_per_age_disability_amount_per_point",
            "fr_prejudice_affection_per_relation_amount",
        }:
            if any(v is None for v in (amount_min, amount_mid, amount_max)):
                raise _RowSkipped(
                    "amount_min/amount_mid/amount_max must all be present "
                    f"for row_type {row_type!r}"
                )
        elif row_type in {
            "fr_capitalisation_viagere_per_age_sex_rate_coefficient",
            "fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient",
        }:
            if coefficient is None:
                raise _RowSkipped(f"coefficient must be present for row_type {row_type!r}")
        elif row_type == "fr_anticipated_payment_years_per_age_sex_rate_years":
            if years_value is None:
                raise _RowSkipped(f"years_value must be present for row_type {row_type!r}")

        # Numeric mapping per row_type. We use the model's existing
        # age_min/age_max/disability_min/max/coefficient slots when they
        # apply; everything else lives in ``extra`` JSON. We do **not**
        # invent columns or extend the model.
        defaults: dict = {}
        extra: dict = {}

        # Source provenance carried verbatim into ``extra`` for audit.
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

        if row_type == "fr_dfp_per_age_disability_amount_per_point":
            defaults["age_min"] = int(row["victim_age_min"])
            defaults["age_max"] = int(row["victim_age_max"])
            defaults["disability_min"] = int(row["disability_min"])
            defaults["disability_max"] = int(row["disability_max"])
            extra["amount_min"] = str(amount_min)
            extra["amount_mid"] = str(amount_mid)
            extra["amount_max"] = str(amount_max)
        elif row_type == "fr_prejudice_affection_per_relation_amount":
            extra["relation_code"] = row.get("relation_code", "").strip()
            extra["relation_label_fr"] = (row.get("relation_label_fr") or "").strip()
            extra["amount_min"] = str(amount_min)
            extra["amount_mid"] = str(amount_mid)
            extra["amount_max"] = str(amount_max)
        elif row_type == "fr_capitalisation_viagere_per_age_sex_rate_coefficient":
            defaults["age_min"] = int(row["age"])
            defaults["age_max"] = int(row["age"])
            defaults["coefficient"] = coefficient
            extra["mortality_table"] = row.get("mortality_table", "").strip()
            extra["sex"] = row.get("sex", "").strip()
            extra["interest_rate_pct"] = row.get("interest_rate_pct", "").strip()
        elif row_type == "fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient":
            defaults["age_min"] = int(row["age"])
            defaults["age_max"] = int(row["age"])
            defaults["coefficient"] = coefficient
            extra["mortality_table"] = row.get("mortality_table", "").strip()
            extra["sex"] = row.get("sex", "").strip()
            extra["interest_rate_pct"] = row.get("interest_rate_pct", "").strip()
            extra["target_age"] = row.get("target_age", "").strip()
        elif row_type == "fr_anticipated_payment_years_per_age_sex_rate_years":
            defaults["age_min"] = int(row["age"])
            defaults["age_max"] = int(row["age"])
            extra["mortality_table"] = row.get("mortality_table", "").strip()
            extra["sex"] = row.get("sex", "").strip()
            extra["interest_rate_pct"] = row.get("interest_rate_pct", "").strip()
            extra["years_value"] = str(years_value)

        defaults["extra"] = extra
        defaults["row_type"] = row_type

        # Look up by (dataset, row_type, extra__nat_key); upsert via
        # update_or_create to be idempotent. Note: ``update_or_create``
        # does an UPDATE when an existing row matches, which is
        # explicitly not a delete+insert — guarantees no destructive
        # operation on prior data.
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
    """Raised when a CSV row fails per-row validation. The import keeps
    going; the row is counted as skipped and the first error reason is
    surfaced in the ExtractionLog."""
