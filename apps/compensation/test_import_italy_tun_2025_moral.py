"""
Tests for `import_italy_tun_2025_moral` — additive moral import command.

REGOLA D'ORO: nessun valore TUN reale nei test. I `Decimal` qui sono
SEGNAPOSTO sintattici (es. 1, 2, 3 EUR) per validare la meccanica del
command. La verifica numerica reale è atto umano dello Studio sui CSV
candidate, non un test automatizzato.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.calculators.enums import CaseType
from apps.compensation.management.commands.import_italy_tun_2025_moral import (
    BASE_SOURCE_SLUG,
    MORAL_DATASET_VERSION_LABEL,
)
from apps.compensation.models import (
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
    ExtractionLog,
)
from apps.compensation.test_fixtures import approved_source_version
from apps.jurisdictions.models import Country, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def italy(db) -> Country:
    return Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")


@pytest.fixture
def italy_jurisdiction(italy: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


@pytest.fixture
def italian(db) -> Language:
    return Language.objects.create(code="it", name="Italiano")


@pytest.fixture
def approved_tun_source(italy, italy_jurisdiction, italian) -> LegalSource:
    """Approved source matching BASE_SOURCE_SLUG, prerequisite of the command."""
    return LegalSource.objects.create(
        slug=BASE_SOURCE_SLUG,
        title="D.P.R. 12/2025 (test stub)",
        country=italy,
        jurisdiction=italy_jurisdiction,
        language=italian,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
        effective_date=date(2025, 1, 13),
    )


@pytest.fixture
def base_dataset_with_rows(approved_tun_source) -> CompensationDataset:
    """The Tabella 1 (biological) dataset, APPROVED, with two placeholder rows.

    Mirrors the production state: il base dataset ha già righe approved che
    DEVONO essere lasciate intatte dal command moral.
    """
    dataset = CompensationDataset.objects.create(
        source=approved_tun_source,
        source_version=approved_source_version(approved_tun_source),
        jurisdiction=approved_tun_source.jurisdiction,
        country=approved_tun_source.country,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN base (test)",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    # Two fixture rows with FAKE point_value (1 and 2 EUR — clearly placeholder).
    CompensationTableRow.objects.create(
        dataset=dataset,
        row_type="tun_biological_total_amount",
        age_min=0,
        age_max=0,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("1"),
    )
    CompensationTableRow.objects.create(
        dataset=dataset,
        row_type="tun_biological_total_amount",
        age_min=1,
        age_max=1,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("2"),
    )
    return dataset


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


CSV_HEADER = (
    "row_type,age_min,age_max,disability_min,disability_max,"
    "point_value,coefficient,daily_amount,source_page,source_note\n"
)


def _write_csv(tmp_path: Path, name: str, rows: list[str]) -> Path:
    p = tmp_path / name
    p.write_text(CSV_HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return p


def _moral_row(row_type: str, age: int, inv: int, pv: str, page: str = "41") -> str:
    return (
        f"{row_type},{age},{age},{inv},{inv},{pv},,,{page},"
        "extraction=automated_pdfplumber_iter2 ; ab_check_status=consistent"
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_command_does_not_delete_base_dataset_rows(base_dataset_with_rows, tmp_path):
    """Importare CSV moral NON cancella le righe del dataset base APPROVED."""
    base_count_before = base_dataset_with_rows.rows.count()
    csv_path = _write_csv(
        tmp_path,
        "moral_min.csv",
        [_moral_row("tun_biological_moral_min_total_amount", 0, 10, "10")],
    )

    call_command("import_italy_tun_2025_moral", "--csv", str(csv_path))

    base_dataset_with_rows.refresh_from_db()
    assert base_dataset_with_rows.rows.count() == base_count_before
    assert base_dataset_with_rows.status == DatasetStatus.APPROVED


@pytest.mark.django_db
def test_command_creates_separate_moral_dataset_in_draft(approved_tun_source, tmp_path):
    """Il command crea un dataset MORAL distinto, status DRAFT."""
    assert not CompensationDataset.objects.filter(
        version_label=MORAL_DATASET_VERSION_LABEL
    ).exists()

    csv_path = _write_csv(
        tmp_path,
        "moral_min.csv",
        [_moral_row("tun_biological_moral_min_total_amount", 0, 10, "10")],
    )
    call_command("import_italy_tun_2025_moral", "--csv", str(csv_path))

    moral = CompensationDataset.objects.get(version_label=MORAL_DATASET_VERSION_LABEL)
    assert moral.status == DatasetStatus.DRAFT
    assert moral.source_id == approved_tun_source.pk
    assert moral.case_type == CaseType.ROAD_ACCIDENT_BODILY_INJURY.value


@pytest.mark.django_db
def test_command_rejects_non_moral_row_types(approved_tun_source, tmp_path):
    """row_type non in ALLOWED_MORAL_ROW_TYPES viene scartato e segnalato."""
    csv_path = _write_csv(
        tmp_path,
        "bad.csv",
        [
            # tipo "base" (Tabella 1) — vietato in import moral
            _moral_row("tun_biological_total_amount", 0, 10, "10"),
            # tipo inventato — vietato
            _moral_row("invented_row_type", 0, 10, "10"),
        ],
    )
    out = StringIO()
    call_command("import_italy_tun_2025_moral", "--csv", str(csv_path), stdout=out)

    moral = CompensationDataset.objects.get(version_label=MORAL_DATASET_VERSION_LABEL)
    # Nessuna riga creata nel dataset moral.
    assert moral.rows.count() == 0
    # Log con esito FAILED (zero righe importate).
    log = ExtractionLog.objects.filter(dataset=moral).latest("created_at")
    assert log.result == ExtractionLog.Result.FAILED
    assert log.rows_skipped == 2
    assert "non ammesso" in log.error_message


@pytest.mark.django_db
def test_command_is_idempotent_via_upsert(approved_tun_source, tmp_path):
    """Re-running the same CSV non duplica le righe e non cresce la tabella."""
    rows = [
        _moral_row("tun_biological_moral_min_total_amount", 0, 10, "10"),
        _moral_row("tun_biological_moral_min_total_amount", 1, 10, "11"),
    ]
    csv_path = _write_csv(tmp_path, "moral_min.csv", rows)

    call_command("import_italy_tun_2025_moral", "--csv", str(csv_path))
    first = CompensationTableRow.objects.filter(
        dataset__version_label=MORAL_DATASET_VERSION_LABEL
    ).count()
    assert first == 2

    # Run again — should upsert, count stays 2.
    call_command("import_italy_tun_2025_moral", "--csv", str(csv_path))
    second = CompensationTableRow.objects.filter(
        dataset__version_label=MORAL_DATASET_VERSION_LABEL
    ).count()
    assert second == 2

    # Re-run con valori cambiati → update_or_create aggiorna, count resta 2.
    rows_updated = [
        _moral_row("tun_biological_moral_min_total_amount", 0, 10, "99"),
        _moral_row("tun_biological_moral_min_total_amount", 1, 10, "100"),
    ]
    csv_updated = _write_csv(tmp_path, "moral_min_v2.csv", rows_updated)
    call_command("import_italy_tun_2025_moral", "--csv", str(csv_updated))
    third = CompensationTableRow.objects.filter(
        dataset__version_label=MORAL_DATASET_VERSION_LABEL
    ).count()
    assert third == 2

    # I valori sono stati aggiornati.
    row = CompensationTableRow.objects.get(
        dataset__version_label=MORAL_DATASET_VERSION_LABEL,
        age_min=0,
        disability_min=10,
    )
    assert row.point_value == Decimal("99")


@pytest.mark.django_db
def test_command_logs_extraction_log(approved_tun_source, tmp_path):
    """Ogni esecuzione del command registra un ExtractionLog."""
    csv_path = _write_csv(
        tmp_path,
        "moral_min.csv",
        [_moral_row("tun_biological_moral_min_total_amount", 0, 10, "10")],
    )
    call_command("import_italy_tun_2025_moral", "--csv", str(csv_path))

    log = ExtractionLog.objects.filter(dataset__version_label=MORAL_DATASET_VERSION_LABEL).latest(
        "created_at"
    )
    assert log.method == ExtractionLog.Method.CSV_IMPORT
    assert log.result == ExtractionLog.Result.SUCCESS
    assert log.rows_imported == 1
    assert log.metadata.get("additive") is True


@pytest.mark.django_db
def test_command_does_not_change_base_dataset_status(base_dataset_with_rows, tmp_path):
    """Lo status del dataset base APPROVED non viene mai toccato."""
    csv_path = _write_csv(
        tmp_path,
        "moral_min.csv",
        [_moral_row("tun_biological_moral_min_total_amount", 0, 10, "10")],
    )
    call_command("import_italy_tun_2025_moral", "--csv", str(csv_path))

    base_dataset_with_rows.refresh_from_db()
    assert base_dataset_with_rows.status == DatasetStatus.APPROVED
    # Verifica che il base dataset NON sia stato confuso con quello moral.
    assert base_dataset_with_rows.version_label == "DPR-12-2025"


@pytest.mark.django_db
def test_command_rejects_empty_point_value(approved_tun_source, tmp_path):
    """Una riga con point_value vuoto è rifiutata e contata in rows_skipped."""
    csv_path = _write_csv(
        tmp_path,
        "moral_min.csv",
        [
            # point_value vuoto
            "tun_biological_moral_min_total_amount,0,0,10,10,,,,41,extraction=test",
        ],
    )
    call_command("import_italy_tun_2025_moral", "--csv", str(csv_path))

    moral = CompensationDataset.objects.get(version_label=MORAL_DATASET_VERSION_LABEL)
    assert moral.rows.count() == 0
    log = ExtractionLog.objects.filter(dataset=moral).latest("created_at")
    assert log.result == ExtractionLog.Result.FAILED
    assert log.rows_skipped == 1


@pytest.mark.django_db
def test_command_refuses_when_moral_dataset_is_not_draft(
    approved_tun_source, italy, italy_jurisdiction, tmp_path
):
    """Difesa: se per qualche motivo il dataset moral è approved, il command si rifiuta."""
    CompensationDataset.objects.create(
        source=approved_tun_source,
        source_version=approved_source_version(approved_tun_source),
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="TUN moral (already approved by mistake)",
        version_label=MORAL_DATASET_VERSION_LABEL,
        status=DatasetStatus.APPROVED,
        valid_from=date(2025, 1, 13),
    )
    csv_path = _write_csv(
        tmp_path,
        "moral_min.csv",
        [_moral_row("tun_biological_moral_min_total_amount", 0, 10, "10")],
    )
    with pytest.raises(CommandError, match="non in DRAFT"):
        call_command("import_italy_tun_2025_moral", "--csv", str(csv_path))


def test_command_source_has_no_destructive_delete():
    """Smoke statico: il body del command non chiama `.delete()` su rows.

    Strippiamo docstring e commenti — la docstring DESCRIVE perché il
    command non fa delete, quindi contiene legittimamente la stringa.
    Il vincolo è sul codice eseguibile.
    """
    import ast

    cmd_module = Path("apps/compensation/management/commands/import_italy_tun_2025_moral.py")
    src = cmd_module.read_text(encoding="utf-8")
    tree = ast.parse(src)
    # Cerca chiamate `something.delete(...)` nel body.
    bad_calls: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if node.func.attr == "delete":
                bad_calls.append(ast.unparse(node))
    assert bad_calls == [], f"Trovate chiamate .delete() nel command moral: {bad_calls}"
