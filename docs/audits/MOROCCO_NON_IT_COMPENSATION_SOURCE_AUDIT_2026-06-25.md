# Morocco & non-IT compensation sources — audit

**Phase**: P6 · 2026-06-25. Answers "which official source governs *damages* (not
family law) in MA / FR / BE / TN, and is there an official *computable* barème?"
Grounded in the live `LegalSource` DB + the registry. Official portals only.

## Morocco — the Moudawana misuse question (explicit)

**Finding: the platform does NOT misuse the Moudawana as a damages engine.**

- DB: `Code de la famille marocain (Moudawana) — Loi n°70-03` is **approved**,
  and the registered MA calculator is `MoroccoInternationalInheritanceCalculator`
  for `case_type=international_inheritance`. The Moudawana is used **only** for
  family/inheritance status (marriage, filiation, shares) — its correct domain —
  and even there the calculator is a **placeholder** (returns unavailable, no
  automatic share computation without an applicable-law mapping). It is **never**
  used to compute road-accident / bodily-injury damages.
- **Correct source for civil liability / bodily-injury damages in Morocco** =
  the **Dahir du 12 août 1913 formant Code des Obligations et des Contrats
  (DOC/COC marocain)**, responsabilité civile (≈ arts. 77–106) — NOT the
  Moudawana. For motor accidents: the compulsory motor-insurance regime +
  **ACAPS** (Autorité de Contrôle des Assurances et de la Prévoyance Sociale)
  supervision. Work injury: the accidents-du-travail legislation.
- **Is there an official *computable* Moroccan barème for bodily-injury
  damages?** Not confirmed as an official, ministry-level, computable table.
  Moroccan damage quantification is largely **judicial/expertise-based**, not a
  published national tariff like the Italian TUN.
- **What to search (official portals):** `sgg.gov.ma` (Bulletin Officiel — DOC,
  insurance & accident-du-travail laws), `adala.justice.gov.ma` /
  `justice.gov.ma` (codes), `acaps.ma` (insurance barèmes/circulaires, if any).
- **Verdict:** **no damages engine.** Keep MA fail-closed with an assisted
  pathway; cite the DOC (responsabilité civile) as the governing source, NOT the
  Moudawana, for any *damages* copy. (Inheritance copy may correctly cite the
  Moudawana.)

## France

- DB: **Loi n°85-677 (Badinter)** `approved` — this is the *liability* statute for
  road accidents, not a quantification tariff. The quantification references —
  **Nomenclature Dintilhac**, **Référentiel Mornet 2024**, **Barème de
  capitalisation Gazette du Palais** — are catalogued `needs_review`/`draft`.
- **Computable official barème?** No. Dintilhac is a *nomenclature* (heads of
  loss), Mornet and the Gazette du Palais are **practitioner référentiels**, not
  official government tariffs. French quantification is judge-led.
- **Verdict:** **no damages engine** (the FR candidate datasets are `draft` in DB
  → engine inert). Fail-closed. To build one, France would need an official
  government tariff, which does not exist in the Italian-TUN sense.

## Belgium

- DB: **Loi du 21/11/1989** (assurance auto obligatoire) `approved`; **Tableau
  Indicatif 2020/2024** + **Tables Schryvers** `needs_review`/`draft`.
- **Computable official barème?** The *Tableau Indicatif* is exactly what its name
  says — *indicative*, produced by the magistrates'/lawyers' associations, **not
  an official ministry tariff**. It is loaded `draft` and never approved.
- **Verdict:** **no damages engine.** Fail-closed (BE candidate dataset is
  `draft`). Correct.

## Tunisia

- DB: **Code du statut personnel (CSP)** + **Code de droit international privé
  (CDIP)** `approved` — used by `TunisiaInternationalInheritanceCalculator`
  (inheritance/applicable-law), a placeholder. These are personal-status /
  PIL codes, **not** damages tariffs.
- **Correct source for damages** = the **Code des Obligations et des Contrats
  tunisien (COC)**, responsabilité civile — not the CSP. No official computable
  bodily-injury tariff confirmed.
- **What to search:** `iort.gov.tn` (JORT / Imprimerie Officielle), official code
  portals.
- **Verdict:** **no damages engine.** Inheritance uses the CSP correctly
  (placeholder, fail-closed). Damages fail-closed with an assisted pathway citing
  the COC.

## Summary

| Country | Damages governing source (official) | Computable official barème? | Engine |
|---|---|---|---|
| MA | Dahir 1913 (DOC) — NOT the Moudawana | no | none (assisted) |
| FR | Loi Badinter (liability) | no (Dintilhac/Mornet = référentiels) | none (assisted) |
| BE | Loi 1989 | no (Tableau Indicatif = indicative) | none (assisted) |
| TN | COC tunisien — NOT the CSP | no | none (assisted) |

All four stay **fail-closed**: their candidate datasets are `draft`, never
`approved`, so the engines are inert — which is the correct, honest behaviour.
The only place the Moudawana / CSP are used is **inheritance** (their correct
domain), and even there only as placeholders pending an applicable-law mapping.
