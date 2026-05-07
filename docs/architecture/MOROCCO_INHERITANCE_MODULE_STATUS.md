# Morocco — international inheritance module status

> Snapshot al 2026-04-29 (post F-ma-tn-international-inheritance-bootstrap).
> Living document. Aggiornare a ogni promozione di status legale.

## 1. Cosa è scaffoldato

### Calculator
- `apps/calculators/engines/morocco.py`:
  - `_MoroccoPlaceholderCalculator` (BaseCalculator → status sempre
    `unavailable_requires_legal_validation`);
  - `MoroccoInternationalInheritanceCalculator` registrato sulla
    coppia `MA-NATIONAL × international_inheritance`;
  - missing-document specifico:
    `calculator_engine_pending_for_jurisdiction`.

### Funnel pubblico MA
- URL `/wizard/ma/inheritance/`.
- View `wizard_morocco_inheritance` in `apps/cases/views.py` (helper
  `_wizard_inheritance_view` condiviso con TN).
- Form `InternationalInheritanceWizardForm` in `apps/cases/forms.py`:
  campi qualitativi (paese deceduto, residenza abituale, nazionalità,
  testamento, coniuge, figli, genitori, paesi degli asset, messaggio).
  Nessun campo monetario.
- Template `templates/public/wizard_morocco_inheritance.html` + partial
  condiviso `_inheritance_wizard_fields.html`.

### Seed metadati fonti
- Command `python manage.py seed_morocco_inheritance_legal_sources`
  (idempotente).
- Tutte le 4 fonti create con status `needs_review`:
  - `ma-moudawana-code-famille-livre-3-successions` — Moudawana,
    Livre III (OFFICIAL_LAW, OFFICIAL);
  - `ma-doc-obligations-contrats` — Code des obligations et des
    contrats (OFFICIAL_LAW, OFFICIAL);
  - `ma-code-procedure-civile` — disposizioni successorie (OFFICIAL_LAW,
    OFFICIAL);
  - `ma-international-private-law-comparative-reference` — Convenzione
    de La Haye 1989 come riferimento comparato (DOCTRINE, MEDIUM —
    NON è atto normativo per il Marocco).

### UI updates trasversali
- `/countries/`: MA mostra "Legal sources under review".
- `/wizard/`: card MA con link "Open scaffold wizard" verso il wizard
  inheritance.
- `/case-types/`: `international_inheritance` ora marcato come
  scaffold (FR e BE restano "Module ready" perché road_accident è
  operativo per IT).
- `/staff/project-status/`: pair `MA-NATIONAL ·
  international_inheritance` con badge `scaffold`.

## 2. Fonti individuate

| Fonte | Stato attuale | Cosa manca |
|---|---|---|
| **Moudawana, Livre III** | metadata seedato, `needs_review` | trascrizione delle quote (faraïd) per combinazione (status civile + parentela + presenza/assenza altri eredi); review legale dello Studio; promozione a `approved`. |
| **Code des obligations et des contrats (DOC)** | metadata seedato, `needs_review` | promozione a `approved` come riferimento per liquidazione passivo. |
| **Code de procédure civile** | metadata seedato, `needs_review` | promozione a `approved` per la parte successoria (atti di notorietà, competenza). |
| **Convention de La Haye 1989 — comparative** | metadata seedato, `needs_review` | resta riferimento di confronto, non vincolante. |

## 3. Cosa manca per il calcolo reale

Ordine di priorità per attivare un calcolatore reale:

1. **Estrazione tabellare** delle quote ereditarie del Livre III: per
   ogni combinazione (genere del defunto, status civile, parentela,
   esistenza coniuge/figli/genitori/fratelli/sorelle) → quota
   spettante per ciascun erede. Il diritto marocchino deriva da
   shari'a codificata → struttura più complessa di una tabella età ×
   invalidità.
2. **Engine** specifico (es. `morocco_moudawana_inheritance_v1`) con
   nuova `amount_rule` (es. `inheritance_share_per_heir`).
3. **CalculationFormula** approvata con `parameters` runtime.
4. **LegalReview** umana per ogni fonte. Particolare attenzione al
   coordinamento tra Moudawana e diritto internazionale privato in
   caso di pratiche transfrontaliere (defunto residente in EU ma
   patrimonio in MA, ecc.).
5. **Promozione** cumulativa source → dataset → formula a `approved`.

## 4. Perché non vengono prodotte quote / importi

Garanzie applicative:

- **Calculator placeholder**: anche con fonti `approved`,
  `_MoroccoPlaceholderCalculator._compute_with_sources` ritorna sempre
  `unavailable_requires_legal_validation`.
- **Nessuna `CalculationFormula` MA in DB**: anche se le fonti fossero
  promosse, missing-document `calculation_formula_approved`.
- **`SUPPORTED_AMOUNT_RULES` non contiene una rule successoria**:
  nessun identificatore JSON in `formula.parameters` può attivare un
  percorso non vetting-ato.
- **Test guardrail**:
  `test_morocco_calculator_unavailable_even_with_approved_source`.

Inoltre il diritto successorio coinvolge profili sensibili:
disuguaglianze di quote tra eredi maschili e femminili nel diritto
marocchino, riconoscimento all'estero di atti di notorietà MA,
qualificazione di beni immobili siti in altre giurisdizioni. Questi
profili richiedono interpretazione professionale, non meccanica:
*meglio nessun calcolo che un calcolo falso* è particolarmente
critico in questa materia.

## 5. Dati sensibili e prudenza GDPR

Il wizard MA inheritance raccoglie:

- paese del defunto, residenza abituale, nazionalità;
- esistenza di testamento;
- presenza di coniuge superstite;
- numero di figli;
- numero di genitori vivi;
- paesi degli asset;
- messaggio testuale libero.

Questi dati cadono in più categorie sensibili o quasi-sensibili:
parentela, status familiare, decesso, beni patrimoniali. Il
`ConsentRecord` per `simulation_processing` resta obbligatorio
(REQ-1, REQ-3). Nessun documento viene caricato in questa fase. Il
funnel resta wizard → result → CTA `/contact/?sim=<uuid>`: il dossier
reale viene aperto solo dopo intervento dello Studio.

In prod servirà: cookie consent EU, retention policy specifica per
case_type successioni, estensione di `apps.compliance.SimulationErasureRequest`
per la cancellazione mirata.

## 6. File creati / modificati

Vedi sezione corrispondente in
`docs/architecture/TUNISIA_INHERITANCE_MODULE_STATUS.md` (le due
funzionalità sono state introdotte nello stesso step e condividono il
form, il partial template, e l'helper di view).
