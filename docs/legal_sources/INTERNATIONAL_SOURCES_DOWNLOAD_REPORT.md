# International legal sources — download report

> Snapshot della prima esecuzione reale del command
> `python manage.py download_international_legal_sources`. Aggiornare
> ad ogni nuovo run. I PDF/HTML scaricati restano locali (gitignore);
> il manifest JSON è la traccia di audit canonica.

## 0. Riepilogo per paese

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
