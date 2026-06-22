# MA — Legal review package (generated, read-only)

> Regenerable snapshot from `python manage.py generate_legal_review_package --country MA --format markdown`. It merges the live `LegalSource` state with the registry ingest policy. It **approves nothing** — it lists what the Studio must decide. See the hand-written `MOROCCO_LEGAL_REVIEW_PACKAGE.md` for the detailed analysis and `MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md` for the attach procedure.

**Summary:** sources=4 · approved=1 · calculation_ready=0 · needs_review=3

Cardinal rule: a source may feed a public calculation **only** when it is `approved` AND backs an `approved` dataset/formula. Authenticating a document is necessary but not sufficient. *Meglio nessun calcolo che un calcolo falso.*

## Sources requiring Studio review

### `eu-regulation-650-2012-successions-fr-ma`

- **Title:** Règlement UE n°650/2012 — successions transfrontalières
- **Type / status / reliability:** official_law / needs_review / official
- **Official URL:** https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32012R0650
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `ma-code-droits-reels-loi-39-08`

- **Title:** Loi n°39-08 relative au Code des droits réels
- **Type / status / reliability:** official_law / needs_review / high
- **Official URL:** https://faolex.fao.org/docs/pdf/mor225024.pdf
- **Dates:** pub=— eff=— until=—
- **Attachments:** 1 (hashed=1) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `ma-code-droits-reels-traduction-aute`

- **Title:** Loi n°39-08 Code des droits réels — traduction
- **Type / status / reliability:** official_law / needs_review / medium
- **Official URL:** https://aute.gov.ma/s/a/library/2023-11-01/146a1724-a0bf-40ed-9169-973ffda26975.pdf
- **Dates:** pub=— eff=— until=—
- **Attachments:** 1 (hashed=1) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

