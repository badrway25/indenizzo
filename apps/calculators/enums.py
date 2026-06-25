"""
Enum del motore di calcolo.

Sono `TextChoices` per coerenza col resto del progetto, anche se non
finiscono in DB: vivono nello schema `CalculationResult`. Le label sono
`gettext_lazy`-friendly perché potrebbero essere mostrate via API/admin.

Le voci di `CaseType` rispecchiano la tassonomia dei moduli giuridici
in `docs/architecture/PRODUCT_REQUIREMENTS.md` (REQ-4). NON è la lista
completa: F4 espone solo i moduli che hanno (o avranno presto) un
calculator registrato. Aggiunte progressive in F5+.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _


class CaseType(models.TextChoices):
    """Tipi di caso supportati dal motore di calcolo (subset MVP)."""

    ROAD_ACCIDENT_BODILY_INJURY = (
        "road_accident_bodily_injury",
        _("Road accident — bodily injury"),
    )
    # P8: official art. 139 CAP micropermanenti (1–9%) for road accidents.
    ROAD_ACCIDENT_MICROLESIONS = (
        "road_accident_microlesions",
        _("Road accident — microlesions (art. 139)"),
    )
    # P8: medical-liability biological damage — tabular estimate only (L. 24/2017
    # → art. 138/139 CAP). Never models fault, causal link or extra heads.
    MEDICAL_LIABILITY_BIOLOGICAL = (
        "medical_liability_biological_damage",
        _("Medical liability — tabular biological damage"),
    )
    MEDICAL_MALPRACTICE = "medical_malpractice", _("Medical malpractice")
    WORK_INJURY = "work_injury", _("Work injury")
    DEATH_COMPENSATION = "death_compensation", _("Death compensation")
    PARENTAL_LOSS = "parental_loss", _("Parental loss")
    PATRIMONIAL_DAMAGE = "patrimonial_damage", _("Patrimonial damage")
    INHERITANCE_BASIC = "inheritance_basic", _("Inheritance — basic")
    INTERNATIONAL_INHERITANCE = (
        "international_inheritance",
        _("Inheritance — international"),
    )
    GENERIC_LEGAL_ASSESSMENT = (
        "generic_legal_assessment",
        _("Generic legal assessment"),
    )


class CalculationStatus(models.TextChoices):
    """
    Stato finale di una `CalculationResult`.

    `unavailable_requires_legal_validation` è il default difensivo: ogni
    volta che mancano fonti `approved` o non c'è ancora una formula
    validata, il motore restituisce questo status. È esattamente la
    regola "meglio nessun calcolo che un calcolo falso" del progetto.
    """

    UNAVAILABLE_REQUIRES_LEGAL_VALIDATION = (
        "unavailable_requires_legal_validation",
        _("Unavailable — requires legal validation"),
    )
    INSUFFICIENT_INPUT = "insufficient_input", _("Insufficient input")
    CALCULATED = "calculated", _("Calculated")
    ERROR = "error", _("Error")


class ConfidenceLevel(models.TextChoices):
    LOW = "low", _("Low")
    MEDIUM = "medium", _("Medium")
    HIGH = "high", _("High")
