# Tunisia — international inheritance module status

> Snapshot al 2026-04-29 (post F-ma-tn-international-inheritance-bootstrap).
> Living document. Aggiornare a ogni promozione di status legale.

## 1. Cosa è scaffoldato

### Calculator
- `apps/calculators/engines/tunisia.py`:
  - `_TunisiaPlaceholderCalculator` (BaseCalculator → status sempre
    `unavailable_requires_legal_validation`);
  - `TunisiaInternationalInheritanceCalculator` registrato sulla
    coppia `TN-NATIONAL × international_inheritance`;
  - missing-document specifico:
    `calculator_engine_pending_for_jurisdiction`.

### Funnel pubblico TN
- URL `/wizard/tn/inheritance/`.
- View `wizard_tunisia_inheritance` in `apps/cases/views.py` (helper
  `_wizard_inheritance_view` condiviso con MA).
- Form `InternationalInheritanceWizardForm` (stesso del Marocco —
  campi qualitativi, nessun campo monetario).
- Template `templates/public/wizard_tunisia_inheritance.html` + partial
  condiviso `_inheritance_wizard_fields.html`.

### Seed metadati fonti
- Command `python manage.py seed_tunisia_inheritance_legal_sources`
  (idempotente).
- Tutte le 4 fonti create con status `needs_review`:
  - `tn-code-statut-personnel-livre-9-successions` — Code du statut
    personnel (CSP), Livre IX (OFFICIAL_LAW, OFFICIAL);
  - `tn-coc-obligations-contrats` — Code des obligations et des
    contrats (OFFICIAL_LAW, OFFICIAL);
  - `tn-code-droit-international-prive-1998` — Loi n° 98-97 sul
    diritto internazionale privato (OFFICIAL_LAW, OFFICIAL);
  - `tn-international-private-law-comparative-reference` — Convenzione
    de La Haye 1989 come riferimento comparato (DOCTRINE, MEDIUM).

### UI updates trasversali
- `/countries/`: TN mostra "Legal sources under review".
- `/wizard/`: card TN con link "Open scaffold wizard".
- `/case-types/`: `international_inheritance` marcato come scaffold
  (insieme a MA).
- `/staff/project-status/`: pair `TN-NATIONAL ·
  international_inheritance` con badge `scaffold`.

## 2. Fonti individuate

| Fonte | Stato attuale | Cosa manca |
|---|---|---|
| **CSP, Livre IX** | metadata seedato, `needs_review` | trascrizione delle quote (faraïd codificate nel CSP); review legale; promozione a `approved`. |
| **Code des obligations et des contrats** | metadata seedato, `needs_review` | promozione a `approved`. |
| **Code de droit international privé (Loi 98-97)** | metadata seedato, `needs_review` | promozione a `approved`. Particolarmente critico per la qualificazione del case-type (nazionalità del defunto, residenza abituale, beni in altre giurisdizioni). |
| **Convention de La Haye 1989 — comparative** | metadata seedato, `needs_review` | resta riferimento di confronto, non vincolante. |

## 3. Cosa manca per il calcolo reale

Stesso ordine del Marocco:

1. **Estrazione tabellare** delle quote del Livre IX del CSP. Il
   sistema tunisino è simile a quello marocchino ma con specificità
   proprie (es. trattamento del coniuge, della figlia unica).
2. **Engine** specifico (es. `tunisia_csp_inheritance_v1`).
3. **CalculationFormula** approvata.
4. **LegalReview** umana per ogni fonte, con focus sul coordinamento
   tra CSP e CDIP per le pratiche transfrontaliere.
5. **Promozione** cumulativa source → dataset → formula a `approved`.

## 4. Perché non vengono prodotte quote / importi

Stesse 4 garanzie del modulo Marocco — vedi
`MOROCCO_INHERITANCE_MODULE_STATUS.md §4`. Test guardrail:
`test_tunisia_calculator_unavailable_even_with_approved_source`.

## 5. Dati sensibili e prudenza GDPR

Identici al modulo Marocco. Il form `InternationalInheritanceWizardForm`
è condiviso, quindi le considerazioni GDPR e di retention si applicano
in modo identico.

## 6. File creati / modificati in F-ma-tn-international-inheritance-bootstrap

| File | Tipo |
|---|---|
| `apps/legal_sources/management/commands/seed_morocco_inheritance_legal_sources.py` | nuovo |
| `apps/legal_sources/management/commands/seed_tunisia_inheritance_legal_sources.py` | nuovo |
| `apps/calculators/engines/morocco.py` | nuovo |
| `apps/calculators/engines/tunisia.py` | nuovo |
| `apps/calculators/engines/__init__.py` | modificato (import morocco + tunisia) |
| `apps/cases/forms.py` | modificato (`InternationalInheritanceWizardForm`) |
| `apps/cases/views.py` | modificato (2 view + helper condiviso, landing aggiornata, pulizia "Coming next") |
| `apps/cases/urls.py` | modificato (2 nuovi path) |
| `templates/public/wizard_morocco_inheritance.html` | nuovo |
| `templates/public/wizard_tunisia_inheritance.html` | nuovo |
| `templates/public/_inheritance_wizard_fields.html` | nuovo (partial condiviso) |
| `apps/core/views.py` | modificato (MA/TN nei set scaffold; `case_types` ora distingue scaffold-only) |
| `templates/public/case_types.html` | modificato (badge "Legal sources under review" per case_type scaffold-only) |
| `apps/calculators/test_morocco_tunisia_scaffold.py` | nuovo (17 test) |
| `apps/cases/tests.py` | modificato (+7 test wizard inheritance) |
| `apps/core/tests.py` | modificato (+4 test UI MA/TN) |
| `docs/architecture/MOROCCO_INHERITANCE_MODULE_STATUS.md` | nuovo |
| `docs/architecture/TUNISIA_INHERITANCE_MODULE_STATUS.md` | questo documento |

Niente modifiche ai moduli Italia/Francia/Belgio, ai dati TUN, alle
formule, ai modelli, alle migrations, al PDF report, al deploy.
