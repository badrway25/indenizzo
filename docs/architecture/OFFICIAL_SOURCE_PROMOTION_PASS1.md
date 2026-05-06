# F-legal-sources-approved-status-promotion-pass1

Promote the six official `LegalSource` rows that
`F-legal-sources-official-validation-pass1` validated to
`status=APPROVED`, creating real `LegalReview` rows attached to an
existing staff reviewer. This pass is the bridge from "official
provenance verified" to "approved by Studio" — but does NOT cross
the line into calculator activation.

## Sources promoted in the dev DB

| Country | Slug | Reviewer | Decision | Previous → New |
|---------|------|----------|----------|----------------|
| EU | `eu-regulation-650-2012-successions`            | `badr` | approve | needs_review → **approved** |
| MA | `ma-code-famille-moudawana-fr-pdf`              | `badr` | approve | needs_review → **approved** |
| TN | `tn-code-statut-personnel-livre-ix-succession`  | `badr` | approve | needs_review → **approved** |
| TN | `tn-code-dip-loi-98-97`                         | `badr` | approve | needs_review → **approved** |
| BE | `be-loi-1989-11-21-rc-auto`                     | `badr` | approve | needs_review → **approved** |
| FR | `fr-loi-badinter-1985`                          | `badr` | approve | needs_review → **approved** |

The IT decree (`it-dpr-12-2025-tun-danno-biologico`) was already
approved before this pass and is correctly recognised as
`already_approved` (no duplicate review row created).

### LegalReview rows

- Before: 2 (both for IT, historical)
- After: 8 (2 historical IT + 6 new from this pass)
- Reviewer: `badr` (existing staff superuser; not a fake user)

### LegalSource counts

- Before: 1 approved / 24 needs_review
- After: **7 approved** / 18 needs_review

## What this pass added

- **`apps/legal_sources/management/commands/promote_official_legal_sources.py`**
  — new management command. Required flags:
    - `--reviewer-username <username>` (the user must already exist
      and be `is_staff=True` and `is_active=True`; the command
      never creates users).
    - `--commit` (without it, the command runs as dry-run).
    - `--slug <slug>` (optional, restricts to a single source).
- **`apps/legal_sources/test_official_source_promotion_pass1.py`**
  — 15 tests covering reviewer gates, allow-list / deny-list
  handling, idempotency, no compensation-layer side effects, and
  the FR/BE/MA/TN unavailable invariant.
- **`scripts/capture_official_source_promotion_pass1.py`** —
  Playwright capture (16 desktop + 5 mobile + 3 RTL/locale frames).

## Three independent gates per source

1. **Allow-list** — `PROMOTABLE_SLUGS` carries exactly the seven
   slugs that may transition to APPROVED via this command. Mornet,
   Gazette du Palais, Tableau Indicatif, Schryvers, Dintilhac, Code
   droits réels, Italian Dlgs/MIMIT/Milano, etc. are all explicitly
   excluded.
2. **Deny-list** — `DENY_LIST_SLUGS` is a hard refusal even if a
   future iter were to add one of those slugs to the allow-list by
   mistake (private barème / court-indicative table / mirror
   copies).
3. **Validation block** — the source must carry an
   `[official_source_validation]` JSON block whose
   `validation_status == "passed"`,
   `official_source_verified == True`, and
   `sha256_verified == True`. If the validate command was not run
   first, the promote command refuses with a clear error message.

## What did NOT change

- No `CompensationDataset` row created or promoted.
- No `CalculationFormula` row created.
- No `CompensationTableRow` row created or modified.
- No FR / BE / MA / TN public calculator activation (verified by
  `audit_product_release_readiness.py` — `unavailable_pass=4/4`).
- No fake `LegalReview` row (the command never creates a user).
- No deny-listed slug promoted.
- No DRAFT compensation dataset promoted.
- No `formula.parameters` mutation.
- Italia 35/10/0 → 26 268 / 27 353 / 28 439 EUR remains.
- IT PDF still serves `%PDF`.

## Browser visual QA

Capture script:
`scripts/capture_official_source_promotion_pass1.py`. Tailwind CDN
is route-aborted to enforce the local-CSS-only baseline.

Screenshots:
`docs/screenshots/live_qa/official_source_promotion_pass1/after/`

- **Desktop (16):** `/countries/`, every country landing
  (IT/FR/BE/MA/TN), every wizard form, IT calculated result,
  and FR/BE/MA/TN unavailable result.
- **Mobile (5):** Morocco landing, IT + MA wizards, IT calculated,
  MA unavailable.
- **RTL/locale (3):** AR Morocco landing, AR Morocco wizard,
  AR Morocco unavailable result.

### Visual notes

- Country landings still carry the right status panel:
  IT shows the OK "Calcolo indicativo disponibile" badge,
  FR/BE/MA/TN keep the gold/sand "Valutazione legale preliminare"
  / "International inheritance review" badge — the source-level
  status promotion did not silently flip any country to "active".
- Wizards show the same form layouts; FR/BE/MA/TN preserve the
  preliminary-assessment banner.
- Result pages: IT renders the calculated range
  (`26268,00 / 27353,00 / 28439,00 EUR`); FR/BE/MA/TN render the
  unavailable card with no EUR amounts.
- AR/RTL surfaces unchanged; Amiri/Tajawal pairing intact.

## Audits ran for this pass

| Audit | Result |
|-------|--------|
| `audit_public_content_hygiene.py` | OK (0 pages with issues) |
| `audit_public_result_messages.py` | OK (no technical strings) |
| `audit_calculator_diagnostic_strings.py` | only `formula_engine_unknown` slug remains (intentional) |
| `audit_local_css_coverage.py` | 318 / 322 covered, 0 critical |
| `audit_product_release_readiness.py` | OK (`it_baseline=OK`, FR/BE/MA/TN 4/4 unavailable, counts unchanged) |
| `audit_official_source_validation_readiness.py` | 1 VALIDATED + 6 OFFICIAL_BUT_NOT_CALCULATION_READY + 18 NEEDS_REVIEW (file-state buckets unchanged — promotion lifted source status only) |
| `run_public_lighthouse_audit.py --mode=playwright` | every URL passes |

## Validation gates

| Gate | Result |
|------|--------|
| `pytest -q` | 1383 passed, 1 skipped |
| `ruff check .` | All checks passed |
| `black --check .` | 294 files unchanged |
| `manage.py check` | No issues |
| `manage.py makemigrations --check` | No changes |
| `manage.py compilemessages` | No errors |

## Server live

- URL: `http://127.0.0.1:48107`
- PID: `61116`
- Stop: `Stop-Process -Id 61116 -Force` (PowerShell).

## Next step

The seven sources are now `APPROVED`. The remaining gates before
FR / BE / MA / TN calculator activation are:

- **MA inheritance:** map Moudawana Livre III → CompensationDataset
  + CalculationFormula + row matrix; same for the EU 650/2012
  applicable-law decision.
- **TN inheritance:** map CSP livre IX + DIP loi 98-97 + EU 650
  → dataset + formula.
- **FR road accident:** map an *official* indemnity table (the
  current Mornet / Gazette / Dintilhac sources are non-official
  and remain `NEEDS_REVIEW_NON_OFFICIAL`); Loi Badinter alone is
  primary law and does not carry the amount table.
- **BE road accident:** map an *official* indemnity table; the
  current Tableau Indicatif / Schryvers sources remain
  `NEEDS_REVIEW_NON_OFFICIAL`. Loi 1989 is primary law only.

Each of those is a separate iter — none of them is in scope here.
