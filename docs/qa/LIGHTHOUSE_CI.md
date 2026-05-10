# Lighthouse CI — runbook

**Iter**: F-p1-seo-2-lighthouse-ci-gating
**Date**: 2026-05-10

This runbook explains how to gate the platform's public pages
against a Lighthouse quality budget (performance, accessibility,
best-practices, SEO).

The companion files are:

- `lighthouserc.json` — the URLs and thresholds.
- `scripts/run_lighthouse_local.sh` — bash gate runner.
- `scripts/run_lighthouse_local.ps1` — PowerShell gate runner.
- `docs/qa/lighthouse-baseline/` — committed baseline JSON
  reports + `SUMMARY.md`.

The Studio does not need to run Lighthouse manually; the runbook
exists so any developer can reproduce the audit before merging a
visual / front-end change.

---

## 1. Prerequisites

- Python venv with the project requirements installed (Django).
- Node.js + npm installed locally. The project does not commit a
  `package.json`; the runner uses `npx` on demand.
- Chromium (Lighthouse downloads its own headless Chrome on first
  run via `chrome-launcher`).
- The dev server reachable on `http://127.0.0.1:8000/`.

The runner refuses to start if the dev server is not already
responding on `127.0.0.1:8000` — that is intentional: starting and
killing `manage.py runserver` from the same script races on Windows
and leaves orphan processes.

---

## 2. Run the gate locally

```
# Terminal A — Django
source .venv/Scripts/activate           # or `. .venv\Scripts\Activate.ps1`
python manage.py runserver 127.0.0.1:8000

# Terminal B — gate
bash scripts/run_lighthouse_local.sh    # bash / Git Bash / WSL
# or
pwsh scripts/run_lighthouse_local.ps1   # PowerShell
```

The script runs `npx lighthouse@latest` against each URL listed in
`lighthouserc.json::ci.collect.url`, writes one JSON report per URL
into `docs/qa/lighthouse-baseline/`, and exits non-zero if any
score is below the gating threshold.

Optional: native LHCI autorun (single command, but EPERMs on
Windows during cleanup):

```
npx --yes @lhci/cli@0.14.x autorun --config=lighthouserc.json
```

The bash / PowerShell wrappers are the recommended path on Windows
because they tolerate the chrome-launcher cleanup race.

---

## 3. URLs gated

Defined in `lighthouserc.json::ci.collect.url`. Current set:

| URL | Why it is gated |
|---|---|
| `/` | landing page |
| `/contact/` | indexable institutional page |
| `/wizard/` | hub page (the concrete forms below are noindex) |
| `/privacy/` | versioned legal page |
| `/disclaimer/` | versioned legal page |
| `/countries/` | hub for the 5 country landings |
| `/case-types/` | hub for case types |
| `/ar/` | RTL home — guards regression on Arabic UI |

URLs deliberately **not** gated:

- `/wizard/it/road-accident/` and the 4 sibling wizards —
  `noindex, nofollow` by design (private funnels). Lighthouse
  always scores `noindex` low on SEO.
- `/wizard/result/<uuid>/` — parametric, post-submit, also
  `noindex`.
- `/contact/thank-you/` — post-submit, also `noindex`.
- `/admin/`, `/staff/` — non-public surface.
- Country landings `/countries/<slug>/` — already covered by the
  `/countries/` hub gate; adding all 5 would 5x the runtime and the
  hub catches any global regression.

---

## 4. Thresholds

| Category | Min |
|---|---|
| performance | 0.80 |
| accessibility | 0.90 |
| best-practices | 0.90 |
| seo | 0.90 |

Rationale: the 2026-05-10 baseline (committed in
`docs/qa/lighthouse-baseline/`) clears every threshold by a comfortable
margin (perf 0.99-1.00, a11y 0.96-0.97, best 1.00, seo 1.00 — except
the noindex pages we exclude). Tightening to e.g. perf>=0.95 would
flag any content-heavy refresh; this batch picks budget over
oscillation.

When a regression is real and intended (e.g. adding a hero photo
that legitimately drops perf to 0.92), the workflow is:

1. Discuss with the Studio before re-baseling.
2. Edit the threshold in `lighthouserc.json`.
3. Re-run `bash scripts/run_lighthouse_local.sh`.
4. Commit the updated JSON reports + the threshold change in the
   same PR, with a note explaining why.

Don't silence categories. Don't comment out URLs. Both leave the
gate weaker than it looks.

---

## 5. Reading a report

`docs/qa/lighthouse-baseline/<label>-desktop.json` is the full
Lighthouse output. Easy ways to inspect:

```bash
# Quick categories summary
python -c "
import json
d = json.load(open('docs/qa/lighthouse-baseline/home-it-desktop.json', encoding='utf-8'))
for k, c in d['categories'].items():
    print(f'{k}: {c[\"score\"]}')
"

# Audits with score < 1.0 (i.e. potential improvements)
python -c "
import json
d = json.load(open('docs/qa/lighthouse-baseline/home-it-desktop.json', encoding='utf-8'))
for k, a in d['audits'].items():
    if a.get('score') is not None and a['score'] < 1.0:
        print(f'{a[\"score\"]:.2f}  {k}  {a[\"title\"]}')
" | sort
```

To open the HTML report in a browser, regenerate with `--output=html`:

```
npx --yes lighthouse@latest http://127.0.0.1:8000/ \
  --output=html --output-path=/tmp/home.html --preset=desktop --quiet
start /tmp/home.html       # on Windows
```

---

## 6. What to do when the gate fails

1. **Read the failing URL's report.** The script prints the failing
   category and the score. Open the corresponding JSON (or the HTML
   variant from §5) and find the audits with `score < 1.0`.
2. **Identify the regression source.** The most common culprits in
   this codebase:
   - new third-party CDN (loosens CSP + adds DNS round-trips);
   - inline styles without nonce (CSP best-practices);
   - missing `alt`, missing `<label>`, low contrast (a11y);
   - new `<a>` without descriptive text or with `target=_blank` and
     no `rel=noopener` (best-practices, SEO).
3. **Fix the underlying issue, not the gate.** If a new feature
   genuinely lowers a score, discuss with the Studio before
   re-baselining.
4. **Re-run the gate.** When all URLs clear, commit the new JSON
   reports.

---

## 7. CI integration

This batch ships the gate as a local-runnable + reproducible script,
not an automated GitHub Actions workflow. Wiring it to CI is a
follow-up (P1-CI-* family) that depends on the team's CI choice. The
recipe is simple: spin up Postgres + Redis + Django in a container,
run the gate against `127.0.0.1:8000`, fail the job on non-zero exit.

Example GitHub Actions outline (not committed yet):

```yaml
name: Lighthouse gate
on: [pull_request]
jobs:
  lhci:
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
      - run: npx --yes @lhci/cli@0.14.x autorun --config=lighthouserc.json
```

When this hits CI, the chrome-launcher EPERM goes away (Linux is
fine with the temp-dir cleanup); on Windows runners we fall back to
`bash scripts/run_lighthouse_local.sh`.

---

## 8. Refreshing the baseline

Whenever the Studio approves a visible change that legitimately
moves the scores:

```
# 1. Make sure the dev server is running with the new code.
# 2. Drop the existing baseline so we don't keep stale JSON.
rm -f docs/qa/lighthouse-baseline/*-desktop.json

# 3. Re-run the gate — it both fails-fast and writes the JSON.
bash scripts/run_lighthouse_local.sh

# 4. Update the SUMMARY.md table to match the new numbers.
# 5. Commit the JSON + SUMMARY.md + (if needed) the threshold tweak.
```

The baseline lives in git intentionally: it lets a future regression
be diff'd against a known-good snapshot.
