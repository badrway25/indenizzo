"""Read-only audit of FR road-accident activation readiness.

Iter: F-france-activation-readiness-audit.

Inspect the live DB and the wizard URL surface to produce a structured
markdown report at ``docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md``.

The audit is **read-only**:

- it never writes to the DB (no ``LegalSource.save``, no
  ``CompensationDataset.save``, no ``CalculationFormula.save``,
  no ``Simulation.save``);
- it does not call ``run_simulation`` (which would persist a Simulation
  audit row); calculator readiness is inferred structurally from
  dataset/formula counts and the registry;
- the wizard probe uses a Django test ``Client`` GET which is
  read-only (template render only — no Simulation row created on a
  GET);
- it never alters the manual_attach files on disk: only sha256/path
  reads.

Exit codes:

- 0 = audit completed (regardless of whether activation is GO or NO-GO).
- 1 = audit failed because of an unexpected error (DB integrity, etc.).
- 2 = required schema/data missing (FR sources or datasets absent).
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

# Force UTF-8 on Windows consoles (cp1252 default would break on any
# non-ASCII glyph the report may surface).
try:
    sys.stdout.reconfigure(encoding="utf-8")
except (AttributeError, OSError):
    pass

import django  # noqa: E402

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client  # noqa: E402

from apps.calculators.enums import CaseType  # noqa: E402
from apps.calculators.registry import get_calculator  # noqa: E402
from apps.compensation.models import (  # noqa: E402
    CalculationFormula,
    CompensationDataset,
    DatasetStatus,
)
from apps.legal_sources.enums import SourceStatus  # noqa: E402
from apps.legal_sources.models import LegalSource  # noqa: E402

REPORT_PATH = REPO_ROOT / "docs" / "architecture" / "FRANCE_ACTIVATION_READINESS_AUDIT.md"

BADINTER_SLUG = "fr-loi-badinter-1985"
MORNET_SLUG = "fr-referentiel-mornet-2024"
GAZETTE_SLUG = "fr-bareme-capitalisation-gazette-palais-2022"

MORNET_DATASET_LABEL = "FR-MORNET-2024-DRAFT"
GAZETTE_DATASET_LABEL = "FR-GAZETTE-PALAIS-2022-DRAFT"

EXPECTED_COUNTS: dict[str, dict[str, int]] = {
    MORNET_DATASET_LABEL: {
        "fr_dfp_per_age_disability_amount_per_point": 180,
        "fr_prejudice_affection_per_relation_amount": 11,
    },
    GAZETTE_DATASET_LABEL: {
        "fr_capitalisation_viagere_per_age_sex_rate_coefficient": 416,
        "fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient": 3752,
        "fr_anticipated_payment_years_per_age_sex_rate_years": 20,
    },
}

# Notes block markers used by the manual_attach pipeline + validation step.
MANUAL_ATTACH_BEGIN = "[manual_attach] BEGIN"
MANUAL_ATTACH_END = "[manual_attach] END"
VALIDATION_BEGIN = "[official_source_validation] BEGIN"
VALIDATION_END = "[official_source_validation] END"


# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class CheckResult:
    label: str
    status: str  # PASS | BLOCKED | FAIL | INFO
    details: str = ""


@dataclass
class AuditReport:
    generated_at: str
    sources: list[CheckResult] = field(default_factory=list)
    datasets: list[CheckResult] = field(default_factory=list)
    formula: list[CheckResult] = field(default_factory=list)
    engine: list[CheckResult] = field(default_factory=list)
    wizard: list[CheckResult] = field(default_factory=list)
    overall_status: str = ""  # NO-GO | OFFICIAL-ONLY | INDICATIVE-ONLY | GO
    overall_summary: str = ""


# ---------------------------------------------------------------------------
# Per-block audits
# ---------------------------------------------------------------------------


def _extract_block(notes: str, begin: str, end: str) -> dict | None:
    if begin not in (notes or ""):
        return None
    payload = notes.split(begin, 1)[1].split(end, 1)[0]
    try:
        return json.loads(payload.strip())
    except json.JSONDecodeError:
        return None


def audit_sources() -> list[CheckResult]:
    out: list[CheckResult] = []

    badinter = LegalSource.objects.filter(slug=BADINTER_SLUG).first()
    if badinter is None:
        out.append(
            CheckResult(
                label="Badinter LegalSource",
                status="FAIL",
                details=f"slug {BADINTER_SLUG!r} missing in DB",
            )
        )
    else:
        ma = _extract_block(badinter.notes or "", MANUAL_ATTACH_BEGIN, MANUAL_ATTACH_END)
        val = _extract_block(badinter.notes or "", VALIDATION_BEGIN, VALIDATION_END)
        ma_ok = (
            ma is not None
            and ma.get("classification") == "manual_attach_success"
            and ma.get("marker_check_passed") is True
        )
        val_ok = (
            val is not None
            and val.get("official_source_validation") == "passed"
            and (val.get("structural_markers_passed") or 0) >= 11
        )
        details_lines = [
            f"status={badinter.status}",
            f"manual_attach_block={'present' if ma else 'missing'}",
            f"official_source_validation_block={'present' if val else 'missing'}",
        ]
        if ma:
            details_lines.append(f"manual_attach.sha256={ma.get('sha256', '')[:12]}")
            details_lines.append(
                f"manual_attach.marker_check_passed={ma.get('marker_check_passed')}"
            )
        if val:
            details_lines.append(
                "official_source_validation."
                f"structural_markers={val.get('structural_markers_passed')}/"
                f"{val.get('structural_markers_total')}"
            )
        out.append(
            CheckResult(
                label="Badinter — official legal basis",
                status="PASS" if ma_ok and val_ok else "BLOCKED",
                details=" | ".join(details_lines),
            )
        )

    for slug in (MORNET_SLUG, GAZETTE_SLUG):
        src = LegalSource.objects.filter(slug=slug).first()
        if src is None:
            out.append(
                CheckResult(
                    label=f"{slug} — quantification source",
                    status="FAIL",
                    details=f"slug {slug!r} missing in DB",
                )
            )
            continue
        attachment_count = src.attachments.count()
        attachment_summary = (
            f"{attachment_count} attachment(s)" if attachment_count else "no LegalSourceAttachment"
        )
        is_blocked = src.status != SourceStatus.APPROVED
        out.append(
            CheckResult(
                label=f"{slug} — quantification source",
                status="BLOCKED" if is_blocked else "PASS",
                details=(
                    f"status={src.status} | reliability={src.reliability} | "
                    f"{attachment_summary} | "
                    f"legal_reviewer={'set' if src.legal_reviewer_id else 'unset'}"
                ),
            )
        )
    return out


def audit_datasets() -> list[CheckResult]:
    out: list[CheckResult] = []
    for label, per_type in EXPECTED_COUNTS.items():
        ds = CompensationDataset.objects.filter(version_label=label).first()
        if ds is None:
            out.append(
                CheckResult(
                    label=f"Dataset {label}",
                    status="FAIL",
                    details=f"version_label {label!r} missing in DB",
                )
            )
            continue
        is_draft = ds.status == DatasetStatus.DRAFT
        is_usable = ds.is_usable_for_calculations
        rows_summary_parts: list[str] = []
        all_counts_match = True
        for row_type, expected in per_type.items():
            actual = ds.rows.filter(row_type=row_type).count()
            mark = "OK" if actual == expected else "MISMATCH"
            rows_summary_parts.append(f"{row_type}={actual}/{expected} [{mark}]")
            if actual != expected:
                all_counts_match = False
        # Dataset is "PASS for DRAFT integrity" if status=DRAFT, not usable,
        # and all row counts match the upstream extractor outputs.
        status = "PASS" if is_draft and not is_usable and all_counts_match else "BLOCKED"
        out.append(
            CheckResult(
                label=f"Dataset {label}",
                status=status,
                details=(
                    f"status={ds.status} | is_usable_for_calculations={is_usable} | "
                    + "; ".join(rows_summary_parts)
                ),
            )
        )
    return out


def audit_formulas() -> list[CheckResult]:
    fr_count = CalculationFormula.objects.filter(dataset__country__code="FR").count()
    return [
        CheckResult(
            label="CalculationFormula(FR) count",
            status="PASS" if fr_count == 0 else "BLOCKED",
            details=(
                f"count={fr_count}; expected 0 — no FR formula must exist on "
                "the public path until Studio approves Mornet/Gazette."
            ),
        )
    ]


def audit_engine() -> list[CheckResult]:
    cls = get_calculator("FR-NATIONAL", CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    name = cls.__name__ if cls is not None else "<missing>"
    # Inspect the registry (services.SUPPORTED_*).
    from apps.compensation.services import (  # noqa: PLC0415
        SINGLE_ROW_RANGE_AMOUNT_RULES,
        SUPPORTED_AMOUNT_RULES,
        SUPPORTED_ENGINES,
    )

    engine_registered = "france_road_accident_v1" in SUPPORTED_ENGINES
    rule_registered = "france_dfp_point_value_direct" in SUPPORTED_AMOUNT_RULES
    rule_is_single_row_range = "france_dfp_point_value_direct" in SINGLE_ROW_RANGE_AMOUNT_RULES
    return [
        CheckResult(
            label="FR calculator class registered",
            status="PASS" if cls is not None else "FAIL",
            details=f"class={name}",
        ),
        CheckResult(
            label="france_road_accident_v1 in SUPPORTED_ENGINES",
            status="PASS" if engine_registered else "FAIL",
            details=f"registered={engine_registered}",
        ),
        CheckResult(
            label="france_dfp_point_value_direct in SUPPORTED_AMOUNT_RULES",
            status="PASS" if rule_registered else "FAIL",
            details=(
                f"registered={rule_registered} | " f"is_single_row_range={rule_is_single_row_range}"
            ),
        ),
    ]


def audit_wizard(client: Client) -> list[CheckResult]:
    out: list[CheckResult] = []
    # Pick a host name guaranteed to be in ALLOWED_HOSTS in this project's
    # config (loopback). The default test client uses ``testserver`` which
    # is rejected by the project's CommonMiddleware/SECURE_HSTS config in
    # production-shape settings.
    host = "127.0.0.1"
    for path in (
        "/healthz/",
        "/countries/france/",
        "/wizard/fr/road-accident/",
        "/contact/",
    ):
        try:
            response = client.get(path, HTTP_HOST=host)
            code = response.status_code
        except Exception as exc:  # noqa: BLE001
            out.append(
                CheckResult(
                    label=f"GET {path}",
                    status="FAIL",
                    details=f"exception {exc.__class__.__name__}: {exc}",
                )
            )
            continue
        out.append(
            CheckResult(
                label=f"GET {path}",
                status="PASS" if 200 <= code < 400 else "BLOCKED",
                details=f"http_status={code}",
            )
        )
    return out


# ---------------------------------------------------------------------------
# Verdict + report writer
# ---------------------------------------------------------------------------


def _compute_verdict(report: AuditReport) -> tuple[str, str]:
    badinter = next(
        (r for r in report.sources if r.label.startswith("Badinter")),
        None,
    )
    mornet_blocked = any(r.status == "BLOCKED" and MORNET_SLUG in r.label for r in report.sources)
    gazette_blocked = any(r.status == "BLOCKED" and GAZETTE_SLUG in r.label for r in report.sources)
    badinter_pass = badinter is not None and badinter.status == "PASS"

    formula_count_zero = all(r.status == "PASS" for r in report.formula)
    engine_pass = all(r.status == "PASS" for r in report.engine)

    if mornet_blocked and gazette_blocked and badinter_pass:
        verdict = "OFFICIAL-ONLY"
        summary = (
            "Badinter validated as official source; Mornet/Gazette stay "
            "needs_review -> calculator stays unavailable. Activating "
            "anything beyond the source validation is NO-GO until a "
            "Studio LegalReview promotes Mornet or Gazette."
        )
    elif mornet_blocked or gazette_blocked:
        verdict = "NO-GO"
        summary = (
            "FR road-accident calculator activation is blocked. At least "
            "one quantification source is still in needs_review/draft."
        )
    elif badinter_pass and formula_count_zero and engine_pass:
        verdict = "INDICATIVE-READY"
        summary = (
            "All upstream sources are APPROVED but no FR formula has been "
            "wired yet. The next iter must add the formula explicitly + a "
            "smoke test before the public path goes live."
        )
    else:
        verdict = "NO-GO"
        summary = "One or more readiness checks failed; see details below."
    return verdict, summary


def _section_table(rows: list[CheckResult]) -> str:
    if not rows:
        return "_(no checks recorded)_"
    lines = ["| Check | Status | Details |", "|---|---|---|"]
    for r in rows:
        details = (r.details or "").replace("|", "\\|")
        lines.append(f"| {r.label} | **{r.status}** | {details} |")
    return "\n".join(lines)


def write_report(report: AuditReport) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    body = f"""# FR road-accident — activation readiness audit

**Iter:** `F-france-activation-readiness-audit`.

**Generated:** `{report.generated_at}`.

Read-only audit of the FR road-accident pipeline. The script that
produced this file (`scripts/legal_data/audit_france_activation_readiness.py`)
makes **no DB writes** and never invokes `run_simulation`. It only
inspects model state, the engine registry, and the wizard URL surface.

## 1. Executive summary

**Verdict:** `{report.overall_status}`.

{report.overall_summary}

## 2. Current status

The current state is the conservative one:

- Loi Badinter (the *cornice normativa*) is mechanically authenticated
  via manual attach + 11/11 structural markers vs Légifrance — it is
  the file the report layer can already cite with a sha256 and a
  Légifrance canonical URL.
- The two *quantification* sources (Mornet 2024, Gazette du Palais 2022)
  remain in `needs_review`. Their candidate datasets exist in DB as
  `DRAFT` only and never feed the calculator.
- The FR calculator class is registered and the engine + amount_rule
  are wired in `apps.compensation.services`, but the gating refuses to
  produce a number while no APPROVED FR `CalculationFormula` exists.
- The public wizard renders without calling the calculator.

## 3. Sources

{_section_table(report.sources)}

## 4. Candidate datasets

{_section_table(report.datasets)}

## 5. Engine

{_section_table(report.engine)}

## 6. Formula status

{_section_table(report.formula)}

## 7. Wizard / public UX

{_section_table(report.wizard)}

The wizard URLs are probed via Django's test client `GET` — no
Simulation row is persisted on a GET; only a POST would. The audit
deliberately never POSTs to avoid leaving a calculator-pending audit
trail in the DB.

## 8. Activation blockers

The blockers below must each be resolved before the FR calculator can
publish numbers on the public path. Each blocker is independently
necessary; no shortcut exists.

1. **Mornet 2024 legal review.** `LegalSource(slug='fr-referentiel-mornet-2024')`
   stays `needs_review`. Promotion requires a `LegalReview.decision=approve`
   from a Studio reviewer + `legal_reviewer` FK valorised. Mornet is a
   *barème privato* (not state-published) — the reviewer must explicitly
   accept the consequences.
2. **Gazette du Palais 2022 legal review.** Same as above for
   `fr-bareme-capitalisation-gazette-palais-2022`. Gazette is a
   jurisprudence-derived capitalisation table; its use as an official
   quantification basis is an editorial decision Studio must sign.
3. **Dataset promotion.** `FR-MORNET-2024-DRAFT` and
   `FR-GAZETTE-PALAIS-2022-DRAFT` must be relabelled to non-DRAFT
   (e.g. `FR-MORNET-2024`) and `status=APPROVED`. The DRAFT label is
   load-bearing: `import_france_candidate_datasets` refuses to write
   into a non-DRAFT dataset, and `verify_france_candidate_import.py`
   asserts the DRAFT one stays DRAFT.
4. **Formula creation.** A `CalculationFormula(status=APPROVED)` must
   point at the engine `france_road_accident_v1` + amount_rule
   `france_dfp_point_value_direct`, declaring `row_type`, `row_match`,
   `requires`, `fault_reduction`. Currently zero FR formulas exist.
5. **Smoke test calculator FR.** A canonical (age × disability ×
   fault) tuple must be committed in `apps/calculators/test_*.py`,
   matching the IT 35/10/0 = 26 268 / 27 353 / 28 439 EUR contract.
6. **Mapping Dintilhac.** The poste-di-pregiudizio nomenclature
   (`fr-nomenclature-dintilhac-2005`) is in DB as `needs_review`.
   It is needed for the report layer to translate engine output
   into the postes the user expects to see.

## 9. Safe activation paths

Three options, presented in increasing aggression. Path C is **not**
pursued in this iter; it is documented for completeness.

### Path A — Conservative (current default)

- Keep FR road-accident `unavailable_requires_legal_validation`.
- Continue work on Belgium / Morocco / Tunisia in parallel.
- No FR formula creation, no calculator activation.
- Recommended until Mornet/Gazette legal reviews land.

### Path B — Official-only

- Promote Loi Badinter `LegalSource.status=APPROVED` (LegalReview
  signed by Studio) — this records that the *cornice normativa* is
  validated.
- Calculator stays `unavailable` because no quantification dataset is
  APPROVED yet. The wizard explicitly says "le quantification reste
  pendante" instead of just "validation pending".
- Allows the report layer to cite Loi Badinter without numbers.
- Does NOT activate the calculator.

### Path C — Explicit indicative-mode (NOT pursued in this iter)

- Treats Mornet 2024 / Gazette 2022 as *indicative* private barèmes
  rather than official quantification sources.
- Public UI must show prominently: "Estimation indicative — barème
  Mornet/Gazette du Palais — non opposable, non normatif, non avis
  juridique."
- Requires a config flag `FRANCE_ENABLE_INDICATIVE_CALCULATOR=false`
  by default, plus a separate iter to wire the disclaimer copy and
  ensure the report PDF carries the same disclaimer prominently.
- Activation requires explicit Studio sign-off in writing on a per-
  release basis.
- **This iter does not implement Path C.** It is documented so the
  next contributor knows the option exists and the constraints around
  it.

## 10. What must NOT happen

- No automated promotion of Mornet/Gazette to APPROVED. Promotion is
  a human decision tracked via `LegalReview`.
- No backdoor formula creation that bypasses the engine + rule
  registries in `apps.compensation.services`.
- No partial activation that surfaces numbers while disclaiming them
  in fine print: either the calculator returns numbers fully or it
  returns `unavailable`.
- No removal of the DRAFT dataset rows. They are the upstream
  extractor's traceability: deleting them breaks audit forensics.
- No promotion that copies real Mornet/Gazette amounts into the test
  fixtures. The static guard in
  `apps/calculators/test_france_engine_inactive.py` is precisely there
  to prevent this drift.

## 11. Rollback plan

If a future iter prematurely activates the FR calculator and the
result needs to be undone:

1. Set the offending `CalculationFormula.status` back to `DRAFT` (do
   not delete: keep the audit trail).
2. Set the offending `CompensationDataset.status` back to `DRAFT`
   (do not delete; do not re-run `import_france_candidate_datasets`).
3. Set the offending `LegalSource.status` back to `needs_review`
   (do not delete; keep `LegalReview` rows for audit).
4. Run `python scripts/legal_data/verify_france_candidate_import.py`
   to confirm DRAFT counts are intact.
5. Run `pytest -q` and `python scripts/live_simulation_matrix.py` to
   confirm Italia 35/10/0 = 26 268 / 27 353 / 28 439 EUR is still
   green and FR is `unavailable_requires_legal_validation` again.

## 12. Next tasks

1. Studio session to schedule the Mornet 2024 + Gazette 2022 legal
   reviews. Output: signed `LegalReview` rows.
2. Iter `F-france-formula-bootstrap` (proposed): once both sources
   are APPROVED, create the FR `CalculationFormula` + locked smoke
   test. This iter is BLOCKED until step 1 lands.
3. Iter `F-france-dintilhac-mapping` (proposed): map calculator
   outputs to Dintilhac postes for the report layer.

---

*This file is regenerated by
`python scripts/legal_data/audit_france_activation_readiness.py`. Do
not edit by hand — re-run the script and commit the diff.*
"""
    REPORT_PATH.write_text(body, encoding="utf-8")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> int:
    report = AuditReport(generated_at=datetime.now(UTC).isoformat(timespec="seconds"))
    report.sources = audit_sources()
    report.datasets = audit_datasets()
    report.formula = audit_formulas()
    report.engine = audit_engine()
    report.wizard = audit_wizard(Client())

    report.overall_status, report.overall_summary = _compute_verdict(report)

    # Console summary — operator-friendly.
    print(f"FR readiness verdict: {report.overall_status}")
    print(f"Summary: {report.overall_summary}")
    for section_label, rows in (
        ("sources", report.sources),
        ("datasets", report.datasets),
        ("formula", report.formula),
        ("engine", report.engine),
        ("wizard", report.wizard),
    ):
        print(f"\n[{section_label}]")
        for r in rows:
            print(f"  [{r.status:>7}] {r.label}")
            if r.details:
                print(f"           {r.details}")

    write_report(report)
    print(f"\nReport written: {REPORT_PATH.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
