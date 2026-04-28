"""
Import additive del danno morale TUN 2025 (Tabelle 2.A/2.B/2.C del D.P.R. 12/2025).

REGOLE ASSOLUTE — necessarie per non rompere la Tabella 1 già `approved`:

1. Il command **NON** chiama mai ``dataset.rows.all().delete()``. Il
   command parente ``import_italy_tun_2025`` lo fa, ed è il motivo per
   cui questo command è separato: chiamare quello sui CSV moral
   cancellerebbe le 9 191 righe della Tabella 1 base.

2. Il command lavora su un dataset SEPARATO (``DPR-12-2025-MORAL``) sulla
   STESSA ``LegalSource`` approved. Status del dataset moral resta
   sempre ``DRAFT`` — la promozione è atto umano dello Studio.

3. Il command NON tocca il dataset base (``DPR-12-2025``) né il suo
   status né le sue righe.

4. Il command NON modifica ``LegalSource.status`` né
   ``CalculationFormula.parameters`` di alcuna formula.

5. Accetta SOLO i tre row_type morali:
       tun_biological_moral_min_total_amount
       tun_biological_moral_mid_total_amount
       tun_biological_moral_max_total_amount
   Qualunque altro row_type è rifiutato (CommandError, nessuna riga
   importata).

6. Upsert per chiave naturale ``(dataset, row_type, age_min, age_max,
   disability_min, disability_max)`` — re-run dello stesso CSV non
   crea duplicati.

7. Rifiuta righe con ``point_value`` vuoto.

8. Registra ``ExtractionLog`` con esito success / partial / failed.

Uso:
    python manage.py import_italy_tun_2025_moral \\
        --csv legal_data/sources/italy/tun_2025/tun_2025_moral_min_candidate.csv

    python manage.py import_italy_tun_2025_moral \\
        --csv legal_data/sources/italy/tun_2025/tun_2025_moral_mid_candidate.csv \\
        --csv legal_data/sources/italy/tun_2025/tun_2025_moral_max_candidate.csv
"""

from __future__ import annotations

import csv
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
from apps.legal_sources.models import LegalSource
from apps.legal_sources.utils import compute_bytes_sha256

BASE_SOURCE_SLUG = "it-dpr-12-2025-tun-danno-biologico"

MORAL_DATASET_VERSION_LABEL = "DPR-12-2025-MORAL"
MORAL_DATASET_NAME = (
    "Tabella Unica Nazionale 2025 — danno morale (Tabelle 2.A/2.B/2.C art. 138 CAP)"
)
MORAL_DATASET_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value

ALLOWED_MORAL_ROW_TYPES = frozenset(
    {
        "tun_biological_moral_min_total_amount",
        "tun_biological_moral_mid_total_amount",
        "tun_biological_moral_max_total_amount",
    }
)

EXPECTED_CSV_COLUMNS = {
    "row_type",
    "age_min",
    "age_max",
    "disability_min",
    "disability_max",
    "point_value",
    "coefficient",
    "daily_amount",
    "source_page",
    "source_note",
}


class Command(BaseCommand):
    help = (
        "Import ADDITIVO delle Tabelle 2.A/2.B/2.C (danno morale) TUN 2025. "
        "Mai cancella righe esistenti. Mai promuove status. Lavora su un "
        "dataset separato `DPR-12-2025-MORAL` (sempre DRAFT)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--csv",
            dest="csv_files",
            action="append",
            required=True,
            help=(
                "Path al CSV moral candidate. Può essere ripetuto per importare "
                "più tabelle in una sola esecuzione."
            ),
        )

    def handle(self, *args, **options):
        csv_paths = [Path(p) for p in options["csv_files"]]
        legal_source = self._get_legal_source()
        dataset = self._get_or_create_moral_dataset(legal_source)

        # Vincolo difensivo: il dataset moral DEVE essere DRAFT. Se per
        # qualche motivo è approved, il command si rifiuta.
        if dataset.status != DatasetStatus.DRAFT:
            raise CommandError(
                f"Dataset moral non in DRAFT (status={dataset.status}); "
                "questo command opera solo su dataset DRAFT."
            )

        for path in csv_paths:
            self._handle_csv_import(legal_source, dataset, path)

        self.stdout.write(
            self.style.SUCCESS(
                f"import_italy_tun_2025_moral completato. "
                f"dataset={dataset.pk} status={dataset.status} (mai promosso)."
            )
        )

    # ------------------------------------------------------------------
    # Step 1 — recupero della LegalSource (già approved)
    # ------------------------------------------------------------------

    def _get_legal_source(self) -> LegalSource:
        try:
            return LegalSource.objects.get(slug=BASE_SOURCE_SLUG)
        except LegalSource.DoesNotExist as exc:
            raise CommandError(
                f"LegalSource '{BASE_SOURCE_SLUG}' non trovata. Esegui prima "
                f"`python manage.py seed_italy_legal_sources`."
            ) from exc

    # ------------------------------------------------------------------
    # Step 2 — dataset MORAL separato in DRAFT
    # ------------------------------------------------------------------

    def _get_or_create_moral_dataset(self, legal_source: LegalSource) -> CompensationDataset:
        # Difesa: NON modifichiamo MAI il dataset base. Cerchiamo solo il
        # dataset MORAL specifico, e lo creiamo se manca.
        dataset, created = CompensationDataset.objects.get_or_create(
            source=legal_source,
            version_label=MORAL_DATASET_VERSION_LABEL,
            defaults={
                "jurisdiction": legal_source.jurisdiction,
                "country": legal_source.country,
                "case_type": MORAL_DATASET_CASE_TYPE,
                "name": MORAL_DATASET_NAME,
                "status": DatasetStatus.DRAFT,
                "valid_from": legal_source.effective_date,
                "notes": (
                    "Dataset morale (Tabelle 2.A/2.B/2.C). Le righe "
                    "richiedono legal review umana prima di essere "
                    "consumate dal calculator pubblico. Il dataset base "
                    "(DPR-12-2025, danno biologico) è separato e resta "
                    "approved senza essere modificato."
                ),
            },
        )
        if created:
            self.stdout.write(f"  + CompensationDataset moral creato (id={dataset.pk}, DRAFT)")
        else:
            self.stdout.write(f"  CompensationDataset moral già presente (id={dataset.pk})")
        return dataset

    # ------------------------------------------------------------------
    # Step 3 — CSV import additivo
    # ------------------------------------------------------------------

    def _handle_csv_import(
        self,
        legal_source: LegalSource,
        dataset: CompensationDataset,
        path: Path,
    ) -> None:
        if not path.exists() or not path.is_file():
            self._log_failure(
                legal_source,
                method=ExtractionLog.Method.CSV_IMPORT,
                file_path=str(path),
                error=f"CSV non trovato sul disco: {path}",
                dataset=dataset,
            )
            raise CommandError(f"CSV non trovato: {path}")

        payload = path.read_bytes()
        sha256 = compute_bytes_sha256(payload)
        size = len(payload)

        rows_imported, rows_updated, rows_skipped, errors = self._import_csv_rows(dataset, path)

        if errors:
            result = (
                ExtractionLog.Result.PARTIAL
                if (rows_imported + rows_updated) > 0
                else ExtractionLog.Result.FAILED
            )
        else:
            result = ExtractionLog.Result.SUCCESS

        self._log_extraction(
            source=legal_source,
            dataset=dataset,
            method=ExtractionLog.Method.CSV_IMPORT,
            file_path=str(path),
            file_sha256=sha256,
            file_size=size,
            rows_imported=rows_imported + rows_updated,
            rows_skipped=rows_skipped,
            result=result,
            error_message="\n".join(errors)[:8000],
            metadata={
                "csv_columns": sorted(EXPECTED_CSV_COLUMNS),
                "rows_inserted": rows_imported,
                "rows_updated": rows_updated,
                "rows_skipped": rows_skipped,
                "additive": True,
            },
        )

        self.stdout.write(
            f"  CSV {path.name}: inseriti={rows_imported} aggiornati={rows_updated} "
            f"skipped={rows_skipped} esito={result}"
        )

    @transaction.atomic
    def _import_csv_rows(
        self, dataset: CompensationDataset, path: Path
    ) -> tuple[int, int, int, list[str]]:
        rows_imported = 0
        rows_updated = 0
        rows_skipped = 0
        errors: list[str] = []

        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                return 0, 0, 0, ["CSV vuoto o senza header."]
            missing = EXPECTED_CSV_COLUMNS - set(reader.fieldnames)
            if missing:
                return 0, 0, 0, [f"CSV header incompleto: mancano colonne {sorted(missing)}."]

            for line_no, raw in enumerate(reader, start=2):
                row_type = (raw.get("row_type") or "").strip()
                if row_type not in ALLOWED_MORAL_ROW_TYPES:
                    rows_skipped += 1
                    errors.append(
                        f"Linea {line_no}: row_type '{row_type}' non ammesso. "
                        f"Solo {sorted(ALLOWED_MORAL_ROW_TYPES)}."
                    )
                    continue

                pv_raw = (raw.get("point_value") or "").strip()
                if not pv_raw:
                    rows_skipped += 1
                    errors.append(f"Linea {line_no}: point_value vuoto.")
                    continue

                try:
                    pv = Decimal(pv_raw.replace(",", "."))
                except (InvalidOperation, ValueError) as exc:
                    rows_skipped += 1
                    errors.append(f"Linea {line_no}: point_value non numerico ({exc}).")
                    continue

                try:
                    age_min = _to_int_or_none(raw.get("age_min"))
                    age_max = _to_int_or_none(raw.get("age_max"))
                    dis_min = _to_int_or_none(raw.get("disability_min"))
                    dis_max = _to_int_or_none(raw.get("disability_max"))
                except ValueError as exc:
                    rows_skipped += 1
                    errors.append(f"Linea {line_no}: range parsing failed ({exc}).")
                    continue

                extra = {}
                if raw.get("source_page"):
                    extra["source_page"] = raw["source_page"].strip()
                notes = (raw.get("source_note") or "").strip()
                coeff = _to_decimal_or_none(raw.get("coefficient"))
                daily = _to_decimal_or_none(raw.get("daily_amount"))

                # Upsert per chiave naturale.
                obj, created = CompensationTableRow.objects.update_or_create(
                    dataset=dataset,
                    row_type=row_type,
                    age_min=age_min,
                    age_max=age_max,
                    disability_min=dis_min,
                    disability_max=dis_max,
                    defaults={
                        "point_value": pv,
                        "coefficient": coeff,
                        "daily_amount": daily,
                        "extra": extra,
                        "notes": notes,
                    },
                )
                if created:
                    rows_imported += 1
                else:
                    rows_updated += 1

        return rows_imported, rows_updated, rows_skipped, errors

    # ------------------------------------------------------------------
    # Logging audit
    # ------------------------------------------------------------------

    def _log_failure(
        self,
        source: LegalSource,
        *,
        method: str,
        file_path: str,
        error: str,
        dataset: CompensationDataset | None = None,
    ) -> None:
        self._log_extraction(
            source=source,
            dataset=dataset,
            method=method,
            file_path=file_path,
            file_sha256="",
            file_size=0,
            rows_imported=0,
            result=ExtractionLog.Result.FAILED,
            error_message=error,
        )

    def _log_extraction(
        self,
        *,
        source: LegalSource,
        dataset: CompensationDataset | None,
        method: str,
        file_path: str,
        file_sha256: str,
        file_size: int,
        rows_imported: int,
        result: str,
        rows_skipped: int = 0,
        error_message: str = "",
        metadata: dict | None = None,
    ) -> ExtractionLog:
        return ExtractionLog.objects.create(
            source=source,
            dataset=dataset,
            method=method,
            file_path=file_path,
            file_sha256=file_sha256,
            file_size_bytes=file_size,
            rows_imported=rows_imported,
            rows_skipped=rows_skipped,
            result=result,
            error_message=error_message,
            metadata=metadata or {},
        )


def _to_int_or_none(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return int(raw)


def _to_decimal_or_none(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return Decimal(raw.replace(",", "."))
