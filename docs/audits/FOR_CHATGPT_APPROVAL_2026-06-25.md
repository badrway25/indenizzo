# For ChatGPT/owner approval — precise blockers (P8)

What remains NOT implementable until the exact official data is supplied. Each
item names the precise file/table/value needed (not a generic phrase).

## A. INAIL biological-damage indemnity engine

- **Need:** the official **menomazione% → indennizzo €** table from
  **D.M. 12/07/2000** (G.U. n.172 del 25/07/2000) and the danno-biologico-in-
  capitale table from **D.M. 45 del 23/04/2019**, plus the age/coefficient rules
  and any annual rivalutazione.
- **Blocker:** these tables are not in the DB and not machine-extractable from an
  accessible primary source; INAIL indemnity must stay **distinct** from the
  civil/differential claim.
- **To unblock, supply:** the verbatim menomazione→indennizzo values (or a
  machine-readable official PDF/CSV) so an `inail_biological_damage` dataset +
  engine can be built with a canary, exactly like art. 139.

## B. Morocco — Dahir 1984 road-injury barème

- **Need:** the numeric barème of **Dahir n°1-84-177 du 2/10/1984** (capital de
  référence, taux d'incapacité, pretium-doloris bands).
- **Blocker:** the official ACAPS PDF (`dahir_1984_indemn_acc_de_circulation.pdf`,
  sha256 `39c78a4c…`, 7 pages) is a **scanned image with 0 text layer** (OCR not
  installed); the method is multi-factor / income(SMIG)-indexed and needs inputs
  the document-free wizard does not collect.
- **To unblock, supply:** an OCR'd + manually-verified barème table (pages of the
  Dahir + the capital-de-référence/coefficient values), and a decision to collect
  income / responsibility / medical-legal inputs.

## C. France / Belgium / Tunisia

- **France:** need an *official government* quantification tariff (Dintilhac is a
  nomenclature; Mornet / Gazette du Palais are practitioner référentiels). None
  exists in the TUN sense → no engine.
- **Belgium:** the Tableau Indicatif is *indicative* (associations), not a
  ministry tariff → no engine.
- **Tunisia:** need an official computable bodily-injury tariff on the JORT (the
  COC governs liability, not a tariff) → no engine.
- All stay fail-closed with premium assisted-pathway copy.

## D. Italy — art. 139 personalizzazione / morale

- The +20% personalizzazione (art. 139 co.3) and any extra moral are **judicial**
  and case-specific. They are intentionally NOT auto-computed (shown as *not
  included, assessable by the court*). No approval needed — this is correct.
