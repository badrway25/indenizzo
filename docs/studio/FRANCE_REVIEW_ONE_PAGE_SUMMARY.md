# Francia — riassunto in una pagina per lo Studio

**Per**: Studio Legale Internazionale Badrane — sessione di review legale Francia.
**Data documento**: 2026-05-12.
**Sintesi**: 1 pagina, leggibile in 5 minuti. Non sostituisce il pacchetto operativo (`docs/product/FRANCE_ACTIVATION_SIGNOFF_PACK.md`); lo riassume per chi non ha tempo di leggerlo tutto.

---

## Perché Francia è il primo candidato non-Italia

- **Volume dati pronti**: 4 380 righe estratte tra Mornet 2024 e Gazette du Palais 2022. Più di 26 volte i dati pronti per il Belgio, oltre 100 volte rispetto a Marocco e Tunisia.
- **Schema giuridico noto**: incidente stradale + danno corporale (cornice Loi Badinter 1985) — pattern simile a quello già funzionante in Italia.
- **Nessun blocker tecnico**: il calcolatore Francia è già scritto, testato e *gated*. Manca solo la firma legale Studio.
- **Nessun blocker doctrinale**: a differenza di Marocco / Tunisia (questioni di diritto di famiglia non risolte, conflitto di leggi UE 650/2012 vs Loi tunisina 98-97), la Francia non richiede decisioni di dottrina, solo accettazione editoriale di tabelle esistenti.

## Cosa serve firmare — 4 documenti

| # | Documento | Natura | Perché serve |
|---|---|---|---|
| 1 | **Référentiel Mornet 2024** | barème privato delle Cours d'Appel | sblocca il calcolo del Déficit Fonctionnel Permanent (DFP) |
| 2 | **Gazette du Palais 2022** | tabella di capitalizzazione jurisprudenziale | serve per capitalizzare rendite future (estensione v2; può attendere ma è meglio firmare ora) |
| 3 | **Nomenclature Dintilhac 2005** | classificazione dei *postes* di pregiudizio | serve per organizzare il report PDF Francia voce per voce |
| 4 | **Disclaimer Francia** | testo legale visibile all'utente | controfirma del testo proposto o sostituzione con redazione Studio |

Più: **3 numeri smoke test** (importi attesi per 3 casi-tipo, vedi sotto).

## Cosa vede l'utente oggi

- `/wizard/fr/road-accident/` rende il form (utente può compilarlo).
- Submit → pagina di "valutazione legale preliminare", **nessun importo pubblicato**, CTA verso lo Studio.
- Disclaimer generico.
- Citazione delle fonti come "in fase di revisione legale Studio".

## Cosa cambia il giorno della firma

- Stesso form, stesso flusso.
- Submit → tre numeri stimati €min/€mid/€max + scomposizione DFP + fonti citate (Mornet 2024 + Loi Badinter) + documenti non inclusi nel calcolo automatico (spese mediche, perdita reddito, rendite, ecc., ognuno con CTA "valutazione Studio caso-per-caso").
- Disclaimer Francia-specifico se redatto, altrimenti il generico controfirmato.

## Perché oggi non appare nessun importo

Regola fondazionale della piattaforma: **meglio nessun calcolo che un calcolo falso**. Il codice rifiuta meccanicamente di emettere numeri Francia fino a quando:

1. la `LegalSource` Mornet non è in stato `APPROVED` con `LegalReview(decision=APPROVE)`;
2. il dataset corrispondente non è promosso da `DRAFT` a `APPROVED`;
3. una `CalculationFormula(France, status=APPROVED)` non è creata.

Tutti e tre i livelli sono indipendentemente necessari. Nessuno è bypassabile da un'edit accidentale dell'admin.

## Limiti dichiarati del calcolatore Francia v1

Quello che il calcolatore v1 **fa**:

- Stima il Déficit Fonctionnel Permanent (DFP) usando Mornet 2024, in funzione di età × % invalidità permanente.
- Applica linearmente la riduzione per concorso di colpa (`fault_percentage`).
- Cita le fonti, dichiara le ipotesi, elenca i documenti non inclusi.

Quello che il v1 **non fa** (esce esplicitamente come "richiede valutazione Studio"):

- spese mediche, perdita reddito, capitalizzazione di rendite, *souffrances endurées*, *préjudice esthétique*, *préjudice d'affection*, *tierce personne*.
- interpolazione tra righe Mornet: se l'input è fuori griglia (es. invalidità 0.5 % che Mornet non copre), il sistema risponde "valutazione preliminare", non un numero approssimato.

## I 3 numeri da firmare

Per ognuno dei 3 casi-tipo, lo Studio firma il range €min/€mid/€max atteso. Questi tre numeri diventeranno il *locked smoke test* della piattaforma: il calcolatore deve riprodurli identici al deploy o il sistema non parte.

| Caso | victim_age | permanent_disability_% | fault_% | €min atteso | €mid atteso | €max atteso |
|---|---|---|---|---|---|---|
| 1 — lieve | 35 | 5 | 0 | (firma Studio) | (firma Studio) | (firma Studio) |
| 2 — grave | 45 | 30 | 0 | (firma Studio) | (firma Studio) | (firma Studio) |
| 3 — concorso colpa | 60 | 15 | 25 | (firma Studio) | (firma Studio) | (firma Studio) |

---

## Documenti completi (se lo Studio vuole approfondire)

- **Pacchetto operativo completo** (~13 KB): `docs/product/FRANCE_ACTIVATION_SIGNOFF_PACK.md`
- **Matrice test e2e** (~7 KB): `docs/product/FRANCE_E2E_TEST_MATRIX.md`
- **Pacchetto review tecnico legale** (~26 KB, DRAFT): `docs/architecture/FRANCE_LEGAL_REVIEW_PACKAGE.md`
- **Checklist 24 voci review tabellare Mornet**: `legal_data/sources/france/review/france_legal_review_checklist_template.csv`
