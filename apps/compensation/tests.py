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
def test_calculator_with_all_approved_but_unknown_engine_stays_unavailable(
    italy, italy_jurisdiction
):
    """
    Fonte + dataset + formula tutti APPROVED ma `parameters.engine` non è
    nei registri supportati: il calculator NON tira a indovinare,
    restituisce `unavailable` con missing=`formula_engine_unknown`.
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
        parameters={},  # nessun engine dichiarato → engine_unknown
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({})

    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert result.estimated_min is None
    assert result.estimated_mid is None
    assert result.estimated_max is None
    assert "formula_engine_unknown" in result.missing_documents


# ---------------------------------------------------------------------------
# F-italy-engine-implementation — engine economico Italia road accident
#
# REGOLA TEST: nessun valore reale TUN. Le `point_value` qui sono fixture
# fittizie (es. Decimal("1.0000")) volutamente fuori scala. Servono solo
# a dimostrare che la pipeline matematica funziona, non a rappresentare
# importi legali. Sono chiaramente etichettate con `notes="fixture only"`.
# ---------------------------------------------------------------------------


def _build_full_stack(
    italy, italy_jurisdiction, *, formula_parameters=None, with_row=True, point_value=None
):
    """
    Helper di scenario: crea una catena fonte/dataset/formula tutti
    APPROVED. Restituisce (source, dataset, formula, row_or_none).
    """
    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Test-only dataset (NOT real TUN data)",
        version_label="DPR-12-2025",
        status=DatasetStatus.APPROVED,
    )
    formula = CalculationFormula.objects.create(
        dataset=dataset,
        code="italy_art_138_tun_2025_base",
        name="Test-only formula",
        status=DatasetStatus.APPROVED,
        parameters=formula_parameters
        or {
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "point_value_times_disability_percentage",
            "fault_reduction": False,
        },
    )
    row = None
    if with_row:
        row = CompensationTableRow.objects.create(
            dataset=dataset,
            row_type="point_value",
            age_min=0,
            age_max=120,
            disability_min=0,
            disability_max=100,
            point_value=point_value or Decimal("1.0000"),  # fixture only
            notes="fixture only — NOT a real TUN value",
        )
    return src, dataset, formula, row


@pytest.fixture
def full_approved_stack(italy, italy_jurisdiction):
    return _build_full_stack(italy, italy_jurisdiction)


# --- happy path -----------------------------------------------------------


@pytest.mark.django_db
def test_calculator_calculated_with_full_stack_and_sufficient_input(full_approved_stack):
    """
    Tutto APPROVED + input sufficiente + riga match → CALCULATED con
    estimated_* non nulli, breakdown popolato, confidence medium.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus, ConfidenceLevel

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})

    assert result.status == CalculationStatus.CALCULATED.value
    assert result.confidence == ConfidenceLevel.MEDIUM.value
    # 1.0 (fixture) × 10 = 10
    assert result.estimated_min == Decimal("10.0000")
    assert result.estimated_mid == Decimal("10.0000")
    assert result.estimated_max == Decimal("10.0000")
    assert result.estimated_min <= result.estimated_mid <= result.estimated_max
    assert len(result.breakdown) == 1
    assert result.breakdown[0].label == "Danno biologico permanente"


@pytest.mark.django_db
def test_breakdown_references_source_and_formula(full_approved_stack):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    src, _, formula, _ = full_approved_stack
    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})

    item = result.breakdown[0]
    assert item.formula == formula.code
    # source_ref_ids contiene almeno la fonte approvata.
    assert src.pk in item.source_ref_ids
    # Le fonti complessive del risultato non sono vuote.
    assert len(result.sources) >= 1


@pytest.mark.django_db
def test_calculated_result_is_json_serializable(full_approved_stack):
    import json

    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})
    payload = json.loads(result.to_json())
    assert payload["status"] == "calculated"
    assert payload["estimated_min"] == "10.0000"
    assert payload["legal_disclaimer"]
    assert payload["breakdown"][0]["label"] == "Danno biologico permanente"


# --- input validation -----------------------------------------------------


@pytest.mark.django_db
def test_missing_victim_age_returns_insufficient_input(full_approved_stack):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"permanent_disability_percentage": 10})
    assert result.status == CalculationStatus.INSUFFICIENT_INPUT.value
    assert any("victim_age" in w for w in result.warnings)
    assert result.estimated_min is None


@pytest.mark.django_db
def test_missing_disability_returns_insufficient_input(full_approved_stack):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30})
    assert result.status == CalculationStatus.INSUFFICIENT_INPUT.value
    assert any("permanent_disability_percentage" in w for w in result.warnings)


@pytest.mark.django_db
def test_fault_percentage_out_of_range_returns_insufficient_input(
    full_approved_stack,
):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute(
        {
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "fault_percentage": 150,
        }
    )
    assert result.status == CalculationStatus.INSUFFICIENT_INPUT.value
    assert any("fault_percentage" in w.lower() for w in result.warnings)


# --- formula gating: engine / amount_rule -------------------------------


@pytest.mark.django_db
def test_formula_with_unknown_engine_returns_unavailable(italy, italy_jurisdiction):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    _build_full_stack(
        italy,
        italy_jurisdiction,
        formula_parameters={"engine": "made_up_engine_v1"},
    )
    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})
    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_engine_unknown" in result.missing_documents


@pytest.mark.django_db
def test_formula_with_known_engine_unknown_rule_returns_unavailable(italy, italy_jurisdiction):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    _build_full_stack(
        italy,
        italy_jurisdiction,
        formula_parameters={
            "engine": "italy_tun_point_value_v1",
            "amount_rule": "made_up_rule_xyz",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
        },
    )
    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})
    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "formula_amount_rule_unknown" in result.missing_documents


# --- row matching --------------------------------------------------------


@pytest.mark.django_db
def test_no_matching_row_returns_unavailable(italy, italy_jurisdiction):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    src, dataset, formula, _ = _build_full_stack(italy, italy_jurisdiction, with_row=False)
    # Crea una riga che NON copre il range richiesto.
    CompensationTableRow.objects.create(
        dataset=dataset,
        row_type="point_value",
        age_min=70,
        age_max=80,
        disability_min=50,
        disability_max=100,
        point_value=Decimal("1.0000"),
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})
    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_row_match" in result.missing_documents


@pytest.mark.django_db
def test_multiple_matching_rows_returns_unavailable_no_arbitrary_choice(italy, italy_jurisdiction):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    src, dataset, formula, _ = _build_full_stack(italy, italy_jurisdiction, with_row=False)
    # Due righe che entrambe matchano l'input → engine deve rifiutarsi
    # di scegliere a caso.
    for i in range(2):
        CompensationTableRow.objects.create(
            dataset=dataset,
            row_type="point_value",
            age_min=0,
            age_max=120,
            disability_min=0,
            disability_max=100,
            point_value=Decimal(str(i + 1)),
            notes=f"fixture row {i}",
        )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})
    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_row_disambiguation" in result.missing_documents
    assert result.estimated_min is None


# --- fault reduction toggle ----------------------------------------------


@pytest.mark.django_db
def test_fault_reduction_applied_only_when_formula_enables_it(italy, italy_jurisdiction):
    """
    Con `fault_reduction=True` nella formula e fault_percentage=50,
    l'importo deve dimezzarsi. Con `fault_reduction=False`, no.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    _build_full_stack(
        italy,
        italy_jurisdiction,
        formula_parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "point_value_times_disability_percentage",
            "fault_reduction": True,
        },
    )
    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute(
        {
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "fault_percentage": 50,
        }
    )
    # 1.0 × 10 × (100-50)/100 = 5
    assert result.estimated_mid == Decimal("5.0000")


@pytest.mark.django_db
def test_fault_reduction_not_applied_when_formula_disables_it(full_approved_stack):
    """
    `fault_reduction=False` (default fixture): il fault_percentage NON
    riduce l'importo, il valore resta intero.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute(
        {
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "fault_percentage": 50,
        }
    )
    assert result.estimated_mid == Decimal("10.0000")


# --- amount_rule: row_amount_direct (TUN Tabella 1 semantics) -------------


@pytest.mark.django_db
def test_row_amount_direct_uses_cell_value_as_final_amount(italy, italy_jurisdiction):
    """
    Con `amount_rule="row_amount_direct"`, il calculator NON moltiplica
    `row.point_value` per la percentuale di invalidità: il valore della
    cella È già l'importo finale (semantica della TUN 'tabella
    comprensiva'). Importo fittizio test-only.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Test-only TUN-style dataset (NOT real values)",
        status=DatasetStatus.APPROVED,
    )
    CalculationFormula.objects.create(
        dataset=dataset,
        code="tun_direct_test",
        name="Test-only direct formula",
        status=DatasetStatus.APPROVED,
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_direct",
            "fault_reduction": False,
        },
    )
    # Cella fittizia: età=30, invalidità=10% → "importo finale" 12345.67.
    # Il valore è volutamente NON tondo per dimostrare che NON viene
    # moltiplicato per 10 (sarebbe 123456.7) — è già il finale.
    CompensationTableRow.objects.create(
        dataset=dataset,
        row_type="tun_biological_total_amount",
        age_min=30,
        age_max=30,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("12345.6700"),
        notes="fixture only — NOT a real TUN value",
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})

    assert result.status == CalculationStatus.CALCULATED.value
    # CRITICO: il valore atteso è ESATTAMENTE 12345.67, NON 12345.67 × 10.
    assert result.estimated_min == Decimal("12345.6700")
    assert result.estimated_mid == Decimal("12345.6700")
    assert result.estimated_max == Decimal("12345.6700")


@pytest.mark.django_db
def test_row_amount_direct_applies_fault_reduction(italy, italy_jurisdiction):
    """
    `row_amount_direct` rispetta il flag `fault_reduction` come la regola
    moltiplicativa: 50% fault dimezza l'importo finale.
    """
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Test-only TUN-style with fault",
        status=DatasetStatus.APPROVED,
    )
    CalculationFormula.objects.create(
        dataset=dataset,
        code="tun_direct_fault_test",
        name="Test-only direct formula with fault",
        status=DatasetStatus.APPROVED,
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "row_amount_direct",
            "fault_reduction": True,
        },
    )
    CompensationTableRow.objects.create(
        dataset=dataset,
        row_type="tun_biological_total_amount",
        age_min=30,
        age_max=30,
        disability_min=10,
        disability_max=10,
        point_value=Decimal("100.0000"),
        notes="fixture only",
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute(
        {
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "fault_percentage": 50,
        }
    )
    # 100 × (100-50)/100 = 50
    assert result.estimated_mid == Decimal("50.0000")


# --- medical_expenses / lost_income ---------------------------------------


@pytest.mark.django_db
def test_medical_expenses_does_not_affect_amount_but_emits_warning(
    full_approved_stack,
):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute(
        {
            "victim_age": 30,
            "permanent_disability_percentage": 10,
            "medical_expenses": "5000.00",
        }
    )
    assert result.estimated_mid == Decimal("10.0000")  # immutato
    assert any("medical_expenses" in w for w in result.warnings)


# --- gating temporale dataset --------------------------------------------


@pytest.mark.django_db
def test_dataset_with_future_valid_from_is_not_used(italy, italy_jurisdiction):
    from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
    from apps.calculators.enums import CalculationStatus

    src = _approved_source(italy, italy_jurisdiction)
    dataset = CompensationDataset.objects.create(
        source=src,
        jurisdiction=italy_jurisdiction,
        country=italy,
        case_type=CaseType.ROAD_ACCIDENT_BODILY_INJURY.value,
        name="Future dataset",
        status=DatasetStatus.APPROVED,
        valid_from=date.today() + timedelta(days=365),
    )
    CalculationFormula.objects.create(
        dataset=dataset,
        code="future",
        name="Future formula",
        status=DatasetStatus.APPROVED,
        parameters={
            "engine": "italy_tun_point_value_v1",
            "requires": ["victim_age", "permanent_disability_percentage"],
            "row_match": ["victim_age", "permanent_disability_percentage"],
            "amount_rule": "point_value_times_disability_percentage",
            "fault_reduction": False,
        },
    )

    calc = ItalyRoadAccidentBodilyInjuryCalculator()
    result = calc.compute({"victim_age": 30, "permanent_disability_percentage": 10})
    # Dataset non ancora vigente → trattato come "nessun dataset approved".
    assert result.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value
    assert "compensation_dataset_approved" in result.missing_documents
