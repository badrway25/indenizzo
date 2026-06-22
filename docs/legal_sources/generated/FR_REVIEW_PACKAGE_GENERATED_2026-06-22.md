# FR — Legal review package (generated, read-only)

> Regenerable snapshot from `python manage.py generate_legal_review_package --country FR --format markdown`. It merges the live `LegalSource` state with the registry ingest policy. It **approves nothing** — it lists what the Studio must decide. See the hand-written `FRANCE_LEGAL_REVIEW_PACKAGE.md` for the detailed analysis and `MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md` for the attach procedure.

**Summary:** sources=5 · approved=1 · calculation_ready=0 · needs_review=4

Cardinal rule: a source may feed a public calculation **only** when it is `approved` AND backs an `approved` dataset/formula. Authenticating a document is necessary but not sufficient. *Meglio nessun calcolo che un calcolo falso.*

## Sources requiring Studio review

### `fr-bareme-capitalisation-gazette-palais-2022`

- **Title:** Barème de capitalisation Gazette du Palais 2022
- **Type / status / reliability:** court_table / needs_review / high
- **Official URL:** https://www.labase-lextenso.fr/sites/lextenso/files/lextenso_upload/gpl441x1.pdf
- **Dates:** pub=— eff=— until=—
- **Attachments:** 1 (hashed=1) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `fr-bareme-capitalisation-gazette-palais-2025-page`

- **Title:** Barème de capitalisation Gazette du Palais 2025 — page officielle
- **Type / status / reliability:** court_table / needs_review / high
- **Official URL:** https://lp.gazette-du-palais.fr/bareme-de-capitalisation
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `fr-nomenclature-dintilhac-2005`

- **Title:** Rapport Dintilhac — nomenclature des préjudices corporels
- **Type / status / reliability:** doctrine / needs_review / official
- **Official URL:** https://www.justice.gouv.fr/documentation/ressources/elaboration-dune-nomenclature-prejudices-corporels
- **Dates:** pub=— eff=— until=—
- **Attachments:** 0 (hashed=0) · versions=0
- **Registry policy:** _not in official_source_registry.json_
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

### `fr-referentiel-mornet-2024`

- **Title:** Référentiel Mornet 2024 — indemnisation des préjudices corporels
- **Type / status / reliability:** court_table / needs_review / high
- **Official URL:** https://www.hello-victimes.fr/app/download/8580040963/R%C3%A9f%C3%A9rentiel%2BMORNET%2B2024%2Bpdf.pdf?t=1759423951
- **Dates:** pub=— eff=— until=—
- **Attachments:** 1 (hashed=1) · versions=0
- **Registry policy:** kind=private_bareme · auto_ingest=False · human_exception_review=True · ingest_mode=human_exception_only · manual_attach_allowed=None
- **Why human review:** Barème privato non ufficiale. Anche se PDF scaricabile, l'uso come fonte di calcolo richiede review giuridica esplicita Studio.
- **Studio decisions to record:**
  - [ ] Document is the authentic official text
  - [ ] SHA-256 matches the official download
  - [ ] Required content markers present
  - [ ] Whether it needs legal interpretation / mapping
  - [ ] Verdict: approve / reject (with signature)

