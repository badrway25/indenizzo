# F-morocco-moudawana-real-pdf-remap-pass2

Replace the synthetic-stub-rooted mapping draft from
`F-morocco-moudawana-livre-iii-mapping-draft-pass1` with one
generated from the real Moudawana PDF, now placed on disk and
validated.

## Initial sha256 verification

```
path:    legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf
size:    489 071 bytes
first40: b'%PDF-1.3\n%\xe2\xe3\xcf\xd3\n1 0 obj \n<<\n/Matrix [1 0 '
sha256:  41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96   ✅ matches expected
```

## What changed

1. **Stale `[official_source_validation]` block stripped** from
   `LegalSource(slug="ma-code-famille-moudawana-fr-pdf").notes`
   (it carried the stub-era sha `932aa55…`).
2. **Re-validation** via
   `python manage.py validate_official_legal_sources --commit --slug ma-code-famille-moudawana-fr-pdf`
   wrote a fresh validation block:
   - `validation_status: passed`
   - `sha256: 41db4ab3…`
   - `sha256_verified: true`
   - `official_source_verified: true`
3. **Extraction re-run** via
   `scripts/legal_data/extract_morocco_moudawana_inheritance_articles.py`
   against the real PDF:
   - extractor: **`pdfplumber`** (was `stub`)
   - articles: **79** (was `0`)
   - source_sha256: **`41db4ab3…`**
   - extraction_blocked_reason: **empty**
4. **Mapping draft rebuilt** via
   `scripts/legal_data/rebuild_morocco_inheritance_mapping_draft.py`
   from the freshly extracted text.

## Articles extracted from the real PDF

79 inheritance articles parsed (Livre VI, articles 321–395, plus a
handful of earlier ones that mention `héritiers` in other
contexts). The mapping anchors on the canonical six articles that
codify the fixed shares:

| Article | Topic |
|---------|-------|
| 322 | Five deductions taken from the estate before allocation |
| 337 | Six heirs entitled to a Fardh share only |
| 339, 340 | Heirs entitled to Fardh + Ta'sib (or one of the two) |
| **342** | Heirs entitled to **1/2** |
| **343** | Heirs entitled to **1/4** |
| **344** | Heir entitled to **1/8** (the wife when descendants exist) |
| **345** | Heirs entitled to **2/3** |
| **346** | Heirs entitled to **1/3** |
| **347** | Heirs entitled to **1/6** |

## Mapping draft regenerated

`legal_data/mappings/morocco_inheritance_mapping_draft.json` now
carries 8 rules anchored on the real PDF:

| Rule | Article(s) | Share | Confidence |
|------|------------|-------|-----------|
| `ma-inh-husband-without-descendants` | 342 | husband 1/2 | medium |
| `ma-inh-husband-with-descendants` | 343 | husband 1/4 | medium |
| `ma-inh-wife-without-descendants` | 343 | wife 1/4 | medium |
| `ma-inh-wife-with-descendants` | 344 | wife 1/8 | high |
| `ma-inh-multiple-daughters-no-sons` | 345 | daughters_group 2/3 | high |
| `ma-inh-mother-no-descendants-no-multi-siblings` | 346 | mother 1/3 | medium |
| `ma-inh-father-with-descendants` | 347 | father 1/6 | high |
| `ma-inh-mother-with-descendants` | 347 | mother 1/6 | high |

Top-level invariants:

```json
{
  "source_sha256": "41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96",
  "extraction_basis": "official_pdf",
  "status": "draft",
  "activation_allowed": false,
  "needs_manual_review": true
}
```

Every rule's `extracted_text_snippet` is a verbatim substring of
the corresponding article in
`moudawana_inheritance_articles.json` (enforced by the test
`test_every_rule_snippet_appears_in_extraction`).

## Synthetic / fixture artefact removal

- `legal_data/sources/morocco/extracted/moudawana_inheritance_articles.json`
  no longer carries `extractor: stub` and `extraction_blocked_reason: …`
  — both replaced by `extractor: pdfplumber` + empty
  blocked reason.
- `legal_data/mappings/morocco_inheritance_mapping_draft.json`
  no longer references "synthetic" / "fixture" / "stub" beyond the
  single explicit `previous_pass_used_synthetic_stub: false`
  provenance flag (machine-readable, value=False).
- The pass1 article numbers `322 / 337 / 341` (which were chosen as
  structural anchors absent any real text) are dropped in favour of
  the share-defining articles `342 / 343 / 344 / 345 / 346 / 347`.

The test
`test_mapping_does_not_reference_synthetic_or_fake` enforces this
on every future run.

## Tests

`apps/calculators/test_morocco_moudawana_mapping_draft.py` — 18
tests now pass (was 13 in pass1). New tests added:

| # | Test |
|---|------|
| pass2.1 | `test_mapping_records_real_pdf_sha256` — mapping carries the real sha + `extraction_basis=official_pdf` |
| pass2.2 | `test_mapping_does_not_reference_synthetic_or_fake` — banned tokens absent from the JSON content |
| pass2.3 | `test_every_rule_snippet_appears_in_extraction` — every snippet is a verbatim substring of an extracted article |
| pass2.4 | `test_every_rule_article_present_in_extraction` — every cited article is in the extraction artefact |
| pass2.5 | `test_extraction_artifact_is_not_a_stub` — extractor must be `pdfplumber`, sha must be real, size > 50 KB |

All 18 mapping tests pass. Full suite: **1411 passed, 1 skipped**.

## MA calculator status

Still `unavailable_requires_legal_validation` — verified by the
public-result test (`test_public_ma_inheritance_stays_unavailable`)
and by the live wizard probe captured in the screenshots.
The pass adds no `CompensationDataset` / `CalculationFormula` /
`CompensationTableRow` / `LegalReview` row in production.

## Browser visual QA

Capture script:
`scripts/capture_morocco_moudawana_real_pdf_remap_pass2.py`.
Tailwind CDN is route-aborted (local CSS only).

Screenshots:
`docs/screenshots/live_qa/morocco_moudawana_real_pdf_remap_pass2/after/`

- **Desktop (6):** `/countries/morocco/`, `/wizard/ma/inheritance/`,
  POST result MA unavailable, `/ar/countries/morocco/`,
  `/ar/wizard/ma/inheritance/`, AR result MA unavailable.
- **Mobile (4):** `/countries/morocco/`, `/wizard/ma/inheritance/`,
  result MA unavailable, AR Morocco wizard.

The country page still shows the gold "International inheritance
review" badge from the centralised `_public_status_panel`. The
result page shows no EUR amount and no share fraction.

## Audits + validation

| Gate | Result |
|------|--------|
| `audit_public_content_hygiene.py` | OK (0 issues) |
| `audit_public_result_messages.py` | OK (no technical strings) |
| `audit_local_css_coverage.py` | 318 / 322 covered, 0 critical |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |
| `pytest -q` | **1411 passed, 1 skipped** (was 1406) |
| `ruff check .` | All checks passed |
| `black --check .` | 302 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |
| `manage.py compilemessages` | No errors |

## Real PDF survival check

After the full pytest run, the on-disk Moudawana sha256 still
equals `41db4ab3…` — the `F-legal-data-test-fixture-isolation-pass1`
protections held: nothing inside pytest could overwrite the real
bytes.

```
size: 489071  sha: 41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96  match: True
```

## What did NOT change

- No `LegalSource.status` change (already APPROVED via earlier iter).
- No `LegalReview` row created.
- No `CompensationDataset` / `CalculationFormula` /
  `CompensationTableRow` row created or modified.
- No FR / BE / MA / TN public calculator activation.
- No Italian calculator change. Italia 35/10/0 still produces
  26 268 / 27 353 / 28 439 EUR.
- IT PDF first 4 bytes still `%PDF`.

## Server live

- URL: `http://127.0.0.1:48107`
- PID: `2036`
- Stop: `Stop-Process -Id 2036 -Force` (PowerShell).

## Next step

Two follow-ups remain before the public MA calculator can be
activated:

1. **Studio review of the 8 rules.** A signed reviewer reads each
   `extracted_text_snippet` against the full Livre VI text in the
   PDF. Confidence levels can then be raised; ambiguous cases
   (e.g. mother-1/3 in article 346 conditioned on absent siblings)
   may be split into more rules or rejected.
2. **Hajb / 'awl / radd / asaba modelling.** The non-modelled
   concepts in the mapping JSON each need their own iter before
   the engine output can claim faraïd completeness.

Public activation requires both. The wizard must also expand its
input shape (sibling counts at minimum) before
`ma-inh-mother-no-descendants-no-multi-siblings` can be used.
