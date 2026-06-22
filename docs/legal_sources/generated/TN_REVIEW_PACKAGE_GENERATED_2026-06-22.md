# TN — Legal review package (generated, read-only)

> Regenerable snapshot from `python manage.py generate_legal_review_package --country TN --format markdown`. It merges the live `LegalSource` state with the registry ingest policy. It **approves nothing** — it lists what the Studio must decide. See the hand-written `TUNISIA_LEGAL_REVIEW_PACKAGE.md` for the detailed analysis and `MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md` for the attach procedure.

**Summary:** sources=11 · approved=2 · calculation_ready=0 · needs_review=9

Cardinal rule: a source may feed a public calculation **only** when it is `approved` AND backs an `approved` dataset/formula. Authenticating a document is necessary but not sufficient. *Meglio nessun calcolo che un calcolo falso.*

## Sources requiring Studio review

### `eu-regulation-650-2012-successions-fr-tn`

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

### `tn-code-statut-personnel-compiled`

- **Title:** Code du statut personnel tunisien — version compilée
- **Type / status / reliability:** official_law / needs_review / high
- **Official URL:** https://jafbase.fr/docMaghreb/TunisieStatutpersonnel.PDF
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `tn-code-statut-personnel-livre-ix-art-113-121`

- **Title:** Code du statut personnel — Livre IX «De la succession» — Fardh — articles 113-121
- **Type / status / reliability:** official_law / needs_review / official
- **Official URL:** https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1095.htm
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** kind=official_law · auto_ingest=True · human_exception_review=False · ingest_mode=fetch · manual_attach_allowed=None
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `tn-code-statut-personnel-livre-ix-art-144-146`

- **Title:** Code du statut personnel — Livre IX «De la succession» — Asaba (résiduaires) — articles 144-146
- **Type / status / reliability:** official_law / needs_review / official
- **Official URL:** https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1105.htm
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** kind=official_law · auto_ingest=True · human_exception_review=False · ingest_mode=fetch · manual_attach_allowed=None
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `tn-code-statut-personnel-livre-ix-art-147-152`

- **Title:** Code du statut personnel — Livre IX «De la succession» — Asaba + Radd + clôture — articles 147-152
- **Type / status / reliability:** official_law / needs_review / official
- **Official URL:** https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1110.htm
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** kind=official_law · auto_ingest=True · human_exception_review=False · ingest_mode=fetch · manual_attach_allowed=None
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `tn-code-statut-personnel-livre-ix-art-89-90`

- **Title:** Code du statut personnel — Livre IX «De la succession» — «Des successibles» — articles 89-90
- **Type / status / reliability:** official_law / needs_review / official
- **Official URL:** https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1080.htm
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** kind=official_law · auto_ingest=True · human_exception_review=False · ingest_mode=fetch · manual_attach_allowed=None
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `tn-code-statut-personnel-livre-ix-art-91-98`

- **Title:** Code du statut personnel — Livre IX «De la succession» — Successibles — articles 91-98
- **Type / status / reliability:** official_law / needs_review / official
- **Official URL:** https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1085.htm
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** kind=official_law · auto_ingest=True · human_exception_review=False · ingest_mode=fetch · manual_attach_allowed=None
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `tn-code-statut-personnel-livre-ix-art-99-110`

- **Title:** Code du statut personnel — Livre IX «De la succession» — Successibles + Fardh — articles 99-110
- **Type / status / reliability:** official_law / needs_review / official
- **Official URL:** https://www.jurisitetunisie.com/tunisie/codes/csp/Csp1090.htm
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** kind=official_law · auto_ingest=True · human_exception_review=False · ingest_mode=fetch · manual_attach_allowed=None
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `tn-jort-code-statut-personnel-1956`

- **Title:** JORT 1956 — Code du statut personnel tunisien
- **Type / status / reliability:** official_law / needs_review / official
- **Official URL:** https://www.pist.tn/jort/1956/1956F/Jo10456.pdf
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

