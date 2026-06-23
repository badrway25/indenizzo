# D2 — Legal Source Evidence & Review Pack UX — Plan

**Branch:** `feature/d2-legal-source-evidence-review-pack-ux` (from `product/staging-readiness-p0` @ `24372a2`).
**Date:** 2026-06-23.

> Goal: make the legal-source review workflow genuinely usable by the Studio —
> surface the *evidence* (attachment, hash, version, review package, latest
> decision) and the recommended next action per source — WITHOUT approving,
> promoting or activating anything. Read-only, fail-closed, migration-free.

## 1. Current state (after D1)

- **D1** added a read-only readiness report (`review_readiness.py` +
  `report_legal_review_readiness`), admin "latest review" / "readiness" columns
  and a read-only readiness action, plus `LegalSource.latest_review` (no
  migration). FR/BE/MA/TN stay fail-closed.
- **Evidence already in the system:** `LegalSourceAttachment.sha256`
  (auto-computed on save), `LegalSourceVersion`, `LegalReview` (append-only),
  and the per-country generated review packages
  `docs/legal_sources/generated/<CC>_REVIEW_PACKAGE_GENERATED_<date>.md`.
- The official registry (`config/official_source_registry.json`) defines the
  *candidate* set (`source_slug`, `expected_format`, `source_kind`, markers) —
  metadata only, no raw legal text. It has **no expected-hash field**; hash
  integrity is proven by the attachment sha256 + the `validate` notes block.

## 2. What was missing for a Studio reviewer

A single per-source **evidence checklist** answering: official attachment? hash?
version? a (fresh) review package for the country? latest decision + age? and
crisp flags — `ready_for_studio_review`, `ready_for_dataset_seed_review`, plus a
fail-closed `never_calculation_ready_reason`. Plus a **review-pack index** report
and admin visibility of the same.

## 3. Design — reuse, additive, no schema change

- **No migration.** Everything is derived from existing fields/files.
- **`apps/legal_sources/review_evidence.py`** — pure, read-only module on top of
  D1's `build_readiness_rows`. Adds the evidence booleans, the review-package
  index (parses the generated filenames + a freshness window), latest-review age,
  `ready_for_studio_review` / `ready_for_dataset_seed_review`, and the
  fail-closed reason. `needs_ocr` is a conservative heuristic (PDF candidate with
  an unhashed attachment) — documented as such.
- **`report_legal_review_pack_index`** command — `--country`, `--format`,
  `--output`, `--today` (testability), and three fail-closed guards:
  `--fail-if-missing-review-pack-for-candidate`,
  `--fail-if-calculation-ready-without-review`,
  `--fail-if-approved-without-source-version`. Default read-only, no DB write,
  no raw PDF/OCR text printed.
- **Admin** — a compact read-only `evidence` column (attach · hash · ver) on the
  LegalSource changelist and a read-only "Show evidence checklist" action.
- **Runbook** — `docs/ops/LEGAL_SOURCE_STUDIO_REVIEW_RUNBOOK.md`, written for the
  Studio/reviewer.

## 4. How automatic approval stays impossible

- The module, command and admin action are **read-only** (tested: no DB write).
- Nothing approves a source, promotes a status, seeds/approves a dataset, or
  registers/activates an engine. Promotion remains only via
  `promote_official_legal_sources` (allow-list + re-validation + staff reviewer).
- `ready_for_dataset_seed_review` is a *reviewer hint*, not an action; the
  calculation-activation step stays a separate, human-gated decision.
- Tested: FR/BE/MA/TN are never calculation-ready; running the index does not
  change a source's status nor make the FR engine produce a number (stays
  `UNAVAILABLE_REQUIRES_LEGAL_VALIDATION`).

## 5. Rollback

- No schema change → reverting the branch fully removes the feature; nothing to
  roll back at the DB level.
- The admin `evidence` column uses 3 cheap `exists()` queries per row (no full
  scan), so the changelist stays responsive.
