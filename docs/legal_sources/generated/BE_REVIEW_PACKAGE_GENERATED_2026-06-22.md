# BE — Legal review package (generated, read-only)

> Regenerable snapshot from `python manage.py generate_legal_review_package --country BE --format markdown`. It merges the live `LegalSource` state with the registry ingest policy. It **approves nothing** — it lists what the Studio must decide. See the hand-written `BELGIUM_LEGAL_REVIEW_PACKAGE.md` for the detailed analysis and `MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md` for the attach procedure.

**Summary:** sources=5 · approved=1 · calculation_ready=0 · needs_review=4

Cardinal rule: a source may feed a public calculation **only** when it is `approved` AND backs an `approved` dataset/formula. Authenticating a document is necessary but not sufficient. *Meglio nessun calcolo che un calcolo falso.*

## Sources requiring Studio review

### `be-tableau-indicatif-2020`

- **Title:** Tableau Indicatif 2020 — dommages corporels
- **Type / status / reliability:** court_table / needs_review / high
- **Official URL:** https://docs.fcgb-bgwf.be/documents/Tabl_Ind_2020_Fr.pdf
- **Dates:** pub=— eff=— until=—
- **Attachments:** 1 (hashed=1) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `be-tableau-indicatif-2024`

- **Title:** Tableau Indicatif 2024 — dommages corporels
- **Type / status / reliability:** court_table / needs_review / high
- **Official URL:** https://docs.fcgb-bgwf.be/documents/Tabl_Ind_2024_Fr.pdf
- **Dates:** pub=— eff=— until=—
- **Attachments:** 1 (hashed=1) · versions=0
- **Registry policy:** kind=court_indicative_table · auto_ingest=False · human_exception_review=True · ingest_mode=human_exception_only · manual_attach_allowed=None
- **Why human review:** Tabella indicativa giurisprudenziale (Magistrats / Avocats), non normativa primaria. Inoltre PDF image-scanned: richiede OCR e validazione Studio per uso in calcolatore.
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `be-tables-schryvers-2026-page`

- **Title:** Tables Schryvers — tables de mortalité et de capitalisation prospectives belges
- **Type / status / reliability:** court_table / needs_review / high
- **Official URL:** https://www.tafelsschryvers.be/?lang=fr
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `be-tables-schryvers-tableurs`

- **Title:** Tables Schryvers — tableurs
- **Type / status / reliability:** court_table / needs_review / high
- **Official URL:** https://www.tafelsschryvers.be/tableurs/?lang=fr
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

