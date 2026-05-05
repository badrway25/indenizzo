# Belgium candidate dataset import — Tableau Indicatif 2020 (DRAFT)

Iter: `F-belgium-import-candidate-datasets-draft-seed`.

## What is imported

The management command
`apps.compensation.management.commands.import_belgium_candidate_datasets`
reads the four CSVs already extracted by
`scripts/legal_data/extract_belgium_ti_2020.py` and writes them into a
single non-public, non-calculable dataset:

- `BE-TABLEAU-INDICATIF-2020-DRAFT` — `status = DRAFT`,
  `is_usable_for_calculations = False`.

Per row_type counts (after a clean import):

| row_type | count |
| --- | ---: |
| `be_souffrances_endurees_per_age_severity_amount` | 63 |
| `be_indemnite_forfaitaire_per_age_annual_amount` | 71 |
| `be_prejudice_deces_affection_per_relation_amount` | 13 |
| `be_vehicule_remplacement_per_type_per_day_amount` | 19 |
| **total** | **166** |

## Why BE 2020 is "historical / candidate"

The Belgian Tableau Indicatif is republished every few years. The 2020
edition is the most recent one we have a clean, automated extraction
for. The 2024 edition exists but currently sits behind a low-quality
OCR pass (see `BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`) and is not yet
machine-extractable end-to-end without manual transcription.

Importing the 2020 edition as a DRAFT dataset gives the Studio a real
candidate corpus to legal-review against — values, structure,
relations, scales — without exposing 2020 numbers as if they were
authoritative. None of these rows is consumable by a public
calculator.

## Why DRAFT

`CompensationDataset.is_usable_for_calculations` requires both the
parent `LegalSource` to be `APPROVED` **and** the dataset itself to be
`APPROVED`. While the BE LegalSource stays `needs_review`, the DRAFT
dataset cannot promote: the engine simply does not see it.

The BE calculator therefore stays
`unavailable_requires_legal_validation`, and `/wizard/be/road-accident/`
keeps surfacing the centralised `Preliminary legal assessment` panel
(pass-7) — there is no public-facing change.

## What is **not** public

- The dataset is `DRAFT` only.
- The 166 rows are visible in admin (and via `verify_belgium_candidate_import.py`)
  but not in any public template, JSON endpoint, or simulation result.
- The `LegalSource(be-tableau-indicatif-2020)` row stays at
  `status = needs_review`.
- No `CalculationFormula` is created for BE.
- No `LegalReview` is auto-recorded — review is a manual Studio step.

## How to verify

After the import, run:

```powershell
.\.venv\Scripts\python.exe scripts/legal_data/verify_belgium_candidate_import.py
```

The script asserts:

- `BE-TABLEAU-INDICATIF-2020-DRAFT` exists with `status = DRAFT`.
- Per row_type counts match (63 / 71 / 13 / 19 / **166** total).
- `is_usable_for_calculations` is `False`.
- `LegalSource(be-tableau-indicatif-2020).status == needs_review`.
- `CalculationFormula(country=BE).count() == 0`.
- `run_simulation(BE-NATIONAL, road_accident_bodily_injury)` resolves to
  `unavailable_requires_legal_validation`.
- Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR is unchanged.

## What it takes to activate Belgium

The import is the first ingredient. To flip BE from "preliminary
legal assessment" to "indicative calculation available", the Studio
must:

1. Legal-review each Tableau Indicatif scale (souffrances endurées,
   indemnité forfaitaire, prejudice de décès / affection, véhicule de
   remplacement) and any 2024 update where applicable.
2. Promote `LegalSource(be-tableau-indicatif-2020).status` →
   `APPROVED` (via admin, with an explicit `LegalReview`).
3. Promote `CompensationDataset(BE-TABLEAU-INDICATIF-2020-DRAFT).status`
   → `APPROVED`.
4. Land a `CalculationFormula(belgium_*_v1, dataset=BE-TABLEAU-INDICATIF-2020-DRAFT)`
   that the engine can read.
5. Register the BE engine entry in `apps.calculators.engines` so
   `run_simulation(BE-NATIONAL, road_accident_bodily_injury)` returns
   `calculated`.
6. Flip the public status: change
   `("BE", "road_accident", _LEGAL_ASSESSMENT)` →
   `_AVAILABLE` in `apps/core/public_status.py` (single-line edit
   thanks to pass-7).

Steps 1–4 are not in scope for this iter. The current iter only seeds
the candidate data and proves it can never accidentally reach the
public calculator.

## Role of BE 2024 OCR / scanned

The 2024 edition exists in the repo as scanned/OCR material under
`legal_data/sources/belgium/scanned/` (see
`BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`). It is NOT imported by this
command and NOT part of `BE-TABLEAU-INDICATIF-2020-DRAFT`.

When a clean 2024 extraction lands, the Studio can:

- Either add a sibling DRAFT dataset
  `BE-TABLEAU-INDICATIF-2024-DRAFT`, anchored to a new
  `LegalSource(be-tableau-indicatif-2024)`, and review both editions
  in parallel before activating.
- Or replace the 2020 material with 2024 once 2020 has been
  legal-reviewed (then 2024 inherits the review process).

Either path goes through the same import-then-legal-review-then-activate
sequence.

## Manual rollback

The command does **not** delete rows. To roll back a candidate import
the operator must do so by hand:

```python
# Django shell, manual operation only.
from apps.compensation.models import CompensationDataset, CompensationTableRow

ds = CompensationDataset.objects.get(version_label="BE-TABLEAU-INDICATIF-2020-DRAFT")
assert ds.status == "draft"  # safety: never delete a non-DRAFT dataset.
CompensationTableRow.objects.filter(dataset=ds).delete()
ds.delete()
```

A re-run of `import_belgium_candidate_datasets` will recreate the
dataset and re-import the rows from the CSVs.

## Idempotence

The command uses `update_or_create` on the natural key
`(dataset, row_type, extra__nat_key)` — a re-run with the same CSV
produces the same row count, just with a fresh `updated_at` timestamp.
A re-run with a CSV that bumps amounts updates the existing row in
place rather than inserting a duplicate.

The command refuses to write into a dataset whose `status != DRAFT`,
which guards against silent regressions if the Studio promotes the
dataset by hand and someone re-runs the import afterwards.
