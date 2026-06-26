# Approval pack — Morocco road-injury barème (Dahir 1984)

Date: 2026-06-26 · Section: Marocco — incidenti stradali (#9) · Target state:
`numeric_estimate_approved` (today `official_guided_path_approved`).

## Decision requested

Validate the **capital de référence** table (by age + income) annexed to the
Dahir so the candidate engine `morocco_road_injury_bareme` can be built. The
**formula is fully known and computable**; only the official age/income table
is missing in machine-readable form (the Dahir PDF is a scanned image).

## Official sources (verified reachable, downloaded, hashed — kept out of repo)

- **Dahir n° 1-84-177 du 2 octobre 1984** (indemnisation des victimes
  d'accidents causés par des véhicules terrestres à moteur).
  - ACAPS copy: `.../publication_documents/dahir_1984_indemn_acc_de_circulation.pdf`
  - SHA256 prefix `39c78a4cc8a88c34…` · **scanned image PDF (0 text layer) →
    needs OCR + legal validation of the annexed tables.**
- **ACAPS — Guide thématique « Indemnisation des victimes d'accidents »**
  - `.../acaps_guide_dahir_version_fr_version_finale.pdf`
  - SHA256 prefix `b4d6f9e8b2c61f70…` · text layer present (24 pages, 7 tables).
- Also relevant: ACAPS « Indemnisation automobile corporelle » ; Code des
  assurances ; Code des obligations et des contrats.

## What was extracted (verified from the ACAPS guide text)

The official method (guide, p. 11):

```
Indemnité principale = Capital de référence(âge, salaire) × taux d'incapacité × taux de responsabilité
```

- **Capital de référence**: *« fixé par le Dahir (tableau prenant compte de
  l'âge de la victime ainsi que de son salaire) »* — i.e. an official table in
  the Dahir annex.
- **Taux d'incapacité (IPP)**: fixed by the medical expert.
- **Taux de responsabilité**: from the procès-verbal.
- Complementary heads (pretium doloris, préjudice esthétique) = capital de
  référence (montant minimum) × taux × responsabilité.
- Minimum reference based on SMIG; multipliers for students (1.5× / 2× / 3×).

### Official worked example (use as CANARY)

> Victime née en 1983 (40 ans), revenu annuel 54 000 Dhs →
> **capital de référence = 346 500 Dhs** (selon le tableau annexé au Dahir).
> IPP 20%, responsabilité 50% →
> **Indemnité principale = 346 500 × 20% × 50% = 34 650 Dhs.**

This single point (age 40, income 54 000 → 346 500) is verifiable; the **full
age/income table** is what is missing.

## Exact data needed

The **capital de référence** table from the Dahir annex:
`rows = (age_band, income_band or income_multiple, capital_de_reference_DHS)`,
plus the SMIG floor/ceiling rules and the pretium-doloris minimum reference.

### Expected format (CSV/JSON → CompensationTableRow)

```
row_type=ma_capital_reference   age_min, age_max, income_min, income_max, point_value(DHS)
row_type=ma_smig_floor          point_value(DHS)
```

## Expected engine

`morocco_road_injury_bareme` (jurisdiction MA-NATIONAL): inputs revenu annuel,
âge, taux d'incapacité (IPP), taux de responsabilité (+ optional pretium
doloris / esthétique). Output in **MAD**, fail-closed until the table is
imported and the 34 650 Dhs canary is green. **Not exposed publicly** until
validated. Moudawana must NOT be used for bodily-damage computation.

## Precise question for ChatGPT

> Fornisci la tabella ufficiale del **capital de référence** allegata al Dahir
> 1-84-177 (per fascia d'età e di reddito/salario), inclusi minimo SMIG e regola
> del pretium doloris. Conferma che, per età 40 e reddito 54 000 Dhs, il capital
> de référence è 346 500 Dhs (esempio ACAPS). Indica fonte/pagina per riga.

## Risks

- Dahir tables are in a scanned PDF: OCR alone is not trustworthy for legal
  values; cross-validation against the ACAPS worked example is mandatory.
- Currency stays MAD; no euro estimate is exposed for Morocco.
