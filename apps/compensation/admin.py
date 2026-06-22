"""
Admin per `apps.compensation`.

Pannelli destinati ai legal reviewer dello Studio. Espongono il workflow
di stato (`draft → needs_review → approved`) e proteggono il vincolo
"approved richiede source approved": è già applicato in `clean()` dei
modelli, qui aggiungiamo solo la UX.
"""

from __future__ import annotations

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    ExtractionLog,
)


class CompensationTableRowInline(admin.TabularInline):
    model = CompensationTableRow
    extra = 0
    fields = (
        "row_type",
        "age_min",
        "age_max",
        "disability_min",
        "disability_max",
        "point_value",
        "daily_amount",
        "coefficient",
        "notes",
    )


class CalculationFormulaInline(admin.TabularInline):
    model = CalculationFormula
    extra = 0
    fields = ("code", "name", "expression_text", "source_reference", "status", "notes")


@admin.register(CompensationDataset)
class CompensationDatasetAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "country",
        "jurisdiction",
        "case_type",
        "status",
        "rows_count",
        "valid_from",
        "valid_to",
        "source",
    )
    list_filter = ("status", "case_type", "country", "jurisdiction", "source__status")
    search_fields = ("name", "version_label", "notes", "source__title")
    autocomplete_fields = ("source", "source_version", "jurisdiction", "country")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CompensationTableRowInline, CalculationFormulaInline]

    @admin.display(description=_("rows"))
    def rows_count(self, obj: CompensationDataset) -> int:
        return obj.rows.count()

    fieldsets = (
        (None, {"fields": ("name", "version_label", "case_type", "status")}),
        # `source_version` è la provenienza alla versione fonte specifica:
        # obbligatoria (clean()) per i dataset APPROVED.
        (
            _("Source & geography"),
            {"fields": ("source", "source_version", "jurisdiction", "country")},
        ),
        (_("Validity"), {"fields": ("valid_from", "valid_to")}),
        (_("Notes"), {"fields": ("notes",)}),
        (_("Audit"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(CompensationTableRow)
class CompensationTableRowAdmin(admin.ModelAdmin):
    list_display = (
        "dataset",
        "row_type",
        "age_min",
        "age_max",
        "disability_min",
        "disability_max",
        "point_value",
        "daily_amount",
        "coefficient",
    )
    list_filter = ("dataset__status", "dataset__case_type", "row_type")
    search_fields = ("dataset__name", "row_type", "notes")
    autocomplete_fields = ("dataset",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(CalculationFormula)
class CalculationFormulaAdmin(admin.ModelAdmin):
    list_display = ("code", "dataset", "name", "status", "source_reference")
    list_filter = ("status", "dataset__case_type")
    search_fields = ("code", "name", "expression_text", "source_reference")
    autocomplete_fields = ("dataset",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(ExtractionLog)
class ExtractionLogAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "source",
        "dataset",
        "method",
        "result",
        "rows_imported",
        "rows_skipped",
    )
    list_filter = ("result", "method", "source__country")
    search_fields = ("source__title", "file_path", "file_sha256", "error_message")
    autocomplete_fields = ("source", "dataset")
    readonly_fields = (
        "source",
        "dataset",
        "method",
        "file_path",
        "file_sha256",
        "file_size_bytes",
        "rows_imported",
        "rows_skipped",
        "result",
        "error_message",
        "metadata",
        "created_at",
    )

    def has_add_permission(self, request):  # pragma: no cover
        # Append-only: i log devono nascere dal command, non a mano.
        return False

    def has_delete_permission(self, request, obj=None):  # pragma: no cover
        return False
