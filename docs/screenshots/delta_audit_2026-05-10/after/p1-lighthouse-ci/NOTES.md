# P1-SEO-2 — Lighthouse CI gating + favicon baseline

**Date**: 2026-05-10
**Iter**: `F-p1-seo-2-lighthouse-ci-gating`
**Branch**: `p1/lighthouse-ci-gating`

## What changed

1. Local SVG favicon: every public page now ships
   `<link rel="icon" type="image/svg+xml" href="/static/img/favicon.svg">`
   in `<head>`. A Django route at `/favicon.ico` returns the same
   SVG with `Content-Type: image/svg+xml` so naive clients (curl,
   bots, the LHCI runner without DOM-discovery) get a 200 instead
   of the pre-existing 404.
2. `lighthouserc.json` defines the gating set (8 indexable URLs)
   and the budget (perf >= 0.80, the rest >= 0.90).
3. `scripts/run_lighthouse_local.{sh,ps1}` drive `npx lighthouse@latest`
   against the URL list, write JSON reports into
   `docs/qa/lighthouse-baseline/`, exit non-zero on gate failure.
4. `docs/qa/lighthouse-baseline/SUMMARY.md` + 9 per-URL JSON
   reports captured on 2026-05-10. Every gated URL clears the
   thresholds; the noindex `/wizard/it/road-accident/` is shown
   in the table for context but is **not** in the gate set
   (Lighthouse always scores noindex 0.66 on SEO).
5. `docs/qa/LIGHTHOUSE_CI.md` runbook: prereqs, how to run, URLs
   gated, thresholds rationale, how to read a report, what to do
   on failure, CI integration outline, baseline refresh procedure.

## Baseline (desktop preset)

| URL | perf | a11y | best | seo |
|---|---|---|---|---|
| `/` | 1.00 | 0.97 | 1.00 | 1.00 |
| `/contact/` | 1.00 | 0.97 | 1.00 | 1.00 |
| `/wizard/` | 1.00 | 0.97 | 1.00 | 1.00 |
| `/wizard/it/road-accident/` (noindex; not gated) | 0.99 | 0.97 | 1.00 | 0.66 |
| `/privacy/` | 1.00 | 0.96 | 1.00 | 1.00 |
| `/disclaimer/` | 1.00 | 0.96 | 1.00 | 1.00 |
| `/countries/` | 0.99 | 0.97 | 1.00 | 1.00 |
| `/case-types/` | 1.00 | 0.96 | 1.00 | 1.00 |
| `/ar/` | 0.99 | 0.97 | 1.00 | 1.00 |

`bash scripts/run_lighthouse_local.sh` final line:

```
RESULT: all URLs cleared the gate.
```

## Files modified / new

**Modified**:
- `templates/base.html` — `<link rel="icon">` to local SVG.
- `apps/core/views.py` — `favicon_ico()` view.
- `config/urls.py` — `/favicon.ico` route (out of i18n_patterns).
- `.gitignore` — `.lighthouseci/` scratch dir excluded.

**New**:
- `static/img/favicon.svg`
- `lighthouserc.json`
- `scripts/run_lighthouse_local.sh`, `scripts/run_lighthouse_local.ps1`
- `apps/core/test_favicon_p1_seo_2.py` (13 tests)
- `docs/qa/LIGHTHOUSE_CI.md`
- `docs/qa/lighthouse-baseline/SUMMARY.md` + 9 JSON reports
- `docs/screenshots/delta_audit_2026-05-10/after/p1-lighthouse-ci/`
  (this NOTES.md + 3 screenshots).

## Tests

`apps/core/test_favicon_p1_seo_2.py` (13 tests):

- `/favicon.ico` returns 200 with SVG content-type;
- base.html links the local SVG, never an external favicon CDN;
- the SVG file exists on disk;
- `lighthouserc.json` excludes every noindex URL (5 wizard forms +
  result + thank-you);
- `lighthouserc.json` thresholds meet the user brief
  (perf >= 0.80, others >= 0.90);
- non-regression: no `fonts.googleapis.com` / `fonts.gstatic.com`
  on home/contact/privacy/disclaimer/wizard/AR home;
- CSP header still present on `/`.

| Run | Result |
|-----|--------|
| `pytest apps/core/test_favicon_p1_seo_2.py -q` | 13 passed |
| `pytest apps/core -q` | 876 passed, 1 skipped |
| `pytest -q` | **1780 passed, 1 skipped** (zero regressions, +13 from P1-CRM-1 baseline) |
| `python manage.py check` | clean (only the expected `core.W001` STUDIO_* dev warning) |
| `bash scripts/run_lighthouse_local.sh` | all 8 URLs cleared the gate |

## Browser live (Playwright)

| # | View | Viewport | Console | File |
|---|------|----------|---------|------|
| 01 | `/` (it) | desktop 1280 | **0 errors / 0 warnings** | `01_home_desktop_it_console_clean.png` |
| 02 | `/ar/` (RTL) | desktop 1280 | **0 errors / 0 warnings** | `02_home_desktop_ar_rtl_console_clean.png` |
| 03 | `/` (it) | mobile 390 | n/a (same surface as 01) | `03_home_mobile_390_it.png` |

Console is **fully clean** on the home page now: the previous favicon
404 is gone, and no CSP violations / no font 404 / no Google Fonts
fetches.

## Gating set rationale

Indexable, public surfaces gated:

```
/                    /contact/         /wizard/
/privacy/            /disclaimer/      /countries/
/case-types/         /ar/
```

Excluded by design:

- `/wizard/it/road-accident/` and 4 sibling wizard forms — `noindex,
  nofollow` private funnels.
- `/wizard/result/<uuid>/` — parametric, post-submit, `noindex`.
- `/contact/thank-you/` — post-submit, `noindex`.
- `/admin/`, `/staff/` — non-public surface.

The noindex pages are still **opened** in browser-live screenshots
across other batches (P0-LEG-2, P0-LEG-3) to ensure functional
regression coverage; they just don't contribute to the SEO/perf
gate.

## Windows note

`@lhci/cli autorun` exits with EPERM during chrome-launcher's
temp-dir cleanup on Windows. The Lighthouse JSON is fully written
**before** the cleanup attempt, and the bash/PowerShell wrappers
explicitly tolerate the cleanup error so the gate run completes.
On Linux runners (typical CI) the EPERM does not occur.

## What the Studio still has to do

Nothing — this is a dev/CI quality gate, not a Studio sign-off
artifact. The runbook is committed for the team and for future
contributors.

## Next batch suggested

1. **P1-SEC-3** — WAF/CDN edge security (Cloudflare / Caddy +
   CrowdSec) once production-style staging is up.
2. **P0-MVP-1** — first non-IT country green end-to-end (FR / BE /
   MA / TN). Unblocks the cardinal constraint of
   `LOCAL_NEXT_STEPS.md` Sec. 0.
3. **Tunisia/EU650 review + merge** — branch
   `work/tunisia-csp-eu650-restore` (`b44a5c2`) waits for Studio
   review.
4. **P1-LEG-2** — extend `audit_public_content_hygiene.py` with
   richer banned-words / deontology phrases.
5. **P2-SEO-1** — mobile preset Lighthouse baseline + budget
   (currently desktop-only).
