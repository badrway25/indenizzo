from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            _("Studio profile"),
            {
                "fields": (
                    "role",
                    "preferred_language",
                    "phone_number",
                    "company_or_firm_name",
                )
            },
        ),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        (
            _("Studio profile"),
            {
                "fields": (
                    "role",
                    "preferred_language",
                    "phone_number",
                    "company_or_firm_name",
                )
            },
        ),
    )
    list_display = (
        "username",
        "email",
        "role",
        "preferred_language",
        "is_staff",
        "created_at",
    )
    list_filter = DjangoUserAdmin.list_filter + ("role", "preferred_language")
    readonly_fields = ("created_at", "updated_at", "last_login", "date_joined")
