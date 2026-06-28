"""
Form pubblico `/contact/`.

Validazione lato server:
- email obbligatoria;
- messaggio minimo 20 caratteri (evita submit vuoti, non blocca lingua);
- consenso privacy obbligatorio (checkbox);
- honeypot `website`: se compilato, il submit è marcato come bot e
  scartato a livello di view (NON di form, per non dare segnale ai bot
  che il campo è una trappola — il form passa, la view droppa).

Niente reCAPTCHA reale in F6 (escluso da scope). Roadmap: F11 deploy.
"""

from __future__ import annotations

from django import forms
from django.utils.translation import gettext_lazy as _

from apps.calculators.enums import CaseType
from apps.jurisdictions.models import Country

from .models import Lead, LeadLanguage

MESSAGE_MIN_LENGTH = 20


class ContactForm(forms.Form):
    first_name = forms.CharField(
        label=_("First name"),
        max_length=80,
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=80,
    )
    email = forms.EmailField(label=_("Email"))
    phone_number = forms.CharField(
        label=_("Phone number"),
        max_length=32,
        required=False,
    )
    preferred_language = forms.ChoiceField(
        label=_("Preferred language"),
        choices=LeadLanguage.choices,
        initial=LeadLanguage.IT,
    )
    country = forms.ModelChoiceField(
        label=_("Country"),
        queryset=Country.objects.filter(is_active=True),
        required=False,
        empty_label=_("Select a country (optional)"),
        widget=forms.Select(attrs={"class": "premium-select mt-1"}),
    )
    case_type = forms.ChoiceField(
        label=_("Case type"),
        choices=[("", _("Not specified"))] + list(CaseType.choices),
        required=False,
        widget=forms.Select(attrs={"class": "premium-select mt-1"}),
    )
    message = forms.CharField(
        label=_("How can we help?"),
        widget=forms.Textarea(attrs={"rows": 5}),
        min_length=MESSAGE_MIN_LENGTH,
    )
    # F-p0-leg-3-consent: doppio consenso GDPR art. 6 + art. 9.
    # `privacy_accepted` (legacy nome) e' il consenso art. 6 (trattamento
    # dei dati di contatto per rispondere alla richiesta). Il nuovo
    # `special_categories_accepted` e' il consenso esplicito art. 9 (dati
    # particolari: salute, eventi traumatici, decesso, dati legali) che
    # possono apparire nel campo `message` o emergere dalla descrizione
    # del caso. Entrambi sono obbligatori sul contact form: la natura
    # del servizio (richiesta di valutazione legale) implica spesso la
    # condivisione di dati art. 9 anche solo nel testo libero.
    privacy_accepted = forms.BooleanField(
        label=_("I have read and accept the privacy notice."),
        required=True,
        error_messages={
            "required": _("You must accept the privacy notice to send your request."),
        },
    )
    special_categories_accepted = forms.BooleanField(
        label=_(
            "I expressly consent to the processing of special categories of "
            "personal data (health, family events, judicial proceedings) under "
            "GDPR art. 9.2.a, for the sole purpose of replying to this request."
        ),
        required=True,
        error_messages={
            "required": _(
                "You must give the explicit special-categories consent (GDPR "
                "art. 9) to send your request."
            ),
        },
    )

    # Hidden fields
    simulation_public_id = forms.CharField(required=False, widget=forms.HiddenInput())
    # Honeypot: utenti reali non lo compilano. I bot sì.
    website = forms.CharField(required=False, widget=forms.HiddenInput())

    def clean_message(self) -> str:
        # Strip + check minimo (anche con min_length già impostato, lo strip
        # previene workaround "                " da bot).
        value = (self.cleaned_data.get("message") or "").strip()
        if len(value) < MESSAGE_MIN_LENGTH:
            raise forms.ValidationError(
                _("Please describe your case in at least %(n)d characters.")
                % {"n": MESSAGE_MIN_LENGTH}
            )
        return value

    @property
    def is_likely_bot(self) -> bool:
        """True se il honeypot è compilato. Il form resta `is_valid()=True`."""
        return bool(self.data.get("website"))

    def to_lead_kwargs(self) -> dict:
        """Mappa i campi puliti del form ai kwargs di `Lead.objects.create`."""
        cleaned = self.cleaned_data
        return {
            "first_name": cleaned["first_name"],
            "last_name": cleaned["last_name"],
            "email": cleaned["email"],
            "phone_number": cleaned.get("phone_number", ""),
            "preferred_language": cleaned["preferred_language"],
            "country": cleaned.get("country"),
            "case_type": cleaned.get("case_type") or "",
            "message": cleaned["message"],
        }

    @staticmethod
    def language_choices() -> list[tuple[str, str]]:
        return list(LeadLanguage.choices)


# Quick re-export per simmetria con altre app.
__all__ = ["ContactForm", "Lead"]
