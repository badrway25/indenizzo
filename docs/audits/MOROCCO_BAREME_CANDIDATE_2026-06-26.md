# Morocco road-injury barème — candidate dataset (Dahir 1984)

Date: 2026-06-26 · Section: Marocco — incidenti stradali (#9) · Currency: **MAD**.

Extracted from the **official ACAPS thematic guide** (text layer, reliable — NOT
OCR), SHA256 `b4d6f9e8b2c61f70…`. The Dahir 1-84-177 itself is a scanned image
(SHA256 `39c78a4cc8a88c34…`, no text layer); the **capital-de-référence base
table** lives in its annex and remains the only missing piece (OCR rasterization
is unavailable in this environment: no pdftoppm/gs/fitz; tesseract is eng-only).

## Formula (official, ACAPS guide pp. 9–11)

```
Indemnité principale = capital_de_référence(âge, salaire) × taux_incapacité × taux_responsabilité
```

- `capital_de_référence`: fixed by the Dahir, table by **age at accident** and
  **salaire / gains professionnels**. *(MISSING — scanned Dahir annex.)*
- Salary rules: gérant/exploitant → assimilation; student/no income → SMIG
  multiples **1.5× / 2× / 3×** (secondaire / sup. 1er-2e cycle / sup. 3e cycle).

### Canary (official worked example, ACAPS p. 11)

```
âge 40, revenu annuel 54 000 → capital_de_référence = 346 500 MAD
Indemnité principale = 346 500 × 20% × 50% = 34 650 MAD
```

## Extracted official coefficients (candidate — ACAPS guide pp. 13–16)

All as **% of the capital de référence**, source page noted.

| head | sub-level | coeff | page |
|---|---|---|---|
| Incapacité permanente (principale) | obligatoire | (formula above) | 13 |
| Pretium doloris | assez important | 5% | 13 |
| Pretium doloris | important | 7% | 13 |
| Pretium doloris | très important | 10% | 13 |
| Préjudice esthétique (avec conséquences carrière) | assez imp. / imp. / très imp. | 5% / 10% / 15% | 13 |
| Préjudice esthétique (sans conséquences carrière) | assez imp. / imp. / très imp. | 25% / 30% / 35% | 13 |
| Incapacité — mise anticipée à la retraite | — | 20% | 14 |
| Incapacité — perte aptitude à l'avancement | — | 15% | 14 |
| Incapacité — perte travaux supplémentaires | — | 10% | 14 |
| Interruption scolarité | définitive / quasi définitive | 25% / 15% | 14 |
| Ayant droit — conjoint | (pluralité: réparti) | 25% | 15 |
| Ayant droit — descendant ≤5e année | (30% pour certains) | 25% | 15 |
| Ayant droit — descendant 6e–10e | — | 20% | 15 |
| Ayant droit — descendant 11e–16e | — | 15% | 15 |
| Ayant droit — descendant ≥17 ans | — | 10% | 15 |
| Ayant droit — ascendant (chacun) | père / mère | 10% | 15 |
| Ayant droit — autres / à charge | — | 10% / 15% | 15–16 |

Death distribution worked example (guide p. 17) totals **100% → 173 250 MAD**
for a capital de référence, consistent with conjoint 25% + descendants + ascendants.

## What is verified vs missing

- **Verified (text-extracted, reliable):** the formula, all complementary/ayants-droit
  percentages above, the salary rules, and the official canary 34 650 MAD.
- **Missing (scanned Dahir annex, OCR-blocked):** the `capital_de_référence(âge,
  salaire)` base table. Only one point is known: (40, 54 000) → 346 500.

## Engine readiness

`morocco_road_injury_bareme` (MA-NATIONAL, MAD) is **specifiable now** but stays
a fail-closed candidate and is **NOT exposed publicly** until the
capital-de-référence base table is supplied/validated and the 34 650 MAD canary
is green. See `docs/audits/CHATGPT_APPROVAL_QUEUE_2026-06-26.md`.
