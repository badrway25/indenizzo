# Legal Review Decision Intake — Runbook (D4)

For the Studio reviewer recording a real `LegalReview` decision in the back-office
after working a review batch (D3). The intake is guarded but **never** activates a
calculation.

> *Meglio nessun calcolo che un calcolo falso.* Recording `approve` authenticates
> the document at the review level — it does NOT make the source feed a public
> calculation.

## 1. From batch (D3) to a manual decision

1. Generate/read the batch: `python manage.py prepare_studio_review_batch --country FR`.
2. Work each item; check evidence (attachment, hash, version, package).
3. Record the decision in the admin: `Legal reviews → Add` (source + decision +
   comment; reviewer is forced to you; append-only).

## 2. When to use each decision

- **reject** — the source is not usable. Always allowed; add a clear comment.
- **request_changes** — fixes are needed (attach the file, verify the hash, add a
  version). Always allowed; comment.
- **reopen** — resume a previously closed review.
- **approve** — the document is authenticated. **Allowed only with an attached,
  hash-verified document.** Missing attachment/hash is **blocked** at intake;
  missing source version / review package produces a warning.

## 3. Why approve does not activate a calculation

The decision guard always returns `calculation_activation_allowed = False`.
Calculation activation is a separate, later, human-gated step that also requires
an APPROVED `CompensationDataset` with a `source_version` (H1-9) and a validated
engine mapping. FR/BE/MA/TN stay `calculation_ready=False`.

## 4. Warnings that must stop you

- "no official attachment" / "attachment is not hash-verified" → **blocking**:
  fix the evidence before approving.
- "no LegalSourceVersion" / "no generated review package" → warnings: do not rely
  on the approval for any downstream step until resolved.

## 5. Prerequisites before a future activation

ALL of: APPROVED sources with verified evidence, an APPROVED dataset with a
`source_version`, a validated engine mapping, and an explicit Studio activation
decision. The audit guards must pass.

## 6. Audit recorded decisions (read-only)

```bash
python manage.py validate_legal_review_decisions --country ALL --format markdown
python manage.py validate_legal_review_decisions --include-history --fail-on-blocking
```

It re-checks every recorded decision against the current evidence and the
fail-closed invariants (calc-ready-without-review, approved-without-version,
non-IT-calc-ready). Read-only, PII-safe. Run it before/after a review session.

## 7. What NOT to do

- Do not approve a source with no attached/verified document (the intake blocks
  it — do not work around it).
- Do not treat an approval as a calculation activation.
- Do not seed/approve an FR/BE/MA/TN dataset from a review.
- Do not paste reviewer emails, hashes, notes or raw legal text into tickets.
- Do not edit/delete a recorded `LegalReview` (append-only by design).
