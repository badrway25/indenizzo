# Official source automation — status (F-product-official-source-automation-and-full-site-functional-upgrade)

Stato: aperto 2026-05-03.

Inventario di tutti i `(jurisdiction, case_type)` registrati nel
prodotto e classificazione automatica vs. eccezione umana, secondo la
regola nuova:

> **NO Studio review** se: fonte ufficiale o istituzionale + URL tracciato +
> file scaricato + sha256 + parser deterministico + QA automatico
> completo + smoke test coerenti + nessuna ambiguità giuridica/OCR.
>
> **YES `human_exception_review`** se: fonte non ufficiale/indicativa,
> PDF scansionato/OCR, fonte privata/dottrinale, tabella ambigua,
> mapping interpretativo, parser con coverage <100%, formula con
> scelta giuridica.

---

## 1. Inventario calculator pairs

Letto da `apps/calculators/registry.py` + `engines/*.py`.

| Pair | Wizard | Calculator | Status engine | Fonti presenti | Dataset | Formula |
|------|--------|-----------|---------------|----------------|---------|---------|
| `IT-NATIONAL × road_accident_bodily_injury` | `templates/public/wizard_italy_road_accident.html` | **REAL** (`ItalyRoadAccidentBodilyInjuryCalculator`) | CALCULATED quando i 4 gate passano (source/dataset/formula/rows tutti `approved`) | D.P.R. 12/2025 (TUN) `approved` + 4 fonti `needs_review` | TUN base + TUN moral (entrambi `approved`) | `italy_art_138_tun_2025_base` `approved` |
| `IT-NATIONAL × inheritance_basic` | n/a | **PLACEHOLDER** (`ItalyInheritanceBasicCalculator`) | Sempre `unavailable_requires_legal_validation` | Codice civile (informativo) | none | none |
| `FR-NATIONAL × road_accident_bodily_injury` | `templates/public/wizard_france_road_accident.html` | **PLACEHOLDER** | Sempre `unavailable…` | Loi Badinter, Mornet 2024, Gazette du Palais (tutte `needs_review`) | none | none |
| `BE-NATIONAL × road_accident_bodily_injury` | `templates/public/wizard_belgium_road_accident.html` | **PLACEHOLDER** | Sempre `unavailable…` | Tableau Indicatif 2020/2024, Tables Schryvers, Loi 1989 (tutte `needs_review`) | none | none |
| `MA-NATIONAL × international_inheritance` | `templates/public/wizard_morocco_inheritance.html` | **PLACEHOLDER** | Sempre `unavailable…` | Moudawana, Code droits réels, EU 650/2012 (tutte `needs_review`) | none | none |
| `TN-NATIONAL × international_inheritance` | `templates/public/wizard_tunisia_inheritance.html` | **PLACEHOLDER** | Sempre `unavailable…` | CSP Livre IX, Loi 98-97, EU 650/2012 (tutte `needs_review`) | none | none |

Riferimenti:

- `apps/calculators/registry.py:93` — registrazioni.
- `apps/calculators/engines/italy.py:86` — engine Italia operativo.
- `apps/calculators/engines/{france,belgium,morocco,tunisia}.py` — placeholder.
- `apps/calculators/enums.py:18` — full `CaseType` choices.
- `apps/calculators/enums.py:41` — `CalculationStatus` choices.

---

## 2. Classificazione automatica vs eccezione umana

### 2.1 — Pair che POSSONO essere automatizzati senza Studio review

| Pair | Motivo |
|------|--------|
| `IT-NATIONAL × road_accident_bodily_injury` | Già operativo. Fonte ufficiale (D.P.R. 12/2025 da Gazzetta Ufficiale), dataset approvato con sha256 ondisk, formula deterministica `italy_art_138_tun_2025_base`, smoke test 35/10/0 → 26 268/27 353/28 439 EUR. **Nessuna review aggiuntiva richiesta** per dati TUN 2025 esistenti. |

### 2.2 — Pair che richiedono `human_exception_review`

| Pair | Motivo (riferito alla regola nuova) |
|------|--------------------------------------|
| `FR-NATIONAL × road_accident_bodily_injury` | **Loi Badinter** (`OFFICIAL_LAW`) può essere sincronizzata come metadata-only: Légifrance restituisce 403 ai client programmatici → richiede manual download + Studio attach. **Mornet 2024** è private barème → `human_exception_review` REQUIRED. **Gazette du Palais** è capitalisation table privata → `human_exception_review`. Engine assente: anche se le tre fonti fossero approved, il calcolatore vero non esiste ancora. |
| `BE-NATIONAL × road_accident_bodily_injury` | **Loi 1989-11-21** è `official_law` ma le fonti operative (Tableau Indicatif, Tables Schryvers) sono private/court_indicative → `human_exception_review`. Engine assente. |
| `MA-NATIONAL × international_inheritance` | **Moudawana / Loi 70-03** è `official_law` (Code de la famille) — sincronizzabile come metadata. **EU 650/2012** è `eu_regulation` ufficiale. Ma il calcolo successioni richiede mapping giuridico interpretativo (livre IX, conflitti di legge) → `human_exception_review` per il calcolatore. Solo i metadata possono essere auto-synced. |
| `TN-NATIONAL × international_inheritance` | **Code du statut personnel** è `official_law` ma JORT 1956 ha host instabili (`pist.tn`) → manual download. Stessa logica MA per il calcolatore. |
| `IT-NATIONAL × inheritance_basic` | Codice civile articoli 565-586 è `official_law` ma le quote successorie hanno casistica articolata (legittima, nuda proprietà, usufrutto coniugale) → `human_exception_review`. |

---

## 3. Cosa cambia con questo iter

1. **Nuovo registry**: `config/official_source_registry.json` cataloga le
   fonti dal punto di vista dell'**automazione** (`source_kind`,
   `can_auto_ingest`, `human_exception_review_required`).
2. **Nuovo command**: `manage.py sync_official_sources` legge il
   registry, scarica solo entries con `can_auto_ingest=true`, salva
   in `legal_data/sources/<country>/official_downloaded/`, calcola
   sha256, scrive manifest, **annota** `LegalSource.notes` con la
   sync metadata. **Mai** crea `LegalReview`/dataset/formula. **Non**
   modifica lo `status` di sources già `APPROVED`.
3. **Vincolo modello**: il `SourceStatus` enum non viene esteso (per
   non introdurre migrazioni rischiose). La traccia "official_synced"
   resta nel manifest JSON + `LegalSource.notes`. Documentato qui per
   trasparenza.
4. **Live simulation matrix**: `scripts/live_simulation_matrix.py`
   esegue una matrice di run engine-level + HTTP per dimostrare:
   - IT 35/10/0 → 26 268/27 353/28 439 EUR (mai cambia).
   - IT 35/10/50 → metà esatta (fault reduction 50%).
   - IT 0/100/0 → max coerente.
   - FR/BE/MA/TN → `unavailable_requires_legal_validation` (sempre).
5. **UX upgrades**: ogni pagina pubblica espone esplicitamente
   "what it does / what it doesn't / next step / module status".

---

## 4. Prossimi target ufficiali (proposta)

In ordine di rapport rischio/valore:

1. **EU Reg. 650/2012** (eur-lex.europa.eu) — `eu_regulation`
   metadata-only sync. Già usato come riferimento da MA + TN landing.
   No calcolatore attivato.
2. **D.P.R. 12/2025 TUN Italia** — già operativo. Verifica periodica
   sha256 e versione decreto.
3. **Loi 70-03 Moudawana** — `official_law` MA via legal-tools.org
   (fallback). Metadata-only.
4. **Code statut personnel TN — Livre IX** (jurisitetunisie.com) —
   `official_law` HTML mirror. Già scaricabile.
5. **Loi Badinter FR** — manual download required (Légifrance 403).
   Resta in `human_exception_review` finché lo Studio non attacca PDF.
6. **Tabelle Tribunale di Milano 2024** — `court_indicative_table`
   non ufficiale: `human_exception_review` sempre.
7. **Tableau Indicatif BE 2024** — `court_indicative_table` non
   ufficiale: `human_exception_review` sempre.

---

## 5. Cosa resta in scope `human_exception_review` permanente

Anche con automazione completa, queste categorie **non** entrano mai
nel pipeline auto-ingest senza firma Studio:

- tabelle giurisprudenziali indicative (Milano, Mornet, Tableau Indicatif);
- baremi privati (Schryvers, Gazette du Palais);
- PDF scansionati che richiedono OCR (Tableau Indicatif 2024 image-scanned);
- mapping conflitti di legge nel diritto internazionale privato;
- formule che richiedono scelta giuridica (es. capitalizzazione lifetime
  da scegliere fra più baremi).

---

## 5b. MA Moudawana — fetch attivo (iter F-official-source-ma-moudawana-fetch-and-trace)

Promosso da `metadata_only` a `fetch` in `config/official_source_registry.json`.

| Field | Valore |
|-------|--------|
| Slug | `ma-code-famille-moudawana-fr-pdf` |
| Source kind | `official_law` |
| Authority | `ministry` (mirror via legal-tools.org) |
| Official URL | `https://www.legal-tools.org/doc/0e057b/pdf/` |
| Final URL | `https://www.legal-tools.org/doc/0e057b/pdf/` |
| HTTP status | `200` |
| Local path | `legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf` |
| Size | 489 071 bytes |
| sha256 | `41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96` |
| File magic | `%PDF` (verified) |
| Classification | `fetch_success` |
| LegalSource status | `needs_review` (NON promosso ad `approved`) |

**Cosa NON è stato attivato:**

- Nessun `LegalReview` creato.
- Nessun `CompensationDataset` creato.
- Nessun `CalculationFormula` creato.
- Nessun `CompensationTableRow` creato.
- Calculator MA × `international_inheritance` resta
  `unavailable_requires_legal_validation` — verificato live via
  `scripts/live_simulation_matrix.py` e via test
  `test_ma_calculator_remains_unavailable_after_fetch`.
- Italia 35/10/0 invariato a 26 268 / 27 353 / 28 439 EUR.

**Cosa serve per arrivare a un engine MA inheritance reale:**

1. **Estrazione tabellare deterministica** del Livre III della
   Moudawana (articoli successione 321-396). Il PDF non è
   machine-readable nativo: serve OCR o text-layer extraction +
   parsing manuale.
2. **Mapping articoli → quote** (asaba / dhawu al-furud /
   ʿawl / radd) con tabelle di riferimento per ogni configurazione
   familiare. Richiede review giurista madrelingua arabo + esperto
   diritto musulmano della famiglia.
3. **Conflitti di legge transfrontalieri** — applicabilità del
   Reg UE 650/2012 ai casi MA-EU, scelta di legge applicabile,
   competenza giurisdizionale. Richiede `human_exception_review`.
4. **Dataset structured + formula `inheritance_share_calculator`**
   approvati. Solo dopo questi 3 step si può rimuovere la
   classificazione `human_exception_review_required` per il
   *calcolatore* (la fonte resta auto-syncable).
5. **Smoke test deterministici** su almeno 5 configurazioni-tipo
   (coniuge + figli, coniuge + genitori, ecc.) prima di esporre
   il calculator al pubblico.

In sintesi: il fetch ufficiale è il **primo gradino**, non
l'ultimo. La fonte è ora tracciabile, hashata e versionabile, ma
il suo uso in un calcolo richiede ancora la pipeline classica
LegalReview → Dataset → Formula → ApprovedRows.

---

## 6. Riferimenti incrociati

- Pacchetto pre-esistente: `download_international_legal_sources` in
  `apps/legal_sources/management/commands/` — scarica FR/BE/MA/TN in
  `legal_data/sources/<country>/downloaded/` con manifest e sha256.
  Il nuovo `sync_official_sources` **non sostituisce** quel command:
  scrive in `official_downloaded/` (cartella separata), e si applica
  **solo** alle fonti classificate ufficiali via registry.
- Stato attuale fonti per paese:
  - `docs/architecture/MOROCCO_INHERITANCE_MODULE_STATUS.md`
  - `docs/architecture/TUNISIA_INHERITANCE_MODULE_STATUS.md`
- Review umana già in pipeline:
  - `legal_data/sources/it/dpr-12-2025/review/` — TUN 2025 review
    pacchetto (gitignore allow-listato per i template).
- Snapshot post-pass2 a11y/SEO: `docs/architecture/PUBLIC_SITE_QA_POLISH_PASS2.md`.
