"""
Read-only audit of non-IT country readiness (FR / BE / MA / TN).

Iter: F-p0-mvp-1-non-it-readiness.

Prints a per-country snapshot of the gating chain:

  LegalSource by status
    → LegalReview audit trail (chain integrity)
      → CompensationDataset by status
        → CalculationFormula by status
          → Calculator class registered
            → Wizard URL HTTP probe (GET only, never POST)

Verdict per country:
- ``SCAFFOLD-ONLY`` — no APPROVED rows in the chain. Today's state.
- ``READY-FOR-REVIEW`` — all NEEDS_REVIEW + non-zero candidate
  datasets exist. France is here.
- ``APPROVED-INCONSISTENT`` — has APPROVED LegalSource(s) but a
  matching APPROVE LegalReview row is missing OR the chain is
  partial (dataset/formula not promoted yet). This is the state the
  ``jurisdictions.E001`` system check fails in production.
- ``APPROVED-CONSISTENT`` — every link in the chain is APPROVED with
  audit trail. The calculator can produce numbers on the public
  path.

Usage:

    .venv/Scripts/python.exe scripts/legal_data/audit_non_it_readiness.py

The script makes **no DB writes** and never calls the calculator.
It is safe to run on any environment (dev / staging / prod) at any
time.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]

NON_IT_COUNTRIES = ("FR", "BE", "MA", "TN")


def _bootstrap_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import django

    django.setup()


def hr(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def section(title: str) -> None:
    print()
    print(f"--- {title} ---")


def _audit_country(code: str) -> dict:
    """Inspect a single country and return its verdict + facts."""
    from apps.calculators.registry import list_available_calculators
    from apps.compensation.models import CalculationFormula, CompensationDataset
    from apps.jurisdictions.models import Country
    from apps.legal_sources.enums import SourceStatus
    from apps.legal_sources.models import LegalReview, LegalSource

    facts: dict = {"code": code}

    try:
        country = Country.objects.get(code=code)
    except Country.DoesNotExist:
        return {"code": code, "verdict": "MISSING-COUNTRY"}

    facts["country_id"] = country.id
    facts["is_active"] = country.is_active

    sources = LegalSource.objects.filter(country=country).order_by("slug")
    facts["source_count"] = sources.count()
    facts["source_status"] = dict(Counter(s.status for s in sources))

    approved_sources = sources.filter(status=SourceStatus.APPROVED)
    facts["approved_source_count"] = approved_sources.count()

    audited = LegalReview.objects.filter(
        source__in=approved_sources, decision=LegalReview.Decision.APPROVE
    ).exclude(reviewer__isnull=True)
    audited_ids = set(audited.values_list("source_id", flat=True))
    facts["audited_source_count"] = len(audited_ids)
    facts["missing_audit"] = sorted(
        s.slug for s in approved_sources if s.id not in audited_ids
    )

    datasets = CompensationDataset.objects.filter(country=country)
    facts["dataset_status"] = dict(Counter(d.status for d in datasets))
    facts["approved_dataset_count"] = datasets.filter(status="approved").count()

    formulas = CalculationFormula.objects.filter(dataset__country=country)
    facts["formula_status"] = dict(Counter(f.status for f in formulas))
    facts["approved_formula_count"] = formulas.filter(status="approved").count()

    juris_code = f"{code}-NATIONAL"
    registered = [
        case_type
        for jur, case_type in list_available_calculators()
        if jur == juris_code
    ]
    facts["registered_calculators"] = registered

    facts["verdict"] = _verdict(facts)
    return facts


def _verdict(facts: dict) -> str:
    if facts["approved_source_count"] == 0:
        if any(
            facts["source_status"].get(s)
            for s in ("needs_review", "reviewed", "extracted")
        ):
            return "READY-FOR-REVIEW"
        return "SCAFFOLD-ONLY"

    if facts["missing_audit"]:
        return "APPROVED-INCONSISTENT"

    if (
        facts["approved_dataset_count"] == 0
        or facts["approved_formula_count"] == 0
    ):
        return "APPROVED-PARTIAL"

    return "APPROVED-CONSISTENT"


def _probe_wizard(client, url: str) -> str:
    try:
        resp = client.get(url, HTTP_HOST="127.0.0.1")
    except Exception as exc:
        return f"ERROR ({exc.__class__.__name__})"
    return f"http_status={resp.status_code}"


def main() -> int:
    _bootstrap_django()

    from django.test import Client

    hr("Non-IT country readiness audit (FR / BE / MA / TN)")
    print(
        "Read-only snapshot. No DB writes, no POSTs, no calculator calls."
    )
    print("Verdicts:")
    print("  SCAFFOLD-ONLY        — no sources beyond DRAFT")
    print("  READY-FOR-REVIEW     — NEEDS_REVIEW sources + candidate datasets")
    print("  APPROVED-INCONSISTENT — APPROVED source(s) without audit trail (E001)")
    print("  APPROVED-PARTIAL     — APPROVED source(s) + audit, but chain incomplete")
    print("  APPROVED-CONSISTENT  — chain complete, calculator can publish numbers")

    client = Client()
    findings = []
    for code in NON_IT_COUNTRIES:
        facts = _audit_country(code)
        if facts["verdict"] == "MISSING-COUNTRY":
            section(f"{code} — MISSING-COUNTRY")
            print("  Country row does not exist in DB.")
            findings.append(facts)
            continue

        section(f"{code} — verdict={facts['verdict']}")
        print(f"  is_active={facts['is_active']}")
        print(f"  source_count={facts['source_count']}")
        print(f"  source_status={facts['source_status']}")
        print(f"  approved_source_count={facts['approved_source_count']}")
        print(f"  audited_source_count={facts['audited_source_count']}")
        if facts["missing_audit"]:
            print(f"  missing_audit_for={facts['missing_audit']}")
        print(f"  dataset_status={facts['dataset_status']}")
        print(f"  approved_dataset_count={facts['approved_dataset_count']}")
        print(f"  formula_status={facts['formula_status']}")
        print(f"  approved_formula_count={facts['approved_formula_count']}")
        print(f"  registered_calculators={facts['registered_calculators']}")

        country_path = {
            "FR": "/countries/france/",
            "BE": "/countries/belgium/",
            "MA": "/countries/morocco/",
            "TN": "/countries/tunisia/",
        }[code]
        wizard_path = {
            "FR": "/wizard/fr/road-accident/",
            "BE": "/wizard/be/road-accident/",
            "MA": "/wizard/ma/inheritance/",
            "TN": "/wizard/tn/inheritance/",
        }[code]
        print(f"  GET {country_path}  → {_probe_wizard(client, country_path)}")
        print(f"  GET {wizard_path}   → {_probe_wizard(client, wizard_path)}")

        findings.append(facts)

    hr("Summary")
    verdicts = Counter(f["verdict"] for f in findings)
    for verdict, count in sorted(verdicts.items()):
        print(f"  {verdict:<24} {count}")

    inconsistent = [f for f in findings if f["verdict"] == "APPROVED-INCONSISTENT"]
    if inconsistent:
        print()
        print(
            "WARNING: at least one country has APPROVED LegalSource(s) "
            "without audit trail. In production, system check "
            "`jurisdictions.E001` will block deploy."
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
