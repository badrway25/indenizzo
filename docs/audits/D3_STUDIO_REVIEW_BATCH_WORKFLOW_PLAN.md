# D3 — Studio Review Batch Workflow — Plan

**Branch:** `feature/d3-studio-review-batch-workflow` (from `product/staging-readiness-p0` @ `527e5d3`).
**Date:** 2026-06-23.

> Goal: make the Studio review workflow concretely runnable by assembling ordered,
> reviewer-oriented **batches** (evidence + readiness + missing steps + a manual
> decision template + a safe link to the generated review package). Read-only and
> fail-closed. It approves nothing, records no `approve`, promotes no dataset,
> activates no calculation, and never exposes raw legal data.

## 1. What already exists (D1/D2)

- **D1** `review_readiness.py` + `report_legal_review_readiness`: per source the
  ordered `missing_steps`, `recommended_next_action`, calculation-readiness, and
  the fail-closed guards (`calculation_ready_without_approve_review`,
  `approved_datasets_without_source_version`).
- **D2** `review_evidence.py` + `report_legal_review_pack_index`: the
  `EvidenceRow` already carries every safe field — attachment/hash/version flags,
  the repo-relative `review_package_path` (+ freshness), `latest_review_decision`,
  `ready_for_studio_review`, `calculation_ready`, `never_calculation_ready_reason`.
- **Admin** `LegalSourceAdmin` with read-only readiness/evidence columns + two
  read-only actions; `LegalReview` is append-only.
- Per-country generated packages in `docs/legal_sources/generated/`.

## 2. What was missing for a real Studio session

A single **batch** per reviewer that orders the above into a worklist with a
**manual decision template** the Studio fills by hand — so a session has a
concrete, archivable artifact — without any automatic approval.

## 3. Design — compose, additive, no schema change

- **No migration.** Everything is derived from D1/D2.
- **`apps/legal_sources/review_batch.py`** — pure read-only builder composing D2
  evidence + D1 readiness into `ReviewBatchItem`s (safe fields only) + a
  `DECISION_TEMPLATE` checklist (placeholder, never parsed) + markdown/JSON
  renderers, with a "do not use for automatic calculation activation" footer.
  Filters: `include_blocked` (default — the review work), `include_ready`,
  `limit`.
- **`prepare_studio_review_batch`** command — `--country`, `--format`,
  `--output`, `--limit`, `--include-ready`, `--no-include-blocked`, `--today`,
  and three fail-closed guards (`--fail-if-empty`,
  `--fail-if-calculation-ready-without-review`,
  `--fail-if-approved-without-source-version`). Read-only, no DB write.
- **Admin** — a third read-only action "Show Studio review batch summary"
  (per-country counts as a message; writes nothing).
- **Runbook** `docs/ops/STUDIO_REVIEW_BATCH_WORKFLOW.md`.

## 4. Public vs internal / leak safety

Emitted (safe): country, slug, title, status, candidate yes/no, attachment/hash/
version **present-absent only**, the **repo-relative** package path + freshness,
`latest_review_decision` (the decision word only), readiness/evidence summary,
missing steps, recommended action, fail-closed reason, the manual decision
template. **Never emitted:** full hashes, absolute paths, reviewer names/emails,
review notes/comments, raw PDF/OCR/legal text, `legal_data/`, secrets. A test
seeds a real attachment hash + reviewer email + review note and asserts none
appear in the JSON/markdown.

## 5. How automatic approval stays impossible

- Builder, command and admin action are **read-only** (tested: record counts
  invariant). Nothing creates a `LegalReview`, promotes a status, seeds/approves
  a dataset, or activates an engine.
- The decision template is plain text the reviewer fills **in the back-office**;
  it is never parsed as a machine decision.
- Tested: FR/BE/MA/TN items are never calculation-ready; the guards flag a
  calc-ready source without an approve review or an approved dataset without a
  source version.

## 6. Rollback

No schema change → reverting the branch removes the module, command, admin action
and tests; nothing to undo at the DB level.
