# GLOBAL — Stato MVP multi-paese

**Iter**: F-global-mvp-status-consolidation · iter1
**Data snapshot**: 2026-04-30
**Stato**: read-only — **nessuna modifica DB, nessun
calculator/wizard toccato, nessun import**.

> Documento di consolidamento dello stato attuale dell'MVP
> Studio Legale Badrane LegalTech. Si basa su un audit
> automatico riproducibile (`scripts/legal_data/audit_global_mvp_status.py`).
> Aggiornare ad ogni iter di promozione/import per non perdere
> il quadro d'insieme.

---

## 0. Sintesi esecutiva (1 schermata)

| Paese | Calculator REAL | Wizard pubblico | LegalSource | LegalReview | Dataset | Formula | Review pkg |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| **IT** | ✅ road accident | ✅ road accident | 5 (1 approved, 4 needs_review) | 2 | 2 (approved, 9 191 + 27 573 rows) | 1 (approved) | — |
| **FR** | ❌ placeholder | scaffold (road accident) | 5 (0 approved) | 0 | 0 | 0 | ✅ |
| **BE** | ❌ placeholder | scaffold (road accident) | 5 (0 approved) | 0 | 0 | 0 | ✅ |
| **MA** | ❌ placeholder | scaffold (inheritance) | 4 (0 approved) | 0 | 0 | 0 | ✅ |
| **TN** | ❌ placeholder | scaffold (inheritance) | 5 (0 approved) | 0 | 0 | 0 | ✅ |

**Totale dataset legali approved: 2 (entrambi IT)**.
**Totale CalculationFormula approved: 1 (IT, art. 138 CAP — TUN 2025)**.
**Totale calcolatori reali nel registry: 1 / 6 registrati**.

---

## 1. Stato per paese

### 1.1 Italia (IT)

**Operativo:**
- Calculator reale: `ItalyRoadAccidentBodilyInjuryCalculator`
  (override di `_compute_with_sources`).
- Wizard pubblico: `/wizard/it/road-accident/`.
- LegalSource `it-dpr-12-2025-tun-danno-biologico` (D.P.R.
  13 gennaio 2025, n. 12) → status `approved` con 2 LegalReview
  firmate (2026-04-27 e 2026-04-29).
- 2 `CompensationDataset` IT in stato `approved`:
  - `DPR-12-2025` — TUN 2025 danno biologico (9 191 righe)
  - `DPR-12-2025-MORAL` — TUN 2025 danno morale (27 573 righe)
- 1 `CalculationFormula` approved:
  - `italy_art_138_tun_2025_base` (`amount_rule =
    row_amount_range_direct`).
- Simulazioni reali calcolate: 3 con `status=calculated`,
  1 con `status=unavailable_requires_legal_validation` (case
  type non operativo).

**Solo scaffold:**
- `ItalyInheritanceBasicCalculator` registrato sulla coppia
  `(IT-NATIONAL, inheritance_basic)` ma non override il
  metodo di compute → ritorna `unavailable_requires_legal_validation`.

**Needs review (4 fonti IT):**
- `it-dlgs-209-2005-cap-art-138-139` (CAP, art. 138/139).
- `it-mimit-2025-07-aggiornamento-art-139` (aggiornamento art.
  139, lesioni di lieve entità).
- `it-mimit-2025-12-aggiornamento-macrolesioni` (aggiornamento
  macrolesioni).
- `it-tabelle-milano-2024` (tabelle Tribunale Milano).

**No-go production (IT):**
- ❌ Wizard `/wizard/it/road-accident/` non è stato testato in
  staging con dati cliente reali end-to-end (verificare).
- ❌ Tabelle Milano 2024 non validate → calcolatore IT usa
  solo TUN 2025; orientamento Tribunale Milano non disponibile.
- ❌ `inheritance_basic` IT è scaffold: il funnel pubblico
  italiano per la successione non è ancora un MVP funzionante.

### 1.2 Francia (FR)

**Operativo:** nessun blocco.

**Scaffold:**
- Calculator: `FranceRoadAccidentBodilyInjuryCalculator`
  (eredita `_FrancePlaceholderCalculator`,
  ritorna sempre `unavailable_requires_legal_validation`).
- Wizard pubblico: `/wizard/fr/road-accident/` (scaffold, raccoglie
  input ma non calcola).

**Candidate (estrazioni read-only on-disk, gitignored):**
- Gazette du Palais 2022 (3 CSV: viagère 416 righe, temporaire
  3 752 righe, anticipated 20 righe).
- Mornet 2024 (4 CSV: DFP 180 righe, affection 11 righe,
  manual fourchettes scaffold 0 righe + 29 review_tasks).

**Needs review (5 fonti FR):**
- `fr-loi-badinter-1985` (manual_download_required).
- `fr-nomenclature-dintilhac-2005`.
- `fr-referentiel-mornet-2024`.
- `fr-bareme-capitalisation-gazette-palais-2022`.
- `fr-bareme-capitalisation-gazette-palais-2025-page` (HTML
  landing 2025; PDF 2025 non scaricato).

**Manual download required:**
- `fr-loi-badinter-1985` (Legifrance HTTP 403 per UA non-browser).

**Review package pronto:**
- `docs/legal_sources/FRANCE_LEGAL_REVIEW_PACKAGE.md` ✅
- `legal_data/sources/france/review/france_legal_review_checklist_template.csv`
  (23 righe `pending`) ✅

**No-go production (FR):**
- ❌ Nessuna LegalSource approved.
- ❌ Nessun dataset, nessuna formula.
- ❌ Calculator FR è placeholder: non può produrre alcun
  importo.

### 1.3 Belgio (BE)

**Operativo:** nessun blocco.

**Scaffold:**
- Calculator: `BelgiumRoadAccidentBodilyInjuryCalculator`
  (placeholder).
- Wizard pubblico: `/wizard/be/road-accident/` (scaffold).

**Candidate (estrazioni read-only on-disk, gitignored):**
- Tableau Indicatif 2020 (4 CSV: souffrances 63 righe,
  esthétique/indemnité forfaitaire 71 righe, décès affection
  13 righe, véhicule remplacement 19 righe).
- Tableau Indicatif 2024 — **OCR spike** documentato in
  `BELGIUM_TI_2024_OCR_SPIKE_REPORT.md`. PDF image-scanned;
  language pack `fra`/`nld` Tesseract mancanti. Non pronto.

**Needs review (5 fonti BE):**
- `be-loi-1989-11-21-rc-auto`.
- `be-tableau-indicatif-2020` (candidate da promuovere a
  `approved` come historical_fallback).
- `be-tableau-indicatif-2024` (NON pronto — OCR insufficiente).
- `be-tables-schryvers-2026-page` (landing).
- `be-tables-schryvers-tableurs` (HTML aggregato).

**Manual download required:**
- (nessun item formalmente flaggato manual_required nel
  manifest BE; ma BE 2024 richiede nuovo iter OCR con
  language pack installati lato Studio.)

**Review package pronto:**
- `docs/legal_sources/BELGIUM_LEGAL_REVIEW_PACKAGE.md` ✅
- `legal_data/sources/belgium/review/belgium_legal_review_checklist_template.csv`
  (21 righe `pending`) ✅
- `BELGIUM_TI_2024_OCR_SPIKE_REPORT.md` ✅ (già committato)

**No-go production (BE):**
- ❌ Nessuna LegalSource approved.
- ❌ BE 2020 va promosso solo come `historical_fallback`
  (BE 2024 ufficiale non disponibile).
- ❌ Calculator BE è placeholder.

### 1.4 Marocco (MA)

**Operativo:** nessun blocco.

**Scaffold:**
- Calculator: `MoroccoInternationalInheritanceCalculator`
  (placeholder).
- Wizard pubblico: `/wizard/ma/inheritance/` (scaffold qualitativo,
  no calcolo).

**Candidate:** nessuno. Il package MA è **mapping-only**: si
producono CSV strutturati di quote faraïd solo dopo che lo
Studio ha completato il mapping legale.

**Needs review (4 fonti MA):**
- `ma-code-famille-moudawana-fr-pdf` (PDF, high).
- `ma-code-droits-reels-loi-39-08` (PDF, high).
- `ma-code-droits-reels-traduction-aute` (PDF, **medium** —
  traduzione non ufficiale).
- `eu-regulation-650-2012-successions-fr-ma` (manual_required).

**Manual download required:**
- `eu-regulation-650-2012-successions-fr-ma` (EUR-Lex HTTP 202
  con body vuoto per richieste non-browser).

**Review package pronto:**
- `docs/legal_sources/MOROCCO_LEGAL_REVIEW_PACKAGE.md` ✅
- `legal_data/sources/morocco/review/morocco_legal_review_checklist_template.csv`
  (21 righe `pending`) ✅

**No-go production (MA):**
- ❌ Nessuna LegalSource approved.
- ❌ Nessun mapping legale degli articoli Moudawana
  (faraïd, ḥajb, ʿawl, radd) — il calcolo è impossibile
  finché lo Studio non firma il mapping.
- ❌ Calculator MA è placeholder.

### 1.5 Tunisia (TN)

**Operativo:** nessun blocco.

**Scaffold:**
- Calculator: `TunisiaInternationalInheritanceCalculator`
  (placeholder).
- Wizard pubblico: `/wizard/tn/inheritance/` (scaffold qualitativo,
  no calcolo).

**Candidate:** nessuno. Stesso pattern MA: mapping-only.

**Needs review (5 fonti TN):**
- `tn-code-statut-personnel-livre-ix-succession` (HTML, high).
- `tn-code-dip-loi-98-97` (HTML, official — Code DIP).
- `tn-jort-code-statut-personnel-1956` (manual_required).
- `tn-code-statut-personnel-compiled` (manual_required).
- `eu-regulation-650-2012-successions-fr-tn` (manual_required).

**Manual download required:**
- `tn-jort-code-statut-personnel-1956` (pist.tn ConnectTimeout).
- `tn-code-statut-personnel-compiled` (jafbase.fr SSL hostname mismatch).
- `eu-regulation-650-2012-successions-fr-tn` (EUR-Lex).

**Review package pronto:**
- `docs/legal_sources/TUNISIA_LEGAL_REVIEW_PACKAGE.md` ✅
- `legal_data/sources/tunisia/review/tunisia_legal_review_checklist_template.csv`
  (26 righe `pending`) ✅

**No-go production (TN):**
- ❌ Nessuna LegalSource approved.
- ❌ Nessun mapping CSP / Loi 98-97 firmato.
- ❌ Doppia regola di conflitto (Loi 98-97 vs Reg. 650/2012)
  non risolta.
- ❌ Calculator TN è placeholder.

---

## 2. Calculator registry (consolidato)

| Jurisdiction | Case type | Class | Stato |
|---|---|---|:---:|
| `BE-NATIONAL` | `road_accident_bodily_injury` | `BelgiumRoadAccidentBodilyInjuryCalculator` | PLACEHOLDER |
| `FR-NATIONAL` | `road_accident_bodily_injury` | `FranceRoadAccidentBodilyInjuryCalculator` | PLACEHOLDER |
| `IT-NATIONAL` | `inheritance_basic` | `ItalyInheritanceBasicCalculator` | PLACEHOLDER |
| `IT-NATIONAL` | `road_accident_bodily_injury` | `ItalyRoadAccidentBodilyInjuryCalculator` | **REAL** |
| `MA-NATIONAL` | `international_inheritance` | `MoroccoInternationalInheritanceCalculator` | PLACEHOLDER |
| `TN-NATIONAL` | `international_inheritance` | `TunisiaInternationalInheritanceCalculator` | PLACEHOLDER |

Heuristica REAL vs PLACEHOLDER: la leaf class è REAL se
sovrascrive `_compute_with_sources` nel proprio `__dict__`.
Tutti i placeholder ereditano dal parent un `_compute_with_sources`
che ritorna sempre `unavailable_requires_legal_validation`.

---

## 3. Wizard pubblici (route attive)

| URL | Vista | Stato |
|---|---|:---:|
| `/wizard/` | `wizard_start` | router |
| `/wizard/it/road-accident/` | `wizard_italy_road_accident` | **operativo** |
| `/wizard/fr/road-accident/` | `wizard_france_road_accident` | scaffold |
| `/wizard/be/road-accident/` | `wizard_belgium_road_accident` | scaffold |
| `/wizard/ma/inheritance/` | `wizard_morocco_inheritance` | scaffold |
| `/wizard/tn/inheritance/` | `wizard_tunisia_inheritance` | scaffold |
| `/wizard/result/<uuid>/` | `wizard_result` | viewer |

I wizard scaffold raccolgono input tramite form `*WizardForm`
ma il calculator chiamato risponde
`unavailable_requires_legal_validation`. Il report PDF generato
indica esplicitamente lo stato.

---

## 4. Review packages già pronti

Tutti committati nella repo (versionati):

| Paese | Package doc | Checklist template | Righe pre-popolate |
|---|---|---|---:|
| FR | `FRANCE_LEGAL_REVIEW_PACKAGE.md` (26 334 B) | `france_legal_review_checklist_template.csv` (5 091 B) | 23 |
| BE | `BELGIUM_LEGAL_REVIEW_PACKAGE.md` (26 946 B) | `belgium_legal_review_checklist_template.csv` (4 559 B) | 21 |
| MA | `MOROCCO_LEGAL_REVIEW_PACKAGE.md` (19 323 B) | `morocco_legal_review_checklist_template.csv` (3 748 B) | 21 |
| TN | `TUNISIA_LEGAL_REVIEW_PACKAGE.md` (21 027 B) | `tunisia_legal_review_checklist_template.csv` (5 048 B) | 26 |

**Italia** non ha review package perché è già parzialmente
operativo: il flusso di promozione IT è stato eseguito riga
per riga su `it-dpr-12-2025-tun-danno-biologico` con 2
`LegalReview` firmate. Le 4 fonti IT residue restano in
`needs_review` come backlog, senza package formale.

---

## 5. File NON committabili (gitignored)

Percorsi on-disk che NON entrano in git ma sono tracciati
dal manifest JSON (committabile):

| Path | Tipo | Note |
|---|---|---|
| `legal_data/sources/{italy,france,belgium,morocco,tunisia}/downloaded/*.pdf` | PDF ufficiali | Hash nei manifest. |
| `…/downloaded/*.html` | HTML scaricati | Hash nei manifest. |
| `legal_data/sources/france/gazette_2022/*.csv` | Candidate FR | 3 file. |
| `legal_data/sources/france/mornet_2024/*.csv` | Candidate FR | 4 file. |
| `legal_data/sources/belgium/tableau_indicatif_2020/*.csv` | Candidate BE | 4 file. |
| `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/` | OCR spike output | 7 file (PNG, TXT, JSON). |
| `legal_data/sources/*/extraction_summary.json` | Audit di estrazione | Committabile (non in regola gitignore) — ma è un manifesto, non un dato. |
| `db.sqlite3` | DB locale | **Solo dev**. PostgreSQL in produzione. |
| `backups/db_*.sqlite3` | Backup locali | Mai committare. |

**Eccezione importante:** `legal_data/sources/*/review/*_template.csv`
sono COMMITTABILI (eccezione gitignore esplicita). Sono solo
template di checklist con `status=pending`, no valori legali.

---

## 6. Mappa prossimi step per paese

(Cross-ref con `docs/architecture/LOCAL_NEXT_STEPS.md` per
la roadmap unificata.)

### IT
1. Promuovere fonti residue (`it-tabelle-milano-2024`, ecc.)
   o lasciarle in needs_review se fuori scope MVP.
2. Definire scope `inheritance_basic` IT o degradarlo a
   "non MVP".
3. Hardening del wizard road accident esistente (E2E test,
   stress su input edge case).

### FR
1. `F-france-studio-review-iter1`: Studio compila checklist.
2. `F-france-import-datasets-readonly-seed` (post-GO): seed
   datasets approved.
3. `F-france-calculator-skeleton`: implementare engine reale.
4. `F-france-wizard-public-rollout`: feature flag attivato.

### BE
1. `F-belgium-studio-review-iter1`: Studio compila checklist
   (incl. decisione tassonomica B2 e formula camions B4).
2. `F-belgium-import-datasets-readonly-seed-2020` (post-GO):
   seed BE 2020 come `historical_fallback`.
3. `F-belgium-calculator-skeleton` (consume BE 2020).
4. `F-belgium-tesseract-langpack-install` (extra-Claude):
   sblocca BE 2024.
5. `F-belgium-ocr-ti-2024-fra-nld-spike`: re-spike OCR.
6. `F-belgium-ti-2024-extraction-with-manual-review`.
7. `F-belgium-migrate-2020-to-2024` (replaced).

### MA
1. `F-eu-650-2012-manual-download-attach`: lo Studio recupera
   il PDF EUR-Lex.
2. `F-morocco-studio-mapping-iter1`: mapping articoli
   Moudawana + Code droits réels.
3. `F-morocco-moudawana-quotes-extraction-manual` (post-GO):
   trascrizione strutturata delle quote faraïd.
4. `F-morocco-import-datasets-readonly-seed`.
5. `F-morocco-inheritance-calculator-engine` (sostituisce
   placeholder).
6. `F-morocco-inheritance-wizard-public`.

### TN
1. `F-tunisia-manual-downloads-attach`: lo Studio recupera
   JORT 1956, CSP compiled, Reg. 650/2012.
2. `F-tunisia-studio-mapping-iter1`: mapping CSP Livre IX +
   Loi 98-97 + posizione su renvoi/ordine pubblico.
3. `F-tunisia-csp-quotes-extraction-manual`.
4. `F-tunisia-import-datasets-readonly-seed`.
5. `F-tunisia-inheritance-calculator-engine`.
6. `F-tunisia-inheritance-wizard-public`.

---

## 7. No-go production (consolidato)

**Vietato in produzione finché tutti i criteri sotto non sono
soddisfatti — anche solo per un paese specifico.**

### 7.1 Cross-paese
- ❌ Nessuna feature flag `enable_*_calculator=true` può essere
  abilitata in production senza:
  1. LegalSource approved per quella giurisdizione/case_type;
  2. CompensationDataset approved con righe legate alla fonte;
  3. CalculationFormula approved con `parameters.engine`
     registrato in `apps.compensation.services`;
  4. Test E2E sul wizard pubblico verde.
- ❌ Nessun import DB di CSV gitignored finché il flusso di
  `LegalReview` non è stato eseguito riga per riga (vedi
  precedente `LegalReview` IT come template).
- ❌ Nessun report PDF utente che mostri valori monetari
  derivati da fonti `needs_review`.
- ❌ Nessun deploy in produzione finché il setup PostgreSQL
  + Redis + Celery + report PDF + email lead non è hardened.

### 7.2 Specifici
- IT: `inheritance_basic` non promuovibile a wizard pubblico
  finché placeholder (lo è oggi).
- FR/BE: bloccati da review Studio. Calculator placeholder
  non rimuovibile.
- MA: `int_inheritance` bloccato da mapping Moudawana.
- TN: `int_inheritance` bloccato da mapping CSP **e** decisione
  scritta sulla doppia regola di conflitto.

---

## 8. Roadmap consigliata locale-first, deploy solo alla fine

Vedi documento dettagliato:
**`docs/architecture/LOCAL_NEXT_STEPS.md`**.

In sintesi (per evitare deploy prematuro):

1. **Fase A — Studio review** (FR + BE + MA + TN, in parallelo):
   review umana di tutti i 4 checklist. Output: GO/NO-GO per
   ciascun blocco. **Locale only**. Nessun cambio produzione.
2. **Fase B — Import FR/BE post-review**: seed datasets +
   formule, sostituzione placeholder con engine reali.
   **Locale only**. Test verde.
3. **Fase C — Mapping MA/TN**: trascrizione quote faraïd post
   mapping firmato. **Locale only**.
4. **Fase D — Hardening prodotto**: PostgreSQL, Celery,
   reportistica PDF, GDPR, accessibility, SEO multilingua.
   **Staging deployable**.
5. **Fase E — Deploy finale**: production rollout per paese,
   feature flag per paese, monitoring, audit log.

Il principio: **niente production deploy** finché almeno un
caso d'uso end-to-end **non IT** è funzionante in staging
con dati validati.

---

## 9. Audit riproducibile

Per ricostruire questo snapshot in qualunque momento:

```bash
.venv/Scripts/python.exe scripts/legal_data/audit_global_mvp_status.py
```

Lo script è read-only (no DB writes, no file mutations) e
stampa LegalSource, LegalReview, Dataset, Formula, registry,
Simulation, Lead, SimulationReport, presenza review packages,
artifacts on-disk.

---

## 10. Disclaimer

Il presente documento è una **snapshot** dello stato MVP a
una data specifica. Ogni dato (calculatori registrati, fonti
approved, dataset, formule, simulazioni) può cambiare nel
tempo. La "verità di sistema" è data dal DB locale e dal
codice; questo documento è un riassunto consultabile e
verificabile via audit script. Il disclaimer obbligatorio
CLAUDE.md resta valido per ogni simulazione pubblicata.
