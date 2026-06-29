# Validation pack — Tunisia loss of a relative

**Country · category:** TN · loss_of_relative (décès, ayants-droit)
**Status:** `needs_legal_review`
**Public behaviour today:** documental path (no amount).

## Official source(s)
- **Code des assurances, Titre V** — décès / ayants-droit distribution
  (percentages × revenu de référence × coefficient d'âge) for road deaths.
- **Loi 2005-86** — framework.
- D.O.C. (COC) — general civil liability for non-road parental loss (no quantum table).
- Registry ids: `tn-code-assurances`, `tn-loi-2005-86`, `tn-doc`.

## Official URL / access
- CGA: https://www.cga.gov.tn · IORT: https://www.iort.gov.tn
- Same access constraints as the Tunisia road pack (no PDF archived yet).

## Table / formula present
- **Partial, only for road deaths.** The décès/ayants-droit distribution is binding
  inside Titre V but not transcribed. Non-road parental loss has no quantum table.

## Required inputs (for a future engine, road death only)
- revenu de référence, âge des ayants droit, lien de parenté, nombre d'ayants droit.

## Canary example (to be provided by the legal reviewer)
```
input:  { revenu_ref: __, lien: "conjoint", n_ayants_droit: __ }
expected_part: __ TND
source: "Code des assurances, Titre V, distribution décès, art. __"
```
_(Empty until verbatim shares are transcribed. No invented value.)_

## Blockers before `ready_for_engine`
1. Validate the Titre V décès/ayants-droit distribution (bundle with the Tunisia
   road validation).
2. Scope: only road deaths are table-based; general parental loss stays guided.

## Next action
Bundle with the Tunisia road validation (share the Titre V transcription). General
(non-road) parental loss is `not_calculable` and remains a documental/guided path.
