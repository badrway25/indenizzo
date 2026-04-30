"""
AUDIT READ-ONLY dello stato MVP globale multi-paese.

Iter: F-global-mvp-status-consolidation · iter1
Stato: read-only. Non modifica DB. Non importa file.

Stampa:
- LegalSource per country/status;
- LegalReview per country;
- CompensationDataset per country/status/version_label/rows;
- CalculationFormula per country/status/code/amount_rule;
- Calculator registry list (calcolatori effettivamente registrati);
- Simulation count by status;
- Lead count by status;
- SimulationReport count;
- Presenza dei review package FR/BE/MA/TN.

Uso:
    .venv/Scripts/python.exe scripts/legal_data/audit_global_mvp_status.py

Lo script funziona da snapshot riproducibile per
GLOBAL_MVP_STATUS.md: rieseguendolo si può confrontare lo
stato a posteriori senza dover ispezionare la shell Django
manualmente.
"""

from __future__ import annotations

import os
import pathlib
import sys
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = pathlib.Path(__file__).resolve().parents[2]


def hr(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


def section(title: str) -> None:
    print()
    print(f"--- {title} ---")


def _bootstrap_django() -> None:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    import django

    django.setup()


def audit_legal_sources() -> None:
    from apps.jurisdictions.models import Country
    from apps.legal_sources.models import LegalSource

    section("LegalSource per country/status")
    total = LegalSource.objects.count()
    print(f"  total: {total}")
    for c in Country.objects.order_by("code"):
        qs = LegalSource.objects.filter(country=c).order_by("slug")
        if not qs.exists():
            continue
        by_status = Counter(s.status for s in qs)
        print(f"  {c.code} ({qs.count()}): {dict(by_status)}")
        for s in qs:
            print(
                f"    - {s.slug} | status={s.status} | "
                f"reliability={s.reliability} | source_type={s.source_type}"
            )


def audit_legal_reviews() -> None:
    from apps.jurisdictions.models import Country
    from apps.legal_sources.models import LegalReview

    section("LegalReview per country")
    total = LegalReview.objects.count()
    print(f"  total: {total}")
    for c in Country.objects.order_by("code"):
        qs = LegalReview.objects.filter(source__country=c)
        if not qs.exists():
            continue
        print(f"  {c.code}: {qs.count()}")
        for r in qs:
            print(
                f"    - source={r.source.slug} | decision={r.decision} | "
                f"reviewer={r.reviewer_id} | created={r.created_at:%Y-%m-%d}"
            )


def audit_datasets() -> None:
    from apps.compensation.models import CompensationDataset
    from apps.jurisdictions.models import Country

    section("CompensationDataset per country")
    total = CompensationDataset.objects.count()
    print(f"  total: {total}")
    for c in Country.objects.order_by("code"):
        qs = CompensationDataset.objects.filter(country=c).order_by("name")
        if not qs.exists():
            continue
        print(f"  {c.code}: {qs.count()}")
        for ds in qs:
            rows = ds.rows.count() if hasattr(ds, "rows") else 0
            print(
                f"    - id={ds.id} | name={ds.name!r} | "
                f"version={ds.version_label} | status={ds.status} | "
                f"case_type={ds.case_type} | rows={rows}"
            )


def audit_formulas() -> None:
    from apps.compensation.models import CalculationFormula
    from apps.jurisdictions.models import Country

    section("CalculationFormula per country")
    total = CalculationFormula.objects.count()
    print(f"  total: {total}")
    for c in Country.objects.order_by("code"):
        qs = CalculationFormula.objects.filter(dataset__country=c).order_by("code")
        if not qs.exists():
            continue
        print(f"  {c.code}: {qs.count()}")
        for f in qs:
            params = f.parameters or {}
            amount_rule = params.get("amount_rule") if isinstance(params, dict) else None
            print(
                f"    - code={f.code} | status={f.status} | "
                f"amount_rule={amount_rule} | "
                f"dataset={f.dataset.version_label}"
            )


def audit_calculators() -> None:
    from apps.calculators.registry import get_calculator, list_available_calculators

    section("Calculator registry")
    entries = list_available_calculators()
    print(f"  total registered: {len(entries)}")
    for jur, ct in entries:
        cls = get_calculator(jur, ct)
        cls_name = cls.__name__ if cls else "?"
        # Heuristica: la leaf class è REAL se override _compute_with_sources
        # sul proprio __dict__. Altrimenti eredita il placeholder
        # (ritorna SEMPRE unavailable_requires_legal_validation).
        overrides_compute = bool(cls and "_compute_with_sources" in cls.__dict__)
        marker = "REAL" if overrides_compute else "PLACEHOLDER"
        print(f"    - ({jur}, {ct}) -> {cls_name} [{marker}]")


def audit_simulations() -> None:
    from apps.cases.models import Simulation

    section("Simulation count by status")
    total = Simulation.objects.count()
    print(f"  total: {total}")
    by_status = Counter(Simulation.objects.values_list("status", flat=True))
    for status, n in sorted(by_status.items()):
        print(f"    {status}: {n}")


def audit_leads() -> None:
    from apps.crm.models import Lead

    section("Lead count by status")
    total = Lead.objects.count()
    print(f"  total: {total}")
    if hasattr(Lead, "status"):
        by_status = Counter(Lead.objects.values_list("status", flat=True))
        for status, n in sorted(by_status.items()):
            print(f"    {status}: {n}")


def audit_reports() -> None:
    from apps.reports.models import SimulationReport

    section("SimulationReport count")
    total = SimulationReport.objects.count()
    print(f"  total: {total}")


def audit_review_packages() -> None:
    section("Review packages (committable docs + checklist templates)")
    docs_dir = ROOT / "docs" / "legal_sources"
    review_dir = ROOT / "legal_data" / "sources"
    expected = [
        (
            "FR",
            "FRANCE_LEGAL_REVIEW_PACKAGE.md",
            "france",
            "france_legal_review_checklist_template.csv",
        ),
        (
            "BE",
            "BELGIUM_LEGAL_REVIEW_PACKAGE.md",
            "belgium",
            "belgium_legal_review_checklist_template.csv",
        ),
        (
            "MA",
            "MOROCCO_LEGAL_REVIEW_PACKAGE.md",
            "morocco",
            "morocco_legal_review_checklist_template.csv",
        ),
        (
            "TN",
            "TUNISIA_LEGAL_REVIEW_PACKAGE.md",
            "tunisia",
            "tunisia_legal_review_checklist_template.csv",
        ),
    ]
    for code, doc_name, country_dir, template_name in expected:
        doc = docs_dir / doc_name
        template = review_dir / country_dir / "review" / template_name
        doc_status = "PRESENT" if doc.exists() else "MISSING"
        template_status = "PRESENT" if template.exists() else "MISSING"
        size_doc = doc.stat().st_size if doc.exists() else 0
        size_tpl = template.stat().st_size if template.exists() else 0
        print(
            f"  {code}: doc={doc_status} ({size_doc} B) | "
            f"template={template_status} ({size_tpl} B)"
        )


def audit_extraction_artifacts() -> None:
    section("Extraction artifacts on-disk (gitignored)")
    artifacts = [
        ("FR", "Gazette 2022 CSV (3 file)", "legal_data/sources/france/gazette_2022/"),
        ("FR", "Mornet 2024 CSV (4 file)", "legal_data/sources/france/mornet_2024/"),
        ("BE", "TI 2020 CSV (4 file)", "legal_data/sources/belgium/tableau_indicatif_2020/"),
        (
            "BE",
            "TI 2024 OCR spike outputs",
            "legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/",
        ),
        ("MA", "PDF downloaded (3 file + manifest)", "legal_data/sources/morocco/downloaded/"),
        ("TN", "HTML downloaded (2 file + manifest)", "legal_data/sources/tunisia/downloaded/"),
    ]
    for code, label, path in artifacts:
        p = ROOT / path
        if p.exists() and p.is_dir():
            n_files = sum(1 for _ in p.iterdir() if _.is_file())
            print(f"  {code}: {label} -> {path} ({n_files} files)")
        else:
            print(f"  {code}: {label} -> {path} (MISSING)")


def main() -> int:
    _bootstrap_django()

    hr("AUDIT GLOBAL MVP STATUS — Studio Legale Badrane LegalTech")
    print(f"ROOT: {ROOT}")
    print("Mode: read-only (no DB writes, no file mutations).")

    audit_legal_sources()
    audit_legal_reviews()
    audit_datasets()
    audit_formulas()
    audit_calculators()
    audit_simulations()
    audit_leads()
    audit_reports()
    audit_review_packages()
    audit_extraction_artifacts()

    hr("Audit complete — see GLOBAL_MVP_STATUS.md for narrative summary")
    return 0


if __name__ == "__main__":
    sys.exit(main())
