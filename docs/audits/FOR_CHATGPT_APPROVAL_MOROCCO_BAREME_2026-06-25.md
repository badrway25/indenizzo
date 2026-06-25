# Approval pack — Morocco Dahir 1984 road-injury barème

**Precise question:** approve the OCR'd + verified numeric barème of the Dahir
1984 so a `morocco_road_accident_bareme` engine can be built (NOT the Moudawana,
which governs only family/inheritance status).

- **Official source / URL:** Dahir n°1-84-177 du 2/10/1984; ACAPS guides.
  `acaps.ma/sites/default/files/publication_documents/dahir_1984_indemn_acc_de_circulation.pdf`
  (sha256 `39c78a4cc8a88c34ae3f30c0c76a148e`, 7 pages);
  `acaps.ma/.../indemnisation_automobile_corporelle_fr_version_finale.pdf`
  (sha256 `f7222afe941e03a32eb6281842c8d827`).
- **Page / table:** the capital-de-référence formula (SMIG-indexed), the taux
  d'incapacité table, and the pretium-doloris / préjudice-esthétique bands.
- **Extracted so far:** NONE — the Dahir PDF is a **scanned image with 0 text
  layer** (pdfplumber extract_text() empty across all 7 pages); OCR
  (pytesseract/tesseract) is not installed in this environment.
- **What is missing:** an OCR pass (or a machine-readable Bulletin Officiel) of
  the barème pages, manually verified line by line.
- **Expected data format:** the capital-de-référence rule + `{taux_incapacité,
  coefficient}` rows + the pretium-doloris bands; plus a decision to collect the
  victim's income / responsibility / medical-legal inputs the wizard lacks.
- **Decision required:** supply the verified barème OR confirm Morocco stays a
  premium guided path (current). Moudawana must NOT be used as a damages engine.
- **Engine use:** income-/incapacity-/responsibility-indexed indemnity, only for
  compatible inputs, fail-closed otherwise.
- **Risk if approved:** medium — the method is multi-factor; needs careful input
  collection + strong disclaimers.
- **Tests after approval:** canary per taux + income band, no-Moudawana-misuse
  guard, fail-closed on missing inputs.
