"""H1-8.1: read-only reproducibility verification of a calculated simulation.

Given a ``Simulation``, re-derive the legal-data provenance from the CURRENT DB
and compare it to the snapshot stored at calculation time (H1-8). Reports whether
the result is still ``reproducible`` or has ``drifted`` — without recomputing
amounts from sensitive input and without exposing any PII.

The re-derivation reuses the exact hashing helpers from
``apps.calculators.provenance`` so a recomputed hash is byte-identical to how it
was first recorded (single source of truth for the hash logic).
"""

from __future__ import annotations

from typing import Any

# Deliberate reuse of the H1-8 snapshot helpers so re-derived hashes match the
# originals exactly. These are internal to the provenance module but are the
# canonical hash logic; re-implementing them here would risk divergence.
from apps.calculators.provenance import (
    SCHEMA_VERSION,
    _dataset_snapshot,
    _formula_snapshot,
    _row_snapshot,
)

# Verification statuses.
REPRODUCIBLE = "reproducible"
DRIFTED = "drifted"
INCOMPLETE = "incomplete"
LEGACY_NO_PROVENANCE = "legacy_no_provenance"
NOT_CALCULATED = "not_calculated"

_CALCULATED = "calculated"
_APPROVED = "approved"


def _check(name: str, ok: bool, detail: str = "") -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def _result(status: str, *, checks, warnings, errors, summary) -> dict[str, Any]:
    return {
        "status": status,
        "checks": checks,
        "warnings": warnings,
        "errors": errors,
        "summary": summary,
        # Contract: this payload is derived only from legal-data ids/labels/
        # hashes/statuses — never from input_data / victim / health / PII.
        "pii_safe": True,
    }


def _verify_dataset(stored: dict, *, label: str, checks, errors) -> bool:
    """Compare a stored dataset snapshot against the current DB. Returns drift."""
    from apps.compensation.models import CompensationDataset

    ds_id = stored.get("id")
    if not ds_id:
        checks.append(_check(f"{label}_id_present", False, "snapshot has no dataset id"))
        return True
    current = CompensationDataset.objects.filter(pk=ds_id).first()
    if current is None:
        checks.append(_check(f"{label}_exists", False, f"dataset id={ds_id} no longer exists"))
        errors.append(f"{label} dataset id={ds_id} deleted")
        return True
    checks.append(_check(f"{label}_exists", True, f"id={ds_id}"))

    drift = False
    fresh = _dataset_snapshot(current)
    # still approved?
    still_approved = current.status == _APPROVED
    checks.append(_check(f"{label}_still_approved", still_approved, f"status={current.status}"))
    drift = drift or not still_approved
    # version label stable
    label_ok = fresh["version_label"] == stored.get("version_label")
    checks.append(_check(f"{label}_version_label_matches", label_ok))
    drift = drift or not label_ok
    # source version + content hash
    if stored.get("source_version_present"):
        sv_ok = fresh["source_version_id"] == stored.get("source_version_id")
        checks.append(_check(f"{label}_source_version_matches", sv_ok))
        hash_ok = fresh["source_content_hash"] == stored.get("source_content_hash")
        checks.append(_check(f"{label}_source_hash_matches", hash_ok))
        drift = drift or not sv_ok or not hash_ok
    else:
        # Honest: there was never a source-version hash to anchor (legacy
        # approved dataset). Not a drift — report as skipped.
        checks.append(
            _check(f"{label}_source_hash_matches", True, "skipped: no source version in snapshot")
        )
    return drift


def verify_simulation(simulation) -> dict[str, Any]:
    """Verify one simulation. Pure + read-only; returns a structured result."""
    checks: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    if simulation.status != _CALCULATED:
        return _result(
            NOT_CALCULATED,
            checks=[_check("status_calculated", False, f"status={simulation.status}")],
            warnings=[],
            errors=[],
            summary=f"Simulation is not calculated (status={simulation.status}).",
        )
    checks.append(_check("status_calculated", True))

    prov = simulation.calculation_provenance or {}
    if not prov:
        return _result(
            LEGACY_NO_PROVENANCE,
            checks=checks + [_check("provenance_present", False)],
            warnings=["calculated before H1-8: no provenance snapshot recorded"],
            errors=[],
            summary="Calculated simulation without a provenance snapshot (legacy).",
        )
    checks.append(_check("provenance_present", True))

    # Structural completeness.
    schema_ok = prov.get("schema_version") == SCHEMA_VERSION
    checks.append(
        _check("schema_version_supported", schema_ok, f"got {prov.get('schema_version')}")
    )
    missing_keys = [k for k in ("dataset", "formula", "table_rows") if not prov.get(k)]
    if missing_keys or not schema_ok:
        if missing_keys:
            warnings.append(f"provenance missing keys: {', '.join(missing_keys)}")
        return _result(
            INCOMPLETE,
            checks=checks,
            warnings=warnings,
            errors=errors,
            summary="Provenance snapshot is incomplete or uses an unsupported schema.",
        )
    checks.append(_check("engine_present", bool(prov.get("engine")), prov.get("engine", "")))
    checks.append(_check("engine_version_present", bool(prov.get("engine_version"))))
    checks.append(_check("calculated_at_present", bool(prov.get("calculated_at"))))

    drift = False

    # Primary dataset.
    drift = _verify_dataset(prov["dataset"], label="dataset", checks=checks, errors=errors) or drift

    # Range dataset (optional).
    if prov.get("range_dataset"):
        drift = (
            _verify_dataset(
                prov["range_dataset"], label="range_dataset", checks=checks, errors=errors
            )
            or drift
        )

    # Formula.
    from apps.compensation.models import CalculationFormula

    f_stored = prov["formula"]
    f_id = f_stored.get("id")
    current_formula = CalculationFormula.objects.filter(pk=f_id).first() if f_id else None
    if current_formula is None:
        checks.append(_check("formula_exists", False, f"formula id={f_id} no longer exists"))
        errors.append(f"formula id={f_id} deleted")
        drift = True
    else:
        checks.append(_check("formula_exists", True, f"id={f_id}"))
        fresh_f = _formula_snapshot(current_formula)
        code_ok = fresh_f["code"] == f_stored.get("code")
        checks.append(_check("formula_code_matches", code_ok))
        hash_ok = fresh_f["params_hash"] == f_stored.get("params_hash")
        checks.append(_check("formula_params_hash_matches", hash_ok))
        drift = drift or not code_ok or not hash_ok

    # Table rows.
    from apps.compensation.models import CompensationTableRow

    for stored_row in prov["table_rows"]:
        r_id = stored_row.get("id")
        current_row = CompensationTableRow.objects.filter(pk=r_id).first() if r_id else None
        if current_row is None:
            checks.append(_check(f"row_{r_id}_exists", False, f"row id={r_id} no longer exists"))
            errors.append(f"table row id={r_id} deleted")
            drift = True
            continue
        fresh_r = _row_snapshot(current_row)
        row_ok = fresh_r["value_hash"] == stored_row.get("value_hash")
        checks.append(_check(f"row_{r_id}_value_hash_matches", row_ok))
        drift = drift or not row_ok

    if drift:
        return _result(
            DRIFTED,
            checks=checks,
            warnings=warnings,
            errors=errors,
            summary="Legal data changed since calculation — estimate needs re-verification.",
        )
    return _result(
        REPRODUCIBLE,
        checks=checks,
        warnings=warnings,
        errors=errors,
        summary="All provenance hashes match the current legal data.",
    )
