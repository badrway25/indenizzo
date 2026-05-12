# Riunione Studio — sessione di review legale Francia

**Per**: Studio Legale Internazionale Badrane.
**Iter**: `STUDIO-1-france-review-session-pack`.
**Data documento**: 2026-05-12.
**Documento ponte**: collega lo Studio ai 4 documenti che richiedono firma. Va letto **prima** della riunione.

---

## 1. Obiettivo della riunione

Decidere, in una sola sessione, se la piattaforma può iniziare a pubblicare stime indicative del danno corporale francese (incidenti stradali, Loi Badinter) e in quali termini.

L'esito atteso è uno di tre:

- **GO** — Studio firma tutto, il dev procede all'attivazione (~1 giorno di lavoro).
- **GO con correzioni** — Studio firma con riserve specifiche (es. disclaimer da riscrivere, range invece di valori puntuali, ecc.). Il dev applica le correzioni e l'attivazione segue.
- **NO-GO** — Studio ritiene che le fonti non siano adeguate alla pubblicazione. La piattaforma resta review-gated, la Francia non viene attivata, si valutano alternative (Belgio, ulteriore lavoro su Mornet, ecc.).

In tutti e tre i casi la decisione viene **tracciata** in `FRANCE_SIGNOFF_DECISION_FORM.md`. Anche un NO-GO è un esito formale che ferma il progetto in modo ordinato.

## 2. Cosa è già pronto (parte tecnica)

- **Pagina Francia online**: `/countries/france/` rende l'attuale "valutazione legale preliminare", senza pubblicare importi. Già visibile a chiunque sul sito.
- **Wizard Francia online**: `/wizard/fr/road-accident/` rende il form di input, accetta la submission, mostra la pagina di "preliminary legal assessment", **non emette numeri**.
- **Calcolatore Francia in codice**: scritto, testato (1 600+ righe di test), 12 gate di sicurezza. Oggi tutti e 12 i gate falliscono per design (fonti `needs_review` → primo gate blocca).
- **4 fonti già archiviate localmente**: PDF di Mornet 2024, Gazette du Palais 2022, Nomenclature Dintilhac 2005, Loi Badinter 1985. La Loi Badinter è già controfirmata meccanicamente (11/11 marcatori strutturali verificati).
- **Estrazione dati**: 191 righe Mornet (DFP × età × invalidità + préjudice d'affection per relazione) e 4 188 righe Gazette (coefficienti di capitalizzazione per età × sesso × tasso) sono in database come `DRAFT`.
- **Audit script read-only**: lo stato della catena è ispezionabile in qualunque momento via `python scripts/legal_data/audit_france_activation_readiness.py`.

## 3. Cosa NON è ancora attivo

- Nessun importo viene pubblicato sulla Francia. Il calcolatore è in stato "review-gated".
- Le 3 fonti quantitative (Mornet 2024, Gazette 2022, Dintilhac 2005) sono in stato `needs_review` — la piattaforma non le considererà autorevoli finché lo Studio non firma.
- Nessuna `CalculationFormula(France)` è registrata. Anche se le fonti fossero promosse, manca questo step per produrre numeri.
- Il disclaimer Francia-specifico (se distinto da quello generico) non è ancora stato firmato.

## 4. Cosa deve essere deciso

Quattro firme legali + tre numeri.

### 4.1 Firme

| # | Decisione |
|---|---|
| A | **Référentiel Mornet 2024**: accettare/respingere come fonte quantitativa indicativa del DFP, ammettendo che è un barème privato (non normativo). |
| B | **Gazette du Palais 2022**: accettare/respingere come base di capitalizzazione di rendite future, ammettendo che è jurisprudence consolidata (non normativa). |
| C | **Nomenclature Dintilhac 2005**: accettare per organizzare il report PDF per *postes* di pregiudizio. |
| D | **Disclaimer Francia**: controfirmare il testo proposto §6 del pacchetto operativo o sostituirlo con redazione Studio. |

Per ciascuna decisione lo Studio annota: la persona responsabile (reviewer), la data, eventuali note o correzioni.

### 4.2 Numeri smoke test

| Caso | Input | €min atteso | €mid atteso | €max atteso |
|---|---|---|---|---|
| 1 — lieve | età 35, invalidità 5 %, colpa 0 % | (firma) | (firma) | (firma) |
| 2 — grave | età 45, invalidità 30 %, colpa 0 % | (firma) | (firma) | (firma) |
| 3 — concorso colpa | età 60, invalidità 15 %, colpa 25 % | (firma) | (firma) | (firma) |

Per ognuno dei 3 casi lo Studio fornisce il range atteso. Se preferisce valori puntuali, basta indicare un singolo numero per ciascuno dei min/mid/max. Se preferisce un range "fino a", indicarlo.

Questi numeri diventeranno il **smoke test bloccante** del deploy. Un cambio futuro richiede una nuova firma.

## 5. Ordine consigliato della riunione

| Tempo | Attività | Note |
|---|---|---|
| 0 — 5 min | Apertura, riepilogo del progetto, obiettivo della sessione | usare `FRANCE_REVIEW_ONE_PAGE_SUMMARY.md` |
| 5 — 10 min | Apertura del wizard Francia oggi su un browser | per ogni partecipante è chiaro cosa l'utente vede ora |
| 10 — 25 min | Discussione Référentiel Mornet 2024 (decisione A) | apertura del PDF allegato + checklist 24 voci `france_legal_review_checklist_template.csv` |
| 25 — 35 min | Discussione Gazette du Palais 2022 (decisione B) | apertura del PDF allegato |
| 35 — 45 min | Discussione Dintilhac 2005 (decisione C) | apertura del documento, verifica che le voci coprano i postes che lo Studio si aspetta |
| 45 — 55 min | Disclaimer Francia (decisione D) | leggere ad alta voce il testo proposto al §6 del pacchetto operativo; ritocchi se necessari |
| 55 — 70 min | Smoke test numbers (decisioni E1, E2, E3) | per ognuno dei 3 casi, lo Studio dichiara il range atteso |
| 70 — 80 min | Decisione finale (F) e firma del documento | compilare `FRANCE_SIGNOFF_DECISION_FORM.md`, salvare PDF/scan |
| 80 — 85 min | Chiusura: cosa farà il dev, in che tempi | usare `FRANCE_ACTIVATION_AFTER_SIGNOFF_CHECKLIST.md` |

Durata totale stimata: **~1 ora e mezza**. La parte critica è la discussione su Mornet (A): il barème ha alcune scelte editoriali (es. valori per fasce di età ai limiti, scala di affection) che richiedono giudizio Studio.

## 6. Domande da porre allo Studio (lista preparatoria)

Domande tecniche-legali pronte per la sessione, raggruppate per decisione:

### Su Mornet 2024 (A)

1. Accettiamo Mornet 2024 come fonte indicativa primaria del DFP, sapendo che è privato e non vincolante?
2. Vogliamo escludere fasce di età o di invalidità che lo Studio considera insufficientemente documentate? (Es. invalidità > 80 % o età > 85)
3. La reliability dichiarata sulla pagina pubblica sarà **HIGH** (non OFFICIAL). Va bene il wording "barème indicatif des Cours d'Appel" o vogliamo qualcosa di più o meno enfatico?
4. Vogliamo aggiornare a Mornet 2025 quando uscirà? In che tempi?

### Su Gazette du Palais 2022 (B)

1. Accettiamo Gazette 2022 come base di capitalizzazione per le rendite vitalizie/temporanee?
2. C'è una versione più recente che riteniamo prevalente?
3. La capitalizzazione NON entra nel v1 — è OK firmare ora per evitare una doppia sessione?

### Su Dintilhac 2005 (C)

1. Vogliamo il PDF organizzato per le 12 voci classiche Dintilhac o vogliamo una sintesi (DFP + altri pregiudizi + altri costi)?
2. Per le voci che il calcolatore non quantifica (souffrances endurées, esthétique, ecc.), vogliamo che il report dica "richiede valutazione Studio" o vogliamo un wording diverso?

### Su Disclaimer Francia (D)

1. Il testo proposto è adeguato? Se no, lo riscrive lo Studio o ne suggerisce le correzioni?
2. Lingue: oltre al francese e all'italiano, vogliamo che la versione araba e inglese siano controfirmate?
3. Aggiorniamo il disclaimer ogni volta che cambia una fonte, o teniamo una versione stabile? (Tecnicamente sostenibile fare una versione `DISCLAIMER_FRANCE_VERSION = 2026-05` che si incrementa.)

### Su smoke numbers (E)

1. Per il caso 35 × 5 × 0, lo Studio fornisce un range puntuale (es. €min = X, €mid = Y, €max = Z), oppure preferisce intervalli di tolleranza (es. "tra A e B")?
2. Per il caso 60 × 15 × 25, vogliamo che la riduzione del 25 % si applichi linearmente a tutto il range, o c'è una clausola di non-riduzione sotto una certa soglia di colpa (es. < 10 %)?
3. Lo Studio vuole un quarto caso smoke test in più? (Es. soggetto > 80 anni, o invalidità 50 %?)

## 7. Rischi se si attiva senza firma

Per chiarezza: **questo è ciò che accadrebbe se qualcuno bypassasse la firma e accendesse il calcolatore Francia**. Le firme servono proprio per evitarne ognuno.

1. **Numeri inventati pubblicati**: la regola d'oro del progetto è violata. Una stima Mornet senza firma significa che la piattaforma sostiene una scelta editoriale che lo Studio non ha autorizzato.
2. **Esposizione professionale**: il sito è collegato al sito madre dello Studio. Un numero falso pubblicato in suo nome ricade legalmente sullo Studio.
3. **Disclaimer inadeguato**: il disclaimer attuale è generico. Per Francia serve un testo specifico che chiarisca la natura non-normativa di Mornet/Gazette. Senza firma, il disclaimer non c'è.
4. **Audit trail incompleto**: il system check `jurisdictions.E001` fallisce in produzione se una `LegalSource` è `APPROVED` senza la `LegalReview(decision=APPROVE)` corrispondente. Quindi tecnicamente non si arriva neppure al deploy.
5. **Rollback difficile**: una volta che un numero è pubblicato, anche per un'ora, è ufficialmente "stato pubblicato". Il rollback tecnico richiede 5 minuti; il rollback reputazionale è un'altra cosa.

Per tutte queste ragioni il sistema impedisce attivamente l'attivazione sulla base del solo PR. Servono 4 firme + 3 numeri.

## 8. Output atteso della riunione

Al termine della sessione lo Studio consegna:

1. `FRANCE_SIGNOFF_DECISION_FORM.md` compilato con A/B/C/D/E1-3/F firmati (PDF scansionato o file Markdown editato direttamente — entrambi vanno bene).
2. Eventuali documenti accessori firmati (es. nuovo testo del disclaimer se sostituito).
3. Una conferma esplicita di **chi è il legal reviewer** (FK utente nel sistema) per ciascuna firma — può essere la stessa persona per le 4 decisioni o persone diverse.

Il dev poi:

1. Riceve `FRANCE_SIGNOFF_DECISION_FORM.md` firmato.
2. Apre il branch `P0-MVP-1-ACTIVATE-france`.
3. Segue `FRANCE_ACTIVATION_AFTER_SIGNOFF_CHECKLIST.md` (passo per passo, ~20 minuti in admin + ~1-2 ore di test + smoke).
4. Apre un PR che attiva la Francia. Una review interna lo verifica. Merge.
5. Deploy staging, Studio verifica sul sito, dopo 24 h deploy prod.

## 9. Cosa NON si decide in questa riunione

Per evitare scope creep:

- Belgio: scope separato (ha bisogno di OCR del Tableau Indicatif 2024 — non disponibile sul dev oggi).
- Marocco / Tunisia: scope ancora più separato (richiedono trascrizione di share numeriche non ancora estratte + decisioni doctrinali su conflitto di leggi).
- Tabelle italiane: già firmate, in produzione, fuori scope.
- Calcolatore inheritance (successioni): fuori scope.
- Disclaimer generico della piattaforma: già firmato, fuori scope (qui si decide solo l'eventuale addendum Francia).

Se durante la riunione emergono altri argomenti, andrebbero parcheggiati in una lista "follow-up" piuttosto che decisi in questa sessione.

---

## Allegati / link

- Riassunto 1 pagina: `docs/studio/FRANCE_REVIEW_ONE_PAGE_SUMMARY.md`
- Modulo decisione: `docs/studio/FRANCE_SIGNOFF_DECISION_FORM.md`
- Checklist dev post-firma: `docs/studio/FRANCE_ACTIVATION_AFTER_SIGNOFF_CHECKLIST.md`
- Pacchetto operativo (~13 KB): `docs/product/FRANCE_ACTIVATION_SIGNOFF_PACK.md`
- Matrice test e2e (~7 KB): `docs/product/FRANCE_E2E_TEST_MATRIX.md`
- Audit tecnico read-only: `docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md`
- Review package tecnico legale (DRAFT, ~26 KB): `docs/architecture/FRANCE_LEGAL_REVIEW_PACKAGE.md`
- Checklist tabellare Mornet (24 voci): `legal_data/sources/france/review/france_legal_review_checklist_template.csv`
- Screenshot stato attuale: `docs/screenshots/delta_audit_2026-05-10/after/product-france-signoff-pack/`
