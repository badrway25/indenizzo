from django.contrib import admin

from .models import Country, Currency, Jurisdiction, Language


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("code", "code_alpha3", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "code_alpha3", "name")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "symbol", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("code", "name")
    ordering = ("code",)


@admin.register(Jurisdiction)
class JurisdictionAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "country",
        "legal_system",
        "default_currency",
        "default_language",
        "is_active",
    )
    list_filter = ("legal_system", "is_active", "country")
    search_fields = ("code", "name", "country__code", "country__name")
    autocomplete_fields = ("country", "default_currency", "default_language")
    readonly_fields = ("created_at", "updated_at")
    ordering = ("code",)
