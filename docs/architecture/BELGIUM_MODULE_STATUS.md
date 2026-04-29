# Belgium module status — Studio Legale Badrane LegalTech

> Snapshot al 2026-04-29 (post F-belgium-road-accident-bootstrap).
> Living document. Aggiornare a ogni promozione di status legale.

## 1. Cosa è stato scaffoldato

### Calculator
- `apps/calculators/engines/belgium.py`:
  - `_BelgiumPlaceholderCalculator` (BaseCalculator → status sempre
    `unavailable_requires_legal_validation`);
  - `BelgiumRoadAccidentBodilyInjuryCalculator` registrato sulla
    coppia `BE-NATIONAL × road_accident_bodily_injury`;
  - missing-document specifico:
    `calculator_engine_pending_for_jurisdiction`.

### Funnel pubblico BE
- URL `/wizard/be/road-accident/`.
- View `wizard_belgium_road_accident` in `apps/cases/views.py`.
- Form `BelgiumRoadAccidentWizardForm` in `apps/cases/forms.py`:
  sottoclasse di `ItalyRoadAccidentWizardForm`, default
  `accident_country = "BE"`. Stesso schema di input.
- Template `templates/public/wizard_belgium_road_accident.html`:
  banner esplicito "Module under legal validation" che cita Loi 1989,
  Tableau indicatif e barème Schryvers.

### Seed metadati fonti
- Command `python manage.py seed_belgium_legal_sources` (idempotente).
- Tutte le 4 fonti create con status `needs_review`:
  - `be-loi-1989-11-21-assurance-rc-auto` (Loi RC auto, OFFICIAL_LAW);
  - `be-code-civil-art-1382-1383` (Code civil belga, OFFICIAL_LAW);
  - `be-tableau-indicatif-cours-tribunaux-2020` (Tableau indicatif,
    COURT_TABLE, reliability HIGH);
  - `be-bareme-capitalisation-schryvers-2020` (Barème Schryvers,
    COURT_TABLE, reliability HIGH).

### UI updates trasversali
- `/countries/` mostra BE come "Legal sources under review" (badge
  oro), insieme a FR.
- `/wizard/` (landing) offre il link BE con etichetta "Open scaffold
  wizard". L'elenco "Coming next" è ora pulito da Belgio (resta MA, TN).
- `/staff/project-status/` marca la pair BE registrata come `scaffold`.

## 2. Fonti individuate

| Fonte | Stato attuale | Cosa manca |
|---|---|---|
| **Tableau indicatif des cours et tribunaux** (2020/2024) | metadata seedato, `needs_review` | trascrizione tabellare per voce di danno (ITT, IPP, pretium doloris, dommage esthétique, perte de revenus, aide d'une tierce personne); review legale dello Studio; promozione a `approved`. |
| **Barème de capitalisation Schryvers 2020** | metadata seedato, `needs_review` | trascrizione coefficienti per età × durata; review legale; necessario solo se il calcolo includerà rendite vitalizie. |
| **Loi du 21 novembre 1989** | metadata seedato, `needs_review` | promozione a `approved` come cornice giuridica RCA. Non produce numeri ma è il riferimento normativo richiesto in audit. |
| **Code civil — art. 1382-1383** | metadata seedato, `needs_review` | promozione a `approved` come cornice civile per la responsabilità extracontrattuale. |

NB: il sistema belga è simile a quello francese — combinazione di
norme primarie (loi + code civil) + référentiels indicativi (tableau +
barème). Reliability delle tabelle finali sarà `HIGH` (non `OFFICIAL`)
e la result page dovrà esplicitarlo.

## 3. Cosa manca per il calcolo reale

1. **Estrazione tabellare**: parser PDF dedicato per il Tableau
   indicatif belga (struttura per testa di danno, non per età ×
   invalidità come la TUN italiana); QA di consistenza; import
   additivo in dataset DRAFT (es. `version_label =
   "TABLEAU-INDICATIF-2020"`).
2. **Engine economico**:
   - identificare le grandezze rilevanti (ITT, IPP, pretium doloris,
     dommage esthétique, perte de revenus);
   - decidere `amount_rule` adeguata — probabilmente la stessa
     `referentiel_indicatif_per_head_of_loss` usata per la Francia,
     se ne sviluppiamo una unificata, oppure
     `tableau_indicatif_belge_v1` separata;
   - registrare la rule in `SUPPORTED_AMOUNT_RULES`;
   - test fixture-only.
3. **Formula** approvata dallo Studio con `parameters` runtime.
4. **LegalReview** umana con `decision=approve` per ciascuna fonte
   coinvolta.
5. **Promozione cumulativa**: source → dataset → formula a `approved`,
   nello stesso ordine di gating del calculator.

## 4. Perché non vengono prodotti importi

Garanzie applicative (identiche al modulo Francia):

- **Calculator placeholder**: anche con fonti `approved`,
  `_BelgiumPlaceholderCalculator._compute_with_sources` ritorna sempre
  `unavailable_requires_legal_validation` con missing-document
  `calculator_engine_pending_for_jurisdiction`.
- **Nessuna `CalculationFormula` BE in DB**: anche se le fonti fossero
  promosse, il calculator non troverebbe formula approved e
  ritornerebbe `calculation_formula_approved` come missing-document.
- **`SUPPORTED_AMOUNT_RULES` non contiene una rule belga**: nessun
  identificatore JSON in `formula.parameters` può attivare un percorso
  di calcolo che non sia stato vetting-ato in code review.
- **Test guardrail**:
  `test_belgium_calculator_unavailable_even_with_approved_source`
  verifica che lo stato resti `unavailable` anche dopo aver creato una
  fonte `approved` di test.

Allinea il Belgio alla regola d'oro del progetto: *meglio nessun calcolo
che un calcolo falso*.

## 5. File creati / modificati in F-belgium-road-accident-bootstrap

| File | Tipo | Note |
|---|---|---|
| `apps/legal_sources/management/commands/seed_belgium_legal_sources.py` | nuovo | seed metadata 4 fonti BE, idempotente. |
| `apps/calculators/engines/belgium.py` | nuovo | placeholder calculator + registry. |
| `apps/calculators/engines/__init__.py` | modificato | aggiunto import `belgium`. |
| `apps/cases/forms.py` | modificato | nuova `BelgiumRoadAccidentWizardForm`. |
| `apps/cases/views.py` | modificato | view `wizard_belgium_road_accident` + landing aggiornata. |
| `apps/cases/urls.py` | modificato | nuovo path BE. |
| `templates/public/wizard_belgium_road_accident.html` | nuovo | template wizard BE. |
| `apps/core/views.py` | modificato | `SCAFFOLD_ONLY_COUNTRIES`/`SCAFFOLD_ONLY_PAIRS` con BE; "Coming next" pulito. |
| `apps/calculators/test_belgium_scaffold.py` | nuovo (10 test) | calcolatore + seed. |
| `apps/cases/tests.py` | modificato (+6 test) | wizard BE end-to-end. |
| `apps/core/tests.py` | modificato (+3 test) | UI BE (dashboard, countries, wizard start). |
| `docs/architecture/BELGIUM_MODULE_STATUS.md` | nuovo | questo documento. |

Niente modifiche ai moduli Italia/Francia, ai dati TUN, alle formule,
ai modelli, alle migrations, al PDF report, al deploy.
