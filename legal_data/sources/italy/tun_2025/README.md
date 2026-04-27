# D.P.R. 13 gennaio 2025, n. 12 — Tabella Unica Nazionale danno biologico

Cartella di lavoro per il caricamento e l'estrazione tabellare della
**Tabella Unica Nazionale** prevista dall'art. 138 del Codice delle
Assicurazioni Private (D.Lgs. 209/2005), introdotta dal D.P.R. 12/2025.

## Materiale atteso (NON committato)

| File | Origine | Stato | Note |
|---|---|---|---|
| `dpr_12_2025_tun.pdf` | [Gazzetta Ufficiale n. 40 del 18/02/2025, S.O. n. 4](https://www.gazzettaufficiale.it/eli/id/2025/02/11/25G00018/sg) | da scaricare | versione di riferimento dell'estrazione |
| `tun_2025_rows.csv` | estrazione manuale dello Studio | da produrre | una riga per ogni voce della tabella |
| `extraction_notes.md` | annotazioni del revisore | opzionale | discrepanze, note marginali, errata corrige |

## 1. Scaricare il PDF

1. Visitare il link Gazzetta Ufficiale.
2. Scaricare il PDF integrale del D.P.R. n. 12/2025 + Supplemento Ordinario.
3. Salvare il file come `dpr_12_2025_tun.pdf` in questa cartella.
4. Verificare che dimensione e numero di pagine corrispondano alla
   pubblicazione G.U. (la prima estrazione registra l'hash SHA-256, le
   estrazioni successive devono confermarlo).

## 2. Allegare il PDF alla LegalSource

```
python manage.py import_italy_tun_2025 \
    --source-file legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf
```

Il command:
- verifica che il file esista (errore controllato altrimenti);
- calcola SHA-256, mime, size;
- crea `LegalSourceAttachment` per la fonte
  `slug=it-dpr-12-2025-tun-danno-biologico` (deve già esistere via
  `seed_italy_legal_sources`);
- crea (o aggiorna) `CompensationDataset` in stato **draft**;
- crea (o aggiorna) `CalculationFormula` documentale in stato **draft**;
- scrive un `ExtractionLog` con esito.

Il command **non** modifica lo status della fonte, del dataset o della
formula. La promozione a `approved` è un atto umano.

## 3. Estrarre le righe

Compilare `tun_2025_rows.csv` con il seguente schema:

| colonna | descrizione |
|---|---|
| `row_type` | tipologia riga: `point_value`, `multiplier_age`, `daily_temporary`, ... |
| `age_min` | età minima coperta dalla riga (intero, vuoto se non applicabile) |
| `age_max` | età massima coperta dalla riga |
| `disability_min` | percentuale di invalidità minima |
| `disability_max` | percentuale di invalidità massima |
| `point_value` | valore-punto in euro (decimal) |
| `coefficient` | coefficiente moltiplicativo (decimal) |
| `daily_amount` | importo giornaliero in euro (decimal) |
| `source_page` | pagina del PDF da cui la riga è estratta |
| `source_note` | annotazione testuale del revisore |

Importazione:

```
python manage.py import_italy_tun_2025 \
    --csv legal_data/sources/italy/tun_2025/tun_2025_rows.csv
```

Tutte le righe vengono importate in stato `draft` (tramite il dataset
proprietario).

## 4. Legal review

Lo Studio:
1. confronta riga per riga il CSV con il PDF;
2. annota eventuali discrepanze;
3. promuove `LegalSource → approved` (solo se i metadati sono coerenti);
4. promuove `CompensationDataset → approved` (solo se la fonte è approved);
5. promuove `CalculationFormula → approved` (solo se il dataset è approved).

Solo a quel punto il calculator pubblico smette di restituire
`unavailable_requires_legal_validation` e produce un range stimato.

## ATTENZIONE

- Non popolare il CSV con valori presi da blog, riviste o commentari:
  i valori devono provenire **esclusivamente** dal testo del PDF G.U.
- Non promuovere `approved` senza una `LegalReview` archiviata.
- Le **Tabelle Milano** non hanno nulla a che fare con questa cartella:
  la TUN è ministeriale e nazionale; le Milano sono giurisprudenziali e
  vivono come `court_table` separata.
