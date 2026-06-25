# Prescrizione — fonti non trovate e follow-up (post-hardening)

**Fase**: F-source-validation-official-hardening · 2026-06-24
**Esito ricerca**: **0 voci `not_found_in_official_sources`.** Dopo due passaggi
di ricerca su sole fonti ufficiali (Normattiva, Gazzetta Ufficiale, EUR-Lex,
IVASS), **tutte** le fonti F1–F6 hanno una fonte ufficiale identificata e sono
state validate **internal-only** (vedi §2bis del review package e
`prescription_review_checklist.yml`). **Nessuna voce resta `unresolved`.**

> Questo file non contiene termini numerici né stati pubblici. Documenta solo
> (a) che nessuna fonte risulta introvabile e (b) i follow-up tecnici/di merito
> che restano in carico allo Studio. **Non** usare blog/Brocardi/Altalex/
> Wikipedia/forum come validazione.

---

## A. `not_found_in_official_sources` — NESSUNA

Tutte le fonti hanno URL ufficiale (`official_url` nel record YAML). Nulla è
classificato come introvabile.

## B. Limite tecnico documentato (non è un "not found")

I **corpi** degli articoli non sono auto-estraibili perché i portali ufficiali
italiani sono JavaScript-rendered (Normattiva `uri-res` e `caricaDettaglioAtto`;
Gazzetta `caricaArticolo`) e il PDF IVASS della CAP ha lo stream FlateDecode
compresso. È confermata l'**identità degli strumenti** e (dove l'indice ha
caricato) la **posizione degli articoli**. EUR-Lex (F6) è pienamente leggibile.

- URL provati (F1): `gazzettaufficiale.it/...caricaArticolo?...042U0262...art.idArticolo=2947` (JS) ·
  `normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262` (indice JS) ·
  `normattiva.it/atto/caricaDettaglioAtto?...042U0262` (indice JS).
- URL provati (F4): `normattiva.it/eli/id/2005/10/08/005G0232/CONSOLIDATED` (indice JS) ·
  `gazzettaufficiale.it/...caricaDettaglioAtto/originario?...005G0232` (metadati).
- URL provati (F5): `ivass.it/.../Cap.pdf` (compresso) · `normattiva.it/eli/id/2005/10/13/005G0233` (JS).

## C. Follow-up in carico allo Studio (conferma di merito, non ricerca)

1. Confermare il **testo consolidato vigente** di ciascun articolo aprendolo sul
   portale ufficiale (Normattiva) o da PDF Gazzetta con estrattore/OCR.
2. Confermare **decorrenza, eccezioni, interruzione/sospensione, rilevanza
   penale, qualificazione** (contrattuale/extracontrattuale) per ciascun
   `case_type`.
3. Decidere GO/NO-GO sull'eventuale `LegalSource` futura (default: NO-GO,
   fail-closed). **Nessun termine** diventa pubblico senza UI/test fail-closed
   dedicati e `approved` firmato — fuori dallo scope di questa fase.
