# F-tunisia-csp-adjacent-article-ranges-fetch-pass2

The CSP Livre IX corpus on jurisitetunisie.com is split across **7
HTML pages**. Pass1 only had `Csp1100.htm` (arts 122-143, Hajb).
Pass2 fetched the 6 adjacent pages so the Livre IX is now covered
for **arts 89-152** (with documented gaps at 85-88, 109, 111, 112).
**No share_spec is derived** — every rule stays blocked. EU 650/2012
remains classified `blocked_fetch_failed` and non-load-bearing.

## Source verification

Discovery probe targeted `https://www.jurisitetunisie.com/tunisie/codes/csp/Csp{nnnn}.htm`
in 5-step increments from 1010 to 1175. Every page that:
- returned HTTP 200,
- contained at least one `<a id="aXXX"></a>` anchor, and
- mentioned "Livre IX"
was a candidate.

Result: 7 pages match the criterion. Sha256 verified by
`sync_official_sources` for each (manifest classification =
`fetch_success`).

| slug | local file | size | sha256 (first 16) | anchored arts |
|------|-----------|------|--------------------|---------------|
| `tn-code-statut-personnel-livre-ix-art-89-90` | Csp1080.htm | 14 123 B | `e7825ee23a32a1f0` | 89-90 |
| `tn-code-statut-personnel-livre-ix-art-91-98` | Csp1085.htm | 21 113 B | `f291debeb9e6…` | 91-98 |
| `tn-code-statut-personnel-livre-ix-art-99-110` | Csp1090.htm | 30 539 B | `43b4204a7c8c…` | 99-110 (109 missing) |
| `tn-code-statut-personnel-livre-ix-art-113-121` | Csp1095.htm | 21 324 B | `b6891c5a222b…` | 113-121 (111-112 missing) |
| `tn-code-statut-personnel-livre-ix-succession` | Csp1100.htm | 36 183 B | `ab8078968ccfa07e` | 122-143 (Hajb) |
| `tn-code-statut-personnel-livre-ix-art-144-146` | Csp1105.htm | 14 741 B | `965e96334553…` | 144-146 |
| `tn-code-statut-personnel-livre-ix-art-147-152` | Csp1110.htm | 18 862 B | `e9be440f0dd4…` | 147-152 |

**Articles missing from the local source tree**: `[85, 86, 87, 88,
109, 111, 112]`. These are not anchored on any of the visible
jurisitetunisie.com Livre IX pages. The mapping records the gap
under `missing_articles_in_local_source_tree` and the rebuilder's
`blockers_before_activation` mentions it explicitly. No fabricated
text — Studio reviewer must consult an alternative edition (e.g.
JORT 1956 originale) to fill the gap.

## Files created / modified

| Path | Change |
|------|--------|
| `config/official_source_registry.json` | added 6 new TN CSP slugs (cloned from existing template); fixed pre-existing UTF-8 mojibake on the BE 1989 entry's `content_must_contain` markers |
| `legal_data/sources/tunisia/official_downloaded/tn-code-statut-personnel-livre-ix-art-{89-90,91-98,99-110,113-121,144-146,147-152}.html` | new — fetched real pages |
| `legal_data/sources/tunisia/official_downloaded/official_sync_manifest.json` | refreshed with 8 entries |
| `LegalSource.notes` for the 6 new slugs | `[official_sync]` and `[official_source_validation]` blocks committed (status=`needs_review` for all 6 — Studio review pending) |
| `legal_data/sources/tunisia/extracted/csp_livre_ix_inheritance_articles.json` | rewritten — multi-page schema, 61 articles, `pages` block + per-article `source_slug`/`source_sha256` |
| `legal_data/mappings/tunisia_inheritance_mapping_draft.json` | rewritten — 61 blocked rules, every rule pins its own `source_slug`+`source_sha256`; iter pin = pass2 |
| `docs/legal_sources/TUNISIA_CSP_LIVRE_IX_INHERITANCE_EXTRACTION.md` | rewritten — page-by-page table |
| `scripts/legal_data/extract_tunisia_csp_inheritance_articles.py` | rewritten — multi-file scanner, per-page sha verification, gap reporting |
| `scripts/legal_data/rebuild_tunisia_inheritance_mapping_draft.py` | rewritten — multi-source context_sources, per-rule source attribution, expanded blockers |
| `apps/calculators/test_tunisia_csp_mapping_draft.py` | updated `test_extraction_json_exists_and_official_html_basis` for new multi-source schema |
| `apps/calculators/test_tunisia_csp_mapping_draft_pass2.py` | new — 24 pass2 tests |
| `scripts/capture_tunisia_csp_adjacent_article_ranges_fetch_pass2.py` | new |
| `docs/architecture/TUNISIA_CSP_ADJACENT_ARTICLE_RANGES_FETCH_PASS2.md` | this file |

## Articles extracted

61 articles (was 22). Confidence distribution: all `high` —
each anchored article has body text ≥ 80 chars containing at least
one doctrinal keyword.

| Range | Page slug | Count |
|-------|-----------|-------|
| 89-90 | `tn-code-statut-personnel-livre-ix-art-89-90` | 2 |
| 91-98 | `tn-code-statut-personnel-livre-ix-art-91-98` | 8 |
| 99-110 | `tn-code-statut-personnel-livre-ix-art-99-110` | 11 |
| 113-121 | `tn-code-statut-personnel-livre-ix-art-113-121` | 9 |
| 122-143 | `tn-code-statut-personnel-livre-ix-succession` | 22 |
| 144-146 | `tn-code-statut-personnel-livre-ix-art-144-146` | 3 |
| 147-152 | `tn-code-statut-personnel-livre-ix-art-147-152` | 6 |
| **Total** | | **61** |

## Mapping draft

`legal_data/mappings/tunisia_inheritance_mapping_draft.json`:

- `iter`: `F-tunisia-csp-adjacent-article-ranges-fetch-pass2`
- `status`: `draft`
- `activation_allowed`: `false`
- `needs_manual_review`: `true`
- `rules`: **61** (one per extracted article)
- All rules carry `blocked: true`, `share_spec: null`,
  `activation_blockers: [...]`, `source_slug`, `source_sha256`.
- Hajb-tagged rules (arts 122-143): 22, with the extra Hajb
  blocker.
- Non-Hajb rules: 39, with the standard "no share_spec derived" +
  "EU 650 still blocked" blockers.
- `context_sources`: 6 new CSP slugs as `real_verified` /
  `load_bearing=true`, plus `tn-code-dip-loi-98-97`
  (`real_verified` / non-load-bearing) and
  `eu-regulation-650-2012-successions` (`blocked_fetch_failed` /
  non-load-bearing).
- `unsupported_mechanisms`: 7 entries (hajb, 'awl, radd,
  asaba_residuary_ordering, applicable_law_decision,
  dip_eu_cross_border_coordination,
  eu_650_blocked_real_source_dependency).

## Tests

| File | Coverage |
|------|----------|
| `apps/calculators/test_tunisia_csp_mapping_draft.py` (pass1) | 17 tests; updated `test_extraction_json_exists_and_official_html_basis` for new multi-source schema |
| `apps/calculators/test_tunisia_csp_mapping_draft_pass2.py` | 24 tests; new |
| `apps/legal_sources/test_official_source_anti_stub_guard_pass1.py` | unchanged guards (still pass) |

Pass2 tests:

| # | Test |
|---|------|
| 1-6 | `test_new_csp_file_is_real[*]` (parametrised x6) |
| 7-12 | `test_new_csp_file_mentions_livre_ix[*]` (parametrised x6) |
| 13 | `test_extraction_covers_seven_pages` |
| 14 | `test_extraction_ranges_match_contract` |
| 15 | `test_mapping_has_61_blocked_rules` |
| 16 | `test_mapping_context_sources_include_new_slugs` |
| 17 | `test_mapping_iter_pin_is_pass2` |
| 18 | `test_no_synthetic_or_fake_markers` |
| 19 | `test_tn_public_funnel_still_unavailable_after_pass2` |
| 20 | `test_no_legal_review_row_created` |
| 21 | `test_no_calculation_formula_for_tn_inheritance` |
| 22 | `test_italy_smoke_unchanged_with_tn_csp_pass2` |
| 23 | `test_italy_pdf_first_four_bytes_unchanged` |
| 24 | `test_each_new_csp_file_present_in_manifest_with_matching_sha` |

Full suite: **1490 passed, 1 skipped** (was 1466 → +24 pass2 tests +
the pass1 test updated for the new schema).

## EU 650 blocked treatment (unchanged)

EU 650/2012 stays:
- `status: blocked_fetch_failed` (EUR-Lex returns HTTP 202 + empty
  body for synchronous fetches).
- `load_bearing: false`.
- `manual_unblock_path` documented inline so a future iter can
  restore the source without re-deriving the steps.

The mapping refuses to use it as a load-bearing reference. Every
rule's `activation_blockers` mentions this dependency.

## What did NOT change

- No `LegalReview` row created.
- No `CalculationFormula` row created or modified.
- No `CompensationDataset` promoted.
- No `LegalSource.status` mutation: the original
  `tn-code-statut-personnel-livre-ix-succession` and
  `tn-code-dip-loi-98-97` stay `approved`; the 6 new slugs are
  `needs_review` (Studio promotion pending).
- TN public calculator stays `unavailable_requires_legal_validation`.
- TN result page still cites only the 2 originally `approved`
  sources (CSP Livre IX + Code DIP). The 6 new slugs are
  intentionally invisible to the public until Studio promotion.
- Italia 35/10/0 still returns 26 268 / 27 353 / 28 439 EUR
  (test `test_italy_smoke_unchanged_with_tn_csp_pass2`).
- Italy DPR-12-2025 PDF first 4 bytes still `%PDF`.
- Moudawana mapping unchanged
  (`source_sha256=41db4ab3…`, `iter=F-inheritance-wizard-spouse-gender-pass2`).

## Side fix

The earlier registry edit (in
`F-tunisia-official-source-real-files-restore-pass1`) had introduced
a UTF-8 double-encoding on the BE 1989 marker `responsabilité`
(stored as `responsabilité`). This iter detected the regression via
`apps/legal_sources/test_official_source_fetch.py::test_be_loi_registry_entry_is_present_and_valid`
and fixed every mojibake'd string in
`config/official_source_registry.json` via a deep-traversal
`encode('latin-1').decode('utf-8')` round-trip.

## Browser live QA

Capture script
`scripts/capture_tunisia_csp_adjacent_article_ranges_fetch_pass2.py`.
Tailwind CDN route-aborted (local CSS only).

Desktop (1440 × 900):
`docs/screenshots/live_qa/tunisia_csp_adjacent_article_ranges_fetch_pass2/after/desktop/`

| # | Frame |
|---|-------|
| 01 | `/countries/tunisia/` |
| 02 | `/wizard/tn/inheritance/` |
| 03 | POST → result TN unavailable (CSP + DIP cited; no EUR / shares / diagnostic slug) |
| 04 | `/ar/wizard/tn/inheritance/` (RTL) |
| 05 | AR POST → result unavailable (RTL) |

The result page still cites only the originally-approved CSP Livre
IX (Csp1100) and Code DIP — the 6 new pages are still
`needs_review` and intentionally invisible to the public.

## Audits + validation

| Gate | Result |
|------|--------|
| `audit_public_content_hygiene.py` | OK (0 issues, 33 pages clean) |
| `audit_public_result_messages.py` | OK (no technical strings on any fixture) |
| `audit_local_css_coverage.py` | 319 / 319 covered, 0 missing, 0 critical |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |
| `pytest -q` | **1490 passed**, 1 skipped (was 1466 → +24) |
| `ruff check .` | All checks passed |
| `black --check .` | 313 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |
| `manage.py compilemessages` | No errors |

## Server live

- URL: `http://127.0.0.1:48113`
- PID: `64280`
- Stop: `Stop-Process -Id 64280 -Force` (PowerShell).

## Next step

Three follow-ups remain before any TN rule can fire publicly:

1. **Manual download for arts 85-88, 109, 111, 112.** These are not
   anchored on jurisitetunisie.com. A Studio reviewer must source
   them from an alternative edition (JORT 1956 originale or other
   gazette), then re-run the extractor and rebuilder.
2. **Unblock EU 650/2012.** Either implement an EUR-Lex
   session-aware fetcher (follow the HTTP 202 redirect and poll the
   prepared URL), or manually download
   `https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32012R0650`
   into `legal_data/sources/eu/official_downloaded/` and re-run
   `sync_official_sources` + `validate_official_legal_sources --commit`.
3. **Studio derivation of share_specs.** The 39 non-Hajb rules
   (arts 89-121, 144-152) are good candidates for share_spec
   derivation, but every share must be Studio-signed before the
   rule's `activation_blockers` list can be lifted. Hajb rules
   (122-143) require an additional engine extension before they can
   be unblocked.

The activation guard installed in
`F-morocco-engine-activation-blockers-guard-pass1` already
enforces "no rule with non-empty `activation_blockers` may fire" —
that contract carries forward when `tunisia_inheritance_v1` is
eventually wired to read this mapping.
