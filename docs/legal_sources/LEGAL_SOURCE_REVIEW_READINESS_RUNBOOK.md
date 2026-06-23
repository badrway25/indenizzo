# Legal Source Review Readiness — Runbook (D1)

How the Studio checks what each legal source still needs before it could ever be
promoted/approved, and how to keep FR/BE/MA/TN fail-closed. All read-only.

> *Meglio nessun calcolo che un calcolo falso.* Nothing in this runbook promotes
> a source, approves a dataset, or activates a calculator.

## 1. See the readiness of every source

```bash
python manage.py report_legal_review_readiness                 # all countries, text
python manage.py report_legal_review_readiness --country FR    # one country
python manage.py report_legal_review_readiness --format markdown \
    --output docs/legal_sources/generated/FR_READINESS.md
```

Per source it reports: status, latest review decision, version/attachment/hash
counts, `calculation_ready` (true only when an APPROVED dataset with a source
version backs it), the ordered **missing steps**, and the **recommended next
action**. Read-only, PII-safe (no emails/personal data).

## 2. Typical review loop (per source)

The `missing steps` are the loop, in order:

1. **attach the official source file** → `attach_official_source_file --slug … --file …`
2. **compute/verify SHA-256** (done by the attach/validate commands)
3. **create a LegalSourceVersion** (admin or seed)
4. **obtain a Studio legal review (approve)** — record a `LegalReview` via the
   admin (`LegalReview` add page forces `reviewer=request.user`) or the
   promotion command. Append-only: decisions are never edited/deleted.
5. **promote the source to APPROVED** → `promote_official_legal_sources
   --reviewer-username … --slug … --commit` (allow-list + re-validation only).
6. **seed + approve a CompensationDataset with a source version** — the separate,
   human-gated **calculation-activation** step. NOT part of this workflow; do it
   only after the legal review explicitly authorises a country.

## 3. Fail-closed guards (Studio / CI)

```bash
# non-zero exit if any calculation-ready source lacks an approve review:
python manage.py report_legal_review_readiness --fail-if-calculation-ready-without-review
# non-zero exit if any APPROVED dataset lacks a source_version (re-asserts H1-9):
python manage.py report_legal_review_readiness --fail-if-approved-without-source-version
```

Run these before/after any promotion. A non-zero exit means STOP and investigate.

## 4. Admin (back-office)

`Admin → Legal sources → Legal sources`:

- the changelist shows **latest review** and **readiness** ("calc-ready" /
  "needs N step(s)") columns;
- filter by country / status;
- the source detail shows versions, attachments (hash) and the append-only
  review history inline;
- the **"Report review readiness (read-only, no changes)"** action surfaces the
  missing steps for the selected sources as messages — it creates nothing.

There is intentionally **no "approve calculation" button**: activation is a
deliberate, separate, human decision.

## 5. What NOT to do

- Do not treat `status == approved` as "calculation active": it only means the
  document is authenticated. `calculation_ready` is the real gate.
- Do not seed/approve an FR/BE/MA/TN dataset before the Studio has approved that
  country's sources and the mapping has been validated.
- Do not edit or delete a `LegalReview` (append-only by design).
- Do not paste reviewer emails or any PII into tickets — the report is already
  PII-safe; keep it that way.
