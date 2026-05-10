# CALCULATION ENGINE INDEX — Indennizzati / Studio Legale Badrane

**Data:** 2026-05-10
**Tipo:** index/cross-link.
**Scopo:** mappa concisa dei file canonici sull'engine di calcolo,
del registry, dello stato implementativo per paese, e dei test che
proteggono il contratto. Nessuna duplicazione: linka, riassume.

> Per i requisiti di prodotto vedi `docs/architecture/PRODUCT_REQUIREMENTS.md`
> REQ-3 e REQ-5. Per la roadmap di estensione paese-per-paese vedi
> `docs/architecture/LOCAL_NEXT_STEPS.md`.

---

## 1. Architettura runtime

| Layer | File | Responsabilità |
|---|---|---|
| Registry | `apps/calculators/registry.py` | Mappa `(jurisdiction, case_type) → BaseCalculator class`. Popolata al `ready()` import dei moduli engine. |
| Base class | `apps/calculators/engines/base.py` | `BaseCalculator` con guardrail `unavailable_requires_legal_validation` di default. Subclass override `_compute_with_sources()`. |
| Engines per paese | `apps/calculators/engines/{italy,france,belgium,morocco,tunisia}.py` | Una classe per `(country, case_type)`. Solo Italy road accident è REAL oggi. |
| Result schema | `apps/calculators/schemas.py` | `CalculationResult` dataclass: range min/mid/max, sources, formulas, assumptions, missing_documents, confidence, legal_disclaimer. |
| Disclaimer | `apps/calculators/disclaimer.py` | Testi disclaimer obbligatori per lingua (CLAUDE.md). |
| Diagnostics | `apps/calculators/diagnostics.py` + `status_labels.py` | Codici diagnostici tradotti, label status pubbliche. |
| Service entry | `apps.cases.services.run_simulation()` | Orchestratore: persiste `Simulation`, chiama registry, registra event + audit. |
| Inheritance applicable law | `apps/calculators/inheritance_applicable_law.py` | Decision engine cross-border (Reg. 650/2012, professio juris) — chiamato da MA/TN engines. |

Heuristica REAL vs PLACEHOLDER: una leaf class è REAL se sovrascrive
`_compute_with_sources` nel proprio `__dict__`. I placeholder ereditano
dal parent un metodo che ritorna sempre
`unavailable_requires_legal_validation` (vedi
`apps/calculators/engines/base.py`).

---

## 2. Stato per paese (snapshot 2026-04-30)

Fonte canonica: `docs/architecture/GLOBAL_MVP_STATUS.md`.

| Paese | Class | File | Stato | Fonti approved | Dataset approved | Formula approved |
|---|---|---|---|---|---|---|
| **IT** road accident | `ItalyRoadAccidentBodilyInjuryCalculator` | `apps/calculators/engines/italy.py` | **REAL** | 1 (D.P.R. 12/2025) | 2 (TUN biologico + morale) | 1 (`italy_art_138_tun_2025_base`) |
| **IT** inheritance_basic | `ItalyInheritanceBasicCalculator` | `apps/calculators/engines/italy.py` | placeholder | — | — | — |
| **FR** road accident | `FranceRoadAccidentBodilyInjuryCalculator` | `apps/calculators/engines/france.py` | placeholder | 0 | 0 | 0 |
| **BE** road accident | `BelgiumRoadAccidentBodilyInjuryCalculator` | `apps/calculators/engines/belgium.py` | placeholder | 0 | 0 | 0 |
| **MA** international_inheritance | `MoroccoInternationalInheritanceCalculator` | `apps/calculators/engines/morocco.py` | placeholder | 0 | 0 | 0 |
| **TN** international_inheritance | `TunisiaInternationalInheritanceCalculator` | `apps/calculators/engines/tunisia.py` | placeholder | 0 | 0 | 0 |

---

## 3. Documentazione di dettaglio (cross-link)

### 3.1 Italia (REAL)

- **`docs/architecture/TUN_MORAL_RANGE_ENGINE.md`** — engine
  TUN 2025 + integrazione tabelle 2.A/2.B/2.C danno morale.
- **`docs/architecture/ITALY_INPUT_VALIDATION_WARNINGS_PASS1.md`** —
  validazione input (età, %, ITT, ecc.) lato server.
- **`docs/architecture/ITALY_WARNING_STRINGS_TRANSLATABLE_PASS1.md`** —
  tutti i warning IT tradotti via `gettext_lazy`.
- canarino: **35/10/0 → 26 268 / 27 353 / 28 439 EUR** (mai cambiare
  senza rifirmare `LegalReview`).

### 3.2 Diagnostica e i18n

- **`docs/architecture/CALCULATOR_DIAGNOSTIC_STRINGS_AUDIT.md`** —
  audit completo dei diagnostic strings (warning prefix migrati a
  diagnostic centralizzati). Solo `formula_engine_unknown` resta
  come stable identifier.
- **`docs/architecture/CALCULATOR_WARNING_STRINGS_TRANSLATABLE_PASS1.md`** —
  centralizzazione dei warning string traducibili.
- **`docs/architecture/RESULT_PAGE_LOCALIZATION_PASS1.md`** —
  localizzazione della result page non-calculating (FR/BE/MA/TN).

### 3.3 Inheritance applicable law (cross-border)

- **`docs/architecture/EU_650_APPLICABLE_LAW_DECISION_ENGINE_SKELETON.md`** —
  skeleton del decision engine Reg. (UE) 650/2012.
- **`docs/architecture/APPLICABLE_LAW_ENGINE_INTEGRATION_PASS1.md`** —
  integrazione del decision engine nei wizard MA/TN.
- **`docs/architecture/MOROCCO_ENGINE_ACTIVATION_BLOCKERS_GUARD_PASS1.md`** —
  guardrail che blocca attivazione MA finché mapping Moudawana
  non è firmato.
- **`docs/architecture/EU_650_REAL_SOURCE_RESTORE_PASS1.md`** —
  ripristino della fonte EUR-Lex Reg. 650/2012 dopo manual download.

### 3.4 Mapping legali draft (Studio review pendente)

- **`docs/architecture/MOROCCO_MOUDAWANA_MAPPING_DRAFT_PASS1.md`** +
  **`PASS2`** + **`PASS3`** — draft mapping articoli Moudawana per
  faraïd. Non in DB finché Studio non firma.
- **`docs/architecture/TUNISIA_CSP_MAPPING_DRAFT_PASS1.md`** +
  **`TUNISIA_CSP_ADJACENT_ARTICLE_RANGES_FETCH_PASS2.md`** —
  draft mapping CSP Livre IX.
- **`docs/legal_sources/MOROCCO_MOUDAWANA_INHERITANCE_EXTRACTION.md`**.
- **`docs/legal_sources/TUNISIA_CSP_LIVRE_IX_INHERITANCE_EXTRACTION.md`**.

### 3.5 Stato modulo per paese

- **`docs/architecture/MVP_STATUS.md`** — stato unico Italia.
- **`docs/architecture/GLOBAL_MVP_STATUS.md`** — snapshot multi-paese
  (canonical).
- **`docs/architecture/FRANCE_MODULE_STATUS.md`**,
  **`BELGIUM_MODULE_STATUS.md`**, **`MOROCCO_INHERITANCE_MODULE_STATUS.md`**,
  **`TUNISIA_INHERITANCE_MODULE_STATUS.md`** — per paese.
- **`docs/architecture/FRANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md`**,
  **`BELGIUM_ENGINE_INACTIVE_FIXTURE_ONLY.md`**,
  **`MOROCCO_INHERITANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md`**,
  **`TUNISIA_INHERITANCE_ENGINE_INACTIVE_FIXTURE_ONLY.md`** — placeholder
  contract: garantiscono che gli engine non producano valori finché
  scaffold.

---

## 4. Output schema (contract pubblico)

Vedi `apps/calculators/schemas.py::CalculationResult`. Ogni
calculator REAL ritorna:

```python
@dataclass
class CalculationResult:
    simulation_id: str
    jurisdiction: str
    case_type: str
    currency: str
    estimated_min: Decimal | None
    estimated_mid: Decimal | None
    estimated_max: Decimal | None
    breakdown: list[dict]
    sources: list[dict]   # title, url, version, date
    assumptions: list[str]
    warnings: list[str]
    missing_documents: list[str]
    confidence: Literal["low", "medium", "high"]
    legal_disclaimer: str
    status: Literal["calculated", "unavailable_requires_legal_validation", "error_legal_data_missing"]
```

Gli `estimated_*` sono `None` quando `status != "calculated"`. Mai
zero (deontologicamente diverso: zero = "calcolato a 0 €", None =
"non calcolabile").

---

## 5. Test di contratto (canarini)

| Canarino | File | Cosa garantisce |
|---|---|---|
| Italy 35/10/0 → 26 268 / 27 353 / 28 439 EUR | molti test, es. `apps/cases/test_*.py`, `apps/calculators/test_italy_*.py` | TUN 2025 IT non regredisce. |
| FR/BE/MA/TN engine restano `unavailable_requires_legal_validation` | `apps/calculators/test_*_engine_inactive.py` (4 file) | Nessun valore numerico EUR può apparire dai paesi non attivi. |
| Disclaimer presente in ogni `CalculationResult` | `apps/calculators/test_*` | `legal_disclaimer` non vuoto. |
| Warning strings traducibili | `apps/calculators/test_diagnostics_i18n.py`, `test_italy_public_warnings_i18n.py` | Niente stringhe hardcoded inglese. |
| `CalculatorRegistry` non solleva su lookup mancante | `apps/calculators/tests.py` | Fail-safe: ritorna `None` invece di crash. |

---

## 6. Aggiungere un nuovo paese × case_type — checklist

> Vincolo: niente codice prima della `LegalReview` firmata sulla
> fonte primaria. Vedi `LOCAL_NEXT_STEPS.md` Fase A.

1. fonte legale: `LegalSource.status=approved` + 1+ `LegalReview` firmata;
2. dataset: `CompensationDataset.status=approved` con righe estratte
   in modo deterministico (no LLM);
3. formula: `CalculationFormula.status=approved` con `parameters.engine`
   registrato;
4. classe engine: subclass di `BaseCalculator`, override
   `_compute_with_sources`, **mai** valori hardcoded;
5. registrazione in `apps/calculators/engines/<country>.py` con
   `_REGISTRY.register("<JUR>", "<case_type>", MyClass)`;
6. test: caso happy path, edge cases (input invalidi), regressione
   IT (canarino 35/10/0 deve restare verde);
7. doc: `<COUNTRY>_<CASE_TYPE>_ENGINE_PASS1.md` in `docs/architecture/`;
8. UI: wizard form + result template aggiornati;
9. SEO: country landing aggiornata (vedi `PRODUCT_COUNTRY_LANDING_SEO.md`);
10. browser live + screenshot + lighthouse.

---

## 7. Gap e P0/P1 aperti su engine

| ID | Voce | Severità |
|---|---|---|
| ENG-P0-1 | Nessun engine non-IT è REAL (vincolo cardinale go-live, vedi `LOCAL_NEXT_STEPS.md` Sez. 0) | P0 (gating Studio review) |
| ENG-P1-1 | `IT/inheritance_basic` registrato ma placeholder. Va deciso: implementarlo o de-registrarlo. | P1 |
| ENG-P1-2 | Tabelle Tribunale Milano 2024 IT in `needs_review` | P1 |
| ENG-P2-1 | Test `_pass1`/`_pass2`/`_passN` dispersi (vedi `LEGAL_DATA_TEST_FIXTURE_ISOLATION_PASS1.md`) | P2 (consolidamento) |

---

## 8. Per Claude Code che lavora sul calcolatore

- **Mai** modificare il canarino IT 35/10/0 senza rifirmare
  `LegalReview` per il nuovo dataset/formula.
- **Mai** introdurre valori hardcoded nel codice engine.
- Ogni nuovo engine eredita da `BaseCalculator`, non costruisce
  un `CalculationResult` da zero.
- I test del registry (`apps/calculators/tests.py`) sono
  load-bearing: passa via `pytest -k registry` prima di committare
  cambi al `_REGISTRY`.
- Sentry: i diagnostic codes sono *stable identifiers*, non
  user-facing. Vedi `CALCULATOR_DIAGNOSTIC_STRINGS_AUDIT.md`.
