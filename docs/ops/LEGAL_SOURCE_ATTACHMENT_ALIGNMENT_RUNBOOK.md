# Legal Source Attachment Alignment — Runbook (D5)

For ops / the Studio. How to read and resolve the strict review-validator's
blocking findings (approved sources with no `LegalSourceAttachment` row) — safely,
without inventing attachments or hashes, and without activating any calculation.

> *Meglio un finding chiaro che una falsa evidenza.* Never fabricate an attachment
> or a hash to silence a finding. Attach the real official file or leave the
> finding for the Studio.

## 1. Why the strict validator flags legacy approves

`validate_legal_review_decisions --fail-on-blocking` flags sources whose latest
review is `approve` but which lack an attachment row / hash / version. Some
official sources were promoted to APPROVED on a disk-file validation
(`promote_official_legal_sources`) without the separate
`attach_official_source_file` step that creates the DB attachment row.

## 2. Read the audit

```bash
python manage.py audit_legacy_attachment_alignment --country ALL --format markdown
python manage.py audit_legacy_attachment_alignment --country TN --format json
```

Per source: classification, strict-validator impact, present/absent evidence
flags and a safe recommended action. Read-only, PII-safe (no full hashes, paths,
reviewer names or notes).

## 3. What the classifications mean

- **`missing_attachment_row`** (registry candidate) — the documented official
  source exists; attach the real file (see §5), then re-validate. *Blocking.*
- **`manual_review_required`** (not a registry candidate) — the Studio must
  source the official file before the approval can stand. *Blocking.*
- **`missing_source_version`** — create a `LegalSourceVersion`. *Warning.*
- **`hash_unavailable`** — run `validate_official_legal_sources` to compute/verify
  the SHA-256. *Blocking.*
- **`ok`** — attachment + hash + version present; nothing to do.

## 4. What requires Studio intervention

Anything `manual_review_required` (no documented official source) and any case
where the official file is not available to ops. Do not approximate.

## 5. Attach an official file correctly

Use the existing, tested workflow (it computes the real SHA-256 from the file and
records a `[manual_attach]` notes block; it never promotes or approves):

```bash
python manage.py attach_official_source_file --slug <slug> --file <path-to-official-file>
python manage.py validate_official_legal_sources --slug <slug> --commit
```

See `docs/legal_sources/MANUAL_ATTACH_OFFICIAL_SOURCE_RUNBOOK.md`. Do NOT commit
the raw official file (`legal_data/` is gitignored).

## 6. Re-run the validator

```bash
python manage.py validate_legal_review_decisions --country ALL --fail-on-blocking
```

Once the attachment + hash (+ version) exist, the source becomes `ok` and the
strict gate stops flagging it.

## 7. What NOT to do

- Do not fabricate a `LegalSourceAttachment` or a hash to clear a finding.
- Do not commit raw legal files / `legal_data/`.
- Do not treat alignment as approval or as calculation activation.
- Do not paste hashes / reviewer emails / notes into tickets.

## 8. Why this does not activate calculations

The audit and the attach workflow only manage *document evidence*. A source feeds
a public calculation only after a real Studio approval **and** an APPROVED
`CompensationDataset` with a `source_version` (H1-9) **and** a validated engine
mapping **and** an explicit activation decision. FR/BE/MA/TN stay
`calculation_ready=False`.
