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
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext_lazy as _

from .models import Lead, LeadEvent, LeadStatus, LeadWebhookDelivery


# F-product-8-studio-lead-activity-timeline: short CSS color per
# severity. Pure presentation — no JS, no behaviour.
_SEVERITY_COLORS: dict[str, str] = {
    "info": "#475569",
    "success": "#15803d",
    "warning": "#a16207",
    "error": "#b91c1c",
}


class HasLinkedSimulationFilter(admin.SimpleListFilter):
    """F-product-7-crm-staff-lead-workflow: split list by funnel origin.

    A Lead with `simulation_id is not None` came through the wizard
    result-page CTA. Filtering on this lets the Studio focus on
    qualified-funnel leads vs cold contact-form submissions."""

    title = _("linked simulation")
    parameter_name = "has_simulation"

    def lookups(self, request, model_admin):
        return (
            ("1", _("Linked (from wizard funnel)")),
            ("0", _("Not linked (cold contact)")),
        )

    def queryset(self, request, queryset):
        if self.value() == "1":
            return queryset.filter(simulation__isnull=False)
        if self.value() == "0":
            return queryset.filter(simulation__isnull=True)
        return queryset


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
        "country",
        "case_type",
        "status",
        "mandate_status",
        "mandate_signed",
        "double_consent_display",
        "linked_simulation_display",
        "source_label_display",
        "webhook_status_display",
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
        "privacy_consent_given",
        "special_categories_consent_given",
        HasLinkedSimulationFilter,
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
        # F-product-7-crm-staff-lead-workflow: consent denormalised
        # fields are an audit snapshot of `compliance.ConsentRecord`;
        # staff must not flip them by hand.
        "privacy_consent_given",
        "privacy_consent_at",
        "privacy_consent_version",
        "special_categories_consent_given",
        "special_categories_consent_at",
        "special_categories_consent_version",
        # F-product-7-crm-staff-lead-workflow: mandate timestamp /
        # version / source are written by `apps.compliance.mandate`
        # services. `mandate_status` + `mandate_signed` stay editable
        # so the Studio can record acceptance through the admin row.
        "mandate_signed_at",
        "mandate_version",
        "mandate_source",
        "webhook_outbox_summary",
        "next_staff_action_display",
        "activity_timeline",
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
        (
            _("Activity timeline"),
            {
                "fields": ("next_staff_action_display", "activity_timeline"),
                "description": _(
                    "Read-only chronological view aggregated from the Lead, "
                    "its linked simulation, consent timestamps, lifecycle "
                    "events, webhook outbox and mandate state. The 'next "
                    "staff action' line is an operational hint derived from "
                    "workflow flags only - it is not a legal opinion on the "
                    "case."
                ),
            },
        ),
        (
            _("Webhook outbox (CRM)"),
            {
                "classes": ("collapse",),
                "fields": ("webhook_outbox_summary",),
                "description": _(
                    "Read-only summary of the related LeadWebhookDelivery rows. "
                    "Manage / inspect individual deliveries via the dedicated "
                    "Lead webhook deliveries admin page."
                ),
            },
        ),
        (_("Audit"), {"fields": ("created_at", "updated_at")}),
    )

    def get_queryset(self, request):
        # F-product-7-crm-staff-lead-workflow: prefetch the outbox rows
        # so the per-row derived `webhook_status_display` does not hit
        # the DB once per list line.
        # F-product-8-studio-lead-activity-timeline: also prefetch the
        # lifecycle events and select_related the simulation so the
        # activity_timeline detail-page render stays under the query
        # budget when admin opens a row.
        qs = super().get_queryset(request)
        return qs.select_related("simulation").prefetch_related(
            "webhook_deliveries", "events"
        )

    def has_add_permission(self, request):
        # I lead nascono dal form pubblico, mai dall'admin.
        return False

    @admin.display(description=_("name"))
    def full_name_display(self, obj: Lead) -> str:
        return obj.full_name

    @admin.display(description=_("2x consent"), boolean=True)
    def double_consent_display(self, obj: Lead) -> bool:
        return obj.has_valid_double_consent

    @admin.display(description=_("simulation"), boolean=True)
    def linked_simulation_display(self, obj: Lead) -> bool:
        return obj.has_linked_simulation

    @admin.display(description=_("source"))
    def source_label_display(self, obj: Lead) -> str:
        """Short derived label: 'wizard' (simulation linked) vs
        'case-type' (case-type landing referrer) vs 'contact' (default).
        Computed from existing fields — no DB migration."""
        if obj.simulation_id is not None:
            return "wizard"
        path = (obj.source_path or "").lower()
        if "/case-types/" in path or "case_type=" in path:
            return "case-type"
        return "contact"

    @admin.display(description=_("webhook"))
    def webhook_status_display(self, obj: Lead) -> str:
        return obj.webhook_delivery_status_summary

    @admin.display(description=_("Next staff action"))
    def next_staff_action_display(self, obj: Lead) -> str:
        """Conservative operational hint. See `apps.crm.timeline.compute_next_staff_action`."""
        return obj.next_staff_action

    @admin.display(description=_("Activity timeline"))
    def activity_timeline(self, obj: Lead):
        """Render the chronological timeline as a safe HTML list.

        Implementation notes:

        - Uses `format_html` + `format_html_join` so every interpolated
          value passes through Django's auto-escape. No `mark_safe`
          on user-supplied text.
        - Severity colours come from a fixed enum-keyed dict — no
          user input reaches the style attribute.
        - No JavaScript, no buttons, no retry links. The page is a
          read-only audit view.
        """
        from .timeline import build_lead_timeline

        items = build_lead_timeline(obj)
        if not items:
            return format_html("<em>{}</em>", _("No activity yet."))

        rows = format_html_join(
            "",
            (
                "<li style=\"margin:0 0 6px 0; padding-left:8px; "
                "border-left:3px solid {};\">"
                "<div style=\"font-size:11px; color:#64748b;\">{} &middot; {}</div>"
                "<div style=\"font-weight:600;\">{}</div>"
                "<div style=\"font-size:12px; color:#334155;\">{}</div>"
                "<div style=\"font-size:11px; color:#64748b; font-family:monospace;\">{}</div>"
                "</li>"
            ),
            (
                (
                    _SEVERITY_COLORS.get(it.severity, "#64748b"),
                    it.timestamp.strftime("%Y-%m-%d %H:%M"),
                    it.category,
                    it.label,
                    it.description,
                    it.source,
                )
                for it in items
            ),
        )
        return format_html(
            "<ul style=\"list-style:none; padding:0; margin:0;\">{}</ul>", rows
        )

    @admin.display(description=_("Webhook deliveries"))
    def webhook_outbox_summary(self, obj: Lead) -> str:
        """Multi-line summary of the related outbox rows, rendered in the
        detail page. Each row reports the event type, status, attempts,
        last status code and the audit-friendly target_url_domain."""
        rows = list(
            obj.webhook_deliveries.order_by("-created_at", "-pk")[:5]
        )
        if not rows:
            return "-"
        return "\n".join(
            (
                f"[{r.created_at:%Y-%m-%d %H:%M}] "
                f"{r.event_type} status={r.status} "
                f"attempts={r.attempts}/{r.max_attempts} "
                f"http={r.last_status_code or '-'} "
                f"target={r.target_url_domain or '-'}"
            )
            for r in rows
        )

    @admin.action(description=_("Mark selected leads as Contacted"))
    def mark_as_contacted(self, request, queryset):
        now = timezone.now()
        count = 0
        for lead in queryset:
            lead.status = LeadStatus.CONTACTED
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


@admin.register(LeadWebhookDelivery)
class LeadWebhookDeliveryAdmin(_ReadOnlyAdminMixin, admin.ModelAdmin):
    """F-product-7-crm-staff-lead-workflow: read-only audit window into
    the CRM webhook outbox. The dispatcher (management command
    `dispatch_crm_webhooks`) owns this table; the admin exists so the
    Studio can SEE pending / failed / dead deliveries without opening
    a shell. CRUD is fully denied — re-firing happens via the
    env-gated command, not via admin clicks."""

    list_display = (
        "created_at",
        "lead",
        "event_type",
        "status",
        "attempts",
        "max_attempts",
        "next_attempt_at",
        "delivered_at",
        "last_status_code",
        "target_url_domain",
    )
    list_filter = ("status", "event_type")
    search_fields = ("lead__public_id", "idempotency_key")
    autocomplete_fields = ("lead",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "lead",
        "event_type",
        "payload_version",
        "idempotency_key",
        "target_url_domain",
        "status",
        "attempts",
        "max_attempts",
        "next_attempt_at",
        "last_attempt_at",
        "delivered_at",
        "last_status_code",
        "last_error",
        "response_excerpt",
        "created_at",
        "updated_at",
    )
