# MULTI-COUNTRY PATTERN — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Tipo:** index/cross-link.
**Scopo:** sintesi del pattern modulare paese-per-paese, lifecycle
delle fonti, regole DIP cross-border. Linka i 4 file
`*_MODULE_STATUS.md` autorevoli per paese.

---

## 1. Filosofia

> Implementazione **in profondità, modulo per modulo, paese per
> paese**. MAI superficiale su tutti i paesi insieme.

Tre vincoli cardinali (vedi `docs/architecture/PRODUCT_REQUIREMENTS.md`
REQ-3, REQ-4):

1. nessun calcolo pubblico senza fonte legale **approved**;
2. ogni paese ha proprio dataset + formula + disclaimer + lingua;
3. nessun deploy in prod finché **almeno un caso non-IT** è verde.

Il pattern è documentato fila-per-fila in
`docs/architecture/LOCAL_NEXT_STEPS.md` (Fasi A → E).

---

## 2. Pattern adapter

Ogni paese × case_type ha la sua "verticale":

```
LegalSource (status=approved) ──► CompensationDataset (status=approved)
        │                                │
        ▼                                ▼
   LegalReview (signed)          CalculationFormula (status=approved,
                                          parameters.engine=…)
        │                                │
        └────────────► <Country><CaseType>Calculator (subclass BaseCalculator,
                       override _compute_with_sources)
                                ↓
                    apps/calculators/registry register
                                ↓
                       Wizard URL /it/wizard/<country>/<case_type>/
                                ↓
                            CalculationResult
```

Stessa shape per ogni paese. La differenza è solo il contenuto
(formula, dataset, disclaimer, lingua dei testi).

---

## 3. Lifecycle status delle fonti

`LegalSource.status` lifecycle (vedi `apps/legal_sources/models.py`):

```
draft  ──►  extracted  ──►  needs_review  ──►  reviewed  ──►  approved
                                                                  │
                                                ┌─────────────────┤
                                                ▼                 ▼
                                          deprecated         replaced
```

Solo `approved` alimenta calcoli pubblici. `replaced` indica
sostituzione con nuova versione (es. TUN 2025 sostituirà TUN 2026
quando uscirà): la vecchia resta in DB per audit storico delle
simulazioni passate.

Ogni transizione `*→approved` richiede una `LegalReview` firmata
(reviewer User staff/lawyer + timestamp). Il flusso è gestito via
Django admin (`apps.legal_sources.admin.py`).

---

## 4. Stato per paese (snapshot 2026-04-30)

Snapshot autorevole: `docs/architecture/GLOBAL_MVP_STATUS.md`.

### 4.1 IT (Italia)

- ✅ Fonte approved: `it-dpr-12-2025-tun-danno-biologico` (D.P.R.
  13 gennaio 2025 n. 12, TUN 2025).
- ✅ Dataset approved: 9 191 + 27 573 righe (biologico + morale).
- ✅ Formula approved: `italy_art_138_tun_2025_base`.
- ✅ Calculator REAL: `ItalyRoadAccidentBodilyInjuryCalculator`.
- ✅ Wizard pubblico: `/wizard/it/road-accident/`.
- 🟡 4 fonti residue in `needs_review` (CAP D.Lgs. 209/2005, MIMIT
  art. 139, MIMIT macrolesioni, Tabelle Milano 2024).
- ❌ `IT/inheritance_basic` registrato ma placeholder.

### 4.2 FR (Francia)

- ❌ Calculator: placeholder (`_FrancePlaceholderCalculator`).
- 🟡 Candidate dataset on-disk (Mornet 2024, Gazette du Palais 2022).
- ❌ Nessun dataset/formula approved.
- ✅ Review package pronto: `docs/legal_sources/FRANCE_LEGAL_REVIEW_PACKAGE.md`
  (23 righe checklist `pending`).
- 🟡 Loi Badinter scaricata manualmente (post-403 Legifrance).

Stato canonical: `docs/architecture/FRANCE_MODULE_STATUS.md`.

### 4.3 BE (Belgio)

- ❌ Calculator: placeholder.
- 🟡 Candidate Tableau Indicatif 2020 (4 CSV); 2024 in attesa OCR
  (lang pack `fra`/`nld` mancanti).
- ❌ Nessun dataset/formula approved.
- ✅ Review package pronto: `BELGIUM_LEGAL_REVIEW_PACKAGE.md`.
- 🟡 BE 2020 va promosso solo come `historical_fallback`.

Stato canonical: `docs/architecture/BELGIUM_MODULE_STATUS.md`.

### 4.4 MA (Marocco)

- ❌ Calculator: placeholder.
- ❌ No candidate. Mapping-only: serve trascrizione manuale **firmata**
  delle quote faraïd post mapping Studio.
- ❌ Reg. UE 650/2012 download manuale richiesto (EUR-Lex 202).
- ✅ Review package: `MOROCCO_LEGAL_REVIEW_PACKAGE.md` (21 righe).

Stato canonical: `docs/architecture/MOROCCO_INHERITANCE_MODULE_STATUS.md`.
Mapping draft: `MOROCCO_MOUDAWANA_MAPPING_DRAFT_PASS1.md`,
`PASS2`, `PASS3`.

### 4.5 TN (Tunisia)

- ❌ Calculator: placeholder.
- ❌ Mapping-only.
- ❌ Doppia regola di conflitto Loi 98-97 (foro TN) vs Reg. 650/2012
  (foro UE) — decisione DIP **non risolta**.
- ❌ JORT 1956 + CSP compiled + Reg. 650/2012: download manuale.
- ✅ Review package: `TUNISIA_LEGAL_REVIEW_PACKAGE.md` (26 righe).

Stato canonical: `docs/architecture/TUNISIA_INHERITANCE_MODULE_STATUS.md`.
Mapping draft: `TUNISIA_CSP_MAPPING_DRAFT_PASS1.md`,
`TUNISIA_CSP_ADJACENT_ARTICLE_RANGES_FETCH_PASS2.md`.

---

## 5. Regole DIP — quando si applicano

| Caso | Norma applicabile | Engine helper |
|---|---|---|
| Successione cross-border IT/FR/BE/altri UE | **Reg. (UE) 650/2012** (residenza abituale → eccezione professio juris) | `apps.calculators.inheritance_applicable_law` |
| Successione MA non in UE / MA con asset UE | combinazione Moudawana + Reg. 650/2012 (se de cuius residente UE) | idem |
| Successione TN | combinazione **CSP Livre IX** + **Loi 98-97 (Code DIP TN)** + Reg. 650/2012 — *doppia regola di conflitto* da risolvere caso per caso | idem |
| Incidente stradale cross-border | Reg. (CE) 864/2007 (Roma II) — applicabile la legge del paese del sinistro | non implementato (P3) |
| Responsabilità medica cross-border | idem Roma II | non implementato (P3) |

Doc dettagliato:
`docs/architecture/EU_650_APPLICABLE_LAW_DECISION_ENGINE_SKELETON.md` +
`APPLICABLE_LAW_ENGINE_INTEGRATION_PASS1.md`.

---

## 6. Convenzioni cross-country

### 6.1 Naming

- Country code: ISO 3166-1 alpha-2 (`IT`, `FR`, `BE`, `MA`, `TN`).
- Jurisdiction code: `<COUNTRY>-NATIONAL` per livello nazionale
  (futuro: `IT-MILANO-TRIBUNALE` per tabelle Milano).
- Case type: snake_case (`road_accident_bodily_injury`,
  `international_inheritance`, `inheritance_basic`).

### 6.2 Slug URL

Vedi `docs/SEO_AUDIT_AND_CONTENT_ARCHITECTURE.md` Sez. 3.3-3.4. Slug
**localizzati** per lingua (`incidente-stradale` IT vs
`accident-route` FR).

### 6.3 Dataset

- Nome: `<COUNTRY>-<SOURCE_REF>` (es. `DPR-12-2025-MORAL`,
  `BE-TI-2020-FALLBACK`).
- Storage: `legal_data/sources/<country>/...` (gitignored).
- Manifesto JSON: `legal_data/sources/<country>/extraction_summary.json`
  (committabile, no PII, no valori legali).
- Hash SHA-256 di ogni PDF/HTML scaricato.

### 6.4 Mapping (per paesi mapping-only: MA, TN)

- CSV strutturato: `legal_data/mappings/<country>_inheritance_mapping_draft.json`.
- Schema: `inheritance_case_code`, `heir_relation_code`, `heir_count`,
  `share_numerator`, `share_denominator`, `share_decimal`,
  `transcription_status`, `source_quote_short`, `notes`,
  `legal_review_required=true`, `no_human_legal_approval=true`.
- Mai LLM-generated; trascrizione manuale o estrazione
  deterministica.

### 6.5 Disclaimer per paese

Disclaimer obbligatorio CLAUDE.md è universale, ma:

- IT: aggiunge riferimento alle Tabelle Milano come orientamento
  giurisprudenziale possibile;
- FR/BE: indica che la stima è preliminare in attesa di review
  Studio;
- MA/TN: aggiunge nota su DIP e ordine pubblico (le regole faraïd
  possono incontrare ordine pubblico nel foro UE).

Tutti tradotti via `apps/calculators/disclaimer.py` + locale `.po`.

---

## 7. Roadmap di estensione paese (cross-link)

Roadmap operativa: `docs/architecture/LOCAL_NEXT_STEPS.md` (5 fasi
A → E con dipendenze e gating Studio).

Vista P0–P5 sintetica: `docs/ROADMAP_PRIORITIZED.md`.

---

## 8. Pattern operativi non negoziabili

(Riassunto da `LOCAL_NEXT_STEPS.md` Sez. 8)

1. **Read-only first**: ogni iter inizia con script read-only
   (estrazione, OCR, audit) prima di toccare il DB.
2. **Candidate read-only on-disk**: CSV estratti restano gitignored
   finché lo Studio non li firma.
3. **`source_note` strutturato** su ogni riga di dataset legale.
4. **Hash SHA-256** di ogni PDF/HTML.
5. **No LLM-generated values** per dati legali.
6. **Test verde prima di tutto**: pytest, ruff, black sempre verdi
   al merge.
7. **No regressioni Italia**: ogni iter chiude con "Italia invariata:
   pytest 328+ passed".

---

## 9. Espansione futura (P4-P5)

Paesi candidati per fasi successive (vedi
`PRODUCT_REQUIREMENTS.md` REQ-4):

- Spagna, Germania, Canada, Romania, Algeria, Egitto.

Pattern:

1. nuovo `Country` + `Currency` + `Language`;
2. nuovo review package (template come MA/TN);
3. fasi A → C come per FR/BE (review → import → calculator skeleton);
4. country landing + SEO + traduzioni;
5. test E2E e screenshot.

Tempo stimato per nuovo paese (post-MVP): 4-8 settimane di
calendario, dipendente prevalentemente dalla disponibilità Studio
per il review.

---

## 10. Per Claude Code che riprende il multi-country

- **Mai** attivare un calcolatore non-IT senza:
  - `LegalSource.status=approved` per quella giurisdizione/case_type;
  - `LegalReview` firmata;
  - `CompensationDataset.status=approved`;
  - `CalculationFormula.status=approved`;
  - test E2E sul wizard pubblico verde;
  - feature flag in prod settabile per paese.
- **Mai** importare CSV gitignored finché `LegalReview` non è
  stata eseguita riga per riga.
- **Mai** mostrare valori monetari da fonti `needs_review` in PDF
  utenti.
- L'IT è il *baseline invariant*: ogni iter conferma "Italia
  invariata".
- Quando si propone l'attivazione di un paese, generare:
  - audit script per quella giurisdizione (`scripts/legal_data/audit_<country>_*.py`);
  - lighthouse + visual QA in `docs/screenshots/live_qa/<iter>/`;
  - aggiornamento `GLOBAL_MVP_STATUS.md` con la nuova riga REAL.
