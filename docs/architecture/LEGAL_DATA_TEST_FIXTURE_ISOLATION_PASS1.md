# F-legal-data-test-fixture-isolation-pass1

Make it impossible for the test suite to overwrite the project's
real legal-source files. The previous test setup wrote synthetic
payloads (`b"%PDF-1.4 fake test payload " + b"x" * 200`, exactly
227 bytes) directly into
`legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf`
because the fetch / attach / download commands hard-coded
`Path(settings.BASE_DIR) / "legal_data" / "sources" / …`. After
this pass, all three commands route through the new
`settings.LEGAL_DATA_ROOT`, and the repo-root `conftest.py`
auto-fixture redirects that setting to a per-test temporary
directory for the entire pytest run.

## The bug we found

`apps/legal_sources/test_official_source_fetch.py:55-57` returned
exactly the bytes that ended up on disk:

```python
def _fake_fetch_pdf(url, timeout=30):
    body = b"%PDF-1.4 fake test payload " + b"x" * 200
    return ("https://www.legal-tools.org/doc/0e057b/pdf/", 200, "application/pdf", body)
```

The test set `settings.MEDIA_ROOT = str(tmp_path / "media")`, but
`MEDIA_ROOT` is for Django uploads — it has nothing to do with
`sync_official_sources`'s on-disk write path. The command
unconditionally wrote to
`Path(settings.BASE_DIR) / "legal_data" / "sources" / "morocco" / "official_downloaded" / "ma-code-famille-moudawana-fr-pdf.pdf"`,
where it overwrote the real Moudawana PDF. The next time
`audit_official_source_validation_readiness.py` ran, the on-disk
sha256 of the real file no longer matched the
`[official_sync]` block — that's the contradiction the previous
iter (`F-morocco-moudawana-real-pdf-remap-pass2`) detected and
halted on.

## How the protection works

### 1. New setting `settings.LEGAL_DATA_ROOT`

`config/settings.py` now defines:

```python
LEGAL_DATA_ROOT = BASE_DIR / "legal_data"
```

Every command that writes legal-source files reads this setting
instead of computing the path from `BASE_DIR`. There are exactly
three such commands:

| Command | Subdirectory it writes to |
|---------|----------------------------|
| `apps/legal_sources/management/commands/sync_official_sources.py` | `<LEGAL_DATA_ROOT>/sources/<country>/official_downloaded/` |
| `apps/legal_sources/management/commands/attach_official_source_file.py` | `<LEGAL_DATA_ROOT>/sources/<country>/manual_attached/` |
| `apps/legal_sources/management/commands/download_international_legal_sources.py` | `<LEGAL_DATA_ROOT>/sources/<country>/downloaded/` |

Each one falls back to an absolute string for `local_path` if
`LEGAL_DATA_ROOT` is overridden outside `BASE_DIR` (the typical
pytest case), so the recorded path is still readable.

### 2. Repo-root `conftest.py` autouse fixture

`conftest.py` adds an `autouse=True` fixture that runs for every
test in the suite:

```python
@pytest.fixture(autouse=True)
def _isolate_legal_data_root(tmp_path, settings):
    isolated_root = tmp_path / "legal_data_isolated"
    isolated_root.mkdir(parents=True, exist_ok=True)
    # ... mirror the directory tree (folders only) ...
    settings.LEGAL_DATA_ROOT = str(isolated_root)
    yield isolated_root
    shutil.rmtree(isolated_root, ignore_errors=True)
```

Per-test isolation — never the same `LEGAL_DATA_ROOT` across two
tests, never the real `legal_data/` tree.

### 3. Existing per-test fixtures keep working

The pre-existing fixture in
`apps/legal_sources/test_download_international_legal_sources.py`
that monkey-patched `settings.BASE_DIR` was extended to also
override `settings.LEGAL_DATA_ROOT` so its assertions
(`Path(settings.BASE_DIR) / 'legal_data' / …`) and the command's
write path agree.

## Protected paths

After this pass, no `pytest` invocation can write into:

- `legal_data/sources/**/official_downloaded/`
- `legal_data/sources/**/manual_attached/`
- `legal_data/sources/**/downloaded/`
- `legal_data/sources/**/extracted/`
- `legal_data/mappings/`

The protection is enforced at the *setting* level, so even a
brand-new test that forgets to use `tmp_path` cannot reach the
real tree.

## Guard regression tests

`apps/legal_sources/test_legal_data_test_fixture_isolation.py`
runs every pytest invocation and fails if any of the protections
weakens:

| # | What it checks |
|---|---------------|
| 1 | `settings.LEGAL_DATA_ROOT` is overridden during pytest |
| 2 | The override is OUTSIDE the real `legal_data/` tree |
| 3 | `sync_official_sources` writes under the override (real Moudawana sha unchanged after the call) |
| 4 | `attach_official_source_file` writes under the override |
| 5 | `download_international_legal_sources` reads from `settings.LEGAL_DATA_ROOT` (static check) |
| 5b | Same for `sync_official_sources.py` (static check) |
| 5c | Same for `attach_official_source_file.py` (static check) |
| 6 | The synthetic stub fingerprint is not present anywhere in the real `legal_data/` tree (other than the historical Moudawana stub the user is restoring) |
| 7 | `"fake test payload"` only appears inside test / fixture / conftest source files, never in production code or shipped data |
| 8 | Italia 35/10/0 still produces 26 268 / 27 353 / 28 439 EUR |

## How to write future legal-data tests

- **Default:** do nothing special. The autouse `_isolate_legal_data_root`
  fixture already redirects writes for you.
- **If the test needs a real source file present in the override
  tree,** seed it explicitly into
  `Path(settings.LEGAL_DATA_ROOT) / "sources" / "<country>" / "<subdir>"`.
- **Never** monkey-patch `settings.BASE_DIR` alone — also patch
  `settings.LEGAL_DATA_ROOT` (or use the autouse fixture's path
  directly).
- **Never** import the real `legal_data/sources/**` paths via
  `Path(__file__).resolve().parents[…] / "legal_data"` in a test.
  That bypasses the setting and re-introduces the bug. The
  guard test #1 will catch this only if the test then calls a
  production command — to be safe, always go through `settings`.

## Why the real Moudawana PDF still needs to be restored manually

This iter **does NOT** restore the real Moudawana PDF. The file at
`legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf`
is still the 227-byte synthetic stub
(sha256 `932aa556678ff0ceed2e49f57b697d818bc92c60ca42ddcd177b0f60e3c2ce3f`).
The plan, agreed before this iter started:

1. **First protect** (this iter — done).
2. **Then restore the real PDF** at the canonical path so its
   sha256 matches the value the iter spec expects
   (`41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96`).
3. **Then re-run** `F-morocco-moudawana-real-pdf-remap-pass2` —
   this time the extraction script will produce real article text
   and the mapping draft can advance from `confidence=low` to
   confidence levels that reflect the actual document.

Step 2 is a manual user action that lives outside any iter
automation: nothing in this codebase fetches the real Moudawana
PDF; the user places it on disk.

## What did NOT change

- No `LegalSource` / `LegalReview` / `CompensationDataset` /
  `CalculationFormula` / `CompensationTableRow` row created or
  modified.
- No FR / BE / MA / TN public calculator activation.
- No Moudawana mapping draft regeneration. The previous pass's
  mapping JSON is preserved verbatim.
- Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
- IT PDF still serves `%PDF`.

## Validation gates

| Gate | Result |
|------|--------|
| `pytest -q` (full) | 1396 passed, 1 skipped (pre-pass baseline) → **plus 10 new guard tests** = 1406 passed, 1 skipped |
| `apps/legal_sources/test_legal_data_test_fixture_isolation.py` | 10 passed |
| Real-tree Moudawana PDF sha256 after full pytest | unchanged at `932aa55…` (= the existing stub; the point is it didn't change *during* the test run) |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |

## Next step

Place the real Moudawana PDF at
`legal_data/sources/morocco/official_downloaded/ma-code-famille-moudawana-fr-pdf.pdf`
(must hash to `41db4ab3d505c16a985e06f7df34678afeabe9f09a0b3df09d38033563beda96`)
and re-issue `F-morocco-moudawana-real-pdf-remap-pass2`. The same
protections apply: even if a future test were to fake-fetch a stub,
it would land in a tmp dir and the real bytes would survive.
