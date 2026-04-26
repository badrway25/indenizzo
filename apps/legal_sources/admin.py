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
    fields = (
        "reviewer",
        "decision",
        "previous_status",
        "new_status",
        "comment",
        "created_at",
    )
    readonly_fields = ("created_at",)
    autocomplete_fields = ("reviewer",)


@admin.register(LegalSource)
class LegalSourceAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "country",
        "jurisdiction",
        "source_type",
        "status",
        "reliability",
        "publication_date",
        "valid_until",
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
    autocomplete_fields = ("source", "reviewer")
    readonly_fields = ("created_at",)
