# Primo paese non-IT — piano di attivazione controllato

**Branch di lavoro:** `product/go-live-readiness-p0`
**Data:** 2026-05-13
**Scope:** analisi maturità Francia vs Belgio + raccomandazione + piano tecnico passo-passo.

> Documento di **pianificazione**: non promuove nulla a `approved`.
> Tutte le promozioni richiedono `LegalReview` firmata dallo Studio.
> Il gating "meglio nessun calcolo che un calcolo falso" resta in vigore.
>
> Fonti di questo piano:
> - `docs/architecture/GLOBAL_MVP_STATUS.md`
> - `docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md`
> - `docs/architecture/BELGIUM_MODULE_STATUS.md`
> - `docs/architecture/FRANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md`
> - `docs/architecture/BELGIUM_ENGINE_INACTIVE_FIXTURE_ONLY.md`
> - Codice live: `apps/calculators/engines/france.py`, `belgium.py`.

---

## 1. Quadro comparativo (executive summary)

| Dimensione | Francia | Belgio |
|---|---|---|
| **Fonti modellate (`LegalSource`)** | 5 (Loi Badinter, Dintilhac, Mornet 2024, Gazette du Palais 2022, Gazette landing 2025) | 4 (Loi 1989, Code civil 1382-1383, Tableau indicatif 2020, Barème Schryvers 2020) |
| **Fonti già `approved`** | 0 (Badinter è "PASS structural" ma `status=needs_review`) | 0 |
| **Dataset DRAFT in DB** | 2 (`FR-MORNET-2024-DRAFT`, `FR-GAZETTE-PALAIS-2022-DRAFT`) | 0 (CSV su disco, non ancora importati in DB) |
| **CSV su disco** | 4 (Mornet) + 3 (Gazette) | 4 (Tableau Indicatif 2020 per perimetro) + spike OCR 2024 |
| **`LegalReview` firmate** | 0 | 0 |
| **Engine class registrata** | `FranceRoadAccidentBodilyInjuryCalculator` (placeholder) | `BelgiumRoadAccidentBodilyInjuryCalculator` (placeholder) |
| **Engine ID in `SUPPORTED_ENGINES`** | `france_road_accident_v1` ✓ | `belgium_road_accident_v1` ✓ |
| **Amount rules in `SUPPORTED_AMOUNT_RULES`** | `france_dfp_point_value_direct` (single-row-range) | 3 rules: `belgium_souffrances_age_severity_direct`, `belgium_forfait_age_annual_direct`, `belgium_deces_affection_relation_direct` |
| **`CalculationFormula` in DB** | 0 (corretto: gating refuses) | 0 |
| **Wizard pubblico raggiungibile** | `/wizard/fr/road-accident/` (scaffold) ✓ | `/wizard/be/road-accident/` (scaffold) ✓ |
| **Test fixture-only verdi** | 2 file test FR | 2 file test BE (`test_belgium_engine_inactive.py`) |
| **Rischio editoriale fonti** | Alto: Mornet è barème privato, Gazette è jurisprudenziale | Medio: Loi 1989 e Code civil sono fonti ufficiali; tableau indicatif è giurisprudenziale ma con tradizione consolidata |
| **Complessità engine economico** | Medio: 1 amount rule wired (DFP per punto); capitalizzazione futura | Alto: 4 perimetri di danno (ITT, IPP, pretium doloris, dommage esthétique, perte revenus); 3 rules già wired, 1 ancora pending |
| **Effort stimato dev** | 1-2 settimane (override engine + formula + smoke test E2E) | 2-3 settimane (import dataset + override engine + 3 rule paths + smoke test) |
| **Effort stimato Studio** | 2-4 settimane (review 2 fonti + decisione editoriale Mornet/Gazette) | 2-4 settimane (review 4 fonti + decisione editoriale tableau) |

---

## 2. Francia — dettaglio

### 2.1 Fonti

| Slug | Tipo | Stato | Maturità |
|---|---|---|---|
| `fr-loi-badinter-1985` | OFFICIAL_LAW | `needs_review` | Manual attach + 11/11 structural markers vs Légifrance. Pronta per promozione una volta che Studio firma `LegalReview`. |
| `fr-nomenclature-dintilhac-2005` | DOCTRINE | `needs_review` | Cornice tassonomica (categorie di danno), non produce numeri. |
| `fr-referentiel-mornet-2024` | DOCTRINE / private référentiel | `needs_review`, reliability=HIGH | Nessun `LegalSourceAttachment`, `legal_reviewer=unset`. **Decisione editoriale richiesta**: Mornet è non-statale. Studio deve accettare esplicitamente di usarlo come base di quantificazione. |
| `fr-bareme-capitalisation-gazette-palais-2022` | DOCTRINE / jurisprudenziale | `needs_review`, reliability=HIGH | Stesso discorso: tabella di capitalizzazione editoriale. Decisione editoriale Studio. |
| `fr-bareme-capitalisation-gazette-palais-2025-page` | DOCTRINE | `needs_review` | PDF 2025 non scaricato; landing HTML solo. |

### 2.2 Dataset

| Dataset | Stato | Righe | Note |
|---|---|---|---|
| `FR-MORNET-2024-DRAFT` | `draft` (gating refuses use) | `fr_dfp_per_age_disability_amount_per_point=180/180` + `fr_prejudice_affection_per_relation_amount=11/11` | Maturo per promozione una volta che Mornet source è approved. |
| `FR-GAZETTE-PALAIS-2022-DRAFT` | `draft` | `viagère 416 + temporaire 3752 + anticipated 20 = 4188 righe` | Maturo per promozione una volta che Gazette source è approved. |

### 2.3 Formula

- **0 `CalculationFormula` in DB FR**. Corretto: il gating dei `compensation.services` rifiuta di scrivere formula su dataset DRAFT.

### 2.4 Engine

- `FranceRoadAccidentBodilyInjuryCalculator` esiste e estende `_FrancePlaceholderCalculator`.
- `_FrancePlaceholderCalculator._compute_with_sources` ritorna sempre `unavailable_requires_legal_validation`.
- **Per produrre numeri**: bisogna scrivere un metodo `_compute_with_sources` reale che:
  1. Lookup `CalculationFormula(approved, engine=france_road_accident_v1)`.
  2. Lookup dataset secondari via `parameters` (per single-row-range).
  3. Ritorni `CalculationResult` con min/mid/max.

### 2.5 Test

- `test_france_engine_inactive_fixture_only.py` — fixture-only, verifica che con source/dataset/formula approved IN TEST il calculator producesse output (oggi: placeholder return).
- `test_france_review_gated_e2e_p0_mvp_1.py` — verifica che il funnel pubblico rispetti il gating.

### 2.6 Blockers per attivazione FR

1. `LegalReview.decision=approve` su `fr-loi-badinter-1985`.
2. `LegalReview.decision=approve` su `fr-referentiel-mornet-2024` (decisione editoriale).
3. `LegalReview.decision=approve` su `fr-bareme-capitalisation-gazette-palais-2022` (decisione editoriale, se necessario per capitalizzazione).
4. Relabel datasets DRAFT → `APPROVED` (`FR-MORNET-2024`, `FR-GAZETTE-PALAIS-2022`).
5. Creazione `CalculationFormula(approved, engine=france_road_accident_v1, amount_rule=france_dfp_point_value_direct, parameters={...})`.
6. Override `FranceRoadAccidentBodilyInjuryCalculator._compute_with_sources` con codice reale (rimuovere ereditarietà placeholder).
7. Test E2E: form `/wizard/fr/road-accident/` con input reali → `Simulation.status=calculated`.
8. Test deontologico: verificare che warnings ed disclaimer siano in francese accurato (review Studio).
9. Aggiornamento `docs/architecture/GLOBAL_MVP_STATUS.md`.

### 2.7 Rischi attivazione FR

- **Editoriale**: Mornet/Gazette sono fonti non ufficiali. Se viene messa in discussione la scelta editoriale, Studio deve poter spiegare e difendere.
- **Aggiornamento annuale**: Mornet pubblica nuove edizioni; serve processo di refresh annuale.
- **Capitalizzazione**: il calcolo del danno futuro richiede Gazette (per ora 2022; 2025 esiste come landing HTML ma PDF non recuperato).

---

## 3. Belgio — dettaglio

### 3.1 Fonti

| Slug | Tipo | Stato | Maturità |
|---|---|---|---|
| `be-loi-1989-11-21-assurance-rc-auto` | OFFICIAL_LAW | `needs_review` | Cornice normativa RCA. Pronta per promozione. |
| `be-code-civil-art-1382-1383` | OFFICIAL_LAW | `needs_review` | Responsabilità extracontrattuale. Pronta. |
| `be-tableau-indicatif-cours-tribunaux-2020` | COURT_TABLE | `needs_review`, reliability=HIGH | Tabella giurisprudenziale, ampia tradizione. **Decisione editoriale**: usarla come base di quantificazione. CSV per perimetro presenti su disco (`legal_data/sources/belgium/tableau_indicatif_2020/`). |
| `be-bareme-capitalisation-schryvers-2020` | COURT_TABLE | `needs_review`, reliability=HIGH | Coefficienti capitalizzazione (rendite vitalizie). Necessario solo se si vuole calcolare rendite. |

### 3.2 Dataset

- **0 dataset BE in DB**. CSV su disco ma command di import non ancora eseguito.
- Differenza chiave vs FR: in FR i dataset DRAFT esistono già; in BE bisogna prima importarli da CSV → DRAFT, poi promuovere a APPROVED.

### 3.3 Formula

- 0 `CalculationFormula` in DB BE.

### 3.4 Engine

- `BelgiumRoadAccidentBodilyInjuryCalculator` placeholder.
- 3 amount rules registrati (`SUPPORTED_AMOUNT_RULES`):
  - `belgium_souffrances_age_severity_direct` (pretium doloris)
  - `belgium_forfait_age_annual_direct` (ITT/IPP forfait annuale)
  - `belgium_deces_affection_relation_direct` (préjudice affection da decesso)
- **4° perimetro non ancora wired**: vehicule de remplacement / perte de revenus complessa.

### 3.5 Test

- `test_belgium_engine_inactive_fixture_only.py` — fixture-only, smoke verde.
- Test canarino IT (35/10/0 → 26 268/27 353/28 439) presente nello stesso file: garantisce che modifiche BE non rompano IT.

### 3.6 Blockers per attivazione BE

1. `LegalReview.decision=approve` su 4 fonti (almeno Loi 1989 + Tableau indicatif sono obbligatorie per il primo rilascio).
2. **Import command** che legge i CSV in `legal_data/sources/belgium/tableau_indicatif_2020/` → crea `CompensationDataset(status=DRAFT)` con righe per perimetro (oggi non esiste un command pronto come per FR — verificare in `apps/legal_sources/management/commands/` se esiste `import_belgium_*` o crearlo).
3. Promozione dataset DRAFT → APPROVED post review legale.
4. Creazione `CalculationFormula(approved, engine=belgium_road_accident_v1, amount_rule=<una delle 3>, parameters={...})`. **Probabilmente 3 formule separate**, una per perimetro, oppure una sola che orchestra le 3.
5. Override `BelgiumRoadAccidentBodilyInjuryCalculator._compute_with_sources` con codice reale.
6. Test E2E `/wizard/be/road-accident/`.

### 3.7 Rischi attivazione BE

- **Complessità engine**: 4 perimetri di danno diversi (ITT, IPP, pretium doloris, dommage esthétique). Più di FR (che ha sostanzialmente DFP per punto + affection).
- **Import dataset non scriptato**: vs FR dove i CSV sono già stati importati in DRAFT, in BE bisogna prima scrivere/eseguire l'import. Possibile riuso del pattern FR.
- **Lingua del calcolo**: il Belgio è multilingue (FR/NL/DE); ma il sito oggi offre FR/EN/AR. NL/DE non sono supportati. Decidere se rilasciare BE solo FR.

---

## 4. Raccomandazione finale

### Belgio o Francia come primo paese non-IT?

**RACCOMANDAZIONE: FRANCIA.**

Motivazione:

1. **Dataset più maturi in DB**: FR ha 2 dataset DRAFT già importati; BE ha solo CSV su disco. **Risparmio di 3-5 giorni dev** per skippare il command di import.
2. **Engine più semplice**: 1 amount rule da orchestrare (DFP per punto) vs 3+1 in BE. Codice di override più piccolo, meno test, meno superficie di errore.
3. **Quadro normativo più chiaro**: Badinter + Mornet sono molto usate nell'ambiente RCA francese; lo Studio probabilmente ha già esperienza diretta nel difendere queste fonti.
4. **Test E2E pre-esistenti**: `test_france_engine_inactive_fixture_only.py` ha già 2 test fixture-only che verificano il flusso quando source/dataset/formula sono tutti APPROVED. Smoke E2E "gratis" una volta promossi i dati.
5. **i18n già al 47%** anche per FR (vedi `docs/architecture/I18N_TRANSLATION_STATUS.md`).

**Belgio resta una scelta valida**, ma a costo maggiore. Considerarlo come **secondo paese non-IT** dopo Francia (slot dopo FR live in produzione).

### Effort consolidato Francia

- **Studio**: 2-4 settimane per review legale + decisione editoriale Mornet/Gazette.
- **Dev**: 1-2 settimane per:
  - Override `_compute_with_sources` reale.
  - Creazione `CalculationFormula` approved.
  - Test E2E `/wizard/fr/road-accident/` con valori reali.
  - Aggiornamento docs (`GLOBAL_MVP_STATUS.md`, `FRANCE_MODULE_STATUS.md`).
- **Smoke QA**: 1-2 giorni (eseguire QA-07 cross-border FR/BE + QA-01 canarino IT per regression).

**Totale realistico**: ~5-7 settimane dal momento in cui Studio decide di partire con FR.

---

## 5. Sequenza operativa Francia (passo-passo)

### Fase A — Studio (review legale)

1. Studio rivede:
   - `legal_data/sources/france/` (manifest + file scaricati).
   - Testo Badinter (Légifrance link in `LegalSource.official_url`).
   - Édition 2024 di Mornet (decisione editoriale).
   - Gazette du Palais 2022 (decisione editoriale).
2. Per ciascuna fonte rivede:
   - Validità temporale (`effective_date`, `valid_until`).
   - Coefficienti/tabelle estratti (riga per riga, almeno spot check).
3. Per ciascuna fonte firma un `LegalReview`:
   - `decision = approve`
   - `reviewer = <utente staff Studio>`
   - `notes = <eventuali note metodologiche>`
   - `decided_at = <data firma>`
4. Conseguentemente `LegalSource.status = approved` per le fonti revisionate.

### Fase B — Dev (promozione tecnica)

1. Per ogni dataset DRAFT:
   - Rinomina `version_label` da `FR-MORNET-2024-DRAFT` a `FR-MORNET-2024`.
   - Setta `status = APPROVED`.
   - Solo dopo che la `LegalSource` correlata è `approved`.
2. Crea `CalculationFormula`:
   ```python
   CalculationFormula.objects.create(
       dataset=<FR-MORNET-2024 dataset>,
       code="france_dfp_mornet_2024_base",
       parameters={
           "engine": "france_road_accident_v1",
           "amount_rule": "france_dfp_point_value_direct",
           "requires": ["victim_age", "permanent_disability_percentage"],
           "row_match": ["victim_age", "permanent_disability_percentage"],
           ...
       },
       status=DatasetStatus.APPROVED,
   )
   ```
   (Parametri precisi: verificare in `apps/compensation/services.py` cosa si aspetta `france_dfp_point_value_direct`.)
3. Refactor `apps/calculators/engines/france.py`:
   - Override `_compute_with_sources` su `FranceRoadAccidentBodilyInjuryCalculator` (rimuove ereditarietà placeholder).
   - Riusa eventualmente codice da `ItalyRoadAccidentBodilyInjuryCalculator` come riferimento (single-row-range pattern).
4. Test mirati:
   ```
   pytest -q apps/calculators/test_france_*.py
   pytest -q apps/cases/test_france_*.py
   ```
5. Test regressione canarino IT (deve restare invariato):
   ```
   pytest -q apps/calculators/test_belgium_engine_inactive.py::test_canarino_italia_invariante
   ```

### Fase C — Smoke staging

1. Deploy del branch su staging.
2. Smoke test E2E via browser:
   - Apri `/fr/wizard/fr/road-accident/`
   - Compila con valori realistici (es. victim_age=30, disability=15%, fault=0%)
   - Submit
   - Verifica `Simulation.status = calculated`, importi positivi, fonti citate (Mornet + Badinter)
3. Verifica deontologica:
   - Disclaimer francese corretto
   - Warning corretti
   - Sources cliccabili e puntano a Légifrance / Gazette
4. QA-07 (cross-border FR/BE) eseguito.

### Fase D — Produzione

1. Solo dopo che smoke staging è verde + `manage.py check --deploy` clean.
2. Deploy tag.
3. Aggiornamento `docs/architecture/GLOBAL_MVP_STATUS.md`: FR passa da "scaffold" a "live".
4. Eventuale annuncio Studio (sito madre + canali comunicazione).

---

## 6. Smoke test post-attivazione

Una volta che FR è live in prod:

```python
# canarino IT — DEVE rimanere identico
sim_it = run_simulation('IT-NATIONAL', 'road_accident_bodily_injury',
    {'victim_age':35, 'permanent_disability_percentage':10, 'fault_percentage':0})
assert (int(sim_it.estimated_min), int(sim_it.estimated_mid), int(sim_it.estimated_max)) == (26268, 27353, 28439)

# nuovo: FR produce un numero
sim_fr = run_simulation('FR-NATIONAL', 'road_accident_bodily_injury',
    {'victim_age':30, 'permanent_disability_percentage':15, 'fault_percentage':0})
assert sim_fr.status == 'calculated'
assert sim_fr.estimated_min > 0
assert sim_fr.estimated_mid > 0
assert sim_fr.estimated_max > 0
assert len(sim_fr.sources_snapshot) >= 1  # almeno Badinter o Mornet citate
```

---

## 7. Cosa NON fare

- **Non promuovere `LegalSource.status=approved` senza `LegalReview` firmata.** Il sistema lo permette tecnicamente (no constraint DB), ma viola la regola d'oro.
- **Non importare Mornet/Gazette PDF freschi senza confronto SHA-256 con Légifrance / sito editore.**
- **Non skippare il refactor del placeholder.** Anche con source/dataset/formula approved, `_FrancePlaceholderCalculator._compute_with_sources` ritorna sempre `unavailable`. Il refactor è obbligatorio.
- **Non modificare il canarino IT** in alcun modo. Tutti i test BE/FR/MA/TN verificano che IT 35/10/0 resti 26 268/27 353/28 439.

---

## 8. Documenti correlati

- `docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md` — audit profondo FR.
- `docs/architecture/BELGIUM_MODULE_STATUS.md` — stato BE.
- `docs/architecture/FRANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md` — pattern fixture-only FR.
- `docs/architecture/BELGIUM_ENGINE_INACTIVE_FIXTURE_ONLY.md` — pattern fixture-only BE.
- `docs/architecture/MULTI_COUNTRY_PATTERN.md` — pattern generale di attivazione paese.
- `docs/go_live/GO_LIVE_READINESS_MATRIX_2026-05-13.md` — Area 19.
