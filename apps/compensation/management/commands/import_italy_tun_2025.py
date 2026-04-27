"""
Import del D.P.R. 12/2025 — Tabella Unica Nazionale danno biologico.

REGOLA ASSOLUTA del progetto: non inventare dati legali. Questo command
NON inserisce numeri arbitrari. Tutti i valori provengono da:
- il PDF ufficiale della Gazzetta Ufficiale (allegato e hashato);
- un CSV di estrazione manuale validato dal revisore legale.

Il command è idempotente, segue tre invariati:

1. NON promuove mai fonti, dataset o formule a `approved`. Ogni cosa
   creata ha status `draft`. La promozione è un atto umano successivo.
2. NON modifica una `LegalSource` già `approved`: rispetta il workflow.
   Si limita ad allegare il PDF e creare/aggiornare il dataset.
3. Lascia traccia in `ExtractionLog` (success / partial / failed) con
   SHA-256 del file letto, così che ogni riga in DB possa essere
   risalita alla provenienza.

Usi tipici:

    # 1. allega il PDF ufficiale e crea dataset + formula in draft.
    python manage.py import_italy_tun_2025 \\
        --source-file legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf

    # 2. importa righe estratte manualmente (sempre draft).
    python manage.py import_italy_tun_2025 \\
        --csv legal_data/sources/italy/tun_2025/tun_2025_rows.csv

    # 3. entrambi in un colpo (PDF prima, poi CSV).
    python manage.py import_italy_tun_2025 \\
        --source-file <PDF> --csv <CSV>

Se il PDF non esiste sul disco, il command **non procede** e lascia un
`ExtractionLog` con `result=failed`. Stessa logica per il CSV.
"""

from __future__ import annotations

import csv
import mimetypes
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.calculators.enums import CaseType
from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
    ExtractionLog,
)
from apps.legal_sources.models import LegalSource, LegalSourceAttachment
from apps.legal_sources.utils import compute_bytes_sha256

SOURCE_SLUG = "it-dpr-12-2025-tun-danno-biologico"

DATASET_NAME = "Tabella Unica Nazionale 2025 — danno biologico (art. 138 CAP)"
DATASET_VERSION_LABEL = "DPR-12-2025"
DATASET_CASE_TYPE = CaseType.ROAD_ACCIDENT_BODILY_INJURY.value

FORMULA_CODE = "italy_art_138_tun_2025_base"
FORMULA_NAME = "Calcolo base danno biologico art. 138 CAP — TUN 2025"
FORMULA_EXPRESSION = (
    "Schema documentale: il valore-punto è funzione di percentuale di "
    "invalidità ed età del danneggiato; ai sensi dell'art. 138 CAP la "
    "liquidazione segue la tabella allegata al D.P.R. 12/2025. La "
    "formula esatta deve essere convalidata dal revisore legale "
    "prima della promozione a `approved` e prima di qualsiasi uso "
    "operativo. Questa formula NON è eseguibile finché il dataset "
    "associato non è approvato."
)
FORMULA_SOURCE_REFERENCE = "D.P.R. 13 gennaio 2025 n. 12, art. 138 CAP"
FORMULA_PARAMETERS = {
    "permanent_disability_percentage": "input from wizard, integer 0..100",
    "victim_age": "input from wizard, integer 0..120",
    "fault_percentage": "optional reduction, integer 0..100",
}

# Colonne attese nel CSV di estrazione manuale. L'ordine non conta: il
# DictReader le riconosce per nome.
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


@dataclass
class _ImportOutcome:
    rows_imported: int = 0
    rows_skipped: int = 0
    errors: list[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class Command(BaseCommand):
    help = (
        "Importa la Tabella Unica Nazionale 2025 (D.P.R. 12/2025). Allega "
        "il PDF ufficiale, crea/aggiorna il CompensationDataset (sempre "
        "DRAFT) e, se fornito, importa le righe da un CSV di estrazione "
        "manuale. Mai approva alcunché."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source-file",
            dest="source_file",
            help="Path al PDF ufficiale del D.P.R. 12/2025.",
        )
        parser.add_argument(
            "--csv",
            dest="csv_file",
            help="Path al CSV di estrazione manuale delle righe TUN.",
        )

    def handle(self, *args, **options):
        source_file = options.get("source_file")
        csv_file = options.get("csv_file")

        if not source_file and not csv_file:
            raise CommandError(
                "Specifica almeno --source-file o --csv. Senza nessuno dei due "
                "il command non ha nulla da fare."
            )

        legal_source = self._get_legal_source()

        if source_file:
            self._handle_pdf_attach(legal_source, Path(source_file))

        # Il dataset esiste sempre dopo l'attach del PDF; se l'utente
        # passa solo --csv senza --source-file, lo creiamo qui in DRAFT.
        dataset = self._get_or_create_dataset(legal_source)
        self._get_or_create_formula(dataset)

        if csv_file:
            self._handle_csv_import(legal_source, dataset, Path(csv_file))

        self.stdout.write(
            self.style.SUCCESS(
                f"import_italy_tun_2025 completato. dataset={dataset.pk} "
                f"status={dataset.status} (mai promosso automaticamente)."
            )
        )

    # ------------------------------------------------------------------
    # Step 1 — recupero / creazione della LegalSource
    # ------------------------------------------------------------------

    def _get_legal_source(self) -> LegalSource:
        try:
            return LegalSource.objects.get(slug=SOURCE_SLUG)
        except LegalSource.DoesNotExist as exc:
            raise CommandError(
                f"LegalSource '{SOURCE_SLUG}' non trovata. Esegui prima "
                f"`python manage.py seed_italy_legal_sources`."
            ) from exc

    # ------------------------------------------------------------------
    # Step 2 — attach del PDF + log
    # ------------------------------------------------------------------

    def _handle_pdf_attach(self, legal_source: LegalSource, path: Path) -> None:
        if not path.exists() or not path.is_file():
            self._log_failure(
                legal_source,
                method=ExtractionLog.Method.PDF_ATTACH,
                file_path=str(path),
                error=f"PDF non trovato sul disco: {path}",
            )
            raise CommandError(f"PDF non trovato: {path}")

        payload = path.read_bytes()
        sha256 = compute_bytes_sha256(payload)
        size = len(payload)

        # Idempotenza: se esiste già un attachment con lo stesso hash per
        # questa fonte, non lo duplichiamo.
        existing = legal_source.attachments.filter(sha256=sha256).first()
        if existing:
            self._log_extraction(
                source=legal_source,
                dataset=None,
                method=ExtractionLog.Method.PDF_ATTACH,
                file_path=str(path),
                file_sha256=sha256,
                file_size=size,
                rows_imported=0,
                result=ExtractionLog.Result.SUCCESS,
                metadata={"attachment_id": existing.pk, "deduplicated": True},
            )
            self.stdout.write(f"  PDF già presente (hash {sha256[:12]}…), skip.")
            return

        mime, _ = mimetypes.guess_type(path.name)
        with path.open("rb") as fh:
            attachment = LegalSourceAttachment(
                source=legal_source,
                original_filename=path.name,
                mime_type=mime or "application/pdf",
                description="D.P.R. 12/2025 — testo ufficiale Gazzetta Ufficiale",
            )
            attachment.file.save(path.name, File(fh), save=False)
            attachment.size_bytes = size
            attachment.sha256 = sha256
            attachment.save()

        self._log_extraction(
            source=legal_source,
            dataset=None,
            method=ExtractionLog.Method.PDF_ATTACH,
            file_path=str(path),
            file_sha256=sha256,
            file_size=size,
            rows_imported=0,
            result=ExtractionLog.Result.SUCCESS,
            metadata={"attachment_id": attachment.pk},
        )
        self.stdout.write(f"  + PDF allegato (hash {sha256[:12]}…, size {size} B)")

    # ------------------------------------------------------------------
    # Step 3 — dataset + formula in DRAFT
    # ------------------------------------------------------------------

    def _get_or_create_dataset(self, legal_source: LegalSource) -> CompensationDataset:
        dataset, created = CompensationDataset.objects.get_or_create(
            source=legal_source,
            version_label=DATASET_VERSION_LABEL,
            defaults={
                "jurisdiction": legal_source.jurisdiction,
                "country": legal_source.country,
                "case_type": DATASET_CASE_TYPE,
                "name": DATASET_NAME,
                # Status DRAFT obbligatorio: la promozione è atto umano.
                "status": DatasetStatus.DRAFT,
                "valid_from": legal_source.effective_date,
                "notes": (
                    "Dataset importato da fonte ufficiale. Le righe "
                    "tabellari richiedono legal review prima di poter "
                    "essere usate dal calculator pubblico."
                ),
            },
        )
        if created:
            self.stdout.write(f"  + CompensationDataset creato (id={dataset.pk}, DRAFT)")
        else:
            self.stdout.write(f"  CompensationDataset già presente (id={dataset.pk})")
        return dataset

    def _get_or_create_formula(self, dataset: CompensationDataset) -> CalculationFormula:
        formula, created = CalculationFormula.objects.get_or_create(
            dataset=dataset,
            code=FORMULA_CODE,
            defaults={
                "name": FORMULA_NAME,
                "expression_text": FORMULA_EXPRESSION,
                "parameters": FORMULA_PARAMETERS,
                "source_reference": FORMULA_SOURCE_REFERENCE,
                # Sempre DRAFT: nessuna promozione automatica.
                "status": DatasetStatus.DRAFT,
                "notes": (
                    "Formula documentale, NON eseguibile finché il "
                    "dataset non è APPROVED e la formula stessa non è "
                    "stata validata dal revisore legale."
                ),
            },
        )
        if created:
            self.stdout.write(f"  + CalculationFormula creata ({FORMULA_CODE}, DRAFT)")
        else:
            self.stdout.write(f"  CalculationFormula già presente ({FORMULA_CODE})")
        return formula

    # ------------------------------------------------------------------
    # Step 4 — CSV import (righe DRAFT)
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

        outcome = self._import_csv_rows(dataset, path)

        if outcome.errors:
            result = (
                ExtractionLog.Result.PARTIAL
                if outcome.rows_imported > 0
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
            rows_imported=outcome.rows_imported,
            rows_skipped=outcome.rows_skipped,
            result=result,
            error_message="\n".join(outcome.errors)[:8000],
            metadata={"csv_columns": sorted(EXPECTED_CSV_COLUMNS)},
        )
        self.stdout.write(
            f"  CSV: {outcome.rows_imported} righe importate, "
            f"{outcome.rows_skipped} saltate, esito={result}."
        )

    @transaction.atomic
    def _import_csv_rows(self, dataset: CompensationDataset, path: Path) -> _ImportOutcome:
        outcome = _ImportOutcome()

        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            if reader.fieldnames is None:
                outcome.errors.append("CSV vuoto o senza header.")
                return outcome

            missing = EXPECTED_CSV_COLUMNS - set(reader.fieldnames)
            if missing:
                outcome.errors.append(f"CSV header incompleto: mancano colonne {sorted(missing)}.")
                return outcome

            # Idempotenza pragmatica: prima di un re-import, ripuliamo le
            # righe del dataset. Solo se il dataset è ancora DRAFT — un
            # dataset APPROVED non viene mai toccato dal command.
            if dataset.status != DatasetStatus.DRAFT:
                outcome.errors.append(
                    f"Dataset non più DRAFT (status={dataset.status}); "
                    "rifiuto di sovrascrivere righe già in revisione/approvate."
                )
                return outcome

            dataset.rows.all().delete()

            for line_no, row in enumerate(reader, start=2):
                try:
                    self._create_row_from_csv(dataset, row)
                    outcome.rows_imported += 1
                except (ValueError, InvalidOperation) as exc:
                    outcome.rows_skipped += 1
                    outcome.errors.append(f"Linea {line_no}: {exc}")

        return outcome

    def _create_row_from_csv(
        self, dataset: CompensationDataset, row: dict[str, str]
    ) -> CompensationTableRow:
        extra = {}
        if row.get("source_page"):
            extra["source_page"] = row["source_page"].strip()

        notes = (row.get("source_note") or "").strip()

        return CompensationTableRow.objects.create(
            dataset=dataset,
            row_type=(row.get("row_type") or "").strip(),
            age_min=_to_int_or_none(row.get("age_min")),
            age_max=_to_int_or_none(row.get("age_max")),
            disability_min=_to_int_or_none(row.get("disability_min")),
            disability_max=_to_int_or_none(row.get("disability_max")),
            point_value=_to_decimal_or_none(row.get("point_value")),
            coefficient=_to_decimal_or_none(row.get("coefficient")),
            daily_amount=_to_decimal_or_none(row.get("daily_amount")),
            extra=extra,
            notes=notes,
        )

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


# ---------------------------------------------------------------------------
# helpers di parsing CSV — tolleranti ma severi (no fallback silenziosi)
# ---------------------------------------------------------------------------


def _to_int_or_none(raw: str | None) -> int | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    return int(raw)  # ValueError → riga skippata, registrata negli errors


def _to_decimal_or_none(raw: str | None) -> Decimal | None:
    if raw is None:
        return None
    raw = raw.strip()
    if not raw:
        return None
    # Tolleriamo virgola decimale italiana ma esplicitamente: nessun
    # parsing implicito di "abbreviazioni" o "K". Solo numeri puliti.
    return Decimal(raw.replace(",", "."))
