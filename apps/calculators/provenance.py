"""Build a deterministic, PII-safe calculation-provenance snapshot.

H1-8. Given the legal-data objects an engine resolved while computing
(``CompensationDataset``, ``CalculationFormula``, the matched
``CompensationTableRow`` rows, and an optional secondary range dataset), produce
a structured dict that lets a CALCULATED simulation be audited and re-derived
even after the underlying legal data changes.

Design rules:

- **Deterministic**: same inputs → identical dict (no timestamps, no randomness;
  ``calculated_at`` is stamped by the service layer at persist time).
- **PII-safe**: contains only legal-data identifiers + hashes. The victim's
  inputs are NOT duplicated here — they already live in ``Simulation.input_data``;
  reproducibility = input_data + this provenance. Row age/disability values are
  *table bands*, not the user's data.
- **No secrets**: never any ``.env`` value, token, or health data.
- **Honest, fail-closed**: if an approved dataset has no ``source_version`` the
  snapshot records ``source_version_present: false`` and a null content hash —
  it never invents provenance and never silently fails the calculation.
- **Never raises**: the builder is defensive so it cannot break a calculation;
  missing attributes degrade to ``None``.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

SCHEMA_VERSION = 1


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical(obj: Any) -> str:
    """Stable JSON for hashing (sorted keys, no whitespace, str-coerced)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str)


def _dataset_snapshot(dataset: Any) -> dict[str, Any]:
    sv = getattr(dataset, "source_version", None)
    sv_present = bool(getattr(dataset, "source_version_id", None))
    return {
        "id": getattr(dataset, "pk", None),
        "version_label": getattr(dataset, "version_label", "") or "",
        "status": getattr(dataset, "status", "") or "",
        "case_type": getattr(dataset, "case_type", "") or "",
        "source_id": getattr(dataset, "source_id", None),
        "source_version_present": sv_present,
        "source_version_id": getattr(dataset, "source_version_id", None),
        "source_version_label": (getattr(sv, "version_label", "") or "") if sv_present else "",
        # Honest: null when there is no source version to anchor the hash to.
        "source_content_hash": (getattr(sv, "content_hash", "") or None) if sv_present else None,
    }


def _formula_snapshot(formula: Any) -> dict[str, Any]:
    params = getattr(formula, "parameters", None) or {}
    return {
        "id": getattr(formula, "pk", None),
        "code": getattr(formula, "code", "") or "",
        "status": getattr(formula, "status", "") or "",
        "params_hash": _sha256(_canonical(params)),
    }


def _row_snapshot(row: Any) -> dict[str, Any]:
    # value_hash covers every monetary-bearing field, so an in-place edit of an
    # approved row is detectable when re-verifying a historical simulation.
    value_payload = {
        "point_value": getattr(row, "point_value", None),
        "daily_amount": getattr(row, "daily_amount", None),
        "coefficient": getattr(row, "coefficient", None),
        "extra": getattr(row, "extra", None) or {},
    }
    return {
        "id": getattr(row, "pk", None),
        "row_type": getattr(row, "row_type", "") or "",
        "age_min": getattr(row, "age_min", None),
        "age_max": getattr(row, "age_max", None),
        "disability_min": getattr(row, "disability_min", None),
        "disability_max": getattr(row, "disability_max", None),
        "value_hash": _sha256(_canonical(value_payload)),
    }


def build_calculation_provenance(
    *,
    engine: str,
    engine_version: str,
    amount_rule: str,
    dataset: Any,
    formula: Any,
    rows: list[Any],
    range_dataset: Any | None = None,
) -> dict[str, Any]:
    """Assemble the provenance snapshot. Defensive — never raises."""
    try:
        snapshot: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "engine": engine or "",
            "engine_version": engine_version or "",
            "amount_rule": amount_rule or "",
            "dataset": _dataset_snapshot(dataset),
            "formula": _formula_snapshot(formula),
            "table_rows": [_row_snapshot(r) for r in rows if r is not None],
        }
        if range_dataset is not None:
            snapshot["range_dataset"] = _dataset_snapshot(range_dataset)
        return snapshot
    except Exception:  # pragma: no cover - provenance must never break a calc
        # Last-resort: record that provenance assembly failed, never fake it.
        return {"schema_version": SCHEMA_VERSION, "error": "provenance_build_failed"}
