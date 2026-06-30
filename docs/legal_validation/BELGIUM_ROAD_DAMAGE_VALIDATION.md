# Validation pack — Belgium road accident bodily injury

**Country · category:** BE · road_accident_bodily_injury
**Status:** `not_calculable` (no binding State barème)
**Public behaviour today:** documental check + applicable-law framing (no amount).

## Official source(s)
- **Loi du 21 novembre 1989** (assurance R.C. véhicules automoteurs) —
  compulsory-insurance framework, **not a quantum table**.
- **Tableau Indicatif** (Indicatieve Tabel) — a **non-binding** guideline issued
  by magistrates' associations, explicitly *not* State law.

## Official URL / access
- economie.fgov.be: https://economie.fgov.be (Loi 1989) — **HTTP 200**.

## Table / formula present
- **No binding State barème.** Belgian personal-injury amounts come from the
  **non-binding** Tableau Indicatif + judicial assessment. It must **not** drive
  an automatic "official" estimate.

## Harvest probe (P50, 2026-06-30)
- `economie.fgov.be` → **HTTP 200** (the 1989 law is reachable) — but the law is
  a framework, **not** an amount table; the Tableau Indicatif is non-binding.

## Canary example
_Not applicable — no binding official table to anchor a canary to._

## Blockers before `ready_for_engine`
- A **binding State barème** would have to exist. It does not. Same policy caveat
  as France: adopting the Tableau Indicatif is a Studio decision with non-binding
  disclaimers, not an official estimate.

## Next action
**Keep guided** — documents + applicable-law. Do **not** promise an automatic
official Belgian estimate.
