# FR — Gazette du Palais 2022 — Estrazione candidate (QA report)

**Iter**: F-france-extraction-gazette-capitalisation · iter1
**Data**: 2026-04-29
**Stato**: candidate read-only — **nessun import DB, nessuna
approvazione**.

> Output di estrazione automatica via `pdfplumber` del barème de
> capitalisation 2022 della Gazette du Palais. I CSV prodotti sono
> in `legal_data/sources/france/gazette_2022/` (path **gitignored**:
> `legal_data/sources/**/*.csv`). Solo il presente report e gli
> script `scripts/legal_data/extract_france_gazette_2022.py` /
> `…/qa_france_gazette_2022.py` sono committabili.

---

## 1. PDF di provenienza

| Attributo | Valore |
|---|---|
| Slug | `fr-bareme-capitalisation-gazette-palais-2022` |
| Path | `legal_data/sources/france/downloaded/fr-bareme-capitalisation-gazette-palais-2022.pdf` |
| Size | 978.456 byte |
| SHA-256 | `686a557b23fa9e76fcd30795e61fda1cc2396d230290b93398874203ebbef3ee` |
| Pagine | 20 |
| Verifica | OK — hash = manifest |

`LegalSource` corrispondente (slug
`fr-bareme-capitalisation-gazette-palais-2022`) è in stato
`needs_review`. L'estrazione **non** la promuove. Resta `needs_review`.

---

## 2. Pagine estratte e tabelle viste

### 2.1. Capitalisation (p.5-20) — 16 tabelle

Layout: ogni pagina = una tabella `[Âge attribution] × [viagère + 19
target_age]`. Le 16 pagine coprono le 4 combinazioni `(sex × rate)`,
ciascuna spezzata su 4 pagine per range di età (0-29, 30-60, 61-91,
92+).

| Pagina | Mortality | Sex | Rate (%) | Age range | viager rows | temporaire rows |
|---:|---|:---:|---:|:---:|---:|---:|
| 5 | INSEEF-2017-2019 | F | -1.00 | 0-29 | 30 | 519 |
| 6 | INSEEF-2017-2019 | F | -1.00 | 30-60 | 31 | 383 |
| 7 | INSEEF-2017-2019 | F | -1.00 | 61-91 | 31 | 36 |
| 8 | INSEEF-2017-2019 | F | -1.00 | 92+ | 12 | 0 |
| 9 | INSEEH-2017-2019 | M | -1.00 | 0-29 | 30 | 519 |
| 10 | INSEEH-2017-2019 | M | -1.00 | 30-60 | 31 | 383 |
| 11 | INSEEH-2017-2019 | M | -1.00 | 61-91 | 31 | 36 |
| 12 | INSEEH-2017-2019 | M | -1.00 | 92+ | 12 | 0 |
| 13 | INSEEF-2017-2019 | F | 0.00 | 0-29 | 30 | 519 |
| 14 | INSEEF-2017-2019 | F | 0.00 | 30-60 | 31 | 383 |
| 15 | INSEEF-2017-2019 | F | 0.00 | 61-91 | 31 | 36 |
| 16 | INSEEF-2017-2019 | F | 0.00 | 92+ | 12 | 0 |
| 17 | INSEEH-2017-2019 | M | 0.00 | 0-29 | 30 | 519 |
| 18 | INSEEH-2017-2019 | M | 0.00 | 30-60 | 31 | 383 |
| 19 | INSEEH-2017-2019 | M | 0.00 | 61-91 | 31 | 36 |
| 20 | INSEEH-2017-2019 | M | 0.00 | 92+ | 12 | 0 |
| **Totale** | | | | | **416** | **3.752** |

### 2.2. Anticipated payment years (p.4) — 2 tabelle

| Tabella | Rate (%) | Età coperte | Sex | Rows |
|---:|---:|:---:|:---:|---:|
| 1 | 0.00 | 20, 30, 40, 50, 60 | M, F | 10 |
| 2 | -1.00 | 20, 30, 40, 50, 60 | M, F | 10 |
| **Totale** | | | | **20** |

---

## 3. Schema CSV candidate

I 3 CSV hanno tutti la colonna `source_note` con metadata di audit:

```
extraction=automated_pdfplumber;
legal_review_required=true;
no_human_legal_approval=true;
pdf_sha256=686a557b23fa9e76fcd30795e61fda1cc2396d230290b93398874203ebbef3ee;
pdf_slug=fr-bareme-capitalisation-gazette-palais-2022;
extractor_script=scripts/legal_data/extract_france_gazette_2022.py;
iter=F-france-extraction-gazette-capitalisation
```

### 3.1. `fr-gazette-2022-capitalisation-viagere.csv`

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `fr_capitalisation_viagere_per_age_sex_rate_coefficient` | costante per file |
| `mortality_table` | str | `INSEEF-2017-2019` / `INSEEH-2017-2019` | discriminante |
| `sex` | str | `M` / `F` | redondante con mortality, utile per query |
| `age` | int | `32` | età d'attribution della rente |
| `interest_rate_pct` | str | `-1.00` / `0.00` | sempre 2 decimali |
| `coefficient` | decimal | `72.459` | capitale per €1 rente annuelle |
| `source_page` | int | `6` | pagina del PDF |
| `source_note` | str | (vedi sopra) | audit completo |

**Righe**: 416 (= 4 combo `(sex×rate)` × 104 età 0..103).

### 3.2. `fr-gazette-2022-capitalisation-temporaire.csv`

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient` | costante |
| `mortality_table` | str | `INSEEF-2017-2019` | |
| `sex` | str | `M` / `F` | |
| `age` | int | `30` | età d'attribution |
| `interest_rate_pct` | str | `-1.00` | sempre 2 decimali |
| `target_age` | int | `69` | "Âge dernier arrérage" |
| `coefficient` | decimal | `45.144` | capitale per €1 rente fino a target_age |
| `source_page` | int | `6` | |
| `source_note` | str | (vedi sopra) | |

**Righe**: 3.752 (combinazioni `(sex × rate × age × target_age)` con
`target_age > age`, dato che le rentes con `target_age <= age` non
hanno periodo di pagamento e sono celle vuote nel PDF).

### 3.3. `fr-gazette-2022-anticipated-payment-years.csv`

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `fr_anticipated_payment_years_per_age_sex_rate_years` | costante |
| `mortality_table` | str | `INSEE-2017-2019` | il PDF non distingue M/F qui |
| `sex` | str | `M` / `F` | colonna della tabella |
| `age` | int | `30` | età d'attribution |
| `interest_rate_pct` | str | `-1.00` / `0.00` | sempre 2 decimali |
| `years_value` | decimal | `66.6` | anni anticipati |
| `source_page` | int | `4` | |
| `source_note` | str | (vedi sopra) | |

**Righe**: 20 (= 2 rates × 5 età {20,30,40,50,60} × 2 sessi).

### 3.4. `extraction_summary.json` (audit run)

File JSON con: `pdf_sha256`, lista pagine processate, metadata
estratti per pagina (sex, mortality, rate), conteggi viager/temporaire
per pagina, totali. Utile per audit del run senza re-eseguire l'estrazione.

---

## 4. Normalizzazione numerica

Convenzioni nel PDF (verificate da spot-check ufficiale, vedi §6):

| Sezione | Formato grezzo | Convenzione | Parser |
|---|---|---|---|
| Capitalisation (p.5-20) | `66.602` | PUNTO = decimale | `parse_capital_decimal()`: `Decimal(s)` diretto |
| Anticipated years (p.4) | `66,6` | VIRGOLA = decimale | `parse_year_decimal()`: replace `,` → `.` poi `Decimal(s)` |
| Tassi nella testata | `Taux d'intérêt = -1.00%` | PUNTO = decimale | regex `(-?\d+(?:[.,]\d+)?)` + replace |
| Tassi nel testo p.4 | `DE - 1 %` | nessun decimale | parser dedicato + `.quantize(Decimal('0.00'))` per uniformare a 2 decimali |

Tutti i `interest_rate_pct` nei CSV sono normalizzati come stringa
fissa a 2 decimali: `-1.00`, `0.00`. Tutti i `coefficient` e
`years_value` sono stringhe numeriche serializzate da `Decimal`.

---

## 5. QA — esiti

QA eseguita via `scripts/legal_data/qa_france_gazette_2022.py`
(read-only, non modifica i CSV). Esito complessivo: **PASS su tutti
i check**.

### 5.1. Conteggi attesi vs trovati

| Check | Atteso | Trovato | Esito |
|---|---:|---:|:-:|
| viager rows totali | 416 | 416 | PASS |
| anticipated rows totali | 20 | 20 | PASS |
| viager (F, -1.00) ages | 104 | 104 | PASS |
| viager (M, -1.00) ages | 104 | 104 | PASS |
| viager (F, 0.00) ages | 104 | 104 | PASS |
| viager (M, 0.00) ages | 104 | 104 | PASS |
| anticipated (M, -1.00) ages | 5 | 5 | PASS |
| anticipated (F, -1.00) ages | 5 | 5 | PASS |
| anticipated (M, 0.00) ages | 5 | 5 | PASS |
| anticipated (F, 0.00) ages | 5 | 5 | PASS |
| range età viager | 0..103 contigue | 0..103 contigue | PASS |

### 5.2. Duplicati

| Check | Trovati | Esito |
|---|---:|:-:|
| Duplicati viager su `(sex, age, rate)` | 0 | PASS |
| Duplicati temporaire su `(sex, age, rate, target_age)` | 0 | PASS |

### 5.3. Null e negativi

| Check | Trovati | Esito |
|---|---:|:-:|
| Null in `viager.coefficient` | 0 | PASS |
| Negativi in `viager.coefficient` | 0 | PASS |
| Null in `temporaire.coefficient` | 0 | PASS |
| Negativi in `temporaire.coefficient` | 0 | PASS |

### 5.4. Plausibilità — monotonicità

| Check | Esito |
|---|:-:|
| viager strict decreasing in `age` per `(F, -1.00)` (104 righe) | PASS |
| viager strict decreasing in `age` per `(M, -1.00)` (104 righe) | PASS |
| viager strict decreasing in `age` per `(F, 0.00)` (104 righe) | PASS |
| viager strict decreasing in `age` per `(M, 0.00)` (104 righe) | PASS |
| viager(rate=-1.00) > viager(rate=0.00) per ogni `(sex, age)` (208 confronti) | PASS |
| temporaire strict increasing in `target_age` per ogni `(sex, rate, age)` (276 buckets) | PASS |

Le tre proprietà oracolari sono soddisfatte:
1. **Decremento con l'età**: a parità di sesso e tasso, capitale
   necessario decresce con l'età d'attribution (vita residua minore).
2. **Decremento con il tasso**: tasso più basso (-1.00%) → capitale
   maggiore rispetto a tasso 0.00% (necessità di maggior capitale per
   compensare rendimento basso/negativo).
3. **Crescita con la durata**: per la rente temporaire, fissati età e
   tasso, capitale cresce con `target_age` (durata maggiore = più
   capitale).

### 5.5. Spot-check ufficiale (esempio PDF p.4)

L'esempio "En pratique" a p.4 del PDF cita:
> *Exemple [...] pour une rente viagère annuelle de 1 000 € chez une
> victime de 32 ans de sexe féminin [...]*
> *- 53,564 × 1 000 = 53 564 € avec un taux d'actualisation nul ;*
> *- 72,459 × 1 000 = 72 459 € avec un taux d'actualisation égal à - 1 %.*

| Spot-check | Atteso | Trovato (CSV) | Esito |
|---|---:|---:|:-:|
| `(F, age=32, rate=-1.00%)` viager | 72.459 | 72.459 | PASS |
| `(F, age=32, rate=0.00%)` viager | 53.564 | 53.564 | PASS |

Lo spot-check **dimostra** che il parser di numeri francesi nel PDF
(punto = decimale nelle tabelle di capitalisation) è corretto e che
nessun valore è stato mal-interpretato come migliaia.

### 5.6. Sample valori — sanity visiva

Estratto direttamente dai CSV:

```
viager — primi e ultimi:
  F age=0   rate=-1.00 coeff=136.868
  F age=1   rate=-1.00 coeff=134.953
  F age=2   rate=-1.00 coeff=132.634
  F age=100 rate=-1.00 coeff=1.640
  F age=101 rate=-1.00 coeff=1.371
  F age=102 rate=-1.00 coeff=1.050
  M age=101 rate=0.00  coeff=1.350
  M age=102 rate=0.00  coeff=1.049
  M age=103 rate=0.00  coeff=0.657

temporaire — esempio età 0 → target 69:
  F age=0 rate=-1.00 ta=69 coeff=97.468
  F age=0 rate=-1.00 ta=68 coeff=95.670
  F age=0 rate=-1.00 ta=67 coeff=93.876

temporaire — limite vicino a viager:
  M age=67 rate=0.00 ta=69 coeff=1.954
  M age=67 rate=0.00 ta=68 coeff=0.985
  M age=68 rate=0.00 ta=69 coeff=0.984
```

I valori coprono tutto il range atteso e sono coerenti con valori
tipici della letteratura di capitalisation francese (coefficienti tra
~0.5 e ~140 con rate basso e età bassa).

---

## 6. Cosa deve verificare lo Studio prima dell'`approved`

Prima che lo Studio possa creare un `LegalReview` su questa
`LegalSource` e promuovere lo status a `approved`:

1. **Cross-check campionario** — selezionare 10-20 righe a campione
   da ciascuno dei 3 CSV e confermare valore-per-valore contro il
   PDF (lettura paginata umana).
2. **Conferma tabelle di mortalità** — verificare che lo Studio
   accetta le tabelle INSEE 2017-2019 (split H/F) come riferimento
   per le simulazioni; in caso contrario indicare quale tabella
   alternativa usare (es. INSEE H+F unisex).
3. **Conferma tassi di attualizzazione applicabili** — il barème
   2022 fornisce solo i due tassi `-1.00%` e `0.00%`. Se lo Studio
   intende usare un tasso intermedio (es. `-0.50%`), dovrà essere
   chiarito se interpolare o limitare le simulazioni ai due tassi
   archiviati.
4. **Verifica edizione** — confermare che il barème 2022 è quello
   ancora di uso giurisprudenziale al momento dell'integrazione, o
   se va sostituito con un'edizione successiva (Gazette 2023/2024/
   2025). La pagina HTML 2025 è scaricata ma il PDF 2025 **non è in
   archivio** in iter1.
5. **Verifica copertura** — Mornet 2024 e Gazette 2022 coprono solo
   la capitalisation. Voci aggiuntive (souffrances endurées,
   préjudice esthétique, agrément, perte de chance, tierce personne,
   …) **non sono in questi CSV** e dovranno essere prodotte in iter
   distinti.
6. **Verifica unità di misura** — il `coefficient` è "capital
   constitutif d'une rente payable à terme échu" per ogni €1 di
   rente annuelle. Lo Studio deve confermare che questa è
   l'interpretazione corretta per i casi che simuleremo (rente
   annuelle vs trimestrielle vs mensuelle).
7. **Approvazione dataset** — solo dopo aver completato i 6 step
   precedenti, lo Studio può approvare via Django admin la
   `LegalSource` (status → `approved`) e successivamente importare
   i CSV come `CompensationDataset` `(version_label = "GAZETTE-PALAIS-2022")`
   tramite un comando di import dedicato (**non ancora implementato
   in iter1**: questa fase è solo di estrazione candidate).

---

## 7. File creati / modificati in iter1

### Committabili

- `docs/legal_sources/FRANCE_GAZETTE_2022_EXTRACTION_REPORT.md` (questo file)
- `scripts/legal_data/extract_france_gazette_2022.py` (extraction read-only)
- `scripts/legal_data/qa_france_gazette_2022.py` (QA read-only)

### Non committabili (gitignored)

- `legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-viagere.csv` (416 righe)
- `legal_data/sources/france/gazette_2022/fr-gazette-2022-capitalisation-temporaire.csv` (3.752 righe)
- `legal_data/sources/france/gazette_2022/fr-gazette-2022-anticipated-payment-years.csv` (20 righe)
- `legal_data/sources/france/gazette_2022/extraction_summary.json` (audit run)

### Non modificati (per regola fondamentale)

- nessun calcolatore (`apps/calculators/engines/france.py` non esiste e non è creato)
- nessun wizard FR
- nessun template
- nessun seeder Italia/TUN
- nessun `apps/compensation/models.py`
- nessun `LegalReview` creato
- nessun `CompensationDataset` creato
- nessun `CalculationFormula` creato
- nessuna `LegalSource` FR promossa: la `fr-bareme-capitalisation-gazette-palais-2022`
  rimane `needs_review`
- nessun command di import scritto (**fuori scope iter1**)
- Italia/TUN totalmente invariate

---

## 8. Disclaimer

> Questo documento descrive un **output di estrazione automatica** non
> ancora validato giuridicamente. Ogni valore in questi CSV è
> `extraction=automated_pdfplumber`, `legal_review_required=true`,
> `no_human_legal_approval=true`. Qualsiasi uso in calcoli pubblici è
> **vietato** finché lo Studio non avrà completato il processo di
> review descritto in §6 e promosso la `LegalSource` a `approved`.
>
> La regola fondamentale del prodotto si applica integralmente:
> meglio nessun calcolo che un calcolo basato su valori non validati
> da un revisore legale qualificato.
