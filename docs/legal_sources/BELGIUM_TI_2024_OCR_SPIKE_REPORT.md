# Belgium — Tableau Indicatif 2024 · OCR Spike Report

**Iter**: F-belgium-ocr-ti-2024-spike / iter1
**Stato**: read-only, candidate. Nessun import DB. Nessuna creazione di
LegalReview / CompensationDataset / CalculationFormula. Nessuna
modifica al calculator. Nessuna modifica wizard. Nessuna modifica
Italia/TUN.
**Documento**: `legal_data/sources/belgium/downloaded/be-tableau-indicatif-2024.pdf`
**Script**: `scripts/legal_data/ocr_belgium_ti_2024_spike.py` (read-only)
**Output**: `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/` (gitignored)

---

## 0. Avvertenze fondamentali

1. **Tableau Indicatif 2024 è un référentiel indicatif**, non un testo
   normativo vincolante. Pubblicato su *T.Pol./J.J.Pol. 4/2024*. Anche
   con OCR perfetto, il documento richiede approvazione legale prima di
   essere usato in un calcolo pubblico.
2. **BE 2024 è image-scanned**: 0 testo estraibile via pdfplumber su
   tutte le 23 pagine. Senza OCR, l'estrazione automatica è impossibile.
3. **Lo spike è uno proof-of-concept tecnico**, non un'estrazione
   completa. Non produce CSV finale né valori candidati per il DB.
4. **BE 2020** resta il dataset storico/fallback già estratto (iter
   F-belgium-extraction-ti-2020): 4 famiglie, 166 righe, candidate
   read-only. Lo Studio potrebbe scegliere di iniziare con la review
   2020 e aggiornare a 2024 solo dopo.

---

## 1. PDF di provenienza

| Campo | Valore |
|---|---|
| Slug | `be-tableau-indicatif-2024` |
| Path | `legal_data/sources/belgium/downloaded/be-tableau-indicatif-2024.pdf` |
| Size | 2.373.682 bytes |
| Source URL | https://docs.fcgb-bgwf.be/documents/Tabl_Ind_2024_Fr.pdf |
| SHA-256 (manifest) | `37b0a0b4606ec39638db4a81c6074928c2275a09274a11597b8fb17e03bc3a45` |
| SHA-256 (computed) | `37b0a0b4606ec39638db4a81c6074928c2275a09274a11597b8fb17e03bc3a45` |
| Match | **PASS** |
| Pubblicazione | T.Pol./J.J.Pol. 4/2024 |

---

## 2. Conferma image-scanned

Il PDF non ha alcun testo macchina:

| Metric | Valore |
|---|---|
| Pagine totali | 23 |
| Testo estraibile (somma `chars` su tutte le pagine) | **0** |
| Immagini totali (1 per pagina) | 23 |
| `is_image_scanned` | **True** |

Confermato anche via `pdfplumber` (vedi `spike_summary.json` →
`image_scanned.per_page`): ogni pagina ha `chars=0` e `images=1`.
È un PDF di sole scansioni — qualsiasi estrazione richiede OCR.

---

## 3. Tooling OCR disponibile

### 3.1 Tesseract — disponibile

| Campo | Valore |
|---|---|
| Binario | `C:\Program Files\Tesseract-OCR\tesseract.EXE` |
| Versione | 5.5.0.20241111 (leptonica-1.85.0) |
| Lingue installate | **`eng`**, `osd` |
| Lingue mancanti per BE | **`fra` mancante**, **`nld` mancante** |

### 3.2 Limitazione critica: pacchetti lingua FR/NL non installati

Tesseract è installato ma sono presenti solo i language pack `eng` e
`osd`. **`fra` e `nld` non sono installati sul sistema**. Conseguenze:

- gli accenti francesi (`é`, `è`, `à`, `ç`) sono ricostruiti da
  Tesseract come se fossero ASCII corrotti (`é` → `é`, `è` → `é`,
  `à` → `a`, `'` → `‘`);
- parole come "Lincapacité" appaiono al posto di "L'incapacité";
- "âge" diventa "age";
- "Béneficiaire" sopravvive ma molti diacritici saltano.

Per i numeri questa limitazione è meno grave — le cifre arabe sono
identiche in tutte le lingue. Quindi il digit-recognition è comunque
ragionevole, ma il riconoscimento dei **label** è rumoroso.

### 3.3 Backend di rendering

`pdfplumber.page.to_image(resolution=300)` ha funzionato senza
installare `pdf2image`/`poppler`. **Nessuna dipendenza pip aggiuntiva
è stata installata** dallo spike.

---

## 4. Pagine campione individuate

Mappatura BE 2024 ↔ BE 2020 ricostruita via OCR-recon a 150 DPI di
tutte le 23 pagine:

| BE 2024 (PDF page) | Famiglia | Equivalente BE 2020 |
|---|---|---|
| **p.9** | Préjudice esthétique permanent (Julin × age band) | p.17 «Souffrances endurées» (stessa shape Julin × age) |
| p.12 | Indemnité forfaitaire / age (€/anno per 1% incapacité) | p.22-23 (stessa shape per_age) |
| **p.14** | Décès / préjudice d'affection | p.26 (BE 2020 aveva 13 righe, BE 2024 ne ha 5) |
| **p.17** | Véhicule de remplacement | p.32 |

Le pagine **9, 14, 17** sono state selezionate come spike rappresentativo
di tre tipologie strutturali distinte (matrice densa, mini-tabella
sparsa, lista veicoli con sub-righe).

---

## 5. Esecuzione OCR

### 5.1 Parametri

| Parametro | Valore |
|---|---|
| Risoluzione di rendering | 300 DPI |
| Backend rendering | `pdfplumber.page.to_image` |
| Engine OCR | Tesseract 5.5.0 |
| Lingua OCR | `eng` (fallback per assenza `fra`/`nld`) |
| PSM (page segmentation mode) | **4** — single column variable sizes |

### 5.2 Confronto PSM 6 vs PSM 4 (lesson learned dello spike)

Il primo run con `--psm 6` («uniform block of text») è stato
**deludente** sulle tabelle sparse:

- **p.14 (décès)** PSM 6 → cattura solo **2/5** righe della tabella
  (perde le righe `Partenaires`, `Frères/sœurs`, `Fausse couche`).
- **p.17 (véhicule)** PSM 6 → perde le righe `bicyclette`, `2 ou 3 roues`,
  e l'header «Véhicule | Indemnité/jour».
- **p.9 (esthétique)** PSM 6 → cattura quasi tutto ma perde l'header
  «1/7 ... 7/7» e la prima colonna `620 euros` per la riga 0-10.

Con `--psm 4` («single column of text of variable sizes») la qualità
migliora drasticamente:

- **p.14**: cattura tutte e 5 le righe + header.
- **p.17**: cattura header + tutte le righe veicolo + sub-righe autobus.
- **p.9**: cattura tutte le 9 fasce d'età × 7 colonne di severità.

Lo script ufficiale (`ocr_belgium_ti_2024_spike.py`) usa quindi PSM 4.

### 5.3 Metriche grezze (PSM 4 / 300 DPI / lang=eng)

| Pagina | Righe non vuote | "euros" hit | Amounts detected | Digit/line |
|---|---|---|---|---|
| p.9 esthétique | 42 | 63 | 107 | 2.45 |
| p.14 décès | 43 | 12 | 28 | 0.58 |
| p.17 véhicule | 43 | 25 | 56 | 1.26 |

Esiti dei controlli "famiglia-specifici":

- p.9 — fasce d'età rilevate: 8/9 (la riga "81 et plus" è splittata su
  due linee `81 et\nplus`, ma è presente; il regex 8 era
  conservativo).
  Severity labels rilevate: `minime, trésléger (fuso), léger, moyen,
  grave, exception(nellement)`. ✅ tutte e 7 sono presenti, alcune con
  spazi persi.
- p.14 — relation keyword rilevate: `partenaire, parents, enfants,
  soeurs, grands-parents, petits-enfants, fausse couche`. ✅ tutte e 5
  le righe della tabella sono presenti.
- p.17 — vehicle keyword rilevate: `bicyclette, remorque, voiture, moto,
  camion, autobus, tracteur, pédélec, quad, speed`. ✅ vocabolario
  completo.

---

## 6. Qualità OCR per pagina (analisi qualitativa)

### 6.1 p.9 — Préjudice esthétique permanent (Julin × age band)

**Struttura**: matrice 9 fasce d'età × 7 livelli Julin (1/7 ... 7/7) =
63 celle euro.

**Quality**: ottima per le cifre. Esempio diretto:

```
0-10  | 620 euros | 2.470 euros | 5.580 euros | 9.920 euros | 17.250 euros | 23.000 euros | 34.500 euros
11-20 | 600 euros | 2.390 euros | 5.405 euros | 9.545 euros | 16.675 euros | 22.140 euros | 33.350 euros
21-30 | 565 euros | 2.300 euros | 5.060 euros | 9.030 euros | 15.755 euros | 20,990 euros | 31.625 euros  ← virgola sbagliata
31-40 | 520 euros | 2.070 euros | 4.715 euros | 8.340 euros | 14.490 euros | 19.320 euros | 29.040 euros
41-50 | 460 euros | 1.840 euros | 4.140 euros | 7.475 euros | 12.880 euros | 17.135 euros | 25.590 euros
51-60 | 400 euros | 1.610 euros | 3.565 euros | 6.380 euros | 11.155 euros | 14.835 euros | 22.425 euros
61-70 | 320 euros | 1.265 euros | 2.990 euros | 5.060 euros | 8.910  euros | 11.900 euros | 17,825 euros  ← virgola sbagliata
71-80 | 230 euros |   920 euros | 2.015 euros | 3.565 euros | 6.325 euros | 8.395 euros | 12.650 euros
81 et |
plus  | 130 euros |   520 euros | 1.210 euros | 2.130 euros | 3.680 euros | 4.890 euros | 7.360 euros
```

**Errori osservati**:

- 2 occorrenze di virgola al posto del punto come separatore migliaia
  (`20,990` e `17,825`). Convenzione belga: punto = migliaia, virgola
  = decimali. `20,990` è ambiguo — letteralmente sarebbe €20.99 ma è
  in realtà €20990. Un normalizzatore deterministico **non può**
  distinguerlo senza euristica (es. controllare che la cifra abbia
  esattamente 3 decimali → migliaia).
- Riga `81 et / plus` è splittata su due linee — il parser dovrebbe
  ricomporre.
- Header severity rilevato come `minime | trésléger | léger | moyen |
  grave | trés grave | exception- / nellement / grave` — leggermente
  sporco ma riconoscibile.
- Header colonne `1/7 ... 7/7` rilevato correttamente come
  `W/7 2/7 3/7 4/7 5/7 6/7 Vif` — alcune cifre fuse o lette male
  (1→W, 7→V), ma posizionalmente affidabile.

**Confronto BE 2020 (per memoria)**: BE 2020 p.17 spot-check:
0-10 / 1-7 = 540 €, 0-10 / 7-7 = 30.000 €.
BE 2024 p.9 (presunti): 0-10 / 1-7 = 620 €, 0-10 / 7-7 = 34.500 €.
**I valori 2024 sono ~15% più alti** rispetto al 2020. È coerente con un
aggiornamento di indicizzazione su 4 anni e va verificato dallo Studio
prima di essere considerato approved.

### 6.2 p.14 — Décès / préjudice d'affection

**Struttura**: tabella 5 relazioni × (min, max).

**Quality**: la tabella compare interamente:

```
Victime décédée/Béneficiaire | minimum | maximum
Partenaires                  | 15,000 euros | 45,000 euros   ← virgole sbagliate
Parents/enfants              | 15.000 euros | 45.000 euros
Fréres/soeurs                | 7,500 euros  | 25,000 euros   ← virgole sbagliate
Grands-parents/Petits-enfants| 7.500 euros  | 25.000 euros
Fausse couche                | 3.000 euros  | 9,000 euros    ← seconda virgola sbagliata
```

**Errori osservati**:

- Virgola usata al posto del punto come separatore migliaia in **3 righe
  su 5 (60%)**. Pattern non sistematico — la stessa cifra "15000"
  è una volta `15,000` (Partenaires) e una volta `15.000`
  (Parents/enfants). Questo è il rischio principale dell'OCR su
  cifre belghe: la disambiguazione comma/period è critica.
- Header rilevato correttamente.
- Confronto BE 2020 (13 relazioni): BE 2024 ha **solo 5 relazioni**
  contro 13 del 2020. Lo Studio deve verificare se in 2024 è stata
  effettivamente fatta una semplificazione, o se le altre relazioni
  sono in un'altra pagina del PDF non ancora ispezionata.

### 6.3 p.17 — Véhicule de remplacement

**Struttura**: lista ~15 tipi di veicolo con `Indemnité/jour`, sub-righe
per remorque (<750/≥750), camions (formula), autobus (5 fasce di
posti).

**Quality**: ottima per la tabella veicoli, con qualche distorsione di
caratteri matematici:

```
Véhicule                                              | Indemnité/jour
bicyclette (avec/sans assistance, max. 25 km/h)       | 12,00 euros
2 ou 3 roues motorisées, quad et speed pédélec        | 17,00 euros
remorque de voiture de:
  - moins de 750 kg                                   | 12,00 euros
  - plus de 750 kg                                    | 17,00 euros
voitures (également usage professionnel et de leasing)| 23,00 euros
mobilhome                                             | 58,00 euros
taxi grandes entreprises                              | 58,00 euros
taxi exploitant indépendant                           | 69,00 euros
voiture de location (hors leasing)                    | 53,00 euros
camionnettes et petits camions
  jusqu'à 3,5 t, charge utile                         | 46,00 euros
camions et véhicules tractés de 3,5 t et plus,
  nettes de charge                                    | 58,00 euros + 12,00 euros par tonne
propriétaire d'un seul camion                         | 72,00 euros
véhicules lourds de nature particuliére (...)         | 173,00 euros
ambulance                                             | 100,00 euros
remorque de camping/caravane                          | 28,00 euros
autobus / autocar:
  < 50 places (< 31 places)                           | 58,00 euros
  ≥ 50 places (≥ 31 places)                           | 103,00 euros   ← OCR: «2 50»
  ≥ 60 places (≥ 38 places)                           | 132,00 euros   ← OCR: «2 60»
  ≥ 70 places (≥ 44 places)                           | 161,00 euros   ← OCR: «= 70»
  ≥ 80 places (≥ 50 places)                           | 207,00 euros   ← OCR: «= 80»
```

**Errori osservati**:

- I simboli `≥` (Unicode "greater-than-or-equal") sono OCR-letti come
  `2` (in alcune righe) o `=` (in altre). Un parser deve riconoscerli e
  riconvertirli, oppure lo Studio deve correggere manualmente.
- Apostrofi tipografici (`'`, `'`) talvolta letti come `‘` o omessi.
- La formula `58,00 euros + 12,00 euros par tonne` è splittata su 3
  linee diverse; un parser deve ricomporla.
- I valori `,00` (centesimi) sono sempre formattati correttamente
  (`12,00`, `17,00`, `46,00`, ...). Per gli importi senza migliaia
  l'OCR è affidabile.
- Confronto BE 2020 (19 codici veicolo): BE 2024 ha lo stesso numero
  di tipologie e identica struttura — l'aggiornamento sembra essere
  solo di importi.

---

## 7. Esempi di errori sistematici (sintesi)

| Tipo errore | Frequenza | Esempi | Recupero automatico? |
|---|---|---|---|
| Virgola al posto del punto come separatore migliaia | ~5-10% degli importi | `15,000 euros`, `20,990 euros`, `17,825 euros` | **Difficile** — ambiguo con valore decimale |
| `≥` letto come `2` o `=` | 4 occorrenze su p.17 | `2 50 places`, `= 70 places` | Sì, con regex |
| Diacritici francesi persi | sistematico | `é` → ASCII corrotto, `à` → `a` | Sì, ma servono `fra` lang pack |
| Apostrofo tipografico → ASCII | sistematico | `L'incapacité` → `Lincapacité` | Sì |
| Riga splittata su 2 linee (cella multi-riga) | ~10% delle righe complesse | `81 et\nplus`, `58,00 euros + 12,00 euros par\ntonne` | Sì, con join euristico |
| Header tabella perso o degradato | 1/3 delle pagine | `1/7` → `W/7`, `7/7` → `Vif` | Parziale |
| Colonna intera persa (con PSM 6) | 0% con PSM 4 | (eliminato cambiando PSM) | n/a |

---

## 8. Confronto con schema BE 2020

| Famiglia | BE 2020 (estratto) | BE 2024 (osservato via spike) | Note |
|---|---|---|---|
| Souffrances endurées (Julin × age) | p.17 / 63 righe / oracle approvato dal QA spot-check | p.9 / matrice intera ricostruibile da OCR / 9 fasce × 7 severità | In 2024 la **matrice Julin × age è etichettata «préjudice esthétique permanent»** (sezione 3.4.2.b) e il quantum doloris (3.4.2.a) rimanda a 2.3 (€/jour). Il 2020 ha la stessa shape ma in posizione diversa. **Mappatura non 1:1** — richiede chiarimento legale. |
| Indemnité forfaitaire / age | p.22-23 / 71 righe / 1 valore per età | p.12 / formato simile / non OCR-zato in questo spike | Da OCR-zare in iter successivo. |
| Décès / affection | p.26 / 13 righe (gerarchia complessa: parent/non parent, cohabitant/non, perte enfant orphelin/non) | p.14 / 5 righe (Partenaires, Parents/enfants, Frères/sœurs, Grands-parents/Petits-enfants, Fausse couche) | **Cambio strutturale significativo**: 2024 sembrerebbe semplificato a 5 categorie. Va verificato sul PDF intero — potrebbero esserci sottocasi su altre pagine. |
| Véhicule remplacement | p.32 / 19 codici | p.17 / ~15-19 codici (struttura quasi identica) | Aggiornamento principalmente di importi. |

**Implicazione**: BE 2020 e BE 2024 NON sono un semplice update di
prezzo — la tassonomia décès/affection è cambiata, e la posizione
della scala Julin è stata ri-mappata. Lo Studio deve decidere quale
dataset è autoritativo e in quale ordine.

---

## 9. Decisione raccomandata

### Opzione A — OCR completo automatico → CSV candidate

- **Pro**: rapido (1 iter Claude per generare 4 CSV draft).
- **Contro**: il rischio comma/period sui migliaia è troppo alto (5-10%
  errori su importi 1.000-99.999 €). Senza review legale ogni cifra è
  inaffidabile. La struttura décès/affection cambiata richiede review
  comunque.
- **Verdetto**: ❌ **non consigliata** per BE 2024. Equivale a inventare
  dati legali (vietato dal CLAUDE.md).

### Opzione B — OCR + heavy review manuale (RACCOMANDATA)

- Iter successivo (Claude) genera CSV draft via OCR PSM 4.
- Lo Studio confronta cella per cella contro le immagini del PDF e
  corregge le ~5-10% di anomalie numeriche.
- Lo Studio approva la tassonomia décès/affection (5 vs 13).
- Lo Studio risolve l'ambiguità Julin × age tra «souffrances endurées»
  e «préjudice esthétique».
- Tempo stimato Studio: 2-4 ore per ~166-200 cifre.
- **Verdetto**: ✅ **consigliata se BE 2024 è prioritario**.

### Opzione C — Trascrizione manuale completa (alternativa)

- Lo Studio compila a mano un CSV-template dal PDF.
- Tempo stimato Studio: 6-10 ore per tutte e 4 le famiglie.
- **Verdetto**: alternativa accettabile, più lenta ma più sicura per
  giurisdizioni ad alto rischio. Stesso pattern già adottato per
  France/Mornet 2024 (`F-france-mornet-manual-fourchettes`).

### Opzione D — Mantenere solo BE 2020, ignorare BE 2024 a breve termine

- BE 2020 è già estratto come candidate read-only (4 CSV, 166 righe).
- Lo Studio lo revvede e approva.
- BE 2024 viene rinviato a quando Tesseract avrà i pacchetti `fra`/`nld`
  installati e/o quando si avrà tempo per Opzione B.
- **Verdetto**: ✅ **consigliata come fallback/incrementale**. Permette
  alla piattaforma di pubblicare un calcolatore Belgio funzionante
  prima di affrontare il refresh 2024.

### Raccomandazione finale (per discussione con lo Studio)

> **D + B**: nel breve termine **D** (review/approval BE 2020 e
> pubblicazione del calcolatore Belgio basato su 2020 con flag
> "historical"), poi **B** quando lo Studio ha capacità di review
> manuale per BE 2024 (idealmente dopo aver installato `tesseract-fra`
> e `tesseract-nld`, che ridurrebbero ulteriormente il rumore label).

---

## 10. Cosa deve verificare lo Studio

Prima di passare a una qualsiasi fase di import 2024:

1. **Confermare il cambio tassonomia décès/affection 2020→2024**: BE
   2024 ha davvero solo 5 categorie? O ce ne sono altre su una pagina
   del PDF che non è stata ispezionata in questo spike?
2. **Confermare che la tabella Julin × age di p.9** in BE 2024 è
   attribuita a «préjudice esthétique permanent» e che il «quantum
   doloris» in 2024 si calcola via €/jour (sezione 2.3) — non più via
   matrice come in 2020.
3. **Confermare gli importi BE 2024 sono inflazionati ~15%** rispetto
   a 2020 — non un cambio sostanziale di metodologia.
4. **Decidere se installare i pacchetti lingua Tesseract `fra` e
   `nld`** (file `tessdata/fra.traineddata` e `nld.traineddata` da
   GitHub UB-Mannheim) — non ho installato nulla autonomamente per
   rispettare la regola "non installare dipendenze globali senza
   dichiararlo".
5. **Decidere fra Opzione A/B/C/D** della §9.

---

## 11. File creati / modificati

### Committabili

| File | Tipo | Note |
|---|---|---|
| `scripts/legal_data/ocr_belgium_ti_2024_spike.py` | Nuovo | Script read-only spike OCR. |
| `docs/legal_sources/BELGIUM_TI_2024_OCR_SPIKE_REPORT.md` | Nuovo | Questo report. |
| `.gitignore` | Modificato | Aggiunta regola `legal_data/sources/**/ocr_spike/`. |

### Gitignored (output spike, non commit)

| File | Tipo | Note |
|---|---|---|
| `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/be-ti-2024-p09.png` | Render PDF→PNG 300 DPI |  |
| `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/be-ti-2024-p09.txt` | Output Tesseract grezzo |  |
| `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/be-ti-2024-p14.png` | Render PDF→PNG 300 DPI |  |
| `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/be-ti-2024-p14.txt` | Output Tesseract grezzo |  |
| `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/be-ti-2024-p17.png` | Render PDF→PNG 300 DPI |  |
| `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/be-ti-2024-p17.txt` | Output Tesseract grezzo |  |
| `legal_data/sources/belgium/tableau_indicatif_2024/ocr_spike/spike_summary.json` | Audit JSON |  |

### Non toccati

- Nessuna modifica a `apps/`.
- Nessuna modifica a `legal_data/sources/belgium/tableau_indicatif_2020/`
  (risultati iter F-belgium-extraction-ti-2020 invariati).
- Nessun import DB. Nessuna `LegalSource` creata o modificata. Nessuna
  `LegalReview`. Nessun `CompensationDataset`. Nessuna
  `CalculationFormula`.
- Nessuna modifica al calculator engine, ai wizard, alle view, al
  template.
- Italia: invariata.
- Tunisia: invariata.

---

## 12. Disclaimer

Tutti gli importi citati in questo report (BE 2024 OCR-letti) sono
**candidate read-only**. Non sono mai stati immessi nel database e non
sono mai stati usati come base di calcolo. Sono presentati al solo
scopo di documentare la qualità OCR osservata e fornire allo Studio i
dati necessari per decidere la prossima azione.

«La simulazione è indicativa e non costituisce parere legale,
medico-legale o garanzia di risultato. La valutazione effettiva dipende
da documenti, perizie, responsabilità, legge applicabile, giurisdizione
competente, orientamenti giudiziari e prassi assicurative.»
