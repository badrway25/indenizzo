"""Admin per `apps.reports`. Read-only: i report sono artefatti immutabili."""

from __future__ import annotations

from django.contrib import admin

from .models import SimulationReport


@admin.register(SimulationReport)
class SimulationReportAdmin(admin.ModelAdmin):
    list_display = (
        "generated_at",
        "simulation",
        "language",
        "status",
        "file_size_bytes",
        "generated_by",
    )
    list_filter = ("status", "language", "generated_at")
    search_fields = (
        "public_id",
        "simulation__public_id",
        "file_hash",
    )
    autocomplete_fields = ("simulation", "generated_by")
    readonly_fields = (
        "public_id",
        "simulation",
        "language",
        "file",
        "file_hash",
        "file_size_bytes",
        "generated_at",
        "generated_by",
        "status",
        "error_message",
        "metadata",
    )

    def has_add_permission(self, request):  # pragma: no cover
        # I report nascono dal service, non a mano.
        return False

    def has_change_permission(self, request, obj=None):  # pragma: no cover
        # Append-only: il record non si modifica.
        return False
