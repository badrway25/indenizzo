# D1 — Legal Source Review Workflow (FR/BE/MA/TN review readiness) — Plan

**Branch:** `feature/d1-legal-source-review-workflow` (from `product/staging-readiness-p0` @ `10a5c79`).
**Date:** 2026-06-23.

> Goal: make it easy for the Studio to see what each legal source still needs
> before it could ever be approved/promoted, WITHOUT activating any FR/BE/MA/TN
> calculation. Read-only, fail-closed, reusing the existing pipeline.

## 1. Current state (audit)

The legal-source pipeline is already mature:

- **Models** — `LegalSource` (status pipeline draft→…→approved), `LegalSourceVersion`,
  `LegalSourceAttachment` (sha256), `LegalReview` (append-only decision log:
  `request_changes` / `approve` / `reject` / `reopen`; ordered `-created_at`).
- **Commands** — `report_legal_source_status` (read-only), `generate_legal_review_package`
  (read-only, per-country packages in `docs/legal_sources/generated/`),
  `validate_official_legal_sources` (dry-run/commit; `NOT_CALCULATION_READY_SLUGS`),
  `promote_official_legal_sources` (dry-run/commit; `PROMOTABLE_SLUGS` +
  `DENY_LIST_SLUGS`; creates an `approve` `LegalReview`, sets `status=APPROVED`,
  **never activates a calculator**), `attach_official_source_file`.
- **Admin** — `LegalSource` (inlines for versions/attachments/reviews),
  `LegalReview` is an append-only freezer (no delete, no edit, reviewer forced to
  `request.user`).
- **Fail-closed today** — FR/BE/MA/TN are not calculation-ready because no
  APPROVED `CompensationDataset` backs them; the placeholder engines return
  `UNAVAILABLE_REQUIRES_LEGAL_VALIDATION`; `calculation_ready` is computed from
  APPROVED datasets only. H1-9 enforces APPROVED dataset → `source_version`.

## 2. What was missing for an orderly Studio review

A single **read-only readiness view** that, per source, answers: is the file
attached & hashed? is there a version? what is the latest review decision? is it
calculation-ready? and — crucially — **what concrete steps remain**, with a
recommended next action. Plus a couple of **fail-closed assertions** the Studio /
CI can run.

## 3. Design — reuse, additive, no schema change

- **No migration.** The existing `LegalReview` already records review decisions
  (append-only, admin-frozen). Adding decision states or boolean
  authorization flags would be premature and risks introducing a
  calculation-authorization toggle — the safest fail-closed choice is to keep
  authorization *computed* from real state (APPROVED dataset + `source_version` +
  active engine), exactly as today. A richer decision taxonomy /
  `calculation_ready_allowed` flag is recorded here as a **future controlled
  extension**, not implemented now.
- **`LegalSource.latest_review`** — a read-only property (`reviews.first()`), no
  DB field, no migration.
- **`apps/legal_sources/review_readiness.py`** — pure, read-only module built on
  `status_report.build_rows`; adds latest-review, ordered `missing_steps`,
  `recommended_next_action`, and two fail-closed checks.
- **`report_legal_review_readiness`** command — `--country FR|BE|MA|TN|IT|EU|ALL`,
  `--format text|json|markdown`, `--output`,
  `--fail-if-calculation-ready-without-review`,
  `--fail-if-approved-without-source-version`. Default read-only, no DB write.
- **Admin** — `LegalSource` changelist gains read-only `latest review` +
  `readiness` columns and a **read-only** "Report review readiness" action
  (messages the missing steps; creates nothing, promotes nothing).

## 4. How unsafe promotion stays impossible

- The readiness report and admin action are **read-only** (tested: no DB write).
- Nothing here approves a source, seeds/approves a dataset, or registers/activates
  an engine. Promotion remains only via `promote_official_legal_sources`
  (allow-list + re-validation + staff reviewer), which never activates a
  calculator.
- `--fail-if-calculation-ready-without-review` flags any calc-ready source lacking
  an `approve` review; `--fail-if-approved-without-source-version` re-asserts H1-9.
- Tested invariant: FR/BE/MA/TN sources are never calculation-ready; running the
  report does not make the FR engine produce a number (stays
  `UNAVAILABLE_REQUIRES_LEGAL_VALIDATION`).

## 5. Risks & rollback

- No schema change → nothing to roll back at the DB level; reverting the branch
  fully removes the feature.
- Admin `readiness` column recomputes per changelist render (O(n) over ~31
  sources) — acceptable for an internal admin; can be memoized later if needed.
