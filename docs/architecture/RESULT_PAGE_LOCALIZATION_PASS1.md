# Result page — message localization, pass 1

**Iter:** `F-inheritance-wizard-result-page-localization-pass1`.

This pass cleans the public wizard-result page so that the
no-estimate path (FR / BE / MA / TN today, plus any future
jurisdiction whose sources are not yet APPROVED) never surfaces
backend diagnostic strings to end users. The Italian calculated path
is preserved verbatim — the existing TUN range card, sources card,
"How to read this range" panel and PDF flow keep working.

The iter introduces:

1. A small, pure-Python helper
   (`apps/cases/public_result_messages.py`) that maps
   `(simulation.status, country_code, case_type)` to a curated,
   pre-translated `PublicResultMessage` (title / summary /
   explanation / next-steps / two CTA labels).
2. A wizard-result template rewrite that renders the helper's output
   in a premium "What happens next" card, with the centralised
   public-status panel and the legal disclaimer below.
3. A removal of the previous direct surfacing of the calculator's
   raw `warnings` / `missing_documents` arrays from the public
   template. Those arrays are still stored in
   `Simulation.output_data` for audit / debug.
4. Translation entries in IT / FR / EN / AR for every new visible
   string, plus a sweep of stale `#, fuzzy` headers that were causing
   intermittent EN fallback on the new translations.
5. A live audit script
   (`scripts/audit_public_result_messages.py`) that POSTs the FR /
   BE / MA / TN forms via plain HTTP and asserts the rendered result
   page contains zero backend diagnostic strings.

---

## Technical messages removed from the public surface

The following backend-emitted phrases used to render verbatim on the
result page when the calculator gating chain blocked an estimate.
After this iter they are no longer in the public template at all:

- "No approved legal sources are available for this jurisdiction/case
  type. The simulation cannot produce an estimate without legally
  validated sources."
- "Approved legal sources are present, but no approved compensation
  dataset is linked to them …"
- "Approved compensation dataset is present, but no approved
  calculation formula is linked to it …"
- "Approved formula declares amount_rule=… but the engine only
  supports …"
- Slug-style values from `missing_documents`:
  `compensation_dataset_approved`, `calculation_formula_approved`,
  `calculator_engine_pending_for_jurisdiction`,
  `formula_engine_unknown`, `formula_amount_rule_unknown`,
  `formula_amount_rule_not_inheritance_share`,
  `formula_amount_rule_not_single_row_range`, `formula_row_type_missing`,
  `compensation_row_match`, `compensation_row_disambiguation`,
  `compensation_range_inconsistent`, `shares_spec_invalid`.
- The status code `unavailable_requires_legal_validation` (which
  previously leaked through the missing-documents bullet list).

These remain stored in `Simulation.output_data["warnings"]` /
`["missing_documents"]` for audit / Studio debug, but the public
template no longer iterates them.

---

## Public message mapping

`apps.cases.public_result_messages.build_public_result_message` is
the single source of truth. It is a pure function — no DB lookups,
no inspection of raw diagnostics — and resolves to one of four
pre-translated copy blocks:

| Match condition                                             | PublicResultMessage              |
|-------------------------------------------------------------|----------------------------------|
| `status == "insufficient_input"`                            | `_INSUFFICIENT_INPUT`            |
| `case_type in {"international_inheritance", "inheritance"}` | `_INHERITANCE_REVIEW` (MA, TN)   |
| `case_type in {"road_accident_bodily_injury", "road_accident"}` | `_ROAD_ACCIDENT_PRELIMINARY_REVIEW` (FR, BE) |
| else                                                        | `_DEFAULT_PRELIMINARY`           |

Each block carries six fields:

```python
PublicResultMessage(
    public_title,        # "International inheritance review", etc.
    public_summary,      # one-sentence headline shown above the panel
    public_explanation,  # multi-line explanation, premium tone
    public_next_steps,   # tuple of <= 3 numbered steps
    primary_cta_label,   # "Request the Studio review"
    secondary_cta_label, # "Back to the wizard"
)
```

Every field uses `gettext_lazy`, so a single `PublicResultMessage`
instance renders correctly across the four MVP locales.

---

## Result template changes

`templates/public/wizard_result.html`:

- The no-estimate branch now renders:
  - `{{ public_message.public_summary }}` as the H2 lede,
  - the centralised public-status panel,
  - a premium "What happens next" card with the curated explanation
    and the numbered next-steps list,
  - the simulation ID + creation timestamp, and
  - three CTAs: primary (label from `public_message.primary_cta_label`)
    → contact form, secondary (label from
    `public_message.secondary_cta_label`) → wizard start, plus the
    PDF download button.
- The Warnings / Missing documents / Assumptions sections are
  removed from the public surface. Assumptions is kept inside the
  calculated-path branch only.
- The "Back to methodology" CTA stays on the calculated path; the
  no-estimate path uses "Back to the wizard" instead so users can
  pick a different country/case if needed.

The calculated path (Italy TUN) is structurally untouched: the
range card, the "What this means", "Next steps" and "Calculation
basis" cards, the cited sources list and the legal disclaimer all
render exactly as before.

---

## Visual review notes

### Desktop 1440 × 900

Before / after screenshots live under
`docs/screenshots/live_qa/result_page_localization_pass1/`.

- **MA (IT)** — *before:* the page rendered a bare H2 "Your case has
  been received — the Studio will reply with a preliminary legal
  assessment." (English in IT locale due to a stale fuzzy header)
  immediately followed by a "Warnings" list containing the slug
  `No approved legal sources are available …`. *After:* the H2 is
  Italian ("Il tuo caso successorio è stato ricevuto …"); the page
  renders the public-status badge "Analisi successoria
  internazionale", followed by a premium "Cosa succede ora" card
  with the Italian explanation and numbered next-steps. Zero
  technical strings remain.
- **FR (/fr/)** — the page now reads end-to-end in French: "Résultat
  préliminaire", "Votre dossier a été reçu pour une évaluation
  juridique préliminaire par le Cabinet", "Évaluation juridique
  préliminaire" badge, "Étapes suivantes" card with three numbered
  steps, "Demander une revue juridique" primary CTA. The legacy
  English warning string is gone.
- **AR (/ar/)** — full RTL Arabic rendering: "نتيجة أولية", "تم
  استلام ملف الميراث الخاص بك …", the "تحليل ميراث دولي" badge, the
  "ما الذي يحدث بعد ذلك" card with Arabic numbered steps. CTAs:
  "اطلب مراجعة قانونية من المكتب" + "العودة إلى المعالج". Zero
  English leakage.
- **IT calculated** — preserved: the range card shows 26 268 / 27 353
  / 28 439 EUR, the "Caso ipotetico" / "Ipotesi" / "Fonti legali
  citate" cards remain.

### Mobile 375 × 800

- All three result variants (MA / TN / IT) collapse to a single
  column without horizontal overflow. The "What happens next" card
  and the public-status panel remain readable; CTAs stack at the
  bottom.

### RTL

- The Arabic page mirrors layout correctly thanks to the existing
  `dir="rtl"` set by `<html>` plus Tailwind's logical utilities. No
  manual `me-*` / `ms-*` overrides were needed.

### Premium fixes applied

- Replaced the previous direct rendering of `warnings` /
  `missing_documents` (English-only, technical) with the curated
  public message.
- Added a "What happens next" headline and numbered next-steps in
  every locale to keep the page from feeling empty when no estimate
  is shown — the no-estimate path now reads as an intentional step,
  not as an error or empty state.
- Cleared the stale `#, fuzzy` header on `Request the Studio
  review` across the four locales so the IT / FR / AR translations
  render natively instead of falling back to EN.

---

## Live verification

Server live at `http://127.0.0.1:48107/`. Six fixtures POSTed via
the new audit script:

```
POST /wizard/fr/road-accident/                      → 302 → /wizard/result/<uuid>/
POST /wizard/be/road-accident/                      → 302 → /wizard/result/<uuid>/
POST /wizard/ma/inheritance/                        → 302 → /wizard/result/<uuid>/
POST /wizard/tn/inheritance/                        → 302 → /wizard/result/<uuid>/
POST /fr/wizard/fr/road-accident/                   → 302 → /fr/wizard/result/<uuid>/
POST /ar/wizard/ma/inheritance/                     → 302 → /ar/wizard/result/<uuid>/
```

All six landing pages report zero backend diagnostic strings.

```
audit_public_content_hygiene.py                   verdict=ok
                                                  pages_with_issues=0
audit_public_result_messages.py                   verdict=OK
                                                  6/6 fixtures clean
run_public_lighthouse_audit.py --mode playwright  verdict=OK
                                                  8/8 routes pass
```

---

## FR / BE / MA / TN remain non-calculating

The iter does **not** activate any calculator. Public DB still has
zero APPROVED `LegalSource` for FR, BE, MA, TN; their public_status
rows in `apps/core/public_status.py::_RULES` remain at
`_PRELIMINARY_REVIEW` / `_INHERITANCE_REVIEW`. The calculator gating
chain still routes to `unavailable_requires_legal_validation` — what
changes is purely the user-facing copy.

## Italia preserved

- 35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR confirmed by
  `test_italy_calculated_result_unchanged`.
- The Italian PDF still serves a valid `%PDF` document
  (`test_italy_pdf_still_starts_with_pdf_marker`).

---

## What remains

- The calculator's raw warning string emitted by
  `apps/calculators/engines/base.py::_compute` ("No approved legal
  sources are available …") is no longer rendered on the public
  template, but it is still stored in `output_data["warnings"]`. A
  future iter could drop it entirely or replace it with a
  translatable `gettext_lazy` string for parity. Today it is
  invisible to the public, so it is not blocking.
- The `assumptions` array still surfaces on the calculated path —
  that is intentional, as the IT TUN result needs to expose its
  per-formula reasoning for transparency.
- A future iter might unify the calculated and unavailable paths
  under a single component (the public-status panel + a "What
  happens next" card), so the pages share the same chrome regardless
  of estimate availability.

---

## Cross-references

- Helper: `apps/cases/public_result_messages.py`
- View: `apps/cases/views.py::wizard_result`
- Template: `templates/public/wizard_result.html`
- Tests: `apps/cases/test_result_page_localization_pass1.py`
- Audit: `scripts/audit_public_result_messages.py`
- Hygiene + lighthouse output:
  - `docs/reports/result_message_audit/audit.json`
  - `docs/reports/lighthouse/result_page_localization_pass1/`
- Screenshots:
  - `docs/screenshots/live_qa/result_page_localization_pass1/before/`
  - `docs/screenshots/live_qa/result_page_localization_pass1/after/`
- Sibling iters:
  - `docs/architecture/INHERITANCE_WIZARD_INPUT_COMPLETENESS_PASS1.md`
  - `docs/architecture/PUBLIC_STATUS_BANNER_PARTIAL_PASS7.md`
