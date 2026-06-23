# Legal Source Studio Review — Runbook (D2)

For the Studio reviewer. How to read a source's readiness and evidence, assemble
what is missing, record a decision, and understand why FR/BE/MA/TN are not yet
calculation-ready. **Everything here is read-only or human-gated — nothing
activates a public calculation automatically.**

> *Meglio nessun calcolo che un calcolo falso.* Authenticating a document is
> necessary but not sufficient. A source feeds a public calculation **only** when
> it is APPROVED *and* backs an APPROVED dataset with a source version — today
> only Italy.

## 1. Read the readiness (what's missing, in order)

```bash
python manage.py report_legal_review_readiness --country FR --format markdown
```
Per source: status, latest review, version/attachment/hash counts, the ordered
**missing steps** and the recommended next action.

## 2. Read the evidence checklist / review-pack index

```bash
python manage.py report_legal_review_pack_index --country FR --format markdown
```
Per source: candidate?, attachment?, hash?, version?, the country's generated
**review package** path, latest review, calculation-ready, and the recommended
action. PII-safe; never prints document contents.

In the admin (`Legal sources → Legal sources`): the changelist shows a compact
`evidence` column (`attach · hash · ver`), `latest review` and `readiness`; the
read-only actions **"Show evidence checklist"** and **"Report review readiness"**
surface the same as messages. There is no "approve calculation" button.

## 3. Attach the official source file

When a source has no attachment (`needs attachment`):

```bash
python manage.py attach_official_source_file --slug <slug> --file <path-to-official-file>
```
Copies the file, runs the marker check, records the `[manual_attach]` notes
block and creates the source as `needs_review` if new. Fail-closed: a marker
failure aborts with no copy and no write. It never promotes or creates a review.
See `docs/legal_sources/MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md`.

## 4. Verify the hash

The attachment's `sha256` is computed automatically on save. To re-validate the
official sources (recompute SHA-256, run the marker check, write the
`[official_source_validation]` notes block):

```bash
python manage.py validate_official_legal_sources           # dry-run
python manage.py validate_official_legal_sources --commit   # write notes block
```
This never changes `status`, never creates a `LegalReview`, never touches a
dataset.

## 5. Generate / refresh the review package

```bash
python manage.py generate_legal_review_package --country FR --format markdown \
  --output docs/legal_sources/generated/FR_REVIEW_PACKAGE_GENERATED_<date>.md
```
Read-only snapshot the reviewer reads; it approves nothing.

## 6. Record a LegalReview decision

In the admin, `Legal reviews → Add`: pick the source and a decision
(`approve` / `reject` / `request_changes` / `reopen`) and a comment. The reviewer
is forced to the logged-in user; reviews are **append-only** (never edited or
deleted). For the official allow-list, promotion to APPROVED is done by:

```bash
python manage.py promote_official_legal_sources --reviewer-username <user> --slug <slug> --commit
```
(allow-list + in-process re-validation + staff reviewer; never activates a
calculator).

## 7. When NOT to proceed

- A `--fail-...` guard exits non-zero → STOP and investigate.
- The source has no attachment / no verified hash / no version.
- There is no Studio `approve` review.
- The document is authenticated but the calculation mapping is not validated.

## 8. Before a future dataset seed

`ready_for_dataset_seed_review = true` means: the source is APPROVED with an
`approve` review — the Studio **may consider** a dataset-seed review. It is NOT
an instruction and does NOT make anything calculation-ready. A seed requires a
separate, validated mapping of the legal data into a `CompensationDataset`
(+ source version, per the H1-9 constraint).

## 9. Before a future calculation activation

Calculation activation for a country requires ALL of: APPROVED sources with
verified evidence, an APPROVED `CompensationDataset` with a `source_version`, a
validated engine mapping, and an explicit Studio decision. The fail-closed guards
(`--fail-if-calculation-ready-without-review`,
`--fail-if-approved-without-source-version`) must pass.

## 10. Interpreting `UNAVAILABLE_REQUIRES_LEGAL_VALIDATION`

This is the engine's **fail-closed** result: the jurisdiction/case-type has no
APPROVED dataset backing it, so the platform refuses to output a number. It is
the correct, safe state for FR/BE/MA/TN today — not a bug. Public labels:
"Validazione legale richiesta" / "Validation juridique requise" / the Arabic
equivalent.
