# France module status — Studio Legale Badrane LegalTech

> Snapshot al 2026-04-29 (post F-france-road-accident-bootstrap).
> Living document. Aggiornare a ogni promozione di status legale.

## 1. Cosa è stato scaffoldato

### Calculator
- `apps/calculators/engines/france.py`:
  - classe `_FrancePlaceholderCalculator` (BaseCalculator → status sempre
    `unavailable_requires_legal_validation`);
  - classe `FranceRoadAccidentBodilyInjuryCalculator` registrata sulla
    coppia `FR-NATIONAL × road_accident_bodily_injury`;
  - missing-document specifico:
    `calculator_engine_pending_for_jurisdiction`.

### Funnel pubblico FR
- URL `/wizard/fr/road-accident/` (con i18n prefix opzionale).
- View `wizard_france_road_accident` in `apps/cases/views.py`.
- Form `FranceRoadAccidentWizardForm` in `apps/cases/forms.py`:
  sottoclasse di `ItalyRoadAccidentWizardForm` con default
  `accident_country = "FR"`. Stesso schema di input.
- Template `templates/public/wizard_france_road_accident.html`:
  banner esplicito "Module under legal validation" che dichiara perché
  il wizard non produrrà un range numerico.

### Seed metadati fonti
- Command `python manage.py seed_france_legal_sources` (idempotente).
- Tutte le 4 fonti create con status `needs_review`:
  - `fr-loi-1985-07-05-badinter` (Loi Badinter, OFFICIAL_LAW);
  - `fr-code-assurances-l211` (Code des assurances, OFFICIAL_LAW);
  - `fr-referentiel-indicatif-cours-appel-2022` (référentiel indicatif,
    COURT_TABLE, reliability HIGH);
  - `fr-bareme-capitalisation-gazette-palais-2022` (barème
    capitalisation, COURT_TABLE, reliability HIGH).

### UI updates trasversali
- `/countries/` mostra FR come "Legal sources under review" (badge
  oro), non "Available".
- `/wizard/` (landing) offre il link FR con etichetta "Open scaffold
  wizard" e badge "Legal sources under review".
- `/staff/project-status/` marca la pair FR registrata come `scaffold`.

## 2. Quali fonti servono prima di calcolare

In ordine di priorità per attivare un calcolatore reale:

| Fonte | Stato attuale | Cosa manca |
|---|---|---|
| **Référentiel indicatif d'indemnisation des cours d'appel** (ed. 2022) | metadata seedato, `needs_review` | trascrizione tabellare per testa di danno (Déficit Fonctionnel Permanent, Souffrances endurées, Préjudice esthétique, ecc.); review legale dello Studio; promozione a `approved`. Senza questo NON c'è un dataset. |
| **Barème de capitalisation Gazette du Palais 2022** | metadata seedato, `needs_review` | trascrizione coefficienti per età × sesso; review legale; necessario solo se il calcolo includerà rendite vitalizie (perte de gains professionnels futurs, tierce personne). |
| **Loi Badinter + Code des assurances** | metadata seedato, `needs_review` | promozione a `approved` come cornice giuridica. Non producono numeri ma sono il riferimento normativo richiesto in audit. |

NB: il sistema legale francese per l'indennizzo del danno corporale è
fondato su giurisprudenza + référentiels indicativi (NON un decreto
ministeriale come la TUN italiana). Questo significa che reliability
delle tabelle finali sarà `HIGH` (non `OFFICIAL`) e che il wording
nella result page dovrà esplicitarlo.

## 3. Cosa manca per il calcolo reale

1. **Estrazione tabellare** (analoga a F-italy-engine-implementation +
   F-italy-tabelle-morali iter1/iter2):
   - PDF/sorgente del Référentiel 2022;
   - parser PDF dedicato per la struttura francese;
   - QA di consistenza (monotonicità, range plausibili);
   - import additivo in dataset DRAFT (es. `version_label =
     "REFERENTIEL-COURS-APPEL-2022"`).
2. **Engine economico** (analogo a `italy_tun_point_value_v1`):
   - identificare le grandezze rilevanti (DFP, SE, PE) e le loro
     scale (capitoli del référentiel);
   - decidere `amount_rule` adeguata (probabilmente nuova:
     `referentiel_indicatif_per_head_of_loss`);
   - registrare la rule in `SUPPORTED_AMOUNT_RULES`;
   - test fixture-only.
3. **Formula** approvata dallo Studio con `parameters` runtime.
4. **LegalReview** umana con `decision=approve` per ciascuna fonte
   coinvolta.
5. **Promozione cumulativa**: source → dataset → formula a `approved`,
   nello stesso ordine di gating del calculator.
6. **Smoke test** equivalente a `(35, 10, 0) → 21 709 EUR` per Italia,
   ma con valori reali del référentiel.

## 4. Perché non vengono prodotti importi

Garanzie applicative e di codice, anche se qualcuno provasse a forzare
l'attivazione editando admin:

- **Calculator placeholder**: anche con fonti `approved`,
  `_FrancePlaceholderCalculator._compute_with_sources` ritorna sempre
  `unavailable_requires_legal_validation` con missing-document
  `calculator_engine_pending_for_jurisdiction`. La regola economica
  non esiste come codice eseguibile.
- **Nessuna `CalculationFormula` FR in DB**: anche se le fonti fossero
  promosse, il calculator non troverebbe formula approved e
  ritornerebbe `calculation_formula_approved` come missing-document.
- **`SUPPORTED_AMOUNT_RULES` non contiene una rule francese**: nessun
  identificatore JSON in `formula.parameters` può attivare un percorso
  di calcolo che non sia stato vetting-ato in code review.
- **Test guardrail**:
  `test_france_calculator_unavailable_even_with_approved_source`
  verifica che lo stato reste `unavailable` anche dopo aver creato una
  fonte `approved` di test.

Questo allinea Francia alla regola d'oro del progetto: *meglio nessun
calcolo che un calcolo falso*.

## 5. File creati / modificati in F-france-road-accident-bootstrap

| File | Tipo | Note |
|---|---|---|
| `apps/legal_sources/management/commands/seed_france_legal_sources.py` | nuovo | seed metadata 4 fonti FR, idempotente. |
| `apps/calculators/engines/france.py` | nuovo | placeholder calculator + registry. |
| `apps/calculators/engines/__init__.py` | modificato | aggiunto import `france`. |
| `apps/cases/forms.py` | modificato | nuova `FranceRoadAccidentWizardForm`. |
| `apps/cases/views.py` | modificato | view `wizard_france_road_accident` + landing aggiornata. |
| `apps/cases/urls.py` | modificato | nuovo path FR. |
| `templates/public/wizard_france_road_accident.html` | nuovo | template wizard FR. |
| `templates/public/wizard_start.html` | modificato | gestione 3-stato `available/scaffold_only/in_preparation`. |
| `templates/public/countries.html` | modificato | nuovo badge "Legal sources under review". |
| `templates/staff/project_status.html` | modificato | badge `scaffold` su moduli registrati ma non operativi. |
| `apps/core/views.py` | modificato | `countries` espone `scaffold_only`; `project_status` espone scaffold flag. |
| `apps/calculators/test_france_scaffold.py` | nuovo | 8 test calcolatore + seed. |
| `apps/cases/tests.py` | modificato | 6 test wizard FR. |
| `apps/core/tests.py` | modificato | 3 test UI scaffold (dashboard, countries, wizard start). |
| `docs/architecture/FRANCE_MODULE_STATUS.md` | nuovo | questo documento. |

Niente modifiche al modulo Italia, ai dati TUN, alla formula Italia, al
report PDF, al deploy, ai modelli, alle migrations. Tutto reversibile
in un singolo `git revert` del commit di feature.
