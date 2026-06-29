# P40 — Official Estimate Expansion Masterplan

_Date: 2026-06-29 · Phase P40, Fase K/L. Grounded in the live repository: the
engine registry, `apps/core/official_sources.py`, the existing source/validation
audits, and a `run_simulation` check against the current public DB. **No source,
table, coefficient or number is invented in this document.**_

## 0. Executive summary — what the platform can really estimate today

A `run_simulation` probe of every "estimate" cell on the current public DB
(2026-06-29) returned a real monetary figure for **exactly two** pairs:

| Pair | `run_simulation` status | Figure? |
|------|------------------------|---------|
| IT · road accident (`road_accident_bodily_injury`) | `calculated` | **yes** |
| IT · medical liability (`medical_liability_biological_damage`) | `calculated` | **yes** |
| IT · inheritance (`inheritance_basic`) | `unavailable_requires_legal_validation` | no |
| FR · road accident | `unavailable_requires_legal_validation` | no |
| BE · road accident | `unavailable_requires_legal_validation` | no |
| MA · inheritance (`international_inheritance`) | `unavailable_requires_legal_validation` | no |
| TN · inheritance (`international_inheritance`) | `unavailable_requires_legal_validation` | no |

Italy's danno biologico is obtainable through the road and medical wizards (same
approved TUN-2025 / art.139 tables), so it is a third user-reachable estimate.

**Consequence (Fase L correction).** The public "Cosa puoi fare, paese per
paese" matrix previously labelled **FR road, BE road, IT/MA/TN inheritance** as
"Estimate available". They are not — the engines are registered but **fail
closed** to legal review on the public DB. The matrix has been corrected so only
IT road / danno biologico / medical show "Estimate available"; FR/BE road now
show "Needs the official table first" and the inheritance cells show "Check your
documents". This removes a real over-statement and honours the cardinal rule
(*meglio nessun calcolo che un calcolo falso*).

## 1. Method
- **Active engines (ground truth):** `list_available_calculators()` returns 8
  registered pairs (IT road/microlesion/medical/inheritance, FR road, BE road,
  MA/TN international_inheritance). *Registered ≠ produces a public figure*: five
  of these gate to `unavailable_requires_legal_validation` because no APPROVED
  `LegalSource` + `CompensationDataset` + `CalculationFormula` exists for them on
  the public DB.
- **Adversarial verification.** Each "can estimate now = yes" claim was
  re-checked by an independent agent against the registry and the engine wiring.
  Of 5 claims, **2 survived** (IT road, IT medical); **3 were refuted**
  (IT biological_damage and IT insurance_offer are not standalone engine keys —
  danno biologico and offer comparison are computed *inside* the road/medical
  flows; MA inheritance is fixture-only and gates to review on the public DB).
- **Source quality scale:** `state_binding` (a State table/formula with the force
  of law) · `non_binding_practice` (insurer/court indicative tables, e.g. ACAPS,
  CGA, Belgian Tableau Indicatif, French Mornet/Gazette du Palais) ·
  `needs_legal_review` (a real instrument not yet legally validated/extracted) ·
  `none`.

## 2. Per-country × category audit (6 × 9)

Legend — **Now?** = produces a real public figure today.

### Italy
| Category | Official source | Table/formula | Quality | Engine | Now? | Next step |
|---|---|---|---|---|---|---|
| Road accident | CAP art.139 (D.Lgs 209/2005) + TUN D.P.R. 12/2025 | yes | state_binding | yes | **yes** | Maintain; optionally fold the MIMIT uplift coefficients (needs legal validation) |
| Danno biologico | TUN macro + art.139 micro | yes | state_binding | via road/medical | **yes** | Optional dedicated entry point reusing art.138/139 |
| Medical liability | L. 24/2017 (Gelli) → art.138/139 | yes | state_binding | yes | **yes** | Keep "tabular biological damage only" scope disclaimer |
| Insurance offer | CAP + TUN (compared against the road estimate) | yes | state_binding | via road | **yes** (comparison) | Maintain; it rides the approved road tables |
| Work injury (INAIL) | T.U. 1124/1965, D.Lgs 38/2000, D.M. 45/2019 | partial | needs_legal_review | no | no | Legal-validate the INAIL indemnity table → import dataset → build engine + canary |
| Loss of a relative | artt. 2043/2059 c.c. (Milano tables = court practice) | no | non_binding_practice | no | no | Stays guided; Milano tables can only ever be an internal reference, never a public auto-number |
| Defective product | Cod. Consumo artt. 114-127 | no | needs_legal_review | no | no | No statutory quantum table exists → stays guided |
| Inheritance | Codice Civile Libro II (not yet catalogued) | no | none | placeholder | no | Catalogue C.C. successioni + build a deterministic legittima/quota engine (fractions, lower risk than a barème) |
| Cross-border | Roma II / Reg. 650/2012 | no | state_binding (conflict-of-laws) | no | no | Applicable-law framing → route to IT engine when IT law applies |

### Morocco
| Category | Official source | Table/formula | Quality | Engine | Now? | Next step |
|---|---|---|---|---|---|---|
| Road accident | Dahir 1-84-177 (1984) + ACAPS guide + Code des assurances | partial (scanned, OCR) | needs_legal_review | no | no | Legal-validate the Dahir capital-de-référence barème + AIPP/liability method (P37 queue) |
| Danno biologico | embedded in the Dahir/ACAPS road method | partial | needs_legal_review | no | no | Validate AIPP coefficients within the road barème |
| Medical liability | none (D.O.C. general civil liability only) | no | none | no | no | Expert-driven; stays guided |
| Insurance offer | Code des assurances + ACAPS | no | needs_legal_review | no | no | Downstream of a validated MA road barème |
| Work injury | none (INAIL is Italian; CNSS/Loi 18-12 not catalogued) | no | none | no | no | Identify + catalogue the MA accidents-du-travail regime |
| Loss of a relative | Dahir ayants-droit (road death only) | partial | needs_legal_review | no | no | Validate ayants-droit shares within the road-death barème |
| Defective product | none | no | none | no | no | Stays guided (no statutory quantum) |
| Inheritance | Moudawana (Loi 70-03), faraïd | partial | state_binding | registered, **gated** | no | Approve `ma-moudawana`, complete the faraïd model (hajb/'awl/radd), require estate_value, add canary |
| Cross-border | Roma II + Reg. 650/2012 | no | needs_legal_review | no | no | Applicable-law framing only (MA is non-EU) |

### Tunisia
| Category | Official source | Table/formula | Quality | Engine | Now? | Next step |
|---|---|---|---|---|---|---|
| Road accident | Code des assurances Titre V (art. 110-179) + Loi 2005-86 | partial (not transcribed) | state_binding | no | no | Transcribe + validate Titre V barème → build `tunisia_road_injury` engine (TND, fail-closed) + canary |
| Danno biologico | Titre V taux d'incapacité | partial | state_binding | no | no | Extract incapacity scale + capitalisation coefficients; reuse the TN road engine |
| Medical liability | none | no | none | no | no | No catalogued source; stays guided |
| Insurance offer | Code des assurances + CGA | partial | state_binding | no | no | Activate the TN road barème first, then add comparison |
| Work injury | none (Loi 94-28 not catalogued) | no | none | no | no | Catalogue the TN accident-du-travail statute |
| Loss of a relative | Titre V décès/ayants-droit | partial | state_binding | no | no | Extract the death/ayants-droit distribution onto the TN road engine |
| Defective product | none | no | none | no | no | Stays guided |
| Inheritance | CSP Livre IX (faraïd) + Loi 98-97 (CDIP) | partial | needs_legal_review | registered, **gated** | no | Legal review of CSP Livre IX → transcribe shares + conflict-of-laws tree → approve + canary |
| Cross-border | Reg. 650/2012 + Roma II + Loi 98-97 | no | state_binding (conflict-of-laws) | no | no | Applicable-law framing only |

### France
| Category | Official source | Table/formula | Quality | Engine | Now? | Next step |
|---|---|---|---|---|---|---|
| Road accident | Loi Badinter 85-677 + Code des assurances | no (no state barème) | non_binding_practice | registered, **gated** | no | Badinter gives the *right*, not the *amount*; a figure needs a legal-policy decision to adopt a non-binding référentiel (Mornet/Gazette) with disclaimers, then validate |
| Danno biologico | Nomenclature Dintilhac (classification) + Mornet (non-binding) | no | non_binding_practice | no | no | Same policy decision as road DFP |
| Medical liability | none (Loi Kouchner / ONIAM not catalogued) | no | none | no | no | Add a guided FR medical path; no state barème exists |
| Insurance offer | Code des assurances (offer procedure) | no | non_binding_practice | no | no | Procedure check only; needs an FR quantum engine first |
| Work injury | none (CSS AT/MP not catalogued) | no | none | no | no | Out of current FR scope |
| Loss of a relative | Mornet affection bands (non-binding, DRAFT) | no | non_binding_practice | no | no | Guided; needs a policy decision + validation |
| Defective product | none (Code civil 1245 ss.) | no | none | no | no | Guided (no tariff) |
| Inheritance | Code civil réserve héréditaire (not catalogued) | no | none | no | no | Most plausible next FR engine: clean statutory quota computation, mirror IT legittima |
| Cross-border | Roma II + Reg. 650/2012 | no | state_binding (conflict-of-laws) | no | no | Applicable-law framing → route to a national engine |

### Belgium
| Category | Official source | Table/formula | Quality | Engine | Now? | Next step |
|---|---|---|---|---|---|---|
| Road accident | Loi 21/11/1989 + Tableau Indicatif 2024 | partial (scanned, non-binding) | non_binding_practice | registered, **gated** | no | No binding State barème; Tableau Indicatif is indicative only. P11/BELGIUM_FINAL recommend keeping the guided path. Reconcile the optimistic P36 "validated" note with the fail-closed reality |
| Danno biologico | subsumed in road (Code civil, in concreto) | partial | non_binding_practice | no | no | Guided |
| Medical liability | none (Loi 31/03/2010 / FAM not catalogued) | no | none | no | no | Guided if in scope |
| Insurance offer | Loi 1989 (context only) | no | needs_legal_review | no | no | Needs a validated BE estimate first |
| Work injury | none (Loi 10/04/1971 / Fedris not catalogued) | no | none | no | no | Research + source if in scope |
| Loss of a relative | Tableau Indicatif décès/affection (non-binding) | partial | non_binding_practice | no | no | Guided |
| Defective product | none (Loi 25/02/1991) | no | none | no | no | Guided |
| Inheritance | Code civil quotas (not catalogued); Reg. 650/2012 | no | needs_legal_review | no | no | Applicable-law framing; build a BE quota engine to estimate |
| Cross-border | Roma II + Reg. 650/2012 | no | needs_legal_review | no | no | Applicable-law framing only |

### EU / Cross-border
Roma II (864/2007) and Reg. 650/2012 are **binding** but are conflict-of-laws
instruments: they designate *which national law applies*, never a monetary
amount. **No EU-level estimate is possible by design.** Every cross-border cell
is `can_estimate_now = false`; the roadmap is a legally-reviewed routing layer
that, once applicable law is determined, invokes an already-validated *national*
engine (today only the IT engines). Never publish an EU-level number.

## 3. Fase L — engine activation decision

**No new monetary engine is activated in P40.** Every candidate fails the bar
"complete, validated, state-binding source + canary":

- **INAIL (IT):** the indemnity/menomazione tables are not in the DB and not
  reliably machine-extractable; status `needs_legal_review`. Requires a
  legally-verified verbatim table before any euro figure.
- **Morocco road (Dahir 1-84-177):** the barème lives in a scanned image (OCR),
  is multifactorial, and is `approval_needed` — not legally validated.
- **Tunisia road (Code des assurances Titre V):** binding but not transcribed/
  validated; official hosts were unreachable during extraction.
- **Morocco / Tunisia inheritance:** faraïd engines are registered but the
  sources (`ma-moudawana`, CSP Livre IX) are `needs_review`, and the faraïd model
  is explicitly incomplete (hajb/'awl/radd). They fail closed publicly.
- **France / Belgium road:** **no binding State barème exists.** The only
  references are non-binding practitioner/court tables (Mornet, Gazette du
  Palais, Tableau Indicatif). Activating them is a *legal-policy* decision for the
  Studio, not a developer decision.

Activating any of these now would mean publishing numbers from sources that are
unvalidated or non-binding — forbidden. The platform instead keeps the
documental pre-check / dossier path and, in P40, makes the public matrix tell
the truth about where a figure is and is not available.

### Recommended priority order (when legal validation is available)
1. **INAIL biological-damage** (IT) — a real State table exists; highest user value.
2. **Tunisia road (Titre V)** — binding State barème, just needs transcription + canary.
3. **Morocco road (Dahir)** — binding but OCR + liability-method validation needed.
4. **Morocco / Tunisia inheritance** — complete the faraïd model + approve sources.
5. **IT inheritance (legittima)** — deterministic quotas, low fabrication risk.
6. France / Belgium road — only after a Studio policy decision on non-binding référentiels.

## 4. Guardrail
A new test (`apps/core/test_p40.py::test_matrix_estimate_cells_are_truly_calculable`)
runs the live engines for every matrix cell marked "Estimate available" and
asserts each returns `calculated`. The matrix can no longer drift ahead of the
engines without failing CI.
