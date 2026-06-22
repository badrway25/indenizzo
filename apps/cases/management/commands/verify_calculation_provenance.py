"""verify_calculation_provenance — read-only reproducibility check (H1-8.1).

Re-derives the provenance of calculated simulations from the CURRENT DB and
reports whether each is reproducible / drifted / incomplete / legacy /
not-calculated. Strictly read-only: no DB writes, no network, no PII (never
prints input_data / victim / health data).

CLI::

    python manage.py verify_calculation_provenance --simulation <uuid>
    python manage.py verify_calculation_provenance --all-calculated --limit 100
    python manage.py verify_calculation_provenance --all-calculated --format json
    python manage.py verify_calculation_provenance --canary
    python manage.py verify_calculation_provenance --all-calculated --fail-on-drift

Exit code is non-zero when --fail-on-drift is set and a drift (or a failing
canary) is found.
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.cases.models import Simulation
from apps.cases.provenance_verifier import (
    DRIFTED,
    LEGACY_NO_PROVENANCE,
    verify_simulation,
)

# Canonical IT canary: inputs 35/10/0 must yield these amounts. Synthetic, not
# PII. Used only by --canary (controlled, read-only recompute).
_CANARY_INPUT = {"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0}
_CANARY_EXPECTED = (Decimal("26268"), Decimal("27353"), Decimal("28439"))
_CANARY_JURISDICTION = "IT-NATIONAL"


class Command(BaseCommand):
    help = (
        "Read-only verification of calculation provenance reproducibility for "
        "calculated simulations. No DB writes, no PII."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--simulation", default=None, help="Verify one simulation by public_id."
        )
        parser.add_argument(
            "--all-calculated", action="store_true", help="Verify all calculated simulations."
        )
        parser.add_argument("--limit", type=int, default=200, help="Max simulations (default 200).")
        parser.add_argument("--format", choices=("text", "json", "markdown"), default="text")
        parser.add_argument("--output", default=None, help="Write to file instead of stdout.")
        parser.add_argument(
            "--fail-on-drift",
            action="store_true",
            help="Exit non-zero if any drift / canary failure.",
        )
        parser.add_argument(
            "--include-legacy",
            action="store_true",
            help="Include legacy (no-provenance) simulations.",
        )
        parser.add_argument(
            "--canary", action="store_true", help="Also run the IT canary reproducibility check."
        )

    def handle(self, *args, **options):
        report: dict = {"canary": None, "results": [], "summary": {}}

        if options["canary"]:
            report["canary"] = _run_canary()

        sims = self._select(options)
        items = []
        for sim in sims:
            res = verify_simulation(sim)
            if res["status"] == LEGACY_NO_PROVENANCE and not options["include_legacy"]:
                continue
            items.append({"public_id": str(sim.public_id), **res})
        report["results"] = items
        report["summary"] = _summarise(items, report["canary"])

        fmt = options["format"]
        rendered = (
            json.dumps(report, indent=2, ensure_ascii=False, default=str)
            if fmt == "json"
            else _render_markdown(report) if fmt == "markdown" else _render_text(report)
        )

        if options["output"]:
            path = Path(options["output"])
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(rendered + "\n", encoding="utf-8")
            self.stdout.write(f"[ok] wrote {fmt} report to {options['output']}")
        else:
            self.stdout.write(rendered)

        drift_found = any(r["status"] == DRIFTED for r in items)
        canary_failed = report["canary"] is not None and not report["canary"]["ok"]
        if options["fail_on_drift"] and (drift_found or canary_failed):
            raise SystemExit(1)

    def _select(self, options):
        if options["simulation"]:
            sim = Simulation.objects.filter(public_id=options["simulation"]).first()
            if sim is None:
                raise CommandError(f"No simulation with public_id={options['simulation']!r}.")
            return [sim]
        if options["all_calculated"]:
            return list(
                Simulation.objects.filter(status="calculated").order_by("-created_at")[
                    : options["limit"]
                ]
            )
        # --canary alone is a valid invocation (no simulations to scan).
        if options["canary"]:
            return []
        raise CommandError("Pass --simulation <uuid>, --all-calculated, or --canary.")


def _run_canary() -> dict:
    """Controlled, read-only IT recompute (compute() never persists)."""
    from apps.calculators.enums import CaseType
    from apps.calculators.registry import get_calculator

    calc_cls = get_calculator(_CANARY_JURISDICTION, CaseType.ROAD_ACCIDENT_BODILY_INJURY.value)
    if calc_cls is None:
        return {"ok": False, "detail": "IT calculator not registered", "amounts": None}
    result = calc_cls(simulation_id="provenance-canary", language="it").compute(_CANARY_INPUT)
    amounts = (result.estimated_min, result.estimated_mid, result.estimated_max)
    ok = result.status == "calculated" and tuple(amounts) == _CANARY_EXPECTED
    return {
        "ok": ok,
        "detail": "IT 35/10/0 reproducible" if ok else "IT canary did NOT reproduce",
        "status": result.status,
        "amounts": [str(a) if a is not None else None for a in amounts],
        "expected": [str(a) for a in _CANARY_EXPECTED],
    }


def _summarise(items, canary) -> dict:
    counts: dict[str, int] = {}
    for r in items:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {
        "total": len(items),
        "by_status": counts,
        "canary_ok": (canary["ok"] if canary else None),
    }


def _render_text(report: dict) -> str:
    lines = ["CALCULATION PROVENANCE VERIFICATION (read-only)"]
    if report["canary"] is not None:
        c = report["canary"]
        lines.append(f"  canary: {'OK' if c['ok'] else 'FAIL'} — {c['detail']}")
    s = report["summary"]
    lines.append(f"  simulations={s['total']}  by_status={s['by_status']}")
    lines.append("")
    for r in report["results"]:
        failed = [c["name"] for c in r["checks"] if not c["ok"]]
        lines.append(f"  {r['public_id']}  [{r['status'].upper()}]  {r['summary']}")
        if failed:
            lines.append(f"      failed checks: {', '.join(failed)}")
        for w in r["warnings"]:
            lines.append(f"      warning: {w}")
    return "\n".join(lines)


def _render_markdown(report: dict) -> str:
    lines = ["# Calculation provenance verification (read-only)", ""]
    if report["canary"] is not None:
        c = report["canary"]
        lines.append(f"**Canary:** {'✅ reproducible' if c['ok'] else '❌ ' + c['detail']}")
        lines.append("")
    s = report["summary"]
    lines.append(f"**Simulations:** {s['total']} · by status: `{s['by_status']}`")
    lines.append("")
    lines.append("| Simulation | Status | Summary |")
    lines.append("|---|:---:|---|")
    for r in report["results"]:
        lines.append(f"| `{r['public_id']}` | {r['status']} | {r['summary']} |")
    return "\n".join(lines)
