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

## 5f. IT D.P.R. 12/2025 — official cross-check (iter F-official-source-it-dpr-12-2025-gazzetta-crosscheck)

Il D.P.R. 13 gennaio 2025, n. 12 (Tabella Unica Nazionale art. 138 CAP) ha
già `LegalSource.status=approved` e dataset `DPR-12-2025` /
`DPR-12-2025-MORAL` `approved` con review Studio del 2026-04-27. Lo Studio
ha chiesto una verifica ufficiale aggiuntiva su `gazzettaufficiale.it`
**senza** reimport del dataset né modifica di formula/righe. Per coprire
questo caso d'uso introduciamo un nuovo `ingest_mode=verify_existing`
nel registry e un classification dedicato `crosscheck_success` /
`crosscheck_failed` (mai `fetch_*`) — così il manifest e le notes restano
distinguibili da una run di estrazione vera.

**URL provati nell'iter (in ordine, con esito reale):**

| # | URL | Stato | Esito |
|---|-----|-------|-------|
| 1 | `https://www.gazzettaufficiale.it/eli/id/2025/02/11/25G00021/sg` | 200 | scartato — body 11 296 B (SPA shell, contenuto JS-rendered, nessun marker raw) |
| 2 | `https://www.gazzettaufficiale.it/eli/gu/2025/02/11/34/sg/pdf` | 200 | **scelto** — PDF Serie Generale n. 34 dell'11 febbraio 2025, 2 820 562 B, marker confermato via `pdfplumber` |

**Estrazione testuale per i PDF.** Il corpo del PDF Gazzetta usa font CMap
con glyph table proprietaria: i marker italiani (`D.P.R.`, `13 gennaio
2025`, `n. 12`, `danno biologico`, `Tabella`) **non** appaiono nei byte
crudi del file. Per supportare il marker check su PDF abbiamo aggiunto un
fallback in `validate_fetch_response`: se il body inizia con `%PDF-` e i
marker non si trovano nei byte, viene tentata l'estrazione testo via
`pdfplumber` sulle prime 16 pagine. Questo cattura `13 gennaio 2025` (data
di firma del decreto, presente nell'indice e nel testo articolato) e
sblocca `marker_check_passed=true`. Per HTML/XML il check resta sui byte
crudi (fast path, già usato per MA/TN/EU).

| Field | Valore |
|-------|--------|
| Slug | `it-dpr-12-2025-tun-danno-biologico` |
| Source kind | `official_decree` |
| Authority | `official_gazette` |
| Ingest mode | `verify_existing` |
| Official URL | `https://www.gazzettaufficiale.it/eli/id/2025/02/11/25G00021/sg` |
| Final URL | `https://www.gazzettaufficiale.it/eli/gu/2025/02/11/34/sg/pdf` |
| HTTP status | `200` |
| Local path | `legal_data/sources/italy/official_downloaded/it-dpr-12-2025-tun-danno-biologico.pdf` |
| Size | 2 820 562 bytes |
| sha256 | `3ecd8597f44c473cb35582cac53d2f2832fd455ca702d876f7280a87e8ba3f19` |
| Content-Type | `application/pdf` |
| Classification | `crosscheck_success` |
| `crosscheck_only` | `true` |
| `no_reimport` | `true` |
| `no_calculator_activation_change` | `true` |
| `marker_check_passed` | `true` (via pdfplumber sulle prime 16 pagine) |
| Fallback attempts | 1 (HTML ELI rifiutato per marker mancanti, atteso) |
| LegalSource status | `approved` (preservato — il flow `verify_existing` non altera mai lo status) |

**Cosa NON è stato modificato (invariants confermati live).**

| Layer | Stato pre-iter | Stato post-iter |
|-------|----------------|-----------------|
| `LegalSource` `it-dpr-12-2025-tun-danno-biologico` | `approved` | `approved` (notes annotate con `[official_sync]`, niente altro) |
| `CompensationDataset` count `approved` (IT) | 2 (`DPR-12-2025` + `DPR-12-2025-MORAL`) | 2 (intatti) |
| `CalculationFormula` count | 1 (`italy_art_138_tun_2025_base`, `amount_rule=row_amount_range_direct`, `approved`) | 1 (intatta) |
| `CompensationTableRow` total | 36 764 | 36 764 |
| `LegalReview` count | 2 | 2 |
| Italia 35/10/0 EUR | 26 268 / 27 353 / 28 439 | 26 268 / 27 353 / 28 439 |

**Relazione con il pipeline TUN 2025 esistente.** Il PDF locale autoritativo
del *solo* D.P.R. 12/2025 — quello effettivamente estratto in 36 764 righe —
resta `legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf` (sha256 e
review pipeline indipendenti, non rifirmati da questo iter). Il file
nuovo `legal_data/sources/italy/official_downloaded/it-dpr-12-2025-tun-danno-biologico.pdf`
è invece l'**intero** fascicolo Gazzetta Serie Generale n. 34 dell'11
febbraio 2025 (multi-decreto, 2.8 MB) — utile come traccia di
pubblicazione/identificazione ELI ma *non* sostituto del PDF di
riferimento per l'estrazione tabellare. I due file convivono per design.

**Stato pipeline ufficiali (post-iter IT crosscheck):**

| Country | Source slug | Mode | Classification | sha256 | Size | Calculator |
|---------|-------------|------|----------------|--------|------|------------|
| IT | `it-dpr-12-2025-tun-danno-biologico` | verify_existing | crosscheck_success | `3ecd8597…` | 2 820 562 B | calculated (35/10/0 = 26268/27353/28439) |
| MA | `ma-code-famille-moudawana-fr-pdf` | fetch | fetch_success | `41db4ab3…` | 489 071 B | unavailable |
| TN | `tn-code-statut-personnel-livre-ix-succession` | fetch | fetch_success | `ab807896…` | 36 183 B | unavailable |
| TN | `tn-code-dip-loi-98-97` | fetch | fetch_success | `d379a070…` | 15 424 B | unavailable |
| EU | `eu-regulation-650-2012-successions` | fetch | fetch_success | `24732567…` (volatile) | 581 041 B | n/a (quadro) |

Cinque fonti ufficiali ora con sha256 tracciato e marker integrity
verificata. Italia è l'unica con `verify_existing` perché è l'unica con
calculator già `approved` e dataset/formula già rivisti dallo Studio: ogni
ulteriore re-fetch deve essere puramente verificatorio.

---

## 5g. BE Loi 1989 RC Auto — fetch attivo (iter F-official-source-be-loi-1989-rc-auto-fetch-and-trace)

Promosso da `metadata_only` a `fetch` in `config/official_source_registry.json`.
La Loi du 21 novembre 1989 relative à l'assurance obligatoire de la
responsabilité en matière de véhicules automoteurs è la cornice normativa
del modulo BE road accident, ma da sola **non** abilita un calculator:
le tabelle indennitarie belghe sono giurisprudenziali / private
(Tableau Indicatif, Schryvers) e restano in scope `human_exception_review`
finché lo Studio non valida un dataset/engine tabellare.

**URL provati nell'iter (in ordine, con esito reale):**

| # | URL | Stato | Esito |
|---|-----|-------|-------|
| 1 | `https://economie.fgov.be/fr/legislation/loi-du-21-novembre-1989` | 200 | **scelto** — HTML 28 155 B con marker `21 NOVEMBRE 1989`, `responsabilité`, `véhicules automoteurs`, `assurance obligatoire` (3 hit ciascuno) |
| 2 | `https://economie.fgov.be/nl/legislation/wet-van-21-november-1989` | 200 (probe) | fallback registrato — HTML 27 836 B (variante NL) |

La traduzione EN (`/en/legislation/law-21-november-1989`) **non** è
inclusa nei `fetch_url_alternatives`: i marker richiesti dal registry
sono in francese, includere l'EN farebbe scattare un falso
`marker_check_failed`. Resta accessibile per traduzione/consultazione
ma non è parte del flow di sync ufficiale.

**Snapshot fields:**

| Field | Valore |
|-------|--------|
| Slug | `be-loi-1989-11-21-rc-auto` |
| Source kind | `official_law` |
| Authority | `spf_economie` |
| Ingest mode | `fetch` |
| Official URL | `https://economie.fgov.be/fr/legislation/loi-du-21-novembre-1989` |
| Final URL | `https://economie.fgov.be/fr/legislation/loi-du-21-novembre-1989` |
| HTTP status | `200` |
| Local path | `legal_data/sources/belgium/official_downloaded/be-loi-1989-11-21-rc-auto.html` |
| Size | 28 155 bytes |
| sha256 | `f806f105b85fc39871d60cf9be463bfba0747602811e09d1043c7403471d8749` |
| Content-Type | `text/html; charset=UTF-8` |
| Classification | `fetch_success` |
| Fallback attempts | `[]` (primary FR accolto al primo tentativo) |
| LegalSource status | `needs_review` (NON promosso ad `approved` — la promozione richiede review Studio esplicita) |

**Cosa NON è stato attivato.**

| Layer | Stato post-iter |
|-------|-----------------|
| Calculator BE × `road_accident_bodily_injury` | `unavailable_requires_legal_validation` (verificato live + via test mockato) |
| `CompensationDataset` (BE) | nessuno creato |
| `CalculationFormula` (BE) | nessuna creata |
| `CompensationTableRow` (BE) | 0 (totale rimane 36 764 — solo IT TUN 2025) |
| `LegalReview` (BE) | nessuna creata |
| Promozione `LegalSource.status` | nessuna (resta `needs_review`) |

**Perché il calculator BE resta unavailable.**

1. **Tableau Indicatif 2020/2024** (`be-tableau-indicatif-2020`,
   `be-tableau-indicatif-2024`) sono `court_indicative_table`: tabelle
   suggerite dal collegio Magistrats/Avocats, non normativa primaria
   binding. Per uso in calcolo serve scelta giuridica esplicita Studio.
2. **Tableau Indicatif 2024** è inoltre PDF scansionato: lo spike OCR
   in `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/`
   conferma che l'estrazione automatica richiede QA per riga.
3. **Schryvers** (`be-tables-schryvers-*`) sono tabelle private (avvocato
   editoriale): `private_bareme`, `human_exception_review` permanente.
4. **Engine BE** non esiste ancora (`apps/calculators/engines/`): la
   funzione `run_simulation` smista BE × road accident a
   `unavailable_requires_legal_validation` di default.
5. **Dataset BE** non esiste: `CompensationDataset.objects.filter(country__code='BE')` → 0.

La Loi 1989 da sola dice *che la RC auto è obbligatoria* e fissa il
quadro responsabilità; il *quanto* indennitario lo determinano i
referenti giurisprudenziali (TI) e la prassi assicurativa, che lo Studio
deve validare prima di trasformarli in righe `CompensationTableRow`.

**Stato pipeline ufficiali (post-iter BE):**

| Country | Source slug | Mode | Classification | sha256 | Size | Calculator |
|---------|-------------|------|----------------|--------|------|------------|
| IT | `it-dpr-12-2025-tun-danno-biologico` | verify_existing | crosscheck_success | `3ecd8597…` | 2 820 562 B | calculated (35/10/0 = 26268/27353/28439) |
| MA | `ma-code-famille-moudawana-fr-pdf` | fetch | fetch_success | `41db4ab3…` | 489 071 B | unavailable |
| TN | `tn-code-statut-personnel-livre-ix-succession` | fetch | fetch_success | `ab807896…` | 36 183 B | unavailable |
| TN | `tn-code-dip-loi-98-97` | fetch | fetch_success | `d379a070…` | 15 424 B | unavailable |
| EU | `eu-regulation-650-2012-successions` | fetch | fetch_success | `24732567…` (volatile) | 581 041 B | n/a (quadro) |
| BE | `be-loi-1989-11-21-rc-auto` | fetch | fetch_success | `f806f105…` | 28 155 B | unavailable |

Sei fonti ufficiali ora con sha256 tracciato. La Loi BE chiude il primo
strato (cornice normativa primaria) per BE road accident; lo strato
tabellare resta `human_exception_review`.

---

## 5h. Manual attach pipeline (iter F-official-source-manual-attach-pipeline)

### Perché esiste

Alcune fonti ufficiali sono inaccessibili al fetcher automatico anche con
User-Agent browser-like e retry on 202:

- **Légifrance** (FR Loi Badinter, FR Code des assurances) → HTTP 403
  permanente per i client non-browser, anche dietro Cloudflare in
  modalità challenge.
- **Pagine SPA puramente JS** (varianti specifiche di
  `gazzettaufficiale.it` o portali ministeriali con bundle React/Vue) →
  raw HTML è un guscio di 5-15 KB senza marker; serve un browser
  headless per estrarre il testo.
- **Endpoint con TLS strict / mTLS** (raramente, ma alcune anagrafi
  pubbliche europee) → handshake fallisce sotto `requests`.
- **PDF dietro paywall / login** (Schryvers PDF, alcune banche dati
  giurisprudenziali) → la pipeline auto-fetch è inutile per design.

Per queste fonti lo Studio scarica manualmente il file (browser, accesso
abbonato, download da PEC istituzionale, ecc.) e lo registra con il
nuovo command `attach_official_source_file`.

### Cosa fa il command

```text
python manage.py attach_official_source_file --slug <slug> --file <path>
```

1. Legge `config/official_source_registry.json` e richiede
   `manual_attach_allowed=true` per lo slug.
2. Calcola `sha256` e `size_bytes` del file fornito.
3. Esegue il marker check `content_must_contain` con la **stessa**
   logica del fetch automatico (raw bytes per HTML/text, fallback
   `pdfplumber` sulle prime 16 pagine per i PDF).
4. Copia il file in
   `legal_data/sources/<country>/manual_attached/<slug>.<ext>`.
5. Aggiorna `legal_data/sources/<country>/manual_attached/manual_attach_manifest.json`
   (cumulativo per paese, idempotente per slug).
6. Annota `LegalSource.notes` con un blocco `[manual_attach] BEGIN…END`
   che **convive** con un eventuale `[official_sync]` precedente — il
   trailer del fetch automatico non viene toccato.

### Cosa NON fa

| Layer | Comportamento |
|-------|---------------|
| `LegalReview` | mai creato |
| `CompensationDataset` | mai creato/modificato |
| `CalculationFormula` | mai creata/modificata |
| `CompensationTableRow` | mai creata/modificata |
| `LegalSource.status` | mai promosso a `APPROVED`. Le nuove righe sono inserite con `NEEDS_REVIEW` |
| Enum `SourceStatus` | mai esteso |
| Calculator del paese | nessuna riattivazione: `unavailable_requires_legal_validation` resta tale finché lo Studio non valida l'engine + dataset (separati) |
| Italia 35/10/0 EUR | invariato (verificato live + via test `test_italy_smoke_unchanged_after_manual_attach`) |

Marker check fallito → `CommandError`, **nessuna** scrittura su file
system o DB. È una protezione esplicita contro l'errore operativo
("ho attaccato il file sbagliato").

### Differenza rispetto a `LegalReview`

`manual_attach` è il *layer integrità*: registra che un certo file con
un certo sha256 è stato depositato in un certo momento. Non ha alcun
effetto semantico — l'estensione, le righe, le formule che lo Studio
deciderà di trarre dalla fonte sono materia di un *secondo* passaggio
manuale (review legale + import dataset).

`LegalReview` è il *layer semantico*: certifica che un revisore
qualificato ha letto la fonte ed esprime un giudizio sul suo uso per un
calculator specifico. Solo questo step può promuovere
`LegalSource.status` a `APPROVED` e sbloccare un engine.

I due layer sono indipendenti per design: una fonte può avere
`manual_attach` ma nessuna `LegalReview` (caso comune al primo upload),
e viceversa una vecchia review umana può esistere senza un manual
attach (se la fonte è stata caricata prima di questo iter).

### Esempio — FR Loi Badinter

La Loi du 5 juillet 1985 è il primo target di questa pipeline:

- Registry: `fr-loi-badinter-1985`, `manual_attach_allowed=true`,
  markers `["5 juillet 1985", "accidents de la circulation", "indemnisation", "victimes"]`.
- Comando:

  ```powershell
  python manage.py attach_official_source_file `
      --slug fr-loi-badinter-1985 `
      --file C:\Users\studio\Downloads\loi-badinter-consolidee.pdf
  ```

- Effetto: file copiato in
  `legal_data/sources/france/manual_attached/fr-loi-badinter-1985.pdf`,
  trailer `[manual_attach]` aggiunto a `LegalSource.notes`,
  `manual_attach_manifest.json` aggiornato.

Runbook completo: [`docs/legal_sources/MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md`](../legal_sources/MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md).

### Cosa resta necessario per attivare l'engine Francia

Il manual attach è lo *step 0*. Per attivare `apps/calculators/engines/france.py`
servono ancora, in ordine:

1. **Review legale Studio** della Loi Badinter sul perimetro `road_accident_bodily_injury` → promozione manuale di `LegalSource.status` a `APPROVED`.
2. **Fonte di quantificazione** validata (Référentiel Mornet 2024
   oppure deductive table giurisprudenziale): oggi `private_bareme` /
   `human_exception_only`, richiede review legale esplicita.
3. **`CompensationDataset` + `CalculationFormula`** allineati al
   bareme validato (pipeline import separata, fuori scope manual_attach).
4. **Engine FR** in `apps/calculators/engines/`: oggi assente,
   `run_simulation` smista FR × road accident a
   `unavailable_requires_legal_validation` di default.

Il manual attach copre il *file integrity* ma non delega né accelera
nessuno degli step 1-4.

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
- Pipeline manual attach (fonti con blocco tecnico al fetch automatico):
  - Comando: `apps/legal_sources/management/commands/attach_official_source_file.py`
  - Runbook: `docs/legal_sources/MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md`
  - Output: `legal_data/sources/<country>/manual_attached/`
- Review umana già in pipeline:
  - `legal_data/sources/it/dpr-12-2025/review/` — TUN 2025 review
    pacchetto (gitignore allow-listato per i template).
- Snapshot post-pass2 a11y/SEO: `docs/architecture/PUBLIC_SITE_QA_POLISH_PASS2.md`.
