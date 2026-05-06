# F-morocco-moudawana-mapping-refinement-pass3

Refine the pass2 Moudawana inheritance mapping draft. Three
structural improvements:

1. **Article 346 split into two rules** — the activatable mother-1/3
   case (no descendants, ≤1 sibling) and an explicitly blocked
   companion (no descendants, ≥2 siblings) that documents the
   doctrinal hajb-noqsan reduction we cannot yet compute.
2. **`unsupported_mechanisms` section** — every Moudawana mechanism
   the engine cannot honour (`hajb`, `'awl`, `radd`,
   `ta'sib / asaba ordering`, `kalala`, `applicable_law_decision`)
   is listed with article references and the rule_ids it blocks.
3. **`activation_blockers` per rule** — every rule now carries a
   machine-readable list of preconditions that must be satisfied
   before the engine can use the rule. Empty list = no blocker.

## Initial sha256 verification

```
sha256: 41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96   ✅ match
size:   489 071 bytes
```

The `F-legal-data-test-fixture-isolation-pass1` protections held —
the on-disk Moudawana sha is unchanged after the full pytest run.

## Wizard input audit (Task 1)

The MA / TN inheritance wizard already captures `siblings_count`
and serialises it into `input_data["heirs"]["siblings"]`:

| Form field | Type | input_data path |
|------------|------|-----------------|
| `spouse_present` | bool | `heirs.spouse` |
| `sons_count` | int (0..30) | `heirs.sons` |
| `daughters_count` | int (0..30) | `heirs.daughters` |
| `father_present` | bool | `heirs.father` |
| `mother_present` | bool | `heirs.mother` |
| `siblings_count` | int (0..30) | `heirs.siblings` |

Verified by `apps/cases/forms.py:298-303` (form field) +
`apps/cases/forms.py:363,380` (serialisation). End-to-end test
`test_pass3_wizard_form_serializes_siblings_into_heirs` exercises
the full path.

The mapping JSON's new `wizard_inputs.captured` section records
this contract. `wizard_inputs.missing_for_full_faraid` lists the
inputs that still need to be added before full faraïd modelling
(husband-vs-wife distinction, sibling sub-typing, grandchildren,
agnatic ascendants).

## Mapping refinement diff

### Article 346 split

Pass2:

```
ma-inh-mother-no-descendants-no-multi-siblings  scenario={mother:1, sons:0, daughters:0}  share=mother:1/3
```

Pass3:

```
ma-inh-mother-no-descendants-no-multi-siblings   scenario={mother:1, sons:0, daughters:0, siblings:"<=1"}  share=mother:1/3
ma-inh-mother-no-descendants-multi-siblings-blocked  scenario={mother:1, sons:0, daughters:0, siblings:">=2"}  share=null  blocked=true
```

The blocked rule:
- carries no `share_spec` (the doctrinal reduced mother share is
  out of scope for this draft);
- lists `blocked_by_unsupported_mechanism: hajb_noqsan` in its
  `activation_blockers`;
- is referenced by the `hajb` entry of `unsupported_mechanisms`
  under `blocked_rules: ["ma-inh-mother-no-descendants-multi-siblings-blocked"]`.

### `unsupported_mechanisms` section

Six entries, each with `name`, `label_en`, `article_references`,
`blocked_rules`, `comment`:

| name | articles | blocks |
|------|----------|--------|
| `hajb` | 332-335 | `ma-inh-mother-no-descendants-multi-siblings-blocked` |
| `'awl` | 364 | — |
| `radd` | 374-378 | — |
| `ta'sib / asaba ordering` | 339, 348-356 | — |
| `kalala` | 348, 351 | — |
| `applicable_law_decision` | — | — |

### Per-rule `activation_blockers`

Every rule now carries an `activation_blockers: [...]` list
(possibly empty). Examples:

- `ma-inh-husband-without-descendants` lists "article 342 also
  covers four other 1/2 cases (single daughter, single
  granddaughter, single full sister, single consanguine sister) —
  this rule isolates only the husband case".
- `ma-inh-father-with-descendants` lists "father's residual asaba
  claim on the remainder (when only female descendants exist) is
  NOT modelled here — articles 348-356".
- `ma-inh-mother-no-descendants-no-multi-siblings` lists three
  blockers including the wizard contract.
- Rules with no preconditions (e.g. `ma-inh-wife-with-descendants`,
  `ma-inh-multiple-daughters-no-sons`) carry an empty list — a
  positive-by-construction signal.

## Tests

`apps/calculators/test_morocco_moudawana_mapping_draft.py` — 23
tests now pass (was 18 in pass2). New pass3 tests:

| # | Test |
|---|------|
| pass3.1 | `test_pass3_article_346_is_split_into_two_rules` |
| pass3.2 | `test_pass3_unsupported_mechanisms_are_explicit` |
| pass3.3 | `test_pass3_every_rule_has_activation_blockers_list` |
| pass3.4 | `test_pass3_wizard_inputs_describe_siblings` |
| pass3.5 | `test_pass3_wizard_form_serializes_siblings_into_heirs` |

Full suite: **1416 passed, 1 skipped** (was 1411 → +5).

## Browser visual QA

Capture script:
`scripts/capture_morocco_moudawana_mapping_refinement_pass3.py`.
Tailwind CDN route-aborted (local CSS only).

Screenshots:
`docs/screenshots/live_qa/morocco_moudawana_mapping_refinement_pass3/after/desktop/`

| # | Frame |
|---|-------|
| 01 | `/countries/morocco/` |
| 02 | `/wizard/ma/inheritance/` |
| 03 | POST → MA result unavailable |
| 04 | `/ar/wizard/ma/inheritance/` |
| 05 | AR POST → result unavailable |

The MA country landing still carries the gold "International
inheritance review" badge from `_public_status_panel`. The result
page shows no EUR amount and no share fraction. AR/RTL surfaces
unchanged.

## Audits + validation

| Gate | Result |
|------|--------|
| `audit_public_content_hygiene.py` | OK (0 issues) |
| `audit_public_result_messages.py` | OK (no technical strings) |
| `audit_local_css_coverage.py` | 318 / 322 covered, 0 critical |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |
| `pytest -q` | **1416 passed**, 1 skipped (was 1411 → +5) |
| `ruff check .` | All checks passed |
| `black --check .` | 303 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |
| `manage.py compilemessages` | No errors |

## What did NOT change

- No `LegalSource.status` change.
- No `LegalReview` row created.
- No `CompensationDataset` / `CalculationFormula` /
  `CompensationTableRow` row created or modified.
- No FR / BE / MA / TN public calculator activation.
- No Italian calculator change. Italia 35/10/0 still produces
  26 268 / 27 353 / 28 439 EUR.
- IT PDF first 4 bytes still `%PDF`.
- No wizard form change — the wizard already had `siblings_count`.

## Server live

- URL: `http://127.0.0.1:48107`
- PID: `25748`
- Stop: `Stop-Process -Id 25748 -Force` (PowerShell).

## Next step

Three follow-ups remain before MA inheritance can be activated:

1. **Husband vs wife split in the form.** The wizard's
   `spouse_present` boolean folds husband and wife together; the
   mapping rules `ma-inh-husband-*` and `ma-inh-wife-*` need a new
   `spouse_gender` (or two booleans) on the form before they can
   distinguish art. 342 from art. 343/344.
2. **hajb-noqsan modelling.** The blocked
   `ma-inh-mother-no-descendants-multi-siblings-blocked` rule
   needs a Studio-signed numeric share (typically 1/6 in classical
   doctrine) before it can become an activatable rule.
3. **Engine awareness of `activation_blockers`.** When MA is
   eventually activated, the engine must read the per-rule
   `activation_blockers` list and refuse to fire any rule that
   still carries non-empty blockers. The mapping is the contract;
   the engine's gate is the enforcer.

Public activation also still depends on every rule's `confidence`
being raised by a Studio reviewer reading the
`extracted_text_snippet` against the full PDF.
