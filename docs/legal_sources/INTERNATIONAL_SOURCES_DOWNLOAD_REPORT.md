# International legal sources — download report

> Living document. Da aggiornare a ogni esecuzione di
> `python manage.py download_international_legal_sources`.
> Lo scaffold di questo report è committato; le tabelle dettagliate
> per esecuzione si popolano dai manifest JSON nelle cartelle
> `legal_data/sources/<country>/downloaded/`.

## 0. Status

| Paese | Comando | Esecuzione | OK | FAIL | Manifest |
|---|---|---|---:|---:|---|
| FR | `download_international_legal_sources --country FR` | _da eseguire_ | — | — | `legal_data/sources/france/downloaded/download_manifest.json` |
| BE | `download_international_legal_sources --country BE` | _da eseguire_ | — | — | `legal_data/sources/belgium/downloaded/download_manifest.json` |
| MA | `download_international_legal_sources --country MA` | _da eseguire_ | — | — | `legal_data/sources/morocco/downloaded/download_manifest.json` |
| TN | `download_international_legal_sources --country TN` | _da eseguire_ | — | — | `legal_data/sources/tunisia/downloaded/download_manifest.json` |

## 1. Cosa fa il command

`apps/legal_sources/management/commands/download_international_legal_sources.py`:

1. Per ogni item del package del paese (4 set hardcoded nel file):
   - scarica l'URL via `requests` (User-Agent
     `StudioLegaleBadrane-LegalSourceDownloader/0.1`, follow redirects,
     timeout 30s);
   - determina l'estensione da Content-Type (PDF / HTML / fallback bin);
   - salva in `legal_data/sources/<country>/downloaded/<slug>.<ext>`;
   - calcola SHA-256 + size;
   - upsert `LegalSource` (sempre `needs_review` per le nuove; mai
     retrocede una fonte già `approved`);
   - per i PDF crea/aggiorna `LegalSourceAttachment`;
   - per HTML resta solo file su disco + entry nel manifest (le pagine
     web sono spesso JS-heavy, non sono il documento normativo).
2. Persiste un manifest JSON con tutto: slug, URL originale, URL finale
   dopo redirect, http_status, content_type, local_path, sha256,
   size_bytes, downloaded_at, country/jurisdiction/language/source_type/
   reliability/status, notes, error.
3. Una richiesta fallita NON interrompe il batch: l'entry resta nel
   manifest con `error` valorizzato e si passa alla successiva.

Garanzie:
- nessun `CompensationDataset` o `CalculationFormula` toccato;
- nessuna `LegalReview` creata;
- nessuna fonte promossa a `approved`;
- gitignore copre PDF/HTML scaricati: solo manifest + report sono
  committabili.

## 2. Manifest schema

```json
{
  "country": "FR",
  "generated_at": "<ISO-8601 UTC>",
  "user_agent": "StudioLegaleBadrane-LegalSourceDownloader/0.1",
  "succeeded": 5,
  "failed": 0,
  "items": [
    {
      "slug": "fr-loi-badinter-1985",
      "title": "Loi n°85-677 du 5 juillet 1985 dite Loi Badinter",
      "source_url": "<original URL>",
      "final_url": "<URL after redirects>",
      "http_status": 200,
      "content_type": "application/pdf",
      "local_path": "legal_data/sources/france/downloaded/fr-loi-badinter-1985.pdf",
      "sha256": "<64 hex chars>",
      "size_bytes": 0,
      "downloaded_at": "<ISO-8601 UTC>",
      "country": "FR",
      "jurisdiction": "FR-NATIONAL",
      "language": "fr",
      "source_type": "official_law",
      "reliability": "official",
      "status": "needs_review",
      "notes": "Downloaded metadata only. Requires Studio legal review before any calculation.",
      "error": ""
    }
  ]
}
```

`error` è non vuoto solo quando il fetch o la persistenza falliscono.

## 3. Pacchetti scaricati per paese

### FR — 5 item
1. `fr-loi-badinter-1985` — Loi n°85-677 du 5 juillet 1985 (LegiFrance HTML).
2. `fr-nomenclature-dintilhac-2005` — Rapport Dintilhac (page Justice).
3. `fr-referentiel-mornet-2024` — Référentiel Mornet 2024 (PDF).
4. `fr-bareme-capitalisation-gazette-palais-2022` — Barème GP 2022 (PDF).
5. `fr-bareme-capitalisation-gazette-palais-2025-page` — landing page GP 2025.

### BE — 5 item
1. `be-loi-1989-11-21-rc-auto` — Loi RC auto 1989 (FGOV HTML).
2. `be-tableau-indicatif-2024` — Tableau Indicatif 2024 (PDF).
3. `be-tableau-indicatif-2020` — Tableau Indicatif 2020 (PDF).
4. `be-tables-schryvers-2026-page` — Schryvers landing.
5. `be-tables-schryvers-tableurs` — Schryvers tableurs.

### MA — 5 item (focus successioni)
1. `ma-code-famille-loi-70-03-dgct` — DGCT page (HTML).
2. `ma-code-famille-moudawana-fr-pdf` — Moudawana FR via Legal-Tools (PDF).
3. `ma-code-droits-reels-loi-39-08` — Loi 39-08 via FAOLEX (PDF).
4. `ma-code-droits-reels-traduction-aute` — traduzione AUTE (PDF).
5. `eu-regulation-650-2012-successions-fr-ma` — Reg. UE 650/2012 (PDF eur-lex).

### TN — 6 item (focus successioni)
1. `tn-jort-code-statut-personnel-1956` — JORT 1956 (PDF).
2. `tn-code-statut-personnel-compiled` — CSP compiled (PDF jafbase).
3. `tn-code-statut-personnel-livre-ix-succession` — Livre IX (HTML).
4. `tn-code-dip-loi-98-97` — Loi 98-97 (HTML).
5. `tn-code-dip-pdf-support` — PDF support (PDF marouani-avocat).
6. `eu-regulation-650-2012-successions-fr-tn` — Reg. UE 650/2012 (PDF eur-lex).

## 4. Warning: fonti indicative / non vincolanti

| Fonte | Avvertenza |
|---|---|
| Référentiel Mornet 2024 | giurisprudenziale, non normativo. `reliability=high`, mai `official`. |
| Tableau Indicatif BE 2020/2024 | non vincolante (Union des juges de paix et de police). |
| Schryvers tables BE | strumento giurisprudenziale; vita tariffaria specifica. |
| Barème Gazette du Palais 2022/2025 | strumento di prassi, non atto normativo. |
| Reg. UE 650/2012 in pacchetti MA/TN | NON vincolante (entrambi i paesi non lo applicano direttamente). Attaccato come **riferimento comparato**, non come fonte primaria. |
| Loi-Tools, FAOLEX, AUTE | aggregatori autorevoli ma non fonte ufficiale di prima mano: la traduzione FR può divergere dal testo arabo. |

Per **ogni** fonte, `notes` riporta:
> *Downloaded metadata only. Requires Studio legal review before any calculation.*

## 5. Cosa serve per la legal review

Per ogni fonte scaricata, prima di poter promuovere a `approved`:

1. **Verifica integrità** — confronta SHA-256 nel manifest con un
   secondo download dalla stessa URL (almeno per le fonti su
   eur-lex.europa.eu, justice.gouv.fr, legifrance.gouv.fr,
   ejustice.just.fgov.be).
2. **Verifica versione** — accertarsi che il documento corrisponda
   all'edizione più aggiornata (alcune URL possono linkare versioni
   storiche, es. Tableau Indicatif 2020 vs 2024).
3. **Confronto con testo arabo** (MA/TN solo): per le fonti in fr
   tradotte, verificare la corrispondenza con la versione araba
   ufficiale prima di trascrivere quote ereditarie.
4. **`LegalReview(decision=approve)`** umana, registrata in DB,
   commentando esplicitamente lo scope (es. "estensione successioni
   transfrontaliere").
5. **Promozione cumulativa** source → dataset → formula a `approved`,
   nello stesso ordine di gating del calculator.

## 6. Prossimi step per FR / BE / MA / TN

### FR / BE — base più rapida
La struttura per voce di danno (DFP, SE, PE, ITT, IPP, perte de
revenus, ecc.) è ben tracciata in Mornet 2024 e Tableau Indicatif 2024.
Dopo legal review è realisticamente possibile:
1. estrarre le tabelle (parser PDF dedicato);
2. importare additivamente in dataset DRAFT (es. version_label
   `MORNET-2024` / `TABLEAU-INDICATIF-2024`);
3. introdurre una `amount_rule` `referentiel_indicatif_per_head_of_loss`;
4. attivare il range pubblico FR/BE post promozione.

### MA / TN — prudenza
La materia successoria coinvolge:
- conflitto di leggi (residenza abituale vs nazionalità vs scelta
  expressa via testamento);
- status personale (matrimonio, filiazione, ripudio, riconoscimento);
- categoria dei beni (mobili / immobili) e loro localizzazione;
- coordinamento con il Reg. UE 650/2012 quando applicabile (residenza
  EU del defunto).

Lo Studio deve **prima** consolidare gli articoli applicabili (Livre III
Moudawana, Livre IX CSP, CDIP TN, ipoteticamente Reg. UE 650/2012).
**Solo dopo** si può iniziare a parlare di engine quote ereditarie.
Un calcolatore reale richiederà una `amount_rule` specifica e un
dataset che mappi ogni combinazione (genere/parentela/coniuge/figli/
genitori/...) → quota — struttura più complessa di una tabella età ×
invalidità tipica della TUN italiana.

## 7. Comandi

Verifica solo:
```
python manage.py check
pytest -q apps/legal_sources/test_download_international_legal_sources.py
```

Esecuzione reale (richiede connessione internet, scrive su disco e DB):
```
python manage.py download_international_legal_sources --country FR
python manage.py download_international_legal_sources --country BE
python manage.py download_international_legal_sources --country MA
python manage.py download_international_legal_sources --country TN
# oppure tutto in un colpo
python manage.py download_international_legal_sources --all
```

Dopo l'esecuzione, il manifest è in
`legal_data/sources/<country>/downloaded/download_manifest.json`. I
PDF/HTML scaricati restano sul disco locale e NON vanno committati
(coperti da `.gitignore`).

## 8. Audit chain riassuntivo

```
URL pubblica
  → fetch (requests, UA noto, timeout 30s, follow redirects)
    → bytes + content-type
      → file su disco con SHA-256
        → manifest JSON aggiornato
          → LegalSource needs_review (idempotente)
            → LegalSourceAttachment (solo PDF)
              → STOP: nessun calcolo, nessuna formula, nessun dataset.
```
