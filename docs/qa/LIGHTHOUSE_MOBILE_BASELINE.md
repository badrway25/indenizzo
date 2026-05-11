# Lighthouse mobile baseline — runbook

**Iter**: F-p2-seo-1-lighthouse-mobile-baseline
**Date**: 2026-05-11

This runbook explains how to capture, gate, and refresh the
Lighthouse **mobile** baseline. It is the companion of
`docs/qa/LIGHTHOUSE_CI.md` (desktop preset, gating the same URL set).

The mobile audit is **opt-in** in the consolidated quality gate. The
default 4-stage gate runs the desktop preset only; mobile is an
explicit 5th stage activated by `--mobile-lighthouse`.

Companion files:

- `lighthouserc.mobile.json` — URLs, mobile emulation settings,
  thresholds.
- `scripts/run_lighthouse_mobile_local.sh` — bash runner.
- `scripts/run_lighthouse_mobile_local.ps1` — PowerShell runner.
- `docs/qa/lighthouse-mobile-baseline/` — committed baseline JSON
  reports + `SUMMARY.md`.

---

## 1. Why a separate mobile baseline

Desktop and mobile Lighthouse runs measure two very different things:

| | Desktop preset | Mobile preset |
|---|---|---|
| Viewport | 1350×940 | 390×844 |
| Form factor | `desktop` | `mobile` |
| CPU throttling | none (×1) | ×4 |
| Network | broadband | simulated 3G-like |
| Run-to-run variance on `perf` | ~±0.02 | ~±0.05 |

A page that scores `perf 1.00` on desktop can land at `0.80` on
mobile purely because of CPU throttling — that is signal, not noise:
mobile is where users live. Gating mobile separately catches
regressions that the desktop preset hides.

It is also kept separate (not merged into the desktop gate) because:

- mobile throttling adds ~2 min of wall-clock on every run;
- the variance floor is real and would force a looser shared budget
  if the two presets shared one threshold;
- the default gate already takes ~5 min — pushing it to ~7 min would
  hurt the inner loop without proportional value.

---

## 2. Prerequisites

Identical to the desktop runner (see `docs/qa/LIGHTHOUSE_CI.md` §1):

- Python venv with project deps installed.
- Node.js + npm on PATH (the runner uses `npx` on demand).
- The dev server reachable on `http://127.0.0.1:8000/`. The runner
  refuses to start if not — see `LIGHTHOUSE_CI.md` §1 for why.

---

## 3. Run the mobile gate locally

```
# Terminal A — Django
source .venv/Scripts/activate          # or `. .venv\Scripts\Activate.ps1`
python manage.py runserver 127.0.0.1:8000

# Terminal B — gate run (default: artifacts/lighthouse-mobile/latest/ — gitignored)
bash scripts/run_lighthouse_mobile_local.sh
# or
pwsh scripts/run_lighthouse_mobile_local.ps1

# Terminal B — explicit baseline refresh (writes tracked files in
# docs/qa/lighthouse-mobile-baseline/ — commit the diff after review)
bash scripts/run_lighthouse_mobile_local.sh --update-baseline
pwsh scripts/run_lighthouse_mobile_local.ps1 -UpdateBaseline
```

Output destination:

- **default (gate run)** — `artifacts/lighthouse-mobile/latest/<label>-mobile.json`.
  The `artifacts/` directory is gitignored, so a routine gate run
  never dirties the working tree.
- **`--update-baseline`** — `docs/qa/lighthouse-mobile-baseline/<label>-mobile.json`.
  The only path that intentionally writes to tracked files. Use it
  when the Studio has approved a visible change that legitimately
  moves the mobile scores. Commit the diff + the matching
  `SUMMARY.md` update.

---

## 4. Run it via the consolidated quality gate

The mobile audit is wired into `scripts/run_quality_gate.{sh,ps1}`
as an **opt-in** 5th stage:

```
# bash
bash scripts/run_quality_gate.sh --mobile-lighthouse

# PowerShell
pwsh scripts/run_quality_gate.ps1 -MobileLighthouse
```

When the flag is absent, the gate runs the standard 4 stages and
ignores the mobile preset entirely (so the default ~5 min budget
holds).

Stage order:

| # | Stage | Skipped by |
|---|-------|------------|
| 1 | Django system checks | — |
| 2 | Test suite | `--no-pytest` / `-NoPytest` |
| 3 | Deontological content hygiene | — |
| 4 | Lighthouse desktop | `--no-lighthouse` / `-NoLighthouse` |
| 5 | Lighthouse mobile (opt-in) | absent without `--mobile-lighthouse` / `-MobileLighthouse` |

See `docs/qa/LOCAL_QUALITY_GATE.md` for the rest of the gate's
contract.

---

## 5. URLs gated

Defined in `lighthouserc.mobile.json::ci.collect.url`. **Same set as
desktop** so a single content change is gated against both presets:

| URL | Why it is gated |
|---|---|
| `/` | landing page |
| `/contact/` | indexable institutional page |
| `/wizard/` | hub page (the concrete forms below are noindex) |
| `/privacy/` | versioned legal page |
| `/disclaimer/` | versioned legal page |
| `/countries/` | hub for the 5 country landings |
| `/case-types/` | hub for case types |
| `/ar/` | RTL home — guards regression on Arabic UI on mobile |

URLs deliberately **not** gated — same exclusions as desktop:
`/wizard/<country>/<case>/`, `/wizard/result/<uuid>/`,
`/contact/thank-you/`, `/admin/`, `/staff/`, the per-country
landings. See `LIGHTHOUSE_CI.md` §3 for the rationale.

---

## 6. Mobile emulation settings

From `lighthouserc.mobile.json::ci.collect.settings`:

| Setting | Value | Why |
|---|---|---|
| `formFactor` | `mobile` | Switches Lighthouse audits to the mobile rulebook (different a11y thresholds, different SEO defaults). |
| `screenEmulation.width` × `height` | 390 × 844 | iPhone-class viewport — the most common mobile profile. |
| `screenEmulation.deviceScaleFactor` | 2 | Matches retina-class devices. |
| `throttling.cpuSlowdownMultiplier` | 4 | Lighthouse default mobile CPU throttling. Simulates a mid-tier Android. |
| `throttling.rttMs` | 150 | Default mobile RTT. |
| `throttling.throughputKbps` | 1638.4 (down) / 750 (up) | Default mobile bandwidth — comparable to 4G in poor conditions. |
| `throttlingMethod` | `simulate` | Lighthouse simulates the throttling on the trace rather than enforcing it at the network layer (more reproducible). |
| `skipAudits` | `is-on-https`, `redirects-http`, `uses-http2`, `uses-long-cache-ttl`, `canonical` | These audits fail by design on `127.0.0.1:8000` (no TLS, no CDN, no canonical absolute URL). They are checked at production-edge by other gates. |

These are the official Lighthouse mobile-preset defaults; the runner
does not invent custom numbers.

---

## 7. Thresholds

From `lighthouserc.mobile.json::ci.assert.assertions`:

| Category | Min | Worst score in baseline | Headroom |
|---|---|---|---|
| performance | 0.75 | 0.79 (`/ar/`) | 4 points |
| accessibility | 0.90 | 0.96 (multiple) | 6 points |
| best-practices | 0.90 | 1.00 (all URLs) | 10 points |
| seo | 0.90 | 1.00 (all URLs) | 10 points |

### Why perf >= 0.75 (and not 0.80 like desktop)

The 2026-05-11 baseline shows mobile performance ranging from 0.79
(`/ar/`) to 0.93 (`/privacy/`, `/disclaimer/`, `/case-types/`). The
delta is real:

- Arabic landing has an RTL stylesheet swap and font fallback that
  costs ~5 perf points under mobile throttling;
- the homepage carries a hero image / Pexels references that the
  CPU-throttled trace amortises poorly.

Setting the floor at 0.80 (matching desktop) would put `/ar/` 1 point
above the line — a single run-to-run jitter could turn it red. A
0.75 floor gives the worst URL 4 points of margin while still
catching a real regression (a 10-point perf drop would still cross
the line on every page).

### Why a11y / best / seo stay at 0.90

These categories are deterministic — they don't move with
throttling. The mobile baseline shows 0.96–1.00 across the board,
identical to desktop. Keeping the floor at 0.90 makes the mobile
budget consistent with desktop on the categories that should be.

### When to re-tune

If a Studio-approved visible change (e.g. a new hero photo, a
content section, an i18n stylesheet refactor) legitimately drops a
score by more than the headroom:

1. Discuss before re-baselining — never silently tighten a budget
   downward.
2. Refresh the baseline (`--update-baseline`).
3. Lower the threshold in `lighthouserc.mobile.json` by exactly the
   minimum needed to clear the new worst score, plus a small margin
   matching the per-category jitter (~0.05 for `perf`, ~0.01 for
   the others).
4. Update this runbook's table in §7.
5. Commit the JSON + the threshold change in the same PR.

Don't silence categories. Don't comment out URLs. The desktop
runbook (`LIGHTHOUSE_CI.md` §4) lists the same anti-patterns for the
same reason.

---

## 8. Reading a mobile report

`docs/qa/lighthouse-mobile-baseline/<label>-mobile.json` is the full
Lighthouse output. Same shape as the desktop reports, with mobile
emulation in the `configSettings` block:

```bash
# Quick categories summary
python -c "
import json
d = json.load(open('docs/qa/lighthouse-mobile-baseline/home-it-mobile.json', encoding='utf-8'))
for k, c in d['categories'].items():
    print(f'{k}: {c[\"score\"]}')
"

# Mobile-specific audits with score < 1.0 (where the throttled trace is dragging us)
python -c "
import json
d = json.load(open('docs/qa/lighthouse-mobile-baseline/home-it-mobile.json', encoding='utf-8'))
for k, a in d['audits'].items():
    if a.get('score') is not None and a['score'] < 1.0:
        print(f'{a[\"score\"]:.2f}  {k}  {a[\"title\"]}')
" | sort
```

To open the HTML variant in a browser:

```
npx --yes lighthouse@latest http://127.0.0.1:8000/ \
  --output=html --output-path=/tmp/home-mobile.html \
  --form-factor=mobile \
  --screenEmulation.mobile=true --screenEmulation.width=390 \
  --screenEmulation.height=844 \
  --throttling.cpuSlowdownMultiplier=4 \
  --quiet
start /tmp/home-mobile.html       # on Windows
```

---

## 9. What to do when the mobile gate fails

The procedure mirrors the desktop runbook (`LIGHTHOUSE_CI.md` §6):

1. **Read the failing URL's report.** The runner prints the failing
   category and the score. Open the corresponding JSON (or HTML
   variant from §8) and find audits with `score < 1.0`.
2. **Identify the regression source.** Common mobile-only culprits:
   - render-blocking CSS / fonts (perf — much worse under
     CPU throttling than desktop);
   - large images without `srcset` or below-the-fold lazy-loading
     (perf, best-practices);
   - tap targets too small / too close on the 390-wide viewport
     (a11y — does not fail at desktop widths);
   - meta-viewport missing or wrong (seo — `seo / has-viewport-meta`);
   - low contrast in the dark hero band (a11y — slightly stricter
     on mobile due to glare assumptions).
3. **Fix the underlying issue, not the gate.** If the regression is
   intentional, discuss with the Studio before re-baselining.
4. **Re-run the gate** (`bash scripts/run_lighthouse_mobile_local.sh`).
   When all URLs clear, commit the new JSON reports via the
   `--update-baseline` workflow in §11.

---

## 10. Variance and stability

Mobile Lighthouse runs are noisier than desktop. Sources of run-to-run
jitter we've measured:

- CPU contention with other processes on the dev box can shift `perf`
  by ±0.03 even at idle.
- The simulated 3G network model is deterministic given a fixed
  trace, but the trace itself depends on when the browser hits each
  request — which depends on real-world wall-clock ordering on the
  first page load.
- Cold cache (first run after `runserver` reload) typically scores
  3–5 perf points lower than the second run.

Mitigations:

- **One run per URL is enough for the baseline.** Running 3× and
  averaging would hide a real regression behind the noise — the
  worst-case score is the one we want to gate.
- **Don't re-run to chase a green.** If the first run fails, do not
  re-run hoping for jitter to clear it. Open the report and fix.
- **Warm cache before capture.** When refreshing the baseline,
  serve the URL once manually (e.g. `curl http://127.0.0.1:8000/`)
  before running the mobile gate — that matches what real users see
  after their first visit.

---

## 11. Refreshing the mobile baseline

Same shape as the desktop refresh (`LIGHTHOUSE_CI.md` §8):

```
# 1. Make sure the dev server is running with the new code.
# 2. Refresh the baseline (writes tracked docs/qa/lighthouse-mobile-baseline/).
bash scripts/run_lighthouse_mobile_local.sh --update-baseline
# or:  pwsh scripts/run_lighthouse_mobile_local.ps1 -UpdateBaseline

# 3. Inspect the diff:
git diff docs/qa/lighthouse-mobile-baseline/

# 4. Update docs/qa/lighthouse-mobile-baseline/SUMMARY.md to match
#    the new numbers (per-URL table + worst-score-vs-threshold).
# 5. If a threshold change is needed, also update
#    lighthouserc.mobile.json AND §7 of this runbook.
# 6. Commit JSON + SUMMARY.md + (optional) threshold change.
```

The baseline lives in git for the same reason as desktop: a future
regression can be diff'd against a known-good snapshot. The default
runner mode (without `--update-baseline`) writes only to
`artifacts/lighthouse-mobile/latest/` which is gitignored.

---

## 12. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `ERROR: Django is not responding on http://127.0.0.1:8000/` | Dev server not running. | Open a second terminal, `python manage.py runserver 127.0.0.1:8000`, re-run. |
| `EPERM, Permission denied … lighthouse.XXXX` on Windows | chrome-launcher temp-dir cleanup race. | Benign — the JSON report is fully written before the cleanup attempt. The runner tolerates it. |
| `perf` on the same URL drops 5 points between two runs with no code change | Mobile throttling jitter (see §10). | Don't re-run to chase green. Investigate the failing audit in the JSON. |
| `seo / has-viewport-meta` audit fails | Page-level `<meta name="viewport">` removed or malformed. | Check the page template. The base template carries it; any page-level override must keep it. |
| `accessibility / tap-targets` audit fails on mobile but passes on desktop | Tap targets under 48×48 px or too close at 390-wide viewport. | Tighten button/link spacing or sizing on the mobile breakpoint. The desktop gate cannot catch this. |
| Mobile gate passes locally but fails on a different dev box | CPU contention differs. The 0.75 perf floor accounts for some of this, but a very weak host (single-core VM) can fall below. | Run on a machine with at least 4 physical cores. CI runners typically clear the gate comfortably; local devs sometimes need to close other heavyweight apps before running. |

---

## 13. CI integration

Same outline as desktop (`LIGHTHOUSE_CI.md` §7). When the GitHub
Actions workflow lands, the mobile gate is added as a second
`lighthouse` job — not a second step in the desktop job — so the two
audits run in parallel and the timeline doesn't lengthen.

```yaml
# Mobile audit job — outline, not committed yet.
jobs:
  lhci-mobile:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: pip install -r requirements.txt
      - run: python manage.py migrate
      - run: nohup python manage.py runserver 127.0.0.1:8000 &
      - run: sleep 5
      - run: bash scripts/run_lighthouse_mobile_local.sh
```

---

## 14. Relationship with other docs

- `docs/qa/LIGHTHOUSE_CI.md` — desktop preset (companion).
- `docs/qa/LOCAL_QUALITY_GATE.md` — consolidated 4-stage gate; this
  runbook covers the optional 5th stage activated by
  `--mobile-lighthouse`.
- `docs/qa/lighthouse-mobile-baseline/SUMMARY.md` — the captured
  baseline numbers themselves (per-URL table). This runbook explains
  *how to use, refresh, and reason about* that baseline; the SUMMARY
  is the data.
