# P11 — Tunisia / Belgium / France numeric-source outcomes

Date: 2026-06-26. Genuine source research (official domains only). Decides, per
country, whether a **state computable barème** exists → candidate engine, or not
→ the public section stays an official guided path (no euro estimate).

## Tunisia — STATE BARÈME EXISTS → approval pack (not yet extracted)

- **Loi n° 2005-86 du 15 août 2005** insère le **Titre V** du Code des
  assurances (art. **110–179**): régime d'indemnisation des préjudices
  corporels résultant des accidents de la circulation.
- **Key**: the loi establishes a **rating scale (barème) binding on insurers
  AND judges**, with a ±15% evaluation margin, plus a 6-month amiable-offer duty
  and a guarantee fund (art. 172–176). This is a genuine **state** barème
  (unlike FR/BE), so a numeric engine is feasible **once the tables are
  validated**.
- Official sources:
  - legislation.tn: `.../detailtexte/Loi-num-2005-86-du----jort-2005-067...`
  - Code des assurances (FR): `cga.gov.tn/.../pdf/Code_Assurance_Version_FR.pdf`
  - CGA (Comité Général des Assurances) — assurance automobile.
- **Status**: `official_guided_path_approved` (public) +
  `chatgpt_approval_required_for_numeric_engine` (internal).
- **Ask**: extract from Code des assurances Titre V the barème tables
  (revenu de référence, coefficient par âge, taux d'incapacité, décès/ayants
  droit) + one official worked example for a canary. Target engine
  `tunisia_road_injury_bareme` (currency TND, fail-closed, not public until a
  canary is green). See `FOR_CHATGPT_APPROVAL_FR_BE_TN_2026-06-25.md`.

## Belgium — NO state barème → guided path stays (final)

- Liability base is official: **Loi du 21 novembre 1989** (assurance RC
  véhicules automoteurs) + Code civil (resp. extracontractuelle), via
  Moniteur belge / SPF Justice.
- **Quantum is assessed *in concreto*** (case-by-case). The **« Tableau
  indicatif »** (montants) is drawn up by magistrates'/judges' associations and
  is **explicitly indicative and non-binding — not a state law/tariff**.
- **Decision**: no numeric engine. Belgium stays
  `official_guided_path_approved`; **no euro estimate** is published. Using the
  Tableau indicatif as an engine would breach the "official source only" rule.
- Approval pack only if an official binding tariff is later identified
  (none found).

## France — NO state barème → guided path stays (final)

- **Loi Badinter (loi n° 85-677 du 5 juillet 1985)** governs the **right** to
  compensation (liability), **not the amount**. Légifrance blocks automated
  fetch (HTTP 403) but the framework is well established.
- The **Nomenclature Dintilhac** is a *classification of heads of damage*, not a
  tariff. The **Référentiel Mornet / barème "Gazette du Palais"** are
  practitioner/indicative references, **not state law**. No state barème
  produces an automatic amount.
- **Decision**: no numeric engine. France stays
  `official_guided_path_approved`; **no euro estimate**. Inquadramento Loi
  Badinter + percorso assistito.

## Summary

| Country | State computable barème? | Engine | Public state |
|---|---|:--:|---|
| Tunisia | yes (loi 2005-86, Code assur. Titre V, binding) | candidate / pack | guided path (euro→TND only when validated) |
| Belgium | no (Tableau indicatif non-binding) | no | guided path, no estimate |
| France | no (Badinter=liability; Dintilhac/Mornet indicative) | no | guided path, no estimate |
