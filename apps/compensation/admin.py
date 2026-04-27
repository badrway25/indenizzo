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

from .models import CalculationFormula, CompensationDataset, CompensationTableRow


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
        "valid_from",
        "valid_to",
        "source",
    )
    list_filter = ("status", "case_type", "country", "jurisdiction")
    search_fields = ("name", "version_label", "notes", "source__title")
    autocomplete_fields = ("source", "jurisdiction", "country")
    readonly_fields = ("created_at", "updated_at")
    inlines = [CompensationTableRowInline, CalculationFormulaInline]
    fieldsets = (
        (None, {"fields": ("name", "version_label", "case_type", "status")}),
        (_("Source & geography"), {"fields": ("source", "jurisdiction", "country")}),
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
