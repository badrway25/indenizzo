# Validation pack — France road accident bodily injury

**Country · category:** FR · road_accident_bodily_injury
**Status:** `not_calculable` (no binding State barème)
**Public behaviour today:** documental check + applicable-law framing (no amount).

## Official source(s)
- **Loi Badinter n° 85-677** — victim-compensation framework (liability/right to
  compensation), **not a quantum table**.
- **Nomenclature Dintilhac** — heads of damage (a *list*, not amounts).
- Non-binding practice references: *Référentiel Mornet*, court *référentiels*,
  ONIAM tables — **orientation only, not State-mandated amounts.**

## Official URL / access
- Légifrance: https://www.legifrance.gouv.fr (Loi 85-677) — **HTTP 403** for
  non-browser agents (blocks automated fetch; not bypassed).

## Table / formula present
- **No binding State barème exists.** France compensates personal injury by
  judicial assessment per the Dintilhac heads; the amounts come from non-binding
  référentiels and case law, which **must not** drive an automatic "official"
  estimate.

## Harvest probe (P50, 2026-06-30)
- `legifrance.gouv.fr` → **HTTP 403** (blocks bots; respected, not bypassed).
- Even if reachable, there is **nothing to extract**: no statutory amount table.

## Canary example
_Not applicable — no binding official table to anchor a canary to._

## Blockers before `ready_for_engine`
- A **binding State barème** would have to exist. It does not. Adopting a
  non-binding référentiel as if official is a **policy decision for the Studio**,
  not an engineering one, and would require prominent "non-binding practice"
  disclaimers — it is not an official estimate.

## Next action
**Keep guided** — documents + "which law may apply." Do **not** promise an
automatic official French estimate.
