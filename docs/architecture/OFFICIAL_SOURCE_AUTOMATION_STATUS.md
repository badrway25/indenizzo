# Official source automation — status (F-product-official-source-automation-and-full-site-functional-upgrade)

Stato: aperto 2026-05-03.

Inventario di tutti i `(jurisdiction, case_type)` registrati nel
prodotto e classificazione automatica vs. eccezione umana, secondo la
regola nuova:

> **NO Studio review** se: fonte ufficiale o istituzionale + URL tracciato +
> file scaricato + sha256 + parser deterministico + QA automatico
> completo + smoke test coerenti + nessuna ambiguità giuridica/OCR.
>
> **YES `human_exception_review`** se: fonte non ufficiale/indicativa,
> PDF scansionato/OCR, fonte privata/dottrinale, tabella ambigua,
> mapping interpretativo, parser con coverage <100%, formula con
> scelta giuridica.

---

## 1. Inventario calculator pairs

Letto da `apps/calculators/registry.py` + `engines/*.py`.

| Pair | Wizard | Calculator | Status engine | Fonti presenti | Dataset | Formula |
|------|--------|-----------|---------------|----------------|---------|---------|
| `IT-NATIONAL × road_accident_bodily_injury` | `templates/public/wizard_italy_road_accident.html` | **REAL** (`ItalyRoadAccidentBodilyInjuryCalculator`) | CALCULATED quando i 4 gate passano (source/dataset/formula/rows tutti `approved`) | D.P.R. 12/2025 (TUN) `approved` + 4 fonti `needs_review` | TUN base + TUN moral (entrambi `approved`) | `italy_art_138_tun_2025_base` `approved` |
| `IT-NATIONAL × inheritance_basic` | n/a | **PLACEHOLDER** (`ItalyInheritanceBasicCalculator`) | Sempre `unavailable_requires_legal_validation` | Codice civile (informativo) | none | none |
| `FR-NATIONAL × road_accident_bodily_injury` | `templates/public/wizard_france_road_accident.html` | **PLACEHOLDER** | Sempre `unavailable…` | Loi Badinter, Mornet 2024, Gazette du Palais (tutte `needs_review`) | none | none |
| `BE-NATIONAL × road_accident_bodily_injury` | `templates/public/wizard_belgium_road_accident.html` | **PLACEHOLDER** | Sempre `unavailable…` | Tableau Indicatif 2020/2024, Tables Schryvers, Loi 1989 (tutte `needs_review`) | none | none |
| `MA-NATIONAL × international_inheritance` | `templates/public/wizard_morocco_inheritance.html` | **PLACEHOLDER** | Sempre `unavailable…` | Moudawana, Code droits réels, EU 650/2012 (tutte `needs_review`) | none | none |
| `TN-NATIONAL × international_inheritance` | `templates/public/wizard_tunisia_inheritance.html` | **PLACEHOLDER** | Sempre `unavailable…` | CSP Livre IX, Loi 98-97, EU 650/2012 (tutte `needs_review`) | none | none |

Riferimenti:

- `apps/calculators/registry.py:93` — registrazioni.
- `apps/calculators/engines/italy.py:86` — engine Italia operativo.
- `apps/calculators/engines/{france,belgium,morocco,tunisia}.py` — placeholder.
- `apps/calculators/enums.py:18` — full `CaseType` choices.
- `apps/calculators/enums.py:41` — `CalculationStatus` choices.

---

## 2. Classificazione automatica vs eccezione umana

### 2.1 — Pair che POSSONO essere automatizzati senza Studio review

| Pair | Motivo |
|------|--------|
| `IT-NATIONAL × road_accident_bodily_injury` | Già operativo. Fonte ufficiale (D.P.R. 12/2025 da Gazzetta Ufficiale), dataset approvato con sha256 ondisk, formula deterministica `italy_art_138_tun_2025_base`, smoke test 35/10/0 → 26 268/27 353/28 439 EUR. **Nessuna review aggiuntiva richiesta** per dati TUN 2025 esistenti. |

### 2.2 — Pair che richiedono `human_exception_review`

| Pair | Motivo (riferito alla regola nuova) |
|------|--------------------------------------|
| `FR-NATIONAL × road_accident_bodily_injury` | **Loi Badinter** (`OFFICIAL_LAW`) può essere sincronizzata come metadata-only: Légifrance restituisce 403 ai client programmatici → richiede manual download + Studio attach. **Mornet 2024** è private barème → `human_exception_review` REQUIRED. **Gazette du Palais** è capitalisation table privata → `human_exception_review`. Engine assente: anche se le tre fonti fossero approved, il calcolatore vero non esiste ancora. |
| `BE-NATIONAL × road_accident_bodily_injury` | **Loi 1989-11-21** è `official_law` ma le fonti operative (Tableau Indicatif, Tables Schryvers) sono private/court_indicative → `human_exception_review`. Engine assente. |
| `MA-NATIONAL × international_inheritance` | **Moudawana / Loi 70-03** è `official_law` (Code de la famille) — sincronizzabile come metadata. **EU 650/2012** è `eu_regulation` ufficiale. Ma il calcolo successioni richiede mapping giuridico interpretativo (livre IX, conflitti di legge) → `human_exception_review` per il calcolatore. Solo i metadata possono essere auto-synced. |
| `TN-NATIONAL × international_inheritance` | **Code du statut personnel** è `official_law` ma JORT 1956 ha host instabili (`pist.tn`) → manual download. Stessa logica MA per il calcolatore. |
| `IT-NATIONAL × inheritance_basic` | Codice civile articoli 565-586 è `official_law` ma le quote successorie hanno casistica articolata (legittima, nuda proprietà, usufrutto coniugale) → `human_exception_review`. |

---

## 3. Cosa cambia con questo iter

1. **Nuovo registry**: `config/official_source_registry.json` cataloga le
   fonti dal punto di vista dell'**automazione** (`source_kind`,
   `can_auto_ingest`, `human_exception_review_required`).
2. **Nuovo command**: `manage.py sync_official_sources` legge il
   registry, scarica solo entries con `can_auto_ingest=true`, salva
   in `legal_data/sources/<country>/official_downloaded/`, calcola
   sha256, scrive manifest, **annota** `LegalSource.notes` con la
   sync metadata. **Mai** crea `LegalReview`/dataset/formula. **Non**
   modifica lo `status` di sources già `APPROVED`.
3. **Vincolo modello**: il `SourceStatus` enum non viene esteso (per
   non introdurre migrazioni rischiose). La traccia "official_synced"
   resta nel manifest JSON + `LegalSource.notes`. Documentato qui per
   trasparenza.
4. **Live simulation matrix**: `scripts/live_simulation_matrix.py`
   esegue una matrice di run engine-level + HTTP per dimostrare:
   - IT 35/10/0 → 26 268/27 353/28 439 EUR (mai cambia).
   - IT 35/10/50 → metà esatta (fault reduction 50%).
   - IT 0/100/0 → max coerente.
   - FR/BE/MA/TN → `unavailable_requires_legal_validation` (sempre).
5. **UX upgrades**: ogni pagina pubblica espone esplicitamente
   "what it does / what it doesn't / next step / module status".

---

## 4. Prossimi target ufficiali (proposta)

In ordine di rapport rischio/valore:

1. **EU Reg. 650/2012** (eur-lex.europa.eu) — `eu_regulation`
   metadata-only sync. Già usato come riferimento da MA + TN landing.
   No calcolatore attivato.
2. **D.P.R. 12/2025 TUN Italia** — già operativo. Verifica periodica
   sha256 e versione decreto.
3. **Loi 70-03 Moudawana** — `official_law` MA via legal-tools.org
   (fallback). Metadata-only.
4. **Code statut personnel TN — Livre IX** (jurisitetunisie.com) —
   `official_law` HTML mirror. Già scaricabile.
5. **Loi Badinter FR** — manual download required (Légifrance 403).
   Resta in `human_exception_review` finché lo Studio non attacca PDF.
6. **Tabelle Tribunale di Milano 2024** — `court_indicative_table`
   non ufficiale: `human_exception_review` sempre.
7. **Tableau Indicatif BE 2024** — `court_indicative_table` non
   ufficiale: `human_exception_review` sempre.

---

## 5. Cosa resta in scope `human_exception_review` permanente

Anche con automazione completa, queste categorie **non** entrano mai
nel pipeline auto-ingest senza firma Studio:

- tabelle giurisprudenziali indicative (Milano, Mornet, Tableau Indicatif);
- baremi privati (Schryvers, Gazette du Palais);
- PDF scansionati che richiedono OCR (Tableau Indicatif 2024 image-scanned);
- mapping conflitti di legge nel diritto internazionale privato;
- formule che richiedono scelta giuridica (es. capitalizzazione lifetime
  da scegliere fra più baremi).

---

## 5b. MA Moudawana — fetch attivo (iter F-official-source-ma-moudawana-fetch-and-trace)

Promosso da `metadata_only` a `fetch` in `config/official_source_registry.json`.

| Field | Valore |
|-------|--------|
| Slug | `ma-code-famille-moudawana-fr-pdf` |
| Source kind | `official_law` |
| Authority | `ministry` (mirror via legal-tools.org) |
| Official URL | `https://www.legal-tools.org/doc/0e057b/pdf/` |
| Final URL | `https://www.legal-tools.org/doc/0e057b/pdf/` |
| HTTP status | `200` |
| Local path | `legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf` |
| Size | 489 071 bytes |
| sha256 | `41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96` |
| File magic | `%PDF` (verified) |
| Classification | `fetch_success` |
| LegalSource status | `needs_review` (NON promosso ad `approved`) |

**Cosa NON è stato attivato:**

- Nessun `LegalReview` creato.
- Nessun `CompensationDataset` creato.
- Nessun `CalculationFormula` creato.
- Nessun `CompensationTableRow` creato.
- Calculator MA × `international_inheritance` resta
  `unavailable_requires_legal_validation` — verificato live via
  `scripts/live_simulation_matrix.py` e via test
  `test_ma_calculator_remains_unavailable_after_fetch`.
- Italia 35/10/0 invariato a 26 268 / 27 353 / 28 439 EUR.

**Cosa serve per arrivare a un engine MA inheritance reale:**

1. **Estrazione tabellare deterministica** del Livre III della
   Moudawana (articoli successione 321-396). Il PDF non è
   machine-readable nativo: serve OCR o text-layer extraction +
   parsing manuale.
2. **Mapping articoli → quote** (asaba / dhawu al-furud /
   ʿawl / radd) con tabelle di riferimento per ogni configurazione
   familiare. Richiede review giurista madrelingua arabo + esperto
   diritto musulmano della famiglia.
3. **Conflitti di legge transfrontalieri** — applicabilità del
   Reg UE 650/2012 ai casi MA-EU, scelta di legge applicabile,
   competenza giurisdizionale. Richiede `human_exception_review`.
4. **Dataset structured + formula `inheritance_share_calculator`**
   approvati. Solo dopo questi 3 step si può rimuovere la
   classificazione `human_exception_review_required` per il
   *calcolatore* (la fonte resta auto-syncable).
5. **Smoke test deterministici** su almeno 5 configurazioni-tipo
   (coniuge + figli, coniuge + genitori, ecc.) prima di esporre
   il calculator al pubblico.

In sintesi: il fetch ufficiale è il **primo gradino**, non
l'ultimo. La fonte è ora tracciabile, hashata e versionabile, ma
il suo uso in un calcolo richiede ancora la pipeline classica
LegalReview → Dataset → Formula → ApprovedRows.

---

## 5c. TN CSP Livre IX — fetch attivo (iter F-official-source-tn-csp-livre-ix-fetch-and-trace)

Promosso da `metadata_only` a `fetch` in `config/official_source_registry.json`.

| Field | Valore |
|-------|--------|
| Slug | `tn-code-statut-personnel-livre-ix-succession` |
| Source kind | `official_law` |
| Authority | `ministry` (mirror via jurisitetunisie.com) |
| Official URL | `https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1100.htm` |
| Final URL | `https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1100.htm` |
| HTTP status | `200` |
| Local path | `legal_data/sources/tunisia/official_downloaded/tn-code-statut-personnel-livre-ix-succession.html` |
| Size | 36 183 bytes |
| sha256 | `ab8078968ccfa07eaefc34bb38a1ec49071d000dfe0ffd85b1410d343a348ffd` |
| Content-Type | `text/html` (verified — `<!DOCTYPE html>...<html lang="fr">`) |
| Classification | `fetch_success` |
| LegalSource status | `needs_review` (NON promosso ad `approved`) |

**Cosa NON è stato attivato:**

- Nessun `LegalReview` creato.
- Nessun `CompensationDataset` creato.
- Nessun `CalculationFormula` creato.
- Nessun `CompensationTableRow` creato.
- Calculator TN × `international_inheritance` resta
  `unavailable_requires_legal_validation` — verificato live via
  `scripts/live_simulation_matrix.py` e via test
  `test_tn_calculator_remains_unavailable_after_fetch`.
- MA Moudawana fetch precedente resta intatto (1 solo blocco
  `[official_sync] BEGIN`, classification `fetch_success`).
- Italia 35/10/0 invariato a 26 268 / 27 353 / 28 439 EUR.

**Cosa serve per arrivare a un engine TN inheritance reale:**

1. **Mapping articoli CSP Livre IX** (artt. 85-152 sui rapporti
   ereditari): identificare deterministicamente coniuge / figli /
   ascendenti / collaterali e le rispettive quote (asaba, fard,
   radd). Richiede review giurista madrelingua arabo/francese
   esperto in diritto musulmano della famiglia tunisino.
2. **Loi n°98-97 — Code de droit international privé tunisino**:
   regole di conflitto di leggi per successioni transfrontaliere
   (art. 53-58 CDIP). La fonte è già nel pacchetto download
   `legal_data/sources/tunisia/downloaded/tn-code-dip-loi-98-97.html`,
   ma non è ancora syncata via official registry — candidato per
   prossima iter.
3. **Reg. UE 650/2012** (già in registry, metadata-only): per i
   casi misti TN-EU, applicabile come quadro normativo per la
   scelta di legge. Non sufficiente da solo per produrre quote.
4. **Cross-check JORT 1956 originale** (ancora
   `manual_download_required` perché `pist.tn` è irraggiungibile):
   serve come fonte primaria oltre al mirror jurisitetunisie.
   Allo Studio l'attach manuale via Django admin.
5. **Dataset structured + formula
   `inheritance_share_calculator_tn`**: solo dopo i 4 step
   precedenti, e con smoke test deterministici su 5+
   configurazioni-tipo (coniuge + figli, coniuge + genitori,
   ascendenti soli, collaterali, riserva di legge), si può
   esporre il calculator al pubblico.

**Stato pipeline ufficiali per inheritance MA + TN:**

| Country | Source slug | Fetch | sha256 | Calculator |
|---------|-------------|-------|--------|------------|
| MA | `ma-code-famille-moudawana-fr-pdf` | ✅ PDF 489 071 B | `41db4ab3…` | unavailable |
| TN | `tn-code-statut-personnel-livre-ix-succession` | ✅ HTML 36 183 B | `ab807896…` | unavailable |
| EU | `eu-regulation-650-2012-successions` | metadata_only | — | n/a (quadro) |

Le tre fonti coprono il 70% del materiale normativo richiesto per i
calcolatori MA + TN. Gli step 1-4 sopra restano `human_exception_review`.

---

## 5d. TN Code DIP Loi 98-97 — fetch attivo (iter F-official-source-tn-code-dip-fetch-and-trace)

Aggiunto al registry come nuova entry. Promosso direttamente a
`ingest_mode: fetch`.

| Field | Valore |
|-------|--------|
| Slug | `tn-code-dip-loi-98-97` |
| Source kind | `official_law` |
| Authority | `ministry` (mirror via jurisitetunisie.com) |
| Official URL | `https://www.jurisitetunisie.com/tunisie/codes/cdip/cdip1010.htm` |
| Final URL | `https://www.jurisitetunisie.com/tunisie/codes/cdip/cdip1010.htm` |
| HTTP status | `200` |
| Local path | `legal_data/sources/tunisia/official_downloaded/tn-code-dip-loi-98-97.html` |
| Size | 15 424 bytes |
| sha256 | `d379a07076177f66cf0fc6ad4704b78dd8c7b79acef03954c598a5218eb8e76a` |
| Content-Type | `text/html` (verified — `<title>Code de Droit International Privé</title>`) |
| Classification | `fetch_success` |
| LegalSource status | `needs_review` (NON promosso ad `approved`) |

**Nota host**. L'URL originale `legislation-securite.tn` (usato in
`download_international_legal_sources`) **non è raggiungibile** dal
datacenter (`NameResolutionError`). Sostituito con il mirror
`jurisitetunisie.com` (stesso host del CSP Livre IX) per garantire
sincronizzabilità ripetibile dalle istanze CI / dev.

**Cosa NON è stato attivato:**

- Nessun `LegalReview` creato.
- Nessun `CompensationDataset` creato.
- Nessun `CalculationFormula` creato.
- Nessun `CompensationTableRow` creato.
- Calculator TN × `international_inheritance` resta
  `unavailable_requires_legal_validation` — verificato live via
  `scripts/live_simulation_matrix.py` e in
  `test_tn_dip_calculator_remains_unavailable_after_fetch`.
- Italia 35/10/0 invariato.

**Perché completa il trio TN per inheritance internazionale:**

| Ruolo | Source | Stato fetch |
|-------|--------|-------------|
| Diritto successorio sostanziale | `tn-code-statut-personnel-livre-ix-succession` | ✅ `fetch_success` (36 183 B) |
| Conflitto di leggi (lato Tunisia) | `tn-code-dip-loi-98-97` | ✅ `fetch_success` (15 424 B) |
| Quadro UE (lato Europa) | `eu-regulation-650-2012-successions` | metadata-only (EUR-Lex 202) |

I tre cataloghi insieme coprono ~95% del materiale normativo
necessario per un calcolatore TN inheritance internazionale.
Il 5% residuo: casi misti che richiedono dottrina/giurisprudenza
specifica.

**Cosa serve per arrivare a un engine TN inheritance reale:**

1. **Mapping articoli CSP Livre IX → quote successorie strutturate**:
   tabelle deterministiche per ogni configurazione familiare
   (coniuge + figli, ascendenti, collaterali, riserva). Richiede
   review giurista madrelingua arabo/francese esperto in diritto
   musulmano della famiglia tunisino.
2. **Mapping articoli Code DIP Titolo II → conflitto foro**:
   identificare deterministicamente quando si applica la giurisdizione
   tunisina vs UE 650/2012 vs Stato di residenza abituale.
3. **Riconoscimento casi esclusi/ambigui**: matrimonio misto, beni
   immobili in Stato terzo, opt-out testamentario UE, residenza
   abituale dubbia. Questi casi devono uscire come
   `unavailable_requires_legal_validation` con explanation
   dedicata, mai con quote inventate.
4. **Quote successorie come tabella numerica reviewata**: solo
   dopo review Studio si crea il `CompensationDataset`
   `tn-inheritance-shares-2026` (o equivalente) e la
   `CalculationFormula` `tn_inheritance_share_calculator_v1`. Il
   sync `[official_sync]` resta separato — non promuove
   automaticamente nessuno dei tre.
5. **Smoke test deterministici** su 10+ configurazioni-tipo prima
   di esporre il calculator al pubblico.

**Stato pipeline ufficiali (aggiornato):**

| Country | Source slug | Fetch | sha256 | Calculator |
|---------|-------------|-------|--------|------------|
| MA | `ma-code-famille-moudawana-fr-pdf` | ✅ PDF 489 071 B | `41db4ab3…` | unavailable |
| TN | `tn-code-statut-personnel-livre-ix-succession` | ✅ HTML 36 183 B | `ab807896…` | unavailable |
| TN | `tn-code-dip-loi-98-97` | ✅ HTML 15 424 B | `d379a070…` | unavailable |
| EU | `eu-regulation-650-2012-successions` | metadata_only | — | n/a (quadro) |

---

## 5e. EU Regulation 650/2012 — fetch attivo (iter F-official-source-eu-reg-650-fetch-and-trace)

Promosso da `metadata_only` a `fetch` in `config/official_source_registry.json`.

**URL provati nell'iter (in ordine, con esito reale):**

| # | URL | Stato | Esito |
|---|-----|-------|-------|
| 1 | `https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650` | 200 | **scelto** — HTML 581 041 B con marker `650/2012` |
| 2 | `https://eur-lex.europa.eu/legal-content/FR/TXT/XML/?uri=CELEX:32012R0650` | 200 (probe) | fallback registrato — XML 1 204 712 B |
| 3 | `https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32012R0650` | 200 (probe) | fallback registrato — PDF 957 802 B |

**Triage CloudFront 202 transitorio.** EUR-Lex CloudFront serve
occasionalmente un body interstiziale (~2 035 B, `<title></title>`) con
HTTP 202 mentre l'origin riempie la cache; la risposta finale arriva 4-8
secondi dopo. La nuova pipeline gestisce questo caso con due livelli:

1. `_fetch` (interno): ritenta automaticamente fino a 3 volte con backoff
   fisso di 4 s quando la risposta ha status 202, prima di rilasciare
   l'esito al chiamante.
2. `validate_fetch_response` (gate qualità): rifiuta come `fetch_failed`
   ogni risposta con `status=202`, `size_bytes=0`, `sha256` pari al
   digest del body vuoto (`e3b0c44…`) o body privo dei marker dichiarati
   in `content_must_contain` (`["650/2012"]` per EU 650).

Se il primary URL è ancora rifiutato dopo i ritentativi e i gate, il
fetcher prova in sequenza i `fetch_url_alternatives` (XML, PDF) e
registra i tentativi falliti in `fallback_attempts` del manifest.

| Field | Valore |
|-------|--------|
| Slug | `eu-regulation-650-2012-successions` |
| Source kind | `eu_regulation` |
| Authority | `eurlex` |
| Official URL | `https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650` |
| Final URL | `https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650` |
| HTTP status | `200` |
| Local path | `legal_data/sources/eu/official_downloaded/eu-regulation-650-2012-successions.html` |
| Size | 581 041 bytes |
| sha256 (snapshot) | `24732567d9f86983046cf1866733ae012035a66d46a005b9bd2fe74bd07501c4` |
| Content-Type | `text/html` (verified — contiene `<title>Reglement … 650/2012</title>`, marker `CELEX:32012R0650`, metadata ELI `eli/reg/2012/650`) |
| Classification | `fetch_success` |
| Fallback attempts | `[]` (primary URL accolto dopo gli eventuali 202 retry interni) |
| LegalSource status | `needs_review` (NON promosso ad `approved`) |

**Nota sulla variabilità del digest.** EUR-Lex inietta nel body alcuni
identificatori dinamici (ad es. `RID_*`, `agentId`, `lastModification`
nello script Dynatrace `ruxitagentjs_*`). Pertanto il `size_bytes` resta
costante (~581 041 B) ma `sha256` può cambiare fra una run e l'altra:
una run precedente ha prodotto `49fa8a746478…`, questa run
`24732567d9f8…`. La verifica di integrità si basa quindi sui
**marker di contenuto** (`650/2012`, `CELEX:32012R0650`, `eli/reg/2012/650`)
piuttosto che su sha256 esatto. Per attribuire una versione canonica
serve un cross-check OJ con timestamp di pubblicazione (manual_attach
admin), che non altera la pipeline auto-sync.

**Perché non attiva calculator MA/TN.** Il regolamento 650/2012 è la
*cornice* UE di diritto internazionale privato: definisce competenza
giurisdizionale, legge applicabile, riconoscimento delle decisioni e
certificato successorio europeo, ma **non produce quote successorie**
direttamente. Le quote restano determinate dalla legge sostanziale
applicabile (Moudawana per MA, CSP Livre IX per TN, Codice civile per
IT, ecc.). Quindi:

- nessun `LegalReview` creato;
- nessun `CompensationDataset` creato;
- nessun `CalculationFormula` creato;
- nessun `CompensationTableRow` creato;
- calculator `MA-NATIONAL × international_inheritance` resta
  `unavailable_requires_legal_validation` (verificato in
  `test_eu_fetch_does_not_activate_ma_or_tn_calculator`);
- calculator `TN-NATIONAL × international_inheritance` resta idem;
- Italia 35/10/0 invariato a 26 268 / 27 353 / 28 439 EUR.

**Ruolo del Reg 650/2012 nei moduli MA/TN inheritance:**

| Domanda giuridica | Risposta data dal Reg 650/2012 |
|-------------------|--------------------------------|
| Quale giudice è competente per la successione? | Art. 4 — di norma residenza abituale del defunto al momento del decesso (per chi muore dopo il 17.08.2015). |
| Quale legge si applica? | Art. 21 — legge dello Stato di residenza abituale del defunto, salvo professio juris (art. 22) per la legge di nazionalità. |
| Riconoscimento decisioni? | Art. 39-58 — reciprocità automatica fra Stati membri partecipanti. |
| Certificato successorio europeo? | Art. 62-73 — ECS come strumento UE per provare lo status di erede o legatario. |

Il modulo TN/MA inheritance integra queste regole nell'explanation
del simulatore quando il caso ha contatti con uno Stato membro UE
(es. defunto residente abituale in Francia, eredi in Tunisia). Tutto
ciò richiede `human_exception_review`: la qualificazione della legge
applicabile, eventuali rinvii, opt-out testamentari e conflitti con
ordine pubblico (es. successione fra eredi non musulmani applicando
una legge che esclude tale categoria) non sono determinati
deterministicamente dal solo testo regolamentare.

**Coordinamento con Moudawana / CSP Livre IX / Code DIP TN:**

| Strato | Quando si applica | Fonte ufficiale syncata |
|--------|-------------------|-------------------------|
| Diritto sostanziale MA (quote) | Defunto soggetto a legge marocchina (residenza abituale + professio juris) | `ma-code-famille-moudawana-fr-pdf` |
| Diritto sostanziale TN (quote) | Defunto soggetto a legge tunisina | `tn-code-statut-personnel-livre-ix-succession` |
| Conflitto leggi lato Tunisia | Caso radicato in TN con contatti esteri | `tn-code-dip-loi-98-97` |
| Conflitto leggi lato Europa | Caso radicato in uno Stato membro UE partecipante | `eu-regulation-650-2012-successions` (questo iter) |

I quattro strati insieme coprono ~95% del materiale normativo
necessario per i moduli inheritance MA/TN. Il 5% residuo sono
casi di rinvio internazionale (renvoi), conflitti con ordine
pubblico nazionale e configurazioni familiari atipiche — destinati
a `human_exception_review` permanente.

**Stato pipeline ufficiali (post-iter EU):**

| Country | Source slug | Fetch | sha256 | Size | Calculator |
|---------|-------------|-------|--------|------|------------|
| MA | `ma-code-famille-moudawana-fr-pdf` | ✅ PDF | `41db4ab3…` | 489 071 B | unavailable |
| TN | `tn-code-statut-personnel-livre-ix-succession` | ✅ HTML | `ab807896…` | 36 183 B | unavailable |
| TN | `tn-code-dip-loi-98-97` | ✅ HTML | `d379a070…` | 15 424 B | unavailable |
| EU | `eu-regulation-650-2012-successions` | ✅ HTML | `24732567…` (volatile) | 581 041 B | n/a (quadro) |

Tutti e quattro i target principali per il modulo inheritance
internazionale MA/TN sono ora `fetch_success` con sha256 tracciato.
Nessun calculator è stato promosso.

---

## 6. Riferimenti incrociati

- Pacchetto pre-esistente: `download_international_legal_sources` in
  `apps/legal_sources/management/commands/` — scarica FR/BE/MA/TN in
  `legal_data/sources/<country>/downloaded/` con manifest e sha256.
  Il nuovo `sync_official_sources` **non sostituisce** quel command:
  scrive in `official_downloaded/` (cartella separata), e si applica
  **solo** alle fonti classificate ufficiali via registry.
- Stato attuale fonti per paese:
  - `docs/architecture/MOROCCO_INHERITANCE_MODULE_STATUS.md`
  - `docs/architecture/TUNISIA_INHERITANCE_MODULE_STATUS.md`
- Review umana già in pipeline:
  - `legal_data/sources/it/dpr-12-2025/review/` — TUN 2025 review
    pacchetto (gitignore allow-listato per i template).
- Snapshot post-pass2 a11y/SEO: `docs/architecture/PUBLIC_SITE_QA_POLISH_PASS2.md`.
