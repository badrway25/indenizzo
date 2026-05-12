# France — activation signoff pack

**Per**: Studio Legale Internazionale Badrane
**Iter**: `PRODUCT-1-france-activation-signoff-pack`
**Data**: 2026-05-12
**Branch**: `product/france-activation-signoff-pack`

Documento operativo. Destinato a chi firma legalmente — non solo al
team tecnico. La piattaforma può iniziare a pubblicare stime
indicative sulla Francia **dopo** la firma di 4 documenti elencati
qui sotto. Senza quelle firme la piattaforma resta in "preliminary
legal assessment" e non pubblica nessun numero.

Questo documento descrive:

1. cosa è già pronto e visibile sul sito;
2. cosa NON è attivo e perché;
3. cosa serve firmare e perché serve quella firma;
4. su quali dati il calcolatore lavorerà dopo la firma;
5. quali sono i limiti del calcolatore francese;
6. quale sarà il disclaimer specifico Francia;
7. tre casi-test fittizi che la piattaforma userà come smoke test;
8. cosa l'utente vede prima e dopo l'attivazione;
9. checklist firma Studio (i 4 documenti);
10. checklist tecnica successiva alla firma.

Un secondo documento di supporto, `FRANCE_ACTIVATION_DEV_PLAN.md`,
contiene il piano operativo lato sviluppo (cosa fa il dev dopo che
le 4 firme arrivano). Un terzo, `FRANCE_E2E_TEST_MATRIX.md`, elenca
i casi-test che la piattaforma esegue automaticamente al deploy.

---

## 1. Cosa è già pronto

| Componente | Stato | Visibile a chi |
|---|---|---|
| Pagina "Francia" sul sito pubblico | online | utenti finali |
| Wizard Francia "incidente stradale — danno corporale" | online (form compilabile, nessun calcolo) | utenti finali |
| Disclaimer generico piattaforma | online | utenti finali |
| Loi Badinter 1985 — testo ufficiale archiviato | scaricato, validato meccanicamente 11/11 marcatori | staff |
| Référentiel Mornet 2024 — file PDF archiviato | scaricato, **non firmato Studio** | staff |
| Gazette du Palais 2022 — file PDF archiviato | scaricato, **non firmato Studio** | staff |
| Nomenclature Dintilhac 2005 — testo archiviato | scaricato, **non firmato Studio** | staff |
| Dataset DRAFT Mornet 2024 in DB | 191 righe estratte | staff |
| Dataset DRAFT Gazette 2022 in DB | 4 188 righe estratte | staff |
| Calcolatore Francia | classe registrata, ma **gating attivo** → non produce importi | nessuno |
| Test automatici di stato "review-gated" | 1 600+ righe; verificano che Francia NON pubblichi numeri | sviluppo |

In altre parole: la macchina è pronta a partire, il combustibile è
nel serbatoio, l'accensione richiede la firma autorizzata.

## 2. Cosa NON è attivo e perché

| Cosa | Perché non è attivo |
|---|---|
| Calcolo automatico di un range €min/€mid/€max per la Francia | Le 3 fonti quantitative (Mornet, Gazette, Dintilhac) sono in stato `needs_review`. Senza una *LegalReview* firmata da una persona dello Studio, la piattaforma rifiuta di emettere numeri. |
| Promozione del dataset Mornet 2024 a "approved" | Subordinata alla firma di Mornet. La piattaforma rifiuta di scrivere in un dataset non-DRAFT senza il via libera firmato. |
| Promozione del dataset Gazette 2022 a "approved" | Idem. |
| Mappatura postes Dintilhac sul report PDF | Senza la firma Dintilhac, il PDF Francia mostra solo "valutazione preliminare", non singoli postes. |
| Disclaimer France-specifico | Oggi viene mostrato il disclaimer generico della piattaforma. Lo Studio decide se basta o serve un addendum. |

**Regola d'oro del progetto**: meglio nessun calcolo che un calcolo
falso. Nessuna delle 4 firme è un atto puramente burocratico — ogni
firma stabilisce una scelta editoriale che lo Studio si assume.

## 3. Cosa serve firmare e perché serve

### 3.1 Référentiel Mornet 2024 (priorità: 1, gating)

- **Documento**: Référentiel indicatif d'indemnisation par les
  Cours d'Appel, edizione Mornet 2024, ~191 righe utilizzabili
  (Déficit Fonctionnel Permanent × età × % d'invalidità +
  Préjudice d'Affection per relazione familiare).
- **Natura**: barème *privato*, non pubblicato dallo Stato. È la
  tabella tipicamente usata dai magistrati francesi come
  riferimento orientativo.
- **Cosa firma lo Studio**: che la piattaforma può usare Mornet
  2024 come *fonte quantitativa indicativa* per il danno biologico
  e parentale, con l'esplicito disclaimer che non è normativa.
- **Effetto della firma**: sblocca la possibilità di produrre un
  range €min/€mid/€max per il **Déficit Fonctionnel Permanent**
  (DFP) e per il **préjudice d'affection** dei parenti.
- **Senza la firma**: nessun importo Francia, mai. Gating attivo
  al primo livello.

### 3.2 Gazette du Palais 2022 (priorità: 2, condizionale)

- **Documento**: Barème de capitalisation, Gazette du Palais
  edizione 2022, 4 188 righe (coefficienti di capitalizzazione
  vitalizia + temporanea + anticipata, per età × sesso × tasso).
- **Natura**: tabella derivata dalla giurisprudenza, hand-curata,
  usata per capitalizzare rendite vitalizie (perte de gains
  professionnels futurs, tierce personne).
- **Cosa firma lo Studio**: che la Gazette 2022 può essere usata
  come base di capitalizzazione, con il disclaimer che è basata
  su jurisprudence consolidata ma non su un decreto.
- **Effetto della firma**: sblocca il calcolo della
  capitalizzazione di rendite/spese future (non rientra nella v1
  del calcolatore: viene attivata in iter successivo).
- **Senza la firma**: la v1 funziona comunque su DFP + préjudice
  d'affection. La Gazette è necessaria solo per estensioni
  successive (rendite vitalizie).

> **Per la v1 (DFP + préjudice d'affection)**, la firma della
> Gazette del Palais può tecnicamente attendere. Si firma comunque
> ora perché lo Studio non vuole una doppia tornata di review e
> perché la documentazione pubblica deve essere completa il giorno
> dell'attivazione.

### 3.3 Nomenclature Dintilhac 2005 (priorità: 3, report)

- **Documento**: Nomenclature dei *postes* di pregiudizio
  redatta dal gruppo Dintilhac (2005), ufficiale di fatto nella
  prassi giudiziaria francese.
- **Cosa firma lo Studio**: che la piattaforma può strutturare il
  report Francia secondo le voci Dintilhac (DFP, DFT, Souffrances
  endurées, Préjudice esthétique, Préjudice d'affection, ecc.).
- **Effetto della firma**: il PDF Francia mostra il calcolo
  organizzato per *poste* — non come totale piatto.
- **Senza la firma**: il report PDF è generico ("totale stimato"
  senza voce-per-voce).

### 3.4 Disclaimer Francia (priorità: 4, copy)

- **Documento**: stringa di disclaimer Francia, scritta dallo
  Studio o controfirmata se basta quella generica della
  piattaforma.
- **Stato attuale**: oggi il sito mostra il disclaimer generico
  italiano ("La simulazione è indicativa e non costituisce parere
  legale, medico-legale o garanzia di risultato…").
- **Cosa firma lo Studio**: o controfirma il testo generico
  esistente, o redige una versione Francia-specifica che
  esplicita: Loi Badinter come cornice; Mornet/Gazette come
  barèmes indicativi non normativi; nomenclature Dintilhac;
  raccomandazione di revisione caso-per-caso.
- **Effetto della firma**: il disclaimer è ciò che il consumatore
  legge prima di vedere una stima — deve essere lo Studio a
  scriverlo.

## 4. Su quali dati lavorerà il calcolatore

Dopo le 4 firme, la prima versione del calcolatore Francia userà:

| Input utente | Dato di lookup | Fonte |
|---|---|---|
| `victim_age` (età alla data dell'incidente) | DFP punto-valore per età | Mornet 2024 |
| `permanent_disability_percentage` (% invalidità) | DFP punto-valore per % | Mornet 2024 |
| `fault_percentage` (concorso di colpa) | riduzione applicata uniformemente al range min/mid/max | Loi Badinter (cornice) |
| Relazione familiare (estensioni v2) | Préjudice d'affection per relazione | Mornet 2024 |

La regola di calcolo della v1 è la stessa pattern già usata per
l'Italia: *single-row range* — la tabella Mornet 2024 contiene
direttamente le coppie (età × invalidità → valore-punto), il
calcolatore non interpola fra righe (per evitare di inventare
numeri intermedi).

## 5. Limiti dichiarati del calcolatore Francia v1

| Limite | Conseguenza |
|---|---|
| Solo *Déficit Fonctionnel Permanent* | spese mediche, perdite reddito, danni patrimoniali, capitalizzazione di rendite **non sono inclusi** nel range automatico. Vengono elencati come "missing documents" / "requires legal review" per la valutazione manuale dello Studio. |
| Nessuna interpolazione | se l'età o l'invalidità sono fuori dalla griglia Mornet (es. invalidità al 11.5 %), il calcolatore restituisce "valutazione preliminare", non un'approssimazione. |
| Reliability = MEDIUM | Mornet non è un decreto. Il public copy lo dichiara esplicitamente. Italia, in confronto, è HIGH/OFFICIAL (TUN). |
| Nessun *Souffrances endurées* / *Préjudice esthétique* | richiedono valutazione caso-per-caso da Studio. Restano fuori dalla v1. |
| Nessuna capitalizzazione | la Gazette si firma per le iter successive. v1 restituisce il valore-DFP nominale, non capitalizzato. |
| Concorso di colpa applicato lineare | come Italia. Se il modello francese richiede una formula diversa, va segnalato in fase di firma. |

## 6. Disclaimer Francia — testo proposto

Bozza, da rivedere/firmare dallo Studio. Pubblicabile così com'è
oppure dopo modifiche.

> «Cette simulation est indicative. Elle ne constitue ni un avis
> juridique, ni une expertise médico-légale, ni une garantie de
> résultat. Le calcul est basé sur le Référentiel Mornet 2024
> (barème indicatif des Cours d'Appel) appliqué dans le cadre de
> la Loi Badinter du 5 juillet 1985. Le résultat dépend en réalité
> des pièces médicales, des expertises, du jugement de
> responsabilité, du tribunal compétent et de la jurisprudence
> locale. Pour une évaluation engageante, le Studio Legale
> Internazionale Badrane vous accompagne dans une revue manuelle
> de votre dossier.»

(Versione italiana / inglese / araba: gestita dal sistema di
traduzione esistente — `locale/fr/`, `locale/it/`, ecc.)

## 7. Tre casi-test fittizi (smoke test)

Casi sintetici che la piattaforma userà come *smoke test* al
deploy. Servono allo Studio per validare che i numeri prodotti
siano nel range atteso.

### Caso 1 — accident lieve

| Campo | Valore |
|---|---|
| `victim_age` | 35 |
| `permanent_disability_percentage` | 5 |
| `fault_percentage` | 0 |
| Atteso (qualitativo) | Mornet → DFP basso (giovane, bassa invalidità) → range di alcuni migliaia di € |
| Disclaimer | testo §6 |
| Output del wizard | "Stima indicativa: €min — €mid — €max + breakdown DFP" |

### Caso 2 — accident grave

| Campo | Valore |
|---|---|
| `victim_age` | 45 |
| `permanent_disability_percentage` | 30 |
| `fault_percentage` | 0 |
| Atteso | Mornet → DFP medio-alto → range di alcune decine di migliaia di € |
| Output del wizard | "Stima indicativa: €min — €mid — €max + breakdown DFP" |

### Caso 3 — accident con concorso di colpa

| Campo | Valore |
|---|---|
| `victim_age` | 60 |
| `permanent_disability_percentage` | 15 |
| `fault_percentage` | 25 |
| Atteso | Mornet → DFP × 0.75 (riduzione lineare per fault 25 %) |
| Output del wizard | "Stima indicativa con riduzione concorso colpa" |

I valori numerici attesi saranno fissati dallo Studio in fase di
firma (allegando, per ciascuno dei 3 casi, il range €min/€mid/€max
considerato corretto). Il dev poi committa quei tre numeri come
*locked smoke test* — un cambio futuro di Mornet aggiornerà i
numeri solo se lo Studio firma un nuovo iter.

Casi-test estesi (pedone, passeggero, dati incompleti, caso
non-calcolabile) sono in `FRANCE_E2E_TEST_MATRIX.md`.

## 8. Cosa vede l'utente — prima e dopo

### Oggi (review-gated)

- Apertura `/wizard/fr/road-accident/`: form compilabile.
- Submit: nessun importo. Messaggio "Valutazione preliminare
  legale — gli importi non vengono pubblicati prima della
  verifica delle fonti per il caso specifico".
- CTA verso il contatto Studio.
- Disclaimer generico.

### Dopo le 4 firme (attivato)

- Apertura `/wizard/fr/road-accident/`: form compilabile (stesso
  identico schermo).
- Submit: tre numeri stimati (€min/€mid/€max) + breakdown DFP +
  fonti citate (Mornet 2024 + Loi Badinter + Dintilhac) + numeri
  riproducibili (sha256 della fonte) + missing-documents espliciti
  (spese mediche, perdite redditi, eccetera).
- Disclaimer Francia-specifico (§6).
- CTA verso il contatto Studio per la revisione manuale.

## 9. Checklist firma Studio

Da spuntare a sessione legale conclusa. Ogni voce richiede:
una persona dello Studio (identificata in `legal_reviewer`), una
data, una firma o un equivalente tracciabile (es. una conferma
scritta via email allegata al record `LegalReview`).

- [ ] **Référentiel Mornet 2024** — `LegalReview.decision=approve`
      su `LegalSource(slug='fr-referentiel-mornet-2024')` con
      `legal_reviewer` FK valorizzato.
      Checklist tabellare di dettaglio:
      `legal_data/sources/france/review/france_legal_review_checklist_template.csv`
      (24 voci pre-popolate).
- [ ] **Gazette du Palais 2022** —
      `LegalReview.decision=approve` su
      `LegalSource(slug='fr-bareme-capitalisation-gazette-palais-2022')`.
- [ ] **Nomenclature Dintilhac 2005** —
      `LegalReview.decision=approve` su
      `LegalSource(slug='fr-nomenclature-dintilhac-2005')`.
- [ ] **Disclaimer Francia** — controfirma del testo §6 (o
      sostituzione con testo Studio-redatto). Il testo
      definitivo va annotato qui dopo la sessione.
- [ ] **Loi Badinter 1985** — *già* `LegalReview.decision=approve`,
      con `legal_reviewer` settato (mechanically verified 11/11
      marcatori). Da riconfermare prima del deploy.
- [ ] **Tre casi-test §7** — numeri attesi €min/€mid/€max
      validati per i tre input (35×5×0, 45×30×0, 60×15×25). I tre
      range diventano il *locked smoke test* della piattaforma.

Output atteso della sessione di firma: 4 nuove righe
`LegalReview(decision=APPROVE, reviewer=…)` nel DB (Mornet,
Gazette, Dintilhac, disclaimer-annotation) + 3 numeri attesi
firmati per i casi smoke. Lo Studio poi consegna al dev:
"firme A/B/C/D fatte, casi smoke A=…/B=…/C=…/D=…".

## 10. Checklist tecnica successiva alla firma

Una volta che lo Studio firma, il dev (in un singolo PR breve):

- [ ] Promuove `LegalSource(Mornet 2024).status = APPROVED` via
      admin.
- [ ] Promuove `LegalSource(Gazette 2022).status = APPROVED`.
- [ ] Promuove `LegalSource(Dintilhac 2005).status = APPROVED`.
- [ ] Crea le 4 righe `LegalReview(decision=APPROVE)`
      corrispondenti (audit trail).
- [ ] Rinomina `FR-MORNET-2024-DRAFT` → `FR-MORNET-2024` e
      promuove `CompensationDataset.status = APPROVED`.
- [ ] Idem per `FR-GAZETTE-PALAIS-2022-DRAFT` → `FR-GAZETTE-PALAIS-2022`.
- [ ] Crea la `CalculationFormula(France)` puntando a
      `engine=france_road_accident_v1`,
      `amount_rule=france_dfp_point_value_direct`.
- [ ] Aggiunge `apps/calculators/test_france_engine_active.py`
      con i 3 numeri smoke firmati dallo Studio.
- [ ] Esegue `python scripts/legal_data/audit_france_activation_readiness.py`
      e verifica che il verdict passi da `OFFICIAL-ONLY` a
      `GO`.
- [ ] Esegue `pytest -q` — deve restare verde.
- [ ] Esegue `bash scripts/run_lighthouse_mobile_local.sh` — i
      gates di perf devono restare cleared.
- [ ] Smoke browser su `/wizard/fr/road-accident/` con il caso
      35×5×0 — deve vedere i 3 numeri attesi.
- [ ] Aggiorna `docs/architecture/FRANCE_MODULE_STATUS.md`
      annotando la data di attivazione.

Dettagli operativi: `FRANCE_ACTIVATION_DEV_PLAN.md`.

## 11. Rollback (se qualcosa va storto post-attivazione)

Tutta la promozione è reversibile via admin in 5 minuti:

1. `CalculationFormula(France).status = DRAFT` (non eliminare —
   l'audit trail resta).
2. `CompensationDataset(FR-MORNET-2024).status = DRAFT` (idem).
3. `LegalSource(Mornet 2024).status = needs_review` (idem).
4. Run `verify_france_candidate_import.py` — verifica che il
   contatore DRAFT sia tornato intatto.
5. Run `pytest -q` — Francia torna a `unavailable_requires_legal_validation`,
   Italia 35/10/0 = 26 268 / 27 353 / 28 439 EUR resta verde.

Nessun dato viene perso. Le righe LegalReview firmate restano
nella storia anche dopo il rollback (sono audit, non stato).

---

## 12. Riferimenti

- `docs/architecture/FRANCE_ACTIVATION_READINESS_AUDIT.md` —
  audit tecnico read-only (generato 2026-05-06 da
  `scripts/legal_data/audit_france_activation_readiness.py`).
- `docs/architecture/FRANCE_MODULE_STATUS.md` — stato scaffold
  Francia (post F-france-road-accident-bootstrap).
- `docs/NON_IT_MVP_READINESS_2026-05-10.md` — confronto tra
  FR / BE / MA / TN e ragioni per cui la Francia è il candidato.
- `docs/architecture/FRANCE_LEGAL_REVIEW_PACKAGE.md` — pacchetto
  di review (DRAFT, ~26 KB) — letture preparatorie per la
  sessione Studio.
- `legal_data/sources/france/review/france_legal_review_checklist_template.csv`
  — checklist tabellare per la sessione di firma Mornet (24 voci).
- `FRANCE_ACTIVATION_DEV_PLAN.md` — piano operativo dev
  post-firma (questo stesso branch).
- `FRANCE_E2E_TEST_MATRIX.md` — matrice test e2e Francia
  (questo stesso branch).
