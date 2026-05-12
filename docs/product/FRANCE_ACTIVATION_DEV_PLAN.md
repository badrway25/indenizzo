# France activation — dev plan

**Per**: chi attiverà Francia dopo le firme.
**Companion of**: `FRANCE_ACTIVATION_SIGNOFF_PACK.md` (Studio-facing).
**Iter target**: `P0-MVP-1-ACTIVATE-france` (futuro, non in questo
branch).
**Pre-condition**: le 4 firme elencate nel signoff pack §9 sono
arrivate dallo Studio.

Questo documento descrive **esattamente** cosa fa il dev quando le
firme arrivano. Niente di tutto questo deve essere eseguito ora —
questo branch è solo documentazione e guardrail. L'attivazione
reale è un PR distinto, descritto qui passo per passo.

---

## 1. Pre-flight — verifica che le firme siano arrivate

```bash
# 1.1 Read-only audit della catena Francia.
.venv/Scripts/python.exe scripts/legal_data/audit_france_activation_readiness.py

# Verdict atteso PRIMA della firma:   OFFICIAL-ONLY  (oggi)
# Verdict atteso DOPO  la firma:      OFFICIAL-ONLY  (lo script NON
#                                     vede le firme finché un admin
#                                     non le materializza in DB —
#                                     vedere §2).
```

Lo Studio deve aver firmato:

1. `LegalSource(slug='fr-referentiel-mornet-2024')` → APPROVED;
2. `LegalSource(slug='fr-bareme-capitalisation-gazette-palais-2022')` → APPROVED;
3. `LegalSource(slug='fr-nomenclature-dintilhac-2005')` → APPROVED;
4. disclaimer Francia: testo definitivo.

In più, lo Studio deve aver consegnato 3 numeri smoke-test attesi
per i casi 35×5×0, 45×30×0, 60×15×25 (vedi signoff pack §7).

Se uno dei 4 non c'è ancora: **non procedere**. Aspettare la firma
mancante. La piattaforma resta `OFFICIAL-ONLY` (review-gated).

---

## 2. Operazioni in admin (5 min × 4 fonti)

### 2.1 Promozione LegalSource × 3

Per ognuna di Mornet, Gazette, Dintilhac, dal Django admin:

1. Aprire `LegalSource` corrispondente.
2. Set `status = APPROVED`.
3. Set `legal_reviewer = <user Studio firmatario>`.
4. Set `publication_date` = data della firma.
5. Salvare.

### 2.2 LegalReview audit row × 3

Sempre dall'admin, per ciascuna delle 3 promozioni, creare una
nuova `LegalReview`:

| Campo | Valore |
|---|---|
| `source` | la `LegalSource` appena promossa |
| `reviewer` | user Studio firmatario |
| `decision` | `APPROVE` |
| `new_status` | `APPROVED` |
| `notes` | "Firma sessione Studio del <data>; riferimento checklist `france_legal_review_checklist_template.csv`" |

> **Importante**: il system check `jurisdictions.E001` (attivo in
> prod, silenzioso in dev) fallisce se una `LegalSource` è
> `APPROVED` ma manca la `LegalReview(decision=APPROVE)`
> corrispondente. Quindi 2.1 senza 2.2 viene bloccato al primo
> deploy. Fare entrambi.

### 2.3 Dataset DRAFT → APPROVED × 2

Per Mornet e per Gazette:

1. Aprire `CompensationDataset(name='FR-MORNET-2024-DRAFT')`.
2. Rinominare `name = 'FR-MORNET-2024'` (rimuove `-DRAFT`).
3. Set `status = APPROVED`.
4. Salvare.

Stesso per `FR-GAZETTE-PALAIS-2022-DRAFT` → `FR-GAZETTE-PALAIS-2022`.

> **Importante**: il suffisso `-DRAFT` è *load-bearing*.
> `scripts/legal_data/import_france_candidate_datasets.py` rifiuta
> di scrivere in un dataset non-DRAFT. Quindi: prima rinominare,
> poi promuovere.

### 2.4 CalculationFormula(France) — creare la formula

Dall'admin, **nuova** `CalculationFormula`:

| Campo | Valore |
|---|---|
| `code` | `france-road-accident-mornet-2024-v1` |
| `jurisdiction` | `FR-NATIONAL` |
| `case_type` | `road_accident_bodily_injury` |
| `status` | `APPROVED` |
| `parameters` (JSON) | (vedi sotto) |

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

`requires` definisce gli input minimi obbligatori per emettere un
numero. Se mancano, il calcolatore restituisce
`INSUFFICIENT_INPUT` invece di calcolare con valori inventati.

---

## 3. Smoke test fixture (codice)

Creare `apps/calculators/test_france_engine_active.py` (nuovo
file). Mirror del pattern Italia
(`test_italy_engine_implementation.py`).

```python
# Pseudocode — vedi il file Italia esistente per la forma precisa.
import pytest
from apps.calculators.engines.france import (
    FranceRoadAccidentBodilyInjuryCalculator,
)
from apps.calculators.enums import CalculationStatus

@pytest.mark.django_db
def test_france_smoke_35_5_0(approved_fr_chain):
    """Caso 1 — Mornet 2024, 35 anni, 5 % invalidità, 0 % colpa.
    Numero atteso firmato Studio: €min=AAAA, €mid=BBBB, €max=CCCC."""
    result = FranceRoadAccidentBodilyInjuryCalculator().compute({
        "victim_age": 35,
        "permanent_disability_percentage": 5,
        "fault_percentage": 0,
    })
    assert result.status == CalculationStatus.CALCULATED.value
    assert result.estimated_min == Decimal("AAAA")
    assert result.estimated_mid == Decimal("BBBB")
    assert result.estimated_max == Decimal("CCCC")

# idem 45_30_0, 60_15_25 — tre asserzioni "locked" con i numeri
# concordati con lo Studio.
```

I tre numeri sono *firmati*. Modificarli in un iter futuro
richiede una nuova firma Studio (locked smoke test contract).

La fixture `approved_fr_chain` deve seedare nel test DB:

- `LegalSource(Mornet 2024, status=APPROVED, reviewer=test_user)`
- `LegalReview(source=Mornet 2024, decision=APPROVE)`
- `CompensationDataset(FR-MORNET-2024, status=APPROVED)`
- N `CompensationTableRow(dataset=FR-MORNET-2024, ...)` con le
  191 righe Mornet
- `CalculationFormula(france-...-v1, status=APPROVED)` come §2.4

(L'esistente `test_france_engine_inactive.py` ha già una fixture
analoga per il path "approved-but-still-unavailable"; copiare e
estendere.)

---

## 4. Disclaimer template — solo se non si usa il generico

Se lo Studio decide di firmare un disclaimer Francia-specifico,
aggiungere il testo come template:

`templates/partials/_disclaimer_france.html` (nuovo) — caricato
dalla view `wizard_france_road_accident_result` quando il
calcolatore restituisce `CALCULATED`.

Se invece lo Studio controfirma il generico, **nessuna modifica
template**. Il disclaimer generico è già reso da
`partials/disclaimer_banner.html`.

---

## 5. Mappatura Dintilhac sul report PDF

Aggiungere in `apps/reports/services.py` (esistente) la
traduzione dell'output del calcolatore in voci Dintilhac:

| Output engine | Poste Dintilhac (PDF) |
|---|---|
| `breakdown[0]` (DFP) | "Déficit fonctionnel permanent (DFP)" |
| `assumptions[*]` | sezione "Hypothèses retenues" |
| `missing_documents[*]` | sezione "Pièces non incluses dans le calcul automatique" |
| `warnings[*]` | sezione "Avertissements" |

(Il sistema attuale già fa qualcosa di simile per Italia — il
codice è in `apps/reports/services.py`; replicare il pattern per
FR.)

---

## 6. Verifica post-attivazione

```bash
# 6.1 Audit catena Francia — verdict deve passare a GO.
.venv/Scripts/python.exe scripts/legal_data/audit_france_activation_readiness.py
# Verdict atteso: GO (non più OFFICIAL-ONLY).

# 6.2 Full test suite.
.venv/Scripts/python.exe -m pytest -q
# Deve essere: 1971+ passed, 1 skipped. Numero nuovo: +3 test smoke FR.

# 6.3 Italia non deve regredire.
.venv/Scripts/python.exe scripts/live_simulation_matrix.py
# Atteso: Italy 35/10/0 = 26 268 / 27 353 / 28 439 EUR.

# 6.4 Quality gate.
bash scripts/run_quality_gate.sh
# Atteso: ALL GATES CLEARED.

# 6.5 Mobile Lighthouse.
bash scripts/run_lighthouse_mobile_local.sh
# Atteso: /ar/ 0.85, /countries/ 0.91, /wizard/ ≥ 0.97, ecc.
```

Se uno dei 5 fallisce: **rollback** (§7).

---

## 7. Rollback (se 6 fallisce)

Tutto reversibile da admin in 5 min:

```sql
-- pseudo-SQL — fare tramite admin, non via shell.
UPDATE calculations_calculationformula
   SET status = 'DRAFT'
 WHERE code LIKE 'france-road-accident-%';

UPDATE compensation_compensationdataset
   SET name = name || '-DRAFT', status = 'DRAFT'
 WHERE name LIKE 'FR-MORNET%' OR name LIKE 'FR-GAZETTE%';

UPDATE legal_sources_legalsource
   SET status = 'needs_review'
 WHERE slug IN (
   'fr-referentiel-mornet-2024',
   'fr-bareme-capitalisation-gazette-palais-2022',
   'fr-nomenclature-dintilhac-2005'
 );
```

**Non eliminare** le righe `LegalReview` firmate — sono audit
storico. Lo stato "firmato → poi disattivato → poi rifirmato"
deve restare tracciabile.

Dopo il rollback:

```bash
.venv/Scripts/python.exe scripts/legal_data/verify_france_candidate_import.py
# DRAFT counter deve essere intatto.
.venv/Scripts/python.exe -m pytest -q
# Deve tornare verde, Francia di nuovo `unavailable_requires_legal_validation`.
```

---

## 8. PR shape

Il PR di attivazione tocca:

| File | Modifica |
|---|---|
| `apps/calculators/test_france_engine_active.py` | nuovo file, 3 test smoke con numeri firmati |
| `apps/reports/services.py` | aggiunta mappatura Dintilhac (~30 righe) |
| `templates/partials/_disclaimer_france.html` | opzionale, solo se disclaimer Francia-specifico |
| `docs/architecture/FRANCE_MODULE_STATUS.md` | data attivazione + smoke contract |
| (db migration) | nessuna nuova migration: l'admin lavora su modelli esistenti |

Il PR non tocca:

- l'engine `france.py` (è già completo, 361 righe, 12 gates);
- l'audit script `audit_france_activation_readiness.py` (read-only,
  lo passiamo solo per verifica);
- il `_FrancePlaceholderCalculator`: viene già ereditato da
  `FranceRoadAccidentBodilyInjuryCalculator` ma sovrascritto in
  `_compute_with_sources`. Una volta che le fonti sono APPROVED,
  la sovrascrittura prende il path eseguibile naturalmente, senza
  cambiare codice.

Il PR è **~50 righe di codice + 3 numeri firmati**. La complessità
è stata pre-pagata negli iter precedenti
(F-france-road-accident-bootstrap, F-france-engine-inactive-fixture-only).

---

## 9. Esempio di sessione di firma → PR (timeline)

| Tempo | Chi | Cosa |
|---|---|---|
| T0 | Studio | sessione di review legale (3 fonti) |
| T0 + 1h | Studio | firme materializzate (4) + 3 numeri smoke consegnati al dev |
| T0 + 1h | dev | apre admin, promozioni §2.1-2.4 (5 min × 4 = 20 min) |
| T0 + 1.5h | dev | committa `test_france_engine_active.py` (1 ora di scrittura + fixture) |
| T0 + 2.5h | dev | esegue §6 (test+gate+audit) → tutto verde |
| T0 + 3h | dev | apre PR `P0-MVP-1-ACTIVATE-france` |
| T0 + 4h | review interna | merge sull'audit branch |
| T0 + 24h | deploy staging | Studio verifica sul sito |
| T0 + 48h | deploy prod | Francia *live* |

Effort totale dev: ~1 giorno-uomo. Effort totale Studio: una sola
sessione di review legale (la parte tecnica è già stata fatta).

---

## 10. Cosa non fare mai

Liste che cristallizzano i divieti — applicabili sia adesso (in
questo branch documentale) sia al PR di attivazione futuro:

1. **No bypass del LegalReview**. Promuovere una `LegalSource` a
   `APPROVED` senza la `LegalReview(decision=APPROVE)`
   corrispondente fa fallire `jurisdictions.E001` in prod.
2. **No formula manuale da shell senza audit**. La
   `CalculationFormula` va creata da admin (UI loggata) o da una
   migration espressamente versionata, mai da `manage.py shell`.
3. **No copia di numeri Mornet/Gazette nei test fixture come
   stringhe inventate**. I 3 numeri smoke sono *firmati*. Se il
   dev non ha i numeri dallo Studio, **non apre il PR**.
4. **No promozione cumulativa "tutto in una"**. Il system check
   richiede consistenza tra `LegalSource`, `LegalReview` e
   `CompensationDataset`. Promozione disordinata = system check
   bloccato.
5. **No rimozione delle righe DRAFT originali**. Sono l'audit
   trail dell'estrattore. La rinominazione `-DRAFT` → senza
   suffisso è una modifica al record, non un nuovo record.
6. **No interpolazione tra righe Mornet**. La regola di calcolo è
   `single-row range` — se nessuna riga matcha esattamente, il
   risultato è `compensation_row_match_missing`, **non** un valore
   interpolato. Lo Studio deve aver firmato che la copertura è
   accettabile.
7. **No deploy prod il giorno della firma**. Sempre staging
   prima, sempre minimo 24 h di verifica Studio sullo staging.
