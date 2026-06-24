# Prescrizione — voci NON risolte (per ChatGPT / validazione umana)

**Fase**: F-source-validation-official · 2026-06-24
**Contesto**: tentata validazione da sole fonti ufficiali (Normattiva, Gazzetta
Ufficiale, EUR-Lex). I siti ufficiali italiani (Normattiva; parte di Gazzetta
`caricaArticolo`) sono **JavaScript-based**: l'identità degli strumenti e — dove
l'indice ha caricato — l'esistenza degli articoli è confermata, ma i **corpi
degli articoli** (e quindi i termini) non sono estraibili in automatico.

> Nessun termine numerico è stato estratto o reso pubblico. Le voci sotto
> servono a completare la validazione *a livello di corpo dell'articolo* tramite
> apertura manuale del portale ufficiale o conferma da fonte ufficiale
> alternativa. **Non** usare blog/Brocardi/Altalex/Wikipedia/forum come
> validazione.

---

## U1 — F1: Codice Civile, art. 2947 (status: `unresolved`)

1. **Domanda precisa**: confermare, da fonte ufficiale leggibile, l'esistenza e
   il testo vigente dell'art. 2947 c.c. (prescrizione del diritto al risarcimento
   del danno) e degli artt. 2943/2945 (interruzione/effetti), 2946 (ordinaria).
2. **Fonte cercata**: Normattiva (Codice Civile, R.D. 262/1942); Gazzetta
   Ufficiale (cod. red. `042U0262`).
3. **Query usate**: «Codice Civile articolo 2947 prescrizione risarcimento danno
   fatto illecito normattiva» (allowed_domains: normattiva.it, gazzettaufficiale.it).
4. **URL provati**:
   - `https://www.gazzettaufficiale.it/atto/serie_generale/caricaArticolo?...codiceRedazionale=042U0262&art.idArticolo=2947...` → «Gazzetta in fase di caricamento» (stato JS, nessun testo).
   - `https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:regio.decreto:1942-03-16;262` → indice caricato (strumento confermato: R.D. 262/1942, GU n.79/1942) ma **troncato prima dell'art. 2947**; corpo non estraibile.
5. **Perché non basta**: l'identità dello strumento è confermata, ma l'art. 2947
   non è stato visto/letto da una fonte ufficiale estraibile in questo pass.
6. **Cosa serve**: conferma del testo vigente dell'art. 2947 (e 2943/2945/2946)
   da Normattiva (apertura diretta dell'articolo) o da altra fonte ufficiale
   estraibile; oppure istruzione manuale dello Studio.

---

## U2 — Corpi/termini degli articoli per le fonti `source_verified_official`

Per F2 (INAIL art. 112), F3 (L. 24/2017 art. 7), F4 (Cod. Consumo artt. 125–126)
lo **strumento** è validato ufficiale e (per F2/F4) l'articolo è confermato
nell'indice ufficiale, ma il **corpo dell'articolo** (e quindi il termine
esatto vigente) non è stato estratto (rendering JS).

1. **Domanda precisa**: estrarre dal corpo ufficiale di ciascun articolo il
   termine vigente e la decorrenza, **senza** fonti non ufficiali.
2. **Fonte cercata**: Normattiva (corpo articolo) / Gazzetta Ufficiale.
3. **URL provati**: quelli in `prescription_review_checklist.yml` (campo
   `official_url`).
4. **Perché non basta**: solo indice/struttura ufficiale leggibile, non il corpo.
5. **Cosa serve**: apertura manuale dell'articolo sul portale ufficiale (o
   conferma ufficiale alternativa) per il testo del termine. **Resta comunque**
   soggetto alle criticità (decorrenza, sospensione, interruzione, penale,
   qualificazione) → non pubblicabile come numero certo.

---

## U3 — F5: CAP, artt. 144–148 (status: `source_verified_official_procedure_only`)

1. **Domanda precisa**: confermare i corpi degli artt. 144/145/148 (procedura,
   azione diretta) da fonte ufficiale leggibile.
2. **URL provati**:
   - `https://www.ivass.it/normativa/nazionale/primaria/Cap.pdf` → PDF ufficiale
     ma **stream FlateDecode compresso, testo non estraibile** (3.4 MB).
   - `https://www.normattiva.it/eli/id/2005/10/13/005G0233/ORIGINAL` (Normattiva, JS).
3. **Perché non basta**: strumento ufficiale identificato, ma corpo non letto.
4. **Cosa serve**: lettura ufficiale degli artt. 144–148 (apertura Normattiva /
   PDF IVASS con OCR/estrattore). Nota: il **termine** prescrizionale RC auto
   resta art. 2947 c.c. + caso concreto — CAP è fonte **procedurale**, non del termine.

---

*Voci risolte in questo pass (non qui)*: F6 (Roma II) `source_verified_official`
— EUR-Lex estratto, art. 15 conferma che la prescrizione segue la *lex causae*.
