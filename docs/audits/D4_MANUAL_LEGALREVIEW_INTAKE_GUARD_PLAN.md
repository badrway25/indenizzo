# D4 — Manual LegalReview Intake & Audit Guard — Plan

**Branch:** `feature/d4-manual-legalreview-intake-guard` (from `product/staging-readiness-p0` @ `5df6a27`).
**Date:** 2026-06-23.

> Goal: make recording a manual `LegalReview` decision in the back-office safer —
> block clearly-incoherent approvals, warn on softer gaps, audit existing
> decisions — WITHOUT automating approvals or activating any calculation.
> Read-only/guard layer, fail-closed, no migration.

## 1. Current state

- **`LegalReview`** — append-only decision log (decisions: approve / reject /
  request_changes / reopen; ordered `-created_at, -pk` after D1's tie-break fix).
- **`LegalReviewAdmin`** — append-only (no delete, existing rows frozen, reviewer
  forced to `request.user`). Today the add form has **no validation, no
  guidance, no evidence display**: a reviewer could record an `approve` on a
  source with no attached/verified document.
- Promotion to APPROVED is also done by `promote_official_legal_sources` via the
  ORM (allow-list + re-validation) — it bypasses the admin form.

## 2. Risks of manual intake

A human can record an `approve` that contradicts the evidence (no attachment, no
verified hash). Nothing surfaces the inconsistency at intake time, and nothing
audits previously-recorded decisions against the current evidence.

## 3. Design — guard layer, additive, no schema change

- **No migration.** The decision set is unchanged (approve/reject/request_changes/
  reopen). Finer decisions remain a documented future option.
- **`apps/legal_sources/review_decision_guard.py`** — pure read-only
  `evaluate_legal_review_decision(source, decision) → DecisionGuardResult`
  (decision, allowed, severity, warnings, blocking_reasons, recommended_action,
  evidence_summary, **calculation_activation_allowed = False**). Rules: reject/
  request_changes/reopen always allowed; `approve` BLOCKED when no attachment or
  unverified hash, WARNED when no source version / review package. No decision
  ever activates a calculation.
- **Admin form** `LegalReviewAdminForm` — validation in the **form** (not the
  model), so the promotion command is unaffected. Blocking reasons raise a
  `ValidationError`; warnings are shown as admin messages after save; the
  decision field gets clear help text; the changelist gains `country` +
  `evidence` columns + a country filter.
- **`validate_legal_review_decisions`** command — read-only audit of recorded
  decisions vs current evidence + the fail-closed invariants
  (calc-ready-without-review, approved-without-version, non-IT-calc-ready).
  `--country`, `--format`, `--output`, `--include-history`, `--fail-on-blocking`,
  `--fail-on-warning`. PII-safe.
- **Runbook** `docs/ops/LEGAL_REVIEW_DECISION_INTAKE_RUNBOOK.md`.

## 4. What stays NOT automated / fail-closed

- The guard NEVER creates a review, approves a source, promotes a status, seeds/
  approves a dataset, or activates an engine. It evaluates and reports.
- Validation lives in the admin form only; the ORM/promotion path is untouched
  (its own allow-list + re-validation gate stays the source of truth there).
- Tested: a recorded approval never makes an FR source calculation-ready; no
  dataset is created; FR/BE/MA/TN stay `calculation_ready=False`; the validator
  is read-only + PII-safe; `--fail-on-blocking` exits non-zero on inconsistency.

## 5. Rollback

No schema change → reverting the branch removes the guard, the form validation,
the command and the tests; nothing to undo at the DB level.
