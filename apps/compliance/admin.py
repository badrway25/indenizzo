"""
Admin compliance.

Regole admin:
- ConsentRecord e PrivacyAuditEvent sono append-only: niente add/change
  manuali, niente delete (preserva integrità GDPR);
- DataDeletionRequest è gestibile dallo staff (status workflow);
- ConsentTextVersion editabile solo finché non è entrata in produzione;
  in F3 lo lasciamo editabile in admin per agility, F10 lo bloccherà
  con permission check più stretto.
"""

from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import (
    ConsentPurpose,
    ConsentRecord,
    ConsentTextVersion,
    DataDeletionRequest,
    DataRetentionPolicy,
    PrivacyAuditEvent,
    StaffAccessEvent,
)


@admin.register(ConsentPurpose)
class ConsentPurposeAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "required_for_simulation",
        "required_for_contact",
        "is_active",
    )
    list_filter = ("is_active", "required_for_simulation", "required_for_contact")
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)


@admin.register(ConsentTextVersion)
class ConsentTextVersionAdmin(admin.ModelAdmin):
    list_display = (
        "purpose",
        "version",
        "language",
        "is_active",
        "effective_from",
        "effective_to",
    )
    list_filter = ("language", "is_active", "purpose")
    search_fields = ("title", "body", "version", "purpose__code")
    autocomplete_fields = ("purpose", "created_by")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "effective_from"


class _ReadOnlyAdminMixin:
    """Append-only admin: lettura/filtri sì, mutazioni no."""

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConsentRecord)
class ConsentRecordAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "accepted_at",
        "purpose",
        "accepted",
        "user",
        "session_key",
        "locale",
        "ip_address",
    )
    list_filter = ("accepted", "purpose", "locale")
    search_fields = (
        "session_key",
        "source_path",
        "user__username",
        "user__email",
        "ip_address",
    )
    autocomplete_fields = ("purpose", "text_version", "user")
    readonly_fields = (
        "user",
        "session_key",
        "purpose",
        "text_version",
        "accepted",
        "accepted_at",
        "ip_address",
        "user_agent",
        "locale",
        "source_path",
        "metadata",
        "created_at",
    )
    date_hierarchy = "accepted_at"


@admin.register(DataRetentionPolicy)
class DataRetentionPolicyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "applies_to", "retention_days", "is_active")
    list_filter = ("applies_to", "is_active")
    search_fields = ("code", "name", "description")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("applies_to", "code")


@admin.register(DataDeletionRequest)
class DataDeletionRequestAdmin(admin.ModelAdmin):
    list_display = (
        "requested_at",
        "email",
        "user",
        "status",
        "handled_by",
        "completed_at",
    )
    list_filter = ("status",)
    search_fields = ("email", "user__username", "user__email", "internal_notes")
    autocomplete_fields = ("user", "handled_by")
    readonly_fields = ("requested_at",)
    date_hierarchy = "requested_at"
    fieldsets = (
        (None, {"fields": ("email", "user", "reason")}),
        (_("Workflow"), {"fields": ("status", "handled_by", "completed_at")}),
        (_("Internal"), {"fields": ("internal_notes", "requested_at")}),
    )


@admin.register(StaffAccessEvent)
class StaffAccessEventAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    """Read-only admin per audit accessi staff/admin (pass 8)."""

    list_display = (
        "created_at",
        "event_type",
        "user",
        "username_hash",
        "ip_address_masked",
        "path",
    )
    list_filter = ("event_type",)
    # Search SOLO su campi non-PII: l'email è esclusa di proposito.
    # Per cercare un evento di un utente specifico, usare l'ID utente
    # o l'hash dell'username (calcolabile via shell).
    search_fields = ("username_hash", "user__id", "ip_address_masked", "path")
    autocomplete_fields = ("user",)
    readonly_fields = (
        "event_type",
        "user",
        "username_hash",
        "ip_address_masked",
        "user_agent_hash",
        "path",
        "metadata",
        "created_at",
    )
    date_hierarchy = "created_at"


@admin.register(PrivacyAuditEvent)
class PrivacyAuditEventAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "created_at",
        "event_type",
        "actor",
        "target_model",
        "target_object_id",
        "ip_address",
    )
    list_filter = ("event_type", "target_model")
    search_fields = (
        "actor__username",
        "target_model",
        "target_object_id",
        "path",
        "ip_address",
    )
    autocomplete_fields = ("actor",)
    readonly_fields = (
        "actor",
        "event_type",
        "target_model",
        "target_object_id",
        "ip_address",
        "user_agent",
        "path",
        "metadata",
        "created_at",
    )
    date_hierarchy = "created_at"
