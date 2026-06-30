# P25 — Estimate-expansion review (pre-check data ↔ engine gap)

Date: 2026-06-28. Companion to `CHATGPT_APPROVAL_QUEUE_2026-06-26.md` (the source
decisions) and `CALCULATOR_ENGINE_EXPANSION_AUDIT_2026-06-25.md`. This file maps
what each pre-check ALREADY collects to what an approved engine would still need,
so the gap is precise. No amount is shown publicly until the queue row is APPROVED
and a canary is green. Nothing here invents tables, coefficients or figures.

For each flow: **collected** = fields the visitor already provides in the P16/P25
pre-check form; **missing for engine** = the validated table/coefficients still
required; **canary** = the official worked example needed to gate the engine.

---

## 1) INAIL — work injury (`inail`) → EUR

- **Collected** (precheck `inail`): event date, age, impairment %, INAIL
  recognised (y/n), benefit received (y/n), medical-legal cert (y/n), employer/
  INAIL docs (y/n), third-party/employer liability (y/n).
- **Engine target**: `inail_biological_damage_capital` (capital indemnity, grade
  6–15%) and the annuity path (>15%).
- **Missing for engine**: the **grado × età capital-value table** (D.M. 12/07/2000
  values, Det. Pres. INAIL 2/2019 + D.M. 45/2019, revalued 01/07/2025) in
  machine-readable form — see queue §3. The downloaded "Allegato 5" is the MOD
  16/TER heirs form, not the value table.
- **Already sufficient from the form**: impairment % + age → the two table axes;
  the band logic (6–15 capital, >15 annuity) is implemented in the pre-check.
- **Canary required**: one official grade×age capital value (2025 revaluation) to
  fail-closed the engine. Gender unification to be confirmed.

## 2) Morocco — road accident (`morocco-road-accident`) → MAD

- **Collected** (precheck `morocco-road-accident`): injury/death, event date,
  place, vehicle insured (y/n/unknown), liability estimate (full/partial/none),
  IPP known (y/n), income documentable (y/n), heirs (if death), police report
  (y/n), medical cert (y/n).
- **Engine target**: `morocco_road_injury_bareme` —
  `capital_de_référence(âge, salaire) × taux_incapacité × taux_responsabilité`.
- **Missing for engine**: the **capital-de-référence base table** (âge × salaire →
  MAD) from the scanned Dahir 1984 annex (queue §1). Complementary + ayants-droit
  percentages already extracted reliably.
- **Already sufficient from the form**: IPP (taux d'incapacité) + liability
  (taux de responsabilité) + documentable income (salaire) → all three engine
  inputs are captured; only the base table is missing.
- **Canary required**: `346 500 × 20% × 50% = 34 650 MAD` (ACAPS p. 11) — already
  identified; needs the base table to reproduce.

## 3) Tunisia — road accident (`tunisia-road-accident`) → TND

- **Collected** (precheck `tunisia-road-accident`): injury/death, event date,
  insurer identified (y/n), IPP known (y/n), income documentable (y/n), heirs (if
  death), police report (y/n), medical cert (y/n).
- **Engine target**: `tunisia_road_injury_bareme` — Code des assurances Titre V
  (art. 110–179) barème, binding ±15%.
- **Missing for engine**: the **barème itself** (revenu de référence, coefficient
  par âge/capitalisation, taux d'incapacité, décès/ayants droit). Both official
  hosts unreachable from this environment (queue §2) — needs owner-provided text.
- **Already sufficient from the form**: IPP + income + insurer → the inputs the
  barème consumes; only the table is missing.
- **Canary required**: one official worked example from Titre V.

## 4) Loss of a relative (`loss-of-relative`) → no state table (confirmed)

- **Collected**: country, cause of death, relationship, cohabitation, victim/
  family age, liability established (y/n), offer received (y/n), civil docs (y/n).
- **Engine target**: NONE for a state table. Italian loss-of-relationship damage
  (artt. 2043, 2059 c.c.) has **no statutory barème**; courts use judicial
  practice (e.g. Milan/Rome tables) which are **case-law practice, not an official
  state source** — out of scope for an approved public numeric engine.
- **Decision**: keep as a guided/documental pre-check (no figure). The pre-check
  now frames the parental claim, the relationship and the established liability,
  and routes foreign cases to applicable-law framing. **Do not** wire a numeric
  engine from judicial-practice tables.

---

## Summary — what unlocks each engine

| Flow | Inputs captured | Missing artefact | Canary | Queue ref |
|------|-----------------|------------------|--------|-----------|
| INAIL | impairment %, age | grado×età capital table (2025) | 1 official value | §3 |
| Morocco | IPP, liability, income | capital-de-référence base table | 34 650 MAD | §1 |
| Tunisia | IPP, income, insurer | Code assurances Titre V barème | 1 Titre V example | §2 |
| Loss-relative | relationship, liability | — (no state table) | — | n/a |

All three numeric candidates are **input-complete on the visitor side** — the only
blocker is the validated official table, exactly as tracked in the approval queue.
No public euro/MAD/TND figure is shown until APPROVED + canary green.
