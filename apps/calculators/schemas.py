"""
Schema di output del motore di calcolo.

Lo schema è dichiarato come dataclass per:
- avere typing forte;
- essere importabile lato test senza setup Django;
- essere serializzabile JSON via `to_dict()` (no float per importi: usiamo
  `Decimal` convertito a stringa per evitare drift di precisione legale).

Compatibile con il formato in `CLAUDE.md` "Output standard del motore di
calcolo". Quando F5 wirara `cases.Simulation`, `simulation_id` sarà la
PK persistente; per ora è una stringa libera.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from .enums import CalculationStatus, ConfidenceLevel


@dataclass(frozen=True)
class SourceRef:
    """
    Riferimento a una `LegalSource` nell'output.

    Snapshot immutabile: copia i campi rilevanti al momento del calcolo
    così che il report PDF (F-report) resti riproducibile anche se la
    `LegalSource` viene successivamente aggiornata.
    """

    id: int | str
    title: str
    citation: str = ""
    official_url: str = ""
    publication_date: str | None = None
    source_type: str = ""
    reliability: str = ""
    country: str = ""
    jurisdiction: str = ""
    language: str = ""

    @classmethod
    def from_legal_source(cls, source: Any) -> SourceRef:
        """Costruttore-cortesia da un'istanza `legal_sources.LegalSource`."""
        publication_date = source.publication_date.isoformat() if source.publication_date else None
        return cls(
            id=source.pk,
            title=source.title,
            citation=source.citation or "",
            official_url=source.official_url or "",
            publication_date=publication_date,
            source_type=source.source_type or "",
            reliability=source.reliability or "",
            country=source.country.code if source.country_id else "",
            jurisdiction=source.jurisdiction.code if source.jurisdiction_id else "",
            language=source.language.code if source.language_id else "",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "citation": self.citation,
            "official_url": self.official_url,
            "publication_date": self.publication_date,
            "source_type": self.source_type,
            "reliability": self.reliability,
            "country": self.country,
            "jurisdiction": self.jurisdiction,
            "language": self.language,
        }


@dataclass(frozen=True)
class BreakdownItem:
    """Voce del breakdown di un calcolo (es. una posta di danno)."""

    label: str
    amount_min: Decimal | None = None
    amount_mid: Decimal | None = None
    amount_max: Decimal | None = None
    formula: str = ""
    source_ref_ids: tuple[int | str, ...] = ()
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "amount_min": _money_to_str(self.amount_min),
            "amount_mid": _money_to_str(self.amount_mid),
            "amount_max": _money_to_str(self.amount_max),
            "formula": self.formula,
            "source_ref_ids": list(self.source_ref_ids),
            "notes": self.notes,
        }


@dataclass
class CalculationResult:
    """Output canonico di ogni `BaseCalculator.compute()`."""

    simulation_id: str
    jurisdiction: str
    case_type: str
    currency: str
    status: str
    legal_disclaimer: str

    estimated_min: Decimal | None = None
    estimated_mid: Decimal | None = None
    estimated_max: Decimal | None = None

    breakdown: list[BreakdownItem] = field(default_factory=list)
    sources: list[SourceRef] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    missing_documents: list[str] = field(default_factory=list)
    confidence: str = ConfidenceLevel.LOW.value

    def to_dict(self) -> dict[str, Any]:
        return {
            "simulation_id": self.simulation_id,
            "jurisdiction": self.jurisdiction,
            "case_type": self.case_type,
            "currency": self.currency,
            "status": self.status,
            "estimated_min": _money_to_str(self.estimated_min),
            "estimated_mid": _money_to_str(self.estimated_mid),
            "estimated_max": _money_to_str(self.estimated_max),
            "breakdown": [item.to_dict() for item in self.breakdown],
            "sources": [src.to_dict() for src in self.sources],
            "assumptions": list(self.assumptions),
            "warnings": list(self.warnings),
            "missing_documents": list(self.missing_documents),
            "confidence": self.confidence,
            "legal_disclaimer": self.legal_disclaimer,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @property
    def is_unavailable(self) -> bool:
        return self.status == CalculationStatus.UNAVAILABLE_REQUIRES_LEGAL_VALIDATION


def _money_to_str(value: Decimal | None) -> str | None:
    """Decimal → str preserva la precisione legale (no float drift)."""
    return None if value is None else str(value)
