# Public service — official-source coverage matrix

**Phase**: P5 — Official Coverage Validation & Premium Labels · 2026-06-25
**Scope**: maps each public service/case section to the **governing official
instrument**, states what is validated vs. not, whether an automatic public
calculation is possible, and the **premium public copy / badge / CTA** to use
instead of weak technical labels.

## Grounding & rules

- Official instruments below are taken from the project's own validated record:
  the `LegalSource` catalogue in the database (31 entries, each with an official
  URL + `status`) and the hardened prescription record
  (`docs/review_packages/prescription_review_checklist.yml`). **Nothing here is
  invented.**
- **Calculation rule (unchanged):** a public numeric estimate is published ONLY
  where a `LegalSource` is `approved` AND an active calculator engine exists.
  Today that is **exactly one** combination: **Italy road-accident bodily
  injury** on the approved **Tabella Unica Nazionale 2025 (D.P.R. 13/01/2025
  n.12)**. Every other section is fail-closed: **no automatic amount**, a guided
  pathway instead.
- **Never public:** numeric prescription terms; internal states
  (`needs_review`, `manual_review_required`, `unresolved`, `source_verified`,
  `approved_for_public_display`, `scaffold`, `placeholder`, "da validare").
- Article *bodies* of Italian instruments are not auto-extractable (Normattiva /
  Gazzetta `caricaArticolo` are JavaScript-rendered; the IVASS CAP PDF stream is
  FlateDecode-compressed). **Instrument identity + official URL are confirmed**;
  EUR-Lex (Roma II / Reg. 650/2012) is fully readable. The Studio still confirms
  the current consolidated text + case modifiers before any use.

## Legend

`can_calc`: **yes** (approved source + engine) · **no** (fail-closed, guided
pathway) · **partial** (approved source exists but no public formula/engine).

---

## 1. Road accident — `road_accident`

- **Public title:** Incidente stradale (Road accident)
- **Official sources (DB):**
  - `approved` **D.P.R. 13 gennaio 2025, n. 12 — Tabella Unica Nazionale** —
    Gazzetta Ufficiale `eli/id/2025/02/11/25G...` *(drives the calculation)*
  - `needs_review` **D.Lgs. 7/9/2005 n. 209 — Codice delle Assicurazioni
    Private (CAP)**, artt. 138-139 (macro/micro), 144-145-148 (procedura) —
    Normattiva
  - `needs_review` **D.M. MIMIT 18/07/2025 & 10/12/2025** — aggiornamento importi
  - *internal only:* art. 2947 c.c. (prescrizione) — **never a public number**
- **Validated:** the TUN 2025 dataset (approved) → indicative min/mid/max range.
- **NOT validated for public output:** CAP macro/micro article bodies; MIMIT
  uplift coefficients (needs_review); any prescription term.
- **can_calc:** **yes** (IT, TUN-compatible cases).
- **Premium copy:** "Stima indicativa dalla Tabella Unica Nazionale ufficiale
  (D.P.R. 12/2025) per i casi compatibili; negli altri casi, percorso assistito."
- **Badge:** `Stima da fonte ufficiale` · base normativa `D.P.R. 12/2025 · CAP D.Lgs. 209/2005`
- **CTA:** "Calcola la stima"

## 2. Medical liability — `medical`

- **Official sources:** **Legge 8/3/2017 n. 24 (Gelli-Bianco) art. 7** (Gazzetta
  `eli/id/2017/03/17/17G00041`); Codice Civile artt. 1218/1228/2043
  (qualificazione); CAP art. 138 per macrolesioni dove applicabile.
- **Validated:** governing framework (Gelli + civil-liability qualification).
- **NOT validated:** no national public formula per medical error; the term
  depends on contractual vs. extracontractual qualification → case-specific.
- **can_calc:** **no**.
- **Premium copy:** "La responsabilità sanitaria è regolata dalla Legge
  Gelli-Bianco (L. 24/2017). La stima dipende da perizia e qualificazione del
  rapporto: percorso assistito su documentazione clinica."
- **Badge:** `Responsabilità sanitaria` · base normativa `L. 24/2017, art. 7`
- **CTA:** "Analisi guidata del caso"

## 3. Workplace injury — `work_injury`

- **Official sources:** **D.P.R. 30/6/1965 n. 1124 — T.U. INAIL**, art. 112
  (Normattiva); distinzione indennizzo INAIL vs. danno differenziale civilistico
  (art. 2087 c.c. / 2043).
- **Validated:** governing instrument (T.U. INAIL) + the indennizzo/differenziale
  distinction.
- **NOT validated:** INAIL indemnity tables not modelled as a public engine; the
  differential follows civil rules → case-specific.
- **can_calc:** **no**.
- **Premium copy:** "Infortunio sul lavoro e malattia professionale: indennizzo
  INAIL (D.P.R. 1124/1965) e danno differenziale civilistico. Verifica dedicata,
  senza importi automatici."
- **Badge:** `INAIL / lavoro` · base normativa `D.P.R. 1124/1965 (T.U. INAIL)`
- **CTA:** "Verifica indennizzo e differenziale"

## 4. Loss of a relative / death — `death`

- **Official sources:** Codice Civile artt. 2043, 2059, 1223, 1226 (danno non
  patrimoniale / nesso / liquidazione equitativa).
- **Validated:** the civil-code basis exists.
- **NOT validated — IMPORTANT:** **there is no official *national* statutory
  table** for parental/loss-of-relationship damages. The widely used reference
  is the **Milano court tables** (in DB as `needs_review`, court practice — NOT a
  primary national source). → see OFFICIAL_SOURCES_NOT_FOUND.
- **can_calc:** **no** (no official national formula; never invent a table).
- **Premium copy:** "Danno da perdita del rapporto parentale: nessuna formula
  pubblica nazionale automatica applicabile con sicurezza. Percorso assistito su
  responsabilità e documentazione, seguito direttamente dallo Studio."
- **Badge:** `Percorso assistito` · base normativa `artt. 2043, 2059 c.c.`
- **CTA:** "Percorso assistito per i familiari"

## 5. Defective product — (covered under cross-border / consumer)

- **Official sources:** **D.Lgs. 6/9/2005 n. 206 — Codice del Consumo**, artt.
  114-127 (Normattiva `CONSOLIDATED`); artt. 125-126 *internal only*
  (prescrizione/decadenza — never a public number).
- **Validated:** governing instrument (responsabilità per prodotto difettoso).
- **NOT validated:** no public automatic formula.
- **can_calc:** **no**.
- **Premium copy:** "Danno da prodotto difettoso: disciplina del Codice del
  Consumo (D.Lgs. 206/2005). Analisi documentale, senza importi automatici."
- **Badge:** `Prodotto difettoso` · base normativa `D.Lgs. 206/2005, artt. 114-127`
- **CTA:** "Analisi documentale"

## 6. Insurance / INAIL offer to check — `insurance_offer`

- **Official sources:** **CAP D.Lgs. 209/2005, artt. 145 & 148** (proponibilità
  + procedura di risarcimento/offerta) — Normattiva; IVASS (vigilanza/reclami).
- **Validated:** the official RC-auto procedure governing the offer.
- **NOT validated:** adequacy of a specific offer is case-specific (no public
  number).
- **can_calc:** **no** (review, not calculation).
- **Premium copy:** "Hai ricevuto un'offerta transattiva o INAIL: verifica
  dell'adeguatezza secondo la procedura assicurativa ufficiale (CAP, artt.
  145/148) prima di firmare."
- **Badge:** `Procedura RC Auto` · base normativa `CAP D.Lgs. 209/2005, art. 148`
- **CTA:** "Fai esaminare la tua offerta"

## 7. Cross-border matters — `international`

- **Official sources:** **Regolamento (CE) 864/2007 (Roma II)**, artt. 4, 5, 15,
  31-32 — EUR-Lex `CELEX:32007R0864` *(fully readable)*; per successioni
  **Reg. (UE) 650/2012** (in DB, `approved`).
- **Validated:** EU framework for applicable law (extracontractual obligations).
- **NOT validated:** no numeric term/amount — prescription follows the *lex
  causae*.
- **can_calc:** **no**.
- **Premium copy:** "Casi con elementi di estraneità: inquadramento della legge
  applicabile (Regolamento Roma II, CE 864/2007) e della giurisdizione
  competente. Percorso guidato multilingue."
- **Badge:** `Legge applicabile` · base normativa `Reg. CE 864/2007 (Roma II)`
- **CTA:** "Inquadramento legge applicabile"

## 8. Foreign nationals / Ta3ouid — `foreigners`, `documents`

- **Official sources:** general access-to-justice for the injured party; **Roma
  II** + **CAP/TUN** where the harm is in Italy.
- **Validated:** the same official framework as the relevant area applies.
- **NOT validated:** nothing area-specific to add; no promises.
- **can_calc:** **no** (assisted, multilingual pathway).
- **Premium copy:** "Assistenza per chi ha subito un danno in Italia, anche
  dall'estero: orientamento con fonti ufficiali, in arabo, francese, italiano e
  inglese."
- **Badge:** `Percorso assistito` · `Multilingue`
- **CTA:** "Richiedi un'analisi guidata del caso"

---

## Country coverage (hub `/countries/`)

| Country | Source (DB) | Status | can_calc | Public badge (premium) |
|---|---|---|---|---|
| IT | D.P.R. 12/2025 TUN | approved + engine | **yes** | Stima da fonte ufficiale |
| FR | Loi Badinter 85-677 (approved); Dintilhac/Mornet (needs_review) | no engine | **no** | Percorso legale assistito |
| BE | Loi 1989 (approved); Tableau Indicatif (needs_review) | no engine | **no** | Percorso legale assistito |
| MA | Moudawana (approved); Reg. 650/2012 | inheritance, no engine | **no** | Successione internazionale assistita |
| TN | CSP + CDIP (approved); Reg. 650/2012 | inheritance, no engine | **no** | Successione internazionale assistita |

FR/BE/MA/TN stay **fail-closed**: premium wording communicates an *assisted
pathway*, never a calculation or an amount.

## Premium label replacements (weak → premium)

| Weak label (banned) | Premium replacement |
|---|---|
| Preliminary assessment needed / Valutazione preliminare necessaria | **Percorso legale assistito** (Assisted legal pathway) |
| Preliminary legal assessment | **Percorso legale assistito** |
| Manual legal review | **Esame legale dedicato** (Dedicated legal review) |
| Request a preliminary assessment (CTA) | **Richiedi un'analisi guidata del caso** |
| Calculable with official source | **Stima da fonte ufficiale** |
| (new) per-area attribution | **Base normativa: <instrument>** |
