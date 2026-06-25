# Morocco — road-injury official barème audit (P7)

**Phase**: P7 · 2026-06-25. Follows the owner's lead (ACAPS / Dahir 2 oct 1984).
Real download + hash + parse attempt of the official ACAPS documents.

## Sources fetched (official ACAPS — Autorité de Contrôle des Assurances)

| Document | URL | sha256 (first 32) | bytes | pages |
|---|---|---|---|---|
| Dahir n°1-84-177 du 2/10/1984 (texte) | acaps.ma/.../dahir_1984_indemn_acc_de_circulation.pdf | `39c78a4cc8a88c34ae3f30c0c76a148e` | 461 038 | 7 |
| Guide "Indemnisation automobile corporelle" | acaps.ma/.../indemnisation_automobile_corporelle_fr_version_finale.pdf | `f7222afe941e03a32eb6281842c8d827` | 180 913 | 6 |

## What the parse found

- **Dahir 1984 PDF = scanned image, 0 extractable text** across all 7 pages
  (pdfplumber `extract_text()` returns empty; `extract_tables()` returns none).
  Reading the numeric barème would require **OCR** (pytesseract/tesseract — not
  installed) **plus** line-by-line manual verification against the Bulletin
  Officiel before any use.
- **ACAPS guide (text-extractable)** confirms the Moroccan compensation method
  is explicitly **"multifactoriel"**: it combines the **part de responsabilité**,
  the **incapacité physique permanente** (with recourse to a tierce personne),
  the **pretium doloris** (catégories), the **préjudice esthétique**, the
  **frais médicaux/transport**, and a **capital de référence** built from the
  victim's **income (SMIG-indexed)**. It is NOT a flat lookup table like the
  Italian TUN.

## Verdict — no automatic engine (precise reasons, not prudence)

1. **No clean extractable barème table.** The numeric barème lives in a scanned
   PDF (no text layer) and across multiple income-/age-/responsibility-indexed
   components — not a single computable table.
2. **Inputs the platform does not collect.** A correct Dahir-1984 indemnity needs
   the victim's **income/SMIG reference**, the **responsibility apportionment**,
   and **medical-legal categorisations** (pretium doloris, préjudice esthétique
   bands) — none of which an automatic, document-free wizard can supply.
3. **Moudawana is NOT the damages source** (re-confirmed): the bodily-injury
   basis is the Dahir 1984 + the DOC (responsabilité civile) + the Code des
   Assurances; the Moudawana governs only family/inheritance status.

➡️ **MA stays fail-closed** for road-injury damages, with a premium assisted
pathway citing the Dahir 1984 as the governing official source. To build an
engine I need: (a) the **machine-readable** official barème (a non-scanned
Bulletin Officiel table or an OCR pass manually verified), and (b) a decision to
collect income / responsibility / medical-legal inputs.

## FR / BE / TN (re-confirmed, P6 + P7)

- **France:** Loi Badinter = liability; the quantification references (Dintilhac
  nomenclature, Mornet/Gazette du Palais référentiels) are **not official
  government tariffs** → no engine; assisted pathway with normative framing.
- **Belgium:** the **Tableau Indicatif** is *indicative* (magistrates'/lawyers'
  associations), loaded `draft`, never `approved` → engine inert. Correct.
- **Tunisia:** damages basis = **COC tunisien** (not the CSP, which correctly
  backs only inheritance); no official computable bodily-injury tariff confirmed
  on the JORT → no engine; assisted pathway.

All four remain fail-closed (candidate datasets `draft`), which is the correct,
honest behaviour. No page is left "poor": each shows premium assisted-pathway
copy with the governing official source (see the P5 coverage doc).
