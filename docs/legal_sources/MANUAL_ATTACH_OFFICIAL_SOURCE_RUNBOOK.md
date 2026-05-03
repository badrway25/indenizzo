# Manual Attach — Official Source Runbook

**Iter:** F-official-source-manual-attach-pipeline.

**Audience:** Studio Legale operators (or staff with shell access to the server) who need to register an officially-sourced document that the auto-fetch pipeline (`sync_official_sources`) cannot retrieve due to technical blocks: HTTP 403 (Légifrance), JS-only SPAs (some `gazzettaufficiale.it` endpoints), anti-bot WAFs (Cloudflare aggressive challenge), TLS strictness, paywalls.

The pipeline never replaces legal review. It only records that **a specific file was attached, by whom, with this checksum, on this date** so the report layer can cite the file alongside its sha256.

---

## When to use it

| Situation | Tool |
|-----------|------|
| Public URL returns 200 with the legal text | `sync_official_sources` (auto-fetch) |
| Public URL returns 403 / 401 / 5xx to programmatic clients | **manual attach** |
| Public URL serves a JS-only SPA shell, content not in raw HTML | manual attach (fetch with `pdfplumber` fallback can sometimes succeed; if not, manual attach) |
| File is a private/court bareme requiring legal review before any use | neither — handle as `human_exception_only` and discuss in legal review package |

The registry entry must declare `manual_attach_allowed: true` *and* provide a `content_must_contain` list. The command rejects any slug that doesn't.

---

## What the command does

```text
python manage.py attach_official_source_file --slug <slug> --file <path>
```

1. **Reads** `config/official_source_registry.json`, validates the entry, requires `manual_attach_allowed=true`.
2. **Reads** the supplied file's bytes (rejects empty files).
3. **Computes** `sha256` and `size_bytes`.
4. **Marker check** (case-insensitive `any-of`):
   - HTML / text → search raw bytes for any of `content_must_contain`.
   - PDF (magic `%PDF-`) → first raw bytes; if none match, falls back to `pdfplumber` text extraction (first 16 pages).
   - Failure → `CommandError`. **No** file copy, **no** notes write, **no** manifest update.
5. **Copies** the file into `legal_data/sources/<country>/manual_attached/<slug>.<ext>`.
6. **Writes/updates** a per-country cumulative manifest at `legal_data/sources/<country>/manual_attached/manual_attach_manifest.json` (idempotent: a re-run for the same slug replaces the prior entry).
7. **Annotates** `LegalSource.notes` with a `[manual_attach] BEGIN…END` JSON trailer that **coexists** with any existing `[official_sync]` block (the auto-fetch pipeline's trailer is preserved verbatim).

What the command **never** does:

- Never creates `LegalReview`.
- Never creates `CompensationDataset` / `CalculationFormula` / `CompensationTableRow`.
- Never promotes `LegalSource.status` to `APPROVED`. New `LegalSource` rows are inserted as `NEEDS_REVIEW` only.
- Never extends the `SourceStatus` enum.
- Never alters Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR.

---

## Difference vs `LegalReview`

| | Manual attach | Legal review |
|---|---|---|
| What it records | "this file has this checksum and was filed today" | "this source has been read and validated by a lawyer for this calculator scope" |
| Who runs it | Studio operator (any staff with shell access) | Studio legal reviewer |
| Effect on calculator | None — calculator stays `unavailable_requires_legal_validation` if it was | Required step before promoting `LegalSource.status` to `APPROVED` and unlocking calculator |
| Effect on `LegalSource.status` | None | The reviewer may set it to `APPROVED` (separate workflow) |
| Where the trace lives | `[manual_attach]` block in `LegalSource.notes` + per-country manifest | `LegalReview` rows + `LegalSource.legal_reviewer` FK |

Manual attach is **not** a substitute for legal review. It's the file-level integrity layer. Legal review is the semantic-level approval layer. Both are required before any calculator can use the source operationally.

---

## Example — FR Loi Badinter

The Loi du 5 juillet 1985 ("Loi Badinter") is the cornerstone of FR road accident indemnisation, but Légifrance returns HTTP 403 to programmatic clients. Studio downloads the consolidated PDF/HTML manually from Légifrance, then:

```powershell
# Activate venv (if not already active)
.\.venv\Scripts\Activate.ps1

# Attach the file Studio just downloaded
python manage.py attach_official_source_file `
    --slug fr-loi-badinter-1985 `
    --file C:\Users\studio\Downloads\loi-badinter-consolidee-2025.pdf
```

Expected output:

```text
  [  OK] fr-loi-badinter-1985  sha256=abcdef012345 size=NNNNNN B -> legal_data\sources\france\manual_attached\fr-loi-badinter-1985.pdf
  manifest -> C:\Dev\badrane-indennizzo\legal_data\sources\france\manual_attached\manual_attach_manifest.json
```

After the run:

- `LegalSource(slug='fr-loi-badinter-1985')` stays `needs_review` (or is created with `needs_review` if it didn't exist).
- `legal_data/sources/france/manual_attached/fr-loi-badinter-1985.pdf` is the byte-for-byte copy of the supplied file.
- `LegalSource.notes` carries a `[manual_attach]` trailer with `sha256`, `size_bytes`, `local_path`, `marker_check_passed=true`, `classification=manual_attach_success`, `no_calculator_activation=true`, `no_dataset_creation=true`.
- `manual_attach_manifest.json` lists this run with timestamp + sha256.

---

## Failure modes

### Marker check failed

```text
CommandError: manual_attach_marker_failed: missing required content markers ['5 juillet 1985', 'accidents de la circulation', 'indemnisation', 'victimes'] in wrong-document.pdf
```

Cause: the supplied file does not contain *any* of the four FR markers, neither in raw bytes nor in `pdfplumber`-extracted text. Likely the operator picked the wrong file (e.g. an unrelated decree, a cookie/banner page, an empty download).

Recovery: verify the file is the right Légifrance export, then re-run.

### `manual_attach_allowed` not set

```text
CommandError: slug 'fr-loi-badinter-1985' does not allow manual_attach (set 'manual_attach_allowed': true in the registry)
```

Cause: the registry entry doesn't opt in. This is intentional — manual attach must be explicitly authorized per slug, not enabled by default.

Recovery: edit `config/official_source_registry.json`, set `"manual_attach_allowed": true` and provide a `content_must_contain` list, then re-run. A registry edit is a code change and should go through review.

### Empty / missing file

```text
CommandError: File not found: <path>
CommandError: File is empty: <path>
```

Cause: the supplied path is wrong, or the download was truncated.

Recovery: re-download.

---

## What this still leaves to do for FR engine activation

The manual attach gives Studio the cited file with checksum. To actually run a calculation for FR road accident, the following separate steps are still required:

1. **Legal review** of Loi Badinter scope by Studio reviewer → set `LegalSource.status = APPROVED`.
2. **Quantification source** (Référentiel Mornet 2024 or jurisprudence-derived bareme) — currently `private_bareme` / `human_exception_only` in the registry. Studio must validate explicitly.
3. **CompensationDataset + CalculationFormula** matching the validated bareme (separate import pipeline, not part of manual attach).
4. **`apps/calculators/engines/france.py`** with deterministic mapping victim_age × disability % × case category → amount (currently absent — `run_simulation` returns `unavailable_requires_legal_validation` for FR by default).

Manual attach is step 0 of this chain: it gives a hash-verified, dated copy of the source. Steps 1-4 remain Studio responsibility.

---

## Re-run / idempotency

A second run for the same slug replaces both the on-disk file and the `[manual_attach]` block in `LegalSource.notes` (no duplication). The manifest entry for that slug is also replaced (one entry per slug, latest run wins). The `[official_sync]` block, if present, is preserved.

This is intentional: when Studio gets a new consolidated version of the same law, the right action is to overwrite, not to accumulate.

---

## Cross-references

- Auto-fetch pipeline: `apps/legal_sources/management/commands/sync_official_sources.py`
- Per-country status: `docs/architecture/OFFICIAL_SOURCE_AUTOMATION_STATUS.md`
- Legal review packages: `docs/legal_sources/{FRANCE,BELGIUM,MOROCCO,TUNISIA}_LEGAL_REVIEW_PACKAGE.md`
