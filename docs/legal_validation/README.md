# Official estimate validation packs

_Phase P45 (2026-06-29). A formal hand-off structure between the legal team and
engineering. A monetary engine is built **only** when a pack reaches
`ready_for_engine`. Nothing here invents a number._

## How a pack becomes an engine
1. The legal team fills the pack: official source, URL, hash (if downloaded),
   the verbatim table/formula, the required inputs, and at least one
   **legally-reviewed worked example** (the canary).
2. Engineering imports the source as an APPROVED `LegalSource` + `CompensationDataset`
   + `CalculationFormula`, builds a fail-closed engine, and wires the canary.
3. The public matrix and source library flip to "estimate available" for that
   (country, category) — never before.

## Status vocabulary (internal only — never shown to the public)
- `ready_for_engine` — validated source + table/formula + canary example. Build now.
- `needs_official_table` — no usable official table/formula exists yet.
- `needs_legal_review` — a real official instrument exists but is not yet legally
  validated / extracted / transcribed.
- `needs_formula` — an official table exists but the computation method
  (coefficients/age/responsibility rules) is not yet fixed.
- `needs_canary` — source + formula are ready, but no legally-reviewed worked
  example exists yet to lock the engine against.
- `not_calculable` — the law gives no computable quantum (assessed case-by-case).

## Current candidates

| Pack | Country · category | Status | One-line reason |
|------|--------------------|--------|-----------------|
| [INAIL_WORK_INJURY_VALIDATION](INAIL_WORK_INJURY_VALIDATION.md) | IT · work injury | `needs_legal_review` | Official INAIL indemnity tables exist (D.M. 12/07/2000 + D.M. 45/2019) but are not transcribed/validated/imported. |
| [MOROCCO_ROAD_DAMAGE_VALIDATION](MOROCCO_ROAD_DAMAGE_VALIDATION.md) | MA · road injury | `needs_legal_review` | Dahir 1-84-177 barème is binding but scanned (OCR), multifactorial, not validated. |
| [TUNISIA_ROAD_DAMAGE_VALIDATION](TUNISIA_ROAD_DAMAGE_VALIDATION.md) | TN · road injury | `needs_legal_review` | Code des assurances Titre V barème is binding but not transcribed/validated. |
| [MOROCCO_FAMILY_LOSS_VALIDATION](MOROCCO_FAMILY_LOSS_VALIDATION.md) | MA · loss of a relative | `needs_legal_review` | Ayants-droit shares live only inside the same unvalidated Dahir road-death barème. |
| [TUNISIA_FAMILY_LOSS_VALIDATION](TUNISIA_FAMILY_LOSS_VALIDATION.md) | TN · loss of a relative | `needs_legal_review` | Titre V décès/ayants-droit distribution is binding but not transcribed. |
| [PRODUCT_LIABILITY_VALIDATION](PRODUCT_LIABILITY_VALIDATION.md) | IT/EU · defective product | `not_calculable` | Cod. Consumo 114–127 + Dir. 85/374 define liability, not a monetary quantum. |
| [FRANCE_ROAD_DAMAGE_VALIDATION](FRANCE_ROAD_DAMAGE_VALIDATION.md) | FR · road injury | `not_calculable` | No binding State barème; only the non-binding Mornet/Dintilhac practice. |
| [BELGIUM_ROAD_DAMAGE_VALIDATION](BELGIUM_ROAD_DAMAGE_VALIDATION.md) | BE · road injury | `not_calculable` | No binding State barème; only the non-binding Tableau Indicatif. |

**No pack is `ready_for_engine` today → no new engine is activated (P45 → P50).**
Priority when validation arrives: INAIL → TN road → MA road → family loss.
`not_calculable` packs (product liability, FR/BE road) will **never** become an
estimate unless official law itself introduces a binding quantum table.

## P50 harvest note (2026-06-30)
A controlled, allowlisted reachability probe (`manage.py harvest_official_sources`)
confirmed several official **landing pages** are reachable (normattiva, acaps,
sgg, cga, economie.fgov.be, eur-lex = 200/202; inail SSL-error, iort
connection-error, legifrance 403). **Reaching a domain is not validating a
table** — every binding barème lives in a sub-page/PDF (often a scanned image) and
none was extracted or transcribed. All statuses are unchanged; **no engine is
activated**. The probe writes only a gitignored provenance manifest.
