"""
Admin `apps.cases`.

Regole:
- `Simulation` è prevalentemente readonly (quasi tutti i campi sono
  output del motore o metadati tecnici): lo staff può solo navigare,
  filtrare, esportare, e lanciare l'azione "anonymize selected".
- `SimulationEvent` è completamente readonly (append-only).
- L'azione admin `anonymize_selected` rimuove i dati personali e crea
  `SimulationEvent` + `PrivacyAuditEvent` (via service layer).
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Simulation, SimulationEvent
from .services import anonymize_simulation


class _ReadOnlyAdminMixin:
    """Lettura/filtri sì, mutazioni no."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SimulationEventInline(admin.TabularInline):
    model = SimulationEvent
    extra = 0
    fields = ("event_type", "message", "metadata", "created_at")
    readonly_fields = ("event_type", "message", "metadata", "created_at")
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "case_type",
        "jurisdiction",
        "status",
        "confidence",
        "currency",
        "estimated_mid",
        "anonymized",
        "created_at",
    )
    list_filter = (
        "status",
        "confidence",
        "case_type",
        "locale",
        "anonymized",
        "jurisdiction",
        "country",
    )
    search_fields = (
        "public_id",
        "session_key",
        "user__username",
        "user__email",
        "ip_address",
        "source_path",
    )
    autocomplete_fields = ("user", "jurisdiction", "country", "consent_record")
    date_hierarchy = "created_at"
    inlines = [SimulationEventInline]
    actions = ("anonymize_selected",)

    readonly_fields = (
        "public_id",
        "user",
        "session_key",
        "jurisdiction",
        "country",
        "case_type",
        "locale",
        "input_data",
        "output_data",
        "sources_snapshot",
        "calculation_provenance",
        "status",
        "confidence",
        "currency",
        "estimated_min",
        "estimated_mid",
        "estimated_max",
        "consent_record",
        "ip_address",
        "user_agent",
        "source_path",
        "anonymized",
        "anonymized_at",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (None, {"fields": ("public_id", "case_type", "locale")}),
        (
            _("Geography"),
            {"fields": ("jurisdiction", "country", "currency")},
        ),
        (
            _("Output"),
            {
                "fields": (
                    "status",
                    "confidence",
                    "estimated_min",
                    "estimated_mid",
                    "estimated_max",
                    "output_data",
                    "sources_snapshot",
                    "calculation_provenance",
                )
            },
        ),
        (
            _("Input & consent"),
            {"fields": ("input_data", "consent_record")},
        ),
        (
            _("Request metadata"),
            {
                "fields": (
                    "user",
                    "session_key",
                    "ip_address",
                    "user_agent",
                    "source_path",
                )
            },
        ),
        (
            _("Anonymization"),
            {"fields": ("anonymized", "anonymized_at")},
        ),
        (_("Audit"), {"fields": ("created_at", "updated_at")}),
    )

    # Sicurezza: niente add/delete; change consentito solo per l'azione admin
    # custom (anonymize) — il form di edit è di fatto inutile perché tutti i
    # campi sono readonly.
    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description=_("Anonymize selected simulations (GDPR)"))
    def anonymize_selected(self, request, queryset):
        count = 0
        for simulation in queryset:
            if simulation.anonymized:
                continue
            anonymize_simulation(simulation, request=request)
            count += 1
        self.message_user(
            request,
            _("%(count)d simulation(s) anonymized.") % {"count": count},
        )


@admin.register(SimulationEvent)
class SimulationEventAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("created_at", "simulation", "event_type", "message")
    list_filter = ("event_type",)
    search_fields = ("simulation__public_id", "message")
    autocomplete_fields = ("simulation",)
    readonly_fields = (
        "simulation",
        "event_type",
        "message",
        "metadata",
        "created_at",
    )
    date_hierarchy = "created_at"
