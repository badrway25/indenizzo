# F-legal-sources-official-validation-pass1

Validate every `LegalSource` whose `notes` already carry a known
provenance block (`[official_sync]` `fetch_success` /
`crosscheck_success`, or `[manual_attach]` `manual_attach_success`)
and bucket all 25 rows into the four categories the iter requires:

1. **VALIDATED_OFFICIAL_SOURCE** — provenance verified, calculator
   actually active.
2. **OFFICIAL_BUT_NOT_CALCULATION_READY** — provenance verified,
   calculator activation gated on mapping work that this iter does
   not do.
3. **NEEDS_REVIEW_NON_OFFICIAL** — `private_bareme` /
   `court_indicative_table` / mirror without validation / OCR-
   incomplete scan / no provenance block at all.
4. **DATASET_APPROVAL_BLOCKED** — DRAFT FR / BE compensation
   datasets rooted on a non-official source whose validation has
   not yet completed.

No fake `LegalReview` row is created. No `LegalSource.status`
change. No FR / BE / MA / TN calculator activation. No
`CompensationDataset` / `CalculationFormula` /
`CompensationTableRow` write. Italia 35/10/0 still produces
26 268 / 27 353 / 28 439 EUR; the IT PDF still serves `%PDF`.

## Results — current bucket counts

```
VALIDATED_OFFICIAL_SOURCE          : 1   (it-dpr-12-2025-tun-danno-biologico — already approved)
OFFICIAL_BUT_NOT_CALCULATION_READY : 6
NEEDS_REVIEW_NON_OFFICIAL          : 18
DATASET_APPROVAL_BLOCKED           : 0   (no FR/BE DRAFT datasets present in the live DB at audit time)
```

### Validated official sources (provenance verified)

| Slug | Country | File | Verdict | Calculator activation |
|------|---------|------|---------|------------------------|
| `it-dpr-12-2025-tun-danno-biologico`            | IT | `legal_data/sources/italy/official_downloaded/...pdf`    | passed | active (already approved before this pass) |
| `eu-regulation-650-2012-successions`            | EU | `legal_data/sources/eu/official_downloaded/...html`      | passed | not yet — EU 650/2012 is the applicable-law rule, not a calculation table |
| `ma-code-famille-moudawana-fr-pdf`              | MA | `legal_data/sources/morocco/official_downloaded/...pdf`  | passed | not yet — Moudawana Livre III mapping required |
| `tn-code-statut-personnel-livre-ix-succession`  | TN | `legal_data/sources/tunisia/official_downloaded/...html` | passed | not yet — CSP livre IX + DIP + 650 mapping required |
| `tn-code-dip-loi-98-97`                         | TN | `legal_data/sources/tunisia/official_downloaded/...html` | passed | not yet — see CSP entry |
| `be-loi-1989-11-21-rc-auto`                     | BE | `legal_data/sources/belgium/official_downloaded/...html` | passed | not yet — primary law only, no compensation table |
| `fr-loi-badinter-1985`                          | FR | `legal_data/sources/france/manual_attached/...pdf`       | passed | not yet — primary law only, no compensation table |

### Sources blocked from validation (and why)

| Slug | Source kind | Reason |
|------|-------------|--------|
| `fr-referentiel-mornet-2024` | `private_bareme` | not an official source; intrinsic block |
| `fr-bareme-capitalisation-gazette-palais-2022` | `non_official` | private bareme, not for public dataset |
| `fr-bareme-capitalisation-gazette-palais-2025-page` | `non_official` | private bareme |
| `fr-nomenclature-dintilhac-2005` | `non_official` | doctrine, not normative |
| `be-tableau-indicatif-2020` | `non_official` | court_indicative_table, not normative |
| `be-tableau-indicatif-2024` | `court_indicative_table` | OCR not clean; human exception only |
| `be-tables-schryvers-2026-page` | `non_official` | private compendium |
| `be-tables-schryvers-tableurs` | `non_official` | private spreadsheets |
| `it-dlgs-209-2005-cap-art-138-139` | (no provenance block) | seed-only; never synced or attached |
| `it-mimit-2025-07-aggiornamento-art-139` | (no provenance block) | seed-only |
| `it-mimit-2025-12-aggiornamento-macrolesioni` | (no provenance block) | seed-only |
| `it-tabelle-milano-2024` | (no provenance block) | seed-only |
| `eu-regulation-650-2012-successions-fr-ma` | (no provenance block) | seed-only mirror |
| `ma-code-droits-reels-loi-39-08` | (no provenance block) | seed-only |
| `ma-code-droits-reels-traduction-aute` | (no provenance block) | seed-only translation |
| `eu-regulation-650-2012-successions-fr-tn` | (no provenance block) | seed-only mirror |
| `tn-code-statut-personnel-compiled` | (no provenance block) | seed-only |
| `tn-jort-code-statut-personnel-1956` | (no provenance block) | seed-only |

### Dataset / formula activation NOT performed

- No `CompensationDataset.status` was promoted from DRAFT.
- No `CalculationFormula` row was created.
- No `CompensationTableRow` row was created or updated.
- No `LegalReview` row was created (no fake reviewer).

## What this pass added

- **`scripts/legal_data/audit_official_source_validation_readiness.py`**
  — read-only classifier. Outputs
  `docs/architecture/OFFICIAL_SOURCE_VALIDATION_READINESS_PASS1.md`
  + `docs/reports/legal_sources/official_source_validation_readiness.json`.
- **`apps/legal_sources/management/commands/validate_official_legal_sources.py`**
  — re-validates every source with a provenance block. Recomputes
  SHA-256, re-runs the registry marker check, and writes a single
  idempotent `[official_source_validation] BEGIN/END` block in
  `LegalSource.notes`. Two flags:
    - `--dry-run` (default if `--commit` is not given): computes
      verdicts, prints to stdout, never writes.
    - `--commit`: writes / refreshes the validation block in DB.
- **`apps/legal_sources/test_official_source_validation_pass1.py`**
  — 15 tests covering audit + command + every iter invariant.
- **`scripts/capture_official_source_validation_pass1.py`** —
  Playwright capture for the visual QA bundle (16 desktop + 5
  mobile + 3 RTL/locale screenshots).

### Validation block schema

The validate command writes a single JSON object per source:

```json
{
  "validation_status": "passed | failed | blocked",
  "validated_at": "<UTC ISO timestamp>",
  "source_slug": "...",
  "sha256": "<current sha256 of the local file>",
  "sha256_verified": true,
  "marker_check_passed": true,        // null when registry has no markers
  "file_exists": true,
  "local_path": "...",
  "size_bytes": <int>,
  "official_source_verified": true,
  "legal_calculator_activation": false,
  "dataset_activation": false,
  "candidate_for_manual_status_approval": true,
  "registry_markers": [...],
  "classification_source": "official_sync | manual_attach",
  "reason": "official source verified, calculation mapping still required",
  "no_legal_review_created": true,
  "no_status_change": true,
  "no_dataset_or_formula_write": true
}
```

`legal_calculator_activation` and `dataset_activation` are
hard-coded to `false` in this iter — they are surfaced as fields
so future iterations cannot silently flip the contract.

### Drift detection

Re-running `--commit` against an unchanged file is a no-op (the
block is replaced with an updated `validated_at` and the same
sha256). If the local bytes change after a successful validation,
the next run records `validation_status: failed` with
`reason: sha256_drift_since_last_validation` — the intended
canary against bit-rot or manual tampering.

## Browser visual QA

Capture script:
`scripts/capture_official_source_validation_pass1.py`. Tailwind
CDN is route-aborted so the rendered layout exercises only
`static/css/site.css`.

Screenshots: `docs/screenshots/live_qa/official_source_validation_pass1/after/`

- **Desktop (16):** `/countries/`, every country landing
  (IT/FR/BE/MA/TN), every wizard form (5), every result page
  (1 calculated IT + 4 unavailable FR/BE/MA/TN).
- **Mobile (5):** `/countries/`, IT + MA wizards, IT calculated
  result, MA unavailable result.
- **RTL/locale (3):** AR Morocco landing, AR Morocco wizard,
  AR Morocco unavailable result.

### Visual notes

- The country-landing pages do not promise calculations that are
  not available — IT carries the OK "Calcolo indicativo
  disponibile" badge, the other four use the gold/sand
  "Valutazione legale preliminare" / "International inheritance
  review" badge, both rendered by the centralised
  `_public_status_panel` partial.
- No misleading "validato legalmente" / "fonte ufficiale
  confermata" / "official source verified" string surfaces in any
  country / wizard / result page (verified by HTML grep).
- Layout premium intact across IT/FR/AR/EN — the previous
  pass's polish (cookie banner spacing, country hero crop,
  AR Amiri/Tajawal pairing) carries over.
- Mobile layouts stack cleanly; RTL flipped correctly with
  Amiri headings on the AR Morocco surfaces.

## Audits ran for this pass

| Audit | Result |
|-------|--------|
| `audit_public_content_hygiene.py` | OK (0 pages with issues) |
| `audit_public_result_messages.py` | OK (no technical strings) |
| `audit_calculator_diagnostic_strings.py` | only `formula_engine_unknown` slug remains (intentional) |
| `audit_local_css_coverage.py` | 318 / 322 covered, 0 critical |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |

## Validation gates

| Gate | Result |
|------|--------|
| `pytest -q` | 1368 passed, 1 skipped |
| `ruff check .` | All checks passed |
| `black --check .` | 291 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |
| `manage.py compilemessages` | No errors |

## What can be approved after this pass

A separate, signed Studio review can manually move any of the
seven validated sources to `LegalSource.status = APPROVED`:

| Slug | Calculator after promotion |
|------|----------------------------|
| `it-dpr-12-2025-tun-danno-biologico`            | already approved + active |
| `eu-regulation-650-2012-successions`            | enables applicable-law decision in MA/TN inheritance funnels — calculator activation still requires CSP / Moudawana mapping |
| `ma-code-famille-moudawana-fr-pdf`              | needed before any MA inheritance dataset can be promoted |
| `tn-code-statut-personnel-livre-ix-succession`  | needed before any TN inheritance dataset can be promoted |
| `tn-code-dip-loi-98-97`                         | needed alongside CSP livre IX + EU 650/2012 |
| `be-loi-1989-11-21-rc-auto`                     | unlocks BE primary-law citation, but BE compensation needs an official table |
| `fr-loi-badinter-1985`                          | unlocks FR primary-law citation, but FR compensation needs an official bareme |

Promotion is **out of scope** for this iter and requires a real
reviewer to set `LegalSource.legal_reviewer` + create a
`LegalReview` row.

## What did NOT change

- No DB schema migration.
- No `LegalSource.status` change.
- No `CompensationDataset` / `CalculationFormula` /
  `CompensationTableRow` row created or modified.
- No `LegalReview` row created.
- No FR / BE / MA / TN calculator activation.
- No `formula.parameters` mutation.
- Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
- IT PDF still starts with `%PDF`.

## Server live

- URL: `http://127.0.0.1:48107`
- PID: `28844`
- Stop: `Stop-Process -Id 28844 -Force` (PowerShell).

## Next step

A signed Studio review can promote the seven validated official
sources to `LegalSource.status = APPROVED` and create the
corresponding `LegalReview` rows. After that, the next blocker
for FR / BE / MA / TN calculator activation is the mapping work
(MA Moudawana Livre III, TN CSP + DIP + EU 650, FR/BE compensation
tables) that this iter does not perform.
