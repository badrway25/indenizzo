# F-morocco-moudawana-livre-iii-mapping-draft-pass1

Produce a structured DRAFT mapping of Moroccan inheritance rules
anchored on the only officially approved Moudawana source in the
project (`ma-code-famille-moudawana-fr-pdf`). The pass is
**non-activating**: it never creates an APPROVED
`CalculationFormula`, never promotes a DRAFT dataset, never
unlocks the public MA inheritance calculator.

## Inputs

- `legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf`
  — APPROVED `LegalSource` (status promoted in
  `F-legal-sources-approved-status-promotion-pass1`),
  `[official_source_validation]` block: passed.
- The dev fixture is a 227-byte synthetic PDF stub (`%PDF-1.4 fake
  test payload xxx…`). The extraction script detects this and
  emits an empty articles list with an explicit
  `extraction_blocked_reason`. The mapping draft below uses this
  stub-aware path: every rule is tagged `confidence=low` +
  `needs_manual_review=true` and `extracted_text_snippet=""`.

## Articles cited

The mapping references the canonical Moudawana article numbers
that govern succession:

| Rule | Article references |
|------|--------------------|
| `ma-inh-spouse-with-descendants`     | 322, 337, 341 |
| `ma-inh-spouse-without-descendants`  | 322, 337 |
| `ma-inh-husband-with-descendants`    | 322, 337 |
| `ma-inh-husband-without-descendants` | 322, 337 |
| `ma-inh-mother-with-descendants`     | 337, 341 |
| `ma-inh-father-with-descendants`     | 337, 341 |
| `ma-inh-only-daughters`              | 337, 341 |
| `ma-inh-single-daughter`             | 337, 341 |

These are the article numbers in Livre VI of the Code de la
Famille (Loi 70-03). Because the dev PDF is a stub, no actual
article text is included in the mapping snippets — the
`extracted_text_snippet` field is empty for every rule and
`needs_manual_review=true` is set on every rule.

## What was mapped

| Rule | scenario | share_spec |
|------|----------|------------|
| `ma-inh-spouse-with-descendants`     | spouse + ≥1 son + ≥0 daughters | spouse=1/8 ; sons_group=remainder_2_to_1 ; daughters_group=remainder_2_to_1 |
| `ma-inh-spouse-without-descendants`  | spouse + 0 son + 0 daughter    | spouse=1/4 |
| `ma-inh-husband-with-descendants`    | husband + ≥1 son + ≥0 daughters | husband=1/4 |
| `ma-inh-husband-without-descendants` | husband alone                  | husband=1/2 |
| `ma-inh-mother-with-descendants`     | mother + ≥1 son                | mother=1/6 |
| `ma-inh-father-with-descendants`     | father + ≥1 son                | father=1/6 |
| `ma-inh-only-daughters`              | ≥2 daughters, no sons          | daughters_group=2/3 |
| `ma-inh-single-daughter`             | 1 daughter, no sons            | daughters_group=1/2 |

## Concepts NOT modelled

The mapping is intentionally narrow. The following Moudawana
concepts are listed in `non_modelled_concepts` and remain pending:

- `hajb` (exclusion of an heir by a closer-degree heir)
- `'awl` (proportional reduction when fixed shares > 1)
- `radd` (devolution of the residue)
- `asaba` ordering across degrees
- `kalala` / `mu'tiqa` edge cases
- EU 650/2012 applicable-law selection (handled by a separate
  skeleton iter, not this one)

## DRAFT compensation dataset — DB or skip?

**Skipped.** The existing `CompensationDataset` /
`CompensationTableRow` model expects numeric `point_value`
entries with age / disability range matching. The Moudawana
mapping is a set of fractional share specifications keyed by
heir-class scenario, not a numeric matrix. Forcing the share
specs into a JSON `extra` field while leaving `point_value=0`
would be a square peg in a round hole and would lure a future
reader into thinking the dataset is closer to activation than it
is. The JSON file
`legal_data/mappings/morocco_inheritance_mapping_draft.json` is
the canonical artefact for this iter; a future iter that adds a
proper `CompensationShareSpecRow` model (or extends
`CompensationTableRow` with a `share_spec_text` column) is the
right place for DB-side persistence.

The test
`apps/calculators/test_morocco_moudawana_mapping_draft.py::test_no_unsupported_draft_dataset_created`
greps the production app code to make sure no loader references
the forbidden DRAFT label.

## Why the public calculator stays inactive

The MA public calculator gating chain (in
`apps/calculators/engines/morocco.py`) requires:

1. an APPROVED `LegalSource` for MA   ✅ (done in pass-1 promotion)
2. an APPROVED `CompensationDataset`   ❌ (not created)
3. an APPROVED `CalculationFormula`    ❌ (not created)

Steps 2 + 3 are deliberately not performed here. The wizard
result therefore continues to show the
"International inheritance review" panel with no automatic shares.

## Relation to EU 650/2012 applicable-law skeleton

`apps/calculators/applicable_law.py` already contains a skeleton
that decides whether a cross-border MA-resident case falls under
Moroccan substantive law or under another forum's law (per Reg.
650/2012). The Moudawana mapping draft above describes
**substantive shares once Moroccan law is selected** — it does not
itself decide jurisdiction. Wiring the two together is a separate
iter; this pass keeps the skeleton + the mapping orthogonal.

## Browser visual QA

Capture script:
`scripts/capture_morocco_moudawana_mapping_draft_pass1.py`. Tailwind
CDN is route-aborted (local CSS only).

Screenshots:
`docs/screenshots/live_qa/morocco_moudawana_mapping_draft_pass1/after/`

- **Desktop (6):** `/countries/morocco/`, `/wizard/ma/inheritance/`,
  POST result MA unavailable, `/ar/countries/morocco/`,
  `/ar/wizard/ma/inheritance/`, AR result MA unavailable.
- **Mobile (4):** `/countries/morocco/`,
  `/wizard/ma/inheritance/`, result MA unavailable,
  `/ar/wizard/ma/inheritance/`.

### Visual notes

- The country page never claims that the MA calculator is active.
  The public-status panel still shows the gold "International
  inheritance review" badge from the centralised
  `_public_status_panel` partial.
- The wizard result page does not show any EUR amount or share
  fraction; the body is the unavailable card + the "what happens
  next" block.
- AR/RTL layout: heading uses Amiri (serif Arabic), body uses
  Tajawal (sans Arabic) — the previous polish pass carries over.
- Mobile layouts stack cleanly on the 375×800 viewport. No
  horizontal overflow, no broken card.

## Audits ran for this pass

| Audit | Result |
|-------|--------|
| `audit_public_content_hygiene.py` | OK (0 pages with issues) |
| `audit_public_result_messages.py` | OK (no technical strings) |
| `audit_local_css_coverage.py` | 318 / 322 covered, 0 critical |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |

## Validation gates

| Gate | Result |
|------|--------|
| `pytest -q` | 1396 passed, 1 skipped |
| `ruff check .` | All checks passed |
| `black --check .` | 297 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |
| `manage.py compilemessages` | No errors |

## What did NOT change

- No `LegalSource.status` change.
- No `CompensationDataset` row created.
- No `CalculationFormula` row created.
- No `CompensationTableRow` row created.
- No `LegalReview` row created.
- No FR / BE / MA / TN public calculator activation.
- No Italian calculator change. Italia 35/10/0 still produces
  26 268 / 27 353 / 28 439 EUR.
- IT PDF first 4 bytes still `%PDF`.

## Server live

- URL: `http://127.0.0.1:48107`
- PID: `65504`
- Stop: `Stop-Process -Id 65504 -Force` (PowerShell).

## Next step

The mapping draft is the input for two distinct future iters:

1. **Real Moudawana PDF.** Replace the synthetic fixture in
   `legal_data/sources/morocco/official_downloaded/` with the
   actual Code de la Famille PDF, re-run
   `scripts/legal_data/extract_morocco_moudawana_inheritance_articles.py`,
   and refresh the mapping draft so each rule's
   `extracted_text_snippet` carries real article text.
2. **Studio review pass.** A signed Studio review walks the
   mapping rules article by article, raises `confidence` from
   `low` to `high` where the text supports it, models the missing
   concepts (`hajb`, `'awl`, `radd`, `asaba`), and decides whether
   the share-spec storage moves from JSON-only to a new
   `CompensationShareSpecRow` model.

Activation of the public MA inheritance calculator is at minimum
two more iters away.
