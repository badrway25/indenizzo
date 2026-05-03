# FR — Candidate dataset import (DRAFT)

**Iter:** `F-france-import-datasets-draft-seed`.

This document describes the management command that lands the existing
French extracted CSVs into Postgres/SQLite as **DRAFT** `CompensationDataset`s,
without activating the FR calculator and without promoting any
`LegalSource` or `CalculationFormula` to `APPROVED`.

The whole pipeline is intentionally segregated: the data exists in DB
for inspection, querying, and Studio review, but no public surface
reads it.

---

## Inputs

The command consumes 5 CSVs already produced by the upstream extractor
scripts:

| Argument | CSV file | Rows | Source script |
|----------|----------|-----:|---------------|
| `--mornet-dfp` | `legal_data/sources/france/mornet_2024/fr-mornet-2024-dfp-per-age-disability.csv` | 180 | `scripts/legal_data/extract_france_mornet_2024.py` |
| `--mornet-affection` | `legal_data/sources/france/mornet_2024/fr-mornet-2024-prejudice-affection-per-relation.csv` | 11 | `scripts/legal_data/extract_france_mornet_2024.py` |
| `--gazette-viagere` | `legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-viagere.csv` | 416 | `scripts/legal_data/extract_france_gazette_2022.py` |
| `--gazette-temporaire` | `legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-temporaire.csv` | 3 752 | `scripts/legal_data/extract_france_gazette_2022.py` |
| `--gazette-anticipated` | `legal_data/sources/france/gazette_2022/fr-gazette-2022-anticipated-payment-years.csv` | 20 | `scripts/legal_data/extract_france_gazette_2022.py` |

Each row carries provenance flags in its `source_note` column
(`legal_review_required=true;no_human_legal_approval=true;...`); the
import preserves them verbatim under `CompensationTableRow.extra.source_flags`.

## Datasets created

| `version_label` | Source | `case_type` | `status` | Rows |
|-----------------|--------|-------------|---------:|-----:|
| `FR-MORNET-2024-DRAFT` | `fr-referentiel-mornet-2024` | `road_accident_bodily_injury` | `draft` | 191 (180 DFP + 11 Affection) |
| `FR-GAZETTE-PALAIS-2022-DRAFT` | `fr-bareme-capitalisation-gazette-palais-2022` | `road_accident_bodily_injury` | `draft` | 4 188 (416 + 3 752 + 20) |

`CompensationDataset.is_usable_for_calculations` returns `False` on both
(both because `status != APPROVED` and because their parent
`LegalSource.status == needs_review`).

### Why DRAFT and only DRAFT

The project's contract is: only an `APPROVED` `LegalSource` × `APPROVED`
`CompensationDataset` × `APPROVED` `CalculationFormula` triple can feed a
public calculation. Promoting any of the three is an explicit human
decision (see `apps/legal_sources/models.py::LegalReview`).

The Mornet / Gazette CSVs are *candidates*. They reflect the upstream
extractor's best automated reading of the PDFs. Studio still has to:

1. Re-read the PDF and confirm each row's exact value (Mornet has many
   fourchettes that need legal interpretation).
2. Decide which rows go into the operational calculator and which need
   per-case Studio judgement (e.g. the Mornet "fourchettes" cells where
   the upstream extractor flattened a range to a single point).
3. File a `LegalReview` row to promote the `LegalSource` from
   `needs_review` to `APPROVED`.

This iter delivers step 0: the data is in DB, traceable, queryable, and
isolated from the public path.

---

## What the import does NOT do

| Layer | Behaviour |
|-------|-----------|
| Calculator FR | Never activated — `run_simulation(FR-NATIONAL, road_accident_bodily_injury)` keeps returning `unavailable_requires_legal_validation` (verified live + via test). |
| `CalculationFormula` (FR) | None created. The engine + the formula are a separate iter. |
| `LegalSource.status` | Never promoted. Mornet / Gazette stay `needs_review`. |
| `LegalReview` | Never auto-created. Promotion is a human decision. |
| Italia 35/10/0 | Untouched — verified live (`26 268 / 27 353 / 28 439 EUR`) + via test `test_italy_smoke_unchanged_after_fr_import`. |
| TUN dataset / formula | Untouched. |
| Destructive deletes | None — guaranteed by the static-source check `test_command_source_has_no_destructive_delete`. Re-runs only call `update_or_create`. |

---

## How it stays idempotent

Each row carries a synthetic *natural key* derived from its identifying
columns:

| `row_type` | Natural key columns |
|------------|---------------------|
| `fr_dfp_per_age_disability_amount_per_point` | `victim_age_min, victim_age_max, disability_min, disability_max` |
| `fr_prejudice_affection_per_relation_amount` | `relation_code` |
| `fr_capitalisation_viagere_per_age_sex_rate_coefficient` | `mortality_table, sex, age, interest_rate_pct` |
| `fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient` | `mortality_table, sex, age, interest_rate_pct, target_age` |
| `fr_anticipated_payment_years_per_age_sex_rate_years` | `mortality_table, sex, age, interest_rate_pct` |

The key is stored at `CompensationTableRow.extra["nat_key"]`. The
command does `update_or_create(dataset=..., row_type=..., extra__nat_key=...)`
on every import, which means:

- a CSV with the same rows on a second run leaves the DB count
  unchanged (only `updated_at` ticks);
- a CSV with edited values for an existing key updates that single
  row in place — no duplication, no orphaned old rows;
- a CSV with new keys appends rows.

The command never removes rows that disappear from the CSV — that
would be destructive. Operators handle that case manually via the
admin or a separate cleanup migration.

## Whitelist row_type

The five accepted `row_type` values are exactly those produced by the
upstream extractor scripts. The iter spec uses shorthand names
(`fr_dfp_per_pct_age_amount` etc.); the command does **not** accept
those forms — they would break traceability between CSV on disk and
DB rows. Any other `row_type` is rejected and counted as
`rows_skipped` on the run's `ExtractionLog`.

---

## How to run it

Real (production-shape) run, all 5 CSVs at once:

```powershell
.\.venv\Scripts\Activate.ps1

python manage.py import_france_candidate_datasets `
  --mornet-dfp legal_data/sources/france/mornet_2024/fr-mornet-2024-dfp-per-age-disability.csv `
  --mornet-affection legal_data/sources/france/mornet_2024/fr-mornet-2024-prejudice-affection-per-relation.csv `
  --gazette-viagere legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-viagere.csv `
  --gazette-temporaire legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-temporaire.csv `
  --gazette-anticipated legal_data/sources/france/gazette_2022/fr-gazette-2022-anticipated-payment-years.csv
```

Expected stdout:

```text
  [  OK] DFP         rows_imported=180 rows_skipped=0 -> fr-mornet-2024-dfp-per-age-disability.csv
  [  OK] Affection   rows_imported=11  rows_skipped=0 -> fr-mornet-2024-prejudice-affection-per-relation.csv
  [  OK] Viagere     rows_imported=416 rows_skipped=0 -> fr-gazette-2022-capitalisation-viagere.csv
  [  OK] Temporaire  rows_imported=3752 rows_skipped=0 -> fr-gazette-2022-capitalisation-temporaire.csv
  [  OK] Anticipated rows_imported=20  rows_skipped=0 -> fr-gazette-2022-anticipated-payment-years.csv
import_france_candidate_datasets done. datasets=[FR-MORNET-2024-DRAFT, FR-GAZETTE-PALAIS-2022-DRAFT] files=5
```

Single-CSV run (e.g. updating just the Mornet DFP table after a re-extraction):

```powershell
python manage.py import_france_candidate_datasets `
  --mornet-dfp legal_data/sources/france/mornet_2024/fr-mornet-2024-dfp-per-age-disability.csv
```

## How to verify after running

```powershell
python scripts/legal_data/verify_france_candidate_import.py
```

This script asserts every invariant listed above (counts per `row_type`,
status checks, calculator stays off, Italia smoke). Exit code 0 = pass.

---

## What's still required to make FR road_accident calculable

Each step is a separate iter — the import alone does not unlock anything:

1. **Studio legal review** of the Mornet 2024 + Gazette du Palais 2022
   contents → `LegalReview.decision=approve` from a real reviewer →
   manual promotion of `LegalSource.status` to `APPROVED`.
2. **Quantification mapping**: convert the DFP per-age × per-disability
   table into the calculator's input shape (a per-point amount × the
   victim's disability percentage); convert the affection table into
   the wrongful-death indemnification flow.
3. **`apps/calculators/engines/france.py`** with deterministic mapping
   victim_age × disability % × case category → amount (engine assent).
4. **`CalculationFormula` rows** linking the formula text to the
   datasets, in `APPROVED` status (only possible after both source and
   dataset are `APPROVED`).
5. **Mapping Dintilhac** of the poste di pregiudizio (`fr-nomenclature-dintilhac-2005`,
   already in DB as `needs_review`).
6. **Smoke test calculator FR** committed in `apps/calculators/test_*.py`,
   on the same line as the IT 35/10/0 = 26 268 / 27 353 / 28 439 EUR test.

Steps 1-6 are independent of this iter. Until they all land, the FR
calculator stays `unavailable_requires_legal_validation` regardless of
how many CSV rows are in the DRAFT datasets.

---

## Rollback

The command never deletes rows. If a DRAFT dataset needs to be wiped
(e.g. after a bad re-extraction), do it explicitly via the Django shell:

```python
from apps.compensation.models import CompensationDataset

ds = CompensationDataset.objects.get(version_label="FR-MORNET-2024-DRAFT")
assert ds.status == "draft"  # never wipe non-DRAFT datasets
ds.rows.all().delete()       # wipes children rows
# Or, to remove the dataset shell too:
ds.delete()
```

This is a destructive operation — it should never be wired into a
management command.

---

## Cross-references

- Command source: `apps/compensation/management/commands/import_france_candidate_datasets.py`
- Verify script: `scripts/legal_data/verify_france_candidate_import.py`
- Tests: `apps/compensation/test_import_france_candidate.py`
- Upstream Mornet extractor: `scripts/legal_data/extract_france_mornet_2024.py`
- Upstream Gazette extractor: `scripts/legal_data/extract_france_gazette_2022.py`
- Manual attach pipeline (used for the cousin Loi Badinter): `docs/legal_sources/MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md`
- Per-source review packages: `docs/legal_sources/FRANCE_LEGAL_REVIEW_PACKAGE.md`
