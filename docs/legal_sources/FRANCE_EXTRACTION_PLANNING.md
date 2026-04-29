# FR — Piano tecnico di estrazione (read-only planning)

**Iter**: F-france-belgium-extraction-planning · iter1
**Data**: 2026-04-29
**Stato**: planning — **nessuna estrazione, nessun import DB,
nessuna approvazione**.

> Documento di lavoro per il prossimo iter di parsing (F-france-extraction-mornet
> e F-france-extraction-gazette). Tutto ciò che è scritto qui è una proposta
> tecnica: nessuna fonte FR è ancora `approved`, nessun `CompensationDataset`
> e nessuna `CalculationFormula` esiste per la giurisdizione `FR-NATIONAL`.

---

## 1. PDF analizzati e verifica integrità

Hash SHA-256 calcolato in locale e confrontato col `download_manifest.json`
di `legal_data/sources/france/downloaded/`.

| Slug | File | Size (B) | SHA-256 | Match manifest |
|---|---|---:|---|:-:|
| `fr-referentiel-mornet-2024` | `fr-referentiel-mornet-2024.pdf` | 898.965 | `2dd2e760bc057b38275a7a6de24a62c009f6d04dd79573c00ee052f4f6df72b4` | OK |
| `fr-bareme-capitalisation-gazette-palais-2022` | `fr-bareme-capitalisation-gazette-palais-2022.pdf` | 978.456 | `686a557b23fa9e76fcd30795e61fda1cc2396d230290b93398874203ebbef3ee` | OK |

Script di analisi read-only: `scripts/legal_data/analyze_fr_be_pdfs.py`
(non importa nulla, non scrive file). Esegue solo `pdfplumber` e calcolo
SHA-256.

Le altre due fonti FR già scaricate sono HTML / pagine landing e non
contengono valori indicizzabili:
`fr-bareme-capitalisation-gazette-palais-2025-page.html` (landing page
edizione 2025 — il PDF 2025 NON è scaricato, quindi indisponibile per
l'estrazione iter1) e `fr-nomenclature-dintilhac-2005.html` (nomenclatura
descrittiva, nessun valore numerico). Esistono inoltre 1 fonte
`manual_download_required` (Loi Badinter 1985 su Legifrance, solo testo
normativo, nessuna tabella).

---

## 2. Struttura PDF — Mornet 2024 (référentiel)

### 2.1. Profilo generale

- **Pagine**: 116
- **Layout dominante**: testo narrativo (è un manuale/trattato
  dottrinale del Conseiller à la Cour de cassation Benoît MORNET,
  ed. Septembre 2024); citazioni di giurisprudenza Civ. 2 + esempi
  numerici.
- **Pagine con tabella reale (>= 3 righe, >= 2 colonne) rilevate da
  `pdfplumber.find_tables()`**: solo 4 (p.71, p.88, p.94, p.108).

### 2.2. Sommario rilevante per il danno corporeo

Da PLAN p.3-5:

- **Chapitre 1** — gli attori (vittime, autori, tiers payeurs) — non
  contiene valori monetari indicizzabili.
- **Chapitre 2** — réparation du dommage corporel:
  - **I** Préjudices patrimoniaux (DSA, perte gains, frais, tierce
    personne) — narrativi con esempi numerici (non tabelle pure).
  - **II.A** Préjudices extra-patrimoniaux temporaires (DFT, SE,
    angoisse de mort imminente, esthétique temporaire) — pp. 65-68,
    narrativi con range citati nel testo.
  - **II.B** Préjudices extra-patrimoniaux permanents — DFP, esthétique
    permanent, agrément, sexuel, établissement — pp. 68-73 — **una
    tabella valori a p.71** (vedi 2.4).
- **Chapitre 4** — préjudice par ricochet (proches victime décédée
  ou survivante) — **una tabella valori a p.94** (vedi 2.4).
- **Chapitre 5** — accident du travail — esempi numerici di
  riparto (p.108), non tabelle di riferimento.

### 2.3. Conteggi keyword (case-insensitive)

| Keyword | Hits |
|---|---:|
| `déficit fonctionnel permanent` (+ `DFP`) | 38 (+4) |
| `tierce personne` | 62 |
| `souffrances endurées` | 14 |
| `préjudice esthétique` | 23 |
| `barème` | 22 |
| `Dintilhac` | 9 |
| `préjudice d'agrément` | 5 |

I valori monetari sono quasi sempre **inline nel testo** o in tabelle
"esempio di calcolo" (p.88, p.108), non in tabelle di riferimento. Il
référentiel Mornet **non è un barème tabulare** stile Tableau Indicatif
belga: è un manuale che propone fourchettes (range "min € à max €")
incorporate nel discorso.

### 2.4. Tabelle reali — contenuto

| Pagina | Tipo | Note |
|---|---|---|
| **p.71** | Tabella `[%DFP] × [classe d'âge] → € punto` | 21 righe (1-5%, 6-10%, …, fino a probabilmente 100%) × 9 classi d'età (0-10, 11-20, …, 81+). Valore = € per punto DFP. **Estraibile in CSV**. |
| **p.88** | Tabella esempio calcolo riparto CPAM/mutuelle | Esempio pedagogico, **non è una fonte di valori indicativi**. Skip. |
| **p.94** | Tabella `[lien de parenté] × [fourchette €]` per préjudice d'affection | 6 righe × 2 colonne. Valori "20.000 € à 30.000 €" ecc. **Estraibile** ma con parsing ad-hoc per separare min/max e gestire majoration percentuale. |
| **p.108** | Tabella esempio calcolo réparation accident du travail | Esempio pedagogico, skip. |

**Conclusione**: solo p.71 e p.94 sono fonti tabulari di
référence. Tutto il resto richiede transcrizione manuale del Studio
delle "fourchettes textuelles" embedded nel narrativo.

---

## 3. Struttura PDF — Gazette du Palais 2022 (barème de capitalisation)

### 3.1. Profilo generale

- **Pagine**: 20
- **Layout dominante**: tabulare (18/20 pagine contengono almeno una
  tabella >= 3 righe × >= 2 colonne).
- **Editore**: Gazette du Palais — barème pubblicato annualmente. Il
  PDF scaricato è l'**edizione 2022**; la pagina HTML 2025 è scaricata
  ma il PDF 2025 **non è in archivio**.

### 3.2. Sommario contenuti

- **p.1-2**: introduzione metodologica (testo).
- **p.3**: tabella di sintesi taux d'actualisation TME × inflation
  per profondità storica (3 colonne, ~6 righe).
- **p.4-5**: tabelle "Espérance de vie" (âge × homme/femme).
- **p.6-9**: tabelle preliminari di taux et tables de mortalité
  (descrittive).
- **p.10-20**: 18 **tabelle di capitalisation** — l'unità di calcolo:
  ogni pagina = una combinazione `(table de mortalité INSEEH/INSEEF,
  taux d'intérêt -1.00% / -0.75% / -0.50% / -0.25% / 0.00%)`. Ogni
  tabella ha:
  - 21 colonne: 1 colonne `Âge à la date d'attribution`, poi
    `viagère`, poi capitali parziali per `dernier arrérage à 69 ans`,
    `68 ans`, `67 ans`, …, `16 ans` (rentes temporaires).
  - ~30+ righe: età d'attribution da 0 a (probabile) 95 anni.

### 3.3. Conteggi keyword

| Keyword | Hits |
|---|---:|
| `barème` | 52 |
| `capitalisation` | 28 |
| `INSEE` | 25 |
| `table de mortalité` | 3 |
| `espérance de vie` | 1 |

### 3.4. Tabelle reali — contenuto

Le 18 tabelle p.3-20 hanno tutte la stessa struttura matriciale
`[Âge attribution] × [Âge dernier arrérage / viagère]`. Le testate
specificano:
- **table de mortalité**: INSEEH 2017-2019 (homme) o INSEEF 2017-2019
  (femme), con varianti `Sexe masculin` / `Sexe féminin` /
  `Hommes-femmes` (unisex).
- **taux d'intérêt**: da -1.00% a 0.00% in step di 0.25%.

Sample p.10 (struttura confermata):
```
Table de survie de référence : INSEEH 2017-2019 (Sexe masculin)
Taux d'intérêt = -1.00%   Barème de capitalisation 2022
Capital constitutif d'une rente payable à terme échu
Âge du bénéficiaire lors du dernier arrérage
Âge|viagère|69 ans|68 ans|...|16 ans
30  |66.602 |45.144|43.939|...|
31  |64.988 |43.727|42.534|...|
...
```

I numeri sono in formato francese **`66.602`** (punto = migliaia,
virgola = decimale assente perché coefficiente intero migliaia di
centesimi) — **attenzione**: nel parser sostituire `.` con vuoto e
gestire `,` come separatore decimale.

---

## 4. Schema CSV candidato — FR Mornet 2024

### 4.1. `fr-mornet-2024-dfp` (estraibile da p.71)

`row_type = "fr_dfp_per_pct_age_amount"` — punto DFP in funzione di
% invalidità e classe d'età.

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `country_code` | str | `FR` | costante |
| `jurisdiction_code` | str | `FR-NATIONAL` | costante |
| `dataset_version_label` | str | `MORNET-2024` | candidate |
| `row_type` | str | `fr_dfp_per_pct_age_amount` | costante per file |
| `disability_min` | int | `1` | % min DFP della classe |
| `disability_max` | int | `5` | % max DFP della classe |
| `age_min` | int | `0` | classe d'età min |
| `age_max` | int | `10` | classe d'età max |
| `point_value` | decimal | `2310.00` | € per punto |
| `currency` | str | `EUR` | costante |
| `notes` | str | `cf. Mornet 2024 p.71` | tracking di provenienza |

**Stima righe**: 20 classi % × 9 classi d'età = **180 righe**.

### 4.2. `fr-mornet-2024-affection` (estraibile da p.94)

`row_type = "fr_prejudice_affection_per_relation_amount"` — fourchette
preuvre d'affection per legame di parentela.

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `relation_code` | str | `spouse` | discriminante chiave |
| `relation_label_fr` | str | `Conjoint / concubin` | label umana |
| `condition` | str | `default` | per gestire majoration |
| `min_amount` | decimal | `20000.00` | min fourchette |
| `max_amount` | decimal | `30000.00` | max fourchette |
| `currency` | str | `EUR` | costante |
| `notes` | str | `cf. Mornet 2024 p.94` | provenance |

**Stima righe**: ~12 (con conditions: enfant mineur,
mineur déjà orphelin, majeur foyer, hors foyer; frères vs hors foyer;
grand-parent rel. fréquentes/peu fréquentes).

### 4.3. Restanti voci Mornet → **transcrizione manuale Studio**

I seguenti dati monetari sono nel narrativo e **non sono in tabelle
auto-estraibili**:
- DFT (Déficit fonctionnel temporaire) — pp. 65-66
- Souffrances endurées (échelle 1/7 à 7/7) — p.66 — fourchettes per
  scala
- Préjudice esthétique temporaire — p.68
- Préjudice esthétique permanent — p.71
- Préjudice d'agrément — p.71-73
- Préjudice sexuel — p.73
- Préjudice d'établissement — p.73
- Tierce personne (taux horaire / forfait jour) — p.59-65
- Indicidence professionnelle — p.55-58
- Frais d'aménagement logement / véhicule — p.59-65

**Pattern raccomandato**: il Studio fornisce un CSV manuale con
fourchette `(min, max, scale_step)` per ognuna di queste voci, e
l'engine FR le legge come `row_type` distinti
(`fr_souffrances_endurees_per_scale_amount`,
`fr_prejudice_esthetique_per_scale_amount`, ecc.).

---

## 5. Schema CSV candidato — FR Gazette du Palais 2022

### 5.1. `fr-gazette-2022-capitalisation-viagere`

`row_type = "fr_capitalisation_viagere_per_age_sex_rate_coefficient"`.

| Colonna | Tipo | Esempio | Note |
|---|---|---|---|
| `dataset_version_label` | str | `GAZETTE-PALAIS-2022` | candidate |
| `row_type` | str | `fr_capitalisation_viagere_per_age_sex_rate_coefficient` | costante |
| `mortality_table` | str | `INSEEH-2017-2019` / `INSEEF-2017-2019` / `INSEE-MIXTE-2017-2019` | discriminante |
| `sex` | str | `M` / `F` / `MIXED` | redondante con mortality_table ma utile per query |
| `interest_rate_pct` | decimal(4,2) | `-1.00` | passo 0.25 |
| `age_at_attribution` | int | `30` | da 0 a 95 |
| `coefficient` | decimal(8,3) | `66.602` | coefficiente moltiplicativo €/€ rente |
| `notes` | str | `cf. Gazette p.10` | provenance |
| `currency_factor_unit` | str | `EUR per EUR rente annuelle` | descrizione coefficient |

**Stima righe** (solo viagère): ~95 età × 3 tables × 5 tassi = **~1.425
righe**. Aggiungendo le rentes temporaires (16 colonne supplementari
per "dernier arrérage"), si arriva a ~22.800 righe → split in CSV
separato `fr-gazette-2022-capitalisation-temporaire` con
`row_type = "fr_capitalisation_temporaire_per_age_sex_rate_targetage_coefficient"`
e colonna aggiuntiva `target_age` (= ultimo arrérage).

### 5.2. `fr-gazette-2022-esperance-vie`

`row_type = "fr_esperance_vie_per_age_sex_years"`. Estraibile da
p.4-5 (tabelle 6 righe × 3 colonne `[Âge | Homme | Femme]`).

| Colonna | Tipo | Esempio |
|---|---|---|
| `age` | int | `30` |
| `sex` | str | `M` / `F` |
| `expected_years` | decimal(5,2) | `49.9` |

**Stima righe**: 2 tabelle (forse ~15-30 righe ciascuna).

---

## 6. Cosa è estraibile automaticamente vs. cosa richiede legal review

### 6.1. Estraibile automaticamente (parser candidato)

| Sorgente | Scope | Approccio |
|---|---|---|
| **Mornet p.71** | tabella DFP | `pdfplumber.find_tables()` → CSV; ~180 righe |
| **Mornet p.94** | tabella affection | `find_tables()` + post-process delle fourchette `"X € à Y €"` |
| **Gazette p.10-20** | 18 tabelle capitalisation | `find_tables()` per pagina + parsing testata per estrarre `(mortality_table, sex, interest_rate_pct)`; numeri francesi `66.602` da convertire |
| **Gazette p.4-5** | espérance vie | `find_tables()` |

### 6.2. Richiede transcrizione manuale Studio

| Voce | Motivo |
|---|---|
| Souffrances endurées 1/7 → 7/7 | Valori narrativi, fourchette per scala (no tabella) |
| Préjudice esthétique temporaire/permanent | Idem |
| Préjudice d'agrément, sexuel, établissement | Idem |
| Tierce personne (taux horaire) | Narrativo + dipende da forme assistance |
| Incidence professionnelle | Forte componente caso-per-caso |
| Frais aménagement logement/véhicule | Narrativo + casuistica |

### 6.3. Richiede legal review **prima** di approvazione (qualunque modalità)

Indipendentemente dalla modalità di estrazione, **tutte** le
`CompensationTableRow` candidate devono passare:

1. **Verifica coerenza con la fonte primaria** — rilettura paginata
   da parte del Studio (cross-check valore-per-valore su almeno il
   10% delle righe estratte automaticamente).
2. **Verifica giurisprudenziale** — i valori Mornet sono indicativi
   non vincolanti; il Studio deve confermare quali tabelle sono
   effettivamente seguite dalla giurisprudenza locale (Cour d'appel
   competente in caso di simulazione).
3. **Verifica di aggiornamento** — Mornet 2024 e Gazette 2022 sono
   le edizioni archiviate; se all'epoca dell'uso esistono edizioni
   successive (Mornet 2025, Gazette 2023/2024/2025), il dataset
   `MORNET-2024` rimane comunque utile come fallback storico.

Solo dopo questi 3 step lo Studio può creare un `LegalReview`
sulla `LegalSource` corrispondente e il calcolatore può puntare al
`CompensationDataset`.

---

## 7. Rischi e ostacoli di parsing

| Rischio | Probabilità | Mitigazione |
|---|---|---|
| Numeri francesi `66.602` interpretati come `66,602` | alta | normalizzare via `re.sub(r'\.(\d{3})', r'\1', s)` PRIMA del parsing |
| Header multi-linea (es. `Âge du\nbénéficiaire\nà la date\nd'attribution`) | alta | uso di `pdfplumber.extract_table(table_settings={"keep_blank_chars": True})` + regex di normalizzazione |
| Tabelle con celle vuote tra colonne (`'4/7'` con due spazi) | media | dropna + columns alignment |
| Mornet p.94 fourchette nel formato `"15.000 € à 25 000 €"` (mix di separatori) | alta | regex `r'([\d\.\s]+)\s*€\s*à\s*([\d\.\s]+)\s*€'` + normalize |
| Mornet — tabella esempio calcolo (p.88 / p.108) confusa con tabella di riferimento | media | whitelist esplicita di `(slug_pdf, page_number)` da estrarre |
| Edizioni successive (Mornet 2025, Gazette 2025) non archiviate | media | flag esplicito nel `dataset_version_label`; fallback a 2024/2022 |
| Loi Badinter 1985 (`manual_download_required` su Legifrance) | nota | testo normativo, no valori; non blocca l'estrazione di Mornet/Gazette |

---

## 8. Prossimi step consigliati (ordine di esecuzione)

1. **iter F-france-extraction-gazette-capitalisation** — la Gazette
   è la fonte più strutturata (18 tabelle pulite). Implementare
   parser dedicato `apps/legal_sources/management/commands/extract_fr_gazette_capitalisation.py`,
   output CSV `legal_data/extracted/france/fr-gazette-2022-capitalisation-viagere.csv`
   (+ `…-temporaire.csv`, + `…-esperance-vie.csv`). **Solo CSV +
   `ExtractionLog`**: nessun `CompensationDataset.APPROVED`, nessun
   `LegalReview`. Il Studio review.
2. **iter F-france-extraction-mornet-tables** — estrarre tabelle p.71
   (DFP) e p.94 (affection). Pattern simile, parser più piccolo.
3. **iter F-france-mornet-manual-fourchettes** — Studio fornisce
   manualmente CSV con le fourchette delle voci narrative
   (souffrances endurées, esthétique, agrément, …); l'app le carica
   come `CompensationTableRow` in stato `needs_review`.
4. **iter F-france-legal-review** — Studio crea `LegalReview` per
   ognuna delle 4 LegalSource FR (Mornet 2024, Gazette 2022, Loi
   Badinter, Nomenclature Dintilhac) con conferma valori spot.
5. **iter F-france-engine** — solo dopo `approved`: implementare
   `apps/calculators/engines/france.py` (registry, input schema,
   output schema, breakdown). Wizard FR in fase separata.

---

## 9. File creati e committabili

- `docs/legal_sources/FRANCE_EXTRACTION_PLANNING.md` (questo file)
- `scripts/legal_data/analyze_fr_be_pdfs.py` (script read-only di
  ispezione, condiviso FR + BE)

**File NON committabili** (gitignored ai sensi del repo policy):
- i PDF in `legal_data/sources/france/downloaded/`
- il `download_manifest.json`

**File NON modificati**:
- nessun calcolatore (nessun `apps/calculators/engines/france.py`)
- nessun wizard
- nessun template
- nessun seeder Italia/TUN
- nessun `apps/compensation/models.py`
- nessun `.env`
- nessuna fonte FR è stata `approved` (rimangono **needs_review**)

---

## 10. Disclaimer

> Questo documento descrive una **proposta tecnica di estrazione** per
> i due PDF FR archiviati. Nessuna delle tabelle proposte costituisce
> ancora una "fonte legalmente validata" ai sensi della regola
> fondamentale di prodotto: ogni `CompensationTableRow` derivata dovrà
> attraversare il flusso `draft → extracted → needs_review → reviewed
> → approved` con `LegalReview` esplicito del Studio prima di poter
> alimentare un calcolo pubblico.
