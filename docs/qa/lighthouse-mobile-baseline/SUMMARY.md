# Lighthouse mobile baseline — 2026-05-11

Run via `bash scripts/run_lighthouse_mobile_local.sh --update-baseline`
against `python manage.py runserver 127.0.0.1:8000`. The per-URL
JSON reports are committed alongside this file.

Mobile preset: 390×844 viewport, `formFactor=mobile`, CPU
throttling ×4, simulated 3G-like network (Lighthouse default
mobile throttling profile).

| URL | performance | accessibility | best-practices | seo |
|---|---|---|---|---|
| `/` | 0.87 | 0.97 | 1.00 | 1.00 |
| `/contact/` | 0.85 | 0.97 | 1.00 | 1.00 |
| `/wizard/` | 0.90 | 0.97 | 1.00 | 1.00 |
| `/privacy/` | 0.93 | 0.96 | 1.00 | 1.00 |
| `/disclaimer/` | 0.93 | 0.96 | 1.00 | 1.00 |
| `/countries/` | 0.83 | 0.97 | 1.00 | 1.00 |
| `/case-types/` | 0.93 | 0.96 | 1.00 | 1.00 |
| `/ar/` | 0.79 | 0.97 | 1.00 | 1.00 |

## Gating thresholds (in `lighthouserc.mobile.json`)

- performance >= 0.75
- accessibility >= 0.90
- best-practices >= 0.90
- seo >= 0.90

The mobile performance floor (0.75) is intentionally lower than the
desktop floor (0.80) because the mobile preset's CPU throttling ×4
and simulated 3G network introduce real-world variance the desktop
preset hides. The worst-performing URL today, `/ar/` at 0.79, still
has 4 points of margin against the floor.

## Notes

- Same URL set as the desktop baseline. Concrete wizard forms
  (`/wizard/<country>/<case>/`), `/wizard/result/<uuid>/` and
  `/contact/thank-you/` are excluded by design (`noindex`).
- Score volatility from run to run is normal on mobile — expect
  ±0.05 on the performance category, less on the others. The 0.75
  floor accounts for this.
- The mobile audit is **opt-in** in the consolidated quality gate.
  Run it with `bash scripts/run_quality_gate.sh --mobile-lighthouse`
  when reviewing a UI change that could plausibly hit mobile
  perf; the default 4-stage gate does not include it because the
  extra ~2 min of throttled audits noticeably slow the inner loop.

## How to regenerate

See `docs/qa/LIGHTHOUSE_MOBILE_BASELINE.md` for the full runbook.
Short version:

```
# Terminal A
python manage.py runserver 127.0.0.1:8000

# Terminal B
bash scripts/run_lighthouse_mobile_local.sh --update-baseline
# then update this SUMMARY.md and commit
```
