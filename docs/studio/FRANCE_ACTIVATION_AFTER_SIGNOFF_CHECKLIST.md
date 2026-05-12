# Francia — checklist dev post-firma

**Per**: dev che attiverà la Francia dopo che lo Studio ha firmato.
**Pre-condizione**: `FRANCE_SIGNOFF_DECISION_FORM.md` consegnato dallo Studio con esito `GO` (o `GO con correzioni` con correzioni completate) — sezione F firmata.
**Branch target**: `P0-MVP-1-ACTIVATE-france` (nuovo, da creare al momento dell'attivazione).
**Effort stimato**: ~1 giorno dev (passaggi in admin + scrittura test smoke + verifiche).

Questo è il piano operativo concreto. Va eseguito **solo dopo aver ricevuto il modulo firmato**. Non eseguire passi sotto senza il modulo. Ogni passo ha una verifica esplicita.

---

## 0 — Pre-flight

Prima di iniziare qualunque promozione:

- [ ] Modulo firmato `FRANCE_SIGNOFF_DECISION_FORM.md` ricevuto e archiviato (PDF firmato o documento Markdown editato + scan/email di conferma del reviewer).
- [ ] Verifica che le 4 sezioni (A, B, C, D) abbiano esito "Approvato" o "Approvato con correzioni" e che le eventuali correzioni siano state applicate prima di procedere.
- [ ] Verifica che le 3 sezioni E (smoke numbers) abbiano valori firmati.
- [ ] Verifica che la sezione F sia in stato `GO` o `GO con correzioni completate`.
- [ ] Crea il branch:

```bash
git checkout audit/indennizzati-platform
git pull   # se applicabile
git checkout -b P0-MVP-1-ACTIVATE-france
```

- [ ] Esegui l'audit pre-attivazione:

```bash
.venv/Scripts/python.exe scripts/legal_data/audit_france_activation_readiness.py
```

Verdict atteso PRIMA delle promozioni admin: `OFFICIAL-ONLY` (lo script ancora non vede le firme perché non sono ancora state materializzate in DB).

---

## 1 — Promozione delle 3 LegalSource (5 min × 3)

Dal Django admin (`/admin/legal_sources/legalsource/`), per ognuna delle 3 fonti:

### 1.1 Mornet 2024

- [ ] Apri `LegalSource` con `slug = 'fr-referentiel-mornet-2024'`.
- [ ] Set `status = APPROVED`.
- [ ] Set `legal_reviewer` = utente Studio firmatario (FK utente — l'utente deve già esistere; se non esiste, crearlo prima).
- [ ] Set `publication_date` = data firma dichiarata in sezione A del modulo.
- [ ] Salva.

### 1.2 Gazette du Palais 2022

- [ ] Apri `LegalSource` con `slug = 'fr-bareme-capitalisation-gazette-palais-2022'`.
- [ ] Stessi 3 campi come 1.1, con data firma dichiarata in sezione B.

### 1.3 Nomenclature Dintilhac 2005

- [ ] Apri `LegalSource` con `slug = 'fr-nomenclature-dintilhac-2005'`.
- [ ] Stessi 3 campi come 1.1, con data firma dichiarata in sezione C.

### Verifica 1

```bash
.venv/Scripts/python.exe scripts/legal_data/audit_france_activation_readiness.py
```

Atteso ora: le 3 fonti sono APPROVED ma il verdict è ancora `OFFICIAL-ONLY` (mancano dataset + formula + LegalReview rows).

---

## 2 — Creazione delle 3 LegalReview audit rows (5 min × 3)

Dal Django admin (`/admin/legal_sources/legalreview/`), per ognuna delle 3 fonti appena promosse, crea una nuova `LegalReview`:

| Campo | Valore |
|---|---|
| `source` | la `LegalSource` corrispondente |
| `reviewer` | utente Studio firmatario (stesso del campo `legal_reviewer` su LegalSource) |
| `decision` | `APPROVE` |
| `new_status` | `APPROVED` |
| `notes` | "Sessione di review legale Studio del [data riunione]. Riferimento modulo decisione `FRANCE_SIGNOFF_DECISION_FORM.md` sezione [A/B/C]. [Eventuali correzioni applicate]." |

- [ ] 2.1 — LegalReview per Mornet 2024.
- [ ] 2.2 — LegalReview per Gazette du Palais 2022.
- [ ] 2.3 — LegalReview per Dintilhac 2005.

### Verifica 2

```bash
.venv/Scripts/python.exe manage.py check
```

Atteso: nessun errore `jurisdictions.E001`. (Il system check fallisce in produzione se una LegalSource APPROVED non ha una LegalReview APPROVE corrispondente.)

---

## 3 — Promozione dei 2 dataset (DRAFT → APPROVED)

> **Importante**: il suffisso `-DRAFT` è *load-bearing*. Lo script `import_france_candidate_datasets.py` rifiuta di scrivere in un dataset non-DRAFT. Quindi: prima rinominare, poi promuovere.

### 3.1 Mornet 2024

- [ ] Apri `CompensationDataset` con `name = 'FR-MORNET-2024-DRAFT'`.
- [ ] Rinomina `name = 'FR-MORNET-2024'` (rimuove il suffisso).
- [ ] Set `status = APPROVED`.
- [ ] Salva.

### 3.2 Gazette du Palais 2022

- [ ] Apri `CompensationDataset` con `name = 'FR-GAZETTE-PALAIS-2022-DRAFT'`.
- [ ] Rinomina `name = 'FR-GAZETTE-PALAIS-2022'`.
- [ ] Set `status = APPROVED`.
- [ ] Salva.

### Verifica 3

```bash
.venv/Scripts/python.exe scripts/legal_data/verify_france_candidate_import.py
```

Atteso: lo script verifica i conteggi righe. Le 191 righe Mornet + 4 188 Gazette devono essere intatte. Nessuna riga persa rispetto al pre-promozione.

---

## 4 — Creazione della CalculationFormula (5 min)

Dal Django admin (`/admin/calculators/calculationformula/`), crea una nuova formula:

| Campo | Valore |
|---|---|
| `code` | `france-road-accident-mornet-2024-v1` |
| `jurisdiction` | `FR-NATIONAL` |
| `case_type` | `road_accident_bodily_injury` |
| `status` | `APPROVED` |
| `parameters` | JSON sotto |

`parameters` (JSON da incollare nel campo):

```json
{
  "engine": "france_road_accident_v1",
  "amount_rule": "france_dfp_point_value_direct",
  "row_type": "fr_dfp_per_age_disability_amount_per_point",
  "row_match": ["victim_age", "permanent_disability_percentage"],
  "requires": ["victim_age", "permanent_disability_percentage"],
  "fault_reduction": true
}
```

- [ ] Salva.

### Verifica 4

```bash
.venv/Scripts/python.exe scripts/legal_data/audit_france_activation_readiness.py
```

Atteso ora: verdict `GO` (la catena Francia è completa).

---

## 5 — Smoke test fixture (~1-2 ore di codice)

- [ ] Crea `apps/calculators/test_france_engine_active.py` con i 3 test smoke. Pattern: copiare da `apps/calculators/test_italy_engine_implementation.py` e adattare a FR. Per ognuno dei 3 casi (35×5×0, 45×30×0, 60×15×25), inserire come asserzioni i valori firmati dallo Studio in sezione E del modulo decisione.

  - [ ] `test_france_smoke_35_5_0_pedone`: assert `result.status == CALCULATED`, `estimated_min == Decimal('<E.1 min>')`, `estimated_mid == Decimal('<E.1 mid>')`, `estimated_max == Decimal('<E.1 max>')`.
  - [ ] `test_france_smoke_45_30_0_passeggero`: idem con i valori E.2.
  - [ ] `test_france_smoke_60_15_25_ciclista`: idem con i valori E.3.

- [ ] Se lo Studio in sezione E ha indicato tolleranze, sostituire `==` con asserzioni di tolleranza (es. `abs(result.estimated_min - Decimal('X')) <= Decimal('Y')`).

### Verifica 5

```bash
.venv/Scripts/python.exe -m pytest apps/calculators/test_france_engine_active.py -v
```

Atteso: 3 test passati. Se anche uno solo fallisce: **stop**. Indica una discrepanza tra il numero firmato dallo Studio e quello che il calcolatore produce con la formula. Indagare prima di proseguire. Se la discrepanza è confermata, ritornare allo Studio (NON modificare i numeri firmati né i dati Mornet).

---

## 6 — Disclaimer Francia (opzionale, dipende da sezione D)

- Se sezione D del modulo dichiara "approvato senza modifiche": **nessuna azione**. Il disclaimer generico viene mostrato.
- Se sezione D dichiara "approvato con correzioni" o "sostituito da testo Studio": creare `templates/partials/_disclaimer_france.html` con il testo finale firmato. Aggiungere logica nella view del wizard `wizard_france_road_accident_result` per renderlo invece del generico.

- [ ] Disclaimer specifico Francia configurato (se applicabile).
- [ ] Traduzioni richieste (segnate in sezione D) inserite in `locale/fr/`, `locale/it/`, `locale/en/`, `locale/ar/` come applicabile.

---

## 7 — Mappatura Dintilhac sul report PDF (~30 min)

Aggiungere in `apps/reports/services.py` (esistente, già fa qualcosa di simile per Italia) la traduzione dell'output del calcolatore in voci Dintilhac:

| Output engine | Voce Dintilhac nel PDF |
|---|---|
| `breakdown[0]` (DFP) | "Déficit fonctionnel permanent" |
| `assumptions[*]` | sezione "Hypothèses retenues" |
| `missing_documents[*]` | sezione "Pièces non incluses dans le calcul automatique" (con CTA "valutazione Studio caso-per-caso" per ciascuna voce non automatizzata) |
| `warnings[*]` | sezione "Avertissements" |

- [ ] Mappatura Dintilhac implementata.
- [ ] Test: generare un PDF Francia di esempio e verificare visivamente la struttura dei *postes*.

---

## 8 — Smoke browser test

Avviare il server di dev e simulare a mano i 3 casi smoke:

```bash
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

Aprire `http://127.0.0.1:8000/wizard/fr/road-accident/`:

- [ ] **Caso 35×5×0**: compilare il form, submit, verificare che vengano mostrati i 3 numeri attesi (€min/€mid/€max secondo sezione E.1).
- [ ] **Caso 45×30×0**: idem con E.2.
- [ ] **Caso 60×15×25**: idem con E.3, verificare che la riduzione del 25 % sia applicata.

Catturare screenshot di ciascun risultato:

```bash
.venv/Scripts/python.exe scripts/capture_product_1_france_signoff_pack.py
# (rinominare manualmente l'output in /after/p0-mvp-1-activate-france/)
```

- [ ] Screenshot post-attivazione catturati e archiviati.

---

## 9 — Test e verifiche finali

```bash
.venv/Scripts/python.exe manage.py check
# Atteso: clean (solo W001 STUDIO_* dev).

.venv/Scripts/python.exe -m pytest -q
# Atteso: 1984+3 = 1987+ passed (i 3 nuovi smoke FR si aggiungono).

.venv/Scripts/python.exe scripts/legal_data/audit_france_activation_readiness.py
# Atteso: verdict GO.

.venv/Scripts/python.exe scripts/legal_data/audit_non_it_readiness.py
# Atteso: France passa da APPROVED-PARTIAL a APPROVED-FULL (gli altri 3 paesi restano APPROVED-PARTIAL).

.venv/Scripts/python.exe scripts/audit_legal_content_hygiene.py --strict
# Atteso: no findings.

bash scripts/run_quality_gate.sh
# Atteso: ALL GATES CLEARED.

.venv/Scripts/python.exe scripts/live_simulation_matrix.py
# Atteso: Italia 35/10/0 = 26 268 / 27 353 / 28 439 EUR (non deve regredire).
```

- [ ] Tutti i check sopra verdi.

Se uno solo fallisce: **rollback** (§11) prima di proseguire al PR.

---

## 10 — PR & deploy

- [ ] Commit:
  ```
  p0-mvp-1-activate-france: activate france road-accident calculator

  Studio sign-off received on [data sessione], modulo
  FRANCE_SIGNOFF_DECISION_FORM.md sezione F: GO.

  - Promotes 3 LegalSource to APPROVED (Mornet 2024, Gazette
    du Palais 2022, Dintilhac 2005) — via admin.
  - Creates 3 LegalReview audit rows (decision=APPROVE, with
    reviewer FK and signature reference notes).
  - Promotes 2 datasets (FR-MORNET-2024, FR-GAZETTE-PALAIS-2022)
    to APPROVED (renamed from -DRAFT).
  - Creates CalculationFormula(france-road-accident-mornet-2024-v1)
    with engine france_road_accident_v1 + amount_rule
    france_dfp_point_value_direct.
  - Adds test_france_engine_active.py with 3 smoke tests
    (35x5x0, 45x30x0, 60x15x25) pinning the Studio-signed
    €min/€mid/€max for each case.
  - [If disclaimer custom] Adds templates/partials/_disclaimer_france.html.
  - Adds Dintilhac mapping in apps/reports/services.py.

  Verifications: pytest 1987+ passed, audit_france_activation_readiness
  verdict GO, quality gate cleared, Italia 35/10/0 unchanged.
  ```
- [ ] Apri PR su `audit/indennizzati-platform`.
- [ ] Review interna (un altro paio d'occhi sui 3 numeri smoke).
- [ ] Merge `--no-ff`.
- [ ] Tag `p0-mvp-1-activate-france-<data>`.
- [ ] Deploy staging.
- [ ] **24 h di verifica Studio sullo staging** prima di deploy prod.
- [ ] Deploy prod.

---

## 11 — Rollback (se qualcosa va storto post-attivazione)

Reversibile in 5 minuti da admin:

```sql
-- pseudo-SQL — eseguire da admin Django, non da shell.

UPDATE calculations_calculationformula
   SET status = 'DRAFT'
 WHERE code = 'france-road-accident-mornet-2024-v1';

UPDATE compensation_compensationdataset
   SET name = name || '-DRAFT', status = 'DRAFT'
 WHERE name IN ('FR-MORNET-2024', 'FR-GAZETTE-PALAIS-2022');

UPDATE legal_sources_legalsource
   SET status = 'needs_review'
 WHERE slug IN (
   'fr-referentiel-mornet-2024',
   'fr-bareme-capitalisation-gazette-palais-2022',
   'fr-nomenclature-dintilhac-2005'
 );
```

> **NON eliminare** le righe `LegalReview` firmate. Sono audit storico. Lo stato "firmato → poi disattivato → poi rifirmato" deve restare tracciabile.

Verifica post-rollback:

```bash
.venv/Scripts/python.exe scripts/legal_data/verify_france_candidate_import.py
# Atteso: DRAFT counter intatto.

.venv/Scripts/python.exe -m pytest -q
# Atteso: tornato a 1984 passed (3 smoke FR ora saltati perché formula non APPROVED).

.venv/Scripts/python.exe scripts/legal_data/audit_france_activation_readiness.py
# Atteso: verdict torna a OFFICIAL-ONLY.
```

---

## 12 — Quello che lo Studio non deve aspettarsi

Per chiarezza, anche dopo l'attivazione la piattaforma Francia v1:

- **non calcola spese mediche / perdita reddito / capitalizzazione di rendite / souffrances endurées / préjudice esthétique / préjudice d'affection / tierce personne**. Sono elencati come "missing documents" / "richiede valutazione Studio" — visibili nel report ma non quantificati automaticamente.
- **non interpola tra righe Mornet**. Se l'input è fuori griglia, il sistema risponde "valutazione preliminare", non un valore approssimato.
- **non aggiorna automaticamente a Mornet 2025** quando uscirà. L'aggiornamento è un nuovo iter con nuova sessione di review legale.
- **non gestisce sinistri pre-Loi Badinter 1985** o sinistri non-stradali. Il wizard FR è per "accident de la circulation, dommages corporels" — altre case-type sono iter futuri.

Tutto questo è già documentato nel pacchetto operativo `docs/product/FRANCE_ACTIVATION_SIGNOFF_PACK.md` §5 (Limiti dichiarati del calcolatore Francia v1). Riportarlo qui serve solo per evitare che lo Studio scopra a deploy fatto che mancano voci che si aspettava.

---

## Riferimenti

- Modulo decisione firmato: `docs/studio/FRANCE_SIGNOFF_DECISION_FORM.md`
- Ordine del giorno della riunione: `docs/studio/FRANCE_REVIEW_MEETING_AGENDA.md`
- Riassunto 1 pagina: `docs/studio/FRANCE_REVIEW_ONE_PAGE_SUMMARY.md`
- Pacchetto operativo completo: `docs/product/FRANCE_ACTIVATION_SIGNOFF_PACK.md`
- Piano dev operativo dettagliato: `docs/product/FRANCE_ACTIVATION_DEV_PLAN.md`
- Matrice test e2e: `docs/product/FRANCE_E2E_TEST_MATRIX.md`
- Audit tecnico read-only: `docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md`
