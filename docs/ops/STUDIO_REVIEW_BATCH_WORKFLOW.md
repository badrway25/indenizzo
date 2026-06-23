# Studio Review Batch Workflow — Runbook (D3)

For the Studio reviewer. How to prepare an ordered review batch for a country,
work through it, and record real decisions in the back-office — **without
approving sources or activating calculations**. Everything here is read-only or
human-gated.

> *Meglio nessun calcolo che un calcolo falso.* The batch is a worklist, not an
> approval. A source feeds a public calculation only after a real Studio
> approval + an APPROVED dataset with a source version + a validated engine
> mapping + an explicit activation decision.

## 1. When to prepare a batch

- Before a Studio review session on a country (FR / BE / MA / TN).
- After attaching/validating new official sources, to re-order the worklist.
- Periodically, to track what is still missing per country.

## 2. Generate a batch

```bash
python manage.py prepare_studio_review_batch --country FR --format markdown \
  --output docs/legal_sources/generated/FR_STUDIO_REVIEW_BATCH_<date>.md
python manage.py prepare_studio_review_batch --country ALL --format json
python manage.py prepare_studio_review_batch --country MA --limit 10
```

Options: `--country FR|BE|MA|TN|IT|ALL`, `--format markdown|json`, `--output`,
`--limit`, `--include-ready` (also list calc-ready sources), `--no-include-blocked`,
`--today <ISO>` (deterministic freshness), and the fail-closed guards
`--fail-if-empty`, `--fail-if-calculation-ready-without-review`,
`--fail-if-approved-without-source-version`.

Default = read-only, PII-safe, **blocked** sources only (the review work). It
writes no DB row; `--output` writes a markdown/JSON file only where you point it
(prefer `docs/legal_sources/generated/`).

## 3. Read evidence / readiness per item

Each item shows: status, readiness (`needs N step(s)` / `calc-ready`), evidence
(`attach=… hash=… version=… package=…`, present/absent only), candidate yes/no,
latest review decision, the **repo-relative** review-package path, the
fail-closed reason, the ordered **missing steps** and the **recommended next
action**. No full hashes, no absolute paths, no reviewer names, no notes, no raw
text.

## 4. Fill in the decision template

Each item ends with a manual checklist — fill it **by hand**, it is never parsed:

```
[ ] Reject
[ ] Request changes
[ ] Approve metadata only
[ ] Approve for dataset seed review
[ ] Escalate for second legal review
```

## 5. Record the real decision in the back-office

The batch records nothing. To register a decision, use the admin
(`Legal reviews → Add`: source + decision + comment; reviewer forced to you;
append-only) or, for the official allow-list, the promotion command:

```bash
python manage.py promote_official_legal_sources --reviewer-username <you> --slug <slug> --commit
```

(allow-list + re-validation + staff reviewer; never activates a calculator).

## 6. What NOT to do

- Do not treat a filled-in checkbox as a system decision — record it in the
  back-office.
- Do not seed/approve an FR/BE/MA/TN dataset from a batch.
- Do not commit the raw official files (`legal_data/`), only the generated batch
  markdown if useful.
- Do not paste hashes / reviewer emails / notes / raw text into tickets — the
  batch is already free of them; keep it that way.

## 7. Why the batch does not activate calculations

It is built from read-only readiness/evidence data and emits only safe fields +
a manual template. It creates no `LegalReview`, promotes no status, seeds no
dataset and registers no engine. FR/BE/MA/TN stay `calculation_ready=False`.

## 8. Before a future activation

A country can be activated only after ALL of: APPROVED sources with verified
evidence, an APPROVED `CompensationDataset` with a `source_version` (H1-9), a
validated engine mapping, and an explicit Studio decision. The guards
(`--fail-if-calculation-ready-without-review`,
`--fail-if-approved-without-source-version`) must pass.

## 9. Archiving a batch safely

Save the generated markdown under `docs/legal_sources/generated/` (it contains no
PII / raw legal data by construction). Do not attach the raw official PDFs to the
batch. Keep one dated file per session.
