# Validation pack — Morocco road injury

**Country · category:** MA · road_accident (dommage corporel)
**Status:** `needs_legal_review`
**Public behaviour today:** "needs the official table first" → documental path (no amount).

## Official source(s)
- **Dahir n° 1-84-177 (1984)** — barème d'indemnisation des dommages corporels
  (accidents de la circulation): capital-de-référence, AIPP, ayants-droit.
- **Code des assurances** (ACAPS) — claims procedure.
- ACAPS guide "Indemnisation automobile corporelle" — **non-binding** administrative practice.
- Registry ids: `ma-dahir-1-84-177`, `ma-code-assurances`, `ma-acaps-guide`.

## Official URL / access
- SGG: https://www.sgg.gov.ma · ACAPS: https://www.acaps.ma
- **Dahir 1984 PDF:** scanned image, no text layer (OCR required). Archived hash on file.
- ACAPS guide PDF: text-extractable but **not a State table**.

## Table / formula present
- **Partial / binding but unusable today.** The Dahir barème is the binding State
  source but it is a **scanned image, multifactorial** (revenu de référence ×
  coefficient d'âge × taux d'AIPP, plus pretium doloris / préjudice esthétique
  bands), status `approval_needed`. The ACAPS guide is non-binding and must not be
  presented as a State table.

## Required inputs (for a future engine)
- revenu / SMIG de référence, âge, taux d'AIPP (%), part de responsabilité,
  pretium doloris, préjudice esthétique, frais médicaux/transport. Currency: MAD.

## Canary example (to be provided by the legal reviewer)
```
input:  { revenu_ref: __, age: __, aipp_pct: __, responsabilite_pct: __ }
expected_indemnite: __ MAD
source: "Dahir 1-84-177, barème capital-de-référence, ligne __"
```
_(Empty until a verbatim Bulletin Officiel row is transcribed. No invented value.)_

## Blockers before `ready_for_engine`
1. OCR + Bulletin Officiel verification of the Dahir barème (verbatim).
2. Legal confirmation of the capital-de-référence × age-coefficient × AIPP method
   and the responsibility apportionment.
3. The wizard must collect income / responsibility / AIPP (not collected today).
4. Flip `ma-dahir-1-84-177` to usable_for_engine only after legal sign-off.

## Next action
Legal validation of the Dahir capital-de-référence barème → fill the canary →
build a fail-closed `morocco_road_injury` engine (MAD) + canary; never use the
non-binding ACAPS guide as the quantum basis.
