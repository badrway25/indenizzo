# Francia — modulo decisione firma legale

**Iter**: `STUDIO-1-france-review-session-pack`.
**Data riunione**: _____________________
**Verbalizzante**: _____________________
**Partecipanti**: ___________________________________

Modulo da compilare durante o subito dopo la riunione descritta in `FRANCE_REVIEW_MEETING_AGENDA.md`. Il dev attiverà Francia solo dopo aver ricevuto questo modulo **firmato in sezione F** con esito GO o GO-con-correzioni. NO-GO ferma il progetto Francia in modo ordinato.

Per ogni decisione: indicare l'esito (approvato / respinto / da correggere), eventuali note, il reviewer responsabile e la data. Se per una decisione si scrive "da correggere", indicare nello spazio note **cosa correggere** in modo che il dev possa eseguire la correzione e tornare a un secondo passaggio della stessa decisione.

---

## A — Référentiel Mornet 2024

Documento sotto review:

- **Titolo**: Référentiel indicatif d'indemnisation par les Cours d'Appel — édition Mornet 2024.
- **Natura**: barème indicatif privato, non normativo.
- **Slug nel sistema**: `fr-referentiel-mornet-2024`.
- **File archiviato**: `legal_data/sources/france/downloaded/fr-referentiel-mornet-2024.pdf`.
- **Righe estratte usabili**: 191 (180 DFP per età × invalidità + 11 préjudice d'affection per relazione).

Cosa firma lo Studio:

- l'uso di Mornet 2024 come *fonte quantitativa indicativa* per il calcolo del Déficit Fonctionnel Permanent;
- l'esplicita accettazione che la piattaforma dichiari nel disclaimer la natura non-normativa di Mornet;
- il livello di affidabilità che verrà visualizzato pubblicamente: `HIGH` (non `OFFICIAL`).

Esito (segnare):

- [ ] Approvato
- [ ] Approvato con correzioni
- [ ] Respinto

Note Studio:

> _______________________________________________________________________________
> _______________________________________________________________________________
> _______________________________________________________________________________

Reviewer (nome + ruolo): _____________________
Data firma: _____________________
Firma / iniziali: _____________________

---

## B — Barème de capitalisation Gazette du Palais 2022

Documento sotto review:

- **Titolo**: Barème de capitalisation — Gazette du Palais, édition 2022.
- **Natura**: tabella di capitalizzazione derivata da jurisprudence consolidata, non normativa.
- **Slug nel sistema**: `fr-bareme-capitalisation-gazette-palais-2022`.
- **File archiviato**: `legal_data/sources/france/downloaded/fr-bareme-capitalisation-gazette-palais-2022.pdf`.
- **Righe estratte usabili**: 4 188 (coefficienti per età × sesso × tasso, viagère + temporaire + anticipated).

Cosa firma lo Studio:

- l'uso di Gazette 2022 come base di capitalizzazione di rendite vitalizie e temporanee in Francia.

Promemoria: la Gazette **non rientra nel v1** del calcolatore (che copre solo il DFP nominale, non la capitalizzazione di rendite). Si firma comunque ora per evitare una seconda sessione di review quando il v2 sarà sviluppato.

Esito (segnare):

- [ ] Approvato
- [ ] Approvato con correzioni
- [ ] Respinto

Note Studio:

> _______________________________________________________________________________
> _______________________________________________________________________________
> _______________________________________________________________________________

Reviewer (nome + ruolo): _____________________
Data firma: _____________________
Firma / iniziali: _____________________

---

## C — Nomenclature Dintilhac 2005

Documento sotto review:

- **Titolo**: Nomenclature des postes de préjudice corporel — Rapport du groupe de travail dirigé par J.-P. Dintilhac, 2005.
- **Natura**: classificazione tassonomica dei *postes* di pregiudizio, riferimento de facto della prassi giudiziaria francese.
- **Slug nel sistema**: `fr-nomenclature-dintilhac-2005`.
- **File archiviato**: `legal_data/sources/france/downloaded/fr-nomenclature-dintilhac-2005.html`.

Cosa firma lo Studio:

- l'uso della nomenclatura Dintilhac per organizzare il report PDF Francia per *postes* di pregiudizio (DFP, DFT, Souffrances endurées, Préjudice esthétique, Préjudice d'affection, ecc.).
- l'accettazione che, per le voci non quantificate automaticamente dal calcolatore v1, il report mostri esplicitamente "richiede valutazione Studio".

Esito (segnare):

- [ ] Approvato
- [ ] Approvato con correzioni
- [ ] Respinto

Note Studio:

> _______________________________________________________________________________
> _______________________________________________________________________________
> _______________________________________________________________________________

Reviewer (nome + ruolo): _____________________
Data firma: _____________________
Firma / iniziali: _____________________

---

## D — Disclaimer Francia

Documento sotto review:

- **Testo proposto** (versione 2026-05-12, italiano + francese — bozza):

> «Cette simulation est indicative. Elle ne constitue ni un avis juridique, ni une expertise médico-légale, ni une garantie de résultat. Le calcul est basé sur le Référentiel Mornet 2024 (barème indicatif des Cours d'Appel) appliqué dans le cadre de la Loi Badinter du 5 juillet 1985. Le résultat dépend en réalité des pièces médicales, des expertises, du jugement de responsabilité, du tribunal compétent et de la jurisprudence locale. Pour une évaluation engageante, le Studio Legale Internazionale Badrane vous accompagne dans une revue manuelle de votre dossier.»

Cosa firma lo Studio:

- la controfirma del testo sopra (eventualmente con modifiche puntuali nelle note), oppure
- la sostituzione completa con un testo redatto direttamente dallo Studio (allegare separatamente e indicare nelle note il riferimento all'allegato).

Esito (segnare):

- [ ] Approvato (testo §D sopra invariato)
- [ ] Approvato con correzioni (annotare le modifiche nello spazio note)
- [ ] Sostituito da testo Studio (allegare riferimento)
- [ ] Respinto

Testo finale o riferimento allegato:

> _______________________________________________________________________________
> _______________________________________________________________________________
> _______________________________________________________________________________
> _______________________________________________________________________________

Lingue da localizzare (segnare quelle che verranno tradotte automaticamente — IT/EN/AR — vs quelle che lo Studio vuole controfirmare individualmente):

- [ ] Italiano — controfirma Studio richiesta
- [ ] Inglese — controfirma Studio richiesta
- [ ] Arabo — controfirma Studio richiesta
- [ ] Traduzione automatica (sistema `locale/`) accettata per le lingue non controfirmate

Reviewer (nome + ruolo): _____________________
Data firma: _____________________
Firma / iniziali: _____________________

---

## E — Smoke test numbers

Per ognuno dei 3 casi qui sotto, lo Studio dichiara il range €min/€mid/€max atteso. Questi numeri diventeranno il **smoke test bloccante** del deploy: il calcolatore Francia non parte se non li riproduce identici al deploy. Un cambio futuro (es. Mornet 2025) richiede una nuova firma in una sessione successiva.

> **Nota**: lo Studio può scegliere se firmare *valori puntuali* (€min/€mid/€max definiti) oppure *intervalli ammessi* (es. "€min compreso tra X e Y va bene"). Indicarlo esplicitamente nello spazio note per ciascun caso.

### E.1 — Caso lieve (35 × 5 × 0)

Input:

| Campo | Valore |
|---|---|
| `victim_age` | 35 |
| `permanent_disability_percentage` | 5 |
| `fault_percentage` | 0 |

Output atteso firmato Studio:

| Campo | Valore atteso (€) |
|---|---|
| `estimated_min` | _____________ |
| `estimated_mid` | _____________ |
| `estimated_max` | _____________ |

Tolleranze ammesse (se valori puntuali troppo rigidi):

> _______________________________________________________________________________
> _______________________________________________________________________________

Reviewer (nome + ruolo): _____________________
Data firma: _____________________

### E.2 — Caso grave (45 × 30 × 0)

Input:

| Campo | Valore |
|---|---|
| `victim_age` | 45 |
| `permanent_disability_percentage` | 30 |
| `fault_percentage` | 0 |

Output atteso firmato Studio:

| Campo | Valore atteso (€) |
|---|---|
| `estimated_min` | _____________ |
| `estimated_mid` | _____________ |
| `estimated_max` | _____________ |

Tolleranze ammesse:

> _______________________________________________________________________________
> _______________________________________________________________________________

Reviewer (nome + ruolo): _____________________
Data firma: _____________________

### E.3 — Caso concorso di colpa (60 × 15 × 25)

Input:

| Campo | Valore |
|---|---|
| `victim_age` | 60 |
| `permanent_disability_percentage` | 15 |
| `fault_percentage` | 25 |

Output atteso firmato Studio:

| Campo | Valore atteso (€) |
|---|---|
| `estimated_min` | _____________ |
| `estimated_mid` | _____________ |
| `estimated_max` | _____________ |

Tolleranze ammesse:

> _______________________________________________________________________________
> _______________________________________________________________________________

Conferma: la riduzione del 25 % per concorso di colpa va applicata linearmente a tutto il range (€min × 0.75, €mid × 0.75, €max × 0.75)?

- [ ] Sì
- [ ] No (specificare alternativa nello spazio note sopra)

Reviewer (nome + ruolo): _____________________
Data firma: _____________________

---

## F — Decisione finale di sessione

L'esito complessivo della sessione, considerando A + B + C + D + E:

- [ ] **GO** — tutte le 4 firme legali (A, B, C, D) sono in stato "approvato" e tutti e 3 i numeri smoke (E.1, E.2, E.3) sono firmati. Il dev può procedere all'attivazione seguendo `FRANCE_ACTIVATION_AFTER_SIGNOFF_CHECKLIST.md`.

- [ ] **GO con correzioni** — una o più decisioni richiedono correzioni puntuali (testo da rivedere, range da rinegoziare, ecc.) **ma non rimettono in discussione l'attivazione complessiva**. Il dev attende il follow-up sulle correzioni e poi procede.

  Correzioni richieste prima dell'attivazione:

  > ____________________________________________________________________________
  > ____________________________________________________________________________
  > ____________________________________________________________________________

  Termine atteso per le correzioni: _____________________

- [ ] **NO-GO** — la sessione decide di non attivare la Francia in questa fase. Le ragioni sono qui sotto. La piattaforma resta review-gated. Il prossimo lavoro prodotto si concentra altrove (Belgio, miglioramento del percorso utente, ecc.).

  Ragione del NO-GO:

  > ____________________________________________________________________________
  > ____________________________________________________________________________
  > ____________________________________________________________________________

  Quando rivedere la decisione: _____________________

### Firma di sezione F

Reviewer responsabile (nome + ruolo): _____________________
Data firma: _____________________
Firma / iniziali: _____________________

---

## Allegati / link

- Riassunto 1 pagina: `docs/studio/FRANCE_REVIEW_ONE_PAGE_SUMMARY.md`
- Ordine del giorno: `docs/studio/FRANCE_REVIEW_MEETING_AGENDA.md`
- Checklist dev post-firma: `docs/studio/FRANCE_ACTIVATION_AFTER_SIGNOFF_CHECKLIST.md`
- Pacchetto operativo (~13 KB): `docs/product/FRANCE_ACTIVATION_SIGNOFF_PACK.md`
- Matrice test e2e (~7 KB): `docs/product/FRANCE_E2E_TEST_MATRIX.md`
