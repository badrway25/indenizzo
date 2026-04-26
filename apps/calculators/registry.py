"""
Registry pluggable dei calculator.

Mappa `(jurisdiction_code, case_type) -> classe BaseCalculator`.

Le registrazioni avvengono al **momento dell'import** dei moduli engine
(es. `apps.calculators.engines.italy`); l'import dei moduli engine è
forzato in `apps.py.ready()` così che la mappa sia popolata in tempo
sia in produzione che nei test.

Regola: se la coppia richiesta non è registrata, il chiamante riceve
`None` (mai eccezione) — è il calculator chiamante che decide se
trattarlo come "unavailable" o errore. Questo evita crash su case_type
non implementati e tiene il sistema "fail safe" verso l'utente finale.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .exceptions import (
    CalculatorAlreadyRegistered,
    CalculatorNotRegistered,
    InvalidCalculatorClass,
)

if TYPE_CHECKING:
    from .engines.base import BaseCalculator


_RegistryKey = tuple[str, str]


class CalculatorRegistry:
    """In-memory map (jurisdiction, case_type) → class."""

    def __init__(self) -> None:
        self._entries: dict[_RegistryKey, type[BaseCalculator]] = {}

    @staticmethod
    def _key(jurisdiction_code: str, case_type: str) -> _RegistryKey:
        return jurisdiction_code.upper(), case_type

    def register(
        self,
        jurisdiction_code: str,
        case_type: str,
        calculator_class: type[BaseCalculator],
        *,
        replace: bool = False,
    ) -> None:
        """Registra una classe calculator. Solleva se già presente, salvo `replace=True`."""
        from .engines.base import BaseCalculator  # late import per evitare ciclo

        if not isinstance(calculator_class, type) or not issubclass(
            calculator_class, BaseCalculator
        ):
            raise InvalidCalculatorClass(
                f"{calculator_class!r} is not a subclass of BaseCalculator"
            )

        key = self._key(jurisdiction_code, case_type)
        if key in self._entries and not replace:
            raise CalculatorAlreadyRegistered(f"calculator already registered for {key}")
        self._entries[key] = calculator_class

    def get(self, jurisdiction_code: str, case_type: str) -> type[BaseCalculator] | None:
        """Recupera la classe calculator. Restituisce None se non registrata."""
        return self._entries.get(self._key(jurisdiction_code, case_type))

    def require(self, jurisdiction_code: str, case_type: str) -> type[BaseCalculator]:
        """Come `get()` ma solleva `CalculatorNotRegistered` se assente."""
        cls = self.get(jurisdiction_code, case_type)
        if cls is None:
            raise CalculatorNotRegistered(
                f"no calculator registered for ({jurisdiction_code}, {case_type})"
            )
        return cls

    def list_available(self) -> list[_RegistryKey]:
        return sorted(self._entries.keys())

    def unregister(self, jurisdiction_code: str, case_type: str) -> None:
        """Per i test. Non chiamare in produzione."""
        self._entries.pop(self._key(jurisdiction_code, case_type), None)

    def clear(self) -> None:
        """Per i test. Reset completo."""
        self._entries.clear()


# Singleton per processo. Importazione lazy nei moduli engine.
registry = CalculatorRegistry()


def register_calculator(
    jurisdiction_code: str,
    case_type: str,
    calculator_class: type[BaseCalculator],
) -> None:
    registry.register(jurisdiction_code, case_type, calculator_class)


def get_calculator(jurisdiction_code: str, case_type: str) -> type[BaseCalculator] | None:
    return registry.get(jurisdiction_code, case_type)


def list_available_calculators() -> list[_RegistryKey]:
    return registry.list_available()
