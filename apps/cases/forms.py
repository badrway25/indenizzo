"""
Form pubblico del wizard simulazione.

`ItalyRoadAccidentWizardForm` è il primo wizard pubblico end-to-end:
serve a raccogliere input strutturato per `cases.run_simulation` su
giurisdizione `IT-NATIONAL` e case_type `road_accident_bodily_injury`.

Principi:
- *tutti* i campi numerici sono opzionali. Il wizard MVP non pretende di
  essere una perizia: l'utente può lasciare vuoti i dati che non conosce
  e la simulazione resta "unavailable_requires_legal_validation" se non
  c'è abbastanza materiale né fonti `approved`;
- consenso `simulation_processing` obbligatorio (REQ-1, REQ-3, GDPR);
- honeypot `website` per anti-spam: se compilato, la view scarta il
  submit ma non rivela la trappola;
- nessun calcolo o trasformazione qui: il form produce solo `input_data`
  pulito che viene passato così com'è al service layer.

Niente formula, niente coefficiente. La regola "meglio nessun calcolo
che un calcolo falso" del progetto si applica anche a questo livello:
non chiediamo input che il calculator non sa ancora usare in modo
legalmente validato.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from django import forms
from django.utils.translation import gettext_lazy as _

ACCIDENT_COUNTRY_DEFAULT = "IT"

# Bound difensivi: meglio rifiutare valori palesemente fuori scala che
# accettare un payload assurdo. Non è validazione medico-legale: serve
# solo ad evitare che il form salvi `999999%` di invalidità nel JSON.
DISABILITY_MIN = Decimal("0")
DISABILITY_MAX = Decimal("100")
FAULT_MIN = Decimal("0")
FAULT_MAX = Decimal("100")
DAYS_MIN = 0
DAYS_MAX = 3650  # ~10 anni; oltre serve valutazione manuale
MONEY_MIN = Decimal("0")
MONEY_MAX = Decimal("99999999.99")
AGE_MIN = 0
AGE_MAX = 120


class ItalyRoadAccidentWizardForm(forms.Form):
    """Form MVP — Italia, incidente stradale con lesioni personali."""

    accident_date = forms.DateField(
        label=_("Date of the accident"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
        help_text=_("If you don't know the exact date, leave this empty."),
    )
    victim_age = forms.IntegerField(
        label=_("Age of the injured person"),
        required=False,
        min_value=AGE_MIN,
        max_value=AGE_MAX,
        help_text=_("Age at the time of the accident, in years."),
    )
    permanent_disability_percentage = forms.DecimalField(
        label=_("Permanent disability (%)"),
        required=False,
        min_value=DISABILITY_MIN,
        max_value=DISABILITY_MAX,
        max_digits=5,
        decimal_places=2,
        help_text=_("Only if a medical report has assessed it. Otherwise leave empty."),
    )
    total_temporary_disability_days = forms.IntegerField(
        label=_("Total temporary disability — days"),
        required=False,
        min_value=DAYS_MIN,
        max_value=DAYS_MAX,
    )
    partial_temporary_disability_days = forms.IntegerField(
        label=_("Partial temporary disability — days"),
        required=False,
        min_value=DAYS_MIN,
        max_value=DAYS_MAX,
    )
    medical_expenses = forms.DecimalField(
        label=_("Documented medical expenses"),
        required=False,
        min_value=MONEY_MIN,
        max_value=MONEY_MAX,
        max_digits=12,
        decimal_places=2,
        help_text=_("Currency: EUR. Only amounts you can document."),
    )
    lost_income = forms.DecimalField(
        label=_("Lost income"),
        required=False,
        min_value=MONEY_MIN,
        max_value=MONEY_MAX,
        max_digits=12,
        decimal_places=2,
        help_text=_("Currency: EUR. Net income lost due to the accident."),
    )
    fault_percentage = forms.DecimalField(
        label=_("Estimated own fault (%)"),
        required=False,
        min_value=FAULT_MIN,
        max_value=FAULT_MAX,
        max_digits=5,
        decimal_places=2,
        help_text=_("0% if you believe you bear no responsibility."),
    )

    # Hidden / locked
    accident_country = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        initial=ACCIDENT_COUNTRY_DEFAULT,
        max_length=2,
    )

    # Consent — obbligatorio per `simulation_processing`.
    consent_simulation = forms.BooleanField(
        label=_(
            "I consent to processing the data above for the sole purpose of "
            "producing an indicative simulation."
        ),
        required=True,
        error_messages={
            "required": _("You must accept the simulation consent to run a simulation."),
        },
    )

    # Honeypot anti-bot.
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        max_length=255,
    )

    def clean_accident_date(self) -> date | None:
        value = self.cleaned_data.get("accident_date")
        if value is None:
            return None
        if value > date.today():
            raise forms.ValidationError(_("The accident date cannot be in the future."))
        return value

    def clean_accident_country(self) -> str:
        value = (self.cleaned_data.get("accident_country") or "").upper().strip()
        return value or ACCIDENT_COUNTRY_DEFAULT

    @property
    def is_likely_bot(self) -> bool:
        """True se il honeypot è compilato. Il form resta `is_valid()`."""
        return bool(self.data.get("website"))

    def to_input_data(self) -> dict[str, Any]:
        """
        Mappa i campi puliti al `input_data` JSON-serializzabile per
        `run_simulation`. NON include il consenso e il honeypot: quei
        campi sono di flusso, non di dominio.

        Decimali → str (preserva precisione legale).
        Date → ISO 8601 string.
        """
        cleaned = self.cleaned_data
        return {
            "accident_country": cleaned.get("accident_country", ACCIDENT_COUNTRY_DEFAULT),
            "accident_date": (
                cleaned["accident_date"].isoformat() if cleaned.get("accident_date") else None
            ),
            "victim_age": cleaned.get("victim_age"),
            "permanent_disability_percentage": _decimal_or_none(
                cleaned.get("permanent_disability_percentage")
            ),
            "total_temporary_disability_days": cleaned.get("total_temporary_disability_days"),
            "partial_temporary_disability_days": cleaned.get("partial_temporary_disability_days"),
            "medical_expenses": _decimal_or_none(cleaned.get("medical_expenses")),
            "lost_income": _decimal_or_none(cleaned.get("lost_income")),
            "fault_percentage": _decimal_or_none(cleaned.get("fault_percentage")),
        }


def _decimal_or_none(value: Decimal | None) -> str | None:
    if value is None:
        return None
    return str(value)


__all__ = ["ItalyRoadAccidentWizardForm", "ACCIDENT_COUNTRY_DEFAULT"]
