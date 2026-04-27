"""
Public-facing display labels for `CalculationStatus`.

Le label pubbliche sono diverse dai valori interni dell'enum: i valori
interni (`unavailable_requires_legal_validation`, `calculated`, ...) sono
identificatori tecnici stabili, le label sono testi rivolti all'utente
finale che possono evolvere senza spostare lo schema. Tenute fuori da
`gettext` di proposito: stringhe brevi, revisionate dallo Studio,
versionate via PR.

Aggiungere una lingua = aggiungere una entry nel dict.
Aggiungere uno status = registrare un'entry per ogni lingua supportata
e fornire un fallback in `_FALLBACK`.
"""

from __future__ import annotations

from .enums import CalculationStatus

DEFAULT_LANGUAGE = "it"

_FALLBACK = {
    CalculationStatus.CALCULATED.value: "Result",
    CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value: "Status",
    CalculationStatus.INSUFFICIENT_INPUT.value: "Status",
    CalculationStatus.ERROR.value: "Status",
}

_LABELS: dict[str, dict[str, str]] = {
    "it": {
        CalculationStatus.CALCULATED.value: "Stima disponibile",
        CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value: (
            "Validazione legale richiesta"
        ),
        CalculationStatus.INSUFFICIENT_INPUT.value: "Dati insufficienti",
        CalculationStatus.ERROR.value: "Errore tecnico",
    },
    "fr": {
        CalculationStatus.CALCULATED.value: "Estimation disponible",
        CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value: (
            "Validation juridique requise"
        ),
        CalculationStatus.INSUFFICIENT_INPUT.value: "Données insuffisantes",
        CalculationStatus.ERROR.value: "Erreur technique",
    },
    "en": {
        CalculationStatus.CALCULATED.value: "Estimate available",
        CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value: (
            "Legal validation required"
        ),
        CalculationStatus.INSUFFICIENT_INPUT.value: "Insufficient input",
        CalculationStatus.ERROR.value: "Technical error",
    },
    "ar": {
        # No localized arabic labels yet — fallback to EN.
        CalculationStatus.CALCULATED.value: "Estimate available",
        CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION.value: (
            "Legal validation required"
        ),
        CalculationStatus.INSUFFICIENT_INPUT.value: "Insufficient input",
        CalculationStatus.ERROR.value: "Technical error",
    },
}


def get_public_status_label(status: str | None, language: str | None = None) -> str:
    """
    Restituisce la label pubblica di uno status del calculator.

    Fallback chain:
    1. label per (language, status);
    2. label per (DEFAULT_LANGUAGE, status);
    3. label generica `_FALLBACK[status]`;
    4. lo status stesso (deve essere stato passato uno valido).
    """
    code = (language or DEFAULT_LANGUAGE).lower().split("-", 1)[0]
    by_lang = _LABELS.get(code) or _LABELS.get(DEFAULT_LANGUAGE) or {}
    if status and status in by_lang:
        return by_lang[status]
    if status and status in _LABELS[DEFAULT_LANGUAGE]:
        return _LABELS[DEFAULT_LANGUAGE][status]
    return _FALLBACK.get(status or "", status or "")
