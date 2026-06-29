# Validation pack — Tunisia road injury

**Country · category:** TN · road_accident (dommage corporel)
**Status:** `needs_legal_review`
**Public behaviour today:** "needs the official table first" → documental path (no amount).

## Official source(s)
- **Code des assurances, Titre V (art. 110-179)** — barème d'indemnisation
  (revenu de référence, coefficient de capitalisation par âge, taux d'incapacité,
  distribution décès/ayants-droit). Binding State source.
- **Loi 2005-86** — related framework.
- Registry ids: `tn-code-assurances`, `tn-loi-2005-86`.

## Official URL / access
- CGA: https://www.cga.gov.tn · IORT: https://www.iort.gov.tn
- **Hosts were unreachable during automated extraction** (cga.gov.tn http=000,
  legislation.tn ECONNREFUSED). No PDF archived yet; obtain a verbatim copy.

## Table / formula present
- **Partial / binding but not transcribed.** Titre V is the binding barème but it
  has not been transcribed/validated into the project; no APPROVED dataset/formula.

## Required inputs (for a future engine)
- revenu de référence (floor/ceiling), âge (capitalisation coefficient),
  taux d'incapacité (IPP %), part de responsabilité. Currency: TND.

## Canary example (to be provided by the legal reviewer)
```
input:  { revenu_ref: __, age: __, ipp_pct: __ }
expected_indemnite: __ TND
source: "Code des assurances, Titre V, art. __, coefficient __"
```
_(Empty until a verbatim Titre V worked example is transcribed. No invented value.)_

## Blockers before `ready_for_engine`
1. Obtain + archive a verbatim copy of Code des assurances Titre V (hash).
2. Transcribe the taux d'incapacité scale + capitalisation coefficients +
   revenu-de-référence floors/ceilings.
3. One official worked example for the canary.

## Next action
This is the **lowest-friction** non-IT candidate (binding State barème, just needs
transcription). Validate Titre V → fill the canary → build a fail-closed
`tunisia_road_injury` engine (TND) + canary.
