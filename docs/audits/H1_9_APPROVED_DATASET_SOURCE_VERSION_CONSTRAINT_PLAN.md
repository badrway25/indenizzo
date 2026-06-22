# H1-9 — Enforce approved dataset source_version at DB level — Plan

**Branch:** `feature/h1-9-approved-dataset-source-version-constraint` (from `product/staging-readiness-p0` @ `da30591`).
**Date:** 2026-06-22.

> Goal: finally enforce at the database layer the rule already in
> `CompensationDataset.clean()`: an `approved` dataset must have a
> `source_version`. Deferred since H1-5 because ~70 synthetic test fixtures
> created approved datasets without one.

## 1. The rule

`status == approved` ⇒ `source_version IS NOT NULL`. `draft` / `needs_review` /
`deprecated` may keep `source_version` NULL. Same-table check (status column +
`source_version_id` column) → valid as a `CheckConstraint` on SQLite and
PostgreSQL (no join).

## 2. Violations found (authoritative)

Adding the constraint and running the full suite produced **70 failures + 121
errors across 67 test files** — every place that creates an
`approved CompensationDataset` via `.objects.create(...)` (which bypasses
`clean()`) without a `source_version`. They are **all synthetic test fixtures**
(engine inactivity tests, public-site seeders, import/seed tests, i18n/OG/Pexels
seeders, etc.). 153 such creations across the 67 files.

**No real data violates the rule:** the dev DB has exactly 2 approved datasets
(D.P.R. 12/2025 base + moral), both already linked to a `LegalSourceVersion`
(backfilled by migration `compensation.0005`). So the constraint migration
applies to real data with zero violations and no data migration is needed.

## 3. How fixtures are corrected (no fake official sources)

A reusable test-only helper `apps/compensation/test_fixtures.py::
approved_source_version(source)` creates a clearly **test-only**
`LegalSourceVersion` (label `TEST-Vn`, `content_hash="test-only-source-hash"`).
Each approved-dataset creation now passes
`source_version=approved_source_version(<its source>)`. The version belongs to
the dataset's own (already test-only) source — no real/official source is
invented, and everything lives inside rolled-back test transactions.

The one test that *specifically* asserted the old "approved without source
version" behaviour (`test_provenance_honest_when_source_version_absent`) is
repurposed to verify the provenance **builder** is honest on a **draft**
dataset (which may legitimately lack a source version) — the approved-without-
version scenario is now structurally impossible, which is the point.

## 4. Constraint choice

```python
models.CheckConstraint(
    name="compdataset_approved_requires_source_version",
    condition=(~models.Q(status=DatasetStatus.APPROVED)
               | models.Q(source_version__isnull=False)),
)
```
Backstops the existing `clean()` rule for non-ORM paths (`.create()`, bulk,
raw SQL, fixtures). `clean()` stays (friendlier app-level error).

## 5. DB compatibility

Same-table CHECK; portable to SQLite (≥3.25, enforced) and PostgreSQL. No
backend-specific feature. Migration is a plain `AddConstraint`.

## 6. Migration / rollback

`compensation.0006_compdataset_approved_requires_source_version` (AddConstraint,
no data migration). Reversible (`migrate compensation 0005` drops it, re-apply
re-adds). Verified: rollback + re-apply, `makemigrations --check` → "No changes".

## 7. CI risk

The fix touches only test fixtures (add a kwarg) — no engine/formula/amount/
approved-source change. The fixtures seed synthetic data (no gitignored
`legal_data`), so the constraint and the fixed tests are deterministic in CI.
Provenance (H1-8), verifier (H1-8.1) and drift guard (H1-8.2) stay green; the IT
canary is unchanged.
