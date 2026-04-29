# BE — Tableau Indicatif 2020 — Estrazione candidate (QA report)

**Iter**: F-belgium-extraction-ti-2020 · iter1
**Data**: 2026-04-29
**Stato**: candidate read-only — **nessun import DB, nessuna
approvazione, dataset storico/fallback**.

> Output di estrazione automatica via `pdfplumber` delle 4 famiglie
> tabulari del *Tableau Indicatif 2020* (édition Union nationale des
> magistrats de police / Vereniging Nationale van politierechters,
> bilingue NL/FR). I CSV prodotti sono in
> `legal_data/sources/belgium/tableau_indicatif_2020/` (path
> **gitignored**: `legal_data/sources/**/*.csv`). Solo questo report
> e gli script `scripts/legal_data/extract_belgium_ti_2020.py` /
> `…/qa_belgium_ti_2020.py` sono committabili.

---

## ⚠️ Avvertenze fondamentali

### Tableau Indicatif è "indicatif", non vincolante

Il *Tableau Indicatif* belga è una **proposta consolidata della
magistratura belga** (Union nationale des magistrats de police /
VNPR) ma **non è una norma di legge**. Le cours d'appel belghe
possono discostarsene caso per caso. Conseguenza:

- ogni report cliente che usa questi valori **deve dichiarare
  esplicitamente** che la simulazione si basa sul Tableau Indicatif
  (référentiel indicatif) e che la décision finale dipende dal
  magistrato del caso.

### BE 2020 è dataset **storico/fallback** — non è il riferimento corrente

Il *Tableau Indicatif 2024* è l'edizione corrente di riferimento
giurisprudenziale; il 2020 è l'edizione precedente. Tuttavia, il PDF
2024 è **image-scanned** (tutte le 23 pagine sono bitmap senza testo
estraibile, vedi `BELGIUM_EXTRACTION_PLANNING.md` §2). L'estrazione
del 2024 richiederà un iter OCR dedicato (`F-belgium-ocr-ti-2024-spike`
+ `F-belgium-extraction-ti-2024`).

In iter1 abbiamo estratto **solo BE 2020**, da usare come:

1. **dataset storico** per fatti generatori datati antecedenti alla
   pubblicazione del 2024 (lo Studio definirà la cut-off date in
   review legale);
2. **template strutturale** per il futuro OCR del 2024 (stesso
   schema colonne, stessi `relation_code` / `vehicle_type_code` per
   il cross-check);
3. **fallback** quando il dataset 2024 sarà `approved` ma per
   ragioni di policy il calcolatore deve restare sul 2020 (es.
   appello pendente).

Quando il 2024 sarà importato, il dataset 2020 verrà marcato
`replaced_by_id = <pk del 2024>` ma resterà query-able.

### Mismatch semantico: p.22-23 NON è "préjudice esthétique"

Il filename `be-ti-2020-prejudice-esthetique.csv` rispetta lo spec
utente, ma la tabella estratta da p.22-23 del PDF è in realtà la
**Tabella delle indennità forfetarie (sezione 3.7. Tableau des
indemnités forfaitaires)** del Tableau Indicatif belga. I valori
sono **€/anno per 1% di incapacité**, applicati alle incapacités
*personnelle*, *ménagère* e *économique* (vedi p.21 testo BE 2020).

Il **préjudice esthétique permanent** belga, secondo BE 2020 sezione
3.4.1.2.b, **non ha un proprio barème distinto in tabella**: condivide
la **stessa scala Julin 1/7..7/7 × età** della *douleur / pijn /
souffrances endurées* (sezione 3.4.1.2.a, tabella a p.17). La
giurisprudenza belga BE 2020 tratta esthétique e douleur con la stessa
griglia.

Conseguenza per la review legale (vedi §6):

- il filename `be-ti-2020-prejudice-esthetique.csv` deve essere
  RINOMINATO o ETICHETTATO chiaramente (es. *Indennité forfaitaire
  per età, non préjudice esthétique*) prima dell'import nel DB;
- il `row_type` interno è già corretto:
  `be_indemnite_forfaitaire_per_age_annual_amount`;
- per il préjudice esthétique permanent BE, lo Studio deciderà se:
  - usare la stessa tabella `be-ti-2020-souffrances-endurees.csv`
    (BE 2020 implica questo nel testo);
  - cercare un barème distinto in altre fonti BE (Schryvers,
    jurisprudence locale Bruxelles).

---

## 1. PDF di provenienza

| Attributo | Valore |
|---|---|
| Slug | `be-tableau-indicatif-2020` |
| Path | `legal_data/sources/belgium/downloaded/be-tableau-indicatif-2020.pdf` |
| Size | 1.985.686 byte |
| SHA-256 | `1b073f5c41c8414018e262143d7e67c496bbeeb832e623f406333b3ece0b8222` |
| Pagine | 46 |
| Edizione | 2020 (édition Union nationale des magistrats de police / VNPR) |
| Bilingue | NL (sinistra) / FR (destra), parallelo riga per riga |
| Verifica hash | OK — match con `download_manifest.json` |

`LegalSource` corrispondente: `be-tableau-indicatif-2020` resta in
stato **`needs_review`**. L'estrazione **non** la promuove.

---

## 2. Pagine estratte (4 famiglie)

| Pagina(e) | Famiglia | Tipo | Output CSV |
|---:|---|---|---|
| **17** | Souffrances endurées / douleur / pijn | Grid `[âge × Julin 1/7..7/7] → €` | `be-ti-2020-souffrances-endurees.csv` |
| **22-23** | Indennité forfaitaire **per età** (NON esthétique — vedi §0) | `[âge] → €/anno per 1% incapacité` | `be-ti-2020-prejudice-esthetique.csv` *(filename utente, contenuto reale ≠ esthétique)* |
| **26** | Préjudice par décès / affection | `[victime décédée → bénéficiaire] → €` | `be-ti-2020-prejudice-deces-affection.csv` |
| **32** | Véhicule de remplacement | `[type véhicule] → €/jour` | `be-ti-2020-vehicule-remplacement.csv` |

Strategia bilingue: **per ogni famiglia preferiamo la versione FR**
(table#1 di p.17, p.26 FR, p.32 FR). I numeri sono identici alla
versione NL; i `relation_code` / `vehicle_type_code` sono codici
stabili snake_case in francese.

---

## 3. Schema CSV candidate

Tutti i CSV hanno la colonna `source_note` con metadata di audit:

```
extraction=automated_pdfplumber;
legal_review_required=true;
no_human_legal_approval=true;
pdf_sha256=1b073f5c41c8414018e262143d7e67c496bbeeb832e623f406333b3ece0b8222;
pdf_slug=be-tableau-indicatif-2020;
extractor_script=scripts/legal_data/extract_belgium_ti_2020.py;
iter=1;
source_is_historical_2020=true
```

### 3.1. `be-ti-2020-souffrances-endurees.csv`

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `be_souffrances_endurees_per_age_severity_amount` | costante |
| `severity_code` | str | `1_7` … `7_7` | scala Julin |
| `severity_label_fr` | str | `minime` / `très léger` / … / `exceptionnellement grave` | label FR canonica |
| `victim_age_min` | int | `0` | classe età min |
| `victim_age_max` | int | `10` | classe età max (`120` per 81+) |
| `amount_min` | decimal | `540.00` | cella unica → min=mid=max |
| `amount_mid` | decimal | `540.00` | idem |
| `amount_max` | decimal | `540.00` | idem |
| `currency` | str | `EUR` | costante |
| `source_page` | int | `17` | costante |
| `source_note` | str | (vedi sopra) | audit |

**Righe**: **63** (= 9 age bands × 7 severities, copertura 100%).

### 3.2. `be-ti-2020-prejudice-esthetique.csv` (= indennità forfaitaria per età)

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `be_indemnite_forfaitaire_per_age_annual_amount` | **riflette il contenuto reale** |
| `severity_code` | str | `default` | nessuna scala di gravità in questa tabella |
| `severity_label_fr` | str | `default (no severity scale)` | placeholder |
| `victim_age_min` | int | `0` | |
| `victim_age_max` | int | `15` (per "Jusque 15 ans"), `120` (per "85+") | |
| `annual_amount` | decimal | `1220.00` | €/anno per 1% incapacité |
| `currency` | str | `EUR` | costante |
| `source_page` | int | `22` o `23` | |
| `source_note` | str | (vedi sopra) | audit |

**Righe**: **71** (= 1 *Jusque 15 ans* + 40 età 16..55 + 29 età 56..84
+ 1 *85+*).

### 3.3. `be-ti-2020-prejudice-deces-affection.csv`

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `be_prejudice_deces_affection_per_relation_amount` | costante |
| `relation_code` | str | `conjoint_perte_conjoint` | snake_case stabile |
| `relation_label_fr` | str | `Conjoint/concubin/pacsé — perte de l'autre …` | FR human |
| `amount_min` | decimal | `15000.00` | cella unica → min=mid=max |
| `amount_mid` | decimal | `15000.00` | idem |
| `amount_max` | decimal | `15000.00` | idem |
| `currency` | str | `EUR` | costante |
| `source_page` | int | `26` | costante |
| `source_note` | str | (vedi sopra) | audit |

**Righe**: **13** relazioni stabili.

### 3.4. `be-ti-2020-vehicule-remplacement.csv`

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `be_vehicule_remplacement_per_type_per_day_amount` | costante |
| `vehicle_type_code` | str | `fr_bicyclette` | snake_case stabile |
| `vehicle_type_label_fr` | str | `Bicyclette (avec/sans assistance, max. 25 km/h)` | FR human |
| `daily_amount_min` | decimal | `10.00` | cella unica → min=mid=max (con sub-rows per remorque/autobus) |
| `daily_amount_mid` | decimal | `10.00` | |
| `daily_amount_max` | decimal | `10.00` | |
| `currency` | str | `EUR` | costante |
| `source_page` | int | `32` | costante |
| `source_note` | str | (vedi sopra) | audit |

**Righe**: **19** (= 12 véhicules semplici + 2 remorque sub-rows
[<750 kg, ≥750 kg] + 5 autobus sub-rows [< 50 / ≥50 / ≥60 / ≥70 / ≥80
posti FR ; in NL le bande sono ≥31/38/44/50, vedi §5]).

**Riga scartata** (1): `camions et véhicules tractés ≥ 3,5 t` — la
cella ha la formula `"50,00 euros + 10,00 euros par tonne"` che
**non è un single rate** ma una formula `base + variabile_per_ton`.
Lo Studio deciderà in review se modellarla come `CalculationFormula`
parametrica o se escluderla dalla simulazione.

---

## 4. Normalizzazione numerica

Convenzione BE 2020 (formato europeo):

| Formato grezzo | Convenzione | Decoded |
|---|---|---|
| `€ 540,00` | `€` simbolo + virgola decimale | 540.00 |
| `€ 2.150,00` | punto migliaia + virgola decimale | 2150.00 |
| `15 000,00` | spazio migliaia + virgola decimale | 15000.00 |
| `10,00 euro` | `euro` testuale + virgola decimale | 10.00 |
| `150,00 euros` | `euros` (FR plural) + virgola decimale | 150.00 |

Parser: `parse_eur_amount()` in
`scripts/legal_data/extract_belgium_ti_2020.py`. Strategia:
1. Strip `€`, `euro`, `euros`, `EUR`.
2. Rimuovi punti/spazi che precedono 3 cifre (= migliaia).
3. Sostituisci virgola con punto.
4. Valida regex `\d+\.\d{2}` o `\d+`, poi `Decimal()`.

---

## 5. QA — esiti (PASS su tutti i 49 controlli)

QA eseguita via `scripts/legal_data/qa_belgium_ti_2020.py`
(read-only, non modifica i CSV). Esito: **49/49 PASS**.

### 5.1. Conteggi

| CSV | Atteso | Trovato | Esito |
|---|---:|---:|:-:|
| Souffrances endurées | 63 | 63 | PASS |
| Esthétique (forfait per età) | 71 | 71 | PASS |
| Décès / affection | 13 | 13 | PASS |
| Véhicule remplacement | 19 | 19 | PASS |
| **Totale** | **166** | **166** | PASS |

### 5.2. Range coverage

| Check | Esito |
|---|:-:|
| SE: tutti i 9×7 (age, severity) presenti, 0 missing/extra | PASS |
| Esthétique: range età 0..120 contiguo (con bande Jusque 15 / 16..84 unitarie / 85+) | PASS |
| Décès: 13/13 `relation_code` attesi presenti, 0 extra | PASS |
| Véhicule: 19/19 `vehicle_type_code` attesi presenti, 0 extra | PASS |

### 5.3. Duplicati, null, negativi

| Check | Trovati | Esito |
|---|---:|:-:|
| Duplicati SE su `(age, severity)` | 0 | PASS |
| Duplicati Esthétique su `(age_min, age_max)` | 0 | PASS |
| Duplicati Décès su `relation_code` | 0 | PASS |
| Duplicati Véhicule su `vehicle_type_code` | 0 | PASS |
| Null in tutti i campi monetari (4 CSV) | 0 | PASS |
| Negativi in tutti i campi monetari | 0 | PASS |
| `min ≤ mid ≤ max` (SE, Décès, Véhicule) | 0 violazioni | PASS |

### 5.4. Plausibilità (oracoli)

| Property | Esito |
|---|:-:|
| **SE — severity ↑ ⇒ amount ↑** (per ogni età, l'indennità cresce con la gravità Julin) | PASS (9 buckets, 0 violazioni) |
| **SE — età ↑ ⇒ amount ↓** (per ogni severity, l'indennità decresce con l'età) | PASS (7 buckets, 0 violazioni) |
| **Esthétique — età ↑ ⇒ annual_amount ↓** (forfait decresce strettamente da 1220 a 165 €) | PASS |

### 5.5. Spot-check ufficiali (estratti dal PDF)

| Spot-check | Atteso | Trovato | Esito |
|---|---:|---:|:-:|
| SE `(0-10, 1/7)` | 540.00 | 540.00 | PASS |
| SE `(0-10, 7/7)` | 30 000.00 | 30 000.00 | PASS |
| SE `(81+, 1/7)` | 115.00 | 115.00 | PASS |
| SE `(81+, 7/7)` | 6 400.00 | 6 400.00 | PASS |
| Esth `Jusque 15 ans` | 1 220.00 | 1 220.00 | PASS |
| Esth `16 ans` | 1 200.00 | 1 200.00 | PASS |
| Esth `85+` | 165.00 | 165.00 | PASS |
| Décès `conjoint_perte_conjoint` | 15 000.00 | 15 000.00 | PASS |
| Décès `parent_cohabitant_perte_enfant_cohabitant_orphelin` | 24 000.00 | 24 000.00 | PASS |
| Décès `petits_enfants_non_cohabitants_perte_grands_parents_non_cohabitants` | 1 500.00 | 1 500.00 | PASS |
| Véhicule `fr_bicyclette` | 10.00 | 10.00 | PASS |
| Véhicule `fr_voiture_perso_pro` | 20.00 | 20.00 | PASS |
| Véhicule `fr_vehicules_lourds_speciaux` | 150.00 | 150.00 | PASS |
| Véhicule `fr_autobus_80_plus` | 180.00 | 180.00 | PASS |

### 5.6. Source-note coherence

| Check | Esito |
|---|:-:|
| `source_note` unico per tutti i 166 record | PASS |
| Contiene `extraction=automated_pdfplumber` | PASS |
| Contiene `legal_review_required=true` | PASS |
| Contiene `no_human_legal_approval=true` | PASS |
| Contiene `pdf_sha256=1b073f5…b8222` | PASS |
| Contiene `pdf_slug=be-tableau-indicatif-2020` | PASS |
| Contiene `iter=1` | PASS |
| Contiene `source_is_historical_2020=true` | PASS |
| `currency=EUR` su tutti i record | PASS |

---

## 6. Ambiguità bilingui rilevate (NL/FR)

### 6.1. Tabelle bilingual con cella interna NL+FR mescolata

`pdfplumber.find_tables()` divide spesso le label NL/FR su più colonne
quando entrambe le lingue compaiono nella stessa cella PDF. Esempi:

- p.17 SE r.1 (FR labels): cella severity 4/7 split su 2 colonne (col
  4 vuoto, col 5 = `moyen`). Risolto via mappatura severity hard-coded
  (vedi `SEVERITY_FR` in `extract_belgium_ti_2020.py`).
- p.26 décès r.1 (FR): label beneficiary "Conjoint/concubin/pacsé"
  split su 3 celle (`Conjoi` + `n` + `t/concubin/pacsé`). Risolto
  parsando il **TESTO della pagina** (linea unica) invece delle celle
  pdfplumber.

### 6.2. Bande autobus diverse tra NL e FR

p.31 NL e p.32 FR riportano bande di posti **diverse** per autobus/
autocar:

| Bande FR (p.32) | Bande NL (p.31) | Indemnité/jour |
|---|---|---:|
| < 50 places | < 31 plaatsen | 50 € |
| ≥ 50 places | ≥ 31 plaatsen | 90 € |
| ≥ 60 places | ≥ 38 plaatsen | 115 € |
| ≥ 70 places | ≥ 44 plaatsen | 140 € |
| ≥ 80 places | ≥ 50 plaatsen | 180 € |

**Le bande NL e FR si riferiscono a sistemi di conteggio diversi**
(probabilmente posti totali vs posti seduti). Lo Studio deve
chiarire in review legale quale convenzione usare nel calcolatore.
Per iter1 abbiamo adottato **le bande FR** (codici `fr_autobus_*`)
e documentiamo entrambe nel `vehicle_type_label_fr`:
*"Autobus/autocar < 50 places (NL: < 31 places)"*.

### 6.3. Codici stabili — convenzione

I `relation_code` e `vehicle_type_code` sono **snake_case basati sui
termini FR**. Esempi: `frere_soeur_cohabitant_perte_frere_soeur_cohabitant`,
`fr_voiture_perso_pro`. La convenzione è documentata nel report e
deve essere **stabile** quando il dataset 2024 sarà importato (= same
codes per cross-check).

---

## 7. Cosa deve verificare lo Studio prima dell'`approved`

Prima di promuovere `LegalSource` `be-tableau-indicatif-2020` da
`needs_review` ad `approved`:

1. **Cross-check campionario** — selezionare 10-20 righe a campione
   da ognuno dei 4 CSV e confermare valore-per-valore contro il PDF
   (la rilettura paginata umana è essenziale, soprattutto per le
   bande età/severity).
2. **Decisione sul filename `prejudice-esthetique`** — confermare
   se:
   - usare il filename utente lasciando `row_type` corretto e
     documentando la mismatch (raccomandazione iter1);
   - rinominare il CSV come
     `be-ti-2020-indemnite-forfaitaire-par-age.csv` per riflettere
     il contenuto reale.
3. **Decisione su préjudice esthétique permanent** — se BE 2020
   condivide la stessa scala Julin di SE, decidere se:
   - applicare la stessa tabella `souffrances-endurees` anche per
     l'esthétique permanent (consistente con BE 2020);
   - cercare un barème esthétique distinto in altre fonti BE.
4. **Decisione su `camions ≥ 3,5 t`** (riga véhicule scartata) —
   modellare la formula `50 + 10×ton` come `CalculationFormula`
   parametrica o escludere dalla simulazione?
5. **Decisione su bande autobus NL vs FR** — quale convenzione di
   conteggio applicare (vedi §6.2)?
6. **Decisione su cut-off date 2020 vs 2024** — quando il dataset
   2024 sarà `approved`, fino a che data del fatto generatore il
   2020 deve restare attivo come fallback?
7. **Disclaimer specifico** — confermare il testo del disclaimer
   del calcolatore BE che dichiara *"référentiel indicatif Tableau
   Indicatif 2020 — la giurisprudenza belga concreta può
   discostarsene"*.
8. **Approvazione fonte** — solo dopo gli step 1-7, lo Studio
   approva via Django admin la `LegalSource` (status →
   `approved`); a quel punto un command di import dedicato
   (**non in iter1**) potrà importare i 4 CSV come
   `CompensationDataset` `(version_label = "TABLEAU-INDICATIF-2020")`,
   con `status = historical` (subset di `replaced` quando 2024
   sarà importato).

---

## 8. File creati / modificati in iter1

### Committabili (3 nuovi)

- `docs/legal_sources/BELGIUM_TI_2020_EXTRACTION_REPORT.md` (questo file)
- `scripts/legal_data/extract_belgium_ti_2020.py` (extraction read-only)
- `scripts/legal_data/qa_belgium_ti_2020.py` (QA read-only)

### Non committabili (gitignored)

- `legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-souffrances-endurees.csv` (63 righe)
- `legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-prejudice-esthetique.csv` (71 righe — *contenuto reale: indennité forfaitaire per età*)
- `legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-prejudice-deces-affection.csv` (13 righe)
- `legal_data/sources/belgium/tableau_indicatif_2020/be-ti-2020-vehicule-remplacement.csv` (19 righe)
- `legal_data/sources/belgium/tableau_indicatif_2020/extraction_summary.json` (audit run)

### Non modificati (per regola fondamentale)

- nessun calcolatore (`apps/calculators/engines/belgium.py` non
  esiste e non è stato creato)
- nessun wizard BE
- nessun template
- nessun seeder Italia/TUN
- nessun `apps/compensation/models.py`
- nessun `LegalReview` creato
- nessun `CompensationDataset` creato
- nessun `CalculationFormula` creata
- nessuna `LegalSource` BE promossa: `be-tableau-indicatif-2020`
  rimane `needs_review`
- nessun command di import scritto (**fuori scope iter1**)
- Italia/TUN totalmente invariate
- BE 2024 (image-scanned) **non toccato** in iter1

---

## 9. Disclaimer

> Questo documento descrive un **output di estrazione automatica**
> non ancora validato giuridicamente. Ogni valore in questi CSV è
> `extraction=automated_pdfplumber`, `legal_review_required=true`,
> `no_human_legal_approval=true`, `source_is_historical_2020=true`.
> Qualsiasi uso in calcoli pubblici è **vietato** finché lo Studio
> non avrà completato il processo di review descritto in §7 e
> promosso la `LegalSource` a `approved`.
>
> Il *Tableau Indicatif 2020* è una **proposta consolidata** della
> magistratura di police belga, NON una norma di legge. Anche dopo
> l'`approved`, ogni report cliente che usa questi valori deve
> dichiarare esplicitamente che la simulazione si basa sul
> **référentiel indicatif** belga e che la décision finale dipende
> dal magistrato del caso.
>
> Inoltre, BE 2020 è un dataset **storico/fallback**: l'edizione
> giurisprudenziale corrente è il *Tableau Indicatif 2024*, non
> ancora estratto in iter1 perché il PDF è image-scanned e richiede
> un pipeline OCR dedicato.
>
> Si applica integralmente la regola fondamentale del prodotto
> (CLAUDE.md): **meglio nessun calcolo che un calcolo basato su
> valori non validati da un revisore legale qualificato**.
