# Review package — Prescrizione (validazione Studio · iter 1)

**Iter**: F-prescription-studio-review-iter1 · 2026-06-24
**Tipo**: pacchetto di review **read-only** per lo Studio — **preparatorio**
**Base**: `docs/audits/PRESCRIPTION_LEGAL_SOURCE_READONLY_AUDIT_2026-06-24.md`
**Stato fonti**: tutte `manual_review_required` — **nessuna `approved`**

> ⚠️ Documento operativo interno. **Non** attiva alcuna `LegalSource`, **non**
> rende pubblico alcun termine, **non** modifica il calcolatore. Serve allo
> Studio per decidere, fonte per fonte, GO / NO-GO / NEEDS_MORE_RESEARCH. Nessun
> termine numerico va al pubblico finché una fonte non è `approved` con review
> firmata (fail-closed, come per il TUN 2025).

Allegati di questa fase:
- decisione: `docs/review_packages/templates/prescription_review_decision_template.md`
- checklist: `docs/review_packages/prescription_review_checklist.csv` (status=`pending`)

---

## 1. Executive summary

- Fase **preparatoria**: prepara la validazione, non la esegue.
- **Nessun termine è pubblico** oggi e nessuno lo diventa con questo pacchetto.
- **Nessuna fonte è `approved`**; tutte sono `manual_review_required`.
- Serve **validazione professionale** dello Studio: testo vigente, articolo,
  ambito, decorrenza, eccezioni, idoneità alla pubblicazione, wording prudente.
- Output atteso: per ogni fonte una decisione firmata (GO/NO-GO/NEEDS_MORE_RESEARCH)
  che abilita (o no) una futura fase `LegalSource` — sempre fail-closed.

---

## 2. Mappa fonti candidate (F1–F6)

> URL istituzionali; il **testo consolidato vigente** va aperto e verificato
> manualmente dallo Studio (Normattiva è JS-based: non estraibile in automatico).

| Codice candidato | Titolo | Ente/fonte | Articoli rilevanti | Ambito | URL da verificare | Rischio interpretativo | Stato | Decisione richiesta |
|---|---|---|---|---|---|:---:|:---:|:---:|
| `it-cc-prescription-2947` | Codice Civile (R.D. 16/03/1942 n. 262) | Stato / Normattiva · Gazzetta Ufficiale | 2947, 2935, 2941–2945, 2946 | tutti gli illeciti civili | normattiva.it urn `regio.decreto:1942-03-16;262` · gazzettaufficiale.it `042U0262` | **alto** (decorrenza, penale, interruzione) | `manual_review_required` | GO / NO-GO / NEEDS_MORE_RESEARCH |
| `it-inail-tu-1124-1965-art112` | T.U. INAIL (D.P.R. 30/06/1965 n. 1124) | Stato / INAIL · Normattiva | 112 | infortunio sul lavoro / malattia prof. | normattiva.it urn `presidente.repubblica:decreto:1965-06-30;1124` | **alto** (sospensione in liquidazione, differenziale) | `manual_review_required` | GO / NO-GO / NEEDS_MORE_RESEARCH |
| `it-l-24-2017-gelli-art7` | Legge 08/03/2017 n. 24 (Gelli-Bianco) | Stato / Gazzetta Ufficiale | 7 | responsabilità sanitaria | gazzettaufficiale.it (L. 24/2017) | **alto** (contrattuale vs extracontrattuale) | `manual_review_required` | GO / NO-GO / NEEDS_MORE_RESEARCH |
| `it-dlgs-206-2005-consumo-art125-126` | Codice del Consumo (D.Lgs. 06/09/2005 n. 206) | Stato / Normattiva | 125, 126, 114–127 | danno da prodotto difettoso | normattiva.it `eli/id/2005/10/08/005G0232/CONSOLIDATED` | **medio** (doppio termine, dies a quo) | `manual_review_required` | GO / NO-GO / NEEDS_MORE_RESEARCH |
| `it-dlgs-209-2005-cap` | Codice delle Assicurazioni Private (D.Lgs. 07/09/2005 n. 209) | Stato / IVASS · Normattiva | 144–145, 148, 138–139 | offerta assicurativa / RC auto | normattiva.it `eli/id/2005/10/13/005G0233` · ivass.it `Cap.pdf` | **medio** | `needs_review` *(già in repo come `it-dlgs-209-2005-cap-art-138-139`)* | GO / NO-GO / NEEDS_MORE_RESEARCH |
| `eu-reg-864-2007-rome-ii` | Reg. (CE) 864/2007 (Roma II) | UE / EUR-Lex | art. su legge applicabile illecito | casi internazionali | EUR-Lex (manual_required) | **alto** (lex causae) | `manual_review_required` | GO / NO-GO / NEEDS_MORE_RESEARCH |

Mappa caso → fonte → criticità: vedi §3 dell'audit (`...AUDIT_2026-06-24.md`).

---

## 2bis. Official source validation pass — 2026-06-24

> Esito della fase **F-source-validation-official**. Valida la **fonte
> normativa** (esistenza/identità su sito ufficiale), **non** l'usabilità
> pubblica di alcun termine. Record machine-readable:
> `prescription_review_checklist.yml`. Voci non risolte:
> `PRESCRIPTION_UNRESOLVED_FOR_CHATGPT_2026-06-24.md`. **Nessun termine
> numerico** è stato estratto/registrato: i siti ufficiali (Normattiva, parte
> di Gazzetta) sono JS-based, quindi i corpi degli articoli non sono estraibili
> in automatico; l'identità degli strumenti e (dove l'indice ufficiale ha
> caricato) l'esistenza degli articoli sono confermate.

| Fonte | Esito | URL ufficiale | Limite | Prossimo passo (Studio) |
|---|:---:|---|---|---|
| **F1** Codice Civile — art. 2947 | `unresolved` | normattiva.it `regio.decreto:1942-03-16;262` · gazzettaufficiale.it `042U0262` | Gazzetta caricaArticolo = stato di caricamento JS; indice Normattiva troncato prima dell'art. 2947 | aprire manualmente l'art. 2947 su Normattiva / fonte ufficiale alternativa |
| **F2** T.U. INAIL — art. 112 | `source_verified_official` | normattiva.it `presidente.repubblica:decreto:1965-06-30;1124` | corpo articolo non estratto (solo indice ufficiale: Capo V — Prestazioni) | aprire art. 112 + circolari INAIL su sospensione (Cass. SU 11928/2019) |
| **F3** L. 24/2017 — art. 7 | `source_verified_official` | gazzettaufficiale.it `eli/id/2017/03/17/17G00041/sg` | legge confermata; corpo art. 7 non nell'estratto | aprire art. 7 + qualificazione contrattuale/extracontrattuale |
| **F4** Cod. Consumo — artt. 125–126 | `source_verified_official` | normattiva.it `eli/id/2005/10/08/005G0232/CONSOLIDATED` | strumento + artt. 125/126 nell'indice ufficiale (Titolo II); corpi non estratti | aprire artt. 125–126 (prescrizione/decadenza) |
| **F5** CAP — artt. 144–148 | `source_verified_official_procedure_only` | normattiva.it `eli/id/2005/10/13/005G0233` · ivass.it `Cap.pdf` | PDF IVASS compresso/non estraibile; CAP è fonte **procedurale**, non del termine | usare solo come procedura (offerta/azione diretta); prescrizione resta art. 2947 + caso |
| **F6** Roma II — artt. 4/5/15/31/32 | `source_verified_official` | eur-lex.europa.eu `CELEX:32007R0864` | nessuno (testo estratto); art. 15 include «prescrizione e decadenza» nella *lex causae* | nessun termine numerico: i casi internazionali seguono la legge applicabile |

**Sintesi**: 4 fonti `source_verified_official` (F2, F3, F4, F6), 1
`source_verified_official_procedure_only` (F5), 1 `unresolved` (F1 — art. 2947).
**Nessuna** fonte è `approved_for_public_display`; **nessun** termine numerico è
pubblico o registrato come certo.

---

## 3. Checklist per lo Studio (per ogni fonte)

Compilare la riga corrispondente in `prescription_review_checklist.csv`
(`status: pending → checked_ok / needs_correction / rejected`). Per ogni fonte:

1. **Testo vigente** confermato su Normattiva/Gazzetta (consolidato, non originario).
2. **Articolo** rilevante confermato (numero + comma).
3. **Ambito applicativo** confermato (a quali `case_type` si applica).
4. **Decorrenza** confermata (dal fatto? dalla conoscenza? art. 2935).
5. **Eccezioni** note documentate (penale, contrattuale, internazionale…).
6. **Interruzione / sospensione** rilevanti documentate (artt. 2941–2945; INAIL).
7. **Mostrabile al pubblico?** sì/no — e a quali condizioni.
8. **Wording prudente** approvato (testo qualitativo, **senza numeri** se non GO).
9. **Reviewer / data / firma**.

---

## 4. Criteri GO / NO-GO

**GO** (solo se TUTTI veri):
- [ ] fonte ufficiale verificata (URL + testo vigente);
- [ ] articolo vigente confermato;
- [ ] ambito chiaro e delimitato;
- [ ] copy prudente approvato dallo Studio;
- [ ] eccezioni note documentate;
- [ ] disclaimer presente sulla superficie pubblica;
- [ ] test fail-closed previsti (il termine appare solo se `approved`).

**NO-GO / NEEDS_MORE_RESEARCH** se anche solo uno tra:
- fonte ambigua o non verificata;
- articolo non confermato vigente;
- decorrenza troppo dipendente dal caso concreto;
- rischio di informazione fuorviante per l'utente;
- manca validazione, wording o firma.

Default in assenza di decisione firmata: **NO-GO** (fail-closed).

---

## 5. Proposta futura `LegalSource` (solo proposta — non implementata)

- Una `LegalSource` per codice candidato (F1–F6), riusando `apps/legal_sources`.
- Stati: `draft → needs_review → approved` (oppure `rejected` / `archived`),
  con promozione **solo** dopo `LegalReviewDecision` firmata (criterio C-2 dei
  package esistenti FR/BE/MA/TN).
- Struttura **descrittiva** (non un «importo»): per ogni `case_type`,
  `applicable_article` + `nominal_term` (testo) + lista strutturata di
  `modifiers` (decorrenza/sospensione/interruzione/penale/qualificazione) con
  flag `requires_professional_assessment=true`.
- Relazione con `LegalReviewDecision` (reviewer, data, esito) come per il TUN.
- **Nessuna attivazione automatica**: nessun engine usa la prescrizione per
  stimare o bloccare; nessun output senza `approved`.

---

## 6. Proposta futura UI pubblica (mock copy prudente — nessun numero)

Bozza testi (qualitativi, **da non pubblicare con cifre** salvo GO firmato):

- «La prescrizione dipende dal caso concreto.»
- «La verifica richiede l'analisi della data, del tipo di danno, degli atti già
  compiuti e dell'eventuale rilevanza penale.»
- «Richiedi una verifica gratuita.»

La notice attuale (`partials/_prescrizione_notice.html`) è già conforme e **non
va sostituita**. Eventuale arricchimento = solo testo qualitativo tradotto
it/fr/ar. **Nessun termine numerico nel sito** finché non `approved`.

---

## 7. Rischi

- **Semplificazione eccessiva**: ridurre la prescrizione a un numero.
- **Decorrenza errata**: partire dal fatto invece che dalla conoscenza.
- **Casi penali**: termine penale più lungo non considerato.
- **Atti interruttivi/sospensivi**: ignorare diffide/trattative/procedimenti.
- **Casi internazionali**: applicare la legge italiana dove vale la *lex causae*.
- **Percezione come consulenza**: l'utente potrebbe leggere la pagina come
  parere legale → disclaimer e wording prudente obbligatori.

---

## 8. Piano della futura fase

1. **Fase 1 — Studio review** (questo pacchetto): decisioni firmate per F1–F6.
2. **Fase 2 — `LegalSource` draft**: creare le fonti GO in stato `draft`
   (read-only on-disk → DB), nessun output pubblico.
3. **Fase 3 — Review firmata**: `LegalReviewDecision` riga-per-riga.
4. **Fase 4 — Approval**: promozione a `approved` solo post-firma.
5. **Fase 5 — UI fail-closed**: il termine appare solo se `approved`, sempre con
   modificatori + disclaimer; mai un numero «certo».
6. **Fase 6 — QA pubblico**: render + browser QA (it/fr/ar, mobile 390, RTL,
   0 console error, disclaimer visibile) + test fail-closed.

---

## 9. Disclaimer

Documento read-only e preparatorio. Non costituisce parere legale. I codici
candidati e gli articoli citati richiedono validazione professionale del testo
vigente. Il sito pubblico non mostra alcun termine di prescrizione finché una
`LegalSource` non è `approved` con review umana firmata.
