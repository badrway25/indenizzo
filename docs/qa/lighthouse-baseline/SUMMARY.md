# Lighthouse baseline — 2026-05-10

Run on Windows + `npx lighthouse@latest --preset=desktop --chrome-flags='--headless --no-sandbox'`
against `python manage.py runserver 127.0.0.1:8000`. The per-URL
JSON reports are committed alongside this file.

| URL | performance | accessibility | best-practices | seo |
|---|---|---|---|---|
| `/` | 1.00 | 0.97 | 1.00 | 1.00 |
| `/contact/` | 1.00 | 0.97 | 1.00 | 1.00 |
| `/wizard/` | 1.00 | 0.97 | 1.00 | 1.00 |
| `/wizard/it/road-accident/` *(noindex by design — not gated)* | 0.99 | 0.97 | 1.00 | 0.66 |
| `/privacy/` | 1.00 | 0.96 | 1.00 | 1.00 |
| `/disclaimer/` | 1.00 | 0.96 | 1.00 | 1.00 |
| `/countries/` | 0.99 | 0.97 | 1.00 | 1.00 |
| `/case-types/` | 1.00 | 0.96 | 1.00 | 1.00 |
| `/ar/` | 0.99 | 0.97 | 1.00 | 1.00 |

## Gating thresholds (in `lighthouserc.json`)

- performance >= 0.80
- accessibility >= 0.90
- best-practices >= 0.90
- seo >= 0.90

The current baseline clears every threshold by a comfortable
margin. The thresholds are intentionally not tight against the
baseline so a small, content-driven dip does not break CI; if a
genuine regression hits production-relevant scores, the gate fails.

## Notes

- The concrete wizard form (`/wizard/it/road-accident/`) is
  intentionally `noindex, nofollow`. Lighthouse always scores
  noindex pages low on SEO (0.66 above), and that is the intent on
  a private funnel. The page is excluded from the `lighthouserc.json`
  URL set.
- Reports were generated on Windows; the chrome-launcher temp-dir
  cleanup EPERM at the end of each run is benign — the JSON is
  fully written before the cleanup attempt. The same run on Linux
  / macOS succeeds without the cleanup error.
- Mobile preset baseline is NOT yet captured. Follow-up: P2-SEO-1
  (mobile content + perf budget) when the Studio prioritises a
  mobile-only audit.
- `/wizard/result/<uuid>/` and `/contact/thank-you/` are
  intentionally `noindex` post-submit pages, also excluded.

## How to regenerate

See `docs/qa/LIGHTHOUSE_CI.md` for the full runbook. Short version:

```
# Terminal A
python manage.py runserver 127.0.0.1:8000

# Terminal B
npx --yes @lhci/cli@0.14.x autorun --config=lighthouserc.json
# or, if LHCI's chrome-launcher EPERMs on Windows:
bash scripts/run_lighthouse_local.sh
```
