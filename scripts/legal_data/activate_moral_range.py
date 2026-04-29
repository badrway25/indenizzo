"""
Activation script F-italy-moral-legal-review-and-activation.

Tutto in UNA transazione atomica. Se uno step fallisce, l'intera
operazione viene rollbacked e il calculator pubblico continua a usare
`row_amount_direct` sul dataset base.

Sequenza:
1. LegalReview decision=approve sulla LegalSource DPR 12/2025 con
   commento di estensione alle Tabelle 2.A/2.B/2.C.
2. CompensationDataset(version_label="DPR-12-2025-MORAL"): full_clean
   + status DRAFT -> APPROVED + notes esteso.
3. CalculationFormula(code="italy_art_138_tun_2025_base"):
   parameters aggiornati con schema range completo. Status APPROVED
   resta tale.

Esegui da Django shell:
    python manage.py shell -c "exec(open('scripts/legal_data/activate_moral_range.py', encoding='utf-8').read())"
"""

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.compensation.models import (
    CalculationFormula,
    CompensationDataset,
    DatasetStatus,
)
from apps.legal_sources.enums import SourceStatus
from apps.legal_sources.models import LegalReview, LegalSource

PDF_SHA256 = "74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92"
SOURCE_SLUG = "it-dpr-12-2025-tun-danno-biologico"
BASE_VERSION = "DPR-12-2025"
MORAL_VERSION = "DPR-12-2025-MORAL"
FORMULA_CODE = "italy_art_138_tun_2025_base"

print("=" * 70)
print("ACTIVATE moral range — F-italy-moral-legal-review-and-activation")
print("=" * 70)

# Staff reviewer
reviewer = User.objects.filter(is_staff=True, is_superuser=True).first()
if reviewer is None:
    raise RuntimeError("Nessun superuser disponibile come reviewer.")
print(f"Reviewer: {reviewer.username} (pk={reviewer.pk})")

src = LegalSource.objects.get(slug=SOURCE_SLUG)
moral = CompensationDataset.objects.get(version_label=MORAL_VERSION)
base = CompensationDataset.objects.get(version_label=BASE_VERSION)
fm = CalculationFormula.objects.get(code=FORMULA_CODE)

print(f"\nPRE: source.status={src.status}")
print(f"PRE: base.status={base.status} pk={base.pk}")
print(f"PRE: moral.status={moral.status} pk={moral.pk}")
print(f"PRE: formula.status={fm.status}")
print(f"PRE: formula.amount_rule={(fm.parameters or {}).get('amount_rule')!r}")
print(f"PRE: moral.rows.count={moral.rows.count()}  base.rows.count={base.rows.count()}")

if src.status != SourceStatus.APPROVED:
    raise RuntimeError(f"Source non approved: {src.status}")
if base.status != DatasetStatus.APPROVED:
    raise RuntimeError(f"Base non approved: {base.status}")
if moral.status != DatasetStatus.DRAFT:
    raise RuntimeError(f"Moral non draft: {moral.status}")
if base.rows.count() != 9191:
    raise RuntimeError(f"Base rows != 9191: {base.rows.count()}")
if moral.rows.count() != 27573:
    raise RuntimeError(f"Moral rows != 27573: {moral.rows.count()}")
print("\n[PRE-CHECK PASS]")

with transaction.atomic():
    # --- 1. LegalReview ---------------------------------------------------
    review = LegalReview.objects.create(
        source=src,
        reviewer=reviewer,
        decision=LegalReview.Decision.APPROVE,
        previous_status=src.status,
        new_status=src.status,  # nessun cambio di status: estendiamo lo scope
        comment=(
            "Formal Studio approval extended to D.P.R. 12/2025 Tabelle 2.A, "
            "2.B, 2.C for moral damage range. Based on iter2 extraction QA: "
            "27.573 rows, 0 null, 0 duplicates, 0 monotonicity violations. "
            "PDF sha256=" + PDF_SHA256 + ". "
            "Activation: dataset DPR-12-2025-MORAL promoted to APPROVED, "
            "formula italy_art_138_tun_2025_base parameters switched to "
            "row_amount_range_direct."
        ),
    )
    print(f"\n[1] LegalReview created pk={review.pk} decision=approve")

    # --- 2. Promuovi dataset moral ---------------------------------------
    moral.status = DatasetStatus.APPROVED
    moral.notes = (
        moral.notes
        + (("\n\n" if moral.notes else "") if moral.notes else "")
        + (
            f"[{timezone.now().date().isoformat()}] Studio Legale Badrane formal approval. "
            f"Contains TUN 2025 Tabelle 2.A/2.B/2.C (danno morale) — 3 row_type, "
            f"9.191 cells each, total 27.573. Tied to LegalSource '{SOURCE_SLUG}' "
            f"(PDF sha256={PDF_SHA256}). Reference: LegalReview pk={review.pk}."
        )
    )
    moral.full_clean()
    moral.save(update_fields=["status", "notes", "updated_at"])
    moral.refresh_from_db()
    print(f"[2] moral.status={moral.status}  notes_len={len(moral.notes)}")

    # --- 3. Aggiorna formula.parameters ----------------------------------
    new_params = {
        "engine": "italy_tun_point_value_v1",
        "requires": ["victim_age", "permanent_disability_percentage"],
        "row_match": ["victim_age", "permanent_disability_percentage"],
        "amount_rule": "row_amount_range_direct",
        "fault_reduction": True,
        "range_dataset_version_label": MORAL_VERSION,
        "min_row_type": "tun_biological_moral_min_total_amount",
        "mid_row_type": "tun_biological_moral_mid_total_amount",
        "max_row_type": "tun_biological_moral_max_total_amount",
    }
    fm.parameters = new_params
    fm.full_clean()
    fm.save(update_fields=["parameters", "updated_at"])
    fm.refresh_from_db()
    print(f"[3] formula.amount_rule={(fm.parameters or {}).get('amount_rule')!r}")

print("\n[COMMIT] activation transaction succeeded.")

# --- POST verification (read-only) -----------------------------------------
print("\n" + "=" * 70)
print("POST-ACTIVATION VERIFICATION")
print("=" * 70)
print(f"  source.status = {src.status}")
print(f"  base.status = {base.status} rows={base.rows.count()}")
print(f"  moral.status = {moral.status} rows={moral.rows.count()}")
print(f"  formula.status = {fm.status}")
print(f"  formula.amount_rule = {(fm.parameters or {}).get('amount_rule')!r}")
print(
    f"  formula.range_dataset_version_label = {(fm.parameters or {}).get('range_dataset_version_label')!r}"
)
print(f"  LegalReview created pk={review.pk} on {review.created_at:%Y-%m-%d %H:%M}")

print("\n" + "=" * 70)
print("ACTIVATION COMPLETE.")
print("=" * 70)
