# Calculator warning strings — translatable pass 1

**Iter:** `F-calculator-warning-strings-translatable-pass1`.

This pass centralises every diagnostic warning emitted by the
calculator engines. The MA / TN / FR / BE / IT engines used to write
hard-coded English sentences inline. Those sentences were never
shown publicly (after `F-result-page-localization-pass1` the
template never iterates `output_data["warnings"]` for the no-estimate
path) but they were stored in `Simulation.output_data` and visible
to Studio reviewers / audit logs.

Now every engine routes through
`apps/calculators/diagnostics.py::diagnostic_to_internal_warning`
with a stable `code` from a fixed vocabulary. The same code drives
the `missing_documents` slug (preserved verbatim for test stability)
and is mapped to a `gettext_lazy`-wrapped message that renders in IT
/ FR / EN / AR.

---

## What was centralised

`apps/calculators/diagnostics.py` exposes:

```python
diagnostic_message(code, *, language=None, context=None) -> str
diagnostic_public_safe(code) -> bool
diagnostic_to_internal_warning(code, *, context=None) -> str
known_diagnostic_codes() -> tuple[str, ...]
```

Plus 21 stable `code` constants (a superset of the 14 historical
`missing_documents` slugs, for forward compatibility):

| Constant | Slug |
|---|---|
| `LEGAL_SOURCES_NOT_APPROVED` | `legal_sources_not_approved` |
| `COMPENSATION_DATASET_NOT_APPROVED` | `compensation_dataset_approved` |
| `RANGE_DATASET_NOT_APPROVED` | `range_dataset_approved` |
| `CALCULATION_FORMULA_NOT_APPROVED` | `calculation_formula_approved` |
| `CALCULATOR_ENGINE_PENDING` | `calculator_engine_pending_for_jurisdiction` |
| `FORMULA_ENGINE_UNKNOWN` | `formula_engine_unknown` |
| `FORMULA_AMOUNT_RULE_UNKNOWN` | `formula_amount_rule_unknown` |
| `FORMULA_AMOUNT_RULE_NOT_SINGLE_ROW_RANGE` | `formula_amount_rule_not_single_row_range` |
| `FORMULA_AMOUNT_RULE_NOT_INHERITANCE_SHARE` | `formula_amount_rule_not_inheritance_share` |
| `FORMULA_ROW_TYPE_MISSING` | `formula_row_type_missing` |
| `FORMULA_RANGE_PARAMETERS_INCOMPLETE` | `formula_range_parameters_incomplete` |
| `COMPENSATION_ROW_MATCH_MISSING` | `compensation_row_match` |
| `COMPENSATION_ROW_DISAMBIGUATION` | `compensation_row_disambiguation` |
| `COMPENSATION_RANGE_INCONSISTENT` | `compensation_range_inconsistent` |
| `INHERITANCE_SHARE_SPEC_INVALID` | `shares_spec_invalid` |
| `APPLICABLE_LAW_REVIEW_REQUIRED` | `applicable_law_review_required` |
| `APPLICABLE_LAW_CONTEXT_MISSING` | `applicable_law_context_missing` |
| `INPUT_FIELDS_MISSING` | `input_fields_missing` |
| `INPUT_ESTATE_VALUE_INVALID` | `input_estate_value_invalid` |
| `INPUT_NEGATIVE_ESTATE` | `input_negative_estate` |
| `INPUT_NO_HEIR_ALLOCATION` | `input_no_heir_allocation` |

`diagnostic_public_safe(code)` returns `False` for every code today
— the public template never renders these. The flag exists so a
future iter can selectively expose specific codes when they become
genuine field-level errors.

---

## Engine migration

Four engine files were migrated to call
`_diag.diagnostic_to_internal_warning(_diag.<CODE>)` instead of
inline English strings:

- `apps/calculators/engines/morocco.py`
- `apps/calculators/engines/tunisia.py`
- `apps/calculators/engines/france.py`
- `apps/calculators/engines/belgium.py`

The `missing_documents` slugs are unchanged (test stability
guarantee). Only the `warnings` list values are now sourced from the
diagnostics layer.

`apps/calculators/engines/italy.py` was **not** migrated — Italy is
the calculated-path engine and its inline warnings are part of the
public surface (e.g. `"Estimated min/mid/max coincide because…"`,
`"Reported '<field>' is not included…"`). Those messages will move
to a future Italy-specific diagnostic batch with public-safe flags
toggled on.

---

## i18n

`makemessages -l it -l fr -l en -l ar` extracted 21 new msgids from
`apps/calculators/diagnostics.py`. All 21 are translated in IT, FR,
EN and AR. `compilemessages` rebuilds all four `django.mo` files.

Translation spot-checks:

```
LEGAL_SOURCES_NOT_APPROVED
EN: "No approved legal sources are available for this jurisdiction…"
IT: "Nessuna fonte legale approvata è disponibile per questa giurisdizione…"
FR: "Aucune source juridique approuvée n'est disponible pour cette juridiction…"
AR: "لا تتوفّر مصادر قانونية معتمدة لهذا الاختصاص…"

APPLICABLE_LAW_REVIEW_REQUIRED
EN: "Applicable-law context requires Studio review before any inheritance shares…"
IT: "Il contesto della legge applicabile richiede una revisione dello Studio…"
FR: "Le contexte de la loi applicable requiert une revue du Cabinet…"
AR: "يتطلب سياق القانون المطبّق مراجعة من المكتب…"
```

---

## What remains internal

Every diagnostic is internal-only:

- `Simulation.output_data["warnings"]` carries the localised message
  (in the current request locale).
- `Simulation.output_data["missing_documents"]` carries the stable
  slug.
- `Simulation.output_data["internal"]["applicable_law_decision"]`
  (from the previous iter) carries the structured decision payload.

The public template (`templates/public/wizard_result.html`) renders
the curated `PublicResultMessage` instead. The result page never
reads `warnings`, `missing_documents`, `assumptions` or `internal`
— audited via `scripts/audit_public_result_messages.py`.

---

## Public result confirmation: no technical strings

Audit pipeline:

- `scripts/audit_public_content_hygiene.py`: **ok**, 0 issues across
  6/6 rules.
- `scripts/audit_public_result_messages.py`: **OK**, 6/6 fixtures
  free of technical strings.
- `scripts/audit_calculator_diagnostic_strings.py`: 9 distinct
  `missing_documents` slugs still appear as literals in the engines
  (down from 14 — the rest are now driven by code constants).
- `scripts/run_public_lighthouse_audit.py --mode playwright`: **OK**,
  8/8 routes pass.
- Tests: 1287 passed, 1 skipped. New
  `apps/calculators/test_diagnostics_i18n.py` carries 15 cases
  covering helper smoke, IT/FR/AR translations, FR/BE/MA/TN engine
  routing, public-result no-leak, banned-words sweep and Italia
  smoke.

---

## Visual review notes

Screenshots live under
`docs/screenshots/live_qa/calculator_warning_strings_i18n_pass1/after/`.

**Desktop 1440 × 900.**

- `result_fr_unavailable.png`, `result_be_unavailable.png` — public
  message + status panel + "Cosa succede ora" card. Zero technical
  strings.
- `result_ma_unavailable.png`, `result_tn_unavailable.png` — same
  shape, hint card visible.
- `result_it_calculated.png` — IT TUN range card 26 268 / 27 353 /
  28 439 EUR, sources list, disclaimer. Calculated path preserved.

**Mobile 375 × 800.**

- `result_ma_unavailable.png`, `result_fr_unavailable.png`,
  `result_it_calculated.png` — single-column layout, no horizontal
  overflow, premium chrome.
- `wizard_ma_inheritance_ar.png` — RTL Arabic wizard, palette and
  spacing intact.

**Local CSS confirmation.** The capture script blocks
`cdn.tailwindcss.com` at the network layer. Every shot is rendered
with `static/css/site.css` only — proving the diagnostics migration
did not break the local-CSS work from the previous iter.

---

## No DB / legal changes

No `LegalSource`, `LegalReview`, `CompensationDataset`,
`CompensationTableRow`, `CalculationFormula` created or promoted by
this iter. No migration. The wizard form is unchanged.

## FR / BE / MA / TN still no automatic calculations

`public_status` rows for FR / BE / MA / TN remain
`STATUS_PRELIMINARY_REVIEW` / `STATUS_INHERITANCE_REVIEW`. POST on
the public DB still returns
`unavailable_requires_legal_validation` because no APPROVED source
exists for these jurisdictions. The diagnostics migration only
changes the *text* of the internal warnings, not the gating chain.

## Italia preserved

`test_italy_smoke_unchanged_after_diagnostics_migration`:
35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR. The IT engine was not
touched in this iter; its inline warnings stay verbatim.

---

## Hygiene + audits + lint

- `manage.py makemigrations --check`: No changes detected.
- `manage.py check`: 0 issues.
- `compilemessages`: OK.
- `pytest -q`: 1287 passed, 1 skipped (1272 prior + 15 new).
- `ruff check .`: All checks passed.
- `black --check .`: 276 files, 0 to reformat.

---

## What remains for future iters

- Italy engine migration: `apps/calculators/engines/italy.py` still
  has inline English warnings on the *calculated path* (e.g.
  "Estimated min/mid/max coincide …"). Those are public-facing
  copy and need their own diagnostic codes with `public_safe=True`
  and dedicated translations.
- `apps/calculators/engines/base.py` still has one inline string
  ("No approved legal sources are available for this jurisdiction
  /case type …"). It is now duplicated in the diagnostics registry
  but the base path still uses the inline version. A follow-up iter
  could route base.py through diagnostics too once the wider engine
  refactor is settled.
- `diagnostic_public_safe` always returns `False` today. A future
  iter can flip specific codes (e.g. `INPUT_FIELDS_MISSING`,
  `INPUT_NEGATIVE_ESTATE`) once they are confirmed safe to surface
  as field-level errors on the public form.

---

## Cross-references

- Helper: `apps/calculators/diagnostics.py`
- Audit: `scripts/audit_calculator_diagnostic_strings.py` →
  `docs/architecture/CALCULATOR_DIAGNOSTIC_STRINGS_AUDIT.md`
- Migrated engines:
  - `apps/calculators/engines/morocco.py`
  - `apps/calculators/engines/tunisia.py`
  - `apps/calculators/engines/france.py`
  - `apps/calculators/engines/belgium.py`
- Tests: `apps/calculators/test_diagnostics_i18n.py`
- Capture script: `scripts/capture_calculator_warning_strings_pass1.py`
- Lighthouse output:
  `docs/reports/lighthouse/calculator_warning_strings_i18n_pass1/`
- Screenshots:
  `docs/screenshots/live_qa/calculator_warning_strings_i18n_pass1/`
- Sibling iters:
  - `docs/architecture/RESULT_PAGE_LOCALIZATION_PASS1.md`
  - `docs/architecture/APPLICABLE_LAW_ENGINE_INTEGRATION_PASS1.md`
  - `docs/architecture/FRONTEND_LOCAL_CSS_PREMIUM_VISUAL_QA_PASS1.md`
