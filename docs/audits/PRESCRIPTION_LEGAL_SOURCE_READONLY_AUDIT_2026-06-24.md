# Audit read-only — Fonti ufficiali sulla prescrizione (risarcimento danni)

**Iter**: F-legal-prescription-source-readonly-audit · 2026-06-24
**Tipo**: audit tecnico-legale **read-only** (nessuna attivazione pubblica)
**Stato**: 🟡 candidate-only — **nessun termine elevato a `approved`**, nessun
output pubblico numerico, calcolatore e registry invariati.

> ⚠️ Documento interno di analisi. **Non** è un parere legale e **non** è la
> fonte di alcun calcolo pubblico. I termini citati sono *candidati* tratti
> dalle fonti ufficiali indicate, riportati **solo** per preparare una futura
> `LegalSource` e **richiedono validazione professionale** prima di qualunque
> uso. Il sito pubblico **non mostra** alcun termine numerico di prescrizione.

---

## 1. Sintesi executive

La prescrizione (e la decadenza) nei casi di risarcimento danni in Italia è
**regolata da fonti ufficiali chiare** (Codice Civile, T.U. INAIL, Codice del
Consumo, Codice delle Assicurazioni), ma il **termine nominale** di ciascun
articolo è solo il punto di partenza: la durata effettiva dipende da fattori
**caso-specifici** che nessun calcolo automatico può determinare in modo
affidabile:

- **decorrenza** (art. 2935 c.c.): il termine non parte dal fatto ma da quando
  il diritto «può essere fatto valere» → spesso dalla **conoscenza** del danno
  e del responsabile (rilevante in responsabilità sanitaria e danno lungolatente);
- **sospensione / interruzione** (artt. 2941–2945 c.c.): atti, diffide,
  trattative, procedimenti possono azzerare o congelare il termine;
- **rilevanza penale** (art. 2947 co. 3 c.c.): se il fatto è reato con
  prescrizione penale più lunga, si applica quella al civile;
- **qualificazione contrattuale vs extracontrattuale** (es. sanità, Legge
  24/2017): cambia il termine base (5 vs 10 anni);
- **sospensione amministrativa** (INAIL, Cass. SU 11928/2019): il triennio è
  sospeso durante la liquidazione;
- **elemento internazionale**: la *lex causae* (Reg. Roma II 864/2007) può
  rendere applicabile una legge straniera con termini diversi.

**Conclusione**: le fonti sono identificabili e **citabili**, ma **non è sicuro**
trasformare un termine in un dato pubblico «certo» o in un gate di calcolo.
La UI pubblica deve restare **prudente e non numerica** (come è oggi). Questo
audit propone una struttura `LegalSource` futura e i relativi controlli, **senza
attivare nulla**.

---

## 2. Fonti ufficiali analizzate

Solo fonti ufficiali/istituzionali. Le URL `gazzettaufficiale.it` e
`normattiva.it` sono istituzionali; il **testo consolidato vigente** va
verificato manualmente dallo Studio (Normattiva è JS-based, non estraibile in
modo affidabile da un fetch automatico → marcato `manual_verification_required`,
coerente con il pattern già usato nei manifest `legal_data/` del progetto).

| # | Strumento (ente) | Articoli rilevanti | Ambito | URL ufficiale | Affidabilità | Perché NON `approved` ora |
|---|---|---|---|---|:---:|---|
| F1 | **Codice Civile** — R.D. 16/03/1942 n. 262 (Stato) | **2947** (prescr. risarcimento: 5 anni; circolazione 2 anni; reato → termine penale); 2935 (decorrenza); 2941–2942 (sospensione); 2943–2945 (interruzione); 2946 (ordinaria 10 anni) | tutti gli illeciti civili | normattiva.it (urn `regio.decreto:1942-03-16;262`); gazzettaufficiale.it cod. red. `042U0262` | alta | Il termine nominale non basta: decorrenza/sospensione/interruzione/penale sono caso-specifici |
| F2 | **T.U. INAIL** — D.P.R. 30/06/1965 n. 1124 | **112** (prescrizione triennale prestazioni) | infortunio sul lavoro / malattia professionale | normattiva.it (urn `presidente.repubblica:decreto:1965-06-30;1124`); gazzettaufficiale.it `065U1124` | alta | Sospensione del triennio in fase di liquidazione (Cass. SU 11928/2019); il differenziale civile segue altre regole |
| F3 | **Legge 08/03/2017 n. 24** (Gelli-Bianco) | **7** (responsabilità struttura vs esercente) | responsabilità sanitaria | gazzettaufficiale.it (L. 24/2017) | alta | Determina contrattuale (struttura, ~10 anni) vs extracontrattuale (esercente, ~5 anni): la qualificazione è giuridica, non automatizzabile |
| F4 | **Codice del Consumo** — D.Lgs. 06/09/2005 n. 206 | **125** (prescrizione 3 anni dalla conoscenza); **126** (decadenza 10 anni dalla messa in circolazione); 114–127 (responsabilità produttore) | danno da prodotto difettoso | normattiva.it `eli/id/2005/10/08/005G0232/CONSOLIDATED`; gazzettaufficiale.it `005G0232` | alta | Doppio termine (prescrizione + decadenza) con dies a quo diversi e legati alla conoscenza |
| F5 | **Codice delle Assicurazioni** — D.Lgs. 07/09/2005 n. 209 (CAP) | 144–145 (azione diretta), 148 (procedura di offerta), 138–139 (danno biologico) | offerta assicurativa / RC auto | normattiva.it `eli/id/2005/10/13/005G0233`; ivass.it `Cap.pdf` | alta | **Già presente in repo come `it-dlgs-209-2005-cap-art-138-139` in stato `needs_review`**; l'azione resta soggetta all'art. 2947; offerta/transazione possono precludere |
| F6 | **Reg. (CE) 864/2007 (Roma II)** + DIP | legge applicabile all'obbligazione extracontrattuale | casi internazionali | EUR-Lex (manual_required, come da pattern EU 650/2012 in repo) | media | La *lex causae* determina la prescrizione: non risolvibile lato piattaforma |

Documenti: **non scaricati** in questa fase (read-only). Se in una fase futura
si scaricano i PDF consolidati, calcolare SHA-256 e registrare solo i metadati
(coerente con `legal_data/sources/*/*.json`). Nessun segreto/cookie/env toccato.

---

## 3. Matrice: caso → fonte candidata → criticità

> I «termini nominali» sotto sono **candidati** dalla fonte citata, **non**
> output del sito e **non** validati. Ogni cella ha modificatori che ne
> impediscono l'uso automatico.

| Caso (ambito) | Fonte candidata | Termine nominale (candidate) | Criticità che bloccano l'automazione |
|---|---|---|---|
| **1. Incidente stradale** | F1 art. 2947 co. 2 + F5 (CAP) | 2 anni (circolazione) | dies a quo; sospensione da richiesta/offerta (CAP); se reato → art. 2947 co. 3 (penale più lungo) |
| **2. Responsabilità sanitaria** | F3 (L. 24/2017) + F1 | 5 anni (extracontr.) o 10 (contr.) | qualificazione struttura/esercente; decorrenza dalla **conoscenza** del danno; danno lungolatente |
| **3. Infortunio sul lavoro / INAIL** | F2 art. 112 + F1 | 3 anni (prestazioni INAIL) | sospensione in liquidazione (Cass. SU 11928/2019); danno **differenziale** civile vs datore segue altre regole (2947 / contrattuale 2087-2946) |
| **4. Decesso da fatto illecito** | F1 art. 2947 | 5 anni (2 se stradale) | danno **iure proprio** dei congiunti; omicidio è reato → quasi sempre **prescrizione penale più lunga** (art. 2947 co. 3) |
| **5. Danno da prodotto difettoso** | F4 artt. 125–126 | prescr. 3 anni + **decadenza** 10 anni | due termini con dies a quo diversi; conoscenza danno/difetto/responsabile; concorso con 2947 |
| **6. Offerta assicurativa ricevuta** | F5 (CAP, artt. 145/148) + F1 | (procedura, non un «termine utente») | accettazione/transazione può **precludere**; l'azione resta a 2947; va valutata l'adeguatezza prima di firmare |
| **7. Rilevanza penale** | F1 art. 2947 co. 3 | = prescrizione penale del reato | dipende dal reato contestato; sentenza penale irrevocabile fa decorrere nuovo termine; non determinabile dai soli input |
| **8. Internazionale / residente estero** | F6 (Roma II) + DIP | secondo *lex causae* | la legge applicabile può non essere quella italiana; richiede qualificazione DIP professionale |

---

## 4. Perché NON è sicuro attivare automaticamente la prescrizione

1. **Non è un numero, è una valutazione.** Il termine effettivo dipende da
   variabili (decorrenza, sospensione, interruzione, penale, qualificazione,
   atti già compiuti) che la piattaforma **non conosce** e non deve indovinare.
2. **Rischio di danno all'utente.** Un termine «certo» errato (es. «hai ancora
   X anni») potrebbe indurre l'utente a **non agire** in tempo → decadenza del
   diritto. È il rischio opposto a quello di un calcolo gonfiato: qui un dato
   falso può **far perdere il diritto**.
3. **Deontologia forense.** Indicare termini come certi senza analisi del caso
   è informazione potenzialmente fuorviante; il Codice Deontologico impone
   prudenza e divieto di claim non dimostrabili.
4. **Coerenza col modello del progetto.** Il sistema pubblica un valore solo se
   legato a una `LegalSource` **`approved`** con review umana firmata (vedi
   `docs/architecture/GLOBAL_MVP_STATUS.md`). Nessuna fonte prescrizione è oggi
   `approved`, quindi **niente output pubblico** — esattamente come oggi.
5. **Versioning / vigenza.** Il testo consolidato va verificato (riforme,
   orientamenti di Cassazione). Lo snapshot va datato e hash-ato come per il TUN.

---

## 5. Proposta di futura implementazione `LegalSource` (NON attivata qui)

Quando lo Studio deciderà di procedere, la struttura **additiva** suggerita
(riusa il modello esistente di `apps/legal_sources`):

- una `LegalSource` per strumento (F1–F5), con `status` che parte da `draft` →
  `needs_review` → `approved` **solo dopo `LegalReview` firmata**;
- un dataset/struttura **descrittiva** (non un «importo»): per ogni `case_type`,
  l'**articolo applicabile** + il **termine nominale** + un elenco strutturato
  dei **modificatori** (decorrenza/sospensione/interruzione/penale/qualificazione)
  con flag «richiede valutazione professionale»;
- **nessun engine** che usi la prescrizione per stimare o bloccare un caso: al
  massimo un componente **informativo** che, *se e solo se* la fonte è
  `approved`, mostra il termine nominale **con tutti i caveat** e un rimando alla
  valutazione. Fino ad allora: solo copy prudente non numerico (stato attuale).
- F5 (CAP 209/2005) è già in repo come `needs_review`: è il candidato naturale
  per il **primo** iter di promozione, perché collegato al caso IT già operativo.

Pattern di sicurezza da mantenere: `candidate read-only on-disk` → `LegalReview`
riga-per-riga → promozione `approved` → output gated. Nessun valore «LLM-generated».

---

## 6. Proposta UI prudente (nessun numero)

Lo stato attuale è già conforme: `templates/partials/_prescrizione_notice.html`
(incluso su `wizard_result.html`) dice, **senza cifre**, che i termini variano e
che serve una verifica professionale. Migliorie *prudenti* possibili **senza
introdurre numeri né certezze**:

- esplicitare i **fattori** che cambiano la valutazione (decorrenza, sospensione,
  interruzione, rilevanza penale, atti già compiuti) — testo, non tabella;
- evitare assolutamente formule tipo «hai ancora X anni»;
- mantenere la CTA «chiedi una verifica» → contatto.

In questo audit **non** sono stati aggiunti numeri pubblici. Eventuale
arricchimento del copy va fatto solo come testo qualitativo tradotto it/fr/ar.

---

## 7. Test consigliati per una futura fase (oltre a quelli aggiunti ora)

- Quando esisterà una `LegalSource` prescrizione: un test che il termine pubblico
  appaia **solo** se la fonte è `approved` (fail-closed come per il TUN).
- Test che ogni `case_type` prescrizione mostri sempre i **modificatori** e il
  disclaimer accanto a qualunque termine.
- Test di provenance/hash sul PDF consolidato (come `calculation_provenance` TUN).
- Test che la prescrizione **non** entri mai nel motore di calcolo dell'importo.

---

## 8. Cosa resta da validare da un professionista (Studio)

1. Testo **consolidato vigente** di ogni articolo (F1–F5) su Normattiva.
2. Decorrenza e qualificazione per ciascun `case_type` (specie sanità e penale).
3. Posizione su danno differenziale INAIL e su omicidio/lesioni come reato.
4. Trattamento DIP per i casi internazionali (lex causae).
5. Decisione GO/NO-GO sulla creazione delle `LegalSource` e firma delle review.

---

## 9. Conferma: il sito non inventa termini

- Pubblico: nessuna cifra di prescrizione (verificato: `_prescrizione_notice.html`
  non contiene cifre/anni/articoli).
- Calcolatore: la prescrizione **non** è usata per stimare o bloccare (nessuna
  modifica a `apps/calculators` / `apps/compensation`).
- Registry: invariato; solo IT `road_accident` (TUN 2025) calcola; FR/BE/MA/TN
  restano `unavailable_requires_legal_validation`.
- Nessun termine elevato a `approved`. I termini in questo documento sono
  **candidati interni** da validare.

---

## Fonti consultate (istituzionali)

- Codice Civile art. 2947 — gazzettaufficiale.it (cod. red. `042U0262`); commento art. 2935/2943.
- D.P.R. 1124/1965 art. 112 — normattiva.it (urn `presidente.repubblica:decreto:1965-06-30;1124`); gazzettaufficiale.it `065U1124`; circolari INAIL (sospensione, Cass. SU 11928/2019).
- D.Lgs. 206/2005 (Codice del Consumo) artt. 125–126 — normattiva.it `005G0232/CONSOLIDATED`; gazzettaufficiale.it `005G0232`.
- D.Lgs. 209/2005 (CAP) artt. 144–148 — normattiva.it `005G0233`; ivass.it `Cap.pdf`.
- L. 24/2017 (Gelli-Bianco); Reg. (CE) 864/2007 (Roma II) — gazzettaufficiale.it / EUR-Lex.

*Disclaimer: le URL e i riferimenti sono istituzionali; il testo vigente va
verificato dallo Studio. Questo audit è read-only e non costituisce parere
legale.*
