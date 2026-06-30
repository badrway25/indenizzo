# ChatGPT approval queue — official numeric engines

Date: 2026-06-26. Single decision file — paste to ChatGPT/owner. For each
candidate: **APPROVARE / RESPINGERE / RICHIEDERE RICERCA**. Nothing is exposed
publicly as a euro/numeric estimate until the relevant row is APPROVED and a
canary is green. Extraction tooling in this env: pdfplumber/pdftotext/pandas/PIL
+ tesseract (**eng-only**); **no PDF→image rasterizer** (pdftoppm/gs/fitz all
missing) → scanned-PDF OCR is not possible here.

---

## 1) Morocco — `morocco_road_injury_bareme` (MAD) — RICHIEDE 1 TABELLA

- **Source**: ACAPS guide Dahir 1984 (text, SHA256 `b4d6f9e8b2c61f70…`) + Dahir
  1-84-177 (scanned, SHA256 `39c78a4cc8a88c34…`). Reachable: acaps.ma.
- **Extracted (reliable, text)**: full formula + all complementary/ayants-droit
  percentages + salary rules + official canary. See `MOROCCO_BAREME_CANDIDATE_2026-06-26.md`.
- **Formula**: `capital_de_référence(âge, salaire) × taux_incapacité × taux_responsabilité`.
- **Canary**: `346 500 × 20% × 50% = 34 650 MAD` (ACAPS p. 11).
- **Missing**: the **capital-de-référence base table** (âge × salaire → MAD) from
  the scanned Dahir annex.
- **Domanda secca**: «APPROVI di fornire/validare la tabella `capital de
  référence` (per fascia d'età e di salario) del Dahir 1984? I coefficienti
  complementari e ayants-droit estratti sono corretti?»
- **Se APPROVATO**: importer `import_morocco_bareme` → dataset approved (MAD) →
  engine fail-closed → canary 34 650 → UI guided→numeric (MAD, mai euro).

## 2) Tunisia — `tunisia_road_injury_bareme` (TND) — RICHIEDE ESTRAZIONE

- **Source**: Loi n° 2005-86; Code des assurances **Titre V, art. 110–179**
  (barème **binding** insurers+judges, ±15%). Sources: cga.gov.tn,
  legislation.tn.
- **Blocker (environmental)**: both Tunisian official hosts are **unreachable
  from this environment** (cga.gov.tn `http=000`; legislation.tn
  `ECONNREFUSED`). No table extracted.
- **Domanda secca**: «APPROVI/fornisci il barème del Code des assurances Titre V
  (revenu de référence, coefficient par âge/capitalisation, taux d'incapacité,
  décès/ayants droit) + un esempio ufficiale per canary?»
- **Se APPROVATO**: importer → dataset (TND) → engine fail-closed → canary → UI.

## 3) INAIL — `inail_biological_damage_capital` (EUR) — RICHIEDE TABELLA VALORI

- **Source chain (verified)**: D.M. 12/07/2000 → Det. Pres. INAIL 2/2019 + D.M.
  Lavoro 45/2019 → rivalutazione Delibera CdA 43 del 26/03/2025 (eff. 01/07/2025).
- **Blocker**: the grado×età capital values are not published machine-readable;
  the downloaded INAIL "Allegato 5" (SHA256 `046b823c…`) is the MOD 16/TER heirs
  form, not the value table. See `FOR_CHATGPT_APPROVAL_INAIL_TABLE_2026-06-26.md`.
- **Domanda secca**: «Fornisci la tabella indennizzo danno biologico in capitale
  vigente (grado 6–15% × età, valori 2019 rivalutati al 01/07/2025; conferma
  unificazione genere)?»
- **Se APPROVATO**: importer → dataset (EUR) → engine fail-closed → canary → UI
  con etichetta «indennizzo INAIL», distinto dal risarcimento civile.

## 4) Belgium — NO ENGINE (final)

Tableau indicatif **non vincolante** (associazioni di magistrati), non legge
statale → guided path definitivo, nessuna stima. See
`BELGIUM_FINAL_NO_STATE_BAREME_2026-06-26.md`. **Nessuna decisione richiesta.**

## 5) France — NO ENGINE (final)

Loi Badinter = responsabilità, non quantum; Dintilhac/Mornet = nomenclature/
référentiels non statali → guided path definitivo, nessuna stima. See
`FRANCE_FINAL_NO_STATE_BAREME_2026-06-26.md`. **Nessuna decisione richiesta.**

---

### Summary

| # | Candidate | State | Currency | Decision needed |
|---|---|---|---|---|
| 1 | Morocco | coefficients extracted; 1 table missing | MAD | provide capital-de-référence table |
| 2 | Tunisia | sources unreachable here | TND | provide Titre V barème |
| 3 | INAIL | chain verified; values not machine-readable | EUR | provide grado×età table |
| 4 | Belgium | no state barème | — | none (final) |
| 5 | France | no state barème | — | none (final) |

---

## P14 — what each approval unlocks (category × country)

The matrix `CATEGORY_COUNTRY_OFFICIAL_ESTIMATE_MATRIX_2026-06-26.md` maps every
country × category to an estimate state. Each pending approval below unlocks a
SET of categories/countries — not a single page:

| Approval | Country | Categories it unlocks | Data needed | Canary |
|---|---|---|---|---|
| INAIL capital table (D.M. 45/2019, riv. 2025) | Italy | work-injury (numeric); strengthens road/medical differential | grado 6–15% × età → € | 1 official worked row |
| Morocco capital-de-référence table (Dahir annex) | Morocco | road-injury, road-death, bodily damage, ayants-droit (all numeric) — coefficients already extracted | capital de référence (âge × revenu) | 346 500 × 20% × 50% = 34 650 MAD |
| Tunisia barème (Code des assurances Titre V) | Tunisia | road-injury, road-death, bodily damage (numeric) | revenu de référence, coeff. âge, IPP, décès | 1 official worked row |
| Death/parental table | Italy | loss-of-relative numeric (currently guided) | a state/ministerial table (none today) | — |
| France / Belgium | FR/BE | none — no state barème (guided is final) | — | — |

Until a row is APPROVED, the corresponding public categories stay `pre_check`
(structured documental collection, official sources cited) or `guided` — never a
weak label, never an invented amount. Morocco and Tunisia already expose their
multi-category coverage publicly on the country pages with the official source
chips above.

---

## P21 — estimate-expansion re-evaluation (no engine activated)

Re-checked every candidate against the cardinal rule (no amount without a
validated official table/formula). **No engine could be activated in this
session** — the missing inputs below are the only blocks, and each maps to the
intelligent public readiness already shown on the pre-check result (the
`potential_path` + `what unlocks a numeric estimate` block), so the public never
sees a bare "blocked" state.

| Candidate | Precise block (single missing input) | Public readiness shown today |
|---|---|---|
| INAIL (work injury) | machine-readable **grado 6–15% × età → € capital** table (D.M. 45/2019 + riv. 2025); annuity for >15% needs the rendita coefficient | "Official INAIL calculation, once the capital/annuity table is validated" + unlock = the validated table for the entered impairment |
| Morocco road | **capital-de-référence** annex (âge × revenu) — the responsibility/IPP coefficients are already extracted | "Official Dahir/ACAPS barème (capital de référence), once validated" + unlock = the validated capital-de-référence table |
| Tunisia road | **Code des assurances Titre V barème** (revenu de référence, coeff. âge, IPP, décès) — sources unreachable from here | "Official Code des assurances barème (loi 2005-86), once validated" + unlock = the validated barème |
| Italy loss-of-relative | **no state/ministerial table exists**; Milano/Roma tables are court *prassi*, not state law → must stay a guided parental-damage assessment, not a numeric engine | "Guided assessment of the parental/family damage" + unlock = documented relationship + established liability |
| France / Belgium | **no state barème** (Badinter = liability; Dintilhac/Mornet/Tableau Indicatif = non-state référentiels) → guided is final | guided legal pathway (documents + liability) |

Conclusion: the three currency engines (MAD/TND/€-INAIL) remain **candidate**,
gated on one official table each; loss-of-relative and FR/BE are **final guided**
(no state quantum source exists). The public surface already expresses this as
readiness, not as a block — no change to the cardinal guardrail.
