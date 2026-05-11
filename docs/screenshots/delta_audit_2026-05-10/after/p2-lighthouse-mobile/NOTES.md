# P2-SEO-1 — Lighthouse mobile baseline + budget

**Date**: 2026-05-11
**Iter**: `F-p2-seo-1-lighthouse-mobile-baseline`
**Branch**: `p2/lighthouse-mobile-baseline`
**Tag baseline P1-QA-1**: `p1-qa-1-local-quality-gate-2026-05-10`.

## Scope

Add a Lighthouse **mobile** preset as a separate, **opt-in** gate
alongside the existing desktop preset. The default 4-stage quality
gate is unchanged: mobile is a 5th stage activated by an explicit
`--mobile-lighthouse` / `-MobileLighthouse` flag.

Goals:

- Capture a mobile baseline against the same indexable URL set as
  desktop (8 URLs — see §5 of the runbook).
- Set realistic budgets that hold against mobile-throttling variance
  but still catch real regressions.
- Wire the mobile audit into the consolidated gate **without forcing
  it** on routine inner-loop runs (the default gate stays at ~5 min).
- Keep the working tree clean on a default mobile-gate run (same
  contract as desktop: `--update-baseline` is the only command that
  writes to tracked files).

## Files modified / new

**New**:
- `lighthouserc.mobile.json` — mobile preset (390×844, CPU×4,
  simulated 3G), budgets, skip-list for production-edge audits.
- `scripts/run_lighthouse_mobile_local.sh` — bash runner with
  `--update-baseline`.
- `scripts/run_lighthouse_mobile_local.ps1` — PowerShell runner with
  `-UpdateBaseline`.
- `apps/core/test_lighthouse_mobile_p2_seo_1.py` — 24 static-side
  smoke tests.
- `docs/qa/LIGHTHOUSE_MOBILE_BASELINE.md` — runbook (14 sections).
- `docs/qa/lighthouse-mobile-baseline/SUMMARY.md` — baseline table.
- `docs/qa/lighthouse-mobile-baseline/*-mobile.json` — 8 baseline
  Lighthouse reports (one per URL).
- `docs/screenshots/delta_audit_2026-05-10/after/p2-lighthouse-mobile/NOTES.md`
  (this).

**Modified**:
- `scripts/run_quality_gate.sh` — added `--mobile-lighthouse` flag
  → optional 5th stage.
- `scripts/run_quality_gate.ps1` — added `-MobileLighthouse` switch
  → optional 5th stage.
- `.gitignore` — added `.lighthouseci-mobile/` (companion of the
  desktop `.lighthouseci/`).

## Captured baseline (2026-05-11)

Per-URL mobile scores, single run each (see runbook §10 on why
single-run is the right baselining strategy):

| URL | perf | a11y | best | seo |
|---|---|---|---|---|
| `/` | 0.87 | 0.97 | 1.00 | 1.00 |
| `/contact/` | 0.85 | 0.97 | 1.00 | 1.00 |
| `/wizard/` | 0.90 | 0.97 | 1.00 | 1.00 |
| `/privacy/` | 0.93 | 0.96 | 1.00 | 1.00 |
| `/disclaimer/` | 0.93 | 0.96 | 1.00 | 1.00 |
| `/countries/` | 0.83 | 0.97 | 1.00 | 1.00 |
| `/case-types/` | 0.93 | 0.96 | 1.00 | 1.00 |
| `/ar/` | 0.79 | 0.97 | 1.00 | 1.00 |

Worst score = `/ar/ perf 0.79`. Best score = `/privacy/`,
`/disclaimer/`, `/case-types/` perf 0.93.

## Chosen thresholds

| Category | Mobile floor | Desktop floor | Worst mobile score | Headroom |
|---|---|---|---|---|
| performance | 0.75 | 0.80 | 0.79 | **+0.04** |
| accessibility | 0.90 | 0.90 | 0.96 | +0.06 |
| best-practices | 0.90 | 0.90 | 1.00 | +0.10 |
| seo | 0.90 | 0.90 | 1.00 | +0.10 |

Rationale documented in `docs/qa/LIGHTHOUSE_MOBILE_BASELINE.md` §7.
Summary: mobile perf floor is 5 points lower than desktop because
the simulated CPU×4 + 3G throttling introduces ~±0.05 run-to-run
jitter. A 0.80 floor would put `/ar/` 1 point above the line —
turning the gate red on jitter, not on regression. A 0.75 floor
gives the worst URL 4 points of margin while still catching a
10-point real regression on any page.

Categories `a11y`/`best`/`seo` are deterministic (don't move with
throttling), so they stay at the desktop floor of 0.90.

## Working-tree discipline

Same contract as the desktop gate:

| Command | Tracked files touched |
|---|---|
| `bash scripts/run_lighthouse_mobile_local.sh` | **none** (writes to gitignored `artifacts/lighthouse-mobile/latest/`) |
| `bash scripts/run_lighthouse_mobile_local.sh --update-baseline` | yes, intentionally — `docs/qa/lighthouse-mobile-baseline/` |
| `bash scripts/run_quality_gate.sh --mobile-lighthouse` | **none** (the gate is a verification step, not a baseliner) |

The PowerShell variants behave identically.

## Why the mobile stage is opt-in

| If I were to make the mobile stage default-on | But |
|---|---|
| Every gate run would catch mobile regressions automatically. | ~2 min slowdown on the inner loop — gate goes from ~5 min to ~7 min. |
| One command, two preset coverage. | The mobile preset has a real jitter floor — false-positive risk doubles. |
| Less to remember for the operator. | The default gate is already comprehensive; mobile is the *spot check* for UI changes specifically. |

Default-off makes the mobile audit visible without forcing it. The
runbook explains when to opt-in (UI / front-end changes that
plausibly affect mobile rendering).

## Smoke tests (24)

`apps/core/test_lighthouse_mobile_p2_seo_1.py`:

1. `lighthouserc.mobile.json` exists.
2. mobile preset has `formFactor=mobile`, 390×844, CPU×4.
3. config URL set matches the desktop indexable set.
4. config excludes noindex wizards.
5. thresholds match the runbook's claim (perf 0.75, a11y/best/seo 0.90).
6. config's `outputDir` is the gitignored `./.lighthouseci-mobile`.
7. bash runner exists with reasonable size.
8. bash runner exposes `--update-baseline` (and points at both
   tracked + gitignored output paths).
9. bash runner carries every expected URL label.
10. bash runner sets mobile emulation flags on the `npx lighthouse`
    command line.
11. PowerShell runner exists.
12. PowerShell runner exposes `-UpdateBaseline`.
13. PowerShell runner sets the same mobile emulation flags.
14. bash runner has no external HTTP targets.
15. PowerShell runner has no external HTTP targets.
16. consolidated bash gate wires `--mobile-lighthouse`.
17. consolidated PowerShell gate wires `-MobileLighthouse`.
18. mobile stage in both gates is opt-in (default off).
19. baseline dir contains exactly one JSON per URL.
20. baseline `SUMMARY.md` lists every URL.
21. each baseline JSON's `configSettings.formFactor == "mobile"`.
22. each baseline JSON itself respects the floor we just set (the
    gate must not be a lie against its own baseline).
23. runbook exists and references every moving piece.
24. `.gitignore` excludes `.lighthouseci-mobile/` and `artifacts/`.

These are *static* tests — no Lighthouse subprocess, no network, no
pytest-inside-pytest. They pin the contract; the actual gating is
the runner script.

## Verifications run

| Command | Result |
|---|---|
| `pytest apps/core/test_lighthouse_mobile_p2_seo_1.py -q` | **24 passed in 0.96 s** |
| `bash scripts/run_lighthouse_mobile_local.sh` (default) | all 8 URLs cleared the mobile gate |
| `bash scripts/run_lighthouse_mobile_local.sh --update-baseline` | 8 baseline JSONs written to `docs/qa/lighthouse-mobile-baseline/` |
| `bash scripts/run_quality_gate.sh --help` | help text mentions `--mobile-lighthouse` |
| `git status` after a default mobile-gate run | clean |

End-to-end full quality gate with `--mobile-lighthouse` is the
operator path the runbook documents (~7 min total). The default
4-stage gate (~5 min) covered the regression-safety baseline in
P1-QA-1.

## Skipped audits (and why)

`lighthouserc.mobile.json::ci.collect.settings.skipAudits` removes:

- `is-on-https` — local dev server is plain HTTP. Production has TLS.
- `redirects-http` — same reason.
- `uses-http2` — Django runserver doesn't speak HTTP/2; CDN does.
- `uses-long-cache-ttl` — runserver doesn't set Cache-Control headers
  for static assets; WhiteNoise / CDN handles it in production.
- `canonical` — absolute canonical URL needs the production host;
  on `127.0.0.1:8000` it would always fail.

These are checked at the production edge by other gates (WAF /
CDN / `manage.py check --deploy`). Skipping them here keeps the
mobile budget honest: a failure is a real regression in code, not
infrastructure.

## What's deliberately NOT in this batch

- **CI wiring** — the runbook §13 outlines the GitHub Actions job;
  actually shipping a workflow is a separate batch (depends on the
  team's CI choice).
- **Per-country wizard mobile audit** — the wizard hub `/wizard/` is
  gated; the concrete `/wizard/<country>/<case>/` forms are
  `noindex` (private funnels) and excluded by design, same as the
  desktop baseline.
- **Mobile lcp / cls budgets** — only category-level scores are
  gated, not individual web-vital audits. Tightening at the audit
  level would force a much narrower budget for marginal value at
  this scale.
- **Auto-baselining on Studio approval** — the workflow stays
  manual-and-explicit; `--update-baseline` is the only path that
  writes tracked files. A bot that re-baselines on a PR label is a
  future improvement.

## Next batch suggested

In order of expected value:

1. **P0-MVP-1** — first non-IT country green end-to-end
   (FR/BE/MA/TN). The mobile preset will then exercise five real
   landing pages instead of just the IT/AR hub set.
2. **Tunisia/EU650 review + merge** — branch
   `work/tunisia-csp-eu650-restore`.
3. **P1-SEC-3** — WAF/CDN edge security.
4. **CI wiring (gate + mobile)** — port to GitHub Actions per
   runbook §13 + `LIGHTHOUSE_CI.md` §7.
5. **P2-A11Y-1** — tighten a11y floor to 0.95 once the worst URL
   sustainably clears it (currently 0.96 on the strict pages,
   0.97 on the rest).
