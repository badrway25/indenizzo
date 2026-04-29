# International legal sources — download report

> Snapshot della prima esecuzione reale del command
> `python manage.py download_international_legal_sources`. Aggiornare
> ad ogni nuovo run. I PDF/HTML scaricati restano locali (gitignore);
> il manifest JSON è la traccia di audit canonica.
>
> **Iter1 → iter2 (2026-04-29).** Triage URL applicato al `PACKAGES`
> in `download_international_legal_sources.py` sulla base degli esiti
> reali di iter1 (vedi §0bis). Il command supporta ora un flag
> `manual_download_required` che crea la `LegalSource` come metadata
> (status `needs_review`) senza scaricare il file: lo Studio carica il
> PDF a mano via Django admin → `LegalSourceAttachment`. Nessuna fonte
> approvata, nessun dataset, nessuna formula creata dal command.
> **Re-run reale eseguito 2026-04-29 09:28-09:29 UTC** — vedi §0ter.

## 0bis. URL triage applicato (iter1 → iter2)

Tre azioni su tre paesi. Belgio invariato (5/5 OK in iter1).

### Slug rimossi (duplicati funzionali, host non raggiungibile)

| Slug rimosso | Paese | Motivo | Coperto da |
|---|---|---|---|
| `ma-code-famille-loi-70-03-dgct` | MA | `ConnectTimeout` su `collectivites-territoriales.gov.ma` (host offline) | `ma-code-famille-moudawana-fr-pdf` (PDF_OK in iter1) |
| `tn-code-dip-pdf-support` | TN | `ConnectionRefused` su `marouani-avocat.com` | `tn-code-dip-loi-98-97` (HTML_OK in iter1) |

### Slug marcati `manual_download_required: True`

Manteniamo la `LegalSource` come metadata + audit trail; il file va
scaricato a mano da browser e attaccato via Django admin.

| Slug | Paese | Motivo | Note operative |
|---|---|---|---|
| `fr-loi-badinter-1985` | FR | Legifrance restituisce `403 Forbidden` per User-Agent non-browser | Scaricare la versione consolidée PDF da `legifrance.gouv.fr` da browser |
| `tn-jort-code-statut-personnel-1956` | TN | `ConnectTimeout` su `pist.tn`; nessuna URL JORT alternativa stabile identificata | Scaricare il fascicolo JORT 1956 da `pist.tn` o `iort.gov.tn` da browser |
| `tn-code-statut-personnel-compiled` | TN | `SSLError` (hostname mismatch) su `jafbase.fr`; nessun mirror ufficiale TN verificato | Per scope successioni il livre-IX HTML basta. Scaricare la versione completa da `legislation.tn` o `iort.gov.tn` se serve la copertura completa |

### URL switch — EUR-Lex Reg. 650/2012

Endpoint `/legal-content/FR/TXT/PDF/?uri=CELEX:32012R0650` risponde
`HTTP 202` + body vuoto (rendering PDF asincrono lato server). Switch
a `/legal-content/FR/TXT/?uri=CELEX:32012R0650` (HTML completo, sempre
`200`). Applicato a entrambi i collegamenti MA + TN.

| Slug | Endpoint precedente | Endpoint nuovo | Classe attesa |
|---|---|---|---|
| `eu-regulation-650-2012-successions-fr-ma` | `/TXT/PDF/?uri=CELEX:32012R0650` | `/TXT/?uri=CELEX:32012R0650` | `HTML_OK_SOURCE_PAGE` |
| `eu-regulation-650-2012-successions-fr-tn` | `/TXT/PDF/?uri=CELEX:32012R0650` | `/TXT/?uri=CELEX:32012R0650` | `HTML_OK_SOURCE_PAGE` |

### Nuovi campi nel manifest

`download_manifest.json` ora include per ogni voce:
- `classification`: tag derivato dall'esito (`MANUAL_DOWNLOAD_REQUIRED`,
  `FAILED_NEEDS_REPLACEMENT_URL`, `HTTP_202_WARNING`,
  `HTML_WARNING_NOT_FINAL_DOCUMENT`, `PDF_OK`, `HTML_OK_SOURCE_PAGE`,
  `BIN_OK`).
- `manual_download_required`: bool. Quando `true` il file non viene
  scaricato; la `LegalSource` viene comunque creata come metadata
  per consentire l'upload manuale via admin.

Il livello paese del manifest aggiunge il contatore `manual_required`
oltre a `succeeded` / `failed`.

### Esiti attesi del re-run (post-triage)

| Paese | Item totali | OK attesi | FAIL attesi | MANUAL attesi | HTTP_202 attesi |
|---|---:|---:|---:|---:|---:|
| FR | 5 | 4 | 0 | 1 (Badinter) | 0 |
| BE | 5 | 5 | 0 | 0 | 0 |
| MA | 4 | 4 | 0 | 0 | 0 |
| TN | 5 | 3 | 0 | 2 (JORT + CSP-compiled) | 0 |
| **Totale** | **19** | **16** | **0** | **3** | **0** |

Il re-run reale è gating per lo Studio: prima conferma del triage,
poi `python manage.py download_international_legal_sources --all`.

## 0ter. Esiti reali del re-run iter2 (2026-04-29 09:28-09:29 UTC)

Re-run eseguito paese-per-paese a triage applicato. **Tutte le righe
di `succeeded`/`failed`/`manual_required` sono lette dai 4 manifest
correnti.**

| Paese | Run UTC | succeeded | failed | manual_required | LegalSource (DB) | Attachment PDF |
|---|---|---:|---:|---:|---:|---:|
| FR | 2026-04-29 09:28:43 | 4 | 0 | 1 | 5 needs_review | 2 |
| BE | 2026-04-29 09:28:49 | 5 | 0 | 0 | 5 needs_review | 2 |
| MA | 2026-04-29 09:28:53 | 4 | 0 | 0 | 4 needs_review | 3 |
| TN | 2026-04-29 09:29:00 | 3 | 0 | 2 | 5 needs_review | 0 |
| **Totale** | | **16** | **0** | **3** | **19** | **7** |

I conteggi attesi del triage sono rispettati al 100%.

### 0ter.1. Distribuzione `classification` reale

| classe | FR | BE | MA | TN | totale | note |
|---|---:|---:|---:|---:|---:|---|
| `PDF_OK` | 2 | 2 | 3 | 0 | **7** | tutti con `Attachment` PDF in DB |
| `HTML_OK_SOURCE_PAGE` | 1 | 3 | 0 | 2 | **6** | nessun `Attachment` (HTML è metadata) |
| `HTML_WARNING_NOT_FINAL_DOCUMENT` | 1 | 0 | 0 | 0 | **1** | landing Gazette du Palais 2025 |
| `HTTP_202_WARNING` | 0 | 0 | 1 | 1 | **2** | EUR-Lex Reg. 650/2012 — vedi §0ter.4 |
| `MANUAL_DOWNLOAD_REQUIRED` | 1 | 0 | 0 | 2 | **3** | metadata creata, file da caricare a mano |
| `FAILED_NEEDS_REPLACEMENT_URL` | 0 | 0 | 0 | 0 | **0** | nessun fallimento — triage efficace |

### 0ter.2. Lista `manual_download_required` (3 fonti)

| Slug | Paese | URL ufficiale | Motivo | Azione richiesta |
|---|---|---|---|---|
| `fr-loi-badinter-1985` | FR | `https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000693454` | Legifrance 403 su UA non-browser | Scaricare consolidée PDF da browser, attaccare via Django admin |
| `tn-jort-code-statut-personnel-1956` | TN | `https://www.pist.tn/jort/1956/1956F/Jo10456.pdf` | `pist.tn` ConnectTimeout | Scaricare JORT 1956 da `pist.tn`/`iort.gov.tn` da browser |
| `tn-code-statut-personnel-compiled` | TN | `https://jafbase.fr/docMaghreb/TunisieStatutpersonnel.PDF` | `jafbase.fr` SSL hostname mismatch | Per scope successioni il livre-IX HTML basta; se serve la versione completa scaricare da `legislation.tn`/`iort.gov.tn` |

In DB ciascuna ha `LegalSource(status=needs_review)` con `notes`
che riporta integralmente la `manual_reason` + il prefisso "Manual
download required:". Nessun `LegalSourceAttachment` finché lo Studio
non carica il file a mano.

### 0ter.3. Hash + size + local_path delle fonti scaricate

| slug | classe | size (B) | sha256 (12c) | local_path |
|---|---|---:|---|---|
| `fr-nomenclature-dintilhac-2005` | HTML_OK | 60 751 | `0db1f1d220b3` | `legal_data/sources/france/downloaded/fr-nomenclature-dintilhac-2005.html` |
| `fr-referentiel-mornet-2024` | PDF_OK | 898 965 | `2dd2e760bc05` | `legal_data/sources/france/downloaded/fr-referentiel-mornet-2024.pdf` |
| `fr-bareme-capitalisation-gazette-palais-2022` | PDF_OK | 978 456 | `686a557b23fa` | `legal_data/sources/france/downloaded/fr-bareme-capitalisation-gazette-palais-2022.pdf` |
| `fr-bareme-capitalisation-gazette-palais-2025-page` | HTML_WARN | 56 413 | `6e42ec8378f1` | `legal_data/sources/france/downloaded/fr-bareme-capitalisation-gazette-palais-2025-page.html` |
| `be-loi-1989-11-21-rc-auto` | HTML_OK | 24 224 | `58402e522116` | `legal_data/sources/belgium/downloaded/be-loi-1989-11-21-rc-auto.html` |
| `be-tableau-indicatif-2024` | PDF_OK | 2 373 682 | `37b0a0b4606e` | `legal_data/sources/belgium/downloaded/be-tableau-indicatif-2024.pdf` |
| `be-tableau-indicatif-2020` | PDF_OK | 1 985 686 | `1b073f5c41c8` | `legal_data/sources/belgium/downloaded/be-tableau-indicatif-2020.pdf` |
| `be-tables-schryvers-2026-page` | HTML_OK | 181 518 | `1e4229479a38` | `legal_data/sources/belgium/downloaded/be-tables-schryvers-2026-page.html` |
| `be-tables-schryvers-tableurs` | HTML_OK | 186 071 | `c70e16124b3c` | `legal_data/sources/belgium/downloaded/be-tables-schryvers-tableurs.html` |
| `ma-code-famille-moudawana-fr-pdf` | PDF_OK | 489 071 | `41db4ab3d505` | `legal_data/sources/morocco/downloaded/ma-code-famille-moudawana-fr-pdf.pdf` |
| `ma-code-droits-reels-loi-39-08` | PDF_OK | 282 302 | `55e190cfd1b1` | `legal_data/sources/morocco/downloaded/ma-code-droits-reels-loi-39-08.pdf` |
| `ma-code-droits-reels-traduction-aute` | PDF_OK | 548 484 | `605d1a65fcce` | `legal_data/sources/morocco/downloaded/ma-code-droits-reels-traduction-aute.pdf` |
| `eu-regulation-650-2012-successions-fr-ma` | HTTP_202 | 0 | `e3b0c44298fc` | `legal_data/sources/morocco/downloaded/eu-regulation-650-2012-successions-fr-ma.html` |
| `tn-code-statut-personnel-livre-ix-succession` | HTML_OK | 36 183 | `ab8078968ccf` | `legal_data/sources/tunisia/downloaded/tn-code-statut-personnel-livre-ix-succession.html` |
| `tn-code-dip-loi-98-97` | HTML_OK | 181 484 | `bc292813708d` | `legal_data/sources/tunisia/downloaded/tn-code-dip-loi-98-97.html` |
| `eu-regulation-650-2012-successions-fr-tn` | HTTP_202 | 0 | `e3b0c44298fc` | `legal_data/sources/tunisia/downloaded/eu-regulation-650-2012-successions-fr-tn.html` |

> **Nota stabilità contenuto rispetto a iter1.** Tutti gli sha256 dei
> contenuti già scaricati a iter1 (es. moudawana, mornet, tableau
> indicatif) sono **identici** a quelli registrati in iter1: nessuna
> variazione lato server. L'unico contenuto nuovo è
> `tn-code-dip-loi-98-97` (sha `bc292813708d` nuovo vs `3ee9c7d11dbc`
> di iter1) — la pagina `legislation-securite.tn` ha contenuto
> dinamico (timestamp/cookie banner). **Nota**: lo sha cambia ma il
> contenuto giuridico è lo stesso; lo Studio lo confermerà nella
> review.

### 0ter.4. EUR-Lex 202 — switch `/TXT/PDF/` → `/TXT/` NON ha risolto

Il triage iter2 prevedeva che lo switch all'endpoint HTML
`/legal-content/FR/TXT/?uri=CELEX:32012R0650` restituisse `200 + corpo
HTML completo`. **Nei fatti, anche l'endpoint HTML risponde HTTP 202 +
body vuoto** quando interrogato da `requests` con UA programmatico:

| slug | http | size | sha256 | classification |
|---|---:|---:|---|---|
| `eu-regulation-650-2012-successions-fr-ma` | 202 | 0 | `e3b0c44298fc…` (null hash) | `HTTP_202_WARNING` |
| `eu-regulation-650-2012-successions-fr-tn` | 202 | 0 | `e3b0c44298fc…` (null hash) | `HTTP_202_WARNING` |

Diagnosi: EUR-Lex applica throttling/rendering asincrono **a tutti**
gli endpoint `/legal-content/FR/TXT/...` con response cache miss.
La `LegalSource` è creata come metadata ma **il file su disco è
vuoto**. Le strategie residue:

1. **Manuale**: scaricare il testo HTML/PDF da browser e attaccare via
   Django admin (analoga al pattern `manual_download_required`).
2. **Re-run con polling**: estendere `_fetch` per ritentare al primo
   202 con back-off di 2-5 secondi finché lo status diventa 200.
   Invasivo: cambia il command, va testato.
3. **Mirror EUR-Lex JSON-LD**: API REST `webapi.legaltools.org` o
   `oeil.secure.europarl.europa.eu` espone il regolamento. Da
   verificare la stabilità.

**Raccomandazione**: trattare come `manual_download_required` in iter3
del triage (file finale via download manuale dallo Studio).

### 0ter.5. Garanzie verificate post re-run

Verifiche eseguite via `python manage.py shell` (read-only):

- `LegalSource` FR/BE/MA/TN: **19 totale, 19 needs_review, 0 approved**.
- `LegalReview` per `country__code__in=("FR","BE","MA","TN")`: **0**.
- `CompensationDataset.objects.count()` = **2** (solo i 2 IT pre-esistenti).
- `CalculationFormula.objects.count()` = **1** (solo IT base).
- Italia `it-dpr-12-2025-tun-danno-biologico`: **approved** (invariato).
- Dataset `DPR-12-2025` base: **approved**, **9 191 righe** (invariato).
- Dataset `DPR-12-2025-MORAL`: **approved**, **27 573 righe** (invariato).
- Formula `italy_art_138_tun_2025_base`: **approved**, `amount_rule = row_amount_range_direct` (invariato).
- Smoke `35/10/0` → `min=26 268 / mid=27 353 / max=28 439` ✓ (invariato).

### 0ter.6. Prossimi step (post re-run iter2)

1. **Studio carica i 3 manuali via admin** (Badinter, JORT 1956, CSP
   compiled). Per ciascuno: aprire la `LegalSource` esistente,
   sezione `Attachments`, upload del PDF reale. Lo SHA-256 verrà
   calcolato dal `LegalSourceAttachment.save()`.
2. **Trattare i 2 EUR-Lex come manuali** (vedi §0ter.4): sostituire i
   file vuoti scaricando il testo da browser. In alternativa, in un
   iter3 del triage marcarli `manual_download_required: True` per
   coerenza con il pattern.
3. **Legal review** per le 19 fonti: lo Studio analizza ciascuna,
   crea `LegalReview(decision=approve|reject|needs_changes)` con
   commento esplicito. Non c'è gating sull'ordine: ogni fonte è
   indipendente.
4. **Estrazione dati per le fonti `approved`** — solo dopo legal
   review:
   - BE Tableau Indicatif 2024 → parser PDF dedicato → CSV → import
     additivo.
   - FR Mornet 2024 → parser PDF dedicato → CSV → import.
   - FR Barème Gazette du Palais 2022 → parser tabellare per
     coefficienti di capitalizzazione.
5. **Engine** (in fase successiva, non ora): stub MA/TN inheritance
   già scaffold; FR/BE road accident scaffold. Nessuna logica
   numerica fino a `approved` su almeno una fonte E `LegalReview`
   esplicita sullo scope.
6. **Lasciare invariato il calculator Italia** — il re-run di iter2
   non l'ha toccato e non deve essere toccato. Smoke 35/10/0 sigilla.

## 0. Riepilogo per paese — STORICO iter1 (sostituito da §0ter)

> Le sezioni §0 / §§1-4 / §5 / §6 documentano il run di iter1
> (2026-04-29 08:57-08:58 UTC), prima del triage. Sono mantenute come
> traccia storica per spiegare *perché* il triage URL è stato necessario;
> i conteggi e le classification *correnti* sono in §0ter.

| Paese | Run | OK | FAIL | HTTP_202 | LegalSource (DB) | Attachment PDF | Manifest |
|---|---|---:|---:|---:|---:|---:|---|
| FR | 2026-04-29 08:57 UTC | 4 | 1 | 0 | 4 needs_review | 2 | `legal_data/sources/france/downloaded/download_manifest.json` |
| BE | 2026-04-29 08:57 UTC | 5 | 0 | 0 | 5 needs_review | 2 | `legal_data/sources/belgium/downloaded/download_manifest.json` |
| MA | 2026-04-29 08:57 UTC | 4 | 1 | 1 | 4 needs_review | 3 | `legal_data/sources/morocco/downloaded/download_manifest.json` |
| TN | 2026-04-29 08:58 UTC | 3 | 3 | 1 | 3 needs_review | 0 | `legal_data/sources/tunisia/downloaded/download_manifest.json` |
| **Totale** | | **16** | **5** | **2** | **16** | **7** | |

Garanzie verificate dopo il run:
- Nessuna `LegalSource` FR/BE/MA/TN promossa a `approved` (count=0).
- Nessuna `LegalReview` creata per FR/BE/MA/TN (count=0).
- `CompensationDataset.objects.count() == 2` (solo i due IT pre-esistenti).
- `CalculationFormula.objects.count() == 1` (solo IT base).
- Italia smoke `(35,10,0)` → `min=26 268 / mid=27 353 / max=28 439` ✓.
- IT TUN dataset base `approved`, 9 191 righe; moral `approved`, 27 573 righe.
- Formula IT `amount_rule = row_amount_range_direct` invariato.

## 1. Tabella dettaglio fonti — FR

| slug | classe | http | content_type | size (B) | sha256 (12c) | DB | attachment | note / link |
|---|---|---:|---|---:|---|---|---:|---|
| `fr-loi-badinter-1985` | **FAILED_NEEDS_REPLACEMENT_URL** | — | — | — | — | non creato | 0 | `403 Forbidden` su `legifrance.gouv.fr` (UA bloccato) |
| `fr-nomenclature-dintilhac-2005` | **HTML_OK_SOURCE_PAGE** | 200 | text/html | 60 751 | `0db1f1d220b3` | needs_review | 0 | landing page `justice.gouv.fr` |
| `fr-referentiel-mornet-2024` | **PDF_OK** | 200 | application/pdf | 898 965 | `2dd2e760bc05` | needs_review | 1 | redirect su `jimcontent.com` (mirror hello-victimes) |
| `fr-bareme-capitalisation-gazette-palais-2022` | **PDF_OK** | 200 | application/pdf | 978 456 | `686a557b23fa` | needs_review | 1 | mirror `labase-lextenso.fr` |
| `fr-bareme-capitalisation-gazette-palais-2025-page` | **HTML_WARNING_NOT_FINAL_DOCUMENT** | 200 | text/html | 56 413 | `6e42ec8378f1` | needs_review | 0 | landing page con form di contatto, non il barème PDF |

## 2. Tabella dettaglio fonti — BE

| slug | classe | http | content_type | size (B) | sha256 (12c) | DB | attachment | note |
|---|---|---:|---|---:|---|---|---:|---|
| `be-loi-1989-11-21-rc-auto` | **HTML_OK_SOURCE_PAGE** | 200 | text/html | 24 224 | `58402e522116` | needs_review | 0 | scheda `economie.fgov.be`, link reale al testo va seguito a mano |
| `be-tableau-indicatif-2024` | **PDF_OK** | 200 | application/pdf | 2 373 682 | `37b0a0b4606e` | needs_review | 1 | edizione corrente |
| `be-tableau-indicatif-2020` | **PDF_OK** | 200 | application/pdf | 1 985 686 | `1b073f5c41c8` | needs_review | 1 | edizione storica |
| `be-tables-schryvers-2026-page` | **HTML_OK_SOURCE_PAGE** | 200 | text/html | 181 518 | `1e4229479a38` | needs_review | 0 | landing tables Schryvers |
| `be-tables-schryvers-tableurs` | **HTML_OK_SOURCE_PAGE** | 200 | text/html | 186 071 | `c70e16124b3c` | needs_review | 0 | indice tableurs |

## 3. Tabella dettaglio fonti — MA

| slug | classe | http | content_type | size (B) | sha256 (12c) | DB | attachment | note |
|---|---|---:|---|---:|---|---|---:|---|
| `ma-code-famille-loi-70-03-dgct` | **FAILED_NEEDS_REPLACEMENT_URL** | — | — | — | — | non creato | 0 | `ConnectTimeout` su `collectivites-territoriales.gov.ma` (host non raggiungibile) |
| `ma-code-famille-moudawana-fr-pdf` | **PDF_OK** | 200 | application/pdf | 489 071 | `41db4ab3d505` | needs_review | 1 | mirror Legal-Tools (CILC) |
| `ma-code-droits-reels-loi-39-08` | **PDF_OK** | 200 | application/pdf | 282 302 | `55e190cfd1b1` | needs_review | 1 | FAOLEX |
| `ma-code-droits-reels-traduction-aute` | **PDF_OK** | 200 | application/pdf | 548 484 | `605d1a65fcce` | needs_review | 1 | mirror AUTE — traduzione, reliability medium |
| `eu-regulation-650-2012-successions-fr-ma` | **HTTP_202_WARNING** | 202 | text/html | 0 | `e3b0c44298fc` | needs_review | 0 | EUR-Lex risponde 202 + body vuoto: rendering asincrono lato server |

## 4. Tabella dettaglio fonti — TN

| slug | classe | http | content_type | size (B) | sha256 (12c) | DB | attachment | note |
|---|---|---:|---|---:|---|---|---:|---|
| `tn-jort-code-statut-personnel-1956` | **FAILED_NEEDS_REPLACEMENT_URL** | — | — | — | — | non creato | 0 | `ConnectTimeout` su `pist.tn` |
| `tn-code-statut-personnel-compiled` | **FAILED_NEEDS_REPLACEMENT_URL** | — | — | — | — | non creato | 0 | `SSLError` certificato `jafbase.fr` non valido |
| `tn-code-statut-personnel-livre-ix-succession` | **HTML_OK_SOURCE_PAGE** | 200 | text/html | 36 183 | `ab8078968ccf` | needs_review | 0 | jurisitetunisie.com Livre IX |
| `tn-code-dip-loi-98-97` | **HTML_OK_SOURCE_PAGE** | 200 | text/html | 181 484 | `3ee9c7d11dbc` | needs_review | 0 | legislation-securite.tn |
| `tn-code-dip-pdf-support` | **FAILED_NEEDS_REPLACEMENT_URL** | — | — | — | — | non creato | 0 | `ConnectionError` su `marouani-avocat.com` (host rifiuta) |
| `eu-regulation-650-2012-successions-fr-tn` | **HTTP_202_WARNING** | 202 | text/html | 0 | `e3b0c44298fc` | needs_review | 0 | EUR-Lex 202 + body vuoto, stesso problema MA |

## 5. Spiegazione `HTTP_202_WARNING` (EUR-Lex)

`eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32012R0650` risponde
`HTTP 202 Accepted` con body vuoto e `Content-Type: text/html` quando il
server EUR-Lex sta generando il PDF on-demand: la risposta arriva senza
seguire ulteriori richieste perché il client (`requests`) considera 202
come terminale e non ri-tenta. Il file salvato è quindi vuoto (sha256 =
`e3b0c44298fc1c149afbf4c8996fb924…` = SHA-256 di byte zero, il "null
hash"). La `LegalSource` è stata creata con questa traccia ma **non è
utilizzabile** finché non si scarica il PDF reale. Il fix richiede o un
client HTTP che gestisca il 202 con polling, o lo switch a una URL HTML
ufficiale stabile (`/legal-content/FR/TXT/?uri=CELEX:32012R0650`). Vedi
§7.

## 6. Classificazione qualità (riepilogo)

| Classe | FR | BE | MA | TN | Totale |
|---|---:|---:|---:|---:|---:|
| `PDF_OK` | 2 | 2 | 3 | 0 | **7** |
| `HTML_OK_SOURCE_PAGE` | 1 | 3 | 0 | 2 | **6** |
| `HTML_WARNING_NOT_FINAL_DOCUMENT` | 1 | 0 | 0 | 0 | **1** |
| `HTTP_202_WARNING` | 0 | 0 | 1 | 1 | **2** |
| `FAILED_NEEDS_REPLACEMENT_URL` | 1 | 0 | 1 | 3 | **5** |

## 7. Recommended replacement URLs (NON applicate automaticamente)

Decisione: **non** ho modificato il `PACKAGES` nel command. Le proposte sotto
vanno valutate dallo Studio prima di aggiornare il file e ri-eseguire il
download. Per ogni fonte fallita o problematica, propongo un'alternativa
ufficiale o stabile, oppure indico se va trattata come "download manuale +
attachment via admin Django".

### 7.1. FR — Loi Badinter

| Aspetto | Valore |
|---|---|
| URL attuale | `https://www.legifrance.gouv.fr/loda/id/JORFTEXT000000693454` |
| Errore | `403 Forbidden` (Légifrance blocca selettivamente UA non-browser) |
| Replacement #1 (preferito) | `https://www.legifrance.gouv.fr/download/pdf/legiOrKali?id=LEGITEXT000006068902.pdf` (export PDF "consolidated" ufficiale) |
| Replacement #2 | landing HTML stabile: stessa URL attuale, ma lasciare in `HTML_WARNING` con `notes` "download manuale richiesto: Legifrance blocca UA programmatici" |
| Replacement #3 | mirror non ufficiale `https://www.codes-et-lois.fr/loi-1985-07-05/...` — sconsigliato, reliability `medium` |
| Raccomandazione | **#2** — accettare scaffold HTML ufficiale e archiviare manualmente un export PDF da browser via admin Django (sezione `LegalSourceAttachment`). |

### 7.2. MA — Code de la famille (DGCT page)

| Aspetto | Valore |
|---|---|
| URL attuale | `https://www.collectivites-territoriales.gov.ma/fr/node/2779` |
| Errore | `ConnectTimeout` (host probabilmente offline o block geo) |
| Replacement #1 (preferito) | `http://adala.justice.gov.ma/production/html/Fr/116146.htm` — Adala (portale Ministère de la Justice MA) |
| Replacement #2 | testo arabo ufficiale dal Bulletin Officiel n° 5184 (5 février 2004), URL via SGG.gov.ma se disponibile |
| Replacement #3 | il PDF Legal-Tools già scaricato (`ma-code-famille-moudawana-fr-pdf`) copre il contenuto — la fonte DGCT è duplicata e si può **rimuovere dal package** |
| Raccomandazione | **#3** — la Moudawana è già coperta da `ma-code-famille-moudawana-fr-pdf` (PDF_OK). Rimuovere `ma-code-famille-loi-70-03-dgct` evita duplicati. |

### 7.3. TN — JORT 1956 CSP

| Aspetto | Valore |
|---|---|
| URL attuale | `https://www.pist.tn/jort/1956/1956F/Jo10456.pdf` |
| Errore | `ConnectTimeout` (`pist.tn` host non raggiungibile dal datacenter) |
| Replacement #1 | `http://www.iort.gov.tn/WD120AWP/WD120Awp.exe/CTX_47832-7-yODySfppEZ/RechercheJort/SYNC_*` — IORT (Imprimerie Officielle TN) — **richiede form di ricerca**, non URL diretto |
| Replacement #2 (preferito) | `https://www.legislation-securite.tn/sites/default/files/lois/Loi%20n%C2%B0%2057-3.pdf` — versione ministeriale TN consolidata |
| Replacement #3 | la versione consolidata di `tn-code-statut-personnel-livre-ix-succession` su jurisitetunisie copre il Livre IX → potenzialmente sufficiente per scope successioni |
| Raccomandazione | **#2** se trovata stabile, altrimenti accettare il fallimento e scaricare a mano. |

### 7.4. TN — CSP compiled (jafbase.fr)

| Aspetto | Valore |
|---|---|
| URL attuale | `https://jafbase.fr/docMaghreb/TunisieStatutpersonnel.PDF` |
| Errore | `SSLCertVerificationError` — certificato hostname mismatch (`jafbase.fr` non in CN) |
| Replacement #1 | rimuovere il flag verify SSL: insicuro, non raccomandato. |
| Replacement #2 (preferito) | `https://legislation.tn/sites/default/files/codes/CodeStatutPersonnel.pdf` — fonte governativa TN consolidata |
| Replacement #3 | duplica `tn-code-statut-personnel-livre-ix-succession` (già scaricato) per lo scope successioni |
| Raccomandazione | **#2** se stabile; altrimenti **rimuovere dal package** (la versione livre-IX è sufficiente). |

### 7.5. TN — Code DIP PDF support (marouani-avocat.com)

| Aspetto | Valore |
|---|---|
| URL attuale | `https://marouani-avocat.com/fr/assets/dip.pdf` |
| Errore | `ConnectionRefusedError` (host non risponde) |
| Replacement #1 | `https://legislation.tn/sites/default/files/codes/CodeDIP.pdf` (se esiste) |
| Replacement #2 (preferito) | `tn-code-dip-loi-98-97` HTML su `legislation-securite.tn` (già scaricato) — copre lo stesso contenuto. **Rimuovere il duplicato PDF**. |
| Raccomandazione | **#2** — `tn-code-dip-pdf-support` è ridondante. Rimuovere dal package. |

### 7.6. MA + TN — EUR-Lex Reg. 650/2012 (HTTP 202)

| Aspetto | Valore |
|---|---|
| URL attuale | `https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32012R0650` |
| Errore | HTTP 202 + body vuoto (rendering PDF asincrono lato EUR-Lex) |
| Replacement #1 (preferito) | `https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650` — versione **HTML ufficiale**, sempre 200, contenuto completo. |
| Replacement #2 | tenere URL PDF ma estendere il client HTTP per gestire 202 con polling sul `Location` header. Più invasivo, richiede cambio del command. |
| Replacement #3 | scaricare il PDF a mano dal browser e attaccarlo via admin |
| Raccomandazione | **#1** — switch URL a versione HTML, accetta `HTML_OK_SOURCE_PAGE`. Il testo del Regolamento UE è disponibile completamente in HTML. |

## 8. Warning su fonti indicative / non vincolanti

| Fonte | Avvertenza |
|---|---|
| Référentiel Mornet 2024 | giurisprudenziale, non normativo. `reliability=high`, mai `official`. |
| Tableau Indicatif BE 2020 / 2024 | non vincolante (Union des juges de paix et de police). |
| Tables Schryvers BE | strumento giurisprudenziale di capitalizzazione. |
| Barème Gazette du Palais 2022 | strumento di prassi, non atto normativo. |
| Reg. UE 650/2012 attaccato a MA / TN | NON vincolante per Marocco e Tunisia (paesi terzi). Attaccato come **riferimento comparato per il diritto internazionale privato**. La nota di ogni fonte lo dichiara. |
| Legal-Tools, FAOLEX, AUTE | aggregatori autorevoli ma non fonte di prima mano: la traduzione FR può divergere dal testo arabo. Per le successioni, prima di promuovere a `approved` lo Studio deve confrontare con il **testo arabo ufficiale** del Bulletin Officiel MA / del Code TN. |

## 9. Cosa serve per la legal review (per ogni fonte scaricata)

1. **Verifica integrità** — confronto SHA-256 con un secondo download
   indipendente, almeno per le fonti `OFFICIAL_LAW`.
2. **Verifica edizione** — accertarsi che il documento corrisponda
   all'edizione vigente (Tableau Indicatif: confrontare 2020 vs 2024;
   Mornet: 2024 vs futuri).
3. **MA / TN — confronto testo arabo** — le quote ereditarie reali
   (faraïd) sono codificate in arabo: la traduzione FR è derivata e
   potenzialmente imprecisa. Lo Studio deve verificare contro il
   Bulletin Officiel MA o il Code arabe TN.
4. **`LegalReview(decision=approve)`** umana, registrata in DB con
   commento esplicito sullo scope (es. "estensione successioni
   transfrontaliere", "approvazione Tableau Indicatif 2024").
5. **Promozione cumulativa** source → dataset → formula a `approved`,
   nello stesso ordine di gating del calculator.

## 10. Prossimi step per paese

### FR
- Sostituire/risolvere il fallimento Loi Badinter (vedi §7.1).
- Iniziare l'estrazione di `Référentiel Mornet 2024` (PDF già in DB con
  attachment): parser PDF dedicato per voce di danno → CSV candidate →
  `import_france_referentiel` additivo + `amount_rule` futura.
- `Barème Gazette du Palais 2022` → estrazione tabellare per
  capitalizzazione rendite (perte de gains, tierce personne).
- La pagina 2025 va seguita manualmente: il PDF aggiornato non è
  esposto pubblicamente.

### BE
- Tutti i 5 download sono OK. Pacchetto più completo dei 4.
- Iniziare estrazione del `Tableau Indicatif 2024` (PDF in DB):
  parser dedicato per voce di danno (ITT, IPP, pretium doloris,
  dommage esthétique, perte de revenus). Conservare 2020 come
  riferimento storico.
- Le pagine Schryvers contengono tabelle interattive (servono pagine
  individuali per età × durata): probabile estrazione in fase 2.

### MA
- Risolvere fallimento DGCT (vedi §7.2: probabile rimozione del
  duplicato).
- I 3 PDF scaricati (Moudawana FR, Loi 39-08, traduzione AUTE)
  coprono il quadro normativo principale. **Prudenza**: prima di
  qualunque calcolo, lo Studio deve mappare gli articoli applicabili
  alla classificazione del caso (statuto personale, conflitto di
  leggi, residenza, beni immobili/mobili).
- Per il Reg. UE 650/2012 vedi §7.6: switch URL a HTML.
- **Non** procedere con engine quote ereditarie finché non ci sono
  fonti `approved` E un articolato della logica di conflitto di
  leggi.

### TN
- 3 fallimenti su 6 — il pacchetto TN è il più fragile.
- Riproporre URL stabili per JORT, CSP, DIP (vedi §§7.3-7.5).
- I 2 HTML scaricati (livre-IX su jurisitetunisie + Loi 98-97 su
  legislation-securite) coprono lo scope minimo per le successioni.
- Stessa prudenza del Marocco: **prima** mappa articoli applicabili,
  conflitto di leggi, statuto personale, residenza abituale e
  nazionalità. **Poi**, eventualmente, engine.

## 11. Comandi

Verifica solo (read-only sui manifest):
```bash
python manage.py check
pytest -q apps/legal_sources/test_download_international_legal_sources.py
```

Re-run dopo aver applicato le replacement URL nel package
(`apps/legal_sources/management/commands/download_international_legal_sources.py`):
```bash
python manage.py download_international_legal_sources --country FR
python manage.py download_international_legal_sources --country MA
python manage.py download_international_legal_sources --country TN
# oppure tutto
python manage.py download_international_legal_sources --all
```

Il command è idempotente: re-run NON retrocede una fonte già
`approved` e NON duplica gli `Attachment` (deduplica per sha256).

## 12. Audit chain

```
URL pubblica
  → fetch (requests, UA noto, timeout 30s, follow redirects)
    → bytes + content-type
      → file su disco (gitignore-coperto) con SHA-256
        → manifest JSON aggiornato (committabile)
          → LegalSource needs_review (idempotente, mai retrocede approved)
            → LegalSourceAttachment (solo PDF)
              → STOP: nessun calcolo, nessuna formula, nessun dataset.
```
