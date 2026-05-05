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


class FranceRoadAccidentWizardForm(ItalyRoadAccidentWizardForm):
    """France — accident de la circulation. Stesso schema input dell'Italia.

    Differenza unica: il default di ``accident_country`` passa da "IT" a
    "FR". I campi numerici/temporali sono identici (età, % invalidità
    permanente, giorni ITT, ecc.); le translation strings ``gettext_lazy``
    sono già localizzate via i18n. Il calculator FR è ancora un
    placeholder che restituisce ``unavailable`` — il form serve solo
    per scaffold del funnel.
    """

    accident_country = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        initial="FR",
        max_length=2,
    )

    def clean_accident_country(self) -> str:
        value = (self.cleaned_data.get("accident_country") or "").upper().strip()
        return value or "FR"


class BelgiumRoadAccidentWizardForm(ItalyRoadAccidentWizardForm):
    """Belgique — accident de la circulation. Stesso schema input.

    Differenza unica: il default di ``accident_country`` passa a "BE".
    Stesso pattern di scaffold del modulo francese: il calculator BE
    è ancora un placeholder che restituisce ``unavailable``.
    """

    accident_country = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        initial="BE",
        max_length=2,
    )

    def clean_accident_country(self) -> str:
        value = (self.cleaned_data.get("accident_country") or "").upper().strip()
        return value or "BE"


class InternationalInheritanceWizardForm(forms.Form):
    """
    Form scaffold per le successioni internazionali (MA, TN).

    REGOLA D'ORO: nessun calcolo qui. Il form raccoglie SOLO contesto
    qualitativo per il triage del caso. Il calculator pubblico
    restituisce ``unavailable_requires_legal_validation`` finché lo
    Studio non avrà promosso fonti/dataset/formula a ``approved``. Le
    quote ereditarie reali (faraïd) richiederanno un engine specifico
    futuro.

    GDPR: trattiamo dati sensibili (parentela, decesso, beni). Il
    consenso `simulation_processing` è obbligatorio. Nessun documento
    viene caricato in questa fase. Tutti i campi sono opzionali tranne
    il consenso.
    """

    deceased_country_of_last_residence = forms.CharField(
        label=_("Country of the deceased's last residence"),
        required=False,
        max_length=2,
        help_text=_("ISO 3166-1 alpha-2 code, e.g. MA, TN, IT, FR, BE."),
    )
    nationality = forms.CharField(
        label=_("Nationality of the deceased"),
        required=False,
        max_length=2,
        help_text=_("ISO 3166-1 alpha-2 code."),
    )
    has_will = forms.NullBooleanField(
        label=_("Did the deceased leave a will?"),
        required=False,
    )

    # --- Family situation ------------------------------------------------
    spouse_present = forms.BooleanField(
        label=_("Surviving spouse"),
        required=False,
        help_text=_("Tick if the deceased is survived by a spouse."),
    )
    sons_count = forms.IntegerField(
        label=_("Number of surviving sons"),
        required=False,
        min_value=0,
        max_value=30,
    )
    daughters_count = forms.IntegerField(
        label=_("Number of surviving daughters"),
        required=False,
        min_value=0,
        max_value=30,
    )
    father_present = forms.BooleanField(
        label=_("Father alive"),
        required=False,
        help_text=_("Tick if the deceased's father is alive."),
    )
    mother_present = forms.BooleanField(
        label=_("Mother alive"),
        required=False,
        help_text=_("Tick if the deceased's mother is alive."),
    )
    siblings_count = forms.IntegerField(
        label=_("Number of surviving siblings"),
        required=False,
        min_value=0,
        max_value=30,
        help_text=_("Optional. Brothers and sisters of the deceased."),
    )

    # --- Patrimony --------------------------------------------------------
    estate_value = forms.DecimalField(
        label=_("Estimated estate value (EUR)"),
        required=False,
        min_value=0,
        max_digits=14,
        decimal_places=2,
        help_text=_(
            "Optional. Used only to render indicative shares; the Studio "
            "verifies the actual estate before any final figure."
        ),
    )
    assets_countries = forms.CharField(
        label=_("Countries where assets are located"),
        required=False,
        max_length=120,
        help_text=_("Comma-separated ISO codes, e.g. 'MA, FR, IT'."),
    )
    message = forms.CharField(
        label=_("Additional context"),
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 3}),
        help_text=_("Anything you think is relevant. No documents needed."),
    )

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

    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        max_length=255,
    )

    @property
    def is_likely_bot(self) -> bool:
        return bool(self.data.get("website"))

    def to_input_data(self) -> dict[str, Any]:
        cleaned = self.cleaned_data
        deceased_country = (
            cleaned.get("deceased_country_of_last_residence") or ""
        ).upper().strip() or None
        sons = int(cleaned.get("sons_count") or 0)
        daughters = int(cleaned.get("daughters_count") or 0)
        siblings = int(cleaned.get("siblings_count") or 0)
        spouse = 1 if cleaned.get("spouse_present") else 0
        father = 1 if cleaned.get("father_present") else 0
        mother = 1 if cleaned.get("mother_present") else 0
        estate_value = cleaned.get("estate_value")
        return {
            "deceased_country_of_last_residence": deceased_country,
            "nationality": (cleaned.get("nationality") or "").upper().strip() or None,
            "has_will": cleaned.get("has_will"),
            "heirs": {
                "spouse": spouse,
                "sons": sons,
                "daughters": daughters,
                "father": father,
                "mother": mother,
                "siblings": siblings,
            },
            "estate_value": str(estate_value) if estate_value is not None else None,
            "assets_countries": (cleaned.get("assets_countries") or "").upper().strip() or None,
            "message": (cleaned.get("message") or "").strip() or None,
        }


__all__ = [
    "ItalyRoadAccidentWizardForm",
    "FranceRoadAccidentWizardForm",
    "BelgiumRoadAccidentWizardForm",
    "InternationalInheritanceWizardForm",
    "ACCIDENT_COUNTRY_DEFAULT",
]
