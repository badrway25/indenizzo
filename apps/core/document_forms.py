"""P30 / P31 — secure, stateless document-intake form.

Validates one OR several uploaded files (MIME allowlist + size + extension +
a configurable count cap), captures the analysis consent and an optional manual
country/category, and a honeypot. Files are NEVER persisted — the view analyses
them in memory, builds a dossier, and discards them.
"""

from __future__ import annotations

import os

from django import forms
from django.conf import settings
from django.utils.translation import gettext_lazy as _

_ALLOWED_EXT = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}


def _validate_upload(f):
    """Per-file guard: size, MIME allowlist and extension. Raises on failure."""
    max_bytes = settings.DOCUMENT_INTAKE_MAX_UPLOAD_MB * 1024 * 1024
    if f.size > max_bytes:
        raise forms.ValidationError(
            _("The file is too large (max %(mb)d MB).")
            % {"mb": settings.DOCUMENT_INTAKE_MAX_UPLOAD_MB})
    content_type = (getattr(f, "content_type", "") or "").lower()
    if content_type not in settings.DOCUMENT_INTAKE_ALLOWED_MIME:
        raise forms.ValidationError(
            _("This file type is not supported. Upload a PDF or an image."))
    ext = os.path.splitext(f.name or "")[1].lower()
    if ext not in _ALLOWED_EXT:
        raise forms.ValidationError(
            _("This file type is not supported. Upload a PDF or an image."))
    return f


class MultipleFileInput(forms.ClearableFileInput):
    """Widget that accepts several files (Django documented pattern)."""
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """FileField that cleans a list of uploads, one validation per file."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if data in (None, ""):
            data = []
        if isinstance(data, (list, tuple)):
            cleaned = [single(d, initial) for d in data if d not in (None, "")]
        else:
            cleaned = [single(data, initial)]
        if not cleaned and self.required:
            raise forms.ValidationError(self.error_messages["required"], code="required")
        return cleaned

_COUNTRY_CHOICES = (
    ("", _("I'm not sure")),
    ("IT", _("Italy")), ("FR", _("France")), ("BE", _("Belgium")),
    ("MA", _("Morocco")), ("TN", _("Tunisia")),
)
_CATEGORY_CHOICES = (
    ("", _("Detect automatically")),
    ("road_accident", _("Road accident")),
    ("medical", _("Medical liability")),
    ("work_injury", _("Workplace injury")),
    ("insurance_offer", _("Insurance offer")),
    ("loss", _("Loss of a relative")),
    ("inheritance", _("Inheritance")),
    ("cross_border", _("Cross-border")),
)
_LANGUAGE_CHOICES = (
    ("", _("Detect automatically")),
    ("it", _("Italian")), ("fr", _("French")), ("ar", _("Arabic")),
    ("en", _("English")),
)


class DocumentUploadForm(forms.Form):
    document = MultipleFileField(
        label=_("Your documents"),
        help_text=_("PDF, JPEG, PNG or WebP."),
    )
    country = forms.ChoiceField(
        label=_("Country"), required=False, choices=_COUNTRY_CHOICES)
    category = forms.ChoiceField(
        label=_("Category"), required=False, choices=_CATEGORY_CHOICES)
    language = forms.ChoiceField(
        label=_("Document language"), required=False, choices=_LANGUAGE_CHOICES)
    analysis_consent = forms.BooleanField(
        label=_("I agree to the documental analysis to organise my dossier."),
        required=True)
    # Honeypot — real users leave it empty.
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    @property
    def is_likely_bot(self) -> bool:
        return bool(self.data.get("website"))

    def clean_document(self):
        files = self.cleaned_data["document"] or []
        max_files = settings.DOCUMENT_INTAKE_MAX_FILES
        if len(files) > max_files:
            raise forms.ValidationError(
                _("You can upload up to %(n)d documents at a time.")
                % {"n": max_files})
        return [_validate_upload(f) for f in files]

    @staticmethod
    def safe_filename(name: str) -> str:
        """A display-only, sanitised file name (the file itself is never stored)."""
        base = os.path.basename(name or "")
        keep = "".join(c for c in base if c.isalnum() or c in " ._-()")
        return (keep[:80] or "document").strip()
