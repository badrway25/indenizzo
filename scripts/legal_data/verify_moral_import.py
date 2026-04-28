"""
Verifica POST-IMPORT del dataset moral DPR-12-2025-MORAL.

Read-only: nessuna modifica al DB. Esegui da shell Django:

    python manage.py shell -c "exec(open('scripts/legal_data/verify_moral_import.py', encoding='utf-8').read())"
"""

from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    CompensationTableRow,
    DatasetStatus,
    ExtractionLog,
)
from apps.legal_sources.enums import SourceStatus


def _line(label, ok, detail=""):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {label}{(' — ' + detail) if detail else ''}")


print("=" * 70)
print("POST-IMPORT VERIFICATION — TUN 2025 morale dataset")
print("=" * 70)

# 1. moral dataset esiste
moral = CompensationDataset.objects.filter(version_label="DPR-12-2025-MORAL").first()
print("\n1. CompensationDataset version_label='DPR-12-2025-MORAL'")
_line("esiste", moral is not None, f"pk={moral.pk if moral else None}")

# 2. status DRAFT
print("\n2. moral.status = DRAFT")
_line("status DRAFT", moral.status == DatasetStatus.DRAFT, f"status={moral.status}")

# 3. stessa LegalSource approved
src = moral.source
print("\n3. moral.source = LegalSource DPR 12/2025 approved")
_line(
    "slug = it-dpr-12-2025-tun-danno-biologico",
    src.slug == "it-dpr-12-2025-tun-danno-biologico",
    f"slug={src.slug!r}",
)
_line("source.status = APPROVED", src.status == SourceStatus.APPROVED, f"status={src.status}")

# 4. rows count per row_type
print("\n4. moral row counts per row_type")
expected = {
    "tun_biological_moral_min_total_amount": 9191,
    "tun_biological_moral_mid_total_amount": 9191,
    "tun_biological_moral_max_total_amount": 9191,
}
total = 0
for rt, exp in expected.items():
    got = CompensationTableRow.objects.filter(dataset=moral, row_type=rt).count()
    total += got
    _line(f"{rt} == {exp}", got == exp, f"count={got}")
_line("totale moral = 27.573", total == 27573, f"total={total}")

# 5. base DPR-12-2025 ancora APPROVED
print("\n5. dataset base DPR-12-2025 ancora APPROVED")
base = CompensationDataset.objects.get(version_label="DPR-12-2025")
_line("base.status = APPROVED", base.status == DatasetStatus.APPROVED, f"status={base.status}")

# 6. base rows = 9191 (Tabella 1)
print("\n6. dataset base ha ancora le 9.191 righe Tabella 1")
base_count = base.rows.count()
_line("base.rows.count() == 9191", base_count == 9191, f"count={base_count}")
base_biological = base.rows.filter(row_type="tun_biological_total_amount").count()
_line(
    "base rows tun_biological_total_amount == 9191",
    base_biological == 9191,
    f"count={base_biological}",
)

# 7. CalculationFormula pubblica ancora APPROVED + amount_rule = row_amount_direct
print("\n7. CalculationFormula pubblica intatta")
fm = CalculationFormula.objects.get(code="italy_art_138_tun_2025_base")
_line("formula.status = APPROVED", fm.status == DatasetStatus.APPROVED, f"status={fm.status}")
amount_rule = (fm.parameters or {}).get("amount_rule")
_line(
    "formula.parameters['amount_rule'] = row_amount_direct",
    amount_rule == "row_amount_direct",
    f"amount_rule={amount_rule!r}",
)
_line(
    "formula.dataset = base DPR-12-2025 (NON quello moral)",
    fm.dataset_id == base.pk,
    f"dataset_id={fm.dataset_id} base.pk={base.pk} moral.pk={moral.pk}",
)

# 8. Smoke 35/10/0 — ancora 21709, min=mid=max
print("\n8. Smoke calculator 35/10/0")
calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
r = calc.compute({"victim_age": 35, "permanent_disability_percentage": 10, "fault_percentage": 0})
_line("status = calculated", r.status == "calculated", f"status={r.status}")
_line(
    "estimated_mid = 21709",
    r.estimated_mid is not None and int(r.estimated_mid) == 21709,
    f"mid={r.estimated_mid}",
)
_line(
    "min == mid",
    r.estimated_min == r.estimated_mid,
    f"min={r.estimated_min} mid={r.estimated_mid}",
)
_line(
    "mid == max",
    r.estimated_mid == r.estimated_max,
    f"mid={r.estimated_mid} max={r.estimated_max}",
)

# 9. ExtractionLog ultimo
print("\n9. ExtractionLog del dataset moral (struttura)")
logs = ExtractionLog.objects.filter(dataset=moral).order_by("-created_at", "-pk")
print(f"  totale log per moral: {logs.count()}")
for log in logs[:5]:
    md = log.metadata or {}
    print(
        f"    pk={log.pk} method={log.method} result={log.result} "
        f"rows_imported={log.rows_imported} rows_skipped={log.rows_skipped} "
        f"file={log.file_path.rsplit('/', 1)[-1]} "
        f"additive={md.get('additive')} inserted={md.get('rows_inserted')} updated={md.get('rows_updated')}"
    )
sum_imported = sum(log.rows_imported for log in logs)
print(
    f"\n  somma rows_imported sui log moral = {sum_imported} (atteso 27573 per primo run; "
    f"se >27573 = re-run idempotente con upsert già contato)"
)
all_success = all(log.result == ExtractionLog.Result.SUCCESS for log in logs)
_line("tutti i log = SUCCESS", all_success)

# Sanity: il dataset moral non ha row_type spurii.
print("\n10. Sanity: il dataset moral non contiene row_type non-moral")
spurious = (
    CompensationTableRow.objects.filter(dataset=moral)
    .exclude(row_type__in=list(expected.keys()))
    .count()
)
_line("0 row_type spurii nel dataset moral", spurious == 0, f"spurious={spurious}")

# Sanity: il dataset base non contiene row_type morali.
spurious_base = CompensationTableRow.objects.filter(
    dataset=base, row_type__startswith="tun_biological_moral_"
).count()
_line("0 row_type morali nel dataset base", spurious_base == 0, f"moral_in_base={spurious_base}")

# Sample value sanity (non-real spot only, oracle property)
print("\n11. Spot sanity moral A+B > biological")
biological_0_10 = base.rows.get(
    row_type="tun_biological_total_amount", age_min=0, disability_min=10
).point_value
moral_min_0_10 = moral.rows.get(
    row_type="tun_biological_moral_min_total_amount", age_min=0, disability_min=10
).point_value
moral_mid_0_10 = moral.rows.get(
    row_type="tun_biological_moral_mid_total_amount", age_min=0, disability_min=10
).point_value
moral_max_0_10 = moral.rows.get(
    row_type="tun_biological_moral_max_total_amount", age_min=0, disability_min=10
).point_value
print(
    f"  (age=0, inv=10) base={biological_0_10}  min={moral_min_0_10}  "
    f"mid={moral_mid_0_10}  max={moral_max_0_10}"
)
_line(
    "monotonia min < mid < max",
    moral_min_0_10 < moral_mid_0_10 < moral_max_0_10,
)
_line(
    "tutti morali > biologico (Tabella 1)",
    biological_0_10 < moral_min_0_10
    and biological_0_10 < moral_mid_0_10
    and biological_0_10 < moral_max_0_10,
)

print("\n" + "=" * 70)
print("FINE VERIFICA — nessuna modifica al DB.")
print("=" * 70)
