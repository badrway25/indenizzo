from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import LegalReview, LegalSource, LegalSourceAttachment, LegalSourceVersion


class LegalSourceVersionInline(admin.TabularInline):
    model = LegalSourceVersion
    extra = 0
    fields = (
        "version_label",
        "valid_from",
        "valid_to",
        "supersedes",
        "content_hash",
    )
    readonly_fields = ("content_hash",)
    autocomplete_fields = ("supersedes",)


class LegalSourceAttachmentInline(admin.TabularInline):
    model = LegalSourceAttachment
    extra = 0
    fields = (
        "file",
        "original_filename",
        "mime_type",
        "size_bytes",
        "sha256",
        "description",
    )
    readonly_fields = ("original_filename", "mime_type", "size_bytes", "sha256")


class LegalReviewInline(admin.TabularInline):
    model = LegalReview
    extra = 0
    can_delete = False
    fields = (
        "reviewer",
        "decision",
        "previous_status",
        "new_status",
        "comment",
        "created_at",
    )
    # Append-only: l'inline è la STORIA in sola lettura delle decisioni di
    # review. Le nuove review si registrano solo via la pagina dedicata
    # `LegalReviewAdmin` (che forza `reviewer=request.user`) o via il comando
    # di promozione — mai modificabili/cancellabili da qui.
    readonly_fields = (
        "reviewer",
        "decision",
        "previous_status",
        "new_status",
        "comment",
        "created_at",
    )

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(LegalSource)
class LegalSourceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "country",
        "source_type",
        "status",
        "latest_review_decision",
        "readiness_label",
        "publication_date",
        "last_checked_at",
    )
    list_filter = (
        "status",
        "reliability",
        "source_type",
        "country",
        "jurisdiction",
        "language",
    )
    search_fields = ("title", "citation", "official_url", "notes", "slug")
    autocomplete_fields = (
        "country",
        "jurisdiction",
        "language",
        "legal_reviewer",
        "supersedes",
        "replaced_by",
    )
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "publication_date"
    inlines = [LegalSourceVersionInline, LegalSourceAttachmentInline, LegalReviewInline]
    actions = ["report_review_readiness_action"]

    @admin.display(description=_("latest review"))
    def latest_review_decision(self, obj):
        review = obj.latest_review
        return review.decision if review else "—"

    @admin.display(description=_("readiness"))
    def readiness_label(self, obj):
        """Read-only, computed. Never marks anything calculation-ready itself."""
        from apps.legal_sources.review_readiness import build_readiness_rows

        rows = build_readiness_rows()
        row = next((r for r in rows if r.slug == obj.slug), None)
        if row is None:
            return "—"
        if row.calculation_ready:
            return "calc-ready"
        n = len(row.missing_steps)
        return f"needs {n} step(s)"

    @admin.action(description=_("Report review readiness (read-only, no changes)"))
    def report_review_readiness_action(self, request, queryset):
        """Surface the missing steps per selected source as admin messages.

        Strictly read-only: creates no review, promotes nothing, activates no
        calculator. Just shows the reviewer what is still missing.
        """
        from apps.legal_sources.review_readiness import build_readiness_rows

        rows = {r.slug: r for r in build_readiness_rows()}
        for source in queryset:
            row = rows.get(source.slug)
            if row is None:
                continue
            ready = "calculation-ready" if row.calculation_ready else "not calculation-ready"
            steps = "; ".join(row.missing_steps) or "no missing steps"
            self.message_user(
                request,
                f"{source.slug}: {ready}. Latest review: "
                f"{row.latest_review_decision or '—'}. Missing: {steps}.",
            )

    fieldsets = (
        (None, {"fields": ("title", "slug", "citation", "official_url")}),
        (
            _("Geography & language"),
            {"fields": ("country", "jurisdiction", "language")},
        ),
        (
            _("Classification"),
            {"fields": ("source_type", "reliability", "status", "legal_reviewer")},
        ),
        (
            _("Dates"),
            {
                "fields": (
                    "publication_date",
                    "effective_date",
                    "valid_until",
                    "last_checked_at",
                )
            },
        ),
        (
            _("Lineage"),
            {"fields": ("supersedes", "replaced_by")},
        ),
        (_("Notes"), {"fields": ("notes",)}),
        (_("Audit"), {"fields": ("created_at", "updated_at")}),
    )


@admin.register(LegalSourceVersion)
class LegalSourceVersionAdmin(admin.ModelAdmin):
    list_display = ("source", "version_label", "valid_from", "valid_to", "content_hash")
    list_filter = ("source__country", "source__status")
    search_fields = ("version_label", "source__title", "content_hash")
    autocomplete_fields = ("source", "supersedes")
    readonly_fields = ("created_at", "updated_at")


@admin.register(LegalSourceAttachment)
class LegalSourceAttachmentAdmin(admin.ModelAdmin):
    list_display = ("source", "original_filename", "mime_type", "size_bytes", "created_at")
    list_filter = ("mime_type", "source__country")
    search_fields = ("original_filename", "sha256", "source__title")
    autocomplete_fields = ("source",)
    readonly_fields = (
        "original_filename",
        "mime_type",
        "size_bytes",
        "sha256",
        "created_at",
        "updated_at",
    )


@admin.register(LegalReview)
class LegalReviewAdmin(admin.ModelAdmin):
    """Registro append-only e non falsificabile delle decisioni di review.

    Invarianti applicati al layer admin:

    - **Non cancellabile** (`has_delete_permission=False`): una decisione di
      validazione legale è un record immutabile per l'audit.
    - **Righe esistenti congelate** (`has_change_permission=False` su `obj`):
      decisione, statuti e reviewer non sono modificabili dopo la creazione.
    - **Identità non falsificabile**: in creazione il `reviewer` è SEMPRE
      forzato a `request.user`, mai scelto a mano.

    L'auditlog (django-auditlog) resta come traccia detective; questo layer
    aggiunge la prevenzione.
    """

    list_display = (
        "source",
        "reviewer",
        "decision",
        "previous_status",
        "new_status",
        "created_at",
    )
    list_filter = ("decision", "new_status", "previous_status")
    search_fields = ("source__title", "comment", "reviewer__username")
    autocomplete_fields = ("source",)
    readonly_fields = ("created_at",)

    def has_delete_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        # Accesso al modulo / changelist / pagina di add consentito; le righe
        # esistenti sono in sola lettura (congelate).
        if obj is None:
            return super().has_change_permission(request, obj)
        return False

    def get_fields(self, request, obj=None):
        if obj is None:
            # In creazione NON mostriamo `reviewer`: forzato in save_model.
            return ("source", "decision", "previous_status", "new_status", "comment")
        return (
            "source",
            "reviewer",
            "decision",
            "previous_status",
            "new_status",
            "comment",
            "created_at",
        )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            # Riga esistente: ogni campo è congelato.
            return (
                "source",
                "reviewer",
                "decision",
                "previous_status",
                "new_status",
                "comment",
                "created_at",
            )
        return ("created_at",)

    def save_model(self, request, obj, form, change):
        if not change:
            # Identità non falsificabile: il reviewer è l'utente loggato.
            obj.reviewer = request.user
        super().save_model(request, obj, form, change)
