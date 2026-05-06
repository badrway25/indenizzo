# F-italy-input-validation-warnings-pass1

Migrate the Italy engine's residual input-validation warnings to the
centralized `apps.calculators.diagnostics` layer with public-safe codes
that translate to IT / FR / AR / EN, including localised field-label
interpolation for both single-field (`{field}`) and multi-field
(`{fields}`) contexts.

## Scope

Two public-facing dynamic warnings emitted by `italy.py` were still
inline English strings after `F-italy-calculator-warning-strings-pass1`:

1. `"Required input fields are missing for this calculation: …"` —
   produced when `requires` declares fields the user did not provide.
2. `"fault_percentage must be between 0 and 100"` and
   `"Invalid number for fault_percentage."` — produced by
   `_validate_fault_percentage`.

Both flowed straight into `result.warnings` and were rendered on the
public result page, exposing English text on the FR/AR locales.

## Approach

### New diagnostic codes

Added five codes to `apps/calculators/diagnostics.py`:

| Code | `public_safe` | Use |
|------|--------------|-----|
| `ITALY_REQUIRED_INPUT_MISSING` | `True` | Missing items declared by `requires`. Interpolates `{fields}`. |
| `ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE` | `True` | `fault_percentage` outside `[0, 100]`. |
| `ITALY_INVALID_PERCENTAGE_INPUT` | `True` | `fault_percentage` not a number. |
| `ITALY_INPUT_PAYLOAD_INVALID` | `False` | Internal-only payload-shape error. |
| `ITALY_FORMULA_INPUT_MISMATCH` | `False` | Internal-only formula/input mismatch. |

### Localised field labels

`_ITALY_FIELD_LABELS` was extended to every input slug surfaced by
the public warnings — `victim_age`, `permanent_disability_percentage`,
`total_temporary_disability_days`, `partial_temporary_disability_days`,
`fault_percentage`, `accident_country`, `accident_date`, `heirs`,
`estate_value`, `deceased_country_of_last_residence`, `nationality`.
Each label is a `gettext_lazy(...)` proxy that resolves at message-
render time.

### `{fields}` interpolation

`_localised_context` learned to handle a list/tuple/set in the
`"fields"` slot: it translates each slug via the field-label map and
joins with `", "`. The `{field}` (single slug) form continues to be
supported for callers that need it.

### Engine wiring

`italy.py`:

- Replaced the inline missing-input warning with
  `_diag.diagnostic_to_public_warning(_diag.ITALY_REQUIRED_INPUT_MISSING, context={"fields": tuple(missing_inputs)})`.
- `_validate_fault_percentage` now returns a diagnostic *code constant*
  rather than a raw English string. The caller routes the code to
  `_diag.diagnostic_to_public_warning` so the user sees the localised
  message.

### Cross-engine reuse

`france.py`, `belgium.py`, `morocco.py`, and `tunisia.py` reuse the
same `ITALY_REQUIRED_INPUT_MISSING` code. The codes are conceptually
shared across all engines (the prefix is a historical artefact of the
pass-1 naming) and the field-label map covers the slugs all engines
emit.

## Tests

`apps/calculators/test_italy_input_validation_warnings.py` (13 cases):

1. Required-input-missing routes through the diagnostic helper.
2. `fault_percentage < 0` routes to `ITALY_FAULT_PERCENTAGE_OUT_OF_RANGE`.
3. `fault_percentage > 100` routes to the same code.
4. `{fields}` localises in every supported language.
5. Single-slug `{field}` localises across IT/FR/AR/EN.
6. FR locale: result page contains the FR translated form, never
   the English source string.
7. AR locale: same, with the AR translation.
8. Public result page never shows raw diagnostic codes.
9. Form labels are visible in IT.
10. Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
11. IT PDF starts with `%PDF`.
12. Public result HTML contains no banned words.
13. No Pexels markers / API keys in the public result page.

The FR/AR locale tests use `translation.override(...)` around
`run_simulation` because the diagnostic message resolves at engine-
compute time using the active translation context — the wizard view
relies on `LocaleMiddleware`, but test invocations of the service
must override explicitly.

`apps/compensation/tests.py`: three pre-existing assertions relaxed
to accept the localised label forms (`victim_age` /
`age of the injured person` / `età della persona infortunata`, etc.).

## Browser QA

Captured under
`docs/screenshots/live_qa/italy_input_validation_warnings_pass1/after/`:

Desktop (8 frames):

- 01 wizard IT
- 02 wizard FR
- 03 wizard AR
- 04 result IT (35/10/0 baseline — calculated)
- 05 result IT (missing input)
- 06 result FR (missing input)
- 07 result AR (missing input)
- 08 result IT (`fault_percentage=150`)

Mobile (4 frames at 375×800):

- 01 wizard IT
- 02 result IT (missing input)
- 03 result FR (missing input)
- 04 result IT (out-of-range fault)

PDF probe: `it_baseline_pdf_probe.bin` — first 4 bytes `%PDF`.

`cdn.tailwindcss.com` is route-aborted by the capture script;
layout integrity confirms the local `static/css/site.css` carries
the result-page card and warning-card styles unaided.

## Audits

| Audit | Result |
|-------|--------|
| Public content hygiene | 0 issues across all locales |
| Public result messages | OK — every fixture is free of technical strings |
| Visible translation fallbacks | 0 fallbacks across IT/FR/AR/EN |
| Local CSS coverage | 319 / 323 classes covered, 0 critical |
| Calculator diagnostic strings | `Required input fields are missing` no longer present in `italy.py`; only the slug `formula_engine_unknown` remains as a stable identifier (intended) |

## What did NOT change

- Calculator math, gating, or DB shape.
- Legal data, sources, datasets, formulas.
- The "unavailable" path (`UNAVAILABLE_REQUIRES_LEGAL_VALIDATION`):
  `base.py` still emits the inline "No approved legal sources …"
  warning. The public-warning view filter restricts rendering to
  `status in {calculated, insufficient_input}` so the unavailable
  message stays gated to its own dedicated card.
- Tailwind CDN: stayed removed (pass-2 baseline).
