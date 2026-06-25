# Approval pack — INAIL biological-damage engine

**Precise question:** approve the official INAIL menomazione→indennizzo table so a
numeric `inail_biological_damage` engine can be built (distinct from the civil
differential claim).

- **Official source / URL:** D.P.R. 30/06/1965 n.1124 (T.U. INAIL); **D.M.
  12/07/2000** (G.U. n.172 del 25/07/2000 — tabella delle menomazioni /
  indennizzo / coefficienti); **D.M. 23/04/2019 n.45** (danno biologico in
  capitale). Portals: normattiva.it, gazzettaufficiale.it, inail.it.
- **File / page / article:** the menomazione% → indennizzo € table (D.M.
  12/07/2000 allegati) + the danno-biologico-in-capitale table (D.M. 45/2019),
  plus age/coefficient rules + annual rivalutazione.
- **Extracted so far:** none — the tables are not in the DB and not
  machine-extractable from an accessible primary source.
- **What is missing:** the verbatim menomazione→indennizzo values (a
  machine-readable PDF/CSV), the coefficient/age rules, the 2025 rivalutazione.
- **Expected data format:** rows `{menomazione_pct, indennizzo_eur, age_band?,
  coefficient?}` (+ the capital table) — mirrors the art. 139 dataset shape
  (CompensationTableRow point_value/coefficient/daily_amount).
- **Decision required:** supply the official table (or confirm an OCR'd+verified
  extraction) → I create an approved LegalSource + dataset + `inail_biological_
  damage` engine.
- **Engine use:** computes the INAIL indemnity ONLY (never merged with the civil
  differential), with a strong "indennizzo INAIL, non risarcimento civilistico"
  disclaimer.
- **Risk if approved:** low if the table is verbatim-official; the engine
  fail-closes on any missing row.
- **Tests after approval:** canary per menomazione band + age, distinct-from-
  civil guard, provenance required, fail-closed on missing row.
