# `legal_data/` — root del materiale legale extra-codice

Questa cartella custodisce i **file ufficiali** delle fonti legali e gli
artefatti di estrazione **di cui il codice non si fida ciecamente**.
Niente di quanto viene posato qui entra automaticamente in produzione:
ogni dato passa dal workflow `draft → needs_review → approved` di
`apps.legal_sources` e `apps.compensation`.

Tre regole assolute:

1. **Nessun file qui dentro è committato** se non i README/template.
   I PDF ufficiali (Gazzetta Ufficiale, decreti MIMIT, ecc.) e i CSV
   di estrazione restano fuori da git: contengono materiale soggetto a
   diritto d'autore (G.U.) e/o lavoro umano dello Studio non ancora
   pubblicato. Il `.gitignore` di repository li esclude esplicitamente.
2. **Solo fonti ufficiali**. Mai scaricare un PDF da un blog o da un
   commentario per usarlo come dato definitivo: il command di import
   rifiuta i file il cui hash non è registrato nei metadati della
   `LegalSource` corrispondente.
3. **Mai promuovere automaticamente**. I command popolano dataset e
   formule sempre in `draft`. La promozione a `approved` è un atto
   umano dello Studio, registrato in `LegalReview`.

## Struttura

```
legal_data/
├── README.md                          ← (questo file)
├── sources/
│   └── italy/
│       └── tun_2025/                  ← D.P.R. 13/01/2025 n. 12
│           ├── README.md              ← istruzioni per il caricamento
│           ├── dpr_12_2025_tun.pdf    ← (ignorato: caricato a mano)
│           └── tun_2025_rows.csv      ← (ignorato: estrazione manuale)
└── extraction_logs/
    └── italy_tun_2025_*.json          ← (ignorati: log per audit)
```

## Workflow tipico

1. Lo Studio scarica il PDF dalla Gazzetta Ufficiale e lo salva sotto
   `sources/<paese>/<modulo>/`.
2. Un revisore legale verifica l'hash SHA-256 con il valore atteso (se
   già noto) e annota le discrepanze.
3. Si lancia `python manage.py import_italy_tun_2025 --source-file <PDF>`
   per allegare il PDF alla `LegalSource` e creare il `CompensationDataset`
   in stato `draft`.
4. Estrazione tabellare manuale → CSV → seconda esecuzione del command
   con `--csv <CSV>` per importare le righe (sempre `draft`).
5. Legal review: ogni riga viene verificata contro la fonte. Lo Studio
   promuove fonte/dataset/formula a `approved` solo quando tutti e tre
   sono coerenti.

Solo dopo lo step 5 il calculator pubblico smette di restituire
`unavailable_requires_legal_validation`.
