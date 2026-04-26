"""
Eccezioni del motore di calcolo.

Sono volutamente poche: `BaseCalculator.compute()` è progettato per
ritornare `CalculationResult` con `status=ERROR` invece di sollevare
eccezioni verso l'API pubblica. Le eccezioni qui sono per errori
*programmatici* (registry, configurazione), non per errori utente.
"""


class CalculatorError(Exception):
    """Base per tutti gli errori del motore."""


class CalculatorAlreadyRegistered(CalculatorError):
    """Tentata registrazione di una coppia (jurisdiction, case_type) già presente."""


class CalculatorNotRegistered(CalculatorError):
    """Calculator non trovato per la coppia (jurisdiction, case_type) richiesta."""


class InvalidCalculatorClass(CalculatorError):
    """Tentata registrazione di una classe che non eredita da BaseCalculator."""
