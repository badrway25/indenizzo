# Review package — Prescrizione (validazione Studio · iter 1)

**Iter**: F-prescription-studio-review-iter1 · 2026-06-24
**Tipo**: pacchetto di review **read-only** per lo Studio — **preparatorio**
**Base**: `docs/audits/PRESCRIPTION_LEGAL_SOURCE_READONLY_AUDIT_2026-06-24.md`
**Stato fonti**: validate **internal-only** (vedi §2bis hardening) — **nessuna `approved_for_public_display`**

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
- **Nessuna fonte è `approved_for_public_display`**; tutte sono validate
  **internal-only** / **procedure-only** (§2bis hardening), mai pubbliche.
- Serve **validazione professionale** dello Studio: testo vigente, articolo,
  ambito, decorrenza, eccezioni, idoneità alla pubblicazione, wording prudente.
- Output atteso: per ogni fonte una decisione firmata (GO/NO-GO/NEEDS_MORE_RESEARCH)
  che abilita (o no) una futura fase `LegalSource` — sempre fail-closed.

---

## 2. Mappa fonti candidate (F1–F6)

> URL istituzionali; il **testo consolidato vigente** va aperto e verificato
> manualmente dallo Studio (Normattiva è JS-based: non estraibile in automatico).

> **Stato interno**: aggiornato dall'hardening pass (§2bis). Nessuno è
> `manual_review_required`/`unresolved`/`approved_for_public_display`; la colonna
> «Decisione Studio» (GO/NO-GO sull'eventuale uso futuro) resta `pending`.

| Codice candidato | Titolo | Ente/fonte | Articoli rilevanti | Ambito | URL da verificare | Rischio | Stato interno (post-hardening) | Decisione Studio |
|---|---|---|---|---|---|:---:|:---:|:---:|
| `it-cc-prescription-2947` | Codice Civile (R.D. 16/03/1942 n. 262) | Stato / Normattiva · Gazzetta Ufficiale | 2947, 2935, 2941–2945, 2946 | tutti gli illeciti civili | normattiva.it urn `regio.decreto:1942-03-16;262` · gazzettaufficiale.it `042U0262` | **alto** | `source_verified_official_internal_only` | pending |
| `it-inail-tu-1124-1965-art112` | T.U. INAIL (D.P.R. 30/06/1965 n. 1124) | Stato / INAIL · Normattiva | 112 | infortunio sul lavoro / malattia prof. | normattiva.it urn `presidente.repubblica:decreto:1965-06-30;1124` | **alto** | `source_verified_official_limited_scope` | pending |
| `it-l-24-2017-gelli-art7` | Legge 08/03/2017 n. 24 (Gelli-Bianco) | Stato / Gazzetta Ufficiale | 7 | responsabilità sanitaria | gazzettaufficiale.it (L. 24/2017) | **alto** | `source_verified_official_internal_only` | pending |
| `it-dlgs-206-2005-consumo-art125-126` | Codice del Consumo (D.Lgs. 06/09/2005 n. 206) | Stato / Normattiva | 125, 126, 114–127 | danno da prodotto difettoso | normattiva.it `eli/id/2005/10/08/005G0232/CONSOLIDATED` | **medio** | `source_verified_official_internal_only` | pending |
| `it-dlgs-209-2005-cap` | Codice delle Assicurazioni Private (D.Lgs. 07/09/2005 n. 209) | Stato / IVASS · Normattiva | 144–145, 148, 138–139 | offerta assicurativa / RC auto | normattiva.it `eli/id/2005/10/13/005G0233` · ivass.it `Cap.pdf` | **medio** | `source_verified_official_procedure_only` | pending |
| `eu-reg-864-2007-rome-ii` | Reg. (CE) 864/2007 (Roma II) | UE / EUR-Lex | 4, 5, 15, 31, 32 | casi internazionali | eur-lex.europa.eu `CELEX:32007R0864` | **alto** | `source_verified_official_internal_only` | pending |

Mappa caso → fonte → criticità: vedi §3 dell'audit (`...AUDIT_2026-06-24.md`).

---

## 2bis. Official hardening validation pass — 2026-06-24

> Esito della fase **F-source-validation-official-hardening**. Ogni fonte è
> validata internamente da fonte ufficiale **oppure** esclusa: **nessuna voce
> resta `unresolved`/`manual_review_required`**, e **0** voci
> `not_found_in_official_sources` (tutte hanno fonte ufficiale). Gli stati sono
> **solo interni** e l'usabilità pubblica è **sempre NO**. I termini nominali
> sotto sono **interni** (mai pubblici, mai nel calcolatore), legati allo
> strumento ufficiale, in attesa di conferma del testo consolidato da parte
> dello Studio. Record machine-readable: `prescription_review_checklist.yml`.
> I portali ufficiali italiani (Normattiva; Gazzetta caricaArticolo/detail) sono
> JavaScript-rendered e il PDF IVASS è compresso: strumento e posizione articoli
> confermati ufficialmente, corpi non auto-estraibili; EUR-Lex (F6) leggibile.

| Fonte | URL ufficiale | Articolo | Estratto/parafrasi (INTERNO) | Stato interno | Pubblico? | Motivo del NO pubblico |
|---|---|---|---|:---:|:---:|---|
| **F1** Cod. Civ. | normattiva.it `regio.decreto:1942-03-16;262` | 2947 | risarcimento danno = 5 anni; danno da circolazione = 2 anni; se reato con prescrizione penale più lunga → quella | `source_verified_official_internal_only` | **NO** | decorrenza (art. 2935), interruzione/sospensione, penale, conoscenza → non auto-determinabile dai soli input |
| **F2** T.U. INAIL | normattiva.it `presidente.repubblica:decreto:1965-06-30;1124` | 112 | prestazioni INAIL = triennale; sospeso in liquidazione (Cass. SU 11928/2019) | `source_verified_official_limited_scope` | **NO** | ambito ristretto (solo prestazioni INAIL); il differenziale civile segue altre regole |
| **F3** L. 24/2017 | gazzettaufficiale.it `eli/id/2017/03/17/17G00041/sg` | 7 | struttura → artt. 1218/1228 c.c. (contrattuale); esercente → art. 2043 c.c. (extracontrattuale, salvo obbligazione contrattuale) | `source_verified_official_internal_only` | **NO** | nessun termine unico: dipende dalla qualificazione del rapporto |
| **F4** Cod. Consumo | normattiva.it `eli/id/2005/10/08/005G0232/CONSOLIDATED` | 125; 126 | prescrizione = 3 anni (dalla conoscenza); decadenza = 10 anni (dalla messa in circolazione) | `source_verified_official_internal_only` | **NO** | doppio termine con dies a quo legati alla conoscenza; nessun automatismo |
| **F5** CAP | normattiva.it `eli/id/2005/10/13/005G0233` · ivass.it `Cap.pdf` | 144; 145; 148 | procedura (azione diretta / richiesta / offerta) — **non** il termine prescrizionale | `source_verified_official_procedure_only` | **NO** | fonte procedurale; il termine RC auto resta art. 2947 c.c. + caso |
| **F6** Roma II | eur-lex.europa.eu `CELEX:32007R0864` | 4; 5; 15; 31; 32 | art. 15: «prescrizione e decadenza» nell'ambito della legge applicabile — nessun numero | `source_verified_official_internal_only` | **NO** | rinvio alla *lex causae*; nessun termine numerico |

**Sintesi hardening**: 4 `source_verified_official_internal_only` (F1, F3, F4, F6),
1 `source_verified_official_limited_scope` (F2), 1
`source_verified_official_procedure_only` (F5). **0** voci `unresolved` o
`not_found_in_official_sources`. **Nessuna** fonte è `approved_for_public_display`
né `public_approved`; **tutti** i termini restano interni e **nessuno** è
pubblico o usato dal calcolatore.

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
