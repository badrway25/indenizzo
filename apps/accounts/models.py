from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        CLIENT = "client", _("Client")
        LAWYER = "lawyer", _("Lawyer")
        STAFF = "staff", _("Staff")
        ADMIN = "admin", _("Admin")

    class Language(models.TextChoices):
        IT = "it", _("Italiano")
        FR = "fr", _("Français")
        EN = "en", _("English")
        AR = "ar", _("العربية")

    role = models.CharField(
        _("role"),
        max_length=16,
        choices=Role.choices,
        default=Role.CLIENT,
    )
    preferred_language = models.CharField(
        _("preferred language"),
        max_length=4,
        choices=Language.choices,
        default=Language.IT,
    )
    phone_number = models.CharField(
        _("phone number"),
        max_length=32,
        blank=True,
    )
    company_or_firm_name = models.CharField(
        _("company or firm name"),
        max_length=255,
        blank=True,
    )
    created_at = models.DateTimeField(_("created at"), auto_now_add=True)
    updated_at = models.DateTimeField(_("updated at"), auto_now=True)

    class Meta(AbstractUser.Meta):
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.get_username()
