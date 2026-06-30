# Validated legal tables — extraction destination

_Phase P50, Fase D. This is where a **validated** official table lands once a
legal reviewer has signed off. Layout:_

```
apps/calculators/data/legal_tables/<country>/<category>/<version>.json
```

**There are no data files here yet — and that is correct.** No official source has
reached `ready_for_engine` (see `docs/legal_validation/`). A file appears here
**only** after a legal reviewer validates the table and provides a worked canary.
Nothing in this tree is invented.

## Extraction pipeline (how a file gets here)
1. **PDF text extraction** (machine-readable PDF) — primary.
2. **Table extraction** (structured tables in the PDF).
3. **HTML table scraping** (official page) — when no PDF.
4. **OCR** — *fallback only*, for scanned images (e.g. the MA Dahir), documented
   and flagged `extraction_method: "ocr"` with lowered `extraction_quality`.
5. **Normalised JSON** — the shape below, **after legal validation**.

## Required JSON shape (`_schema.json`)
Every file MUST carry full provenance and a canary, and is **ignored by the
engine** unless `validation_status == "ready_for_engine"`:

```json
{
  "source_id": "tn-cga-titre-v-2024",
  "authority": "Comité Général des Assurances (CGA)",
  "url": "https://www.cga.gov.tn/...",
  "fetched_at": "2026-06-30T00:00:00Z",
  "version_date": "YYYY-MM-DD",
  "extraction_method": "pdf_table | html_table | ocr | manual_transcription",
  "hash": "sha256:...",
  "fields": ["age", "incapacity_pct", "coefficient"],
  "rows": [],
  "validation_status": "needs_legal_review",
  "canaries": [],
  "notes": "..."
}
```

- `rows` and `canaries` stay **empty** until the legal reviewer fills verbatim
  values; an engine must refuse to load a file whose `validation_status` is not
  `ready_for_engine` and whose `canaries` is empty.
- Heavy source PDFs are **not** stored here (gitignored `media/legal_harvest/` /
  `legal_data/sources/`); only the small normalised JSON + its hash live here.
