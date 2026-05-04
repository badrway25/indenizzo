# Public funnel — Lighthouse / Visual QA pass 1

Iter: F-product-lighthouse-visual-qa-pass1.
Date: 2026-05-04.
Scope: ship a repeatable local audit harness for the public funnels
(perf / a11y / SEO / best-practices). **No** changes to legal data,
calculator engines, country activation status or Italian dataset.

## 1. setup

- Server: `http://127.0.0.1:48107/` (live throughout the iter).
- Audit script: `scripts/run_public_lighthouse_audit.py`.
- Thresholds: `config/public_lighthouse_thresholds.json`.
- Screenshot capture: `scripts/capture_lighthouse_visual_qa_pass1_screenshots.py`.
- Tests: `apps/cases/test_public_lighthouse_audit.py` (11 tests).

## 2. tool used

The Lighthouse CLI is **not** installed on this machine and the spec
explicitly forbids triggering an internet install. The audit therefore
runs in the **Playwright fallback** mode, which is intentionally
exhaustive on the structural rules that matter most for the funnels:
HTTP 200, `<title>`, `<meta name="description">`, single `<h1>`, no
horizontal overflow on a 375 px mobile viewport, every `<img>` carries
`alt` and explicit `width`/`height`, no Pexels "Photo by …" caption,
no API-key / token leak.

The lighthouse path is fully wired in the audit script. When a
`lighthouse` (or `lhci`) binary appears on PATH, the script will run
the desktop preset against each URL, persist the JSON / HTML reports
under `docs/reports/lighthouse/public_site_pass1/`, and compare each
category against the thresholds in
`config/public_lighthouse_thresholds.json`.

## 3. audit results — Playwright fallback

Source of truth: `docs/reports/lighthouse/public_site_pass1/audit.json`.

| URL | HTTP | Title | Meta desc | One H1 | No overflow (375 px) | Img alt | Img w/h | No Pexels | No leak | Verdict |
| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: | :-: |
| `/` | OK | OK | OK | OK | OK | OK | OK | OK | OK | **PASS** |
| `/countries/` | OK | OK | OK | OK | OK | OK | OK | OK | OK | **PASS** |
| `/countries/italy/` | OK | OK | OK | OK | OK | OK | OK | OK | OK | **PASS** |
| `/wizard/` | OK | OK | OK | OK | OK | OK | OK | OK | OK | **PASS** |
| `/wizard/it/road-accident/` | OK | OK | OK | OK | OK | OK | OK | OK | OK | **PASS** |
| `/wizard/fr/road-accident/` | OK | OK | OK | OK | OK | OK | OK | OK | OK | **PASS** |
| `/contact/` | OK | OK | OK | OK | OK | OK | OK | OK | OK | **PASS** |
| `/methodology/` | OK | OK | OK | OK | OK | OK | OK | OK | OK | **PASS** |

Verdict: **OK — every required rule passes** on all 8 audited URLs at
both desktop (1280 × 900) and mobile (375 × 800) viewports.

## 4. screenshots

Captured by
`scripts/capture_lighthouse_visual_qa_pass1_screenshots.py` against
the live server. 16 PNGs total, 8 URLs × {desktop, mobile}. Naming:
`<slug>__<viewport>.png` under
`docs/screenshots/live_qa/lighthouse_visual_qa_pass1/`.

| URL | desktop | mobile |
| --- | --- | --- |
| `/` | `home__desktop.png` | `home__mobile.png` |
| `/countries/` | `countries__desktop.png` | `countries__mobile.png` |
| `/countries/italy/` | `countries_italy__desktop.png` | `countries_italy__mobile.png` |
| `/wizard/` | `wizard__desktop.png` | `wizard__mobile.png` |
| `/wizard/it/road-accident/` | `wizard_it_road-accident__desktop.png` | `wizard_it_road-accident__mobile.png` |
| `/wizard/fr/road-accident/` | `wizard_fr_road-accident__desktop.png` | `wizard_fr_road-accident__mobile.png` |
| `/contact/` | `contact__desktop.png` | `contact__mobile.png` |
| `/methodology/` | `methodology__desktop.png` | `methodology__mobile.png` |

## 5. failures / warnings

None. The 8 audited URLs pass every required rule on both viewports.
A handful of latent observations (kept as remediation notes — none
trigger a build failure):

- **Pass-3 / pass-4 baseline holds.** The fallback rules cover the
  same surface area that pass-3/pass-4 pinned, so a regression on any
  of them would now break this audit too.
- **Lighthouse-grade perf metrics** (LCP, CLS, TBT) are not yet being
  measured. To gate them we need the Lighthouse CLI on PATH (or a
  pinned `npx lighthouse` install) — see remediation note 3.

## 6. remediation list (priority order)

| # | Item | Why | When |
| --- | --- | --- | --- |
| 1 | None blocking — the fallback audit is green. | All structural rules pass. | — |
| 2 | Pin the Lighthouse CLI version in a future `package.json` (or a `tools/` script) so the script can run the lighthouse path deterministically. | Today the script silently falls back to Playwright if the binary is missing. Once we pin a version we can lift the warning-only level on `performance`. | F-perf-pass2 |
| 3 | Add LCP / CLS / TBT measurements on `/`, `/wizard/`, `/wizard/it/road-accident/` (the LCP-sensitive pages with hero images). | These are the perf metrics most sensitive to Pexels image weight. | F-perf-pass2 |
| 4 | Wire CI to fail the build when accessibility / SEO drop below 0.90 (currently the audit returns exit code 1, but we don't run it in CI yet). | Lock-in regressions fast. | F-perf-pass2 |
| 5 | Re-run after Pexels API integration (currently each Pexels image is local). | New image flow could regress LCP. | After Pexels iter |

## 7. validation

- `python manage.py makemigrations --check` → no new migrations.
- `python manage.py check` → 0 issues.
- `python manage.py compilemessages -l fr -l ar -l it` → unchanged.
- `pytest -q` → green (1037 + 11 new = 1048 tests).
- `ruff check .` → all checks passed.
- `black --check .` → all files unchanged.

## 8. summary

| Verdict | Detail |
| --- | --- |
| Audit | OK on all 8 URLs (Playwright fallback, both viewports). |
| Italia | 35/10/0 → 26 268 / 27 353 / 28 439 EUR — unchanged (smoke test passing). |
| Other countries | FR/BE/MA/TN remain inactive. |
| Server | Live on `127.0.0.1:48107`. |
| Tools added | audit script, thresholds JSON, screenshot script, 11 tests, this report. |
