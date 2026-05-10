"""
Admin CRM (F6).

Pipeline gestita dallo staff Studio:
- `Lead` editabile per i campi di workflow (status, priority, assigned_to,
  internal_notes, contacted_at, converted_at);
- request metadata, public_id, consent_record, simulation, timestamp readonly;
- 3 azioni bulk: contacted / qualified / archive;
- `LeadEvent` completamente readonly (append-only).
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Lead, LeadEvent


class _ReadOnlyAdminMixin:
    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class LeadEventInline(admin.TabularInline):
    model = LeadEvent
    extra = 0
    fields = ("event_type", "message", "metadata", "created_at")
    readonly_fields = ("event_type", "message", "metadata", "created_at")
    can_delete = False
    show_change_link = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "full_name_display",
        "email",
        "phone_number",
        "country",
        "case_type",
        "status",
        "mandate_status",
        "mandate_signed",
        "priority",
        "assigned_to",
    )
    list_filter = (
        "status",
        "mandate_status",
        "mandate_signed",
        "priority",
        "country",
        "case_type",
        "preferred_language",
        "assigned_to",
    )
    search_fields = (
        "public_id",
        "first_name",
        "last_name",
        "email",
        "phone_number",
    )
    autocomplete_fields = ("user", "assigned_to", "country", "consent_record", "simulation")
    date_hierarchy = "created_at"
    inlines = [LeadEventInline]
    actions = ("mark_as_contacted", "mark_as_qualified", "archive_selected")

    readonly_fields = (
        "public_id",
        "user",
        "session_key",
        "consent_record",
        "simulation",
        "ip_address",
        "user_agent",
        "source_path",
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        (None, {"fields": ("public_id", "status", "priority", "assigned_to")}),
        (
            _("Contact"),
            {
                "fields": (
                    "first_name",
                    "last_name",
                    "email",
                    "phone_number",
                    "preferred_language",
                )
            },
        ),
        (
            _("Case context"),
            {"fields": ("country", "case_type", "message", "simulation")},
        ),
        (
            _("Workflow"),
            {"fields": ("contacted_at", "converted_at", "internal_notes")},
        ),
        (
            _("Mandate (professional engagement)"),
            {
                "fields": (
                    "mandate_status",
                    "mandate_signed",
                    "mandate_signed_at",
                    "mandate_version",
                    "mandate_source",
                ),
                "description": _(
                    "Mandate state. A lead becomes an active case only after "
                    "the Studio signs a separate written agreement (mandate). "
                    "Use the dedicated service apps.compliance.mandate."
                    "mark_mandate_signed to record acceptance."
                ),
            },
        ),
        (
            _("Privacy"),
            {"fields": ("consent_record",)},
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
                    "utm_source",
                    "utm_medium",
                    "utm_campaign",
                )
            },
        ),
        (_("Audit"), {"fields": ("created_at", "updated_at")}),
    )

    def has_add_permission(self, request):
        # I lead nascono dal form pubblico, mai dall'admin.
        return False

    @admin.display(description=_("name"))
    def full_name_display(self, obj: Lead) -> str:
        return obj.full_name

    @admin.action(description=_("Mark selected leads as Contacted"))
    def mark_as_contacted(self, request, queryset):
        now = timezone.now()
        count = 0
        for lead in queryset:
            lead.status = Lead._meta.get_field("status").choices[1][0]  # 'contacted'
            lead.contacted_at = lead.contacted_at or now
            lead.save(update_fields=["status", "contacted_at", "updated_at"])
            LeadEvent.objects.create(
                lead=lead,
                event_type=LeadEvent.EventType.CONTACTED,
                message="Marked as contacted from admin.",
            )
            count += 1
        self.message_user(request, _("%(n)d lead(s) marked as contacted.") % {"n": count})

    @admin.action(description=_("Mark selected leads as Qualified"))
    def mark_as_qualified(self, request, queryset):
        count = 0
        for lead in queryset:
            lead.status = "qualified"
            lead.save(update_fields=["status", "updated_at"])
            LeadEvent.objects.create(
                lead=lead,
                event_type=LeadEvent.EventType.QUALIFIED,
                message="Marked as qualified from admin.",
            )
            count += 1
        self.message_user(request, _("%(n)d lead(s) marked as qualified.") % {"n": count})

    @admin.action(description=_("Archive selected leads"))
    def archive_selected(self, request, queryset):
        count = 0
        for lead in queryset:
            lead.status = "archived"
            lead.save(update_fields=["status", "updated_at"])
            LeadEvent.objects.create(
                lead=lead,
                event_type=LeadEvent.EventType.ARCHIVED,
                message="Archived from admin.",
            )
            count += 1
        self.message_user(request, _("%(n)d lead(s) archived.") % {"n": count})


@admin.register(LeadEvent)
class LeadEventAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("created_at", "lead", "event_type", "message")
    list_filter = ("event_type",)
    search_fields = ("lead__public_id", "message")
    autocomplete_fields = ("lead",)
    readonly_fields = ("lead", "event_type", "message", "metadata", "created_at")
    date_hierarchy = "created_at"
