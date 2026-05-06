# Italy calculator warnings — translatable pass 1

**Iter:** `F-italy-calculator-warning-strings-translatable-pass1`.

This pass migrates the Italian calculated-path warnings to the
centralised diagnostics layer. Italy's road-accident engine
historically wrote two English sentences inline whenever the
calculator produced an estimate:

- "Estimated min/mid/max coincide because no approved
  personalisation range is configured for this engine yet."
- "Reported '<field>' is not included in the automatic calculation:
  the approved formula does not aggregate it. Verify with legal
  review for case-specific evaluation."

These are *public* warnings — they reach the result page and the
PDF report. After this iter both are stored as **public-safe**
diagnostic codes with full IT / FR / EN / AR translations, the
field name is interpolated against a localised label, and the result
template surfaces them in a premium, sand-toned callout under the
calculated-path branch.

The IT TUN smoke (35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR) is
preserved verbatim. The PDF still serves a valid `%PDF` document.

---

## Audit — Italy warning strings

`scripts/audit_calculator_diagnostic_strings.py` reports **1
distinct missing_documents slug** literal across the engine layer
(down from 14 before the diagnostics work). The remaining literal
is the `block` variable in the MA/TN engines that intentionally
forwards a slug computed elsewhere — every other diagnostic is
sourced from the centralised registry.

Italy-specific public warnings now live as:

| Warning | Diagnostic code | public_safe |
|---|---|---|
| min/mid/max coincide (single-row rule) | `italy_range_collapsed` | True |
| reported `<field>` not aggregated | `italy_field_not_aggregated` | True |
| fault reduction applied | `italy_fault_reduction_applied` | True (ready for future use) |
| fault reduction applied uniform | `italy_fault_reduction_applied_uniform` | True (ready for future use) |

The first two are emitted by the engine on the calculated path; the
last two are registered for future iters that may want to expose
the fault-reduction note on the public surface.

---

## Diagnostics public-safe API

`apps/calculators/diagnostics.py` now exposes:

```python
diagnostic_message(code, *, language=None, context=None) -> str
diagnostic_public_safe(code) -> bool          # True only for vetted codes
diagnostic_to_internal_warning(code, *, context=None) -> str   # any code
diagnostic_to_public_warning(code, *, language=None, context=None) -> str
```

`diagnostic_to_public_warning` raises `ValueError` if the code is
not flagged `public_safe=True` — engines that try to surface an
internal-only message on a public surface get an immediate guard.

`diagnostic_message` now also supports `{name}` placeholder
interpolation. `ITALY_FIELD_NOT_AGGREGATED` uses this for the
`{field}` slot, which is rendered through a localised label dict
(`medical_expenses` → "spese mediche documentate" / "frais médicaux
documentés" / "النفقات الطبية الموثّقة").

---

## Migrated Italy warnings

`apps/calculators/engines/italy.py`:

- Single-row calculated path (e.g. `point_value_times_disability_percentage`):
  - Range-collapsed warning → `ITALY_RANGE_COLLAPSED` via
    `_diag.diagnostic_to_public_warning`.
  - Field-not-aggregated warning (medical_expenses / lost_income) →
    `ITALY_FIELD_NOT_AGGREGATED` with `context={"field": field}`.
- Range calculated path (`row_amount_range_direct`):
  - Field-not-aggregated warning → same code as above.
- Internal warnings (placeholder, dataset, formula, row-match,
  range-monotonicity, formula-status helper) all routed through
  `_diag.diagnostic_to_internal_warning(_diag.<CODE>)` consistently
  with the previous iter's MA/TN/FR/BE migration.

The `missing_documents` slug for every gate is unchanged (preserved
for test stability and Studio audit log compatibility).

---

## Result page + PDF

`templates/public/wizard_result.html` was extended with a public
warnings card that renders only on the calculated path:

```html
{% if has_estimate and public_warnings %}
  <div class="mt-8 rounded-3xl border border-stone2-200 bg-sand-100 p-6 lg:p-7">
    <p class="text-[11px] uppercase tracking-[0.22em] text-gold-600 font-semibold">
      {% translate "Notes on this estimate" %}
    </p>
    <ul class="mt-3 space-y-2">
      {% for w in public_warnings %}
        <li class="flex gap-3 text-sm text-ink-800 leading-relaxed">
          <span aria-hidden="true" class="mt-1 inline-block w-1.5 h-1.5 rounded-full bg-gold-500"></span>
          <span>{{ w }}</span>
        </li>
      {% endfor %}
    </ul>
  </div>
{% endif %}
```

The view (`apps/cases/views.py::wizard_result`) builds
`public_warnings` from `simulation.output_data["warnings"]` and
passes it only when `has_estimate` is True. The no-estimate path
keeps rendering the curated `PublicResultMessage` exclusively (no
warnings exposed there).

The "Notes on this estimate" header is translated:

- IT: *Note su questa stima*
- FR: *Notes sur cette estimation*
- AR: *ملاحظات حول هذا التقدير*
- EN: *Notes on this estimate*

PDF: the IT calculated PDF still starts with `%PDF` and includes
the new public warnings (it consumes the same
`Simulation.output_data["warnings"]` array). Verified by
`test_italy_pdf_remains_valid_pdf`.

---

## i18n

`makemessages -l it -l fr -l en -l ar` extracted 5 new public-safe
strings + 1 template header. All translated in IT / FR / EN / AR.

Spot check (Italian):

```
italy_range_collapsed:
  EN: "The estimated min, central and max values coincide because the
       approved formula does not yet configure a personalisation range…"
  IT: "I valori min, centrale e max coincidono perché la formula
       approvata non configura ancora un range di personalizzazione…"

italy_field_not_aggregated (field=medical_expenses):
  EN: "The reported documented medical expenses is not included in the
       automatic estimate…"
  IT: "spese mediche documentate indicate non rientrano nella stima
       automatica…"
```

---

## Tests

`apps/calculators/test_italy_public_warnings_i18n.py` — 16 cases:

1. Italy public-safe codes return `True`.
2. Internal codes (FR/BE/MA/TN/Italy gating) remain
   `public_safe=False`.
3. `diagnostic_to_public_warning` raises `ValueError` on internal
   codes.
4. IT / FR / AR translations exist for all four Italy codes
   (parametrized over the 4 codes).
5. Field label localisation: `medical_expenses` → "spese mediche".
6. IT 35/10/0 unchanged: 26 268 / 27 353 / 28 439 EUR.
7. Single-row scenario: warning routed through public diagnostic.
8. Public result page IT renders the translated warning text.
9. PDF IT remains a valid `%PDF` document.
10. No banned public words on Italy result page.
11. No Pexels attribution leak.
12. No API key leak.
13. Single H1 regression net.

Plus 3 parametrize cases (one per language) for test 4.

Pre-existing test
`apps/compensation/tests.py::test_medical_expenses_does_not_affect_amount_but_emits_warning`
was relaxed to accept the new localised "spese mediche" form
alongside the legacy raw `medical_expenses` slug.

---

## Visual review notes

Screenshots: `docs/screenshots/live_qa/italy_public_warnings_i18n_pass1/after/`.

- `desktop/wizard_it_road_accident.png` — wizard form premium
  styled (sand background, ink CTA).
- `desktop/result_it_calculated.png` — range card showing **26 268
  / 27 353 / 28 439 EUR**, "Caso ipotetico" / "Ipotesi" / "Fonti
  legali citate" cards intact, public warnings card rendered as
  sand-100 callout on `has_estimate=True` path.
- `desktop/result_fr_calculated_FR_locale.png` — full FR rendering:
  "Résultat préliminaire", `26 268` / `27 353` / `28 439` EUR
  range, "Notes sur cette estimation" header, French warning text.
- `desktop/result_ar_calculated_AR_locale.png` — full RTL Arabic,
  range card, "ملاحظات حول هذا التقدير" header, Arabic warning
  text.
- `mobile/result_it_calculated.png`, `mobile/result_ar_calculated_AR_locale.png`
  — single-column stack, no horizontal overflow, the public-warning
  callout occupies full width.

PDF probe: `it_result_pdf_probe.bin` saved with the first 4 KB of
the calculated-path PDF response. First bytes are `b'%PDF'` —
verified by `test_italy_pdf_remains_valid_pdf`.

**Local CSS confirmation.** Every shot was captured with
`cdn.tailwindcss.com` blocked at the network layer. The pages keep
their full premium chrome (sand background, ink/gold palette,
rounded-3xl cards, shadow-card, serif headings, RTL helpers). No
visual regression vs. the previous iters.

---

## No DB / legal changes

No model edit, no migration, no `LegalSource`, `LegalReview`,
`CompensationDataset`, `CompensationTableRow`, `CalculationFormula`
created or promoted. Italy calculation values are byte-identical.

## FR / BE / MA / TN still no automatic calculations

`public_status` rows unchanged. POST on the public DB still returns
`unavailable_requires_legal_validation` for FR / BE / MA / TN. The
Italy migration only touches Italy's calculated path; the other
engines were already migrated in the previous iter.

## Italia preserved + PDF %PDF

- 35 / 10 / 0 → 26 268 / 27 353 / 28 439 EUR (verified by
  `test_italy_smoke_unchanged_after_italy_warning_migration`).
- IT PDF response starts with `%PDF` (verified by
  `test_italy_pdf_remains_valid_pdf`).
- Public result page in IT/FR/AR contains the translated warning
  card without any technical leakage.

---

## Hygiene + audits + lint

- `manage.py makemigrations --check`: No changes detected.
- `manage.py check`: 0 issues.
- `compilemessages`: OK.
- `pytest -q`: 1303 passed, 1 skipped (1287 prior + 16 new).
- `ruff check .`: All checks passed.
- `black --check .`: 278 files, 0 to reformat.
- `audit_public_content_hygiene.py`: **ok**, 0 issues, 6/6 rules.
- `audit_public_result_messages.py`: **OK**, 6/6 fixtures clean.
- `audit_calculator_diagnostic_strings.py`: 18 findings, 1 distinct
  literal slug (the deliberate `block` variable forward).
- `run_public_lighthouse_audit.py --mode playwright`: **OK**, 8/8
  routes pass.

---

## What remains for future iters

- `apps/calculators/engines/base.py` still has one inline English
  warning string ("No approved legal sources are available for this
  jurisdiction/case type …"). It is duplicated in the diagnostics
  registry under `LEGAL_SOURCES_NOT_APPROVED` but the base path
  still uses the inline version. A follow-up iter could route
  base.py through diagnostics too.
- The Italy engine's `Required input fields are missing for this
  calculation: …` and `fault_percentage…` warnings are still
  inline (they're concatenated with dynamic field names). A future
  iter could move them to `INPUT_FIELDS_MISSING` /
  `INPUT_NEGATIVE_ESTATE` codes with proper context interpolation.
- `ITALY_FAULT_REDUCTION_APPLIED` / `…_UNIFORM` codes are
  registered but not yet emitted. A future iter could expose the
  "fault reduction applied" assumption as a public warning when
  the user provided `fault_percentage > 0`.

---

## Cross-references

- Helper: `apps/calculators/diagnostics.py`
- Italy engine: `apps/calculators/engines/italy.py`
- Result view: `apps/cases/views.py::wizard_result`
- Result template: `templates/public/wizard_result.html`
- Tests: `apps/calculators/test_italy_public_warnings_i18n.py`
- Capture script: `scripts/capture_italy_public_warnings_pass1.py`
- Lighthouse output:
  `docs/reports/lighthouse/italy_public_warnings_i18n_pass1/`
- Screenshots:
  `docs/screenshots/live_qa/italy_public_warnings_i18n_pass1/`
- PDF probe:
  `docs/screenshots/live_qa/italy_public_warnings_i18n_pass1/after/it_result_pdf_probe.bin`
- Sibling iters:
  - `docs/architecture/CALCULATOR_WARNING_STRINGS_TRANSLATABLE_PASS1.md`
  - `docs/architecture/RESULT_PAGE_LOCALIZATION_PASS1.md`
  - `docs/architecture/FRONTEND_LOCAL_CSS_PREMIUM_VISUAL_QA_PASS1.md`
