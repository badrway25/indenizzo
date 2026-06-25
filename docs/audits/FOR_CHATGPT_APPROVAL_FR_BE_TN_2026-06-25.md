# Approval pack — France / Belgium / Tunisia numeric engines

**Precise question:** is there an OFFICIAL, government-issued, computable
bodily-injury tariff for FR / BE / TN? If yes, supply it; if no, confirm the
premium guided path (current).

## France
- **Sources:** Loi n°85-677 (Badinter) — liability; Code des assurances; Code de
  la sécurité sociale. Légifrance.
- **Missing:** an official *state* quantification tariff. Dintilhac is a
  *nomenclature* (heads of loss); Mornet / Gazette du Palais are *practitioner
  référentiels*, not government tariffs.
- **Decision:** confirm "no state tariff → guided path", or supply an official
  tariff URL + table.

## Belgium
- **Sources:** Loi du 21/11/1989 (assurance auto); Moniteur belge.
- **Missing:** the **Tableau Indicatif** is *indicative* (magistrates'/lawyers'
  associations), not a binding ministry tariff.
- **Decision:** confirm guided path, or supply a binding official barème.

## Tunisia
- **Sources:** Code des Obligations et des Contrats (COC) — responsabilité
  civile; JORT / iort.gov.tn.
- **Missing:** an official computable bodily-injury tariff on the JORT.
- **Decision:** confirm guided path, or supply the official barème.

**Expected data format (if any approved):** `{taux_incapacité/poste, valeur}` +
the capitalisation rule, in the CompensationTableRow shape.
**Engine use:** per-country road-accident engine, fail-closed on incompatible
inputs. **Risk:** must NOT treat a practitioner référentiel as an official tariff.
**Tests after approval:** canary + "no euro estimate unless real engine" guard.
