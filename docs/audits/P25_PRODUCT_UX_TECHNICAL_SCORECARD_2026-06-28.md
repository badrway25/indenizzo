# P25 — Product UX / Technical Scorecard

Date: 2026-06-28 · Branch: `feature/p3-public-ux-redesign` · Baseline: P24 (3009 passed)

Scores are 1–5 (1 = weak, 5 = professional). Columns:
**Fn** functional value · **Cl** user clarity · **An** analytical quality ·
**Lg** legal/professional · **Gr** graphic/premium · **Mo** mobile · **Rt** RTL ·
**Ct** CTA/funnel · **Tr** trust/sources · **Pm** premium feel.

`→` marks the score after the P25 changes in this branch.

| Page | Fn | Cl | An | Lg | Gr | Mo | Rt | Ct | Tr | Pm |
|------|----|----|----|----|----|----|----|----|----|----|
| home | 4 | 4 | 3 | 4 | 4→5 | 4 | 4 | 4 | 4 | 4→5 |
| services | 4 | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| guided router | 3→5 | 3→5 | 2→4 | 4 | 4→5 | 4 | 4 | 3→5 | 4→5 | 4 |
| countries hub | 4 | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| Morocco / Tunisia | 4 | 4 | 3 | 4 | 4→5 | 4 | 4 | 4 | 4 | 4 |
| France / Belgium | 3 | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| case-types hub | 4 | 4 | 3 | 4 | 4 | 4 | 4 | 4 | 4 | 4 |
| INAIL pre-check | 3→5 | 3→5 | 2→5 | 4→5 | 3→5 | 4 | 4 | 3→5 | 4→5 | 3→5 |
| loss-relative pre-check | 3→5 | 3→5 | 2→5 | 4→5 | 3→5 | 4 | 4 | 3→5 | 4 | 3→5 |
| Morocco pre-check | 3→5 | 3→5 | 2→5 | 4→5 | 3→5 | 4 | 4 | 3→4 | 5 | 3→5 |
| Tunisia pre-check | 3→5 | 3→5 | 2→5 | 4→5 | 3→5 | 4 | 4 | 3→4 | 5 | 3→5 |
| international pre-check | 3→5 | 3→5 | 2→5 | 5 | 3→5 | 4 | 4 | 3→4 | 5 | 3→5 |
| pre-check RESULT | 2→5 | 2→5 | 1→5 | 4→5 | 2→5 | 4 | 4 | 2→5 | 4→5 | 2→5 |
| road estimate result | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 5 | 4 |
| medical result | 4 | 4 | 4 | 5 | 4 | 4 | 4 | 4 | 5 | 4 |
| offer result | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 5 | 4 |

## Concrete problems → fixes

### P0 — pre-check result was a flat readiness bar (lowest scores)
- **Problem:** one progress bar + a list of missing docs + a single CTA. No
  explanation of what was evaluated, what is solid, what is missing, why the path
  applies, what could be estimated, or how solid the dossier is. Reads as a form
  echo, not an analysis.
- **Fix (done):** `precheck_engine.PreCheckResult` extended with a top-line
  `result_status` + summary, `strong_points` / `attention_points`, `path_reason`,
  `assessable_now` / `pending_for_estimate`, a categorised `document_items`
  checklist (essential / useful / optional, each with a purpose), and a secondary
  CTA. `precheck.html` result section redesigned into an analytical report shell.
- **Files:** `apps/core/precheck_engine.py`, `templates/public/precheck.html`.

### P0 — pre-checks were not "intelligent" enough per category
- **Problem:** generic guidance regardless of the answers.
- **Fix (done):** per-flow signal analysis — INAIL grade bands (6–15 capital,
  >15 annuity, third-party → differential secondary action); MA/TN barème
  readiness from incapacity + income + liability; loss-of-relative parental
  framing with foreign re-routing to applicable-law. No invented amounts.
- **Files:** `apps/core/precheck_engine.py`.

### P1 — guided router read as an index, not a cockpit
- **Problem:** cards showed only a badge + a one-line hint.
- **Fix (done):** pre-click preview per route — data required, main official
  source (`§`), and an honest non-monetary time band — plus the existing
  path/estimate framing.
- **Files:** `apps/core/guided_router.py`, `templates/public/guided_router.html`.

### P1 — premium feel / composition
- **Fix (done):** the pre-check result is now a stack of premium cards (status
  hero, solid/attention split, legal-path panel, categorised checklist, CTA
  group) with `premium-rise` entrance; guided cards carry a structured preview.
- **Pending (lower priority):** richer art-direction on services / case-types /
  countries hubs (already premium from P22–P24; not blocking).

### Technical
- **Fixed:** a `_` shadowing bug in `_eval_international` that would have 500'd
  the international pre-check (caught by the new tests).
- Centralised: status/labels stay in `precheck_engine`, `guided_router`,
  `public_status`, `public_labels` — no new hardcoded duplication.

## Guardrails honoured
No invented amounts/tables/sources. No money on engine-less flows. No slug / weak
states / "in revisione" / "placeholder". No inline styles, no external CDN.
IT/FR/AR translated, 0 fuzzy. Mobile + RTL routes 200.
