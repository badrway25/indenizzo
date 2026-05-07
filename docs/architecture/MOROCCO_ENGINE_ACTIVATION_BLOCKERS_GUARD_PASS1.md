# F-morocco-engine-activation-blockers-guard-pass1

The Moudawana mapping draft tags every rule with an
`activation_blockers` list — preconditions a Studio reviewer must
lift before the rule can fire publicly (hajb-noqsan modelling,
sibling sub-typing, gender disambiguation, …). Pass3 wrote the
contract; pass1 of this iter wires the **enforcer** in the
Morocco inheritance engine.

When a Studio reviewer eventually promotes a mapping rule to
`CalculationFormula.parameters`, they carry over the blocker list.
The engine refuses to fire whenever the list is non-empty.

No public activation. Fixture-only. The mapping JSON's
`activation_allowed=false` flag is unchanged; the public MA / TN
funnels still return `unavailable_requires_legal_validation`.

## Engine guard

`apps/calculators/engines/morocco.py` gains a new gate (6.5) that
runs *after* the formula's `amount_rule` is resolved as an
inheritance-share rule and *before* input validation:

```python
blockers = _extract_activation_blockers(params)
if blockers:
    return self._build_result(
        status=UNAVAILABLE_REQUIRES_LEGAL_VALIDATION,
        sources=source_refs,
        warnings=[diagnostic_to_internal_warning(INHERITANCE_RULE_ACTIVATION_BLOCKED)],
        missing_documents=[INHERITANCE_RULE_ACTIVATION_BLOCKED],
    )
```

`_extract_activation_blockers(params)` reads the canonical
`params['activation_blockers']` slot first. For
forward-compatibility with future formulas that nest the rule
payload under `rule_metadata` or `selected_rule`, it also looks at
those siblings. A non-list value (e.g. a string) is silently
treated as empty — the engine refuses to *infer* a blocker from a
malformed payload.

## Diagnostic

`apps/calculators/diagnostics.py` registers
`INHERITANCE_RULE_ACTIVATION_BLOCKED = "inheritance_rule_activation_blocked"`
with `public_safe=False` (default). The translated message is
*"The selected inheritance rule still carries one or more activation
blockers declared in its mapping payload. The engine refuses to fire
the rule until every blocker is lifted by a Studio reviewer."* The
diagnostic only ever lands in `Simulation.output_data` (audit /
Studio dashboard) — the public result template never renders it.

## Tests

New file
`apps/calculators/test_morocco_engine_activation_blockers_guard_pass1.py`
(11 tests):

| # | Test |
|---|------|
| 1 | `test_engine_calculates_when_blockers_absent` |
| 2 | `test_engine_calculates_when_blockers_empty_list` |
| 3 | `test_engine_unavailable_when_blockers_present` |
| 4 | `test_mapping_blocked_mother_rule_has_non_empty_blockers` |
| 5 | `test_engine_refuses_promoted_blocked_mother_rule` |
| 6 | `test_engine_guards_on_nested_rule_metadata_blockers` |
| 7 | `test_engine_ignores_malformed_blockers` |
| 8 | `test_diagnostic_is_internal_only` |
| 9 | `test_public_ma_result_does_not_leak_diagnostic_slug` |
| 10 | `test_italy_smoke_unchanged_with_pass1_guard` |
| 11 | `test_italy_pdf_first_four_bytes_unchanged` |

Test 5 is the load-bearing one: it pulls the
`ma-inh-mother-no-descendants-multi-siblings-blocked` rule
straight from the mapping JSON, copies its `activation_blockers`
list into a synthetic APPROVED `CalculationFormula.parameters`,
and asserts the engine refuses to fire.

Full suite: **1441 passed, 1 skipped** (was 1430 → +11 pass1 tests).

## Browser visual QA

Capture script
`scripts/capture_morocco_engine_activation_blockers_guard_pass1.py`.
Tailwind CDN route-aborted (local CSS only).

Desktop screenshots at
`docs/screenshots/live_qa/morocco_engine_activation_blockers_guard_pass1/after/desktop/`:

| # | Frame |
|---|-------|
| 01 | `/wizard/ma/inheritance/` — wizard form |
| 02 | POST → `/wizard/result/<id>/` — result MA unavailable (no EUR amounts, no shares, no diagnostic slug) |
| 03 | `/ar/wizard/ma/inheritance/` — RTL wizard |
| 04 | AR POST → result page (RTL, no diagnostic slug) |

The result page shows the standard "Risultato preliminare" panel
with "Caso ricevuto" badge — the curated public message for
inheritance reviews. No EUR amount, no share fraction, no
`inheritance_rule_activation_blocked` slug surfaces.

## Audits + validation

| Gate | Result |
|------|--------|
| `audit_public_content_hygiene.py` | OK (0 issues) |
| `audit_public_result_messages.py` | OK (no technical strings on any fixture) |
| `audit_local_css_coverage.py` | 319 / 319 covered, 0 missing, 0 critical |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |
| `pytest -q` | **1441 passed**, 1 skipped (was 1430 → +11) |
| `ruff check .` | All checks passed |
| `black --check .` | 307 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |

## What did NOT change

- No `LegalSource.status` change.
- No `LegalReview` row created.
- No `CompensationDataset` / `CalculationFormula` /
  `CompensationTableRow` created or modified in production state.
- Mapping JSON unchanged (`source_sha256` still
  `41db4ab3…3df09d38033563beda96`, 489 071 bytes,
  `iter=F-inheritance-wizard-spouse-gender-pass2`,
  `activation_allowed=false`).
- No FR / BE / MA / TN public calculator activation.
- Italia 35/10/0 still produces 26 268 / 27 353 / 28 439 EUR.
- IT PDF first 4 bytes still `%PDF`.
- Public-template wording unchanged (the new diagnostic stays
  internal).

## Server live

- URL: `http://127.0.0.1:48110`
- PID: `49336`
- Stop: `Stop-Process -Id 49336 -Force` (PowerShell).

## Next step

Three follow-ups remain before MA inheritance can be activated:

1. **Promotion script.** When the Studio promotes a mapping rule to
   an APPROVED `CalculationFormula`, the script must copy the
   rule's `activation_blockers` list verbatim into
   `formula.parameters['activation_blockers']`. Until those rules'
   blockers are *lifted* (i.e. the list is emptied), the engine
   guard added in this pass will keep them inert — by design.
2. **hajb-noqsan modelling.** The blocked
   `ma-inh-mother-no-descendants-multi-siblings-blocked` rule still
   needs a Studio-signed numeric share before its blocker can be
   lifted.
3. **Engine awareness of `surviving_spouse_gender`** (separate
   from the activation guard). The husband-* / wife-* rules carry
   gender-specific preconditions in their `scenario` block; the
   engine needs to read `heirs.surviving_spouse_gender` and select
   the correct rule. Until that lands, the activation_blockers
   listed on those rules keep them inert.

Public activation also still depends on the EU 650/2012
applicable-law decision being wired into the public funnel for
cross-border cases.
