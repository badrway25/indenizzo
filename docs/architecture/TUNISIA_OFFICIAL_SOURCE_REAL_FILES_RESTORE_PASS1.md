# F-tunisia-official-source-real-files-restore-pass1

The Tunisia / EU / MA / BE official sources stored under
`legal_data/sources/**/official_downloaded/` had been silently
overwritten by 47-byte / 210-byte / 372-byte / 467-byte HTML stubs,
and the previous validation pass had blessed them as `passed`. This
iter restores the real bytes, refreshes the sync manifests + the
validation blocks, and installs durable anti-stub guards. **No
Tunisia mapping is created**; the TN public funnel still returns
`unavailable_requires_legal_validation`.

## Audit before / after

| slug | before (size / sha) | after (size / sha) | classification |
|------|---------------------|---------------------|----------------|
| `tn-code-statut-personnel-livre-ix-succession` | 47 B / `44ee9d91…` (stub) | 36 183 B / `ab8078968ccfa07e…` | `fetch_success` |
| `tn-code-dip-loi-98-97` | 210 B / `214c2e03…` (stub) | 15 424 B / `d379a07076177f66…` | `fetch_success` |
| `eu-regulation-650-2012-successions` | 467 B / `5514d2fa…` (stub) | unchanged (467 B) | **`fetch_failed`** — EUR-Lex returned HTTP 202 (async content-delivery), real download requires a session-aware fetch path |
| `ma-code-famille-moudawana-fr-pdf` | manifest stale at 227 B / `932aa556…` (disk was already real) | manifest refreshed → 489 071 B / `41db4ab3d505c16a…` | `fetch_success` |
| `be-loi-1989-11-21-rc-auto` | 372 B / `708cb6ea…` (stub) | 27 517 B / `5c8f53c123be25b2…` | `fetch_success` |

The two TN re-fetches yielded sha256 that match the historical 2026-05-03
record stored in `LegalSource.notes` `[official_sync]` block — proof
that the original sources had been overwritten, not legally rotated.

`LegalSource.status` was **never modified** during this iter. Every
row stayed `approved` (where it already was). The validation blocks
were re-committed via `manage.py validate_official_legal_sources --commit`
so their stored sha matches the restored disk content.

## Files created / modified

| File | Change |
|------|--------|
| `legal_data/sources/tunisia/official_downloaded/tn-code-statut-personnel-livre-ix-succession.html` | restored from stub (47 B → 36 183 B) |
| `legal_data/sources/tunisia/official_downloaded/tn-code-dip-loi-98-97.html` | restored (210 B → 15 424 B) |
| `legal_data/sources/tunisia/official_downloaded/official_sync_manifest.json` | rewritten by `sync_official_sources --country TN` |
| `legal_data/sources/eu/official_downloaded/official_sync_manifest.json` | refreshed; classification stays `fetch_failed` |
| `legal_data/sources/belgium/official_downloaded/be-loi-1989-11-21-rc-auto.html` | restored (372 B → 27 517 B) |
| `legal_data/sources/belgium/official_downloaded/official_sync_manifest.json` | refreshed |
| `legal_data/sources/morocco/official_downloaded/official_sync_manifest.json` | refreshed (already-real disk; manifest was stale) |
| `LegalSource.notes` for the 5 slugs | `[official_source_validation]` block re-committed via `--commit` |
| `apps/legal_sources/test_official_source_anti_stub_guard_pass1.py` | new, 8 tests |
| `scripts/capture_tunisia_official_source_restore_pass1.py` | new |
| `docs/architecture/TUNISIA_OFFICIAL_SOURCE_REAL_FILES_RESTORE_PASS1.md` | this file |

## Anti-stub guards

`apps/legal_sources/test_official_source_anti_stub_guard_pass1.py` —
8 tests that fail loud if a regression reintroduces stubs:

| # | Test |
|---|------|
| 1 | `test_no_fetch_success_manifest_entry_points_at_stub` — every `fetch_success` entry across all `official_downloaded/official_sync_manifest.json` files must point at a file > 1 KB. |
| 2 | `test_fetch_success_manifest_sha_matches_file_on_disk` — manifest sha256 must match recomputed disk sha. |
| 3 | `test_validation_passed_blocks_hash_match_local_files` — every `LegalSource.notes` `[official_source_validation]` block claiming `validation_status=passed` must be backed by a file whose sha matches the block's sha256. |
| 4 | `test_tn_csp_livre_ix_is_real_file_after_pass1` — pins TN CSP Livre IX at 36 183 B / `ab8078968ccfa07e…` and asserts the body contains "Code du statut personnel". |
| 5 | `test_tn_dip_loi_98_97_is_real_file_after_pass1` — pins TN DIP at 15 424 B / `d379a07076177f66…` and asserts "Code de Droit International" + "TITRE II". |
| 6 | `test_eu_650_remains_blocked_pending_eurlex_async_fetch` — manifest must keep EU 650 classified as `fetch_failed`; the file (if present) stays under the stub threshold. |
| 7 | `test_tn_public_funnel_still_unavailable_after_pass1` — TN POST still returns `UNAVAILABLE_REQUIRES_LEGAL_VALIDATION`. |
| 8 | `test_no_tunisia_inheritance_mapping_draft_created_in_pass1` — `legal_data/mappings/tunisia_inheritance_mapping_draft.json` must NOT exist after this iter. |

LEGAL_DATA_ROOT isolation (`F-legal-data-test-fixture-isolation-pass1`)
already prevents pytest from overwriting `legal_data/sources/**` —
that protection is already in `conftest.py::_isolate_legal_data_root`
and was preserved by this iter.

Full suite: **1449 passed, 1 skipped** (was 1441 → +8 anti-stub
guards; the test that previously asserted the EU stub size is now
implicit via guard #6).

## What did NOT change

- No `LegalReview` row created.
- No `CalculationFormula` row created or modified.
- No `CompensationDataset` promoted.
- No `LegalSource.status` mutation. Every row that was `approved`
  stayed `approved`.
- **No Tunisia inheritance mapping created.**
  `legal_data/mappings/tunisia_inheritance_mapping_draft.json` does
  not exist.
- TN public calculator stays `unavailable_requires_legal_validation`.
- Italia 35/10/0 still returns 26 268,00 / 27 353,00 / 28 439,00 EUR
  (verified on the live dev server in screenshot 08).
- Italy DPR-12-2025 PDF first 4 bytes still `%PDF` (491 873 B,
  unchanged).
- `morocco_inheritance_mapping_draft.json` unchanged (`source_sha256
  = 41db4ab3…`).

## Browser live QA

Capture script
`scripts/capture_tunisia_official_source_restore_pass1.py`. Tailwind
CDN route-aborted (local CSS only).

Desktop (1440 × 900):
`docs/screenshots/live_qa/tunisia_official_source_restore_pass1/after/desktop/`

| # | Frame |
|---|-------|
| 01 | `/countries/tunisia/` |
| 02 | `/wizard/tn/inheritance/` |
| 03 | POST → result TN unavailable |
| 04 | `/ar/countries/tunisia/` (RTL) |
| 05 | `/ar/wizard/tn/inheritance/` (RTL) |
| 06 | AR POST → result unavailable (RTL) |
| 07 | `/countries/italy/` |
| 08 | POST IT 35/10/0 → calculated 26 268,00 / 27 353,00 / 28 439,00 EUR |

Mobile (390 × 844, 2× DPI):
`docs/screenshots/live_qa/tunisia_official_source_restore_pass1/after/mobile/`

| # | Frame |
|---|-------|
| m01 | `/countries/tunisia/` |
| m02 | `/wizard/tn/inheritance/` |
| m03 | result TN unavailable |
| m04 | `/ar/wizard/tn/inheritance/` |

Italia screenshot 08 confirms the public IT calculator is still wired
(26 268,00 / 27 353,00 / 28 439,00 EUR exactly).

## Audits + validation

| Gate | Result |
|------|--------|
| `audit_public_content_hygiene.py` | OK (0 issues, 33 pages clean) |
| `audit_public_result_messages.py` | OK (no technical strings) |
| `audit_local_css_coverage.py` | 319 / 319 covered, 0 missing, 0 critical |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |
| `pytest -q` | **1449 passed**, 1 skipped (was 1441 → +8) |
| `ruff check .` | All checks passed |
| `black --check .` | 307 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |
| `manage.py compilemessages` | No errors |

## Server live

- URL: `http://127.0.0.1:48111`
- PID: `75432`
- Stop: `Stop-Process -Id 75432 -Force` (PowerShell).

## Next step

`F-tunisia-csp-livre-ix-mapping-draft-pass1` can now be re-attempted
because the TN CSP and TN DIP source files are real and validated.
The EU 650/2012 source is still classified as `fetch_failed`
pending an EUR-Lex session-aware fetch:

1. Either implement an async-aware EUR-Lex fetcher (follow the 202
   redirect and poll the prepared URL), or
2. Manually download
   `https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:32012R0650`
   into
   `legal_data/sources/eu/official_downloaded/eu-regulation-650-2012-successions.pdf`,
   then run
   `manage.py sync_official_sources --slug eu-regulation-650-2012-successions`
   followed by
   `manage.py validate_official_legal_sources --commit --slug eu-regulation-650-2012-successions`.

Until the EU 650 source is real, the Tunisia mapping draft must stay
on the **CSP only**: cross-border (Reg. 650/2012) coordination must
be referenced as a `context_source` with classification `blocked`,
not as an active rule input.
