"""
Tests F-sources-italy — apps.compensation.

Verifichiamo i vincoli strutturali sui dataset di compensazione:
- un dataset APPROVED richiede una fonte APPROVED;
- una formula APPROVED richiede un dataset APPROVED;
- la creazione di un dataset DRAFT è sempre permessa, anche con fonte
  in `needs_review`;
- valid_to deve essere ≥ valid_from;
- nessun valore monetario reale è hardcoded nei test (regola d'oro).

NESSUN test usa importi o coefficienti reali. I `Decimal` qui sono
volutamente segnaposto sintattici per validare la persistenza, mai per
rappresentare un valore legale.
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError

from apps.calculators.enums import CaseType
from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
)
from apps.jurisdictions.models import Country, Jurisdiction
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource


@pytest.fixture
def italy(db) -> Country:
    return Country.objects.create(code="IT", code_alpha3="ITA", name="Italia")


@pytest.fixture
def italy_jurisdiction(db, italy: Country) -> Jurisdiction:
    return Jurisdiction.objects.create(
        country=italy,
        code="IT-NATIONAL",
        name="Italia (livello nazionale)",
        legal_system=Jurisdiction.LegalSystem.CIVIL_LAW,
    )


def _approved_source(italy, italy_jurisdiction, italian_language=None):
    from apps.jurisdictions.models import Language

    language = italian_language or Language.objects.create(code="it", name="Italiano")
    return LegalSource.objects.create(
        title="D.P.R. placeholder per test",
        country=italy,
        jurisdiction=italy_jurisdiction,
        language=language,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.APPROVED,
        publication_date=date(2025, 2, 11),
    )


def _needs_review_source(italy, italy_jurisdiction):
    return LegalSource.objects.create(
        title="Fonte in revisione",
        country=italy,
        jurisdiction=italy_jurisdiction,
        source_type=SourceType.MINISTRY_DECREE,
        status=SourceStatus.NEEDS_REVIEW,
    )


# ---------------------------------------------------------------------------
# CompensationDataset
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_compensation_dataset_default_status_is_draft(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Placeholder dataset",
    )
    assert dataset.status == DatasetStatus.DRAFT
    assert dataset.is_usable_for_calculations is False


@pytest.mark.django_db
def test_dataset_cannot_be_approved_if_source_is_not_approved(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Premature approval",
        status=DatasetStatus.APPROVED,
    )
    with pytest.raises(ValidationError) as exc:
        dataset.full_clean()
    assert "status" in exc.value.error_dict


@pytest.mark.django_db
def test_dataset_can_be_approved_when_source_is_approved(italy, italy_jurisdiction):
    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Validly approved",
        status=DatasetStatus.APPROVED,
    )
    # Non deve sollevare.
    dataset.full_clean()
    dataset.save()
    assert dataset.is_usable_for_calculations is True


@pytest.mark.django_db
def test_dataset_valid_to_must_be_gte_valid_from(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Bad date range",
        valid_from=date(2025, 6, 1),
        valid_to=date(2025, 1, 1),
    )
    with pytest.raises(ValidationError) as exc:
        dataset.full_clean()
    assert "valid_to" in exc.value.error_dict


# ---------------------------------------------------------------------------
# CompensationTableRow
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_table_row_age_max_must_be_gte_age_min(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Dataset with rows",
    )
    row = CompensationTableRow(
        dataset=dataset,
        age_min=40,
        age_max=20,
    )
    with pytest.raises(ValidationError) as exc:
        row.full_clean()
    assert "age_max" in exc.value.error_dict


@pytest.mark.django_db
def test_table_row_disability_max_must_be_gte_disability_min(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Dataset with rows",
    )
    row = CompensationTableRow(
        dataset=dataset,
        disability_min=30,
        disability_max=10,
    )
    with pytest.raises(ValidationError) as exc:
        row.full_clean()
    assert "disability_max" in exc.value.error_dict


@pytest.mark.django_db
def test_table_row_can_persist_decimal_placeholders(italy, italy_jurisdiction):
    """
    Persistenza tecnica di valori decimal: la struttura accetta numeri.
    NON è un test su importi reali — i Decimal qui sono segnaposto.
    """
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Dataset for placeholder",
    )
    row = CompensationTableRow.objects.create(
        dataset=dataset,
        row_type="placeholder_only",
        point_value=Decimal("1.0000"),
        coefficient=Decimal("1.000000"),
    )
    row.full_clean()
    assert row.dataset_id == dataset.pk


# ---------------------------------------------------------------------------
# CalculationFormula
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_formula_cannot_be_approved_when_dataset_is_not(italy, italy_jurisdiction):
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Draft dataset",
    )
    formula = CalculationFormula(
        dataset=dataset,
        code="placeholder_formula",
        name="Placeholder formula",
        status=DatasetStatus.APPROVED,
    )
    with pytest.raises(ValidationError) as exc:
        formula.full_clean()
    assert "status" in exc.value.error_dict


@pytest.mark.django_db
def test_formula_can_be_approved_when_dataset_is_approved(italy, italy_jurisdiction):
    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Approved dataset",
        status=DatasetStatus.APPROVED,
    )
    formula = CalculationFormula(
        dataset=dataset,
        code="placeholder_formula",
        name="Placeholder formula",
        status=DatasetStatus.APPROVED,
    )
    formula.full_clean()
    formula.save()
    assert formula.pk is not None


@pytest.mark.django_db
def test_formula_unique_code_per_dataset(italy, italy_jurisdiction):
    from django.db import IntegrityError

    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Dataset with formulas",
    )
    CalculationFormula.objects.create(dataset=dataset, code="dup_code", name="First")
    with pytest.raises(IntegrityError):
        CalculationFormula.objects.create(dataset=dataset, code="dup_code", name="Second")


# ---------------------------------------------------------------------------
# Calculator non sblocca importi senza dataset approvato
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_calculator_with_approved_source_but_no_dataset_remains_unavailable(
    italy, italy_jurisdiction
):
    """
    Anche con fonte APPROVED, in assenza di dataset/formule APPROVED il
    calculator placeholder italiano resta `unavailable_requires_legal_validation`.
    Conferma che l'esistenza della fonte da sola NON sblocca importi.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    _approved_source(italy, italy_jurisdiction)
    # Nessun CompensationDataset creato.

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})

    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.estimated_min is None
    assert result.estimated_mid is None
    assert result.estimated_max is None


@pytest.mark.django_db
def test_dataset_with_draft_status_does_not_unlock_calculation(italy, italy_jurisdiction):
    """
    Anche con fonte APPROVED + dataset esistente ma in DRAFT, il
    calculator non produce importi (il placeholder F4 non li produce
    neanche con dataset, e quando arriverà l'engine reale leggerà solo
    `is_usable_for_calculations` == True).
    """
    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Draft dataset",
        status=DatasetStatus.DRAFT,
    )
    assert dataset.is_usable_for_calculations is False


# ---------------------------------------------------------------------------
# Coerenza temporale dataset vs source
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_dataset_validity_window_can_predate_today(italy, italy_jurisdiction):
    """
    Un dataset può avere `valid_from` antecedente a oggi: serve per
    simulazioni datate. Test puramente strutturale, nessun importo.
    """
    src = _needs_review_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Past dataset",
        valid_from=date.today() - timedelta(days=365),
        valid_to=date.today() - timedelta(days=1),
    )
    dataset.full_clean()
    assert dataset.valid_to < date.today()


# ---------------------------------------------------------------------------
# F-extract-italy-tun — import_italy_tun_2025 + 3-level gating
# ---------------------------------------------------------------------------


def _ensure_italian_seed():
    """Esegue il seed metadata necessario al command (idempotente)."""
    from django.core.management import call_command

    call_command("seed_italy_legal_sources", "--quiet")


@pytest.fixture
def fake_pdf_file(tmp_path):
    """File 'PDF' fittizio: bytes arbitrari, header PDF-like per mime."""
    path = tmp_path / "dpr_12_2025_tun.pdf"
    # Bytes test-only. Non rappresentano un PDF reale del decreto. Sono
    # sufficienti perché il command li hashi e li alleghi come blob.
    path.write_bytes(b"%PDF-1.7\n% test fixture only - non un PDF reale\n")
    return path


@pytest.fixture
def fake_csv_file(tmp_path):
    """
    CSV test-only con UNA riga di placeholder (nessun valore reale).

    I valori sono volutamente fuori scala (`row_type=test_placeholder`,
    point_value=1.0) per evidenziare che NON sono dati legali. Il test
    valida solo che il pipeline di import funzioni.
    """
    path = tmp_path / "tun_2025_rows.csv"
    path.write_text(
        "row_type,age_min,age_max,disability_min,disability_max,"
        "point_value,coefficient,daily_amount,source_page,source_note\n"
        "test_placeholder,30,40,10,20,1.0000,1.000000,,12,fixture row only\n",
        encoding="utf-8",
    )
    return path


@pytest.mark.django_db
def test_import_command_fails_on_missing_pdf(tmp_path):
    """File PDF inesistente → CommandError + ExtractionLog FAILED."""
    from django.core.management import call_command
    from django.core.management.base import CommandError

    from apps.compensation.models import ExtractionLog

    _ensure_italian_seed()
    missing = tmp_path / "does_not_exist.pdf"

    with pytest.raises(CommandError):
        call_command("import_italy_tun_2025", "--source-file", str(missing))

    log = ExtractionLog.objects.first()
    assert log is not None
    assert log.result == ExtractionLog.Result.FAILED
    assert log.method == ExtractionLog.Method.PDF_ATTACH
    assert "does_not_exist" in log.file_path


@pytest.mark.django_db
def test_import_command_fails_on_missing_csv(tmp_path):
    """File CSV inesistente → CommandError + ExtractionLog FAILED."""
    from django.core.management import call_command
    from django.core.management.base import CommandError

    from apps.compensation.models import ExtractionLog

    _ensure_italian_seed()
    missing = tmp_path / "does_not_exist.csv"

    with pytest.raises(CommandError):
        call_command("import_italy_tun_2025", "--csv", str(missing))

    log = ExtractionLog.objects.filter(result=ExtractionLog.Result.FAILED).first()
    assert log is not None
    assert log.method == ExtractionLog.Method.CSV_IMPORT


@pytest.mark.django_db
def test_import_command_requires_at_least_one_arg():
    """Senza --source-file e senza --csv il command rifiuta di avviarsi."""
    from django.core.management import call_command
    from django.core.management.base import CommandError

    _ensure_italian_seed()
    with pytest.raises(CommandError):
        call_command("import_italy_tun_2025")


@pytest.mark.django_db
def test_import_command_requires_seed_already_run(tmp_path):
    """Senza la LegalSource seedata il command si rifiuta di proseguire."""
    from django.core.management import call_command
    from django.core.management.base import CommandError

    pdf = tmp_path / "dpr_12_2025_tun.pdf"
    pdf.write_bytes(b"%PDF-1.7\n")
    with pytest.raises(CommandError):
        call_command("import_italy_tun_2025", "--source-file", str(pdf))


@pytest.mark.django_db
def test_import_command_creates_dataset_in_draft(fake_pdf_file):
    """Pipeline base: PDF → attachment + dataset DRAFT + formula DRAFT."""
    from django.core.management import call_command

    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        ExtractionLog,
    )

    _ensure_italian_seed()
    call_command("import_italy_tun_2025", "--source-file", str(fake_pdf_file))

    dataset = CompensationDataset.objects.get(version_label="DPR-12-2025")
    assert dataset.status == DatasetStatus.DRAFT
    assert dataset.case_type == CaseType.ROAD_ACCIDENT_BODILY_INJURY.value

    formula = CalculationFormula.objects.get(dataset=dataset)
    assert formula.status == DatasetStatus.DRAFT
    assert formula.code == "italy_art_138_tun_2025_base"

    # ExtractionLog scritto.
    log = ExtractionLog.objects.filter(method=ExtractionLog.Method.PDF_ATTACH).first()
    assert log is not None
    assert log.result == ExtractionLog.Result.SUCCESS
    assert log.file_sha256 != ""


@pytest.mark.django_db
def test_import_command_does_not_promote_source(fake_pdf_file):
    """La fonte resta NEEDS_REVIEW dopo l'import."""
    from django.core.management import call_command

    _ensure_italian_seed()
    call_command("import_italy_tun_2025", "--source-file", str(fake_pdf_file))

    src = LegalSource.objects.get(slug="it-dpr-12-2025-tun-danno-biologico")
    assert src.status == SourceStatus.NEEDS_REVIEW


@pytest.mark.django_db
def test_import_command_is_idempotent(fake_pdf_file):
    """Re-run senza nuovi file: nessun duplicato di attachment, dataset, formula."""
    from django.core.management import call_command

    from apps.compensation.models import (
        CalculationFormula,
        CompensationDataset,
        ExtractionLog,
    )
    from apps.legal_sources.models import LegalSourceAttachment

    _ensure_italian_seed()
    call_command("import_italy_tun_2025", "--source-file", str(fake_pdf_file))
    call_command("import_italy_tun_2025", "--source-file", str(fake_pdf_file))

    assert LegalSourceAttachment.objects.count() == 1
    assert CompensationDataset.objects.count() == 1
    assert CalculationFormula.objects.count() == 1
    # Due ExtractionLog (uno per run), entrambi SUCCESS.
    assert (
        ExtractionLog.objects.filter(
            method=ExtractionLog.Method.PDF_ATTACH,
            result=ExtractionLog.Result.SUCCESS,
        ).count()
        == 2
    )


@pytest.mark.django_db
def test_import_command_imports_csv_rows_in_draft(fake_pdf_file, fake_csv_file):
    """CSV → righe DRAFT. ExtractionLog success con rows_imported=1."""
    from django.core.management import call_command

    from apps.compensation.models import (
        CompensationDataset,
        CompensationTableRow,
        ExtractionLog,
    )

    _ensure_italian_seed()
    call_command(
        "import_italy_tun_2025",
        "--source-file",
        str(fake_pdf_file),
        "--csv",
        str(fake_csv_file),
    )

    dataset = CompensationDataset.objects.get(version_label="DPR-12-2025")
    rows = CompensationTableRow.objects.filter(dataset=dataset)
    assert rows.count() == 1
    row = rows.first()
    assert row.row_type == "test_placeholder"
    assert row.age_min == 30 and row.age_max == 40
    assert row.disability_min == 10 and row.disability_max == 20

    # Dataset resta DRAFT (no auto-approve).
    assert dataset.status == DatasetStatus.DRAFT

    csv_log = ExtractionLog.objects.filter(method=ExtractionLog.Method.CSV_IMPORT).first()
    assert csv_log is not None
    assert csv_log.result == ExtractionLog.Result.SUCCESS
    assert csv_log.rows_imported == 1


@pytest.mark.django_db
def test_import_command_csv_rejects_bad_header(tmp_path, fake_pdf_file):
    """CSV con header incompleto → ExtractionLog FAILED, niente righe."""
    from django.core.management import call_command

    from apps.compensation.models import (
        CompensationDataset,
        CompensationTableRow,
        ExtractionLog,
    )

    _ensure_italian_seed()
    call_command("import_italy_tun_2025", "--source-file", str(fake_pdf_file))

    bad_csv = tmp_path / "bad.csv"
    bad_csv.write_text("only_one_column\nfoo\n", encoding="utf-8")
    call_command("import_italy_tun_2025", "--csv", str(bad_csv))

    dataset = CompensationDataset.objects.get(version_label="DPR-12-2025")
    assert CompensationTableRow.objects.filter(dataset=dataset).count() == 0

    log = ExtractionLog.objects.filter(method=ExtractionLog.Method.CSV_IMPORT).first()
    assert log is not None
    assert log.result == ExtractionLog.Result.FAILED
    assert "header" in log.error_message.lower()


@pytest.mark.django_db
def test_import_command_csv_skips_invalid_rows(tmp_path, fake_pdf_file):
    """Una riga con valori non parsabili → skip + log PARTIAL."""
    from django.core.management import call_command

    from apps.compensation.models import (
        CompensationDataset,
        CompensationTableRow,
        ExtractionLog,
    )

    _ensure_italian_seed()
    call_command("import_italy_tun_2025", "--source-file", str(fake_pdf_file))

    csv_path = tmp_path / "mixed.csv"
    csv_path.write_text(
        "row_type,age_min,age_max,disability_min,disability_max,"
        "point_value,coefficient,daily_amount,source_page,source_note\n"
        "good_row,20,30,5,10,1.0,1.0,,1,\n"
        "bad_row,not_a_number,40,10,20,1.0,1.0,,2,\n",
        encoding="utf-8",
    )
    call_command("import_italy_tun_2025", "--csv", str(csv_path))

    dataset = CompensationDataset.objects.get(version_label="DPR-12-2025")
    rows = CompensationTableRow.objects.filter(dataset=dataset)
    assert rows.count() == 1
    assert rows.first().row_type == "good_row"

    log = ExtractionLog.objects.filter(method=ExtractionLog.Method.CSV_IMPORT).first()
    assert log is not None
    assert log.result == ExtractionLog.Result.PARTIAL
    assert log.rows_imported == 1
    assert log.rows_skipped == 1


@pytest.mark.django_db
def test_import_command_refuses_to_overwrite_non_draft_dataset(fake_pdf_file, fake_csv_file):
    """
    Se il dataset non è più DRAFT (es. il revisore l'ha promosso a
    NEEDS_REVIEW o APPROVED), il command CSV non sovrascrive le righe.
    """
    from django.core.management import call_command

    from apps.compensation.models import (
        CompensationDataset,
        CompensationTableRow,
        ExtractionLog,
    )

    _ensure_italian_seed()
    call_command("import_italy_tun_2025", "--source-file", str(fake_pdf_file))
    call_command("import_italy_tun_2025", "--csv", str(fake_csv_file))

    dataset = CompensationDataset.objects.get(version_label="DPR-12-2025")
    assert CompensationTableRow.objects.filter(dataset=dataset).count() == 1

    # Promozione manuale a NEEDS_REVIEW (simula intervento dello Studio).
    dataset.status = DatasetStatus.NEEDS_REVIEW
    dataset.save(update_fields=["status"])

    # Re-run del CSV: il command rifiuta di toccare le righe.
    call_command("import_italy_tun_2025", "--csv", str(fake_csv_file))
    assert CompensationTableRow.objects.filter(dataset=dataset).count() == 1

    last_log = (
        ExtractionLog.objects.filter(method=ExtractionLog.Method.CSV_IMPORT)
        .order_by("-created_at")
        .first()
    )
    assert last_log.result == ExtractionLog.Result.FAILED
    assert "DRAFT" in last_log.error_message


# ---------------------------------------------------------------------------
# Calculator gating a 3 livelli
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_calculator_gate_level1_no_approved_source(italy, italy_jurisdiction):
    """Livello 1: nessuna fonte APPROVED → unavailable, niente gating successivo."""
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    _needs_review_source(italy, italy_jurisdiction)
    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})
    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.sources == []
    # Nessun missing_documents: il primo gate è la fonte stessa.


@pytest.mark.django_db
def test_calculator_gate_level2_dataset_draft(italy, italy_jurisdiction):
    """
    Livello 2: fonte APPROVED ma dataset DRAFT → unavailable con
    missing_documents=['compensation_dataset_approved'].
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    src = _approved_source(italy, italy_jurisdiction)
    CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Draft dataset",
        status=DatasetStatus.DRAFT,
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})

    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_dataset_approved" in result.missing_documents
    assert result.estimated_min is None


@pytest.mark.django_db
def test_calculator_gate_level3_formula_draft(italy, italy_jurisdiction):
    """
    Livello 3: fonte + dataset APPROVED, formula DRAFT → unavailable con
    missing_documents=['calculation_formula_approved'].
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Approved dataset",
        status=DatasetStatus.APPROVED,
    )
    CalculationFormula.objects.create(
        dataset=dataset,
        code="placeholder",
        name="Placeholder",
        status=DatasetStatus.DRAFT,
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})

    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "calculation_formula_approved" in result.missing_documents
    assert result.estimated_min is None


@pytest.mark.django_db
def test_calculator_does_not_invent_amounts_even_with_all_approved(italy, italy_jurisdiction):
    """
    Anche con fonte + dataset + formula tutti APPROVED, in F-extract-italy-tun
    l'engine economico non è ancora implementato: il calculator deve
    restituire `unavailable` con missing_documents=['economic_engine_implementation'].
    NON deve inventare importi.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Fully approved dataset",
        status=DatasetStatus.APPROVED,
    )
    CalculationFormula.objects.create(
        dataset=dataset,
        code="approved_formula",
        name="Approved formula",
        status=DatasetStatus.APPROVED,
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})

    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.estimated_min is None
    assert result.estimated_mid is None
    assert result.estimated_max is None
    assert "economic_engine_implementation" in result.missing_documents
