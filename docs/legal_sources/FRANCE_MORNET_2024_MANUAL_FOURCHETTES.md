# FR — Référentiel Mornet 2024 — Workflow di trascrizione manuale (fourchettes)

**Iter**: F-france-mornet-manual-fourchettes · iter1
**Data**: 2026-04-29
**Stato**: scaffold-only — **nessun importo è stato dedotto
automaticamente, nessun import DB, nessuna approvazione**.

> Documento operativo per lo Studio. Definisce **come** trascrivere
> manualmente le voci NARRATIVE del Référentiel Mornet 2024 (souffrances
> endurées, esthétique, agrément, sexuel, établissement, tierce
> personne, scolaire, perte gains futurs, incidence professionnelle,
> ecc.) in un CSV strutturato senza inventare dati legali. Si applica
> la regola fondamentale del prodotto: **meglio nessun calcolo che un
> calcolo basato su valori non validati**.

---

## 1. Perché questa fase esiste — perché non auto-estraiamo

Il *Référentiel Mornet* è un trattato dottrinale di 116 pagine, di cui
solo 2 sono tabelle di riferimento auto-estraibili in modo sicuro:

- **p.71** — DFP (Déficit Fonctionnel Permanent), griglia
  `[%invalidità] × [classe d'età]` → € per punto. **Già auto-estratto
  in iter precedente** (`fr-mornet-2024-dfp-per-age-disability.csv`,
  180 righe).
- **p.94** — Préjudice d'affection (en cas de décès), tabella per
  legame familiare. **Già auto-estratto in iter precedente**
  (`fr-mornet-2024-prejudice-affection-per-relation.csv`, 11 righe).

Tutto il resto del PDF è **testo narrativo dottrinale** (giurisprudenza
Civ. 2, esempi pedagogici, commenti) con **fourchettes embedded
inline** (es. "souffrances endurées 1/7 = jusqu'à 2.000 €"). Estrarre
automaticamente questi valori sarebbe rischioso per quattro ragioni:

1. **Falsi positivi** — un parser potrebbe confondere un esempio
   pedagogico (es. "3.740 € le point" usato per illustrare il calcolo
   DFP) con un valore di riferimento.
2. **Convenzioni numeriche locali** — il PDF usa il punto come
   separatore di migliaia in alcuni contesti, ma le fourchettes
   inline mescolano spazi (`50 000 €`) e punti (`50.000 €`); una
   regex rigida potrebbe sbagliare.
3. **Ambiguità unitarie** — "20 €/heure" (tierce personne), "30 €/jour"
   (DFT), "5.000 €" (forfait), "20.000-30.000 €" (range affection),
   "Majoration de 40-60%" (modificatore percentuale): parser unico
   non discriminabile.
4. **Responsabilità legale** — Mornet è **référentiel indicativo non
   vincolante**; ogni cifra trascritta deve passare il filtro umano
   di un professionista legale che dichiara: *"questa cifra è la
   fourchette indicata da Mornet 2024 per questa specifica voce e
   io la considero applicabile al nostro use-case"*.

Per queste ragioni la trascrizione **deve essere manuale**, **una
voce alla volta**, con **citazione testuale** (`source_quote_short`)
e **firma del reviewer** (`reviewer`).

---

## 2. File coinvolti (tutti gitignored, sotto `legal_data/sources/france/mornet_2024/`)

| File | Ruolo | Lo modifica? |
|---|---|---|
| `fr-mornet-2024-manual-fourchettes-template.csv` | CSV vuoto (solo header) — il **destinatario** della trascrizione | Studio (compila) |
| `fr-mornet-2024-manual-fourchettes-review_tasks.csv` | Catalogo delle 29 voci da trascrivere, con `source_pages` e `instructions` per ognuna | Studio (aggiorna stato) |
| `manual_fourchettes_seed_summary.json` | Audit del seed: hash PDF, timestamp, conteggi | nessuno (è generato) |

I committabili (sotto `scripts/legal_data/` e `docs/legal_sources/`):

| File | Ruolo |
|---|---|
| `scripts/legal_data/seed_france_mornet_manual_fourchettes.py` | Seed-only: ricrea template + review_tasks (idempotente, NON sovrascrive il lavoro dello Studio se il template è già stato compilato — vedi §6) |
| `scripts/legal_data/qa_france_mornet_manual_fourchettes.py` | QA validator del template compilato dallo Studio (read-only) |
| `docs/legal_sources/FRANCE_MORNET_2024_MANUAL_FOURCHETTES.md` | Questo documento |

---

## 3. Schema CSV `fr-mornet-2024-manual-fourchettes-template.csv`

### 3.1. Colonne

| Colonna | Obbligatoria | Esempio | Note |
|---|---|---|---|
| `row_type` | sì | `fr_souffrances_endurees_per_scale_amount` | snake_case stabile. Stesso `row_type` per tutte le righe della stessa voce (es. tutte le 8 righe di SE). |
| `head_of_loss_code` | sì | `fr_souffrances_endurees` | identifica la voce Dintilhac. Vedi `review_tasks.csv` per la lista canonica. |
| `head_of_loss_label_fr` | sì | `Souffrances endurées` | label per UI/PDF. |
| `severity_code` | se applicabile | `1_7`, `2_7`, …, `7_7`, `exceptional`, `default` | per voci con scala (SE, esthétique). `default` per voci senza scala. |
| `severity_label_fr` | se applicabile | `très léger`, `léger`, … | label umana della gravità. |
| `victim_age_min` | se applicabile | `0` | per voci con dipendenza età (es. établissement: < 30 ans). |
| `victim_age_max` | se applicabile | `120` | `120` = "et plus". |
| `amount_min` | se transcribed | `2000` | min della fourchette. **Vuoto se "jusqu'à X"** (open lower bound). |
| `amount_mid` | se transcribed | `3000` | media `(min+max)/2` aritmetica calcolata DALLO STUDIO. **Vuoto se min vuoto**. |
| `amount_max` | se transcribed | `4000` | max della fourchette. |
| `unit` | sì | `EUR`, `EUR_per_hour`, `EUR_per_day`, `EUR_per_year`, `EUR_per_point`, `percent` | unità dell'importo. |
| `currency` | se transcribed | `EUR` | costante per voci Mornet. |
| `source_page` | se transcribed | `68` | pagina PDF della fonte. |
| `source_quote_short` | se transcribed | `"1/7 très léger jusqu'à 2.000 €"` | citazione testuale (max ~150 char) della frase Mornet su cui si basa il valore. |
| `transcription_status` | sì | `pending`, `transcribed`, `human_checked`, `rejected`, `needs_clarification` | stato della riga (vedi §4). |
| `reviewer_notes` | no | "Confermato con Studio Bianchi 2026-05-03" | annotazioni libere reviewer. |
| `source_note` | sì se transcribed | (vedi §3.2) | metadata di audit. |

### 3.2. Formato `source_note` (obbligatorio per righe transcribed/human_checked)

```
extraction=manual_human;
legal_review_required=true;
no_human_legal_approval=true;
pdf_sha256=2dd2e760bc057b38275a7a6de24a62c009f6d04dd79573c00ee052f4f6df72b4;
pdf_slug=fr-referentiel-mornet-2024;
extractor_script=manual;
iter=F-france-mornet-manual-fourchettes;
reviewer=<initials>;
review_date=YYYY-MM-DD
```

**Importante**: anche dopo `transcription_status=human_checked` la
riga rimane `legal_review_required=true` e `no_human_legal_approval=true`
fintanto che la `LegalSource` non è promossa ad `approved`. Sono due
fasi distinte: trascrizione QA (questa fase) → review legale formale
con `LegalReview` (fase successiva).

---

## 4. Stati di trascrizione

| Status | Significato | Permette importi vuoti? |
|---|---|---|
| `pending` | Voce non ancora trascritta. È lo stato iniziale di tutte le 29 righe in `review_tasks.csv`. | sì |
| `transcribed` | Lo Studio ha trascritto la fourchette dal PDF. Necessita ancora di un secondo paio d'occhi. | no — `amount_max` deve essere definito; tutti gli altri vincoli QA si applicano |
| `human_checked` | La trascrizione è stata verificata da un secondo reviewer dello Studio. Pronta per il legal-review formale (`LegalReview`). | no |
| `rejected` | Lo Studio ha deciso che Mornet **non fornisce una fourchette stabile** per questa voce (es. `établissement` è "case-by-case" per definizione). La riga rimane nel CSV con `amount_*` vuoti come traccia della decisione. | sì |
| `needs_clarification` | La fourchette nel PDF è ambigua (es. mescolanza di forfait e %); blocco in attesa di consultazione esterna. | sì |

Il calcolatore FR **userà solo le righe** con `transcription_status =
human_checked` E `LegalSource = approved`. Le righe `transcribed` non
sono ancora utilizzabili.

---

## 5. Come compilare — workflow per lo Studio

### 5.1. Preparazione

1. Aprire `fr-mornet-2024-manual-fourchettes-review_tasks.csv` per
   vedere la lista delle 29 voci da trascrivere, con `source_pages`
   e `instructions` per ognuna.
2. Aprire il PDF `fr-referentiel-mornet-2024.pdf` (in
   `legal_data/sources/france/downloaded/`).
3. Aprire `fr-mornet-2024-manual-fourchettes-template.csv` come
   foglio (Excel/LibreOffice/numeric editor).

### 5.2. Per ogni `head_of_loss_code` da trascrivere

1. Leggere le pagine indicate in `source_pages` del review_task.
2. Identificare la fourchette concreta (se Mornet ne fornisce una).
3. **Se Mornet fornisce una fourchette stabile** (es. SE p.68,
   esthétique perm p.72):
   - Aggiungere una o più righe nel template (una per livello di
     gravità: 8 righe per SE, 8 per esthétique, …).
   - Compilare tutti i campi obbligatori con `transcription_status =
     transcribed`.
   - `source_quote_short` deve essere una citazione testuale precisa
     (es. `"1/7 très léger jusqu'à 2.000 €"`).
   - Se la fourchette è del tipo "jusqu'à X €", lasciare `amount_min`
     **vuoto** (open lower bound) e impostare `amount_max = X`. In
     questo caso `amount_mid` può essere lasciato vuoto.
   - Se la fourchette è del tipo "X € à Y €", impostare
     `amount_min = X`, `amount_max = Y`, `amount_mid = (X+Y)/2`
     calcolato a mano.
   - Se la fourchette è del tipo "X € et plus" (no upper bound),
     lasciare `amount_max` **vuoto** e impostare `amount_min = X`.
4. **Se Mornet NON fornisce una fourchette stabile** (è il caso
   della maggioranza delle voci in `case_by_case`):
   - Impostare la riga `transcription_status = rejected` con
     `reviewer_notes` che spiega perché (es. *"Mornet pp.59-65
     discute solo gli importi reali da devis; nessuna fourchette
     dottrinale stabile"*).
   - Lasciare `amount_*` vuoti.
   - Aggiornare la stessa riga in `review_tasks.csv` settando
     `transcription_status = rejected` per coerenza.
5. **Se la fourchette è ambigua o richiede consultazione**:
   - Impostare `transcription_status = needs_clarification`.
   - Spiegare in `reviewer_notes` la natura del dubbio.
   - Aggiornare il review_task corrispondente.
6. Eseguire la QA dopo ogni voce trascritta:
   ```
   .venv/Scripts/python.exe scripts/legal_data/qa_france_mornet_manual_fourchettes.py
   ```
   Tutte le righe `transcribed/human_checked` devono passare i 7
   check QA (vedi §7).

### 5.3. Secondo paio d'occhi

Una volta che tutte le voci pianificate sono `transcribed`:
1. Un secondo reviewer dello Studio rilegge ogni riga `transcribed`
   contro il PDF.
2. Cambia lo stato a `human_checked` se conferma.
3. Aggiorna `reviewer_notes` con iniziali e data.

Solo dopo questo passaggio la `LegalSource` può essere proposta per
approvazione formale (passo successivo, fuori scope di questo iter).

---

## 6. Idempotenza del seeder

`scripts/legal_data/seed_france_mornet_manual_fourchettes.py`
**sovrascrive** sempre il template (essendo vuoto) e i review_tasks.
**Non sovrascrive il lavoro dello Studio** se questo è stato salvato
in un file con nome diverso (es.
`fr-mornet-2024-manual-fourchettes.csv` senza `-template`).

**Best practice**: lo Studio compila il template direttamente, ma al
primo salvataggio rinomina il file in
`fr-mornet-2024-manual-fourchettes.csv` (rimuovendo `-template`). Il
seeder può essere rilanciato in futuro per rigenerare lo scaffold
senza toccare il file di lavoro.

---

## 7. QA — regole applicate da `qa_france_mornet_manual_fourchettes.py`

Lo script accetta `--csv <path>` per validare un CSV diverso dal
template (utile per il file di lavoro `fr-mornet-2024-manual-fourchettes.csv`).

| # | Check | Quando si applica |
|---|---|---|
| 1 | Header esatto (17 colonne in ordine canonico) | sempre |
| 2 | `transcription_status` ∈ {`pending`, `transcribed`, `human_checked`, `rejected`, `needs_clarification`} | sempre |
| 3a | `amount_max` definito | solo righe `transcribed` / `human_checked` |
| 3b | `amount_min ≤ amount_mid ≤ amount_max` quando tutti definiti | quando i 3 campi sono tutti compilati |
| 3c | `currency = EUR` quando ci sono importi | quando almeno un `amount_*` è compilato |
| 3d | `source_page` non vuoto | solo righe `transcribed` / `human_checked` |
| 3e | `source_quote_short` ≥ 5 caratteri | solo righe `transcribed` / `human_checked` |
| 3f | `source_note` contiene `legal_review_required=true` e `no_human_legal_approval=true` | solo righe `transcribed` / `human_checked` |
| 4 | Nessun valore negativo in `amount_*` | sempre |
| 5 | Righe `pending` possono avere `amount_*` vuoti | sempre (non genera failure) |

Exit code: `0` = OK, `1` = anomalie. Le anomalie **non cancellano
nulla**: lo Studio le risolve modificando il CSV.

---

## 8. Cosa NON deve essere fatto prima dell'`approved`

Anche dopo che il CSV è interamente `human_checked`:

1. **Non importare le righe nel DB**: questo iter non crea
   `CompensationDataset` né `CompensationTableRow`. Esisterà uno
   step di import dedicato (`F-france-mornet-import-manual`) **dopo**
   che lo Studio avrà:
   - validato tutto il CSV (`human_checked` su ogni riga "vera"),
   - creato un `LegalReview` esplicito sulla `LegalSource`
     `fr-referentiel-mornet-2024` con conferma valori spot,
   - promosso la `LegalSource` da `needs_review` a `approved`.
2. **Non popolare il calcolatore FR** (`apps/calculators/engines/france.py`)
   con valori derivati da queste fourchettes finché il dataset non è
   `approved`.
3. **Non mostrare valori derivati nel public wizard** finché tutti
   i passi precedenti non sono completati.
4. **Non assumere che Mornet sia vincolante**: ogni report cliente
   che usa questi valori deve dichiarare esplicitamente
   *"référentiel indicatif Mornet 2024 — la giurisprudenza concreta
   può discostarsi"*.

---

## 9. Voci catalogate nel `review_tasks.csv` (29 totali)

Come riferimento rapido (la fonte canonica è `review_tasks.csv`):

| `head_of_loss_code` | `expected_structure` | `source_pages` |
|---|---|---:|
| `fr_depenses_sante_actuelles` | case_by_case | 42-43 |
| `fr_perte_gains_professionnels_actuels` | formula_based | 43-45 |
| `fr_prejudice_scolaire_universitaire_formation` | case_by_case | 45-46 |
| `fr_frais_divers` | case_by_case | 46-48 |
| `fr_depenses_sante_futures` | case_by_case | 50-51 |
| `fr_perte_gains_professionnels_futurs` | formula_based | 51-55 |
| `fr_incidence_professionnelle` | case_by_case | 55-58 |
| `fr_frais_logement_adapte` | case_by_case | 59-65 |
| `fr_frais_vehicule_adapte` | case_by_case | 59-65 |
| `fr_assistance_tierce_personne` | hourly_rate | 59-65 |
| `fr_deficit_fonctionnel_temporaire` | daily_or_monthly_forfait | 65-66 |
| `fr_souffrances_endurees` | scale_1_to_7 | 66-68 |
| `fr_angoisse_mort_imminente` | case_by_case | 67-68 |
| `fr_esthetique_temporaire` | scale_1_to_7 | 68 |
| `fr_esthetique_permanent` | scale_1_to_7 | 71-72 |
| `fr_prejudice_agrement` | case_by_case | 71-73 |
| `fr_prejudice_sexuel` | case_by_case | 73-74 |
| `fr_prejudice_etablissement` | case_by_case | 73-75 |
| `fr_prejudices_permanents_exceptionnels` | case_by_case | 75-76 |
| `fr_prejudices_evolutifs_hors_consolidation` | case_by_case | 75-76 |
| `fr_prejudice_impreparation_medicale` | case_by_case | 76-77 |
| `fr_perte_revenus_proches_victime_vivante` | formula_based | 89 |
| `fr_frais_divers_proches_victime_vivante` | case_by_case | 89 |
| `fr_prejudice_affection_victime_vivante` | case_by_case | 90 |
| `fr_prejudices_extra_patrimoniaux_exceptionnels_proches` | case_by_case | 90 |
| `fr_prejudice_accompagnement_deces` | case_by_case | 93-95 |
| `fr_frais_obseques` | case_by_case | 95 |
| `fr_frais_divers_deces` | case_by_case | 95 |
| `fr_perte_revenus_proches_deces` | formula_based | 96-100 |

> Voci **escluse** dal review_tasks (perché già auto-estratte in iter
> precedenti):
> - `fr_dfp_per_age_disability` — DFP grid, p.71 (180 righe in
>   `fr-mornet-2024-dfp-per-age-disability.csv`).
> - `fr_prejudice_affection_per_relation_deces` — décès, p.94 (11 righe
>   in `fr-mornet-2024-prejudice-affection-per-relation.csv`).

---

## 10. Disclaimer

> Questo documento descrive il **workflow di trascrizione manuale**
> per le voci narrative del Référentiel Mornet 2024. Nessun importo è
> stato dedotto automaticamente. Il template CSV
> (`fr-mornet-2024-manual-fourchettes-template.csv`) è intenzionalmente
> vuoto: solo lo Studio Legale Badrane può popolarlo, e ogni riga
> popolata richiede `LegalReview` formale prima di alimentare un
> calcolo pubblico.
>
> Il *Référentiel Mornet* è una **proposta dottrinale** del Conseiller
> Benoît Mornet, NON una norma vincolante. Anche dopo l'`approved`,
> ogni report al cliente che usa questi valori deve dichiarare
> esplicitamente che la simulazione si basa sul **référentiel
> indicatif** Mornet 2024 e che la décision finale dipende dal
> magistrato del caso e dalla Cour d'appel competente.
>
> Si applica integralmente la regola fondamentale del prodotto
> (CLAUDE.md): **meglio nessun calcolo che un calcolo basato su
> valori non validati da un revisore legale qualificato**.
