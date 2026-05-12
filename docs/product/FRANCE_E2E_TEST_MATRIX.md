# France — end-to-end test matrix

**Per**: chi scriverà i test e chi li firmerà.
**Companion of**: `FRANCE_ACTIVATION_SIGNOFF_PACK.md`,
`FRANCE_ACTIVATION_DEV_PLAN.md`.

Matrice di casi-test che la piattaforma userà come *contract* per
il modulo Francia. I tre `smoke test` (§9-11 della checklist
signoff pack) sono *locked*: i numeri attesi vengono firmati dallo
Studio in sessione di review e qualsiasi modifica futura richiede
una nuova firma.

Sono incluse anche scenari **review-gated** — input per i quali
la piattaforma **non** deve pubblicare un numero anche dopo
l'attivazione. Sono altrettanto importanti dei casi calcolabili:
proteggono il consumatore da numeri non veritieri quando i dati
sono incompleti, fuori scala, o richiedono manualmente Studio.

---

## 1. Convenzioni

| Campo | Significato |
|---|---|
| `victim_age` | Età alla data dell'incidente, intero ≥ 0. |
| `permanent_disability_percentage` | % di invalidità permanente, intero 0–100. Mornet 2024 copre 1–100 % a passi di 1. |
| `total_temporary_disability_days` | Giorni di ITT (incapacità temporanea totale). Non entra nel calcolo automatico v1. |
| `partial_temporary_disability_days` | Giorni di ITP. Non entra nel calcolo automatico v1. |
| `medical_expenses` | Spese mediche documentate (EUR). Non entrano in v1. |
| `lost_income` | Perdita reddito (EUR). Non entra in v1. |
| `fault_percentage` | Concorso di colpa 0–100 %. Applicato uniformemente al range. |
| `accident_country` | Sempre `FR` per il wizard Francia. |

`v1` = prima versione del calcolatore Francia, copertura
`Déficit Fonctionnel Permanent` + applicazione lineare del
concorso di colpa. Tutto il resto è esplicitamente fuori scope v1.

Output atteso categorie:

- **CALCULATED**: tre numeri €min/€mid/€max + breakdown DFP.
- **INSUFFICIENT_INPUT**: il form ha ricevuto valori che non
  permettono il calcolo (input obbligatori mancanti, fault fuori
  range). Status pubblicato, nessun numero.
- **UNAVAILABLE_REQUIRES_LEGAL_VALIDATION**: la combinazione di
  input cade in un caso non coperto (es. invalidità a 0.5 % che
  non matcha nessuna riga Mornet, oppure incidente fuori
  giurisdizione FR). Nessun numero, raccomandazione Studio.

---

## 2. Smoke test 1 — Incidente lieve

**Storia**: pedone urbano in attraversamento sulle strisce,
investito a bassa velocità. Frattura piede destro, recupero
completo dopo riabilitazione, residuo di invalidità minore.

| Campo | Valore |
|---|---|
| `victim_age` | 35 |
| `permanent_disability_percentage` | 5 |
| `total_temporary_disability_days` | 30 |
| `partial_temporary_disability_days` | 0 |
| `medical_expenses` | 2 500 |
| `lost_income` | 0 |
| `fault_percentage` | 0 |
| `accident_country` | FR |

**Fonte usata**: Mornet 2024 — `fr_dfp_per_age_disability_amount_per_point`,
riga `victim_age=35` × `permanent_disability_percentage=5`.

**Output atteso (status)**: `CALCULATED`.

**Output atteso (numeri)**: firmati Studio in sessione.
Placeholder: €min = AAAA, €mid = BBBB, €max = CCCC.
Range tipico atteso dal pattern Mornet: alcuni migliaia di € a
basso DFP.

**Disclaimer**: §6 signoff pack (testo proposto), versione
italiana / francese / inglese / araba.

**Voci NON calcolate (visibili nel risultato)**:

- `total_temporary_disability_days`: "non incluso nel calcolo
  automatico; richiede valutazione manuale";
- `medical_expenses`: idem.

**Test automatico**:
`apps/calculators/test_france_engine_active.py::test_france_smoke_35_5_0_pedone`.

---

## 3. Smoke test 2 — Incidente grave (passeggero)

**Storia**: passeggero anteriore in un'auto che subisce uno
scontro frontale in autostrada. Lesione spinale, invalidità
permanente media.

| Campo | Valore |
|---|---|
| `victim_age` | 45 |
| `permanent_disability_percentage` | 30 |
| `total_temporary_disability_days` | 120 |
| `partial_temporary_disability_days` | 60 |
| `medical_expenses` | 18 000 |
| `lost_income` | 22 000 |
| `fault_percentage` | 0 |
| `accident_country` | FR |

**Fonte usata**: Mornet 2024, riga `victim_age=45` ×
`permanent_disability_percentage=30`.

**Output atteso (status)**: `CALCULATED`.

**Output atteso (numeri)**: firmati Studio.

**Disclaimer**: §6 signoff pack.

**Voci NON calcolate visibili**:

- `total_temporary_disability_days`, `partial_temporary_disability_days`,
- `medical_expenses`, `lost_income`.

Tutti elencati come "missing documents / requires legal review".

**Test automatico**:
`apps/calculators/test_france_engine_active.py::test_france_smoke_45_30_0_passeggero`.

---

## 4. Smoke test 3 — Concorso di colpa significativo

**Storia**: ciclista in carreggiata principale di notte senza
luci, scontro con auto in svolta. Lesione anca con esiti
permanenti. Concorso di colpa del ciclista al 25 %.

| Campo | Valore |
|---|---|
| `victim_age` | 60 |
| `permanent_disability_percentage` | 15 |
| `total_temporary_disability_days` | 60 |
| `partial_temporary_disability_days` | 30 |
| `medical_expenses` | 8 000 |
| `lost_income` | 4 000 |
| `fault_percentage` | 25 |
| `accident_country` | FR |

**Fonte usata**: Mornet 2024, riga `victim_age=60` ×
`permanent_disability_percentage=15`. Output ridotto del 25 %.

**Output atteso (status)**: `CALCULATED`.

**Output atteso (numeri)**: firmati Studio.
La riduzione per fault è lineare e uniforme su min/mid/max — la
firma deve confermare che la matematica (`amount × (1 − fault/100)`)
è quella attesa.

**Disclaimer**: §6 signoff pack + nota addizionale sulla
riduzione applicata.

**Assumption stampata sotto il calcolo**:
"Fault reduction applied uniformly to min/mid/max."

**Test automatico**:
`apps/calculators/test_france_engine_active.py::test_france_smoke_60_15_25_ciclista`.

---

## 5. Caso review-gated 1 — Dati incompleti

**Storia**: utente apre il wizard, ha compilato età ma non ha la
percentuale di invalidità a portata di mano. Submit.

| Campo | Valore |
|---|---|
| `victim_age` | 40 |
| `permanent_disability_percentage` | *(vuoto)* |
| `total_temporary_disability_days` | 14 |
| `medical_expenses` | 1 200 |
| `fault_percentage` | 0 |
| `accident_country` | FR |

**Fonte usata**: nessuna (gating sull'input).

**Output atteso (status)**: `INSUFFICIENT_INPUT`.

**Output atteso (messaggio)**:
"Input minimi mancanti: percentuale di invalidità permanente."

**Nessun numero** viene mostrato. CTA verso il contatto Studio.

**Test automatico**:
`apps/calculators/test_france_engine_active.py::test_france_insufficient_input_missing_disability`.

---

## 6. Caso review-gated 2 — Riga Mornet non disponibile

**Storia**: incidente con invalidità all'1 % — fuori scala
inferiore Mornet (la tabella Mornet 2024 inizia a livelli più
alti per molte fasce di età).

| Campo | Valore |
|---|---|
| `victim_age` | 50 |
| `permanent_disability_percentage` | 1 |
| `fault_percentage` | 0 |
| `accident_country` | FR |

**Fonte usata**: tentativo Mornet 2024 → nessuna riga match.

**Output atteso (status)**:
`UNAVAILABLE_REQUIRES_LEGAL_VALIDATION` con `missing_documents =
['compensation_row_match_missing']`.

**Output atteso (messaggio)**:
"La combinazione di età e invalidità non è coperta dalla tabella
Mornet 2024 utilizzata dalla piattaforma. La valutazione richiede
analisi manuale Studio."

**Nessun numero**.

**Test automatico**:
`apps/calculators/test_france_engine_active.py::test_france_unavailable_row_not_in_mornet_grid`.

---

## 7. Caso review-gated 3 — Concorso di colpa fuori range

**Storia**: utente immette `fault_percentage = 150` (errore di
battitura: voleva scrivere 15).

| Campo | Valore |
|---|---|
| `victim_age` | 35 |
| `permanent_disability_percentage` | 10 |
| `fault_percentage` | 150 |
| `accident_country` | FR |

**Fonte usata**: nessuna (validazione input).

**Output atteso (status)**: `INSUFFICIENT_INPUT`.

**Output atteso (messaggio)**:
"La percentuale di concorso di colpa deve essere compresa tra 0 e
100."

**Nessun numero**.

**Test automatico**:
`apps/calculators/test_france_engine_active.py::test_france_insufficient_input_fault_out_of_range`.

---

## 8. Caso pre-attivazione (oggi)

**Storia**: lo stato di oggi, prima delle 4 firme. Pubblicato
ora. Resta valido finché l'attivazione non è eseguita.

| Campo | Valore |
|---|---|
| qualsiasi input | qualsiasi valore |

**Output atteso (status)**:
`UNAVAILABLE_REQUIRES_LEGAL_VALIDATION` con `missing_documents =
['calculator_engine_pending_for_jurisdiction']`.

**Output atteso (UI)**: il pannello "Preliminary legal
assessment", testo Studio-centric, CTA verso contatto.

**Test automatico** (già esistente):
`apps/cases/test_france_review_gated_e2e_p0_mvp_1.py::test_france_review_gated_e2e`.

Questo test rimarrà nel codice anche dopo l'attivazione; sarà
sostituito da un test "post-attivazione" che invece controlla
che il numero corretto sia pubblicato. Il rimpiazzo è parte del
PR di attivazione (`P0-MVP-1-ACTIVATE-france`).

---

## 9. Riepilogo

| # | Nome | Status atteso | Calcola? | Test file |
|---|---|---|---|---|
| 1 | Incidente lieve 35×5×0 | CALCULATED | sì | `test_france_engine_active.py::test_france_smoke_35_5_0_pedone` |
| 2 | Incidente grave 45×30×0 | CALCULATED | sì | `test_france_engine_active.py::test_france_smoke_45_30_0_passeggero` |
| 3 | Concorso 60×15×25 | CALCULATED | sì (con riduzione) | `test_france_engine_active.py::test_france_smoke_60_15_25_ciclista` |
| 4 | Dati incompleti | INSUFFICIENT_INPUT | no | `test_france_engine_active.py::test_france_insufficient_input_missing_disability` |
| 5 | Riga Mornet non disponibile | UNAVAILABLE | no | `test_france_engine_active.py::test_france_unavailable_row_not_in_mornet_grid` |
| 6 | Fault fuori range | INSUFFICIENT_INPUT | no | `test_france_engine_active.py::test_france_insufficient_input_fault_out_of_range` |
| 7 | Pre-attivazione (oggi) | UNAVAILABLE | no | `apps/cases/test_france_review_gated_e2e_p0_mvp_1.py` (esistente) |

**6 nuovi test** post-attivazione. **1 test pre-attivazione** che
sopravvive solo finché l'attivazione non è eseguita, poi viene
sostituito.

---

## 10. Cosa NON è in scope per la v1

Per chiarezza — il futuro PR di attivazione **non** copre:

- *Souffrances endurées*: scala 1–7 Mornet — richiede una riga
  diversa e un secondo `row_type`. Iter futuro.
- *Préjudice esthétique permanent* / *temporaire*: idem.
- *Perte de gains professionnels futurs*: richiede la Gazette per
  capitalizzazione. Iter futuro.
- *Préjudice d'affection* per relazione (parente di vittima): è
  in Mornet 2024 (11 righe), ma è una case-type diversa
  (`death_compensation_parental`) e ha una propria formula. Iter
  futuro.
- *Tierce personne* (assistenza di terzi): non in v1.
- *Frais médicaux et hospitaliers*: documenti elencati come
  "missing documents", non aggregati.
- *Dintilhac mapping completo*: la v1 mostra solo DFP come voce
  Dintilhac. Altri postes (12+ voci) richiedono mappature
  separate, eseguibili in un iter di reportistica successivo.

Tutto quanto sopra è esplicitamente "fuori v1" — significa che il
calcolatore restituisce il numero v1 + missing-documents per il
resto + CTA Studio. Non significa che il consumatore "non sa di
questi diritti": il sistema **dichiara** che esistono e che
servono valutazioni separate.
