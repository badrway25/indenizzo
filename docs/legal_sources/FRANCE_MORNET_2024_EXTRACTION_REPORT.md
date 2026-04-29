# FR — Référentiel Mornet 2024 — Estrazione candidate (QA report)

**Iter**: F-france-mornet-extraction-tables · iter1
**Data**: 2026-04-29
**Stato**: candidate read-only — **nessun import DB, nessuna
approvazione**.

> Output di estrazione automatica via `pdfplumber` delle 2 sole
> tabelle di riferimento del *Référentiel Mornet 2024* (Conseiller
> Benoît Mornet, Cour de cassation, septembre 2024). I CSV prodotti
> sono in `legal_data/sources/france/mornet_2024/` (path
> **gitignored**: `legal_data/sources/**/*.csv`). Solo il presente
> report e gli script `scripts/legal_data/extract_france_mornet_2024.py`
> e `…/qa_france_mornet_2024.py` sono committabili.

---

## ⚠️ Avvertenza fondamentale — Mornet è référentiel indicativo, non vincolante

Il *Référentiel Mornet* è una **proposta dottrinale** elaborata dal
Conseiller à la Cour de cassation Benoît Mornet, ad uso interno della
magistratura francese. **Non è una norma vincolante**, **non è un
décret**, **non ha forza di legge**. La giurisprudenza francese può
discostarsene caso per caso, e Cours d'appel diverse possono adottare
fourchettes diverse.

Conseguenza per il prodotto:

- I valori di questi CSV sono **una proposta dottrinale** e devono
  essere usati come **stima indicativa**, mai come "valore di legge".
- Nel report al cliente lo Studio deve dichiarare esplicitamente che
  la simulazione si basa sul Référentiel Mornet (référentiel
  indicatif) e che la décision finale dipende dal magistrato del
  caso.
- Il `disclaimer` del prodotto (CLAUDE.md) si applica integralmente:
  *"La simulazione è indicativa e non costituisce parere legale,
  medico-legale o garanzia di risultato. La valutazione effettiva
  dipende da documenti, perizie, responsabilità, legge applicabile,
  giurisdizione competente, orientamenti giudiziari e prassi
  assicurative."*
- Lo Studio **deve** dichiarare in fase di review legale che il
  contenuto del Référentiel Mornet può variare tra Cours d'appel e
  che il valore "moyen" del barème ha valore puramente orientativo.

---

## 1. PDF di provenienza

| Attributo | Valore |
|---|---|
| Slug | `fr-referentiel-mornet-2024` |
| Path | `legal_data/sources/france/downloaded/fr-referentiel-mornet-2024.pdf` |
| Size | 898.965 byte |
| SHA-256 | `2dd2e760bc057b38275a7a6de24a62c009f6d04dd79573c00ee052f4f6df72b4` |
| Pagine | 116 |
| Edizione | Septembre 2024 (Conseiller Benoît Mornet) |
| Verifica hash | OK — match con `download_manifest.json` |

`LegalSource` corrispondente: `fr-referentiel-mornet-2024` resta in
stato **`needs_review`**. L'estrazione **non** la promuove.

---

## 2. Scope e pagine estratte

### 2.1. Pagine INCLUSE (iter1)

| Pagina | Tabella | Tipo | Output CSV |
|---:|---|---|---|
| **71** | DFP / déficit fonctionnel permanent | Grid `[%invalidità] × [classe d'età]` → € **per punto DFP** | `fr-mornet-2024-dfp-per-age-disability.csv` |
| **94** | Préjudice d'affection | Fourchette per relazione familiare in caso di décès | `fr-mornet-2024-prejudice-affection-per-relation.csv` |

### 2.2. Pagine ESCLUSE — perché

| Pagina | Contenuto | Motivo dell'esclusione |
|---:|---|---|
| **88** | Tabella esempio "riparto CPAM/mutuelle" su un caso fittizio (DFP 9.200 €, perte gains 6.900 €, …) | È un **esempio pedagogico** che illustra la *meccanica del riparto* tra responsabile/CPAM/mutuelle, **non è una fonte di valori indicativi**. I numeri sono inventati per l'esempio (Mornet usa "9.200 €" per spiegare il calcolo, non per indicare quanto vale un DFP). Importarli come fonte sarebbe **inventare dati legali**. |
| **108** | Tabella esempio "accident du travail" con riparto victime / tiers payeur | Idem — esempio pedagogico, non riferimento. I valori (10.000 € DFP, 3.000 € incidence, …) sono cifre tonde di esempio. |
| **65-76, 78-87, 89-93, 95-107, 109-116** | Sezioni narrative su DFT, souffrances endurées, esthétique, agrément, sexuel, établissement, tierce personne, frais d'aménagement, perte de chance, accidents du travail, … | Le fourchettes sono **citate inline nel narrativo** (es. "souffrances 1/7 = 1.000 € à 2.000 €") ma non sono in tabella strutturata. **Estrazione automatica vietata**: lo Studio dovrà transcriverle manualmente in un iter dedicato (`F-france-mornet-manual-fourchettes`). |

---

## 3. Schema CSV candidate

Tutti i CSV hanno la colonna `source_note` con metadata di audit:

```
extraction=automated_pdfplumber;
legal_review_required=true;
no_human_legal_approval=true;
pdf_sha256=2dd2e760bc057b38275a7a6de24a62c009f6d04dd79573c00ee052f4f6df72b4;
pdf_slug=fr-referentiel-mornet-2024;
extractor_script=scripts/legal_data/extract_france_mornet_2024.py;
iter=1
```

### 3.1. `fr-mornet-2024-dfp-per-age-disability.csv`

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `fr_dfp_per_age_disability_amount_per_point` | costante per file |
| `victim_age_min` | int | `21` | classe età min |
| `victim_age_max` | int | `30` | classe età max (`120` per "81+") |
| `disability_min` | int | `31` | %DFP min |
| `disability_max` | int | `35` | %DFP max (`100` per "96+ %") |
| `amount_min` | decimal | `3740` | € **per punto DFP** (cella unica → min=mid=max) |
| `amount_mid` | decimal | `3740` | idem |
| `amount_max` | decimal | `3740` | idem |
| `currency` | str | `EUR` | costante |
| `source_page` | int | `71` | costante |
| `source_note` | str | (vedi sopra) | audit |

**Righe**: 180 (= 20 disability bands × 9 age bands, 100% coverage).

> **Nota d'unità importante**: `amount_*` è il **valore di un singolo
> punto di DFP**, NON il totale dell'indennizzo. Per ottenere
> l'indennizzo totale per una vittima specifica, occorre moltiplicare
> per il %DFP effettivo del soggetto. Esempio (dal PDF): "Un homme
> de 25 ans atteint d'un déficit fonctionnel de 32% pourra être
> indemnisé à hauteur de 3.740 € le point" → 32 × 3.740 € ≈ 119.680 €.
> Lo Studio deve confermare in review legale questa interpretazione e
> la formula di applicazione (lineare per default).

### 3.2. `fr-mornet-2024-prejudice-affection-per-relation.csv`

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `row_type` | str | `fr_prejudice_affection_per_relation_amount` | costante |
| `relation_code` | str | `enfant_mineur_perte_parent` | discriminante stabile |
| `relation_label_fr` | str | `Enfant mineur — décès du père ou de la mère` | label legale |
| `amount_min` | decimal | `25000` | minimo della fourchette in € |
| `amount_mid` | decimal | `27500` | media aritmetica `(min+max)/2` — **calcolata, non presente nel PDF** |
| `amount_max` | decimal | `30000` | massimo della fourchette in € |
| `currency` | str | `EUR` | costante |
| `source_page` | int | `94` | costante |
| `source_note` | str | (vedi sopra) | audit |

**Righe**: 11 (= 6 categorie del PDF, alcune con sub-items). Una
riga ("enfant mineur déjà orphelin", "Majoration de 40% à 60%") è
**scartata** (vedi §4.2).

### 3.3. `extraction_summary.json` (audit run)

JSON con `pdf_sha256`, lista pagine processate, totali, dettaglio
delle righe scartate per "Majoration".

---

## 4. Normalizzazione numerica

### 4.1. Importi monetari

Convenzione Mornet (DIVERSA dalla Gazette del barème di
capitalisation):

| Formato grezzo | Convenzione | Decoded |
|---|---|---|
| `2.310` | **PUNTO = separatore migliaia** | 2310 |
| `25 000` | **SPAZIO = separatore migliaia** | 25000 |
| `880` | nessun separatore | 880 |
| `20.000 €` | PUNTO = migliaia + simbolo € | 20000 |
| `15.000 € à 25 000 €` | range con preposizione `à` | (15000, 25000) |

Parser: `parse_eur_amount()` in
`scripts/legal_data/extract_france_mornet_2024.py`.
Strip `€`, strip spazi e punti, validazione cifre, conversione a
`Decimal`.

### 4.2. Range con `à` e Majoration

- `"X € à Y €"` → `(amount_min=X, amount_max=Y, amount_mid=(X+Y)/2)`
- Caso unico (no `à`): `amount_min = amount_mid = amount_max`
- `"Majoration de 40% à 60%"` → **SCARTATO** (è un modificatore
  percentuale per "enfant mineur déjà orphelin", non una fourchette
  monetaria assoluta). Lo Studio dovrà gestirlo manualmente in
  review (es. creare una `CalculationFormula` parametrica del tipo
  `enfant_mineur_perte_parent × (1 + majoration_pct)` con
  `majoration_pct ∈ [40%, 60%]`).

L'`extraction_summary.json` riporta esplicitamente la riga scartata:

```json
{
  "affection_rows_skipped_majoration": 1,
  "affection_skipped_detail": [
    {
      "heading": "Préjudice de l'enfant en cas de décès du père ou de la mère ...",
      "sub": "enfant mineur déjà orphelin",
      "amount": "Majoration de 40% à 60%"
    }
  ]
}
```

### 4.3. Apostrofi tipografici

Il PDF usa apostrofi U+2019 (`’`) invece dell'apostrofo ASCII (`'`).
Il parser normalizza U+2019 → `'` prima del lookup di
`relation_code`, evitando false-negative dovute al matching
sub-stringa.

---

## 5. QA — esiti (verde su tutti i 27 controlli)

QA eseguita via `scripts/legal_data/qa_france_mornet_2024.py`
(read-only, non modifica i CSV). Esito complessivo: **27/27 PASS**.

### 5.1. Conteggi

| Check | Atteso | Trovato | Esito |
|---|---:|---:|:-:|
| DFP rows | 180 | 180 | PASS |
| Affection rows | 11 | 11 | PASS |
| Affection skipped (Majoration) | 1 | 1 | PASS |

### 5.2. Range coverage DFP

- Tutti i 9 age_bands × 20 disability_bands = 180 (age, disability)
  presenti, **zero combinazioni mancanti**, **zero combinazioni
  extra** rispetto allo schema atteso.

### 5.3. Duplicati

| Check | Trovati | Esito |
|---|---:|:-:|
| DFP duplicati su `(age_min, age_max, dis_min, dis_max)` | 0 | PASS |
| Affection duplicati su `relation_code` | 0 | PASS |

### 5.4. Null e negativi

- DFP: 0 null, 0 negativi su `amount_min/mid/max`.
- Affection: 0 null, 0 negativi su `amount_min/mid/max`.

### 5.5. Range coerenti

| Check | Esito |
|---|:-:|
| DFP `min <= mid <= max` (180 righe) | PASS |
| Affection `min <= mid <= max` (11 righe) | PASS |

### 5.6. Plausibilità (oracoli)

| Property | Esito |
|---|:-:|
| **DFP — età ↑ ⇒ valore-punto ↓** (per ogni %DFP, l'indennità per punto decresce con l'età) | PASS (20 buckets, 0 violations) |
| **DFP — %DFP ↑ ⇒ valore-punto ↑** (per ogni classe d'età, l'indennità per punto cresce con la gravità) | PASS (9 buckets, 0 violations) |
| Affection — importi in [1.000 €, 50.000 €] (range Mornet plausibile) | PASS |

### 5.7. Spot-check ufficiale (esempio PDF p.71)

Il PDF a p.71 contiene un esempio applicativo:
> *"EXEMPLE : Un homme de 25 ans atteint d'un déficit fonctionnel de
> 32% pourra être indemnisé à hauteur de 3.740 € le point …"*

| Spot-check | Atteso | Trovato (CSV) | Esito |
|---|---:|---:|:-:|
| `(victim_age=25, disability=32%)` → cella `(age_band=21-30, dis_band=31-35)` | `3.740 €` per punto | `3740` | **PASS** |

Lo spot-check **dimostra** che:
1. la classe d'età è correttamente parsata (25 cade in 21-30);
2. la classe %DFP è correttamente parsata (32% cade in 31-35);
3. il valore "3.740" è correttamente normalizzato come 3740 (e
   **non** come 3.74 — il punto è separatore di migliaia).

### 5.8. Affection — copertura relation_code

| Check | Esito |
|---|:-:|
| Tutti gli 11 `relation_code` attesi presenti | PASS |
| Nessun `relation_code` extra | PASS |

I 11 codici stabili:
1. `conjoint_perte_conjoint`
2. `enfant_mineur_perte_parent`
3. `enfant_majeur_au_foyer_perte_parent`
4. `enfant_majeur_hors_foyer_perte_parent`
5. `parent_perte_enfant`
6. `freres_soeurs_meme_foyer`
7. `freres_soeurs_hors_foyer`
8. `grand_parent_perte_petit_enfant_freq`
9. `grand_parent_perte_petit_enfant_peu_freq`
10. `petit_enfant_perte_grand_parent_freq`
11. `petit_enfant_perte_grand_parent_peu_freq`

### 5.9. Source-note coherence

| Check | Esito |
|---|:-:|
| `source_note` unico identico per tutte le righe (DFP+Affection) | PASS |
| Contiene `extraction=automated_pdfplumber` | PASS |
| Contiene `legal_review_required=true` | PASS |
| Contiene `no_human_legal_approval=true` | PASS |
| Contiene `pdf_sha256=2dd2e7…b4` | PASS |
| Contiene `pdf_slug=fr-referentiel-mornet-2024` | PASS |
| Contiene `iter=1` | PASS |

### 5.10. Sample DFP (sanity visiva)

```
age=[0,10]   dis=[1,5]    amount=2310 (cella più alta in basso a sx)
age=[11,20]  dis=[1,5]    amount=2150 (decresce con età)
age=[71,80]  dis=[96,100] amount=2610
age=[81,120] dis=[96,100] amount=1925 (cella più bassa in basso a dx)
```

### 5.11. Sample Affection (tutte le 11 righe)

```
conjoint_perte_conjoint                       min=20000 mid=25000 max=30000
enfant_mineur_perte_parent                    min=25000 mid=27500 max=30000
enfant_majeur_au_foyer_perte_parent           min=15000 mid=20000 max=25000
enfant_majeur_hors_foyer_perte_parent         min=11000 mid=13000 max=15000
parent_perte_enfant                           min=20000 mid=25000 max=30000
freres_soeurs_meme_foyer                      min=15000 mid=20000 max=25000
freres_soeurs_hors_foyer                      min=11000 mid=13000 max=15000
grand_parent_perte_petit_enfant_freq          min=11000 mid=12500 max=14000
grand_parent_perte_petit_enfant_peu_freq      min= 7000 mid= 8500 max=10000
petit_enfant_perte_grand_parent_freq          min= 6000 mid= 8000 max=10000
petit_enfant_perte_grand_parent_peu_freq      min= 3000 mid= 5000 max= 7000
```

---

## 6. Cosa deve verificare lo Studio prima dell'`approved`

Prima di promuovere `LegalSource` `fr-referentiel-mornet-2024` da
`needs_review` ad `approved`, lo Studio deve completare:

1. **Cross-check campionario DFP** — selezionare 10-20 celle a
   campione dalle 180 e confermarle valore-per-valore contro la
   tabella p.71 del PDF.
2. **Cross-check completo affection** — verificare tutte e 11 le
   righe contro p.94 del PDF (è una tabella piccola, quindi check
   completo è fattibile).
3. **Conferma unità DFP** — confermare che il valore della cella è
   "EUR per **punto** DFP" e che la formula di applicazione lineare
   `total = %DFP × valore_punto` è quella corretta per il caso
   d'uso. In alternativa lo Studio può preferire una formula
   diversa (es. progressiva).
4. **Decisione su "Majoration 40-60% pour orphelin"** — definire
   come gestire la maggiorazione (riga scartata in §4.2):
   - opzione A: escludere il caso "enfant_mineur_orphelin" dal
     calcolatore, mostrando un messaggio "richiede valutazione
     personalizzata Studio";
   - opzione B: aggiungere una riga calcolata
     `enfant_mineur_orphelin_perte_parent` con
     `min = 25000 × 1.40 = 35000`, `max = 30000 × 1.60 = 48000`,
     `mid = (35000+48000)/2 = 41500` — ma SOLO se lo Studio dichiara
     esplicitamente questa interpretazione come legale.
5. **Conferma `relation_code`** — verificare che gli 11 codici
   stabili coprono tutti i casi d'uso del calcolatore FR. Se ne
   mancano (es. concubin de fait sans pacs, partenaire de pacs, …)
   indicare se vanno aggiunti in iter futuro.
6. **Disclaimer specifico** — confermare il testo del disclaimer
   del calcolatore FR quando userà questo dataset, in particolare
   sul fatto che Mornet è référentiel indicativo e che la
   giurisprudenza concreta può essere diversa.
7. **Verifica edizione** — confermare che il référentiel 2024 è
   l'edizione di riferimento attuale e definire la policy per
   future edizioni (Mornet 2025, 2026): il dataset `MORNET-2024`
   resterà come fallback storico, oppure verrà sostituito?
8. **Approvazione fonte** — solo dopo gli step 1-7, lo Studio
   approva via Django admin la `LegalSource`
   `fr-referentiel-mornet-2024` (status → `approved`); a quel punto
   un command di import dedicato (**non in iter1**) potrà
   importare i CSV come `CompensationDataset`
   `(version_label = "MORNET-2024")`.

---

## 7. File creati / modificati in iter1

### Committabili (3 nuovi)

- `docs/legal_sources/FRANCE_MORNET_2024_EXTRACTION_REPORT.md` (questo file)
- `scripts/legal_data/extract_france_mornet_2024.py` (extraction read-only)
- `scripts/legal_data/qa_france_mornet_2024.py` (QA read-only)

### Non committabili (gitignored)

- `legal_data/sources/france/mornet_2024/fr-mornet-2024-dfp-per-age-disability.csv` (180 righe)
- `legal_data/sources/france/mornet_2024/fr-mornet-2024-prejudice-affection-per-relation.csv` (11 righe)
- `legal_data/sources/france/mornet_2024/extraction_summary.json` (audit run)

### Non modificati (per regola fondamentale)

- nessun calcolatore (`apps/calculators/engines/france.py` non
  esiste e non è stato creato)
- nessun wizard FR
- nessun template
- nessun seeder Italia/TUN
- nessun `apps/compensation/models.py`
- nessun `LegalReview` creato
- nessun `CompensationDataset` creato
- nessun `CalculationFormula` creata
- nessuna `LegalSource` FR promossa: `fr-referentiel-mornet-2024`
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
> Inoltre, il *Référentiel Mornet* è una **proposta dottrinale**, non
> una norma di legge. Anche dopo l'`approved`, il calcolatore dovrà
> sempre dichiarare nel report al cliente che il barème Mornet è
> **indicativo** e che la décision finale dipende dal magistrato del
> caso e dalla Cour d'appel competente.
>
> Si applica integralmente la regola fondamentale del prodotto
> (CLAUDE.md): **meglio nessun calcolo che un calcolo basato su
> valori non validati da un revisore legale qualificato**.
