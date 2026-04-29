# MVP status — Studio Legale Internazionale Badrane LegalTech

> Snapshot al 2026-04-29. Living document. Aggiornare a ogni promozione
> di status legale o aggiunta di un nuovo modulo.

## 0. Moral range activated

Stato attuale (post F-italy-moral-legal-review-and-activation):

- Tabelle 2.A / 2.B / 2.C del D.P.R. 12/2025 importate in dataset
  separato `DPR-12-2025-MORAL` (27 573 righe), promosso a `approved`
  con `LegalReview` formale dello Studio.
- La formula `italy_art_138_tun_2025_base` ora dichiara
  `amount_rule = "row_amount_range_direct"` con
  `range_dataset_version_label = "DPR-12-2025-MORAL"` e i 3 row_type
  morali min/mid/max.
- **Cosa significa**: il calculator pubblico restituisce un range
  reale `min < mid < max` invece di tre valori coincidenti. La cella
  base biological non viene più letta dal funnel — sostituita dalle
  tre celle "comprensive" del moral dataset (biologico + morale).
- **Smoke 35/10/0**: `min = 26 268 EUR`, `mid = 27 353 EUR`,
  `max = 28 439 EUR`. `confidence = medium`. Tutti > 21 709 (= valore
  biologico solo) di un incremento ~21–31% in linea con i parametri di
  legge.
- **Rollback** (1 edit, ~5 secondi):
  ripristinare `formula.parameters.amount_rule = "row_amount_direct"` e
  rimuovere i 4 campi range. Il calculator torna immediatamente a
  `min == mid == max == 21 709`. Il dataset moral resta in DB intatto
  (mai cancellato, mai cambia per il rollback).

Le 9 191 righe Tabella 1 base restano `approved` e intatte. La
`LegalSource` resta `approved` invariata.

## 1. Cosa è operativo oggi

### Funnel pubblico end-to-end (live nel browser)
1. Home `/` con design premium ink/sand/gold, multilingua switcher (it/fr/en/ar), CTA verso il sito istituzionale.
2. Pagine pubbliche `/methodology/`, `/disclaimer/`, `/privacy/`, `/countries/`, `/case-types/` — tutte 200, contenuto coerente con la regola "no fabricated numbers".
3. Wizard Italia incidente stradale `/wizard/it/road-accident/` con form 9 campi opzionali + consenso obbligatorio + honeypot.
4. Submit → crea `Simulation` UUID + `ConsentRecord` + esegue calcolo → redirect alla result page.
5. Result page con due varianti coerenti:
   - **`status=calculated`**: box "Stima disponibile" verde con MIN/MID/MAX, breakdown, fonti citate (DPR 12/2025), assumptions, disclaimer IT.
   - **`status=unavailable_requires_legal_validation`**: box "Validazione legale richiesta" sand con spiegazione professionale.
6. CTA "Download PDF report" `/reports/simulation/<uuid>/pdf/` → PDF reportlab (~5-7 KB) con tutto il contenuto del result, audit `PrivacyAuditEvent(DATA_EXPORTED)`.
7. CTA "Request legal review" `/contact/?sim=<uuid>` → form CRM con `simulation_public_id` precompilato → submit → `Lead` collegato + `LeadEvent` + redirect thank-you.

### Modulo legale attivo: **Italia road accident bodily injury**
- Source: D.P.R. 13 gennaio 2025, n. 12 — Tabella Unica Nazionale danno biologico (G.U. n. 40 del 18/02/2025, S.O. 4/L)
- PDF SHA-256: `74d4d4f7b4154694bbb47e0257d9d6f7e663f21348fa4bc9346065eb06b82c92`
- 9 191 righe TUN (101 età × 91 invalidità) con `point_value` validati e monotonicità verificata
- Engine: `italy_tun_point_value_v1` con `amount_rule = row_amount_direct` e `fault_reduction = true`
- LegalReview umana registrata, status promossi a `approved` nei tre livelli

### Calculator engine
- 4 livelli di gating: source approved → dataset approved → formula approved → row match unico
- Pluggable registry per espandere ad altri paesi/case_type
- 2 amount_rule registrate: `point_value_times_disability_percentage`, `row_amount_direct`
- Tutto JSON-serializzabile per persistenza in `Simulation.output_data` + breakdown + sources_snapshot

### Staff dashboard
- `/staff/project-status/` (login + staff required)
- Snapshot live di source/dataset/formula, hash PDF, conteggi rows/Simulation/Lead/Report, moduli attivi/upcoming, no-go per produzione

### Compliance / GDPR
- `ConsentRecord` per ogni Simulation pubblica (purpose `simulation_processing`)
- `ConsentRecord` per ogni Lead (consenso esplicito a privacy + disclaimer)
- `PrivacyAuditEvent` per `DATA_ACCESSED` (run_simulation), `DATA_EXPORTED` (PDF), `DATA_DELETION_*`
- Honeypot `website` su tutti i form pubblici
- `RedactPIIFilter` su logging
- Auditlog su modelli sensibili (`LegalSource`, `CompensationDataset`, `CalculationFormula`, `ExtractionLog`, `SimulationReport`, `LegalReview`)

### Test coverage
- 205 test unit tutti verdi (apps.core, apps.cases, apps.reports, apps.compensation, apps.legal_sources, apps.calculators, apps.crm, apps.compliance, apps.jurisdictions)
- 0 ruff issues, 0 black issues
- `manage.py check`: 0 silenced

## 2. Quali dati sono approvati

Snapshot al 2026-04-27 in DB locale di sviluppo:

| Modello | pk | identificatore | status |
|---|---|---|---|
| `LegalSource` | 1 | slug `it-dpr-12-2025-tun-danno-biologico` | **approved** |
| `LegalSourceAttachment` | 1 | sha256 `74d4d4f7…` | (PDF G.U.) |
| `CompensationDataset` | 1 | version_label `DPR-12-2025` | **approved** |
| `CompensationTableRow` | 1..9191 | (101 × 91) | (rows del dataset) |
| `CalculationFormula` | 1 | code `italy_art_138_tun_2025_base` | **approved** |
| `LegalReview` | 1 | reviewer `badr` (staff/superuser locale) | decision `approve` |

Le altre 4 fonti italiane seedate (`it-mimit-2025-07-aggiornamento-art-139`, `it-mimit-2025-12-aggiornamento-macrolesioni`, `it-dlgs-209-2005-cap-art-138-139`, `it-tabelle-milano-2024`) restano in `needs_review` — non ancora usate dal calculator pubblico.

## 3. Come riprodurre l'import TUN da zero

Pre-requisito: PDF G.U. del D.P.R. 12/2025 disponibile in
`legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf` (NON committato,
SHA-256 atteso `74d4d4f7…`).

```bash
# 1. Seed delle 5 fonti italiane core (idempotente, status needs_review)
python manage.py seed_italy_legal_sources

# 2. Allegare PDF + creare dataset DRAFT + formula DRAFT
python manage.py import_italy_tun_2025 \
    --source-file legal_data/sources/italy/tun_2025/dpr_12_2025_tun.pdf

# 3. Importare il CSV con le 9 191 righe (production CSV creato da
#    review assistita; tutte le righe portano legal_review_required=true
#    e no_human_legal_approval=true nel notes)
python manage.py import_italy_tun_2025 \
    --csv legal_data/sources/italy/tun_2025/tun_2025_rows.csv

# 4. Configurare i parameters runtime della formula (admin Django o shell):
#    {
#      "engine": "italy_tun_point_value_v1",
#      "requires": ["victim_age", "permanent_disability_percentage"],
#      "row_match": ["victim_age", "permanent_disability_percentage"],
#      "amount_rule": "row_amount_direct",
#      "fault_reduction": true
#    }

# 5. Legal review umana e promozione cumulativa a approved:
#    LegalSource → CompensationDataset → CalculationFormula
#    (vincoli clean(): ognuno richiede il precedente già approved)
#    Crea LegalReview(decision=approve) come traccia.
```

## 4. Verifica del calcolo 35/10/0 = 21 709 €

Con tutti i livelli `approved` e `parameters` runtime configurati:

```python
from apps.calculators.engines.italy import ItalyRoadAccidentBodilyInjuryCalculator
calc = ItalyRoadAccidentBodilyInjuryCalculator(language="it")
result = calc.compute({
    "victim_age": 35,
    "permanent_disability_percentage": 10,
    "fault_percentage": 0,
})
assert result.status == "calculated"
assert int(result.estimated_mid) == 21709
```

Casi noti:

| Input | Risultato atteso |
|---|---|
| età=35, inv=10%, fault=0 | 21 709 € |
| età=0, inv=100%, fault=0 | 1 037 028 € |
| età=35, inv=10%, fault=50 | 10 854,50 € |

Verifica via wizard: `/wizard/it/road-accident/` → riempire (35, 10, 0) → "Stima disponibile" con MIN/MID/MAX = 21 709,00 EUR.

## 5. Cosa resta da fare per produzione (no-go list)

In ordine di priorità:

| Priorità | Item |
|---|---|
| P0 | Postgres migration per prod (oggi SQLite dev) |
| P0 | `SECRET_KEY` env-driven in prod (oggi default insicuro in `settings.py`) |
| P0 | `DJANGO_DEBUG=false` + `ALLOWED_HOSTS` configurati in prod |
| P0 | Backup + restore strategy del DB |
| P0 | Sentry/observability + alerting |
| P1 | Compilare `.mo` per fr/en/ar (oggi solo file `.po`) |
| P1 | Build Tailwind via PostCSS (rimuovere CDN script) |
| P1 | Email transactional sui Lead nuovi (SMTP/SES) |
| P1 | Cookie consent EU banner |
| P2 | Status display labels: 4 status × 4 lingue completate (oggi `ar` fallback inglese) |
| P2 | Tabelle 2.A/2.B/2.C TUN per range min/mid/max veri (oggi range coincidente) |
| P2 | Rate-limit sui POST pubblici (anti-abuse) |
| P2 | MFA per admin |
| P2 | Token firmato per PDF download (oggi UUID = capability token) |
| P3 | Espansione paesi: FR Loi Badinter, BE 2008/2012, MA DOC, TN CO |
| P3 | Inheritance Italia (Codice civile artt. 565+) |
| P3 | E2E Playwright in CI |
| P3 | Subdomain SEO `simulatore.studiolegalebadrane.it` |
| P3 | Audit log esportabile per richieste GDPR |

## 6. Architettura sintetica

```
apps/
  accounts/        # User custom
  core/            # Home, public pages, staff dashboard
  jurisdictions/   # Country, Currency, Language, Jurisdiction
  legal_sources/   # LegalSource, LegalSourceVersion, LegalSourceAttachment, LegalReview
  calculators/     # BaseCalculator, registry, engines, schemas
  compensation/    # CompensationDataset, CompensationTableRow, CalculationFormula, ExtractionLog
  cases/           # Simulation, SimulationEvent, wizard views, services
  reports/         # SimulationReport, PDF rendering (reportlab)
  crm/             # Lead, LeadEvent, contact form
  compliance/      # ConsentPurpose, ConsentRecord, PrivacyAuditEvent, DataDeletionRequest
  cms_content/     # (placeholder for future SEO/CMS content)
  analytics/       # (placeholder for future funnel metrics)
  inheritance/     # (placeholder for future inheritance modules)

config/
  settings.py      # env-driven, multilingua, custom user, audit middleware
  urls.py          # i18n_patterns con prefix_default_language=False
  logging_filters.py  # RedactPIIFilter (mai PII nei log)

templates/
  base.html        # layout premium ink/sand/gold, language switcher, footer
  partials/
  public/          # home, methodology, disclaimer, privacy, countries, case_types,
                   # wizard_start, wizard_italy_road_accident, wizard_result, contact, contact_thank_you
  staff/project_status.html

legal_data/        # gitignored: PDFs, CSVs, extraction logs, review tasks
docs/architecture/ # PRODUCT_REQUIREMENTS.md (canonico), MVP_STATUS.md (questo)
```

## 7. Riferimenti

- `CLAUDE.md` — istruzioni di prodotto
- `docs/architecture/PRODUCT_REQUIREMENTS.md` — requisiti vincolanti
- `legal_data/sources/italy/tun_2025/README.md` — workflow PDF/CSV
- `legal_data/sources/italy/tun_2025/tun_2025_extraction_report.md` — report estrazione assistita
- `legal_data/sources/italy/tun_2025/page_34_assisted_review_report.md` — review assistita pagina 34
- `legal_data/sources/italy/tun_2025/tun_2025_final_csv_assistant_report.md` — report finale CSV tecnico
- `docs/screenshots/live_qa/` — screenshot live verification
