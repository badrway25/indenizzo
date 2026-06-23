# H1-10.1 — Lighthouse Metric-Zero Hardening — Plan

**Branch:** `fix/h1-10-1-lighthouse-metric-zero-retry` (from `product/staging-readiness-p0` @ `711751c`).
**Date:** 2026-06-23.

> Infra-only. No engine/formula/amount/approved-source/source_version change.
> Goal: re-collect a *corrupted* Lighthouse report (valid JSON but
> `performance=0.00` from an empty/errored trace) without ever hiding a real
> budget miss. The gate stays blocking and single-shot.

## 1. What H1-10 already covers

`scripts/run_lighthouse_local.sh` (and the mobile twin) retry report
**collection** up to 2× when Chrome produces **no valid JSON** (launch/artifact
flake), kill orphan Chrome between attempts, and run the score **gate**
single-shot. `--disable-dev-shm-usage` reduces Chrome crashes. The gate is never
retried, so a real budget miss fails.

## 2. What was left uncovered (PR #14 symptom)

Lighthouse can emit a **valid** JSON (with `categories`) whose
`performance.score == 0.00` while `accessibility/best-practices/seo` stay high
(observed on PR #14: one URL perf 0.00, the rest 0.96–1.00, re-run green). The
H1-10 "collected" check only verified `categories` existed, so this corrupt
report was accepted and the single-shot gate failed it with no retry — a false
red requiring a manual re-run.

## 3. Corrupt report vs real budget miss

A small testable guard (`scripts/lighthouse_score_guard.py`,
`classify_report`) returns one word:

- **`retry`** — `performance.score` is `0`/`None` AND ≥3 of the core
  performance-metric audits (FCP, LCP, Speed Index, TBT, CLS) are
  errored/missing AND at least one other category is healthy (≥0.5). That is a
  corrupt trace: the page loaded (a11y/seo measured) but the perf metrics could
  not be computed → not a real 0% performance.
- **`accept`** — any other usable report: a normal score, a *plausible* low
  score (e.g. 0.40), or even a genuine `perf=0` whose audits **were** computed.
  The single-shot gate judges it and fails it if below budget. Never retried.
- **`invalid`** — file missing / not JSON / no `categories` (the H1-10 case).

The discriminator is deliberately conservative: a real regression is a plausible
non-zero score with computed audits, never an exact 0.00 with errored perf
metrics while a11y/SEO stayed high.

## 4. Retry behavior (runner integration)

Per URL the runner now:
1. runs Lighthouse, then asks the guard for a verdict;
2. `accept` → collected, break (gate judges);
3. `retry` → log `suspicious performance=0.00 report (corrupt trace),
   re-collecting`, kill Chrome, retry once;
4. `invalid` → the existing no-JSON retry path;
5. after 2 attempts: if a JSON with `categories` persists (metric-zero did not
   clear) it is handed to the **single-shot gate so it FAILS HONESTLY** on
   `perf < 0.80`; only a genuinely missing report aborts (exit 3).

The score gate (Python heredoc) is unchanged — one `global_failed=1`, no retry.

## 5. Stays blocking

No `continue-on-error`, no skipped gate, no relaxed budgets, no infinite retry
(max 2 attempts), no masking. The gate stays red for: a plausible low
performance, a11y/best/seo below floor, a missing page, a real JS error, a
report whose metrics are coherent but under budget, or a metric-zero that
persists after the single retry.

## 6. Limits & rollback

- The guard reads only scores/audit status — PII-safe, stdlib-only,
  cross-platform.
- If a future genuine perf disaster somehow produced exactly 0.00 with **all
  perf audits errored** AND healthy a11y/SEO, the runner would retry once; if the
  page is truly broken it stays 0.00 on the retry and the gate fails. So the
  worst case is one extra ~15 s collection, never a masked failure.
- No schema/workflow change. Reverting the branch restores the H1-10 behavior.
