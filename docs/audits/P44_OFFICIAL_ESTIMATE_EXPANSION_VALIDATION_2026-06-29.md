# P44 — Official Estimate Expansion: Validation Workstream

_Date: 2026-06-29 · Phase P44, Fase L/M. Builds on the P40 masterplan
(`P40_OFFICIAL_ESTIMATE_EXPANSION_MASTERPLAN`). Re-verified against the live
engines on the current public DB. **No source, table or number is invented.**_

## Live re-verification (run_simulation, public DB, 2026-06-29)
Unchanged since P40 — only two pairs return a real figure:

| Pair | Status | Figure |
|------|--------|--------|
| IT road accident | `calculated` | **yes** |
| IT medical liability | `calculated` | **yes** |
| IT inheritance, FR road, BE road, MA inheritance, TN inheritance | `unavailable_requires_legal_validation` | no |

Italy danno biologico is reachable through the road/medical wizards (same
approved tables). All other pairs fail closed.

## Per-country × category validation (what would unlock an engine)

Columns: **Src** = official source found · **Link** = official PDF/link ·
**Tbl** = table/formula present · **Extract** = reliable extraction today ·
**Canary** = a canary tuple is possible from validated values · **Now** = engine
possible now · **Next** = next action.

### Italy
| Category | Src | Tbl | Extract | Canary | Now | Next |
|---|---|---|---|---|---|---|
| Road accident | CAP 139 + TUN DPR 12/2025 | yes | yes (approved) | yes (live) | **yes** | maintain |
| Danno biologico | TUN + art.139 | yes | yes | yes | **yes** (via road/medical) | optional dedicated entry |
| Medical liability | L.24/2017 → art.138/139 | yes | yes | yes | **yes** | keep tabular-only disclaimer |
| Insurance offer | CAP/TUN (vs road estimate) | yes | yes | yes | **yes** (comparison) | maintain |
| Work injury (INAIL) | DM 45/2019 + DLgs 38/2000 | partial | **no** (not in DB, not machine-extractable) | no | no | legal-validate the INAIL indemnity table → import dataset → engine + canary |
| Loss of a relative | artt. 2043/2059 c.c. | no (Milano = court practice) | n/a | no | no | guided only; Milano tables never a public auto-number |
| Defective product | Cod. Consumo 114-127 | no | n/a | no | no | no statutory quantum → guided |
| Inheritance | C.C. Libro II (not catalogued) | no | n/a | no | no | catalogue C.C. successioni → deterministic legittima/quota engine |
| Cross-border | Roma II / Reg. 650 | no (conflict-of-laws) | n/a | no | no | applicable-law framing → route to IT engine |

### Morocco / Tunisia / France / Belgium / EU
Summarised (full per-cell detail in the P40 masterplan):
- **MA road / danno biologico / loss:** Dahir 1-84-177 barème is binding but
  **scanned (OCR needed), multifactorial, `approval_needed`** → no extraction, no
  engine. ACAPS guide is non-binding.
- **MA inheritance:** Moudawana faraïd engine registered but source `needs_review`
  and the faraïd model incomplete (hajb/'awl/radd) → fails closed.
- **TN road / biologico / loss / offer:** Code des assurances Titre V is binding
  but **not transcribed/validated**; hosts unreachable during extraction → no engine.
- **TN inheritance:** CSP Livre IX `needs_review`; conflict-of-laws tree absent.
- **FR road / biologico / loss / offer:** **no binding State barème exists** — only
  non-binding Mornet / Gazette du Palais / Nomenclature Dintilhac. Activating
  them is a Studio legal-policy decision, not a developer one.
- **BE road / biologico / loss:** only the non-binding Tableau Indicatif; the
  registered engine fails closed.
- **MA/TN/FR/BE medical · product · work injury:** mostly no catalogued source;
  expert/in-concreto valuation, no statutory quantum table.
- **EU / cross-border (all categories):** Roma II + Reg. 650 are conflict-of-laws
  only — **no EU-level amount is possible by design**; route to a validated
  national engine once applicable law is determined.

## Fase M decision — no new engine activated
No candidate meets the bar (complete + validated + state-binding source +
extractable + canary). Activating any would mean publishing numbers from
unvalidated or non-binding sources — forbidden. The public UX instead keeps the
documental check / summary / applicable-law paths, and the documentation hub now
explains in plain words **why some cases show no amount** (new mini-FAQ entry).

### Priority order when legal validation arrives (unchanged from P40)
1. INAIL biological-damage (IT) — a real State table exists.
2. Tunisia road (Titre V) — binding, needs transcription + canary.
3. Morocco road (Dahir) — binding, needs OCR + method validation.
4. MA/TN inheritance — complete faraïd model + approve sources.
5. IT inheritance (legittima) — deterministic quotas, low fabrication risk.
6. FR/BE road — only after a Studio policy decision on non-binding référentiels.

## Guardrail
`apps/core/test_p40.py::test_only_italy_shows_estimate_available_in_matrix` and
`::test_gated_pairs_do_not_estimate_on_public_db` run the live engines and fail
CI if the matrix ever promises a figure an engine cannot produce. P44 keeps them
green.
