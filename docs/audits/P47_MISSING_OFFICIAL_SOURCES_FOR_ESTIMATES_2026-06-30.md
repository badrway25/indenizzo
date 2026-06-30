# P47 — Missing official sources for estimates (honest gap map)

_Date: 2026-06-30 · Phase P47, Fase K. For the team, not the public. What is
missing, per country × category, to enable a fast, simple, **honest** monetary
estimate. Grounded in the live engines (`run_simulation`) and the P40/P44/P45
audits + the validation packs. **No source or number is invented.**_

## What actually estimates today (verified)
Only **Italy** produces a real figure: road accident, danno biologico, medical
liability. Every other (country, category) returns
`unavailable_requires_legal_validation`.

Legend — **Active?** = a real figure is produced today · **Priority** = effort/value
to unlock (high/medium/low).

## Italy
| Category | Active? | Official source available | What's missing | Risk if computed now | Next step | Priority |
|---|---|---|---|---|---|---|
| Road accident | **yes** | CAP art.139 + TUN D.P.R.12/2025 (approved) | — | — | maintain | — |
| Danno biologico | **yes** (via road/medical) | TUN + art.139 | — | — | maintain | — |
| Medical liability | **yes** | L.24/2017 → art.138/139 | — | — | keep "tabular only" disclaimer | — |
| Insurance offer | **yes** (comparison) | CAP/TUN vs road estimate | — | — | maintain | — |
| Work injury (INAIL) | no | D.M.45/2019 + D.M.12/07/2000 (real, not imported) | the menomazione%×età indemnity table transcribed/verified; canary | **high** — would publish numbers from an un-imported table | validate table → dataset → engine + canary | **high** |
| Loss of a relative | no | artt.2043/2059 c.c. (no statutory table) | nothing importable (Milano = court practice, non-binding) | high — non-binding figures presented as official | stays guided | low |
| Defective product | no | Cod. Consumo 114-127 | **no statutory monetary formula exists** | high | stays guided (responsibility/documents only) | low |
| Inheritance | no | C.C. Libro II (not catalogued) | catalogue C.C.; build deterministic legittima/quota engine | medium | quotas are fractions (low fabrication risk) | medium |
| Cross-border | no | Roma II / Reg.650 (conflict-of-laws) | n/a — no tariff by design | low | route to IT engine when IT law applies | low |

## Morocco
| Category | Active? | Source available | What's missing | Risk now | Next step | Priority |
|---|---|---|---|---|---|---|
| Road accident | no | Dahir 1-84-177 (scanned, binding) | OCR + verbatim capital-de-référence barème, AIPP/responsibility method, canary | **high** | validate Dahir → engine + canary | **high** |
| Danno biologico | no | embedded in Dahir road method | AIPP coefficients verified (same barème) | high | bundle with road | medium |
| Medical liability | no | none (D.O.C. only) | a quantum basis (none exists) | high | expert-driven; stays guided | low |
| Insurance offer | no | Code des assurances (procedural) | a validated MA road baseline | high | downstream of road barème | medium |
| Work injury | no | none (CNSS/Loi 18-12 not catalogued) | identify + catalogue the regime | high | research | low |
| Loss of a relative | no | Dahir ayants-droit (road death only) | verbatim shares (same barème); non-road has no table | high | bundle with road; general loss stays guided | medium |
| Defective product | no | none | a statutory quantum (none) | high | guided | low |
| Inheritance | no | Moudawana faraïd (binding, needs_review) | approve source + complete faraïd model (hajb/'awl/radd) + estate value + canary | medium | promote source + finish model | medium |
| Cross-border | no | Roma II / Reg.650 | n/a (non-EU; framing only) | low | applicable-law framing | low |

## Tunisia
| Category | Active? | Source available | What's missing | Risk now | Next step | Priority |
|---|---|---|---|---|---|---|
| Road accident | no | Code des assurances Titre V (binding) | transcription + validation of the barème; canary | medium | transcribe Titre V → engine + canary | **high** |
| Danno biologico | no | Titre V taux d'incapacité | extracted scale + capitalisation coefficients | medium | reuse TN road engine | medium |
| Medical liability | no | none | a quantum source (none) | high | stays guided | low |
| Insurance offer | no | Code des assurances + CGA | a validated TN road baseline | medium | activate road first | medium |
| Work injury | no | none (Loi 94-28 not catalogued) | catalogue the statute | high | research | low |
| Loss of a relative | no | Titre V décès/ayants-droit (binding) | verbatim distribution; canary | medium | extract onto TN road engine | medium |
| Defective product | no | none | a statutory quantum (none) | high | guided | low |
| Inheritance | no | CSP Livre IX (needs_review) | legal review + faraïd shares + conflict-of-laws tree + canary | high | Studio review | medium |
| Cross-border | no | Reg.650 / Roma II / Loi 98-97 | n/a (framing only) | low | applicable-law framing | low |

## France / Belgium
| Category | Active? | Source available | What's missing | Risk now | Next step | Priority |
|---|---|---|---|---|---|---|
| FR road / biologico / loss | no | **no binding State barème** — only Mornet / Gazette / Nomenclature Dintilhac (non-binding) | a State table (does not exist) | **high** — non-binding practice presented as official | **cannot promise an automatic official estimate**; a figure needs a Studio policy decision to adopt a non-binding référentiel with disclaimers | low |
| BE road / biologico / loss | no | only the non-binding Tableau Indicatif | a binding State table (does not exist) | high | keep guided (P11/BELGIUM_FINAL); same policy caveat as FR | low |
| FR/BE medical · offer · work · product · inheritance · cross-border | no | mostly none / framing only | a catalogued, validated source | high | guided / applicable-law | low |

## EU / cross-border
Roma II (864/2007) and Reg.650/2012 are binding but **conflict-of-laws only** — they
designate which national law applies, never an amount. **No EU-level estimate is
possible by design.** Every cell is `Active? = no`; the only path is to route to a
validated national engine (today, only the IT engines) once applicable law is set.

## Summary of priorities
- **High:** INAIL (IT) · Morocco road (Dahir) · Tunisia road (Titre V) — real
  binding State sources exist; they only need validation/extraction + a canary.
- **Medium:** MA/TN family loss (within the road barèmes) · MA/TN inheritance
  (faraïd) · IT inheritance (legittima).
- **Low (no automatic estimate possible):** France/Belgium road (no State barème),
  defective product (no statutory quantum), all medical/work outside Italy,
  cross-border (framing only).

**Nothing here is `ready_for_engine`.** Until the legal team fills a validation
pack (`docs/legal_validation/`) to that state, the public keeps the documental
check / summary / applicable-law paths — never an invented number.
