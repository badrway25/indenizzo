# Validation pack — Morocco loss of a relative

**Country · category:** MA · loss_of_relative (décès, ayants-droit)
**Status:** `needs_legal_review`
**Public behaviour today:** documental path (no amount).

## Official source(s)
- **Dahir n° 1-84-177 (1984)** — the ayants-droit indemnity shares for a road
  **death** live inside the same road-accident barème (capital de référence ×
  distribution par lien de parenté).
- D.O.C. (Code des obligations et des contrats) — general civil-liability basis
  for non-road parental loss (no quantum table).
- Registry ids: `ma-dahir-1-84-177`, `ma-doc`.

## Official URL / access
- SGG: https://www.sgg.gov.ma · ACAPS: https://www.acaps.ma
- Same scanned Dahir PDF as the road pack (OCR required).

## Table / formula present
- **Partial, only for road deaths.** The ayants-droit distribution percentages are
  in the (unvalidated, scanned) Dahir road-death barème. **Non-road** parental loss
  has **no quantum table** — assessed in concreto under the D.O.C.

## Required inputs (for a future engine, road death only)
- lien de parenté, ayants droit, revenu du défunt, part de responsabilité.

## Canary example (to be provided by the legal reviewer)
```
input:  { revenu_defunt: __, lien: "conjoint", n_ayants_droit: __ }
expected_part: __ MAD
source: "Dahir 1-84-177, distribution ayants-droit, ligne __"
```
_(Empty until verbatim shares are transcribed. No invented value.)_

## Blockers before `ready_for_engine`
1. Validate the ayants-droit distribution within the Dahir road-death barème
   (same validation as the Morocco road pack — do them together).
2. **Scope clearly:** only road-accident deaths are table-based; general parental
   loss stays a guided path (no figure).

## Next action
Bundle with the Morocco road validation. General (non-road) parental loss is
`not_calculable` and remains a documental/guided path.
