"""Seed the APPROVED art. 139 micropermanenti dataset (P8).

REGOLA: non inventare dati. I valori qui sono i dati UFFICIALI approvati dal
titolare (vedi docs/audits/CHATGPT_SOURCE_APPROVALS_2026-06-25.md), provenienti
da art. 139 CAP (comma 6 coefficienti) + D.M. MIMIT 18/07/2025 (G.U. n.176 del
31/07/2025, decorrenza aprile 2025). L'engine legge questi valori dalle righe DB
(mai hardcoded nel motore). Il command è idempotente.

    python manage.py import_italy_micro_art139_2025
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.calculators.enums import CaseType
from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
)
from apps.jurisdictions.models import Country, Currency, Jurisdiction, Language
from apps.legal_sources.enums import SourceStatus, SourceType
from apps.legal_sources.models import LegalSource, LegalSourceVersion

SOURCE_SLUG = "it-art139-cap-micropermanenti-2025"
DATASET_VERSION = "ART139-MIMIT-2025"
# Official approved data (art. 139 co.6 coefficients + D.M. MIMIT 18/07/2025).
COEFFICIENTS = {1: "1.0", 2: "1.1", 3: "1.2", 4: "1.3", 5: "1.5", 6: "1.7", 7: "1.9", 8: "2.1", 9: "2.3"}
FIRST_POINT_VALUE = Decimal("963.40")
ITT_DAILY_ABSOLUTE = Decimal("56.18")
# A stable content hash documenting the approved provenance (not a file hash).
CONTENT_HASH = "approved:art139-mimit-2025-gu176-20250731"


class Command(BaseCommand):
    help = "Crea (idempotente) il dataset APPROVED micropermanenti art. 139 (D.M. MIMIT 2025)."

    @transaction.atomic
    def handle(self, *args, **options):
        country, _ = Country.objects.get_or_create(
            code="IT", defaults={"code_alpha3": "ITA", "name": "Italia"})
        eur, _ = Currency.objects.get_or_create(code="EUR", defaults={"name": "Euro", "symbol": "€"})
        lang, _ = Language.objects.get_or_create(code="it", defaults={"name": "Italiano"})
        juris, _ = Jurisdiction.objects.get_or_create(
            code="IT-NATIONAL",
            defaults={
                "country": country, "name": "Italia (livello nazionale)",
                "legal_system": Jurisdiction.LegalSystem.CIVIL_LAW,
                "default_currency": eur, "default_language": lang,
            },
        )
        src, created = LegalSource.objects.get_or_create(
            slug=SOURCE_SLUG,
            defaults={
                "title": "Art. 139 CAP — micropermanenti (D.M. MIMIT 18/07/2025, G.U. n.176)",
                "country": country, "jurisdiction": juris, "language": lang,
                "source_type": SourceType.MINISTRY_DECREE, "status": SourceStatus.APPROVED,
                "publication_date": date(2025, 7, 31), "effective_date": date(2025, 4, 1),
            },
        )
        version, _ = LegalSourceVersion.objects.get_or_create(
            source=src, version_label="DM-MIMIT-2025",
            defaults={"content_hash": CONTENT_HASH})

        dataset, ds_created = CompensationDataset.objects.get_or_create(
            source=src, version_label=DATASET_VERSION,
            defaults={
                "source_version": version, "jurisdiction": juris, "country": country,
                "case_type": CaseType.ROAD_ACCIDENT_MICROLESIONS.value,
                "name": "Microlesioni art. 139 (D.M. MIMIT 2025)",
                "status": DatasetStatus.APPROVED, "valid_from": date(2025, 4, 1),
                "notes": "Dati ufficiali approvati (art. 139 co.6 + D.M. MIMIT 18/07/2025).",
            },
        )
        if ds_created or dataset.rows.count() == 0:
            dataset.rows.all().delete()
            for pct, coeff in COEFFICIENTS.items():
                CompensationTableRow.objects.create(
                    dataset=dataset, row_type="disability_coefficient",
                    disability_min=pct, disability_max=pct, coefficient=Decimal(coeff),
                    notes="art. 139 co.6 coefficiente progressione")
            CompensationTableRow.objects.create(
                dataset=dataset, row_type="first_point_value", point_value=FIRST_POINT_VALUE,
                notes="valore primo punto 2025 — D.M. MIMIT 18/07/2025")
            CompensationTableRow.objects.create(
                dataset=dataset, row_type="itt_daily_absolute", daily_amount=ITT_DAILY_ABSOLUTE,
                notes="ITT inabilità assoluta €/giorno 2025 — D.M. MIMIT 18/07/2025")

        CalculationFormula.objects.get_or_create(
            dataset=dataset, code="italy_art139_micro_2025",
            defaults={
                "name": "Microlesioni art. 139 CAP — D.M. MIMIT 2025",
                "expression_text": (
                    "permanente = primo_punto × coeff(P) × P × (1 − max(0, età−10)×0,005); "
                    "temporaneo = giorni_ITT × itt_daily (parziali 50%)."),
                "parameters": {
                    "engine": "italy_art139_micro_v1", "amount_rule": "italy_art139_micro_v1",
                    "requires": ["victim_age", "permanent_disability_percentage"],
                    "provenance": {
                        "article": "art. 139 D.Lgs. 209/2005 (co.1, co.6)",
                        "decree": "D.M. MIMIT 18/07/2025", "gazzetta": "G.U. n.176 del 31/07/2025",
                        "valid_from": "2025-04", "approval": "CHATGPT_SOURCE_APPROVALS_2026-06-25",
                    },
                },
                "source_reference": "art. 139 CAP + D.M. MIMIT 18/07/2025",
                "status": DatasetStatus.APPROVED,
            },
        )
        self.stdout.write(self.style.SUCCESS(
            f"art.139 micro dataset OK (id={dataset.pk}, status={dataset.status}, "
            f"rows={dataset.rows.count()})."))
